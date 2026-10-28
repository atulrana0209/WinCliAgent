"""Deterministic fast-path command templates for standard read-only queries."""

from __future__ import annotations

import re
from typing import Optional

# Words or symbols indicating parameters, filters, specific targets, or complex requirements.
# If ANY of these appear in the prompt, the template matcher MUST refuse to match.
DISQUALIFYING_PATTERNS = [
    # Parameters / filters
    r"\bwhere\s+(?!am\s+i\b)",
    r"\bfilter\b",
    r"\bfind\b",
    r"\bsearch\b",
    r"\bcontain(?:s|ing)?\b",
    r"\blike\b",
    r"\bstarting\b",
    r"\bending\b",
    r"\bonly\b",
    # Specific extensions / formats
    r"\.\w+",
    r"\bpython\b",
    r"\bmarkdown\b",
    r"\btext\b",
    r"\bcsv\b",
    r"\bjson\b",
    r"\bpdf\b",
    # Limits, quantifiers, counts
    r"\btop\b",
    r"\bfirst\b",
    r"\blast\b",
    r"\bcount\b",
    r"\bhow many\b",
    r"\bnumber of\b",
    r"\blimit\b",
    r"\bmax\b",
    r"\bmin\b",
    r"\blargest\b",
    r"\bsmallest\b",
    r"\bbiggest\b",
    r"\bnewest\b",
    r"\boldest\b",
    r"\b\d+\b",  # Any digit/number
    # Size / threshold constraints
    r"\bbytes?\b",
    r"\bkb\b",
    r"\bmb\b",
    r"\bgb\b",
    r"\blarger\b",
    r"\bsmaller\b",
    r"\bmore\b",
    r"\bless\b",
    r"\bgreater\b",
    r"\bexceed\b",
    # Temporal modifiers
    r"\bhours?\b",
    r"\bdays?\b",
    r"\bweeks?\b",
    r"\bmonths?\b",
    r"\byears?\b",
    r"\byesterday\b",
    r"\btomorrow\b",
    r"\bago\b",
    r"\bsince\b",
    # Named paths, specific targets
    r"[/\\]",
    r"\b(?:c|d):",
    r"\bsrc\b",
    r"\blogs?\b",
    r"\btests?\b",
    r"\bdocs?\b",
    r"\beval\b",
    r"\bbuild\b",
    r"\bnamed\b",
    r"\bcalled\b",
    r"\bsvchost\b",
    r"\bchrome\b",
    r"\bnotepad\b",
    r"\badapter\b",
    r"\binterface\b",
    r"\bwi-?fi\b",
    r"\bethernet\b",
    r"\bmac\b",
    r"\bping\b",
    # Actions beyond reading
    r"\bcreate\b",
    r"\bdelete\b",
    r"\bremove\b",
    r"\bkill\b",
    r"\bstop\b",
    r"\bstart\b",
    r"\brestart\b",
    r"\bchange\b",
    r"\bset\b",
    r"\bmake\b",
    r"\bwrite\b",
    r"\bclear\b",
    r"\bformat\b",
    r"\bwipe\b",
    r"\bdownload\b",
    r"\berase\b",
    # Chaining or multi-statement
    r"\band\s+(?!time\b)",
    r"\bthen\b",
    r"\balso\b",
    r"[;&|]",
]

DISQUALIFYING_REGEX = re.compile("|".join(DISQUALIFYING_PATTERNS), re.IGNORECASE)


TEMPLATES: list[dict] = [
    {
        "intent": "current_directory",
        "patterns": [
            r"^(?:what is |get |show |print )?(?:my )?(?:current |working )+(?:directory|dir|path|folder)(?:\s+path)?$",
            r"^(?:what is |get |show )?(?:my )?(?:current )?working directory(?:\s+path)?$",
            r"^pwd$",
            r"^where am i(?: right now)?$",
        ],
        "command": "Get-Location",
        "explanation": "Get current working directory path",
        "risk": "read",
    },
    {
        "intent": "free_disk_space",
        "patterns": [
            r"^(?:show |get |check |display )?(?:free |available )?disk (?:space|usage|space usage)$",
            r"^(?:show |get |check |display )?free disk space on (?:my )?computer$",
            r"^(?:show |get |check |display )?(?:free |available )?drive (?:space|usage|space usage)$",
        ],
        "command": "Get-PSDrive -PSProvider FileSystem",
        "explanation": "Display available file system drive space",
        "risk": "read",
    },
    {
        "intent": "current_user",
        "patterns": [
            r"^whoami$",
            r"^(?:who am i|what is my (?:current )?username|show current user|get current user)$",
        ],
        "command": "whoami",
        "explanation": "Display the current user identity",
        "risk": "read",
    },
    {
        "intent": "hostname",
        "patterns": [
            r"^hostname$",
            r"^(?:get |show |what is )?(?:the |my )?(?:computer |machine )?(?:computer\s*name|machine\s*name|host\s*name)$",
        ],
        "command": "hostname",
        "explanation": "Display local computer network hostname",
        "risk": "read",
    },
    {
        "intent": "datetime",
        "patterns": [
            r"^(?:get |show |what is )?(?:the )?(?:current )?(?:date and time|date|time)$",
            r"^what time is it$",
            r"^what is today'?s date$",
        ],
        "command": "Get-Date",
        "explanation": "Display current system date and time",
        "risk": "read",
    },
    {
        "intent": "running_processes",
        "patterns": [
            r"^(?:get|show|list) (?:all )?(?:running |active )?processes$",
            r"^what processes are running$",
        ],
        "command": "Get-Process",
        "explanation": "List all active processes",
        "risk": "read",
    },
    {
        "intent": "os_version",
        "patterns": [
            r"^(?:get |show |what is )?(?:the |my )?(?:os|operating system) version$",
            r"^(?:show |what is )?(?:the |my )?windows version$",
            r"^(?:show |get )?my computer information$",
        ],
        "command": "Get-ComputerInfo",
        "explanation": "Display operating system and computer configuration",
        "risk": "read",
    },
    {
        "intent": "ip_address",
        "patterns": [
            r"^(?:get |show |what is )?(?:my )?(?:ip address|ip config|ip configuration)$",
        ],
        "command": "Get-NetIPConfiguration",
        "explanation": "Display IP configuration details",
        "risk": "read",
    },
    {
        "intent": "list_files",
        "patterns": [
            r"^(?:list |show )?(?:all )?files(?: in (?:this|the|current|the current) (?:folder|directory))?$",
            r"^(?:list |show )?(?:all )?contents of (?:this|the|current|the current) (?:folder|directory)$",
            r"^dir$",
            r"^ls$",
        ],
        "command": "Get-ChildItem",
        "explanation": "List files and directories in current location",
        "risk": "read",
    },
]


def match_template(prompt: str) -> Optional[tuple[str, str, str]]:
    """Match a natural language prompt against conservative deterministic templates.

    Returns:
        (command, explanation, risk) if matched, else None.
    """
    cleaned = prompt.strip().lower()
    cleaned = re.sub(r"[?!.]+$", "", cleaned).strip()

    if not cleaned:
        return None

    # Conservative disqualification check:
    # If the prompt contains any filtering, specific paths, targets, limits, or modifiers,
    # reject template matching immediately to avoid false positives.
    if DISQUALIFYING_REGEX.search(cleaned):
        return None

    for entry in TEMPLATES:
        for pat in entry["patterns"]:
            if re.match(pat, cleaned, re.IGNORECASE):
                return (entry["command"], entry["explanation"], entry["risk"])

    return None
