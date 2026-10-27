"""Safety screening, 4-tier risk assessment, and deterministic rule-based analysis for PowerShell commands."""

from __future__ import annotations

import re
from typing import Optional

from .normalizer import (
    extract_all_command_segments,
    normalize_command,
    resolve_segment_alias,
)

# Tier ordering for max() comparison
TIER_RANK: dict[str, int] = {
    "LOW": 1,
    "MEDIUM": 2,
    "HIGH": 3,
    "CRITICAL": 4,
}

RANK_TO_TIER: dict[int, str] = {
    1: "LOW",
    2: "MEDIUM",
    3: "HIGH",
    4: "CRITICAL",
}

LLM_TIER_MAP: dict[str, str] = {
    "read": "LOW",
    "low": "LOW",
    "modifying": "MEDIUM",
    "modify": "MEDIUM",
    "medium": "MEDIUM",
    "destructive": "HIGH",
    "destroy": "HIGH",
    "high": "HIGH",
    "critical": "CRITICAL",
}

CRITICAL_PATTERNS = [
    r"\bformat\b",
    r"\bformat-volume\b",
    r"\bclear-disk\b",
    r"\bremove-partition\b",
    r"\bdiskpart\b",
    r"\bcipher\b\s+/w",
    r"\bvssadmin\b\s+delete",
    r"\bbcdedit\b",
    r"\bwbadmin\b\s+delete",
    # Recursive force deletion targeting root, drive root, or wildcard
    r"\bremove-item\b.*-recurse.*-force",
    r"\bremove-item\b.*-force.*-recurse",
    r"\bremove-item\b.*\*",
    r"\bdel\b\s+/[sqf]",
    r"\brmdir\b\s+/s",
    # Deletion targeting sensitive system directories or root drives
    r"\bremove-item\b.*\b(c:\\|c:/|[a-z]:\\|[a-z]:/|/|\\)\b",
    r"(\bremove-item\b|\bdel\b|\brmdir\b|\brm\b|\bri\b|\brd\b).*(\bc:\\windows\b|\bc:\\windows\\system32\b|\$env:(windir|systemroot)\b|%windir%|%systemroot%)",
    # Critical registry wipe
    r"\breg\b\s+delete\s+(hklm|hkcu)\b",
    r"\bremove-item\b\s+.*(hklm|hkcu):",
    # Raw physical drive access
    r"\\\\\\\\\.\\\\physicaldrive",
]

HIGH_PATTERNS = [
    # Deletion cmdlets and aliases
    r"\bremove-item\b",
    r"\bdel\b",
    r"\brm\b",
    r"\bri\b",
    r"\brd\b",
    r"\berase\b",
    r"\brmdir\b",
    r"\bclear-content\b",
    r"\bclc\b",
    # Process and service termination
    r"\bstop-process\b",
    r"\bkill\b",
    r"\bspps\b",
    r"\bstop-service\b",
    # System state change
    r"\brestart-computer\b",
    r"\bstop-computer\b",
    r"\bshutdown\b",
    # Dynamic execution & code injection
    r"\binvoke-expression\b",
    r"\biex\b",
    r"\[scriptblock\]::create",
    r"\binvoke-command\b",
    r"\bicm\b",
    # Encoded commands
    r"\b(powershell|pwsh)\b.*(-e|-enc|-encodedcommand)\b",
    # Download cradles & remote execution
    r"(\.downloadstring|\.downloadfile)\b",
    r"\b(invoke-webrequest|iwr|curl|wget|invoke-restmethod|irm)\b.*\|\s*(invoke-expression|iex|cmd|pwsh|powershell|bash|sh)",
    r"\bstart-bitstransfer\b",
    r"\bcertutil\b.*-urlcache",
    r"\bmshta\b",
    # Path traversal & targeting system directories
    r"\.\.[\\/]\.\.[\\/]",
    r"(\bc:\\windows\b|\bc:\\windows\\system32\b|\$env:(windir|systemroot)\b|%windir%|%systemroot%)",
]

MEDIUM_PATTERNS = [
    r"\bstart-process\b",
    r"\bset-location\b",
    r"\bcd\b",
    r"\bchdir\b",
    r"\bset-service\b",
    r"\bnew-item\b",
    r"\bni\b",
    r"\bmove-item\b",
    r"\bmove\b",
    r"\bmv\b",
    r"\bmi\b",
    r"\brename-item\b",
    r"\bren\b",
    r"\brni\b",
    r"\bcopy-item\b",
    r"\bcopy\b",
    r"\bcp\b",
    r"\bcpi\b",
    r"\bset-content\b",
    r"\bsc\b",
    r"\badd-content\b",
    r"\bac\b",
    r"\bset-itemproperty\b",
    r"\bnew-itemproperty\b",
    r"\bremove-itemproperty\b",
    r"\bset-executionpolicy\b",
    r"\bset-netipaddress\b",
]

DANGEROUS_ARGUMENTS = [
    r"-force\b",
    r"-recurse\b",
    r"/[sqf]\b",
    r"-confirm:\$false\b",
]

# Strict Allowlist: A command can be LOW / auto-run only if EVERY segment is on this allowlist
STRICT_ALLOWLIST_CMDS = {
    "get-childitem",
    "get-process",
    "get-service",
    "get-netipconfiguration",
    "get-netipaddress",
    "get-netadapter",
    "get-computerinfo",
    "get-date",
    "get-location",
    "get-content",
    "get-psdrive",
    "get-volume",
    "get-disk",
    "get-command",
    "get-help",
    "get-alias",
    "get-clipboard",
    "select-object",
    "where-object",
    "sort-object",
    "measure-object",
    "format-table",
    "format-list",
    "out-string",
    "write-output",
    "write-host",
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
    "gci",
    "gps",
    "ps",
    "gsv",
    "cat",
}

READONLY_VERBS = (
    "get-",
    "show-",
    "measure-",
    "test-",
    "select-",
    "where-",
    "export-",
    "format-",
    "out-",
)


def is_segment_on_allowlist(segment: str) -> bool:
    """Check if an individual segment is strictly on the read-only allowlist."""
    seg_clean = resolve_segment_alias(segment).strip().lower()
    if not seg_clean:
        return True

    # Check for dangerous arguments or redirection in read segment
    if any(re.search(p, seg_clean, flags=re.IGNORECASE) for p in DANGEROUS_ARGUMENTS):
        return False
    if ">" in seg_clean or ">>" in seg_clean:
        return False

    first_word = seg_clean.split()[0].strip("()`{}[]")
    if first_word in STRICT_ALLOWLIST_CMDS:
        return True

    if first_word.startswith(READONLY_VERBS):
        return True

    # Property predicates in filters/scriptblocks (e.g. $_.CPU -gt 10, $_.Length)
    if first_word.startswith("$_") or first_word.startswith("$psitem"):
        if not re.search(r"\b(rm|del|remove|stop|set|format)\b", seg_clean, flags=re.IGNORECASE) and "=" not in seg_clean:
            return True

    return False


def analyze_segment_risk(segment: str) -> tuple[str, str]:
    """Classify the risk tier of a single command segment.
    
    Returns:
        (tier: str, reason: str)
    """
    normalized_seg = resolve_segment_alias(segment).strip()
    cmd_lower = normalized_seg.lower()

    if not cmd_lower:
        return "LOW", "Empty segment"

    # 1. Check CRITICAL
    for pattern in CRITICAL_PATTERNS:
        if re.search(pattern, cmd_lower, flags=re.IGNORECASE):
            return "CRITICAL", f"Critical destructive system pattern detected: {pattern}"

    # 2. Check HIGH patterns
    for pattern in HIGH_PATTERNS:
        if re.search(pattern, cmd_lower, flags=re.IGNORECASE):
            return "HIGH", f"High-risk operation or execution pattern detected: {pattern}"

    # 3. Check dangerous arguments on non-readonly commands
    first_word = cmd_lower.split()[0].strip("()`{}[]")
    is_readonly = first_word in STRICT_ALLOWLIST_CMDS or first_word.startswith(READONLY_VERBS)

    if not is_readonly:
        for arg_pattern in DANGEROUS_ARGUMENTS:
            if re.search(arg_pattern, cmd_lower, flags=re.IGNORECASE):
                return "HIGH", f"Dangerous modification arguments detected: {arg_pattern}"

    # 4. Check MEDIUM patterns
    for pattern in MEDIUM_PATTERNS:
        if re.search(pattern, cmd_lower, flags=re.IGNORECASE):
            return "MEDIUM", f"Medium-risk state-changing command: {pattern}"

    # 5. Check Allowlist for LOW
    if is_segment_on_allowlist(segment):
        return "LOW", "Allowlisted read-only command"

    # Default unknown commands to MEDIUM
    return "MEDIUM", "Unknown or unclassified command"


def classify_rule_tier_all_segments(command: str) -> tuple[str, str, bool]:
    """Tokenize and evaluate rule risk tier across ALL command segments and subexpressions.
    
    Returns:
        (max_tier: str, primary_reason: str, is_all_allowlisted: bool)
    """
    segments = extract_all_command_segments(command)
    if not segments:
        return "LOW", "Empty command", True

    max_rank = 1
    primary_reason = "Allowlisted read-only command"
    all_allowlisted = True

    for seg in segments:
        tier, reason = analyze_segment_risk(seg)
        rank = TIER_RANK.get(tier, 1)

        if not is_segment_on_allowlist(seg):
            all_allowlisted = False

        if rank > max_rank:
            max_rank = rank
            primary_reason = f"Segment '{seg}': {reason}"

    max_tier = RANK_TO_TIER[max_rank]
    # To be LOW, every segment must be on allowlist
    if max_tier == "LOW" and not all_allowlisted:
        max_tier = "MEDIUM"
        primary_reason = "Contains segments not on the strict read-only allowlist"

    return max_tier, primary_reason, all_allowlisted


def combine_risk_tiers(rule_tier: str, llm_risk: Optional[str] = None) -> str:
    """Enforce: final tier = max(rule_tier, llm_tier).
    
    The LLM must NEVER be able to downgrade a rule-based safety classification.
    """
    rule_rank = TIER_RANK.get(rule_tier.upper(), 1)

    llm_rank = 1
    if llm_risk:
        mapped_llm_tier = LLM_TIER_MAP.get(llm_risk.strip().lower(), "LOW")
        llm_rank = TIER_RANK.get(mapped_llm_tier, 1)

    final_rank = max(rule_rank, llm_rank)
    return RANK_TO_TIER[final_rank]


def classify_risk_tier(command: str, llm_risk: Optional[str] = None) -> tuple[str, str]:
    """Classify command into risk tier ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL') and action.
    
    Action semantics:
    - CRITICAL: BLOCKED (hard block, no override)
    - HIGH: REQUIRES_CONFIRMATION (explicit typed confirmation required)
    - MEDIUM: ALLOWED (standard confirmation)
    - LOW: ALLOWED (auto-run allowed if allowlisted)
    """
    rule_tier, _reason, _allowlisted = classify_rule_tier_all_segments(command)
    final_tier = combine_risk_tiers(rule_tier, llm_risk)

    if final_tier == "CRITICAL":
        return final_tier, "BLOCKED"
    if final_tier == "HIGH":
        return final_tier, "REQUIRES_CONFIRMATION"

    return final_tier, "ALLOWED"


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


def screen_command_risk(
    command: str, llm_risk: Optional[str] = None
) -> tuple[bool, str, str, str]:
    """Screen command for safety and classify into 4-tier risk level.

    Returns:
        (is_safe: bool, reason: str, risk_level: str, action: str)
    """
    rule_tier, reason, _allowlisted = classify_rule_tier_all_segments(command)
    final_tier = combine_risk_tiers(rule_tier, llm_risk)

    if final_tier == "CRITICAL":
        return False, f"Critical risk system/destructive operation: {reason}", final_tier, "BLOCKED"

    if final_tier == "HIGH":
        return False, f"High risk potentially destructive command: {reason}", final_tier, "REQUIRES_CONFIRMATION"

    if final_tier == "MEDIUM":
        return True, f"Medium risk modification operation: {reason}", final_tier, "ALLOWED"

    return True, f"Low risk read-only command: {reason}", final_tier, "ALLOWED"
