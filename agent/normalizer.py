"""Command alias normalization and structural parsing for PowerShell commands."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

POWERSHELL_ALIASES: dict[str, str] = {
    "gci": "Get-ChildItem",
    "dir": "Get-ChildItem",
    "ls": "Get-ChildItem",
    "gps": "Get-Process",
    "ps": "Get-Process",
    "gsv": "Get-Service",
    "gal": "Get-Alias",
    "gcb": "Get-Clipboard",
    "rm": "Remove-Item",
    "del": "Remove-Item",
    "erase": "Remove-Item",
    "rd": "Remove-Item",
    "rmdir": "Remove-Item",
    "cd": "Set-Location",
    "chdir": "Set-Location",
    "pwd": "Get-Location",
    "ren": "Rename-Item",
    "copy": "Copy-Item",
    "cp": "Copy-Item",
    "move": "Move-Item",
    "mv": "Move-Item",
    "cat": "Get-Content",
    "type": "Get-Content",
    "cls": "Clear-Host",
    "clear": "Clear-Host",
}


@dataclass
class ParsedCommandStructure:
    raw_command: str
    normalized_command: str
    cmdlets: list[str] = field(default_factory=list)
    parameters: list[str] = field(default_factory=list)
    has_pipeline: bool = False


def normalize_command(command: str) -> str:
    """Normalize PowerShell aliases to canonical cmdlet names.

    Example:
        gci -Path . -> Get-ChildItem -Path .
        dir | Where-Object ... -> Get-ChildItem | Where-Object ...
    """
    if not command or not command.strip():
        return ""

    pipeline_segments = command.split("|")
    normalized_segments = []

    for segment in pipeline_segments:
        segment_str = segment.strip()
        if not segment_str:
            continue

        tokens = segment_str.split(maxsplit=1)
        first_token = tokens[0]
        remainder = tokens[1] if len(tokens) > 1 else ""

        canonical = POWERSHELL_ALIASES.get(first_token.lower(), first_token)

        if remainder:
            normalized_segments.append(f"{canonical} {remainder}")
        else:
            normalized_segments.append(canonical)

    return " | ".join(normalized_segments)


def parse_command_structure(command: str) -> ParsedCommandStructure:
    """Structurally inspect PowerShell command pipeline, cmdlets, and parameters."""
    normalized = normalize_command(command)
    segments = [s.strip() for s in normalized.split("|") if s.strip()]

    cmdlets = []
    parameters = []

    for segment in segments:
        words = segment.split()
        if words:
            cmdlets.append(words[0])
            for word in words[1:]:
                if word.startswith("-") or word.startswith("/"):
                    parameters.append(word)

    return ParsedCommandStructure(
        raw_command=command,
        normalized_command=normalized,
        cmdlets=cmdlets,
        parameters=parameters,
        has_pipeline=len(segments) > 1,
    )
