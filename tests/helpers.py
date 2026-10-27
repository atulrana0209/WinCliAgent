"""Test helper utilities for offline/integration test detection and mocking."""

from __future__ import annotations

import socket


def is_ollama_reachable(host: str = "127.0.0.1", port: int = 11434, timeout: float = 0.5) -> bool:
    """Check if the local Ollama daemon is reachable."""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except (OSError, socket.timeout):
        return False
