"""Structured audit logging for WinCliAgent."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any, Optional

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
    approval_decision: Optional[str] = None,
) -> dict[str, Any]:
    """Append a structured JSON audit event log entry to logs/agent.log.

    Records risk tier and exact approval decision per tier.
    """
    ensure_log_dir()

    risk_upper = risk.upper()
    action_upper = action.upper()

    if approval_decision is None:
        if risk_upper == "CRITICAL":
            approval_decision = "HARD_BLOCKED"
        elif not approved:
            approval_decision = "REJECTED"
        elif risk_upper == "HIGH":
            approval_decision = "APPROVED_EXPLICIT"
        elif risk_upper == "MEDIUM":
            approval_decision = "APPROVED_CONFIRMATION"
        else:
            approval_decision = "AUTO"

    event = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "user_prompt": user_prompt,
        "generated_command": generated_command,
        "risk": risk_upper,
        "action": action_upper,
        "approved": approved,
        "approval_decision": approval_decision.upper(),
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
