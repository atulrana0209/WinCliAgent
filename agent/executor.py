"""Command execution."""

from __future__ import annotations

import platform
import shutil
import subprocess
from dataclasses import dataclass


@dataclass
class ExecutionResult:
    stdout: str
    stderr: str
    exit_code: int


DEFAULT_TIMEOUT_SECONDS = 60


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
        "commands on this platform (it is preinstalled in the provided Docker image)."
    )


def run_command(
    command: str,
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
) -> ExecutionResult:

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
            stderr=f"Command timed out after {timeout} seconds.",
            exit_code=124,
        )

    except FileNotFoundError as exc:
        return ExecutionResult(
            stdout="",
            stderr=str(exc),
            exit_code=127,
        )