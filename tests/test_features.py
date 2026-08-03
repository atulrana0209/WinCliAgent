"""Unit tests for new WinCliAgent features (Risk Tiers, Audit Logs, Normalizer, Timeout, Dry-Run)."""

import os
import unittest
from agent.executor import MAX_EXECUTION_TIME, run_command
from agent.logger import LOG_FILE, log_audit_event
from agent.normalizer import normalize_command, parse_command_structure
from agent.safety import classify_risk_tier, screen_command_risk


class TestNewFeatures(unittest.TestCase):

    def test_risk_tiers_classification(self):
        tier, action = classify_risk_tier("Get-Process")
        self.assertEqual(tier, "LOW")
        self.assertEqual(action, "ALLOWED")

        tier, action = classify_risk_tier("Start-Process notepad")
        self.assertEqual(tier, "MEDIUM")
        self.assertEqual(action, "ALLOWED")

        tier, action = classify_risk_tier("Remove-Item -Path file.txt")
        self.assertEqual(tier, "HIGH")
        self.assertEqual(action, "BLOCKED")

        tier, action = classify_risk_tier("format C:")
        self.assertEqual(tier, "CRITICAL")
        self.assertEqual(action, "BLOCKED")

    def test_screen_command_risk_structure(self):
        is_safe, reason, risk, action = screen_command_risk("Get-NetIPConfiguration")
        self.assertTrue(is_safe)
        self.assertEqual(risk, "LOW")
        self.assertEqual(action, "ALLOWED")

    def test_alias_normalization(self):
        cmd = "gci -Path . | Select-Object Name"
        normalized = normalize_command(cmd)
        self.assertEqual(normalized, "Get-ChildItem -Path . | Select-Object Name")

        cmd2 = "dir"
        self.assertEqual(normalize_command(cmd2), "Get-ChildItem")

    def test_structural_command_parsing(self):
        cmd = "dir -Path C:\\ -Recurse | Where-Object {$_.Length -gt 100}"
        parsed = parse_command_structure(cmd)
        self.assertTrue(parsed.has_pipeline)
        self.assertIn("Get-ChildItem", parsed.cmdlets)
        self.assertIn("-Path", parsed.parameters)

    def test_executor_timeout_setting(self):
        self.assertEqual(MAX_EXECUTION_TIME, 10)

    def test_audit_logging(self):
        event = log_audit_event(
            user_prompt="test prompt",
            generated_command="Get-Date",
            risk="LOW",
            action="ALLOWED",
            approved=True,
            exit_code=0,
            validation="PASS",
            retry_count=0,
        )
        self.assertEqual(event["user_prompt"], "test prompt")
        self.assertEqual(event["risk"], "LOW")
        self.assertTrue(os.path.exists(LOG_FILE))


if __name__ == "__main__":
    unittest.main()
