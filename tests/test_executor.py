"""Unit tests for PowerShell executor module."""

import os
import unittest
from unittest.mock import MagicMock, patch
import subprocess

from agent.config import COMMAND_TIMEOUT_SECONDS, MAX_OUTPUT_BYTES, TRUNCATION_MARKER
from agent.executor import ExecutionResult, _truncate_output, run_command


class TestExecutor(unittest.TestCase):

    @unittest.skipUnless(os.getenv("RUN_HOST_TESTS") == "1", "Host-dependent test (requires live Windows/PowerShell); set RUN_HOST_TESTS=1 to run")
    def test_successful_execution(self):
        result = run_command("Get-Date")
        self.assertEqual(result.exit_code, 0)
        self.assertTrue(len(result.stdout) > 0)

    @unittest.skipUnless(os.getenv("RUN_HOST_TESTS") == "1", "Host-dependent test (requires live Windows/PowerShell); set RUN_HOST_TESTS=1 to run")
    def test_failed_execution(self):
        result = run_command("NonExistentCmdlet12345")
        self.assertNotEqual(result.exit_code, 0)
        self.assertTrue(len(result.stderr) > 0 or len(result.stdout) > 0)

    @unittest.skipUnless(os.getenv("RUN_HOST_TESTS") == "1", "Host-dependent test (requires live Windows/PowerShell); set RUN_HOST_TESTS=1 to run")
    def test_live_command_timeout(self):
        """Live test: command that sleeps longer than timeout returns 124."""
        result = run_command("Start-Sleep -Seconds 3", timeout=1)
        self.assertEqual(result.exit_code, 124)
        self.assertIn("timed out", result.stderr)

    @unittest.skipUnless(os.getenv("RUN_HOST_TESTS") == "1", "Host-dependent test (requires live Windows/PowerShell); set RUN_HOST_TESTS=1 to run")
    def test_live_huge_output_truncation(self):
        """Live test: command generating > 100KB output gets truncated."""
        result = run_command("1..20000 | ForEach-Object { 'Line ' + $_ }")
        self.assertIn(TRUNCATION_MARKER, result.stdout)

    def test_command_timeout(self):
        """Hanging command must be killed after timeout and return exit code 124."""
        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd=["mock"], timeout=2)):
            result = run_command("Start-Sleep -Seconds 10", timeout=2)
            self.assertEqual(result.exit_code, 124)
            self.assertIn("timed out after 2 seconds", result.stderr)

    def test_huge_output_truncation(self):
        """Output exceeding MAX_OUTPUT_BYTES must be truncated and marked."""
        huge_str = "A" * (MAX_OUTPUT_BYTES + 500)
        truncated = _truncate_output(huge_str, max_bytes=MAX_OUTPUT_BYTES)
        self.assertTrue(len(truncated.encode("utf-8")) <= MAX_OUTPUT_BYTES + len(TRUNCATION_MARKER.encode("utf-8")))
        self.assertIn(TRUNCATION_MARKER, truncated)

    def test_run_command_truncates_large_output(self):
        """run_command must truncate process output if it exceeds size limits."""
        huge_stdout = "x" * (MAX_OUTPUT_BYTES + 1000)
        huge_stderr = "y" * (MAX_OUTPUT_BYTES + 1000)
        mock_completed = subprocess.CompletedProcess(
            args=["pwsh"], returncode=0, stdout=huge_stdout, stderr=huge_stderr
        )
        with patch("subprocess.run", return_value=mock_completed):
            result = run_command("Get-HugeData")
            self.assertIn(TRUNCATION_MARKER, result.stdout)
            self.assertIn(TRUNCATION_MARKER, result.stderr)


if __name__ == "__main__":
    unittest.main()
