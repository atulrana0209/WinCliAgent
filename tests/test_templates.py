"""Unit tests for deterministic command templates and zero-bypass safety."""

import os
import unittest
from unittest.mock import MagicMock, patch

from agent.graph import build_graph, new_thread_config
from agent.nodes import generate_node
from agent.safety import classify_risk_tier
from agent.templates import match_template
from agent.validator import validate_command


class TestCommandTemplates(unittest.TestCase):
    """Test deterministic fast-path template matching and safety guarantees."""

    def test_positive_intent_matches(self):
        cases = [
            ("where am i", "Get-Location"),
            ("get current working directory path", "Get-Location"),
            ("show disk space usage", "Get-PSDrive -PSProvider FileSystem"),
            ("show free disk space on my computer", "Get-PSDrive -PSProvider FileSystem"),
            ("whoami", "whoami"),
            ("what is my current username", "whoami"),
            ("get computer hostname", "hostname"),
            ("show current date and time", "Get-Date"),
            ("what time is it", "Get-Date"),
            ("show running processes", "Get-Process"),
            ("list all active processes", "Get-Process"),
            ("show my computer information", "Get-ComputerInfo"),
            ("show windows version", "Get-ComputerInfo"),
            ("what is my ip address", "Get-NetIPConfiguration"),
            ("show files in this folder", "Get-ChildItem"),
            ("list all files in the current directory", "Get-ChildItem"),
        ]
        for prompt, expected_cmd in cases:
            with self.subTest(prompt=prompt):
                matched = match_template(prompt)
                self.assertIsNotNone(matched, f"Template should match prompt: '{prompt}'")
                cmd, exp, risk = matched
                self.assertEqual(cmd, expected_cmd)
                self.assertEqual(risk, "read")
                self.assertTrue(len(exp) > 0)

    def test_conservative_near_miss_disqualifications(self):
        """Verify that any prompt with filters, qualifiers, named targets, or parameters falls through to LLM."""
        near_misses = [
            # Path / folder qualifiers
            "list files in src folder",
            "show files in logs directory",
            "show free disk space on drive C",
            "list files in C:\\Windows",
            # Extension / type filters
            "list all python files in current folder",
            "show all markdown files in workspace",
            "display all txt files in current folder",
            # Size / limit / count parameters
            "find files larger than 1000 bytes in current directory",
            "show files smaller than 100 bytes",
            "show top 5 processes by CPU usage",
            "count the number of files in current directory",
            "how many files are in this folder",
            # Named process / service targets
            "find processes named svchost",
            "show all services on this computer",
            "list only running services",
            # Modifying / destructive verbs
            "delete all files in the current folder",
            "wipe the system volume using format C:",
            "terminate all running processes with Stop-Process",
            "create a new directory called build_output",
            # Network specific parameters
            "ping 127.0.0.1 2 times",
            "show MAC address of network adapters",
            "show network adapters",
            # Temporal / relative
            "what is the date tomorrow",
            "list files modified in the last 24 hours in current folder",
        ]
        for prompt in near_misses:
            with self.subTest(prompt=prompt):
                matched = match_template(prompt)
                self.assertIsNone(matched, f"Near-miss prompt MUST NOT match template: '{prompt}'")

    def test_templates_disabled_flag(self):
        """When ENABLE_TEMPLATES is '0', generate_node must skip templates and call LLM."""
        state = {"prompt": "where am i", "previous_commands": []}
        with patch.dict(os.environ, {"ENABLE_TEMPLATES": "0"}):
            with patch("agent.nodes.generate_command") as mock_gen:
                mock_gen.return_value = ("Get-Location", "Mocked location", "read")
                res = generate_node(state)
                self.assertTrue(mock_gen.called)
                self.assertFalse(res.get("template_hit", False))

    def test_zero_safety_bypass_full_graph_execution(self):
        """Test that a template-matched command goes through validator, safety classifier, and audit logging."""
        prompt = "show current date and time"
        matched = match_template(prompt)
        self.assertIsNotNone(matched)
        cmd, _, _ = matched

        # 1. Semantic validator must validate the command
        is_valid, reason = validate_command(cmd, prompt)
        self.assertTrue(is_valid, f"Template command '{cmd}' must pass validator: {reason}")

        # 2. Safety classifier must evaluate the command
        tier, action = classify_risk_tier(cmd)
        self.assertEqual(tier, "LOW", f"Template command '{cmd}' must classify as LOW tier")
        self.assertEqual(action, "ALLOWED", f"Template command '{cmd}' must be ALLOWED")

        # 3. Full pipeline execution: verify graph processes all stages with interrupt
        graph = build_graph()
        config = new_thread_config()
        initial_state = {
            "prompt": prompt,
            "auto": True,
            "verbose": False,
        }

        with patch("agent.nodes.run_command") as mock_exec:
            from agent.executor import ExecutionResult
            mock_exec.return_value = ExecutionResult(stdout="Wednesday, October 28, 2026", stderr="", exit_code=0)

            with patch("agent.nodes.log_audit_event") as mock_logger:
                # First invoke runs generate -> validate -> safety -> interrupts before execute
                graph.invoke(initial_state, config)
                state_before_exec = graph.get_state(config).values

                self.assertTrue(state_before_exec.get("template_hit", False))
                self.assertEqual(state_before_exec.get("command"), "Get-Date")
                self.assertTrue(state_before_exec.get("is_valid"))
                self.assertEqual(state_before_exec.get("risk_level"), "LOW")
                self.assertEqual(state_before_exec.get("action"), "ALLOWED")

                # Resume after approval
                graph.update_state(config, {"approved": True})
                final_state = graph.invoke(None, config)

                self.assertTrue(mock_exec.called)
                self.assertTrue(mock_logger.called)
                # Verify logger received correct tier and command
                logged_kwargs = mock_logger.call_args[1]
                self.assertEqual(logged_kwargs.get("generated_command"), "Get-Date")
                self.assertEqual(logged_kwargs.get("risk"), "LOW")


if __name__ == "__main__":
    unittest.main()
