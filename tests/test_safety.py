"""Unit tests for safety screening module."""

import unittest
from agent.safety import classify_risk, screen_command


class TestSafety(unittest.TestCase):

    def test_readonly_commands(self):
        safe_commands = [
            "Get-ChildItem",
            "Get-Process",
            "Get-Service",
            "Get-NetIPConfiguration",
            "Get-ComputerInfo",
            "Get-Date",
            "pwd",
            "ipconfig",
        ]
        for cmd in safe_commands:
            is_safe, reason, risk = screen_command(cmd)
            self.assertTrue(is_safe, f"Expected {cmd} to be safe")
            self.assertEqual(risk, "read", f"Expected {cmd} to be classified as 'read'")

    def test_destructive_commands(self):
        destructive_commands = [
            "Remove-Item -Path . -Recurse",
            "Stop-Process -Name explorer",
            "Stop-Service -Name wuauserv",
            "format C:",
            "del /s /q *.*",
            "shutdown /s /t 0",
        ]
        for cmd in destructive_commands:
            is_safe, reason, risk = screen_command(cmd)
            self.assertFalse(is_safe, f"Expected {cmd} to be blocked")
            self.assertEqual(risk, "destructive", f"Expected {cmd} to be classified as 'destructive'")

    def test_dangerous_arguments(self):
        cmd = "Set-ItemProperty -Path . -Name Test -Value 1 -Force"
        is_safe, reason, risk = screen_command(cmd)
        self.assertFalse(is_safe)
        self.assertEqual(risk, "destructive")

    def test_unknown_commands(self):
        cmd = "Custom-Tool -Option Value"
        is_safe, reason, risk = screen_command(cmd)
        self.assertTrue(is_safe)
        self.assertEqual(risk, "unknown")


if __name__ == "__main__":
    unittest.main()
