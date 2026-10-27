# Benchmark Baseline Report: `qwen2.5:3b`

- **Date**: 2026-10-28 04:17:40
- **OS**: Windows 11 (10.0.26200)
- **CPU**: AMD64 Family 25 Model 116 Stepping 1, AuthenticAMD (16 logical cores)
- **RAM**: 15.29 GB total (2.85 GB available)
- **Ollama Version**: ollama version is 0.40.6
- **Model Quantization**: Q4_K_M | Parameters: 3.1B
- **Seed**: 42 | Temperature: 0.0
- **Git Commit**: `3859e18`

## Overall Performance Summary

| Metric | Value |
| :--- | :--- |
| **Final Task Success Rate** | **84.62%** (55/65) [95% CI: 73.94% – 91.42%] |
| **First-Attempt Success Rate** | **76.92%** |
| **Risk-Tier Accuracy** | **89.23%** |
| **Average Retries per Task** | **0.17** |
| **Avg Latency per Task** | **6.43s** (LLM: 2.64s, Exec: 1.57s) |
| **Cold-Start Latency** | **8.15s** (Warm Avg: 6.4s) |
| **Ollama Peak RAM** | **2216.1 MB** (Avg: 2147.9 MB) |

## Dataset Split Performance (with Wilson 95% CI)

| Split | Total Tasks | Success Rate | 95% Confidence Interval | Avg Latency |
| :--- | :--- | :--- | :--- | :--- |
| `dev` | 65 | **84.6%** | [73.94% – 91.42%] | 6.43s |

## Risk-Tier Confusion Matrix

| Expected \ Actual | LOW | MEDIUM | HIGH | CRITICAL | Total |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **LOW** | 46 | 7 | 0 | 0 | 53 |
| **MEDIUM** | 0 | 4 | 0 | 0 | 4 |
| **HIGH** | 0 | 0 | 3 | 0 | 3 |
| **CRITICAL** | 0 | 0 | 0 | 5 | 5 |

## Category Breakdown

| Category | Total | Success Rate | Avg Latency |
| :--- | :--- | :--- | :--- |
| `file_listing` | 8 | 87.5% | 6.38s |
| `filtering_sorting` | 8 | 100.0% | 5.57s |
| `largest_newest` | 6 | 33.3% | 5.65s |
| `counting` | 6 | 66.7% | 8.46s |
| `reading_contents` | 7 | 85.7% | 6.17s |
| `disk_system_info` | 6 | 66.7% | 7.99s |
| `process_info` | 6 | 100.0% | 5.42s |
| `network_info` | 6 | 100.0% | 7.78s |
| `creating_files_folders` | 4 | 100.0% | 6.25s |
| `safety_escalation` | 8 | 100.0% | 5.24s |

## Difficulty Breakdown

| Difficulty | Total | Success Rate | Avg Latency |
| :--- | :--- | :--- | :--- |
| `easy` | 22 | 90.9% | 6.78s |
| `medium` | 23 | 82.6% | 5.82s |
| `hard` | 20 | 80.0% | 6.73s |

## Failure Taxonomy

| Failure Category | Count |
| :--- | :--- |
| `syntax_error` | 5 |
| `wrong_command` | 5 |

