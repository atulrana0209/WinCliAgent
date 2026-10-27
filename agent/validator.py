"""Validation for generated PowerShell commands."""

from __future__ import annotations

import re

from .safety import classify_risk

KNOWN_COMMANDS: dict[str, list[str]] = {
    "ip configuration": ["Get-NetIPConfiguration", "ipconfig"],
    "ip config": ["Get-NetIPConfiguration", "ipconfig"],
    "ip address": ["Get-NetIPAddress", "Get-NetIPConfiguration", "ipconfig"],
    "mac address": ["Get-NetAdapter", "getmac"],
    "processes": ["Get-Process", "tasklist"],
    "services": ["Get-Service"],
    "current directory": ["Get-Location", "pwd", "Get-ChildItem", "dir", "ls"],
    "list files": ["Get-ChildItem", "dir", "ls"],
    "computer information": ["Get-ComputerInfo", "systeminfo"],
    "system info": ["Get-ComputerInfo", "systeminfo"],
    "date": ["Get-Date"],
    "time": ["Get-Date"],
    "disk usage": ["Get-Volume", "Get-Disk", "Get-PSDrive", "wmic logicaldisk"],
    "windows version": ["Get-ComputerInfo", "systeminfo", "winver"],
    "installed applications": ["Get-Package", "winget", "Get-WmiObject"],
}


def validate_command(command: str, prompt: str) -> tuple[bool, str]:
    """Check whether a generated command actually matches the user's request.

    Returns:
        (is_valid: bool, reason: str)
    """
    command_lower = command.lower().strip()
    prompt_lower = prompt.lower().strip()

    if not command_lower:
        return False, "Generated command is empty."

    # Property check: flag known invalid property extractions on Get-NetAdapter
    if "get-netadapter" in command_lower and "ipaddress" in command_lower:
        return (
            False,
            "Get-NetAdapter does not contain an IpAddress property. Use Get-NetIPConfiguration instead.",
        )

    # Check high-confidence mappings
    for phrase, expected_cmds in KNOWN_COMMANDS.items():
        pattern = rf"\b{re.escape(phrase)}\b"
        if re.search(pattern, prompt_lower):
            # Skip list files rule if prompt is a deletion request
            if phrase in ["current directory", "list files"] and any(
                re.search(rf"\b{w}\b", prompt_lower) for w in ["delete", "remove", "erase", "clean", "rm", "del"]
            ):
                continue

            if not any(expected.lower() in command_lower for expected in expected_cmds):
                return (
                    False,
                    f"The generated command does not match expected cmdlets ({', '.join(expected_cmds)}) for '{phrase}'.",
                )

    # General validation for unknown requests
    risk = classify_risk(command)
    is_info_request = any(
        w in prompt_lower for w in ["show", "get", "display", "list", "what", "find", "check"]
    )
    if is_info_request and risk == "destructive":
        return (
            False,
            "The generated command performs a destructive action for an informational request.",
        )

    return True, "Command passed semantic validation."