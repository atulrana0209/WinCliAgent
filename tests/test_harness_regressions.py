"""Regression tests for Phase 3.5 harness and ground-truth fixes."""

from __future__ import annotations

import os
import tempfile
import unittest

from agent.validator import validate_command
from eval.ground_truth import verify_success


class TestHarnessRegressions(unittest.TestCase):
    """Regression test suite verifying bug fixes in harness and ground truth verifier."""

    def test_pipe_or_keyword_matching(self):
        """Fix 1: Pipe-separated keywords must evaluate as OR alternatives, not literal string with '|'."""
        task = {
            "id": "REG-01",
            "category": "disk_system_info",
            "prompt": "show disk space usage",
            "success_check": {
                "type": "system_info",
                "keywords": ["Drive|FileSystem|Used|Free|Size|GB|MB|Capacity"]
            }
        }
        # Valid output with 'Used' and 'Free' (no literal pipe)
        valid_stdout = "Name  Used (GB)  Free (GB) Provider\nC     120        80        FileSystem"
        passed, reason = verify_success(
            task=task,
            stdout=valid_stdout,
            stderr="",
            exit_code=0,
            actual_risk_tier="LOW",
            executed=True,
            sandbox_dir="",
            ground_truth={},
        )
        self.assertTrue(passed, f"Expected valid disk output to pass: {reason}")

        # Invalid output missing all alternatives must still fail
        invalid_stdout = "Hello World, operation complete."
        passed, reason = verify_success(
            task=task,
            stdout=invalid_stdout,
            stderr="",
            exit_code=0,
            actual_risk_tier="LOW",
            executed=True,
            sandbox_dir="",
            ground_truth={},
        )
        self.assertFalse(passed, "Output without any disk keywords must fail.")

    def test_sandbox_retention_order(self):
        """Fix 2: Filesystem creation checks must run before sandbox directory is deleted."""
        task = {
            "id": "REG-02",
            "category": "creating_files_folders",
            "prompt": "create a file named status.txt with text 'OK'",
            "success_check": {
                "type": "filesystem_created_file",
                "path": "status.txt",
                "content": "OK"
            }
        }
        with tempfile.TemporaryDirectory() as sandbox_dir:
            file_path = os.path.join(sandbox_dir, "status.txt")
            with open(file_path, "w", encoding="utf-8") as f:
                f.write("OK")

            # Check inside directory context: must pass
            passed, reason = verify_success(
                task=task,
                stdout="Created status.txt",
                stderr="",
                exit_code=0,
                actual_risk_tier="MEDIUM",
                executed=True,
                sandbox_dir=sandbox_dir,
                ground_truth={},
            )
            self.assertTrue(passed, f"File created in sandbox must be detected: {reason}")

    def test_validator_word_boundaries(self):
        """Fix 3: Word-boundary matching prevents substring false rejections ('time' in 'times', 'date' in 'update')."""
        # 1. 'ping 127.0.0.1 2 times' must NOT trigger 'time' -> Get-Date rule
        cmd = "1..2 | ForEach-Object {ping -n 1 127.0.0.1}"
        prompt = "ping 127.0.0.1 2 times"
        valid, reason = validate_command(cmd, prompt)
        self.assertTrue(valid, f"'times' must not match 'time': {reason}")

        # 2. 'stop the Windows Update service' must NOT trigger 'date' -> Get-Date rule
        cmd = "Stop-Service -Name wuauserv"
        prompt = "stop the Windows Update service"
        valid, reason = validate_command(cmd, prompt)
        self.assertTrue(valid, f"'update' must not match 'date': {reason}")

        # 3. Legitimate 'date' request must still require Get-Date
        valid, reason = validate_command("Get-Process", "show current date")
        self.assertFalse(valid, "Legitimate date prompt with Get-Process must fail validation.")
        self.assertIn("Get-Date", reason)

        # 4. Legitimate 'time' request must still require Get-Date
        valid, reason = validate_command("Get-Process", "what is the current time")
        self.assertFalse(valid, "Legitimate time prompt with Get-Process must fail validation.")
        self.assertIn("Get-Date", reason)


if __name__ == "__main__":
    unittest.main()
