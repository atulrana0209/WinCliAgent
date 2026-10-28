"""Global configuration constants for WinCliAgent."""

from __future__ import annotations

import os

# Execution timeout in seconds
COMMAND_TIMEOUT_SECONDS: int = int(os.getenv("COMMAND_TIMEOUT_SECONDS", "10"))

# Output size limit in bytes (stdout / stderr truncate cap)
MAX_OUTPUT_BYTES: int = int(os.getenv("MAX_OUTPUT_BYTES", str(100 * 1024)))  # 100 KB default

# Truncation marker string
TRUNCATION_MARKER: str = "\n... [OUTPUT TRUNCATED: Exceeded size limit]"
