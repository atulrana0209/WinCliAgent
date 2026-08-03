"""LangGraph node functions."""

from __future__ import annotations

from langgraph.graph import END

from .executor import run_command
from .llm import generate_command
from .result_validator import validate_result
from .safety import screen_command
from .state import AgentState
from .validator import validate_command

MAX_RETRIES = 2


def generate_node(state: AgentState) -> AgentState:
    """Turn the user prompt into a Windows CLI command, preventing duplicate failed commands."""

    prompt = state.get("prompt", "")
    error_feedback = state.get("error_feedback")
    previous_commands = list(state.get("previous_commands", []))

    command, explanation, _risk = generate_command(prompt, error_feedback=error_feedback)

    # Phase 4: Prevent repeated failed commands
    if command.strip().lower() in [c.strip().lower() for c in previous_commands]:
        retry_feedback = (
            f"{error_feedback or ''}\n\n"
            f"The command '{command}' was ALREADY tried and failed. "
            "You MUST generate a completely DIFFERENT PowerShell command."
        )
        command, explanation, _risk = generate_command(prompt, error_feedback=retry_feedback)

    previous_commands.append(command)

    return {
        "command": command,
        "explanation": explanation,
        "executed": False,
        "semantic_valid": False,
        "previous_commands": previous_commands,
    }


def validate_node(state: AgentState) -> AgentState:
    """Check whether the generated command matches the user's request."""

    command = state.get("command", "")
    prompt = state.get("prompt", "")

    is_valid, reason = validate_command(command, prompt)

    updates: AgentState = {
        "is_valid": is_valid,
        "validation_reason": reason,
    }

    if not is_valid:
        updates["error_feedback"] = (
            f"Original request:\n{prompt}\n\n"
            f"Previous command:\n{command}\n\n"
            f"Validation failure:\n{reason}"
        )

    return updates


def safety_node(state: AgentState) -> AgentState:
    """Screen the generated command."""

    command = state.get("command", "")
    is_safe, reason, _risk = screen_command(command)

    return {
        "is_safe": is_safe,
        "safety_reason": reason,
    }


def execute_node(state: AgentState) -> AgentState:
    """Execute the command and capture its output."""

    if not state.get("is_safe", False) or not state.get("is_valid", False):
        return {
            "executed": False,
            "stdout": "",
            "stderr": "Execution blocked due to safety or validation errors.",
            "exit_code": None,
        }

    result = run_command(state["command"])

    return {
        "executed": True,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "exit_code": result.exit_code,
    }


def result_validation_node(state: AgentState) -> AgentState:
    """Validate whether the execution result actually answers the user prompt."""

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
    """Decide whether to execute or block."""

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