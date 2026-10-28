"""Comprehensive test suite for semantic result validation, LLM generation, safety, and agent pipeline."""

import unittest
from unittest.mock import patch
from agent.graph import build_graph, new_thread_config
from agent.llm import parse_response
from agent.nodes import generate_node
from agent.result_validator import validate_result
from agent.state import AgentState


class TestPhase10ResultValidator(unittest.TestCase):

    # 1. Successful IP configuration
    def test_ip_configuration_success(self):
        res = validate_result(
            user_prompt="show my IP configuration",
            command="Get-NetIPConfiguration",
            stdout="InterfaceAlias : Wi-Fi\nIPv4Address : 192.0.2.1\nIPv4DefaultGateway : 192.0.2.254",
            stderr="",
            exit_code=0,
        )
        self.assertTrue(res["valid"])
        self.assertEqual(res["quality"], "success")

    # 2. Successful process listing
    def test_process_listing_success(self):
        res = validate_result(
            user_prompt="show running processes",
            command="Get-Process",
            stdout="Handles NPM(K) PM(K) WS(K) CPU(s) Id ProcessName\n770 21 17780 29232 10456 svchost",
            stderr="",
            exit_code=0,
        )
        self.assertTrue(res["valid"])
        self.assertEqual(res["quality"], "success")

    # 3. Successful service listing
    def test_service_listing_success(self):
        res = validate_result(
            user_prompt="show services",
            command="Get-Service",
            stdout="Status Name DisplayName\nRunning wuauserv Windows Update",
            stderr="",
            exit_code=0,
        )
        self.assertTrue(res["valid"])
        self.assertEqual(res["quality"], "success")

    # 4. Successful Python file listing
    def test_python_file_listing_success(self):
        res = validate_result(
            user_prompt="list Python files",
            command="Get-ChildItem -Filter '*.py'",
            stdout="-a---- 03-08-2026 12:43 3944 main.py",
            stderr="",
            exit_code=0,
        )
        self.assertTrue(res["valid"])
        self.assertEqual(res["quality"], "success")

    # 5. Successful disk usage
    def test_disk_usage_success(self):
        res = validate_result(
            user_prompt="show disk usage",
            command="Get-PSDrive -PSProvider FileSystem | Select-Object Name, Used, Free",
            stdout="Name Used Free\n---- ---- ----\nC 50GB 100GB\nD 10GB 400GB",
            stderr="",
            exit_code=0,
        )
        self.assertTrue(res["valid"])
        self.assertEqual(res["quality"], "success")

    # 6. Empty stdout with exit_code 0
    def test_empty_stdout_exit_0(self):
        res = validate_result(
            user_prompt="show running processes",
            command="Get-Process -Name non_existent_app",
            stdout="",
            stderr="",
            exit_code=0,
        )
        self.assertFalse(res["valid"])
        self.assertEqual(res["quality"], "empty")

    # 7. GUI command with empty stdout
    def test_gui_command_empty_stdout(self):
        res = validate_result(
            user_prompt="show Windows version",
            command="winver",
            stdout="",
            stderr="",
            exit_code=0,
        )
        self.assertTrue(res["valid"])
        self.assertEqual(res["quality"], "gui_success")

    # 8. PowerShell command failure
    def test_powershell_failure(self):
        res = validate_result(
            user_prompt="show my IP configuration",
            command="Get-NetIPConfiguration -InvalidParam",
            stdout="",
            stderr="Get-NetIPConfiguration : A parameter cannot be found matching parameter name 'InvalidParam'.",
            exit_code=1,
        )
        self.assertFalse(res["valid"])
        self.assertEqual(res["quality"], "failed")

    # 9. CommandNotFoundException
    def test_command_not_found_exception(self):
        res = validate_result(
            user_prompt="show my IP configuration",
            command="get-invalidcmdletname",
            stdout="",
            stderr="get-invalidcmdletname : CommandNotFoundException: The term 'get-invalidcmdletname' is not recognized...",
            exit_code=1,
        )
        self.assertFalse(res["valid"])
        self.assertEqual(res["quality"], "failed")

    # 10. PropertyNotFoundException
    def test_property_not_found_exception(self):
        res = validate_result(
            user_prompt="show my IP configuration",
            command="Get-NetAdapter | Select-Object IpAddress",
            stdout="PropertyNotFoundException",
            stderr="",
            exit_code=0,
        )
        self.assertFalse(res["valid"])
        self.assertEqual(res["quality"], "failed")

    # 11. Irrelevant output
    def test_irrelevant_output(self):
        res = validate_result(
            user_prompt="show running processes",
            command="Get-PSDrive -PSProvider FileSystem",
            stdout="Name Used Free\nC 50GB 100GB",
            stderr="",
            exit_code=0,
        )
        self.assertFalse(res["valid"])
        self.assertEqual(res["quality"], "irrelevant")

    # 12. Useful output
    def test_useful_output(self):
        res = validate_result(
            user_prompt="show date",
            command="Get-Date",
            stdout="Monday, August 3, 2026 12:00:00 PM",
            stderr="",
            exit_code=0,
        )
        self.assertTrue(res["valid"])
        self.assertEqual(res["quality"], "success")

    # 13. Retry with corrected command
    @patch("agent.nodes.generate_command")
    def test_retry_with_corrected_command(self, mock_gen):
        mock_gen.return_value = (
            "Get-NetIPConfiguration",
            "Retrieves network configuration.",
            "read",
        )
        graph = build_graph()
        config = new_thread_config()
        graph.invoke({"prompt": "show my IP configuration"}, config)
        state: AgentState = graph.get_state(config).values
        self.assertTrue(state.get("is_valid"))
        self.assertTrue(state.get("is_safe"))

    # 14. Retry does not repeat the same command
    @patch("agent.nodes.generate_command")
    def test_retry_does_not_repeat_same_command(self, mock_gen):
        mock_gen.side_effect = [
            ("Get-NetIPConfiguration", "Retrieving network configuration.", "read"),
            ("ipconfig", "Alternative command.", "read"),
        ]
        initial_state: AgentState = {
            "prompt": "show my IP configuration",
            "previous_commands": ["Get-NetIPConfiguration"],
            "error_feedback": "Previous command Get-NetIPConfiguration failed.",
        }
        res = generate_node(initial_state)
        self.assertIn("Get-NetIPConfiguration", res["previous_commands"])
        self.assertGreaterEqual(len(res["previous_commands"]), 2)

    # 15. Retry cannot bypass safety validation
    @patch("agent.nodes.generate_command")
    def test_retry_cannot_bypass_safety_validation(self, mock_gen):
        mock_gen.return_value = (
            "Remove-Item -Path . -Recurse -Force",
            "Delete files",
            "destructive",
        )
        graph = build_graph()
        config = new_thread_config()
        graph.invoke({"prompt": "delete all files in current directory"}, config)
        state: AgentState = graph.get_state(config).values
        self.assertFalse(state.get("is_safe", True))

    # 16. MAX_RETRIES = 2
    @patch("agent.nodes.generate_command")
    def test_max_retries_limit(self, mock_gen):
        mock_gen.return_value = (
            "Get-PSDrive -PSProvider FileSystem",
            "Get disk drives",
            "read",
        )
        graph = build_graph()
        config = new_thread_config()
        graph.invoke({"prompt": "show disk usage"}, config)
        state: AgentState = graph.get_state(config).values
        self.assertLessEqual(state.get("retry_count", 0), 2)

    # 17. Destructive command remains blocked
    @patch("agent.nodes.generate_command")
    def test_destructive_command_blocked(self, mock_gen):
        mock_gen.return_value = (
            "Remove-Item -Path . -Recurse -Force",
            "Delete files",
            "destructive",
        )
        graph = build_graph()
        config = new_thread_config()
        graph.invoke({"prompt": "delete all files in current directory"}, config)
        state: AgentState = graph.get_state(config).values
        self.assertFalse(state.get("is_safe", True))

    # 18. Human confirmation remains active
    def test_human_confirmation_active(self):
        graph = build_graph()
        self.assertIn("execute", graph.interrupt_before_nodes)

    # 19. JSON parsing from Qwen
    def test_json_parsing_qwen(self):
        json_output = '{\n  "command": "Get-NetIPConfiguration",\n  "explanation": "Retrieves network configuration.",\n  "risk": "read"\n}'
        cmd, exp, risk = parse_response(json_output)
        self.assertEqual(cmd, "Get-NetIPConfiguration")
        self.assertEqual(exp, "Retrieves network configuration.")
        self.assertEqual(risk, "read")

    # 20. Malformed Qwen response handling
    def test_malformed_qwen_response_handling(self):
        raw_text = "COMMAND: Get-Process\nEXPLANATION: Lists running processes.\nRISK: read"
        cmd, exp, risk = parse_response(raw_text)
        self.assertEqual(cmd, "Get-Process")
        self.assertEqual(exp, "Lists running processes.")
        self.assertEqual(risk, "read")


if __name__ == "__main__":
    unittest.main()
