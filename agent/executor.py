"""Command execution with process timeout controls."""

from __future__ import annotations

import platform
import shutil
import subprocess
from dataclasses import dataclass

from .config import COMMAND_TIMEOUT_SECONDS, MAX_OUTPUT_BYTES, TRUNCATION_MARKER

MAX_EXECUTION_TIME = COMMAND_TIMEOUT_SECONDS  # Backward compatibility alias


@dataclass
class ExecutionResult:
    stdout: str
    stderr: str
    exit_code: int


def _truncate_output(text: str, max_bytes: int = MAX_OUTPUT_BYTES) -> str:
    """Truncate output if it exceeds max_bytes and append TRUNCATION_MARKER."""
    if not text:
        return ""
    encoded = text.encode("utf-8", errors="replace")
    if len(encoded) > max_bytes:
        truncated_bytes = encoded[:max_bytes]
        return truncated_bytes.decode("utf-8", errors="ignore") + TRUNCATION_MARKER
    return text


def _resolve_shell(command: str) -> list[str]:
    """Pick how to invoke the command depending on the host platform."""

    system = platform.system()

    if system == "Windows":
        if shutil.which("pwsh"):
            return ["pwsh", "-NoProfile", "-Command", command]

        if shutil.which("powershell"):
            return ["powershell", "-NoProfile", "-Command", command]

        return ["cmd", "/c", command]

    pwsh = shutil.which("pwsh")

    if pwsh:
        return [pwsh, "-NoProfile", "-Command", command]

    raise RuntimeError(
        "PowerShell Core (pwsh) is not installed. Install it to run Windows-style "
        "commands on this platform."
    )


def run_command(
    command: str,
    timeout: int = COMMAND_TIMEOUT_SECONDS,
    cwd: str | None = None,
) -> ExecutionResult:
    """Run command with a strict execution timeout and optional working directory."""

    argv = _resolve_shell(command)

    try:
        completed = subprocess.run(
            argv,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=cwd,
        )

        stdout = _truncate_output(completed.stdout)
        stderr = _truncate_output(completed.stderr)

        return ExecutionResult(
            stdout=stdout,
            stderr=stderr,
            exit_code=completed.returncode,
        )

    except subprocess.TimeoutExpired:
        return ExecutionResult(
            stdout="",
            stderr=f"Command execution timed out after {timeout} seconds.",
            exit_code=124,
        )

    except FileNotFoundError as exc:
        return ExecutionResult(
            stdout="",
            stderr=str(exc),
            exit_code=127,
        )