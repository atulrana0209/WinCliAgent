# Benchmark Baseline Report: `qwen2.5:3b`

- **Date**: 2026-10-28 03:54:05
- **OS**: Windows 11 (10.0.26200)
- **CPU**: AMD64 Family 25 Model 116 Stepping 1, AuthenticAMD (16 logical cores)
- **RAM**: 15.29 GB total (2.12 GB available)
- **Ollama Version**: ollama version is 0.40.6
- **Model Quantization**: Q4_K_M | Parameters: 3.1B
- **Seed**: 42 | Temperature: 0.0
- **Git Commit**: `af84b13`

## Overall Performance Summary

| Metric | Value |
| :--- | :--- |
| **Final Task Success Rate** | **76.92%** (49/65) [95% CI: 65.36% – 85.49%] |
| **First-Attempt Success Rate** | **75.38%** |
| **Risk-Tier Accuracy** | **53.85%** |
| **Average Retries per Task** | **0.17** |
| **Avg Latency per Task** | **6.65s** (LLM: 2.56s, Exec: 1.9s) |
| **Cold-Start Latency** | **9.54s** (Warm Avg: 6.6s) |
| **Ollama Peak RAM** | **2236.73 MB** (Avg: 2211.39 MB) |

## Dataset Split Performance (with Wilson 95% CI)

| Split | Total Tasks | Success Rate | 95% Confidence Interval | Avg Latency |
| :--- | :--- | :--- | :--- | :--- |
| `dev` | 45 | **80.0%** | [66.18% – 89.1%] | 6.25s |
| `held_out` | 20 | **70.0%** | [48.1% – 85.45%] | 7.55s |

## Risk-Tier Confusion Matrix

| Expected \ Actual | LOW | MEDIUM | HIGH | CRITICAL | Total |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **LOW** | 23 | 30 | 0 | 0 | 53 |
| **MEDIUM** | 0 | 4 | 0 | 0 | 4 |
| **HIGH** | 0 | 0 | 3 | 0 | 3 |
| **CRITICAL** | 0 | 0 | 0 | 5 | 5 |

## Category Breakdown

| Category | Total | Success Rate | Avg Latency |
| :--- | :--- | :--- | :--- |
| `file_listing` | 8 | 100.0% | 5.91s |
| `filtering_sorting` | 8 | 50.0% | 9.57s |
| `largest_newest` | 6 | 50.0% | 9.66s |
| `counting` | 6 | 50.0% | 6.34s |
| `reading_contents` | 7 | 57.1% | 5.76s |
| `disk_system_info` | 6 | 83.3% | 5.73s |
| `process_info` | 6 | 83.3% | 5.96s |
| `network_info` | 6 | 100.0% | 6.41s |
| `creating_files_folders` | 4 | 100.0% | 6.04s |
| `safety_escalation` | 8 | 100.0% | 4.89s |

## Difficulty Breakdown

| Difficulty | Total | Success Rate | Avg Latency |
| :--- | :--- | :--- | :--- |
| `easy` | 22 | 86.4% | 5.89s |
| `medium` | 23 | 73.9% | 6.62s |
| `hard` | 20 | 70.0% | 7.51s |

## Failure Taxonomy

| Failure Category | Count |
| :--- | :--- |
| `syntax_error` | 5 |
| `wrong_command` | 10 |

