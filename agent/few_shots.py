"""Compact, non-contaminating few-shot examples for Windows PowerShell command generation.

Demonstrates general transferable habits NOT represented in evaluation tasks:
- Registry reading (Get-ItemProperty)
- Environment variable inspection (Get-ChildItem Env:)
- Cryptographic hash computation (Get-FileHash)
- Hotfix / patch inspection (Get-HotFix)
- Event log querying (Get-WinEvent)
"""

from __future__ import annotations

# 5 compact, general few-shot examples
FEW_SHOT_EXAMPLES: list[dict[str, str]] = [
    {
        "prompt": "inspect system environment variables",
        "command": "Get-ChildItem -Path Env: | Sort-Object Name",
        "explanation": "List all environment variables sorted alphabetically",
        "risk": "read",
    },
    {
        "prompt": "compute sha256 checksum of document.pdf",
        "command": "Get-FileHash -Path document.pdf -Algorithm SHA256",
        "explanation": "Calculate SHA256 cryptographic hash of a target file",
        "risk": "read",
    },
    {
        "prompt": "list recently installed windows update hotfixes",
        "command": "Get-HotFix | Sort-Object InstalledOn -Descending | Select-Object -First 10",
        "explanation": "Display the 10 most recent Windows update packages",
        "risk": "read",
    },
    {
        "prompt": "retrieve registered powershell execution policy registry value",
        "command": "Get-ItemProperty -Path 'HKLM:\\Software\\Microsoft\\PowerShell\\1\\ShellIds\\Microsoft.PowerShell' -Name ExecutionPolicy",
        "explanation": "Read execution policy configuration directly from registry",
        "risk": "read",
    },
    {
        "prompt": "query recent system error events from the event log",
        "command": "Get-WinEvent -FilterHashtable @{LogName='System'; Level=2} -MaxEvents 5",
        "explanation": "Retrieve the 5 most recent Error-level entries from the System log",
        "risk": "read",
    },
]
