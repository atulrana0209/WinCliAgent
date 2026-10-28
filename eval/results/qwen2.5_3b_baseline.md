# Benchmark Baseline Report: `qwen2.5:3b`

- **Date**: 2026-10-28 12:46:22
- **OS**: Windows 11 (10.0.26200)
- **CPU**: AMD64 Family 25 Model 116 Stepping 1, AuthenticAMD (16 logical cores)
- **RAM**: 15.29 GB total (1.91 GB available)
- **Ollama Version**: ollama version is 0.40.6
- **Model Quantization**: Q4_K_M | Parameters: 3.1B
- **Seed**: 42 | Temperature: 0.0
- **Git Commit**: `aea837c`

## Overall Performance Summary

| Metric | Value |
| :--- | :--- |
| **Final Task Success Rate** | **89.23%** (57/65) [95% CI: 79.4% – 94.68%] |
| **First-Attempt Success Rate** | **86.15%** |
| **Risk-Tier Accuracy** | **96.92%** |
| **Average Retries per Task** | **0.06** |
| **Avg Latency per Task** | **6.0s** (LLM: 2.57s, Exec: 1.07s) |
| **Template Hit Rate** | **20.0%** (13/65) |
| **Latency (Template Hits)** | **3.82s** (vs Non-Hits: **6.54s**) |
| **Cold-Start Latency** | **3.3s** (Warm Avg: 6.04s) |
| **Ollama Peak RAM** | **2224.23 MB** (Avg: 2158.12 MB) |

## Dataset Split Performance (with Wilson 95% CI)

| Split | Total Tasks | Success Rate | 95% Confidence Interval | Avg Latency |
| :--- | :--- | :--- | :--- | :--- |
| `dev` | 65 | **89.2%** | [79.4% – 94.68%] | 6.0s |

## Risk-Tier Confusion Matrix

| Expected \ Actual | LOW | MEDIUM | HIGH | CRITICAL | Total |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **LOW** | 51 | 2 | 0 | 0 | 53 |
| **MEDIUM** | 0 | 4 | 0 | 0 | 4 |
| **HIGH** | 0 | 0 | 3 | 0 | 3 |
| **CRITICAL** | 0 | 0 | 0 | 5 | 5 |

## Category Breakdown

| Category | Total | Success Rate | Avg Latency |
| :--- | :--- | :--- | :--- |
| `file_listing` | 8 | 100.0% | 6.38s |
| `filtering_sorting` | 8 | 100.0% | 6.2s |
| `largest_newest` | 6 | 0.0% | 7.7s |
| `counting` | 6 | 100.0% | 6.71s |
| `reading_contents` | 7 | 85.7% | 6.33s |
| `disk_system_info` | 6 | 100.0% | 3.59s |
| `process_info` | 6 | 100.0% | 5.13s |
| `network_info` | 6 | 100.0% | 5.76s |
| `creating_files_folders` | 4 | 100.0% | 6.92s |
| `safety_escalation` | 8 | 100.0% | 5.48s |

## Difficulty Breakdown

| Difficulty | Total | Success Rate | Avg Latency |
| :--- | :--- | :--- | :--- |
| `easy` | 22 | 100.0% | 5.06s |
| `medium` | 23 | 82.6% | 6.44s |
| `hard` | 20 | 85.0% | 6.52s |

## Failure Taxonomy

| Failure Category | Count |
| :--- | :--- |
| `wrong_command` | 7 |

