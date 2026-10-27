# Benchmark Baseline Report: `qwen2.5:3b`

- **Date**: 2026-10-28 03:14:35
- **OS**: Windows 11 (10.0.26200)
- **CPU**: AMD64 Family 25 Model 116 Stepping 1, AuthenticAMD (16 logical cores)
- **RAM**: 15.29 GB total (1.9 GB available)
- **Ollama Version**: ollama version is 0.40.6
- **Git Commit**: `6de2443`

## Overall Performance Summary

| Metric | Value |
| :--- | :--- |
| **Final Task Success Rate** | **53.85%** (35/65) |
| **First-Attempt Success Rate** | **52.31%** |
| **Risk-Tier Accuracy** | **55.38%** |
| **Average Retries per Task** | **0.17** |
| **Avg Latency per Task** | **6.16s** (LLM: 3.26s, Exec: 1.63s) |
| **Cold-Start Latency** | **3.8s** (Warm Avg: 6.2s) |
| **Ollama Peak RAM** | **49.47 MB** (Avg: 48.22 MB) |

## Dataset Split Performance

| Split | Total Tasks | Success Rate | Avg Latency |
| :--- | :--- | :--- | :--- |
| `dev` | 44 | **56.8%** | 5.7s |
| `held_out` | 21 | **47.6%** | 7.12s |

## Category Breakdown

| Category | Total | Success Rate | Avg Latency |
| :--- | :--- | :--- | :--- |
| `file_listing` | 8 | 100.0% | 4.17s |
| `filtering_sorting` | 8 | 50.0% | 9.14s |
| `largest_newest` | 6 | 50.0% | 9.67s |
| `counting` | 6 | 50.0% | 5.53s |
| `reading_contents` | 7 | 57.1% | 4.59s |
| `disk_system_info` | 6 | 0.0% | 4.71s |
| `process_info` | 6 | 16.7% | 4.93s |
| `network_info` | 6 | 16.7% | 7.59s |
| `creating_files_folders` | 4 | 100.0% | 5.05s |
| `safety_escalation` | 8 | 87.5% | 5.87s |

## Difficulty Breakdown

| Difficulty | Total | Success Rate | Avg Latency |
| :--- | :--- | :--- | :--- |
| `easy` | 22 | 31.8% | 4.68s |
| `medium` | 23 | 65.2% | 6.29s |
| `hard` | 20 | 65.0% | 7.63s |

## Failure Taxonomy

| Failure Category | Count |
| :--- | :--- |
| `syntax_error` | 5 |
| `wrong_command` | 23 |
| `validator_false_reject` | 2 |

