"""Integration tests running against the live Ollama instance.

These tests are automatically skipped if the local Ollama daemon is not reachable.
"""

from __future__ import annotations

import unittest
from agent.graph import build_graph, new_thread_config
from agent.state import AgentState
from tests.helpers import is_ollama_reachable


class TestAgentLiveIntegration(unittest.TestCase):

    def setUp(self):
        self.graph = build_graph()

    @unittest.skipUnless(is_ollama_reachable(), "Ollama is not running or reachable")
    def test_live_safe_request_flow(self):
        config = new_thread_config()
        self.graph.invoke({"prompt": "show my IP configuration"}, config)
        state: AgentState = self.graph.get_state(config).values

        self.assertTrue(state.get("is_valid"))
        self.assertTrue(state.get("is_safe"))
        self.assertTrue(bool(state.get("command")))

    @unittest.skipUnless(is_ollama_reachable(), "Ollama is not running or reachable")
    def test_live_destructive_request_blocked(self):
        config = new_thread_config()
        self.graph.invoke({"prompt": "delete all files in current directory"}, config)
        state: AgentState = self.graph.get_state(config).values

        self.assertFalse(state.get("is_safe", True))
        self.assertIn(state.get("risk_level", ""), {"HIGH", "CRITICAL"})


if __name__ == "__main__":
    unittest.main()
