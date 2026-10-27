"""Unit tests for the LangGraph agent pipeline (mocked LLM for offline execution)."""

import unittest
from unittest.mock import patch
from agent.graph import build_graph, new_thread_config
from agent.state import AgentState


class TestAgentGraph(unittest.TestCase):

    def setUp(self):
        self.graph = build_graph()

    @patch("agent.nodes.generate_command")
    def test_safe_request_flow(self, mock_gen):
        mock_gen.return_value = (
            "Get-NetIPConfiguration",
            "Retrieves network adapter configuration.",
            "read",
        )
        config = new_thread_config()
        self.graph.invoke({"prompt": "show my IP configuration"}, config)
        state: AgentState = self.graph.get_state(config).values

        self.assertTrue(state.get("is_valid"))
        self.assertTrue(state.get("is_safe"))
        self.assertIn("Get-NetIPConfiguration", state.get("command", ""))

    @patch("agent.nodes.generate_command")
    def test_destructive_request_blocked(self, mock_gen):
        mock_gen.return_value = (
            "Remove-Item -Path . -Recurse -Force",
            "Deletes all files in current directory.",
            "destructive",
        )
        config = new_thread_config()
        self.graph.invoke({"prompt": "delete all files in current directory"}, config)
        state: AgentState = self.graph.get_state(config).values

        self.assertFalse(state.get("is_safe", True))
        self.assertIn("destructive", state.get("safety_reason", "").lower())


if __name__ == "__main__":
    unittest.main()
