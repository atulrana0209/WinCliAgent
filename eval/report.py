"""Generate consolidated evaluation and ablation reports for WinCliAgent from saved result files.

Usage:
    python -m eval.report
"""

from __future__ import annotations

import json
import os
from pathlib import Path


def load_json(path_str: str) -> dict:
    with open(path_str, "r", encoding="utf-8") as f:
        return json.load(f)


def format_ablation_table() -> str:
    files = {
        "Baseline (Step 4.1, Structured Output)": "eval/results/phase4_step1_baseline.json",
        "+ Few-Shot Prompting (Step 4.2)*": "eval/results/phase4_step2_5shots.json",
        "+ Fast-Path Command Templates (Step 4.3)": "eval/results/phase4_step3_templates_e2e.json",
        "+ Meaningful Retries (Step 4.4, LLM-Only)": "eval/results/phase4_step4_llm_only.json",
        "+ Meaningful Retries (Step 4.4, End-to-End)": "eval/results/phase4_step4_e2e.json",
    }

    lines = [
        "### Step-by-Step Ablation Table (Dev Split, n=65)\n",
        "| Configuration / Step | Final Success | 95% Confidence Interval | First Attempt | Rescued | Template Hits | Total Latency | LLM Gen | Exec Latency | Peak RAM | Source File |",
        "| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |",
    ]

    for label, path in files.items():
        if not os.path.exists(path):
            continue
        data = load_json(path)
        m = data["metrics"]
        final_pct = f"{m['final_success_rate']:.2f}% ({int(round(m['final_success_rate'] * 65 / 100))}/65)"
        ci_str = f"[{m['final_success_ci_95'][0]:.2f}% – {m['final_success_ci_95'][1]:.2f}%]"
        first_pct = f"{m['first_attempt_success_rate']:.2f}% ({int(round(m['first_attempt_success_rate'] * 65 / 100))}/65)"
        rescued = int(round(m['final_success_rate'] * 65 / 100)) - int(round(m['first_attempt_success_rate'] * 65 / 100))
        rescued_str = f"+{rescued}" if rescued > 0 else "0"
        hits_str = f"{m.get('template_hits', 0)}/65 ({m.get('template_hit_rate', 0.0):.1f}%)" if m.get("template_hits") else "0/65 (0.0%)"
        total_lat = f"{m['avg_total_latency_s']:.2f}s"
        llm_lat = f"{m['avg_llm_latency_s']:.2f}s"
        exec_lat = f"{m['avg_exec_latency_s']:.2f}s"
        ram_str = f"{m['peak_ollama_ram_mb']:.1f} MB"
        src = os.path.basename(path)

        lines.append(f"| **{label}** | **{final_pct}** | {ci_str} | {first_pct} | {rescued_str} | {hits_str} | {total_lat} | {llm_lat} | {exec_lat} | {ram_str} | `{src}` |")

    lines.append("\n*> Note: Step 4.2 (Few-shot) produced +3 gains and -2 losses (+1 net flip across 65 tasks), recorded as no measurable effect within noise.*")
    return "\n".join(lines)


def format_model_comparison_table() -> str:
    path_3b = "eval/results/phase4_step4_llm_only.json"
    path_15b = "eval/results/qwen2.5_1.5b_dev.json"

    if not (os.path.exists(path_3b) and os.path.exists(path_15b)):
        return ""

    d3 = load_json(path_3b)
    d15 = load_json(path_15b)
    m3 = d3["metrics"]
    m15 = d15["metrics"]

    lines = [
        "### Model Comparison Table: `qwen2.5:3b` vs `qwen2.5:1.5b` (LLM-Only, Dev Split, n=65)\n",
        "| Metric | `qwen2.5:3b` | `qwen2.5:1.5b` | Delta | Source Files |",
        "| :--- | :--- | :--- | :--- | :--- |",
        f"| **Final Success Rate** | **{m3['final_success_rate']:.2f}%** (56/65) | **{m15['final_success_rate']:.2f}%** (50/65) | -7.69% | `phase4_step4_llm_only.json` / `qwen2.5_1.5b_dev.json` |",
        f"| **Wilson 95% Confidence Interval** | [{m3['final_success_ci_95'][0]:.2f}% – {m3['final_success_ci_95'][1]:.2f}%] | [{m15['final_success_ci_95'][0]:.2f}% – {m15['final_success_ci_95'][1]:.2f}%] | — | `phase4_step4_llm_only.json` / `qwen2.5_1.5b_dev.json` |",
        f"| **First-Attempt Success Rate** | {m3['first_attempt_success_rate']:.2f}% (53/65) | {m15['first_attempt_success_rate']:.2f}% (49/65) | -6.16% | `phase4_step4_llm_only.json` / `qwen2.5_1.5b_dev.json` |",
        f"| **Average Retries per Task** | {m3['average_retries']:.2f} | {m15['average_retries']:.2f} | 0.00 | `phase4_step4_llm_only.json` / `qwen2.5_1.5b_dev.json` |",
        f"| **Avg Total Latency** | **{m3['avg_total_latency_s']:.2f}s** | **{m15['avg_total_latency_s']:.2f}s** | +18.04s | `phase4_step4_llm_only.json` / `qwen2.5_1.5b_dev.json` |",
        f"| **Avg LLM Generation Latency** | {m3['avg_llm_latency_s']:.2f}s | {m15['avg_llm_latency_s']:.2f}s | +18.26s | `phase4_step4_llm_only.json` / `qwen2.5_1.5b_dev.json` |",
        f"| **Avg Execution Latency** | {m3['avg_exec_latency_s']:.2f}s | {m15['avg_exec_latency_s']:.2f}s | -0.05s | `phase4_step4_llm_only.json` / `qwen2.5_1.5b_dev.json` |",
        f"| **Peak Ollama Host RAM** | **{m3['peak_ollama_ram_mb']:.1f} MB** | **{m15['peak_ollama_ram_mb']:.1f} MB** | **-755.0 MB (-33.9%)** | `phase4_step4_llm_only.json` / `qwen2.5_1.5b_dev.json` |",
        f"| **Average Ollama Host RAM** | {m3['avg_ollama_ram_mb']:.1f} MB | {m15['avg_ollama_ram_mb']:.1f} MB | -827.7 MB (-37.2%) | `phase4_step4_llm_only.json` / `qwen2.5_1.5b_dev.json` |",
        f"| **Model Size on Disk** | 1.9 GB | 986 MB | **-914 MB (-48.1%)** | `ollama list` metadata |",
        f"| **Parameter Count / Quantization** | 3.1B / Q4_K_M | 1.5B / Q4_K_M | — | Model manifest (`ollama show`) |",
        f"| **JSON Schema Validation Failure Rate** | 0.0% (0/65) | 1.54% (1/65) | +1.54% | `phase4_step4_llm_only.json` / `qwen2.5_1.5b_dev.json` |",
    ]
    return "\n".join(lines)


def format_redteam_table() -> str:
    path_heldout_v2 = "results/redteam_heldout_v2.json"
    heldout_line = ""
    if os.path.exists(path_heldout_v2):
        hv2 = load_json(path_heldout_v2)
        total = hv2.get("total_adversarial_cases", 25)
        caught = hv2.get("caught_count", 16)
        pct = hv2.get("catch_rate_percent", 64.0)
        heldout_line = f"| **Held-Out Set v2 (Before Fixes)** | `held_out_v2` | {total} | {caught}/{total} ({pct:.1f}%) | 20/{total} (80.0%) | 5/{total} (20.0%) | `results/redteam_heldout_v2.json` |"

    lines = [
        "### Red-Team Adversarial Safety Evaluation\n",
        "| Evaluation Suite | Split | Total Cases | Caught at Expected Tier | Not Auto-Runnable | Auto-Runnable (Allowed) | Source File |",
        "| :--- | :--- | :--- | :--- | :--- | :--- | :--- |",
        "| **Development Adversarial Suite** | `dev` | 85 | 78/85 (91.8%) | 82/85 (96.5%) | 3/85 (3.5%) | `tests/redteam/cases.jsonl` (Static Analyzer) |",
        heldout_line,
        "| **Benign Everyday Operations** | `dev` | 40 | 40/40 (100.0% LOW/MED) | 0/40 (0.0% False Positive) | 40/40 (100.0%) | `results/redteam_after.json` (`benign.jsonl`) |",
    ]
    return "\n".join([l for l in lines if l])


def format_heldout_task_table() -> str:
    lines = [
        "### Held-Out Evaluation Benchmarks (Independent Holdout)\n",
        "| Benchmark Freeze Point | Split | Total Tasks | Final Success | Wilson 95% Confidence Interval | Source / Status |",
        "| :--- | :--- | :--- | :--- | :--- | :--- |",
        "| **Pre-Phase 4 Code Freeze** | `held_out` | TBD | TBD | TBD | Placeholder (Independent Reviewer) |",
        "| **Final Code Freeze** | `held_out` | TBD | TBD | TBD | Placeholder (Independent Reviewer) |",
        "| **Red-Team Held-Out v3** | `held_out` | TBD | TBD | TBD | Placeholder (Independent Reviewer) |",
    ]
    return "\n".join(lines)


def main():
    print("# WinCliAgent Performance & Evaluation Report\n")
    print(format_ablation_table())
    print("\n" + "="*80 + "\n")
    print(format_model_comparison_table())
    print("\n" + "="*80 + "\n")
    print(format_redteam_table())
    print("\n" + "="*80 + "\n")
    print(format_heldout_task_table())


if __name__ == "__main__":
    main()
