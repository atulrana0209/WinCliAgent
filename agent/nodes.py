"""LangGraph node functions."""

from __future__ import annotations

from langgraph.graph import END

from .executor import run_command
from .llm import generate_command
from .logger import log_audit_event
from .normalizer import normalize_command
from .result_validator import validate_result
from .safety import (
    classify_rule_tier_all_segments,
    combine_risk_tiers,
    screen_command_risk,
)
from .state import AgentState
from .validator import validate_command

MAX_RETRIES = 2


def generate_node(state: AgentState) -> AgentState:
    """Turn user prompt into a normalized Windows CLI command, avoiding duplicates."""

    prompt = state.get("prompt", "")
    error_feedback = state.get("error_feedback")
    previous_commands = list(state.get("previous_commands", []))

    command, explanation, llm_risk = generate_command(prompt, error_feedback=error_feedback)
    normalized = normalize_command(command)

    # Prevent repeating failed commands
    if normalized.strip().lower() in [c.strip().lower() for c in previous_commands]:
        retry_feedback = (
            f"{error_feedback or ''}\n\n"
            f"The command '{normalized}' was ALREADY attempted and failed. "
            "Generate a completely DIFFERENT PowerShell command."
        )
        command, explanation, llm_risk = generate_command(prompt, error_feedback=retry_feedback)
        normalized = normalize_command(command)

    previous_commands.append(normalized)

    if state.get("verbose"):
        print(f"\n[GENERATE]\nModel : Ollama (qwen2.5:3b)\nCommand: {normalized}\nLLM Risk: {llm_risk}")

    return {
        "command": normalized,
        "explanation": explanation,
        "llm_risk": llm_risk,
        "executed": False,
        "semantic_valid": False,
        "previous_commands": previous_commands,
    }


def validate_node(state: AgentState) -> AgentState:
    """Check whether the generated command matches the user's request."""

    command = state.get("command", "")
    prompt = state.get("prompt", "")

    is_valid, reason = validate_command(command, prompt)

    if state.get("verbose"):
        print(f"\n[VALIDATE]\nSyntax & Concept Check: {'PASS' if is_valid else 'FAIL'}\nReason: {reason}")

    updates: AgentState = {
        "is_valid": is_valid,
        "validation_reason": reason,
    }

    if not is_valid:
        updates["error_feedback"] = (
            f"Original request:\n{prompt}\n\n"
            f"Previous command:\n{command}\n\n"
            f"Validation problem:\n{reason}"
        )

    return updates


def safety_node(state: AgentState) -> AgentState:
    """Screen the generated command using 4-tier risk classification."""

    command = state.get("command", "")
    llm_risk = state.get("llm_risk")

    is_safe, reason, risk_level, action = screen_command_risk(command, llm_risk=llm_risk)
    _rule_tier, _rule_reason, is_allowlisted = classify_rule_tier_all_segments(command)

    if state.get("verbose"):
        print(f"\n[SAFETY]\nRisk   : {risk_level}\nAction : {action}\nReason : {reason}")

    return {
        "is_safe": is_safe,
        "safety_reason": reason,
        "risk_level": risk_level,
        "action": action,
        "is_allowlisted": is_allowlisted,
    }


def execute_node(state: AgentState) -> AgentState:
    """Execute command or skip if dry-run / explain mode / unapproved."""

    # Dry-Run / Explain mode check
    if state.get("dry_run") or state.get("explain_mode"):
        log_audit_event(
            user_prompt=state.get("prompt", ""),
            generated_command=state.get("command", ""),
            risk=state.get("risk_level", "LOW"),
            action=state.get("action", "ALLOWED"),
            approved=False,
            exit_code=0,
            validation="DRY_RUN",
            retry_count=state.get("retry_count", 0),
            approval_decision="DRY_RUN",
        )
        return {
            "executed": False,
            "stdout": "DRY RUN / EXPLAIN — command was NOT executed",
            "stderr": "",
            "exit_code": 0,
        }

    risk = state.get("risk_level", "LOW")
    approved = state.get("approved", False)
    is_valid = state.get("is_valid", False)

    # CRITICAL: Hard block, no override
    if risk == "CRITICAL":
        log_audit_event(
            user_prompt=state.get("prompt", ""),
            generated_command=state.get("command", ""),
            risk=risk,
            action="BLOCKED",
            approved=False,
            exit_code=None,
            validation="BLOCKED",
            retry_count=state.get("retry_count", 0),
            approval_decision="HARD_BLOCKED",
        )
        return {
            "executed": False,
            "stdout": "",
            "stderr": "Execution blocked: CRITICAL risk command cannot be executed under any circumstances.",
            "exit_code": None,
        }

    # HIGH: Requires explicit typed confirmation
    if risk == "HIGH" and not approved:
        log_audit_event(
            user_prompt=state.get("prompt", ""),
            generated_command=state.get("command", ""),
            risk=risk,
            action="BLOCKED",
            approved=False,
            exit_code=None,
            validation="BLOCKED",
            retry_count=state.get("retry_count", 0),
            approval_decision="REJECTED_EXPLICIT",
        )
        return {
            "executed": False,
            "stdout": "",
            "stderr": "Execution blocked: HIGH risk command requires explicit typed confirmation.",
            "exit_code": None,
        }

    # Validation failure check
    if not is_valid:
        log_audit_event(
            user_prompt=state.get("prompt", ""),
            generated_command=state.get("command", ""),
            risk=risk,
            action="BLOCKED",
            approved=False,
            exit_code=None,
            validation="BLOCKED",
            retry_count=state.get("retry_count", 0),
            approval_decision="REJECTED",
        )
        return {
            "executed": False,
            "stdout": "",
            "stderr": "Execution blocked due to safety or validation errors.",
            "exit_code": None,
        }

    if state.get("verbose"):
        print(f"\n[EXECUTE]\nRunning command through PowerShell...")

    result = run_command(state["command"])

    if state.get("verbose"):
        print(f"Exit Code: {result.exit_code}")

    return {
        "executed": True,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "exit_code": result.exit_code,
    }


def result_validation_node(state: AgentState) -> AgentState:
    """Validate output quality and record audit event."""

    if state.get("dry_run") or state.get("explain_mode"):
        return {
            "semantic_valid": True,
            "semantic_reason": "Dry run mode completed.",
        }

    if not state.get("executed", False):
        return {
            "semantic_valid": False,
            "semantic_reason": "Command execution was not performed.",
        }

    prompt = state.get("prompt", "")
    command = state.get("command", "")
    stdout = state.get("stdout", "")
    stderr = state.get("stderr", "")
    exit_code = state.get("exit_code", 1)

    val_res = validate_result(prompt, command, stdout, stderr, exit_code)
    is_valid = bool(val_res["valid"])
    reason = str(val_res["reason"])

    if state.get("verbose"):
        print(f"\n[RESULT]\nSemantic Validation: {'PASS' if is_valid else 'FAIL'}\nQuality: {val_res.get('quality')}\nReason: {reason}")

    # Determine approval decision recorded in audit log
    approval_decision = "AUTO"
    if state.get("risk_level") == "HIGH":
        approval_decision = "APPROVED_EXPLICIT"
    elif state.get("risk_level") == "MEDIUM":
        approval_decision = "APPROVED_CONFIRMATION"
    elif not state.get("is_allowlisted", True):
        approval_decision = "APPROVED_CONFIRMATION"

    # Audit log entry
    log_audit_event(
        user_prompt=prompt,
        generated_command=command,
        risk=state.get("risk_level", "LOW"),
        action=state.get("action", "ALLOWED"),
        approved=state.get("approved", True),
        exit_code=exit_code,
        validation="PASS" if is_valid else "FAILED",
        retry_count=state.get("retry_count", 0),
        approval_decision=approval_decision,
    )

    updates: AgentState = {
        "semantic_valid": is_valid,
        "semantic_reason": reason,
    }

    if not is_valid:
        updates["error_feedback"] = (
            f"Original request:\n{prompt}\n\n"
            f"Previous command:\n{command}\n\n"
            f"Exit code:\n{exit_code}\n\n"
            f"STDOUT:\n{stdout.strip()}\n\n"
            f"STDERR:\n{stderr.strip()}\n\n"
            f"Validation failure:\n{reason}"
        )

    return updates


def retry_node(state: AgentState) -> AgentState:
    """Increment retry counter before re-generating command."""
    current_retries = state.get("retry_count", 0)
    return {
        "retry_count": current_retries + 1,
    }


def blocked_node(state: AgentState) -> AgentState:
    """Terminal node for invalid or unsafe commands when no retries remain."""

    reason = ""
    if not state.get("is_valid", True):
        reason = "Validation error: " + state.get("validation_reason", "Invalid command")
    elif not state.get("is_safe", True):
        reason = "Safety screen: " + state.get("safety_reason", "Unsafe command")
    else:
        reason = "Execution blocked."

    return {
        "executed": False,
        "stdout": "",
        "stderr": f"Execution blocked: {reason}",
        "exit_code": None,
    }


def route_after_validation(state: AgentState) -> str:
    """Decide whether to proceed to safety screening or retry/block."""

    if state.get("is_valid", False):
        return "safety"

    if state.get("retry_count", 0) < MAX_RETRIES:
        return "retry"

    return "blocked"


def route_after_safety(state: AgentState) -> str:
    """Decide whether to execute or block.

    CRITICAL is a hard block: no override allowed.
    HIGH requires explicit typed confirmation (proceeds to human-in-the-loop interrupt).
    MEDIUM and LOW proceed to execute (subject to confirmation/auto-run).
    """
    risk = state.get("risk_level", "LOW")
    if risk == "CRITICAL":
        return "blocked"

    if risk == "HIGH":
        return "execute"

    if state.get("is_safe", False):
        return "execute"

    return "blocked"


def route_after_result_validation(state: AgentState) -> str:
    """Decide whether to finish or retry after result validation."""

    if state.get("semantic_valid", False):
        return "end"

    if state.get("retry_count", 0) < MAX_RETRIES:
        return "retry"

    return "end"
