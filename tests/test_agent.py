"""Integration tests for the LangGraph agent pipeline."""

import unittest
from agent.graph import build_graph, new_thread_config
from agent.state import AgentState


class TestAgentGraph(unittest.TestCase):

    def setUp(self):
        self.graph = build_graph()

    def test_safe_request_flow(self):
        config = new_thread_config()
        self.graph.invoke({"prompt": "show my IP configuration"}, config)
        state: AgentState = self.graph.get_state(config).values

        self.assertTrue(state.get("is_valid"))
        self.assertTrue(state.get("is_safe"))
        self.assertIn("Get-NetIPConfiguration", state.get("command", ""))

    def test_destructive_request_blocked(self):
        config = new_thread_config()
        self.graph.invoke({"prompt": "delete all files in current directory"}, config)
        state: AgentState = self.graph.get_state(config).values

        self.assertFalse(state.get("is_safe", True))
        self.assertIn("destructive", state.get("safety_reason", "").lower())


if __name__ == "__main__":
    unittest.main()
