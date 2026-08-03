"""Command execution with process timeout controls."""

from __future__ import annotations

import platform
import shutil
import subprocess
from dataclasses import dataclass

MAX_EXECUTION_TIME = 10  # Seconds


@dataclass
class ExecutionResult:
    stdout: str
    stderr: str
    exit_code: int


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
    timeout: int = MAX_EXECUTION_TIME,
) -> ExecutionResult:
    """Run command with a strict execution timeout."""

    argv = _resolve_shell(command)

    try:
        completed = subprocess.run(
            argv,
            capture_output=True,
            text=True,
            timeout=timeout,
        )

        return ExecutionResult(
            stdout=completed.stdout,
            stderr=completed.stderr,
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