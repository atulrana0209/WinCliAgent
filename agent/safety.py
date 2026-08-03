"""Safety screening and 4-tier risk assessment for PowerShell commands."""

from __future__ import annotations

import re
from .normalizer import normalize_command, parse_command_structure

CRITICAL_PATTERNS = [
    r"\bformat\b",
    r"\bformat-volume\b",
    r"\bclear-disk\b",
    r"\bremove-partition\b",
    r"\bdiskpart\b",
    r"\bcipher\b\s+/w",
    r"\breg\b\s+delete",
    r"\bvssadmin\b\s+delete",
    r"\bbcdedit\b",
    r"\bremove-item\b.*-recurse.*-force",
    r"\bremove-item\b.*-force.*-recurse",
    r"\bremove-item\b.*\*",
    r"\bdel\b\s+/[sqf]",
    r"\brmdir\b\s+/s",
]

HIGH_PATTERNS = [
    r"\bremove-item\b",
    r"\bstop-process\b",
    r"\bstop-service\b",
    r"\brestart-computer\b",
    r"\bstop-computer\b",
    r"\bshutdown\b",
    r"\bclear-content\b",
    r"\bdel\b",
    r"\berase\b",
    r"\brmdir\b",
    r"\brd\b",
]

MEDIUM_PATTERNS = [
    r"\bstart-process\b",
    r"\bset-location\b",
    r"\bset-service\b",
    r"\bnew-item\b",
    r"\bmove-item\b",
    r"\brename-item\b",
    r"\bcopy-item\b",
    r"\bset-executionpolicy\b",
    r"\bset-netipaddress\b",
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
    "get-childitem",
    "get-process",
    "get-service",
    "get-netipconfiguration",
    "get-computerinfo",
    "get-date",
    "get-location",
    "get-content",
    "get-netadapter",
    "ipconfig",
    "systeminfo",
    "whoami",
    "hostname",
    "ping",
    "tracert",
    "echo",
    "type",
    "pwd",
    "dir",
    "ls",
}


def classify_risk_tier(command: str) -> tuple[str, str]:
    """Classify command into risk tier ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL') and action ('ALLOWED', 'BLOCKED')."""
    normalized = normalize_command(command)
    cmd_lower = normalized.strip().lower()

    # Check CRITICAL
    for pattern in CRITICAL_PATTERNS:
        if re.search(pattern, cmd_lower, flags=re.IGNORECASE):
            return "CRITICAL", "BLOCKED"

    # Check HIGH
    for pattern in HIGH_PATTERNS:
        if re.search(pattern, cmd_lower, flags=re.IGNORECASE):
            return "HIGH", "BLOCKED"

    # Check dangerous arguments on non-readonly commands
    parsed = parse_command_structure(command)
    first_cmdlet = parsed.cmdlets[0].lower() if parsed.cmdlets else ""
    is_readonly = first_cmdlet.startswith(READONLY_VERBS) or first_cmdlet in READONLY_CMDS

    if not is_readonly:
        for arg_pattern in DANGEROUS_ARGUMENTS:
            if re.search(arg_pattern, cmd_lower, flags=re.IGNORECASE):
                return "HIGH", "BLOCKED"

    # Check MEDIUM
    for pattern in MEDIUM_PATTERNS:
        if re.search(pattern, cmd_lower, flags=re.IGNORECASE):
            return "MEDIUM", "ALLOWED"

    # Check LOW
    if is_readonly:
        return "LOW", "ALLOWED"

    return "MEDIUM", "ALLOWED"


def classify_risk(command: str) -> str:
    """Backward compatible risk level function returning 'destructive', 'read', or 'unknown'."""
    tier, _action = classify_risk_tier(command)
    if tier in ("HIGH", "CRITICAL"):
        return "destructive"
    if tier == "LOW":
        return "read"
    return "unknown"


def screen_command(command: str) -> tuple[bool, str, str]:
    """Backward compatible screening function.

    Returns:
        (is_safe: bool, reason: str, risk_level: str)
    """
    is_safe, reason, risk_level, _action = screen_command_risk(command)
    if risk_level in ("HIGH", "CRITICAL"):
        return is_safe, reason, "destructive"
    if risk_level == "LOW":
        return is_safe, reason, "read"
    return is_safe, reason, "unknown"


def screen_command_risk(command: str) -> tuple[bool, str, str, str]:
    """Screen command for safety and classify into 4-tier risk level.

    Returns:
        (is_safe: bool, reason: str, risk_level: str, action: str)
    """
    normalized = normalize_command(command)
    risk_level, action = classify_risk_tier(normalized)
    is_safe = (action == "ALLOWED")

    if risk_level == "CRITICAL":
        return False, f"Critical risk system/destructive operation: {normalized}", risk_level, action

    if risk_level == "HIGH":
        return False, f"High risk potentially destructive command: {normalized}", risk_level, action

    if risk_level == "MEDIUM":
        return True, f"Medium risk modification operation: {normalized}", risk_level, action

    return True, f"Low risk read-only command: {normalized}", risk_level, action