# Benchmark Baseline Report: `qwen2.5:1.5b`

- **Date**: 2026-10-28 14:38:36
- **OS**: Windows 11 (10.0.26200)
- **CPU**: AMD64 Family 25 Model 116 Stepping 1, AuthenticAMD (16 logical cores)
- **RAM**: 15.29 GB total (1.78 GB available)
- **Ollama Version**: ollama version is 0.40.6
- **Model Quantization**: Q4_K_M | Parameters: 1.5B
- **Seed**: 42 | Temperature: 0.0
- **Git Commit**: `77b6a07`

## Overall Performance Summary

| Metric | Value |
| :--- | :--- |
| **Final Task Success Rate** | **78.46%** (50/65) [95% CI: 67.03% – 86.71%] |
| **First-Attempt Success Rate** | **75.38%** |
| **Risk-Tier Accuracy** | **93.85%** |
| **Average Retries per Task** | **0.11** |
| **Avg Latency per Task** | **24.86s** (LLM: 21.39s, Exec: 1.24s) |
| **Cold-Start Latency** | **7.19s** (Warm Avg: 25.38s) |
| **Ollama Peak RAM** | **1470.38 MB** (Avg: 1396.74 MB) |

## Dataset Split Performance (with Wilson 95% CI)

| Split | Total Tasks | Success Rate | 95% Confidence Interval | Avg Latency |
| :--- | :--- | :--- | :--- | :--- |
| `dev` | 65 | **78.5%** | [67.03% – 86.71%] | 24.86s |

## Risk-Tier Confusion Matrix

| Expected \ Actual | LOW | MEDIUM | HIGH | CRITICAL | Total |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **LOW** | 52 | 0 | 1 | 0 | 53 |
| **MEDIUM** | 0 | 3 | 1 | 0 | 4 |
| **HIGH** | 1 | 0 | 2 | 0 | 3 |
| **CRITICAL** | 0 | 1 | 0 | 4 | 5 |

## Category Breakdown

| Category | Total | Success Rate | Avg Latency |
| :--- | :--- | :--- | :--- |
| `file_listing` | 8 | 100.0% | 4.89s |
| `filtering_sorting` | 8 | 87.5% | 165.34s |
| `largest_newest` | 6 | 50.0% | 4.89s |
| `counting` | 6 | 50.0% | 5.51s |
| `reading_contents` | 7 | 85.7% | 4.51s |
| `disk_system_info` | 6 | 83.3% | 5.56s |
| `process_info` | 6 | 100.0% | 4.66s |
| `network_info` | 6 | 66.7% | 6.09s |
| `creating_files_folders` | 4 | 75.0% | 5.97s |
| `safety_escalation` | 8 | 75.0% | 4.79s |

## Difficulty Breakdown

| Difficulty | Total | Success Rate | Avg Latency |
| :--- | :--- | :--- | :--- |
| `easy` | 22 | 90.9% | 5.38s |
| `medium` | 23 | 69.6% | 5.12s |
| `hard` | 20 | 75.0% | 68.99s |

## Failure Taxonomy

| Failure Category | Count |
| :--- | :--- |
| `syntax_error` | 4 |
| `wrong_command` | 8 |
| `validator_false_reject` | 1 |
| `wrong_risk_tier` | 1 |

