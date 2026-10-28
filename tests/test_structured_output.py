"""Hermetic unit tests for LLM structured output parsing and schema validation."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from pydantic import ValidationError

from agent.llm import CommandOutput, generate_command, parse_response


class TestStructuredOutput(unittest.TestCase):
    """Test parse_response and schema validation with mocked LLM output."""

    def test_valid_json_parses_cleanly(self):
        """Valid JSON conforming to schema parses into command, explanation, risk."""
        raw = '{"command": "Get-ChildItem -File", "explanation": "List all files", "risk": "read"}'
        cmd, exp, risk = parse_response(raw)
        self.assertEqual(cmd, "Get-ChildItem -File")
        self.assertEqual(exp, "List all files")
        self.assertEqual(risk, "read")

    def test_valid_json_wrapped_in_markdown(self):
        """JSON enclosed in markdown code fences parses correctly."""
        raw = '```json\n{"command": "Get-Process", "explanation": "Show running processes", "risk": "read"}\n```'
        cmd, exp, risk = parse_response(raw)
        self.assertEqual(cmd, "Get-Process")
        self.assertEqual(risk, "read")

    def test_malformed_json_fallback(self):
        """Malformed JSON falls back to regex / key-value extraction."""
        raw = "Here is the command:\nCOMMAND: Get-Service\nEXPLANATION: Show services\nRISK: read"
        cmd, exp, risk = parse_response(raw)
        self.assertEqual(cmd, "Get-Service")
        self.assertEqual(exp, "Show services")
        self.assertEqual(risk, "read")

    def test_missing_required_fields_fails_validation(self):
        """JSON missing required fields cannot construct CommandOutput."""
        # Missing 'command'
        raw = '{"explanation": "No command here", "risk": "read"}'
        with self.assertRaises(RuntimeError):
            parse_response(raw)

        # Missing 'risk'
        raw2 = '{"command": "Get-Location", "explanation": "cwd"}'
        # In fallback, missing risk defaults to 'read' or raises if invalid
        cmd, exp, risk = parse_response(raw2)
        self.assertEqual(cmd, "Get-Location")
        self.assertEqual(risk, "read")

    def test_extra_fields_forbidden(self):
        """Schema specifies extra='forbid', extra fields trigger validation failure or fallback."""
        raw = '{"command": "Get-Date", "explanation": "current date", "risk": "read", "unexpected_payload": 42}'
        # Direct Pydantic validation should forbid extra fields
        with self.assertRaises(ValidationError):
            CommandOutput.model_validate_json(raw)

        # parse_response recovers valid core fields via fallback
        cmd, exp, risk = parse_response(raw)
        self.assertEqual(cmd, "Get-Date")
        self.assertEqual(risk, "read")

    def test_wrong_risk_value(self):
        """Risk value outside Literal['read', 'modifying', 'destructive'] is rejected by Pydantic."""
        raw = '{"command": "Stop-Process -Name svchost", "explanation": "kill", "risk": "extremely_dangerous"}'
        with self.assertRaises(ValidationError):
            CommandOutput.model_validate_json(raw)

    def test_empty_or_whitespace_command(self):
        """Empty command or backtick-only string fails validation."""
        for empty_val in ['{"command": "", "explanation": "none", "risk": "read"}',
                          '{"command": "   ", "explanation": "none", "risk": "read"}',
                          '{"command": "`   `", "explanation": "none", "risk": "read"}']:
            with self.assertRaises(RuntimeError):
                parse_response(empty_val)

    def test_command_containing_quotes_and_newlines(self):
        """PowerShell command with nested quotes, escaped characters, and newlines parses cleanly."""
        raw = '{"command": "Get-ChildItem -Filter \\"*.txt\\" | Where-Object { $_.Length -gt 100 }", "explanation": "Filter files", "risk": "read"}'
        cmd, exp, risk = parse_response(raw)
        self.assertEqual(cmd, 'Get-ChildItem -Filter "*.txt" | Where-Object { $_.Length -gt 100 }')
        self.assertEqual(risk, "read")

    @patch("agent.llm.get_llm")
    def test_reprompt_on_initial_schema_failure(self, mock_get_llm):
        """When initial model response is completely unparseable, re-prompts once with error."""
        mock_llm_instance = MagicMock()
        mock_get_llm.return_value = mock_llm_instance

        # First call returns garbage, second call returns valid JSON
        mock_resp1 = MagicMock()
        mock_resp1.content = "Invalid garbage text with no command whatsoever."
        mock_resp2 = MagicMock()
        mock_resp2.content = '{"command": "Get-Process", "explanation": "Processes", "risk": "read"}'

        mock_llm_instance.invoke.side_effect = [mock_resp1, mock_resp2]

        cmd, exp, risk = generate_command("show running processes")
        self.assertEqual(cmd, "Get-Process")
        self.assertEqual(risk, "read")
        # Ensure LLM was invoked twice (initial + reprompt)
        self.assertEqual(mock_llm_instance.invoke.call_count, 2)


if __name__ == "__main__":
    unittest.main()
