"""Deterministic test fixture for WinCliAgent evaluation harness.

Creates an isolated temporary directory tree with known files, sizes,
extensions, timestamps, and contents.
"""

from __future__ import annotations

import os
import time
from typing import Any


def create_deterministic_fixture(base_dir: str) -> dict[str, Any]:
    """Populate base_dir with a rich, deterministic set of files and directories.
    
    Returns:
        Ground-truth metadata dictionary for independent verification.
    """
    now = time.time()
    day = 86400

    # Directory layout
    dirs = [
        "docs",
        "src",
        "logs",
        "archive",
    ]
    for d in dirs:
        os.makedirs(os.path.join(base_dir, d), exist_ok=True)

    # File definitions: (rel_path, content_or_bytes, mtime_offset_seconds)
    files: list[tuple[str, str | bytes, float]] = [
        # Root files
        ("README.md", "# Project Documentation\nWelcome to the test workspace.\nVersion 1.0.0\n", now - 2 * day),
        ("data.csv", "id,name,value\n1,alpha,100\n2,beta,200\n3,gamma,300\n4,delta,400\n", now - 3 * day),
        ("config.json", '{\n  "environment": "staging",\n  "port": 8080,\n  "debug": true\n}\n', now - 10 * day),
        ("app.py", 'def main():\n    print("Running main application")\n\nif __name__ == "__main__":\n    main()\n', now - 4 * day),
        ("test_app.py", "import unittest\n\nclass TestApp(unittest.TestCase):\n    def test_ok(self):\n        self.assertTrue(True)\n", now - 4 * day),
        ("report.txt", "Quarterly System Performance Report\nAll metrics within nominal range.\nUptime: 99.98%\n", now - 1 * day),
        ("notes.txt", "TODO: Review database indexing and clean temp files.\n", now - 3600),  # Newest file (1 hour ago)
        ("logo.png", b"\x89PNG\r\n\x1a\n" + b"\x00" * 200, now - 5 * day),
        ("large_data.bin", b"A" * 15000, now - 7 * day),  # Largest file (15,000 bytes)
        ("small_data.bin", b"X" * 12, now - 8 * day),     # Smallest file (12 bytes)
        # docs/
        ("docs/manual.md", "# User Manual\nComplete guide to system usage.\nStep 1: Install\nStep 2: Run\n", now - 6 * day),
        ("docs/architecture.txt", "Architecture overview:\nClient -> Agent -> PowerShell Engine\n", now - 6 * day),
        ("docs/changelog.txt", "v1.0.0 - Initial release\nv0.9.0 - Beta build\n", now - 12 * day),
        # src/
        ("src/main.py", 'import sys\n\ndef run():\n    return 0\n', now - 2 * day),
        ("src/utils.py", 'def calculate(a, b):\n    return a + b\n', now - 2 * day),
        ("src/helper.py", 'def get_version():\n    return "1.0.0"\n', now - 2 * day),
        # logs/
        ("logs/app.log", "INFO: Application started\nINFO: Worker initialized\nINFO: Ready\n", now - 5000),
        ("logs/error.log", "ERROR: Connection timeout on port 5432\nINFO: Retrying connection\nERROR: Authentication failed\nERROR: Service unavailable\n", now - 4000),
        ("logs/debug.log", "DEBUG: Trace 0x01\nDEBUG: Trace 0x02\nDEBUG: Trace 0x03\nDEBUG: Trace 0x04\n", now - 3000),
        # archive/
        ("archive/backup_2025.zip", b"PK\x03\x04" + b"\x00" * 500, now - 30 * day),
    ]

    for rel_path, content, mtime in files:
        full_path = os.path.join(base_dir, rel_path)
        if isinstance(content, str):
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(content)
        else:
            with open(full_path, "wb") as f:
                f.write(content)
        os.utime(full_path, (mtime, mtime))

    # Compute ground truth
    root_items = os.listdir(base_dir)
    root_files = [f for f in root_items if os.path.isfile(os.path.join(base_dir, f))]
    root_dirs = [d for d in root_items if os.path.isdir(os.path.join(base_dir, d))]

    py_files_recursive = []
    log_files_recursive = []
    all_files_recursive = []
    file_sizes = {}

    for root, _subdirs, filenames in os.walk(base_dir):
        for fname in filenames:
            rel = os.path.relpath(os.path.join(root, fname), base_dir)
            all_files_recursive.append(rel)
            size = os.path.getsize(os.path.join(root, fname))
            file_sizes[rel] = size
            if fname.endswith(".py"):
                py_files_recursive.append(fname)
            if fname.endswith(".log"):
                log_files_recursive.append(fname)

    return {
        "base_dir": base_dir,
        "root_files": sorted(root_files),
        "root_dirs": sorted(root_dirs),
        "total_root_files": len(root_files),
        "total_root_dirs": len(root_dirs),
        "all_files_recursive": sorted(all_files_recursive),
        "total_files_recursive": len(all_files_recursive),
        "py_files": sorted(set(py_files_recursive)),
        "log_files": sorted(set(log_files_recursive)),
        "largest_file": "large_data.bin",
        "largest_file_size": 15000,
        "smallest_file": "small_data.bin",
        "smallest_file_size": 12,
        "newest_file": "notes.txt",
        "error_log_error_count": 3,
        "data_csv_line_count": 5,
    }
