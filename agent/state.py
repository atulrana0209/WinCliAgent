"""Shared state passed between graph nodes."""

from __future__ import annotations

from typing import Optional, TypedDict


class AgentState(TypedDict, total=False):
    """State that flows through the LangGraph pipeline."""

    prompt: str
    command: str
    explanation: str
    is_valid: bool
    validation_reason: str
    is_safe: bool
    safety_reason: str
    risk_level: str  # LOW, MEDIUM, HIGH, CRITICAL
    action: str      # ALLOWED, BLOCKED
    stdout: str
    stderr: str
    exit_code: Optional[int]
    executed: bool
    approved: bool
    dry_run: bool
    explain_mode: bool
    verbose: bool
    semantic_valid: bool
    semantic_reason: str
    retry_count: int
    error_feedback: Optional[str]
    previous_commands: list[str]