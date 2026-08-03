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
    stdout: str
    stderr: str
    exit_code: Optional[int]
    executed: bool
    semantic_valid: bool
    semantic_reason: str
    retry_count: int
    error_feedback: Optional[str]
    previous_commands: list[str]