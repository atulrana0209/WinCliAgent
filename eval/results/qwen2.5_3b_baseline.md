# Benchmark Baseline Report: `qwen2.5:3b`

- **Date**: 2026-10-28 10:44:54
- **OS**: Windows 11 (10.0.26200)
- **CPU**: AMD64 Family 25 Model 116 Stepping 1, AuthenticAMD (16 logical cores)
- **RAM**: 15.29 GB total (1.87 GB available)
- **Ollama Version**: ollama version is 0.40.6
- **Model Quantization**: Q4_K_M | Parameters: 3.1B
- **Seed**: 42 | Temperature: 0.0
- **Git Commit**: `8f6929e`

## Overall Performance Summary

| Metric | Value |
| :--- | :--- |
| **Final Task Success Rate** | **84.62%** (55/65) [95% CI: 73.94% – 91.42%] |
| **First-Attempt Success Rate** | **76.92%** |
| **Risk-Tier Accuracy** | **100.0%** |
| **Average Retries per Task** | **0.17** |
| **Avg Latency per Task** | **6.43s** (LLM: 2.66s, Exec: 1.52s) |
| **Cold-Start Latency** | **14.36s** (Warm Avg: 6.31s) |
| **Ollama Peak RAM** | **2213.02 MB** (Avg: 2140.68 MB) |

## Dataset Split Performance (with Wilson 95% CI)

| Split | Total Tasks | Success Rate | 95% Confidence Interval | Avg Latency |
| :--- | :--- | :--- | :--- | :--- |
| `dev` | 65 | **84.6%** | [73.94% – 91.42%] | 6.43s |

## Risk-Tier Confusion Matrix

| Expected \ Actual | LOW | MEDIUM | HIGH | CRITICAL | Total |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **LOW** | 53 | 0 | 0 | 0 | 53 |
| **MEDIUM** | 0 | 4 | 0 | 0 | 4 |
| **HIGH** | 0 | 0 | 3 | 0 | 3 |
| **CRITICAL** | 0 | 0 | 0 | 5 | 5 |

## Category Breakdown

| Category | Total | Success Rate | Avg Latency |
| :--- | :--- | :--- | :--- |
| `file_listing` | 8 | 87.5% | 7.82s |
| `filtering_sorting` | 8 | 100.0% | 5.78s |
| `largest_newest` | 6 | 33.3% | 5.83s |
| `counting` | 6 | 66.7% | 8.25s |
| `reading_contents` | 7 | 85.7% | 5.98s |
| `disk_system_info` | 6 | 66.7% | 7.7s |
| `process_info` | 6 | 100.0% | 5.11s |
| `network_info` | 6 | 100.0% | 7.13s |
| `creating_files_folders` | 4 | 100.0% | 5.8s |
| `safety_escalation` | 8 | 100.0% | 5.01s |

## Difficulty Breakdown

| Difficulty | Total | Success Rate | Avg Latency |
| :--- | :--- | :--- | :--- |
| `easy` | 22 | 90.9% | 6.9s |
| `medium` | 23 | 82.6% | 5.83s |
| `hard` | 20 | 80.0% | 6.61s |

## Failure Taxonomy

| Failure Category | Count |
| :--- | :--- |
| `syntax_error` | 5 |
| `wrong_command` | 5 |

