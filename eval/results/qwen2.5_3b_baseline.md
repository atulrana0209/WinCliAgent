# Benchmark Baseline Report: `qwen2.5:3b`

- **Date**: 2026-10-28 03:31:10
- **OS**: Windows 11 (10.0.26200)
- **CPU**: AMD64 Family 25 Model 116 Stepping 1, AuthenticAMD (16 logical cores)
- **RAM**: 15.29 GB total (3.16 GB available)
- **Ollama Version**: ollama version is 0.40.6
- **Model Quantization**: Q4_K_M | Parameters: 3.1B
- **Seed**: 42 | Temperature: 0.0
- **Git Commit**: `70ba49b`

## Overall Performance Summary

| Metric | Value |
| :--- | :--- |
| **Final Task Success Rate** | **100.0%** (2/2) [95% CI: 34.24% – 100.0%] |
| **First-Attempt Success Rate** | **100.0%** |
| **Risk-Tier Accuracy** | **50.0%** |
| **Average Retries per Task** | **0.0** |
| **Avg Latency per Task** | **10.49s** (LLM: 6.25s, Exec: 0.84s) |
| **Cold-Start Latency** | **13.79s** (Warm Avg: 7.18s) |
| **Ollama Peak RAM** | **2136.97 MB** (Avg: 2136.95 MB) |

## Dataset Split Performance (with Wilson 95% CI)

| Split | Total Tasks | Success Rate | 95% Confidence Interval | Avg Latency |
| :--- | :--- | :--- | :--- | :--- |
| `dev` | 2 | **100.0%** | [34.24% – 100.0%] | 10.49s |

## Risk-Tier Confusion Matrix

| Expected \ Actual | LOW | MEDIUM | HIGH | CRITICAL | Total |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **LOW** | 1 | 1 | 0 | 0 | 2 |
| **MEDIUM** | 0 | 0 | 0 | 0 | 0 |
| **HIGH** | 0 | 0 | 0 | 0 | 0 |
| **CRITICAL** | 0 | 0 | 0 | 0 | 0 |

## Category Breakdown

| Category | Total | Success Rate | Avg Latency |
| :--- | :--- | :--- | :--- |
| `file_listing` | 2 | 100.0% | 10.49s |

## Difficulty Breakdown

| Difficulty | Total | Success Rate | Avg Latency |
| :--- | :--- | :--- | :--- |
| `easy` | 2 | 100.0% | 10.49s |

## Failure Taxonomy

Zero task failures recorded.

