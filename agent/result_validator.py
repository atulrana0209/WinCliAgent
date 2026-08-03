"""Semantic result validation for executed PowerShell commands."""

from __future__ import annotations

import re
from typing import Any

EXPECTED_CONCEPTS: dict[str, list[str]] = {
    "ip configuration": ["ip", "address", "adapter", "interface", "gateway", "dns", "ethernet", "wi-fi", "v4", "v6"],
    "ip config": ["ip", "address", "adapter", "interface", "gateway", "dns", "ethernet", "wi-fi"],
    "ip address": ["ip", "address", "adapter", "interface", "gateway"],
    "mac address": ["mac", "address", "adapter", "physical"],
    "disk usage": ["used", "free", "size", "gb", "mb", "drive", "provider", "filesystem", "capacity"],
    "processes": ["process", "processname", "cpu", "handles", "pm(k)", "ws(k)", "id"],
    "services": ["status", "displayname", "running", "stopped", "service"],
    "python files": [".py"],
    "list files": ["mode", "lastwritetime", "length", "directory", "file"],
    "windows version": ["caption", "version", "build", "os", "microsoft", "windows", "productname"],
}

GUI_COMMANDS = {"winver", "notepad", "calc", "ms-settings"}

ERROR_INDICATORS = [
    r"CommandNotFoundException",
    r"ParameterBindingException",
    r"PropertyNotFoundException",
    r"Cannot find path",
    r"Access is denied",
    r"The term '[^']+' is not recognized",
]


def extract_keywords(prompt: str) -> set[str]:
    """Extract key non-stop words from prompt for generic relevance matching."""
    stop_words = {
        "show", "get", "list", "display", "view", "find", "check", "my", "the",
        "a", "an", "in", "of", "on", "for", "with", "all", "current", "running", "directory"
    }
    words = re.findall(r"\b[a-zA-Z0-9_-]{3,}\b", prompt.lower())
    return {w for w in words if w not in stop_words}


def validate_result(
    user_prompt: str,
    command: str,
    stdout: str,
    stderr: str,
    exit_code: int,
) -> dict[str, Any]:
    """Check whether the command output actually provides useful information answering the user request.

    Returns:
        {
            "valid": bool,
            "reason": str,
            "quality": "success" | "empty" | "failed" | "irrelevant" | "gui_success" | "malformed"
        }
    """
    cmd_lower = command.strip().lower()
    prompt_lower = user_prompt.strip().lower()
    stdout_clean = stdout.strip()
    stderr_clean = stderr.strip()

    # RULE 1 — PowerShell failure
    if exit_code != 0:
        err_msg = stderr_clean or stdout_clean or f"Non-zero exit code ({exit_code})"
        return {
            "valid": False,
            "reason": f"PowerShell command failed: {err_msg}",
            "quality": "failed",
        }

    # RULE 3 — GUI commands & legitimate empty output
    if any(gui_cmd in cmd_lower for gui_cmd in GUI_COMMANDS):
        return {
            "valid": True,
            "reason": "GUI command launched successfully.",
            "quality": "gui_success",
        }

    # RULE 4 — Detect obvious PowerShell error indicators
    combined_output = f"{stderr_clean}\n{stdout_clean}".strip()
    for pattern in ERROR_INDICATORS:
        match = re.search(pattern, combined_output, flags=re.IGNORECASE)
        if match:
            return {
                "valid": False,
                "reason": f"Detected PowerShell error: '{match.group(0)}'",
                "quality": "failed",
            }

    # RULE 2 — Useful stdout check
    if not stdout_clean:
        return {
            "valid": False,
            "reason": "Command executed successfully with exit code 0 but produced no output.",
            "quality": "empty",
        }

    stdout_lower = stdout_clean.lower()

    # Special check for disk usage
    if "disk usage" in prompt_lower or ("disk" in prompt_lower and "usage" in prompt_lower):
        has_disk_info = any(k in stdout_lower for k in ["used", "free", "size", "gb", "mb", "capacity", "filesystem"])
        if not has_disk_info:
            return {
                "valid": False,
                "reason": "Command completed but did not clearly provide useful disk usage information.",
                "quality": "irrelevant",
            }

    # CONCEPT CHECK for known categories
    for key, concepts in EXPECTED_CONCEPTS.items():
        if key in prompt_lower:
            if not any(concept in stdout_lower for concept in concepts):
                return {
                    "valid": False,
                    "reason": f"Command output does not contain expected details ({', '.join(concepts[:4])}) for '{key}'.",
                    "quality": "irrelevant",
                }
            return {
                "valid": True,
                "reason": "Command successfully answered the request with useful output.",
                "quality": "success",
            }

    # RULE 5 — Generic request/result relevance matching for unknown categories
    prompt_keywords = extract_keywords(user_prompt)
    if prompt_keywords:
        if "process" in prompt_lower and "process" not in stdout_lower:
            return {
                "valid": False,
                "reason": "Output does not contain process information for process request.",
                "quality": "irrelevant",
            }
        if "ip" in prompt_lower and not any(k in stdout_lower for k in ["ip", "address", "adapter"]):
            return {
                "valid": False,
                "reason": "Output does not contain IP or network information for IP request.",
                "quality": "irrelevant",
            }

    return {
        "valid": True,
        "reason": "Command successfully answered the request with useful output.",
        "quality": "success",
    }
