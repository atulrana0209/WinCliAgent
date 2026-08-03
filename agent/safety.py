"""Safety and risk assessment for PowerShell commands."""

from __future__ import annotations

import re

DESTRUCTIVE_COMMANDS = [
    r"\bremove-item\b",
    r"\bstop-process\b",
    r"\bstop-service\b",
    r"\brestart-computer\b",
    r"\bstop-computer\b",
    r"\bshutdown\b",
    r"\bformat\b",
    r"\bclear-content\b",
    r"\bclear-disk\b",
    r"\bremove-partition\b",
    r"\bdiskpart\b",
    r"\bcipher\b\s+/w",
    r"\breg\b\s+delete",
    r"\bvssadmin\b\s+delete",
    r"\bbcdedit\b",
    r"\bdel\b",
    r"\berase\b",
    r"\brmdir\b",
    r"\brd\b",
]

DANGEROUS_ARGUMENTS = [
    r"-force\b",
    r"-recurse\b",
    r"/[sqf]\b",
    r"-confirm:\$false\b",
]

READONLY_VERBS = (
    "get-",
    "show-",
    "measure-",
    "test-",
    "select-",
    "where-",
    "export-",
)

READONLY_CMDS = {
    "pwd",
    "dir",
    "ls",
    "ipconfig",
    "getmac",
    "systeminfo",
    "whoami",
    "hostname",
    "ping",
    "tracert",
    "echo",
    "type",
}


def classify_risk(command: str) -> str:
    """Classify command risk level: 'destructive', 'read', or 'unknown'."""
    cmd_lower = command.strip().lower()

    for pattern in DESTRUCTIVE_COMMANDS:
        if re.search(pattern, cmd_lower, flags=re.IGNORECASE):
            return "destructive"

    # Check for dangerous arguments on non-readonly commands
    first_word = cmd_lower.split()[0] if cmd_lower else ""
    is_readonly = first_word.startswith(READONLY_VERBS) or first_word in READONLY_CMDS

    for arg_pattern in DANGEROUS_ARGUMENTS:
        if re.search(arg_pattern, cmd_lower, flags=re.IGNORECASE):
            if not is_readonly:
                return "destructive"

    if is_readonly:
        return "read"

    return "unknown"


def screen_command(command: str) -> tuple[bool, str, str]:
    """Screen command for safety and classify risk level.

    Returns:
        (is_safe, reason, risk_level)
    """
    cmd_lower = command.strip().lower()
    risk = classify_risk(command)

    for pattern in DESTRUCTIVE_COMMANDS:
        match = re.search(pattern, cmd_lower, flags=re.IGNORECASE)
        if match:
            return (
                False,
                f"Potentially destructive command detected: {match.group(0)}",
                "destructive",
            )

    # Inspect dangerous arguments
    for arg_pattern in DANGEROUS_ARGUMENTS:
        match = re.search(arg_pattern, cmd_lower, flags=re.IGNORECASE)
        if match:
            # If dangerous argument is passed to a non-readonly command, block it
            first_word = cmd_lower.split()[0] if cmd_lower else ""
            if not (first_word.startswith(READONLY_VERBS) or first_word in READONLY_CMDS):
                return (
                    False,
                    f"Dangerous argument detected: {match.group(0)}",
                    "destructive",
                )

    if risk == "read":
        return True, "Command appears safe (read-only).", "read"

    return True, "Command risk is unclassified (unknown); exercise caution.", "unknown"