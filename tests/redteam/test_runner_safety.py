"""Unit test asserting the red-team runner never imports or executes commands."""

import ast
import os
import unittest


class TestRedteamRunnerSafety(unittest.TestCase):

    def test_runner_imports_no_executor_or_subprocess(self):
        runner_path = os.path.join(os.path.dirname(__file__), "runner.py")
        self.assertTrue(os.path.exists(runner_path), f"Runner file not found at {runner_path}")

        with open(runner_path, "r", encoding="utf-8") as f:
            tree = ast.parse(f.read(), filename="runner.py")

        forbidden_imports = {
            "subprocess",
            "agent.executor",
            "executor",
        }

        forbidden_names = {
            "run_command",
            "system",
            "popen",
            "exec",
            "spawn",
        }

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    self.assertNotIn(
                        alias.name,
                        forbidden_imports,
                        f"Forbidden import '{alias.name}' detected in red-team runner!",
                    )
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                self.assertNotIn(
                    module,
                    forbidden_imports,
                    f"Forbidden from-import module '{module}' detected in red-team runner!",
                )
                for alias in node.names:
                    self.assertNotIn(
                        alias.name,
                        forbidden_names,
                        f"Forbidden imported function '{alias.name}' from '{module}' in red-team runner!",
                    )


if __name__ == "__main__":
    unittest.main()
