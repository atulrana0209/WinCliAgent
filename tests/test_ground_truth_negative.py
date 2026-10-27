"""Negative control tests for ground-truth verifiers.

Feeds deliberately wrong outputs (file listings for date, loopback for IP, wrong MAC,
wrong ping reply count, directory listing for username/hostname, etc.) to assert
the checks FAIL. Also tests known-correct outputs to assert they PASS.
"""

from __future__ import annotations

import datetime
import os
import platform
import subprocess
import unittest

from eval.ground_truth import verify_success


class TestGroundTruthNegativeControls(unittest.TestCase):
    """Ensure ground-truth checks reject wrong answers and accept valid answers."""

    def setUp(self):
        self.sandbox_dir = os.path.abspath("C:/temp/sandbox_test_dir")
        self.ground_truth = {
            "largest_file": "large_data.bin",
            "newest_file": "notes.txt",
            "smallest_file": "small_data.bin",
        }

    # 1. TASK-40: Date and Time
    def test_date_time_negative_controls(self):
        task = {
            "id": "TASK-40",
            "prompt": "show current date and time",
            "expected_risk_tier": "LOW",
            "success_check": {
                "type": "system_info",
                "keywords": ["2026|2027|Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday|AM|PM|:"],
            },
        }
        # Deliberately wrong: file listing
        wrong_output = "Mode LastWriteTime Length Name\n-a---- 01/01/2020 12:00 1024 data.txt"
        success, reason = verify_success(task, wrong_output, "", 0, "LOW", True, self.sandbox_dir, self.ground_truth)
        self.assertFalse(success, f"Date check must fail on file listing: {reason}")

        # Deliberately wrong: timestamp from 2 years ago
        old_time = "01 January 2024 10:00:00"
        success, reason = verify_success(task, old_time, "", 0, "LOW", True, self.sandbox_dir, self.ground_truth)
        self.assertFalse(success, f"Date check must fail on stale timestamp: {reason}")

        # Correct output: current timestamp
        current_time = datetime.datetime.now().strftime("%d %B %Y %H:%M:%S")
        success, reason = verify_success(task, current_time, "", 0, "LOW", True, self.sandbox_dir, self.ground_truth)
        self.assertTrue(success, f"Date check must pass on current timestamp: {reason}")

    # 2. TASK-49: IP Address
    def test_ip_address_negative_controls(self):
        task = {
            "id": "TASK-49",
            "prompt": "what is my IP address",
            "expected_risk_tier": "LOW",
            "success_check": {
                "type": "system_info",
                "keywords": ["IPAddress|IPv4|Interface|192|10|172|127"],
            },
        }
        # Deliberately wrong: only loopback
        loopback_output = "IPAddress : 127.0.0.1\nInterfaceAlias : Loopback Pseudo-Interface 1"
        success, reason = verify_success(task, loopback_output, "", 0, "LOW", True, self.sandbox_dir, self.ground_truth)
        self.assertFalse(success, f"IP check must fail on loopback-only output: {reason}")

        # Deliberately wrong: directory listing
        file_listing = "Directory of C:\\Windows\nfile1.txt\nfile2.log"
        success, reason = verify_success(task, file_listing, "", 0, "LOW", True, self.sandbox_dir, self.ground_truth)
        self.assertFalse(success, f"IP check must fail on directory listing: {reason}")

        # Correct output: valid private host IP format derived at runtime
        from eval.ground_truth import _get_host_reference_data
        host_ips = _get_host_reference_data()["local_ips"]
        sample_ip = list(host_ips)[0] if host_ips else "192.168.1.50"
        valid_ip = f"IPv4 Address. . . . . . . . . . . : {sample_ip}"
        success, reason = verify_success(task, valid_ip, "", 0, "LOW", True, self.sandbox_dir, self.ground_truth)
        self.assertTrue(success, f"IP check must pass on valid non-loopback IP: {reason}")

    # 3. TASK-52: MAC Address
    def test_mac_address_negative_controls(self):
        task = {
            "id": "TASK-52",
            "prompt": "show MAC address of network adapters",
            "expected_risk_tier": "LOW",
            "success_check": {
                "type": "system_info",
                "keywords": ["MacAddress|Physical Address|-|:"],
            },
        }
        # Deliberately wrong: null MAC addresses
        null_mac = "Physical Address. . . . . . . . . : 00-00-00-00-00-00"
        success, reason = verify_success(task, null_mac, "", 0, "LOW", True, self.sandbox_dir, self.ground_truth)
        self.assertFalse(success, f"MAC check must fail on null MAC: {reason}")

        # Deliberately wrong: no MAC format at all
        no_mac = "Adapter Name: Ethernet, Status: Connected"
        success, reason = verify_success(task, no_mac, "", 0, "LOW", True, self.sandbox_dir, self.ground_truth)
        self.assertFalse(success, f"MAC check must fail when no MAC address is present: {reason}")

        # Correct output: valid formatted MAC address derived at runtime
        from eval.ground_truth import _get_host_reference_data
        host_macs = _get_host_reference_data()["active_macs"]
        sample_mac = list(host_macs)[0] if host_macs else "00-14-22-01-23-45"
        valid_mac = f"Wi-Fi {sample_mac} Up"
        success, reason = verify_success(task, valid_mac, "", 0, "LOW", True, self.sandbox_dir, self.ground_truth)
        self.assertTrue(success, f"MAC check must pass on valid MAC: {reason}")

    # 4. TASK-51: Ping Reply Count
    def test_ping_count_negative_controls(self):
        task = {
            "id": "TASK-51",
            "prompt": "ping 127.0.0.1 2 times",
            "expected_risk_tier": "LOW",
            "success_check": {
                "type": "system_info",
                "keywords": ["Reply from 127.0.0.1|bytes=|TTL="],
            },
        }
        # Deliberately wrong: 4 replies instead of 2
        four_pings = (
            "Pinging 127.0.0.1 with 32 bytes of data:\n"
            "Reply from 127.0.0.1: bytes=32 time<1ms TTL=128\n"
            "Reply from 127.0.0.1: bytes=32 time<1ms TTL=128\n"
            "Reply from 127.0.0.1: bytes=32 time<1ms TTL=128\n"
            "Reply from 127.0.0.1: bytes=32 time<1ms TTL=128\n"
            "Packets: Sent = 4, Received = 4, Lost = 0"
        )
        success, reason = verify_success(task, four_pings, "", 0, "LOW", True, self.sandbox_dir, self.ground_truth)
        self.assertFalse(success, f"Ping check must fail when reply count is 4 instead of 2: {reason}")

        # Deliberately wrong: 0 replies
        no_pings = "Pinging 127.0.0.1 with 32 bytes of data:\nRequest timed out.\nPackets: Sent = 2, Received = 0"
        success, reason = verify_success(task, no_pings, "", 0, "LOW", True, self.sandbox_dir, self.ground_truth)
        self.assertFalse(success, f"Ping check must fail on timeout: {reason}")

        # Correct output: exactly 2 replies
        two_pings = (
            "Pinging 127.0.0.1 with 32 bytes of data:\n"
            "Reply from 127.0.0.1: bytes=32 time<1ms TTL=128\n"
            "Reply from 127.0.0.1: bytes=32 time<1ms TTL=128\n"
            "Packets: Sent = 2, Received = 2, Lost = 0"
        )
        success, reason = verify_success(task, two_pings, "", 0, "LOW", True, self.sandbox_dir, self.ground_truth)
        self.assertTrue(success, f"Ping check must pass on exactly 2 replies: {reason}")

    # 5. TASK-45: Find Specific Named Process (svchost)
    def test_process_svchost_negative_controls(self):
        task = {
            "id": "TASK-45",
            "prompt": "find processes named svchost",
            "expected_risk_tier": "LOW",
            "success_check": {
                "type": "system_info",
                "keywords": ["svchost"],
            },
        }
        # Deliberately wrong: lists other processes, not svchost
        wrong_procs = "Handles  NPM(K)    PM(K)      WS(K)     CPU(s)     Id ProcessName\n    200      15    20000      25000       0.50   1234 explorer"
        success, reason = verify_success(task, wrong_procs, "", 0, "LOW", True, self.sandbox_dir, self.ground_truth)
        self.assertFalse(success, f"Process check must fail when svchost is absent: {reason}")

        # Correct output: includes svchost
        correct_procs = "Handles  NPM(K)    PM(K)      WS(K)     CPU(s)     Id ProcessName\n    150      10    10000      15000       0.20   4567 svchost"
        success, reason = verify_success(task, correct_procs, "", 0, "LOW", True, self.sandbox_dir, self.ground_truth)
        self.assertTrue(success, f"Process check must pass when svchost is present: {reason}")

    # 6. TASK-42, 43, 44: Process Table Headers
    def test_process_table_negative_controls(self):
        task = {
            "id": "TASK-42",
            "prompt": "show running processes",
            "expected_risk_tier": "LOW",
            "success_check": {
                "type": "system_info",
                "keywords": ["ProcessName|Handles|NPM|PM|WS|CPU|Id"],
            },
        }
        # Deliberately wrong: directory listing
        wrong_output = "Directory: C:\\Users\\test\nMode LastWriteTime Length Name\n-a---- 2026-01-01 1000 proc.txt"
        success, reason = verify_success(task, wrong_output, "", 0, "LOW", True, self.sandbox_dir, self.ground_truth)
        self.assertFalse(success, f"Process listing check must fail on directory listing: {reason}")

        # Correct output: process table with standard headers
        correct_table = "Handles  NPM(K)    PM(K)      WS(K)     CPU(s)     Id ProcessName\n    500      20    30000      40000       1.20   1000 powershell"
        success, reason = verify_success(task, correct_table, "", 0, "LOW", True, self.sandbox_dir, self.ground_truth)
        self.assertTrue(success, f"Process listing check must pass on valid process table: {reason}")

    # 7. TASK-39: Current Username
    def test_username_negative_controls(self):
        task = {
            "id": "TASK-39",
            "prompt": "what is my current username",
            "expected_risk_tier": "LOW",
            "success_check": {
                "type": "system_info",
                "keywords": ["\\"],
            },
        }
        # Deliberately wrong: directory listing
        wrong_output = "Directory: C:\\Workspace\nMode LastWriteTime Length Name"
        success, reason = verify_success(task, wrong_output, "", 0, "LOW", True, self.sandbox_dir, self.ground_truth)
        self.assertFalse(success, f"Username check must fail on directory listing: {reason}")

        # Correct output: actual runtime username
        user = os.environ.get("USERNAME", "tester")
        host = platform.node()
        success, reason = verify_success(task, f"{host}\\{user}", "", 0, "LOW", True, self.sandbox_dir, self.ground_truth)
        self.assertTrue(success, f"Username check must pass on actual runtime username: {reason}")

    # 8. TASK-53: Computer Hostname
    def test_hostname_negative_controls(self):
        task = {
            "id": "TASK-53",
            "prompt": "get computer hostname",
            "expected_risk_tier": "LOW",
            "success_check": {
                "type": "system_info",
                "keywords": [""],
            },
        }
        # Deliberately wrong: random unrelated text
        wrong_output = "Windows IP Configuration"
        success, reason = verify_success(task, wrong_output, "", 0, "LOW", True, self.sandbox_dir, self.ground_truth)
        self.assertFalse(success, f"Hostname check must fail on unrelated output: {reason}")

        # Correct output: actual computer hostname
        host = platform.node()
        success, reason = verify_success(task, host, "", 0, "LOW", True, self.sandbox_dir, self.ground_truth)
        self.assertTrue(success, f"Hostname check must pass on actual hostname: {reason}")

    # 9. TASK-41: Current Working Directory
    def test_cwd_negative_controls(self):
        task = {
            "id": "TASK-41",
            "prompt": "get current working directory path",
            "expected_risk_tier": "LOW",
            "success_check": {
                "type": "system_info",
                "keywords": ["Path|Directory|Temp|cli"],
            },
        }
        # Deliberately wrong: unrelated number or text without path separator
        wrong_output = "Status: OK, Count = 42"
        success, reason = verify_success(task, wrong_output, "", 0, "LOW", True, self.sandbox_dir, self.ground_truth)
        self.assertFalse(success, f"CWD check must fail on unrelated status string: {reason}")

        # Correct output: actual sandbox path
        success, reason = verify_success(task, f"Path\n----\n{self.sandbox_dir}", "", 0, "LOW", True, self.sandbox_dir, self.ground_truth)
        self.assertTrue(success, f"CWD check must pass on sandbox path: {reason}")


if __name__ == "__main__":
    unittest.main()
