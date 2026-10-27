"""Command alias normalization, quote-aware tokenization, and structural parsing for PowerShell commands."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

POWERSHELL_ALIASES: dict[str, str] = {
    # Discovery & Read-only
    "gci": "Get-ChildItem",
    "dir": "Get-ChildItem",
    "ls": "Get-ChildItem",
    "gps": "Get-Process",
    "ps": "Get-Process",
    "gsv": "Get-Service",
    "gal": "Get-Alias",
    "gcb": "Get-Clipboard",
    "cat": "Get-Content",
    "type": "Get-Content",
    "gc": "Get-Content",
    "pwd": "Get-Location",
    "select": "Select-Object",
    "where": "Where-Object",
    "?": "Where-Object",
    "%": "ForEach-Object",
    "foreach": "ForEach-Object",
    "sort": "Sort-Object",
    "measure": "Measure-Object",
    "ft": "Format-Table",
    "fl": "Format-List",
    # Deletion & Destructive (CRITICAL / HIGH)
    "rm": "Remove-Item",
    "del": "Remove-Item",
    "erase": "Remove-Item",
    "rd": "Remove-Item",
    "rmdir": "Remove-Item",
    "ri": "Remove-Item",
    "kill": "Stop-Process",
    "spps": "Stop-Process",
    "clc": "Clear-Content",
    # Execution & Injection (HIGH)
    "iex": "Invoke-Expression",
    "icm": "Invoke-Command",
    "iwr": "Invoke-WebRequest",
    "irm": "Invoke-RestMethod",
    "curl": "Invoke-WebRequest",
    "wget": "Invoke-WebRequest",
    # State-Changing & Creation (MEDIUM)
    "cd": "Set-Location",
    "chdir": "Set-Location",
    "ren": "Rename-Item",
    "rni": "Rename-Item",
    "copy": "Copy-Item",
    "cp": "Copy-Item",
    "cpi": "Copy-Item",
    "move": "Move-Item",
    "mv": "Move-Item",
    "mi": "Move-Item",
    "ni": "New-Item",
    "sc": "Set-Content",
    "ac": "Add-Content",
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


def deobfuscate_powershell_tokens(command: str) -> str:
    """Remove inline backtick obfuscation from PowerShell tokens/cmdlets.
    
    Preserves PowerShell escape sequences (`n, `t, `r, `a, `0, `b, `f, `v) inside strings.
    Strips obfuscation backticks inside identifiers and unquoted words.
    """
    if not command or "`" not in command:
        return command

    result: list[str] = []
    in_single_quote = False
    in_double_quote = False
    i = 0
    n = len(command)

    while i < n:
        ch = command[i]

        if ch == "'" and not in_double_quote:
            in_single_quote = not in_single_quote
            result.append(ch)
            i += 1
            continue

        if ch == '"' and not in_single_quote:
            if i > 0 and command[i - 1] == "`" and in_double_quote:
                result.append(ch)
                i += 1
                continue
            in_double_quote = not in_double_quote
            result.append(ch)
            i += 1
            continue

        if ch == "`":
            if i + 1 < n:
                next_char = command[i + 1]
                # Inside double quotes: preserve recognized escape sequences
                if in_double_quote and next_char.lower() in ("0", "a", "b", "e", "f", "n", "r", "t", "v", '"', "$", "`"):
                    result.append(ch)
                    i += 1
                    continue
                # Outside quotes: if followed by word character, it is token obfuscation
                if not in_single_quote and not in_double_quote and re.match(r"[a-zA-Z0-9_\-]", next_char):
                    i += 1
                    continue
                # Inside quotes: if followed by ordinary character, strip backtick
                if in_double_quote and re.match(r"[a-zA-Z0-9_\-]", next_char) and next_char.lower() not in ("0", "a", "b", "e", "f", "n", "r", "t", "v"):
                    i += 1
                    continue

        result.append(ch)
        i += 1

    return "".join(result)


def extract_all_command_segments(command: str) -> list[str]:
    """Tokenize a PowerShell command string into discrete command segments.
    
    Quote-aware:
    - Semicolons (;), pipelines (|), and operators (&&, ||) inside quotes do NOT split.
    - Subexpressions $(...) and scriptblocks {...} are extracted as nested command segments.
    - Handles backtick command substitution and deobfuscation.
    """
    if not command or not command.strip():
        return []

    cleaned = deobfuscate_powershell_tokens(command.strip())

    segments: list[str] = []
    nested_segments: list[str] = []

    current_token: list[str] = []
    in_single_quote = False
    in_double_quote = False
    i = 0
    n = len(cleaned)

    # Subexpression tracking
    subexpr_start_stack: list[int] = []

    while i < n:
        ch = cleaned[i]

        # 1. Single quotes '...'
        if ch == "'" and not in_double_quote:
            # Check for escaped single quote ''
            if in_single_quote and i + 1 < n and cleaned[i + 1] == "'":
                current_token.append("''")
                i += 2
                continue
            in_single_quote = not in_single_quote
            current_token.append(ch)
            i += 1
            continue

        # 2. Double quotes "..."
        if ch == '"' and not in_single_quote:
            # Check for escaped double quote `"
            if i > 0 and cleaned[i - 1] == "`":
                current_token.append(ch)
                i += 1
                continue
            # Check for escaped double quote ""
            if in_double_quote and i + 1 < n and cleaned[i + 1] == '"':
                current_token.append('""')
                i += 2
                continue
            in_double_quote = not in_double_quote
            current_token.append(ch)
            i += 1
            continue

        # 3. Detect subexpressions $(...) - valid outside quotes AND inside double quotes
        if ch == "$" and i + 1 < n and cleaned[i + 1] == "(" and not in_single_quote:
            subexpr_start_stack.append(len(current_token) + 2)
            current_token.append("$(")
            i += 2
            continue

        if ch == ")" and subexpr_start_stack and not in_single_quote:
            start_pos = subexpr_start_stack.pop()
            # Extract the inner subexpression text
            sub_content = "".join(current_token[start_pos:])
            if sub_content.strip():
                nested_segments.append(sub_content.strip())
            current_token.append(")")
            i += 1
            continue

        # 4. Detect unix-style backtick substitution `command` outside quotes
        if ch == "`" and not in_single_quote and not in_double_quote:
            # Check if there is another backtick later
            closing_bt = cleaned.find("`", i + 1)
            if closing_bt != -1 and closing_bt - i > 1:
                inner_bt = cleaned[i + 1:closing_bt].strip()
                if inner_bt and not re.match(r"^[0abefnrtv]$", inner_bt):
                    nested_segments.append(inner_bt)
                    current_token.append(cleaned[i:closing_bt + 1])
                    i = closing_bt + 1
                    continue

        # 5. Outside any quotes: detect delimiters (; , \n , && , || , |)
        if not in_single_quote and not in_double_quote:
            # Check && or ||
            if i + 1 < n and cleaned[i:i + 2] in ("&&", "||"):
                seg = "".join(current_token).strip()
                if seg:
                    segments.append(seg)
                current_token = []
                i += 2
                continue

            # Check ; or \n
            if ch in (";", "\n"):
                seg = "".join(current_token).strip()
                if seg:
                    segments.append(seg)
                current_token = []
                i += 1
                continue

            # Check pipeline | (ensure not part of ||)
            if ch == "|" and (i + 1 >= n or cleaned[i + 1] != "|") and (i == 0 or cleaned[i - 1] != "|"):
                seg = "".join(current_token).strip()
                if seg:
                    segments.append(seg)
                current_token = []
                i += 1
                continue

            # Check scriptblock { ... }
            if ch == "{" and (i == 0 or cleaned[i - 1] != "$"):
                # Find matching brace
                brace_depth = 1
                j = i + 1
                while j < n and brace_depth > 0:
                    if cleaned[j] == "{":
                        brace_depth += 1
                    elif cleaned[j] == "}":
                        brace_depth -= 1
                    j += 1
                inner_block = cleaned[i + 1:j - 1].strip()
                if inner_block:
                    nested_segments.append(inner_block)

        current_token.append(ch)
        i += 1

    last_seg = "".join(current_token).strip()
    if last_seg:
        segments.append(last_seg)

    # Recursively process nested segments to extract any chained commands inside them
    all_segments: list[str] = []
    for s in segments:
        if s:
            all_segments.append(s)

    for ns in nested_segments:
        all_segments.extend(extract_all_command_segments(ns))

    return all_segments


def resolve_segment_alias(segment: str) -> str:
    """Normalize the leading cmdlet alias in a single command segment."""
    seg_clean = segment.strip()
    if not seg_clean:
        return ""

    tokens = seg_clean.split(maxsplit=1)
    first_token = deobfuscate_powershell_tokens(tokens[0])
    remainder = tokens[1] if len(tokens) > 1 else ""

    canonical = POWERSHELL_ALIASES.get(first_token.lower(), first_token)
    if remainder:
        return f"{canonical} {remainder}"
    return canonical


def normalize_command(command: str) -> str:
    """Normalize PowerShell aliases to canonical cmdlet names across all segments.
    
    Quote-aware: leaves quoted strings intact while normalizing commands in pipelines
    and statement chains.
    """
    if not command or not command.strip():
        return ""

    deobfuscated = deobfuscate_powershell_tokens(command.strip())

    # Split top-level statement delimiters while preserving quote boundaries
    parts: list[str] = []
    current: list[str] = []
    in_sq = False
    in_dq = False
    i = 0
    n = len(deobfuscated)

    while i < n:
        ch = deobfuscated[i]
        if ch == "'" and not in_dq:
            in_sq = not in_sq
            current.append(ch)
            i += 1
            continue
        if ch == '"' and not in_sq:
            in_dq = not in_dq
            current.append(ch)
            i += 1
            continue

        if not in_sq and not in_dq:
            if i + 1 < n and deobfuscated[i:i + 2] in ("&&", "||"):
                op = deobfuscated[i:i + 2]
                seg = "".join(current).strip()
                if seg:
                    parts.append(resolve_segment_alias(seg))
                parts.append(op)
                current = []
                i += 2
                continue
            if ch in (";", "|"):
                seg = "".join(current).strip()
                if seg:
                    parts.append(resolve_segment_alias(seg))
                parts.append(ch)
                current = []
                i += 1
                continue

        current.append(ch)
        i += 1

    last = "".join(current).strip()
    if last:
        parts.append(resolve_segment_alias(last))

    # Reconstruct normalized command with standard spacing around operators
    res = []
    for p in parts:
        if p in (";", "|", "&&", "||"):
            if res and not res[-1].endswith(" "):
                res.append(f" {p} ")
            else:
                res.append(f"{p} ")
        else:
            res.append(p)

    reconstructed = "".join(res).strip()
    # Clean up double spaces
    return re.sub(r" +", " ", reconstructed)


def parse_command_structure(command: str) -> ParsedCommandStructure:
    """Structurally inspect PowerShell command pipeline, cmdlets, and parameters."""
    normalized = normalize_command(command)
    segments = extract_all_command_segments(normalized)

    cmdlets = []
    parameters = []

    for segment in segments:
        words = segment.split()
        if words:
            cmdlet = words[0].strip("()`{}[]")
            if cmdlet:
                cmdlets.append(cmdlet)
            for word in words[1:]:
                if word.startswith("-") or word.startswith("/"):
                    parameters.append(word)

    return ParsedCommandStructure(
        raw_command=command,
        normalized_command=normalized,
        cmdlets=cmdlets,
        parameters=parameters,
        has_pipeline="|" in command,
    )
