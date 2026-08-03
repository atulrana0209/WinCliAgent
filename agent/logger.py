"""Structured audit logging for WinCliAgent."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any

LOG_DIR = "logs"
LOG_FILE = os.path.join(LOG_DIR, "agent.log")


def ensure_log_dir() -> None:
    """Ensure the logs directory exists."""
    if not os.path.exists(LOG_DIR):
        os.makedirs(LOG_DIR, exist_ok=True)


def log_audit_event(
    user_prompt: str,
    generated_command: str,
    risk: str,
    action: str,
    approved: bool,
    exit_code: int | None,
    validation: str,
    retry_count: int = 0,
) -> dict[str, Any]:
    """Append a structured JSON audit event log entry to logs/agent.log.

    Returns:
        The logged event dictionary.
    """
    ensure_log_dir()

    event = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "user_prompt": user_prompt,
        "generated_command": generated_command,
        "risk": risk.upper(),
        "action": action.upper(),
        "approved": approved,
        "exit_code": exit_code,
        "validation": validation.upper(),
        "retry_count": retry_count,
    }

    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(event) + "\n")
    except Exception as exc:
        print(f"Warning: Failed to write audit log entry: {exc}")

    return event
