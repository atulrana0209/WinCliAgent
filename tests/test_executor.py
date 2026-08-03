"""Unit tests for PowerShell executor module."""

import unittest
from agent.executor import run_command


class TestExecutor(unittest.TestCase):

    def test_successful_execution(self):
        result = run_command("Get-Date")
        self.assertEqual(result.exit_code, 0)
        self.assertTrue(len(result.stdout) > 0)

    def test_failed_execution(self):
        result = run_command("NonExistentCmdlet12345")
        self.assertNotEqual(result.exit_code, 0)
        self.assertTrue(len(result.stderr) > 0 or len(result.stdout) > 0)


if __name__ == "__main__":
    unittest.main()
