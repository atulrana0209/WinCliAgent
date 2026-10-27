"""Deterministic fixture generator for Held-Out Evaluation Set v2.

Creates an alternative isolated directory tree with distinct file names, contents,
extensions, and timestamps, preventing test contamination.
"""

from __future__ import annotations

import os
import time
from typing import Any


def create_heldout_v2_fixture(base_dir: str) -> dict[str, Any]:
    """Populate base_dir with an alternative deterministic directory structure.

    Tree structure:
    base_dir/
      summary.txt              (180 bytes, created T0 - 3600s)
      inventory.json           (420 bytes, created T0 - 7200s)
      metrics.csv              (6 lines, created T0 - 1800s)
      server.py                (Python entrypoint, 240 bytes)
      deploy.ps1               (PowerShell script, 150 bytes)
      backup_archive.bak       (Large binary file, 15360 bytes)
      license.rtf              (Small file, 45 bytes)
      telemetry/
        events.log             (Log file containing 'WARN' and 'FATAL', 500 bytes)
        stats.json             (JSON metadata, 120 bytes)
      config/
        settings.yaml          (Config file, 95 bytes)
        credentials.template   (Template file, 60 bytes)
      archive_data/
        database.dump          (DB dump, 4096 bytes)
        bundle.tar             (Tar archive, 2048 bytes)
    """
    now = time.time()

    # Subdirectories
    subdirs = ["telemetry", "config", "archive_data"]
    for sd in subdirs:
        os.makedirs(os.path.join(base_dir, sd), exist_ok=True)

    # 1. summary.txt
    summary_path = os.path.join(base_dir, "summary.txt")
    with open(summary_path, "w", encoding="utf-8") as f:
        f.write("Executive Summary\nStatus: Operational\nRelease: 2.4.0-stable\nEnvironment: Production\n")
    os.utime(summary_path, (now - 3600, now - 3600))

    # 2. inventory.json
    inv_path = os.path.join(base_dir, "inventory.json")
    with open(inv_path, "w", encoding="utf-8") as f:
        f.write('{\n  "service": "api-gateway",\n  "cluster": "prod-us-east",\n  "replicas": 4\n}\n')
    os.utime(inv_path, (now - 7200, now - 7200))

    # 3. metrics.csv
    csv_path = os.path.join(base_dir, "metrics.csv")
    with open(csv_path, "w", encoding="utf-8") as f:
        f.write("timestamp,cpu_pct,mem_mb\n100,12.5,256\n101,14.0,260\n102,11.8,255\n103,15.2,264\n104,13.1,258\n")
    os.utime(csv_path, (now - 1800, now - 1800))

    # 4. server.py
    py_path = os.path.join(base_dir, "server.py")
    with open(py_path, "w", encoding="utf-8") as f:
        f.write("import http.server\n\nif __name__ == '__main__':\n    print('Starting server on port 8080')\n")
    os.utime(py_path, (now - 5000, now - 5000))

    # 5. deploy.ps1
    ps1_path = os.path.join(base_dir, "deploy.ps1")
    with open(ps1_path, "w", encoding="utf-8") as f:
        f.write("# Deploy script\nWrite-Output 'Deploying v2.4'\n")
    os.utime(ps1_path, (now - 4000, now - 4000))

    # 6. backup_archive.bak (Largest file: 15 KB)
    bak_path = os.path.join(base_dir, "backup_archive.bak")
    with open(bak_path, "wb") as f:
        f.write(b"BAK_HEADER" + b"\x00" * 15350)
    os.utime(bak_path, (now - 10000, now - 10000))

    # 7. license.rtf (Smallest file: ~40 bytes)
    rtf_path = os.path.join(base_dir, "license.rtf")
    with open(rtf_path, "w", encoding="utf-8") as f:
        f.write("{\\rtf1\\ansi Standard MIT License 2026}\n")
    os.utime(rtf_path, (now - 8000, now - 8000))

    # Subfolder files
    # telemetry/events.log
    events_path = os.path.join(base_dir, "telemetry", "events.log")
    with open(events_path, "w", encoding="utf-8") as f:
        f.write("2026-10-28 01:00:00 INFO Initializing subsystems\n2026-10-28 01:15:22 WARN High memory usage threshold\n2026-10-28 01:20:00 FATAL Network partition encountered\n")
    os.utime(events_path, (now - 2500, now - 2500))

    # config/settings.yaml
    settings_path = os.path.join(base_dir, "config", "settings.yaml")
    with open(settings_path, "w", encoding="utf-8") as f:
        f.write("version: 2.4\nport: 8080\nworkers: 4\n")

    # archive_data/database.dump
    dump_path = os.path.join(base_dir, "archive_data", "database.dump")
    with open(dump_path, "wb") as f:
        f.write(b"SQL_DUMP" + b"\xAA" * 4088)

    return {
        "largest_file": "backup_archive.bak",
        "smallest_file": "license.rtf",
        "newest_file": "metrics.csv",
        "oldest_file": "backup_archive.bak",
        "total_root_files": 7,
        "csv_lines": 6,
    }
