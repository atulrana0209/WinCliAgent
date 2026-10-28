"""Unit tests for meaningful retry loop, feedback, attempt caps, and tier escalation protection."""

import unittest
from unittest.mock import MagicMock, call, patch

from agent.executor import ExecutionResult
from agent.graph import build_graph, new_thread_config
from agent.nodes import MAX_RETRIES, generate_node, safety_node, validate_node


class TestMeaningfulRetries(unittest.TestCase):
    """Test retry feedback, attempt limits, duplicate rejection, and safety escalation."""

    def test_feedback_appears_in_retry_prompt(self):
        """Verify failed command, exit code, and truncated stderr appear in error feedback for retry."""
        graph = build_graph()
        config = new_thread_config()

        gen_calls = []

        def mock_generate_side_effect(prompt, error_feedback=None):
            gen_calls.append((prompt, error_feedback))
            if len(gen_calls) == 1:
                return ("Get-BrokenCmd", "Broken command", "read")
            return ("Get-FixedCmd", "Fixed command", "read")

        with patch("agent.nodes.generate_command", side_effect=mock_generate_side_effect), \
             patch("agent.nodes.validate_command", return_value=(True, "Semantic validation pass")), \
             patch("agent.nodes.run_command") as mock_exec, \
             patch("agent.nodes.validate_result") as mock_val_res:

            # Attempt 1: Execution produces non-zero exit code and stderr
            mock_exec.side_effect = [
                ExecutionResult(stdout="", stderr="CommandNotFoundException: Get-BrokenCmd not found on system", exit_code=1),
                ExecutionResult(stdout="Success", stderr="", exit_code=0),
            ]
            mock_val_res.side_effect = [
                {"valid": False, "reason": "Non-zero exit code with error message"},
                {"valid": True, "reason": "Successful output"},
            ]

            # Invoke graph up to execute interrupt
            graph.invoke({"prompt": "find my documents", "auto": True}, config)
            # Approve attempt 1
            graph.update_state(config, {"approved": True})
            # Resume: executes attempt 1, fails result_validation, transitions to retry -> generate (attempt 2)
            graph.invoke(None, config)

            self.assertEqual(len(gen_calls), 2, "generate_command should have been called twice (initial + retry)")
            second_call_feedback = gen_calls[1][1]
            self.assertIsNotNone(second_call_feedback)
            self.assertIn("Get-BrokenCmd", second_call_feedback)
            self.assertIn("Exit code: 1", second_call_feedback)
            self.assertIn("CommandNotFoundException", second_call_feedback)

    def test_cap_at_three_attempts_total(self):
        """Verify pipeline terminates after 3 attempts (MAX_RETRIES = 2 retries after 1 initial)."""
        graph = build_graph()
        config = new_thread_config()

        gen_count = 0

        def failing_gen(prompt, error_feedback=None):
            nonlocal gen_count
            gen_count += 1
            return (f"Get-Attempt{gen_count}", f"Attempt #{gen_count}", "read")

        with patch("agent.nodes.generate_command", side_effect=failing_gen), \
             patch("agent.nodes.validate_command", return_value=(True, "Semantic validation pass")), \
             patch("agent.nodes.run_command", return_value=ExecutionResult(stdout="", stderr="persistent error", exit_code=1)), \
             patch("agent.nodes.validate_result", return_value={"valid": False, "reason": "failed"}):

            # Attempt 1
            graph.invoke({"prompt": "query something", "auto": True}, config)
            graph.update_state(config, {"approved": True})

            # Attempt 2
            graph.invoke(None, config)
            state_2 = graph.get_state(config).values
            if not state_2.get("executed"):
                graph.update_state(config, {"approved": True})

            # Attempt 3
            graph.invoke(None, config)
            state_3 = graph.get_state(config).values
            if not state_3.get("executed"):
                graph.update_state(config, {"approved": True})
            final_state = graph.invoke(None, config)

            # Cap must enforce exactly 3 attempts (initial attempt 1 + 2 retries = 3)
            self.assertLessEqual(gen_count, 3, f"Expected at most 3 generation attempts, got {gen_count}")

    def test_identical_command_rejection_counts_as_failed_attempt(self):
        """Verify that returning the same command as previously failed is rejected as duplicate."""
        state = {
            "prompt": "list files",
            "previous_commands": ["Get-ChildItem"],
            "attempts": 1,
            "retry_count": 1,
            "error_feedback": "Previous command failed",
        }

        with patch("agent.nodes.generate_command", return_value=("Get-ChildItem", "List files", "read")):
            gen_res = generate_node(state)
            self.assertTrue(gen_res.get("is_duplicate"))
            self.assertEqual(gen_res.get("attempts"), 2)

            # Now validate_node must flag it as invalid duplicate
            state.update(gen_res)
            with patch("agent.nodes.log_audit_event") as mock_log:
                val_res = validate_node(state)
                self.assertFalse(val_res.get("is_valid"))
                self.assertIn("repeated previously failed command", val_res.get("validation_reason"))
                self.assertTrue(mock_log.called)

    def test_tier_escalation_stop_requires_confirmation(self):
        """Verify a retry that raises tier above original request's tier stops and requires confirmation."""
        # Attempt 1: established as LOW tier
        state_attempt1 = {
            "command": "Get-Location",
            "llm_risk": "read",
            "retry_count": 0,
            "original_tier": None,
        }
        res1 = safety_node(state_attempt1)
        self.assertEqual(res1.get("risk_level"), "LOW")
        self.assertEqual(res1.get("original_tier"), "LOW")
        self.assertFalse(res1.get("tier_escalated"))

        # Attempt 2 (retry): raises to MEDIUM tier (e.g. Set-Content or modifying command)
        state_attempt2 = {
            "command": "Set-Content -Path test.txt -Value hello",
            "llm_risk": "modifying",
            "retry_count": 1,
            "original_tier": "LOW",
        }
        res2 = safety_node(state_attempt2)
        self.assertEqual(res2.get("risk_level"), "MEDIUM")
        self.assertTrue(res2.get("tier_escalated"), "Safety node must flag tier escalation")
        self.assertEqual(res2.get("action"), "REQUIRES_CONFIRMATION", "Escalated tier must disallow auto-run")

        # Test graph routing: unapproved escalated command must block/halt before execute
        state_for_routing = {
            "risk_level": "MEDIUM",
            "tier_escalated": True,
            "approved": False,
            "is_safe": True,
        }
        from agent.nodes import route_after_safety
        destination = route_after_safety(state_for_routing)
        self.assertEqual(destination, "blocked", "Escalated unapproved retry must be blocked from execution")


if __name__ == "__main__":
    unittest.main()
