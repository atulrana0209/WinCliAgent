"""Unit tests for command validator module."""

import unittest
from agent.validator import validate_command


class TestValidator(unittest.TestCase):

    def test_known_command_mappings(self):
        test_cases = [
            ("show my IP configuration", "Get-NetIPConfiguration", True),
            ("show my IP configuration", "ipconfig", True),
            ("show my MAC address", "Get-NetAdapter", True),
            ("show my MAC address", "getmac", True),
            ("list files in current directory", "Get-ChildItem", True),
            ("show running processes", "Get-Process", True),
            ("show services", "Get-Service", True),
            ("show date", "Get-Date", True),
        ]
        for prompt, cmd, expected in test_cases:
            is_valid, reason = validate_command(cmd, prompt)
            self.assertEqual(is_valid, expected, f"Prompt: '{prompt}', Cmd: '{cmd}'. Reason: {reason}")

    def test_invalid_property_hallucination(self):
        bad_cmd = "Get-NetAdapter | Select-Object -ExpandProperty IpAddress"
        prompt = "show my IP configuration"
        is_valid, reason = validate_command(bad_cmd, prompt)
        self.assertFalse(is_valid)
        self.assertIn("Get-NetIPConfiguration", reason)

    def test_destructive_action_on_info_request(self):
        bad_cmd = "Remove-Item -Path . -Recurse"
        prompt = "show my current directory"
        is_valid, reason = validate_command(bad_cmd, prompt)
        self.assertFalse(is_valid)


if __name__ == "__main__":
    unittest.main()
