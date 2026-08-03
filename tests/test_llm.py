"""Unit tests for LLM parser and generation module."""

import unittest
from agent.llm import parse_response


class TestLLMParser(unittest.TestCase):

    def test_json_parsing(self):
        json_output = '{\n  "command": "Get-NetIPConfiguration",\n  "explanation": "Retrieves network configuration.",\n  "risk": "read"\n}'
        cmd, exp, risk = parse_response(json_output)
        self.assertEqual(cmd, "Get-NetIPConfiguration")
        self.assertEqual(exp, "Retrieves network configuration.")
        self.assertEqual(risk, "read")

    def test_markdown_json_parsing(self):
        markdown_json = '```json\n{\n  "command": "Get-ChildItem",\n  "explanation": "Lists directory contents.",\n  "risk": "read"\n}\n```'
        cmd, exp, risk = parse_response(markdown_json)
        self.assertEqual(cmd, "Get-ChildItem")
        self.assertEqual(exp, "Lists directory contents.")
        self.assertEqual(risk, "read")

    def test_fallback_keyvalue_parsing(self):
        kv_output = "COMMAND: Get-Process\nEXPLANATION: Lists running processes.\nRISK: read"
        cmd, exp, risk = parse_response(kv_output)
        self.assertEqual(cmd, "Get-Process")
        self.assertEqual(exp, "Lists running processes.")
        self.assertEqual(risk, "read")


if __name__ == "__main__":
    unittest.main()
