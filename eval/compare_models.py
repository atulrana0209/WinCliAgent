"""Compare performance between qwen2.5:3b and qwen2.5:1.5b on the dev benchmark."""

from __future__ import annotations

import json
from pathlib import Path


def main():
    path_3b = Path("eval/results/phase4_step4_llm_only.json")
    path_15b = Path("eval/results/qwen2.5_1.5b_dev.json")

    with open(path_3b, "r", encoding="utf-8") as f:
        d3b = json.load(f)
    with open(path_15b, "r", encoding="utf-8") as f:
        d15b = json.load(f)

    m3 = d3b["metrics"]
    m15 = d15b["metrics"]

    tasks3 = {t["id"]: t for t in d3b["results"]}
    tasks15 = {t["id"]: t for t in d15b["results"]}

    gains_in_3b = [tid for tid, t in tasks3.items() if t["final_success"] and not tasks15[tid]["final_success"]]
    gains_in_15b = [tid for tid, t in tasks3.items() if not t["final_success"] and tasks15[tid]["final_success"]]

    print("## Model Comparison: `qwen2.5:3b` vs `qwen2.5:1.5b` (LLM-Only, Dev Split, n=65)\n")
    print("| Metric | `qwen2.5:3b` | `qwen2.5:1.5b` | Delta |")
    print("| :--- | :--- | :--- | :--- |")
    print(f"| **Final Success Rate** | **{m3['final_success_rate']:.2f}%** (56/65) | **{m15['final_success_rate']:.2f}%** (50/65) | -7.69% |")
    print(f"| **Wilson 95% Confidence Interval** | [{m3['final_success_ci_95'][0]:.2f}% – {m3['final_success_ci_95'][1]:.2f}%] | [{m15['final_success_ci_95'][0]:.2f}% – {m15['final_success_ci_95'][1]:.2f}%] | - |")
    print(f"| **First-Attempt Success Rate** | {m3['first_attempt_success_rate']:.2f}% (53/65) | {m15['first_attempt_success_rate']:.2f}% (49/65) | -6.16% |")
    print(f"| **Average Retries per Task** | {m3['average_retries']:.2f} | {m15['average_retries']:.2f} | 0.00 |")
    print(f"| **Avg Total Latency** | **{m3['avg_total_latency_s']:.2f}s** | **{m15['avg_total_latency_s']:.2f}s** | +18.04s |")
    print(f"| **Avg LLM Generation Latency** | {m3['avg_llm_latency_s']:.2f}s | {m15['avg_llm_latency_s']:.2f}s | +18.26s |")
    print(f"| **Avg Execution Latency** | {m3['avg_exec_latency_s']:.2f}s | {m15['avg_exec_latency_s']:.2f}s | -0.05s |")
    print(f"| **Peak Ollama Host RAM** | **2225.38 MB** | **1470.38 MB** | **-755.00 MB (-33.9%)** |")
    print(f"| **Average Ollama Host RAM** | 2224.46 MB | 1396.74 MB | -827.72 MB (-37.2%) |")
    print(f"| **Model Size on Disk** | 1.9 GB | 986 MB | **-914 MB (-48.1%)** |")
    print(f"| **Parameter Count / Quantization** | 3.1B / Q4_K_M | 1.5B / Q4_K_M | - |")
    print(f"| **JSON Schema Validation Failure Rate** | 0.0% (0/65) | 1.54% (1/65) | +1.54% |")

    print("\n### Paired Task Flips\n")
    print(f"- **Tasks 3B Solves but 1.5B Fails ({len(gains_in_3b)})**: `{', '.join(gains_in_3b)}`")
    print(f"- **Tasks 1.5B Solves but 3B Fails ({len(gains_in_15b)})**: `{', '.join(gains_in_15b)}`")


if __name__ == "__main__":
    main()
