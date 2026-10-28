"""LLM command generation using local Ollama."""

from __future__ import annotations

import json
import logging
import os
import re
from typing import Literal, Optional

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_ollama import ChatOllama
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

load_dotenv()

logger = logging.getLogger(__name__)

OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:3b")
FEW_SHOT_COUNT = int(os.getenv("FEW_SHOT_COUNT", "5"))


class CommandOutput(BaseModel):
    """Pydantic model representing structured CLI command generation."""

    model_config = ConfigDict(extra="forbid")

    command: str = Field(description="The exact Windows PowerShell command to execute")
    explanation: str = Field(description="A concise one-line explanation of what the command does")
    risk: Literal["read", "modifying", "destructive"] = Field(
        description="Risk tier: 'read' for observational commands, 'modifying' for state changes, 'destructive' for deletions/terminations"
    )

    @field_validator("command")
    @classmethod
    def check_non_empty(cls, v: str) -> str:
        cleaned = v.strip().strip("`").strip()
        if not cleaned:
            raise ValueError("Command field must not be empty.")
        return cleaned


def get_llm(use_structured_format: bool = True) -> ChatOllama:
    """Create the local Ollama model instance with optional JSON schema format."""

    format_arg = CommandOutput.model_json_schema() if use_structured_format else None

    return ChatOllama(
        model=os.getenv("OLLAMA_MODEL", OLLAMA_MODEL),
        temperature=0,
        seed=42,
        num_thread=8,
        format=format_arg,
    )


def parse_response(text: str) -> tuple[str, str, str]:
    """Parse and validate JSON response from Ollama against the Pydantic schema with fallback parsers.

    Returns:
        (command, explanation, risk)
    """
    cleaned = text.strip()

    # Clean markdown code blocks if wrapped
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    cleaned = cleaned.strip()

    # Strategy 1: Strict Pydantic model validation from JSON
    try:
        validated = CommandOutput.model_validate_json(cleaned)
        return validated.command, validated.explanation, validated.risk
    except ValidationError:
        pass
    except Exception:
        pass

    # Strategy 2: If JSON is valid dictionary, extract core fields and validate via Pydantic
    if cleaned.startswith("{") and cleaned.endswith("}"):
        try:
            data = json.loads(cleaned)
            if isinstance(data, dict) and "command" in data:
                cmd = str(data.get("command", "")).strip("`").strip()
                if not cmd:
                    raise RuntimeError(f"Parsed JSON contained empty command: {data}")
                exp = str(data.get("explanation", "")).strip() or "Generated command"
                risk_raw = str(data.get("risk", "read")).lower().strip()
                risk = risk_raw if risk_raw in ("read", "modifying", "destructive") else "read"
                validated = CommandOutput(command=cmd, explanation=exp, risk=risk)
                return validated.command, validated.explanation, validated.risk
            elif isinstance(data, dict) and "command" not in data:
                raise RuntimeError(f"Parsed JSON missing required 'command' field: {data}")
        except (RuntimeError, ValueError) as e:
            raise RuntimeError(str(e)) from e
        except Exception:
            pass

    # Strategy 3: Attempt key-value text parsing fallback
    cmd, exp, risk = "", "", "read"
    for line in text.splitlines():
        line_str = line.strip()
        if line_str.upper().startswith("COMMAND:"):
            cmd = line_str[len("COMMAND:"):].strip()
        elif line_str.upper().startswith("EXPLANATION:"):
            exp = line_str[len("EXPLANATION:"):].strip()
        elif line_str.upper().startswith("RISK:"):
            risk_val = line_str[len("RISK:"):].strip().lower()
            if risk_val in ("read", "modifying", "destructive"):
                risk = risk_val

    if not cmd:
        code_match = re.search(
            r"```(?:powershell|cmd|ps1)?\s*(.*?)\s*```", text, re.DOTALL | re.IGNORECASE
        )
        if code_match:
            cmd = code_match.group(1).strip()

    cmd = cmd.strip("`").strip()

    if not cmd:
        # Non-JSON plain string fallback ONLY if it doesn't look like JSON
        if not cleaned.startswith("{") and not cleaned.startswith("["):
            lines_clean = [
                l.strip()
                for l in text.splitlines()
                if l.strip() and not l.strip().upper().startswith("EXPLANATION:")
            ]
            # Don't accept conversational English as a command
            if lines_clean and not any(w in lines_clean[0].lower() for w in ["invalid", "garbage", "cannot", "sorry", "error"]):
                cmd = lines_clean[0].strip("`").strip()

    if not cmd:
        raise RuntimeError(f"Could not parse valid command from Ollama response:\n{text}")

    # Final attempt to validate extracted fields through Pydantic
    try:
        validated = CommandOutput(
            command=cmd,
            explanation=exp or "Generated command",
            risk=risk if risk in ("read", "modifying", "destructive") else "read",
        )
        return validated.command, validated.explanation, validated.risk
    except ValidationError as e:
        raise RuntimeError(f"Extracted command failed Pydantic schema validation: {e}\nRaw output: {text}") from e


def generate_command(
    prompt: str, error_feedback: Optional[str] = None
) -> tuple[str, str, str]:
    """Convert natural language into a Windows PowerShell command using Ollama structured output.

    If schema validation fails, re-prompts once with the validation error before raising.
    """

    llm = get_llm(use_structured_format=True)

    system_prompt = (
        "You are a Windows PowerShell command generator.\n\n"
        "Your job is to convert the user's request into ONE PowerShell command.\n\n"
        "Rules:\n"
        "1. Return exactly one command.\n"
        "2. Prefer built-in Windows PowerShell cmdlets.\n"
        "3. Prefer read-only commands when the user asks for information.\n"
        "4. Never use destructive commands unless the user explicitly requests the operation.\n"
        "5. Do not invent PowerShell object properties or parameters.\n"
        "6. Prefer simple, reliable commands over unnecessarily complex pipelines.\n"
        "7. Command guidelines:\n"
        "   - Do not restrict file searches to specific extensions (such as *.ps1) unless the user explicitly requested that extension.\n"
        "   - The -Filter parameter accepts only a single string without commas. For multiple extensions or general files, omit -Filter or use Where-Object.\n"
        "   - To read file contents, use Get-Content (do not use Get-ChildItem to display file contents).\n"
        "   - Use standard Windows PowerShell cmdlets (e.g. Get-PSDrive for disk space, Get-Process for processes, Get-Location for current directory).\n"
        "8. Return your response ONLY as a JSON object matching this schema:\n"
        "{\n"
        '  "command": "<PowerShell command>",\n'
        '  "explanation": "<short explanation>",\n'
        '  "risk": "read|modifying|destructive"\n'
        "}\n"
        "Do not include any text outside the JSON object."
    )

    if FEW_SHOT_COUNT > 0:
        try:
            from .few_shots import FEW_SHOT_EXAMPLES
            selected = FEW_SHOT_EXAMPLES[:FEW_SHOT_COUNT]
            if selected:
                system_prompt += "\n\nExamples of correct command generation:\n"
                for ex in selected:
                    system_prompt += (
                        f"Request: {ex['prompt']}\n"
                        f'{{"command": "{ex["command"]}", "explanation": "{ex["explanation"]}", "risk": "{ex["risk"]}"}}\n'
                    )
        except ImportError:
            pass

    user_content = f"User request:\n{prompt}"
    if error_feedback:
        user_content += (
            f"\n\n{error_feedback}\n\n"
            "Generate a different PowerShell command that directly satisfies the original request. "
            "Do NOT repeat the failed command. Prefer standard Windows PowerShell cmdlets."
        )

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_content),
    ]

    try:
        response = llm.invoke(messages)
        text = response.content.strip()
        return parse_response(text)
    except Exception as initial_err:
        logger.warning("Initial response failed schema validation or invocation: %s. Re-prompting once with schema error.", initial_err)
        # Re-prompt once with the schema error
        reprompt_messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(
                content=(
                    f"User request:\n{prompt}\n\n"
                    f"Your previous response failed JSON schema validation with error:\n{initial_err}\n\n"
                    "Please correct the JSON output so that it strictly adheres to the schema with non-empty 'command', "
                    "'explanation', and 'risk' being one of 'read', 'modifying', or 'destructive'. Return ONLY valid JSON."
                )
            ),
        ]
        try:
            second_response = llm.invoke(reprompt_messages)
            second_text = second_response.content.strip()
            return parse_response(second_text)
        except Exception as second_err:
            raise RuntimeError(f"LLM command generation failed after re-prompt: {second_err}") from second_err