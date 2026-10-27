"""LLM command generation using local Ollama."""

from __future__ import annotations

import json
import os
import re
from typing import Optional

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_ollama import ChatOllama

load_dotenv()

OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:3b")


def get_llm() -> ChatOllama:
    """Create the local Ollama model instance."""

    return ChatOllama(
        model=OLLAMA_MODEL,
        temperature=0,
        seed=42,
    )


def parse_response(text: str) -> tuple[str, str, str]:
    """Parse JSON response from Ollama with fallback parsers.

    Returns:
        (command, explanation, risk)
    """
    cleaned = text.strip()

    # Clean markdown code blocks if wrapped
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    cleaned = cleaned.strip()

    # Strategy 1: Attempt JSON parsing
    try:
        data = json.loads(cleaned)
        if isinstance(data, dict) and "command" in data:
            cmd = str(data.get("command", "")).strip("`").strip()
            exp = str(data.get("explanation", "")).strip()
            risk = str(data.get("risk", "unknown")).lower().strip()
            if cmd:
                return cmd, exp, risk
    except Exception:
        pass

    # Strategy 2: Attempt key-value text parsing (COMMAND: / EXPLANATION:)
    cmd, exp, risk = "", "", "unknown"
    for line in text.splitlines():
        line_str = line.strip()
        if line_str.upper().startswith("COMMAND:"):
            cmd = line_str[len("COMMAND:"):].strip()
        elif line_str.upper().startswith("EXPLANATION:"):
            exp = line_str[len("EXPLANATION:"):].strip()
        elif line_str.upper().startswith("RISK:"):
            risk = line_str[len("RISK:"):].strip().lower()

    if not cmd:
        code_match = re.search(
            r"```(?:powershell|cmd|ps1)?\s*(.*?)\s*```", text, re.DOTALL | re.IGNORECASE
        )
        if code_match:
            cmd = code_match.group(1).strip()

    cmd = cmd.strip("`").strip()

    if not cmd:
        lines_clean = [
            l.strip()
            for l in text.splitlines()
            if l.strip() and not l.strip().upper().startswith("EXPLANATION:")
        ]
        if lines_clean:
            cmd = lines_clean[0].strip("`").strip()

    if not cmd:
        raise RuntimeError(f"Could not parse command from Ollama response:\n{text}")

    return cmd, exp, risk


def generate_command(
    prompt: str, error_feedback: Optional[str] = None
) -> tuple[str, str, str]:
    """Convert natural language into a Windows PowerShell command."""

    llm = get_llm()

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

    response = llm.invoke(messages)
    text = response.content.strip()

    return parse_response(text)