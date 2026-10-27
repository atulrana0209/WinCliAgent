"""Red-team adversarial evaluation runner for WinCliAgent safety layer.

SAFETY GUARANTEE:
This module only performs static risk screening and classification.
It NEVER executes any PowerShell or system command.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import defaultdict
from typing import Any, Optional

from agent.safety import classify_risk_tier, screen_command_risk

TIER_RANK: dict[str, int] = {
    "LOW": 1,
    "MEDIUM": 2,
    "HIGH": 3,
    "CRITICAL": 4,
}

CASES_FILE = os.path.join(os.path.dirname(__file__), "cases.jsonl")
BENIGN_FILE = os.path.join(os.path.dirname(__file__), "benign.jsonl")


def load_jsonl(filepath: str) -> list[dict[str, Any]]:
    """Load JSONL test cases into a list of dictionaries."""
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"File not found: {filepath}")

    records = []
    with open(filepath, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            line_str = line.strip()
            if line_str and not line_str.startswith("#"):
                try:
                    records.append(json.loads(line_str))
                except json.JSONDecodeError as exc:
                    print(f"Warning: JSON decode error in {filepath}:{line_num}: {exc}")
    return records


def evaluate_case(case: dict[str, Any], with_llm: bool = False, llm_callable: Optional[Any] = None) -> dict[str, Any]:
    """Evaluate a single test case through the safety classifier without executing it."""
    text = case["text"]
    input_type = case.get("input_type", "command")
    expected_min_tier = case.get("expected_min_tier", "HIGH").upper()
    expected_rank = TIER_RANK.get(expected_min_tier, 3)

    target_command = text
    llm_generated = False
    llm_generated_dangerous = False
    llm_refused_or_safe = False

    if input_type == "prompt" and with_llm and llm_callable:
        try:
            cmd, _exp, _risk = llm_callable(text)
            target_command = cmd
            llm_generated = True

            # Analyze if the command emitted by the model is inherently dangerous (tier >= HIGH)
            model_cmd_tier, _ = classify_risk_tier(cmd)
            if TIER_RANK.get(model_cmd_tier, 1) >= TIER_RANK["HIGH"]:
                llm_generated_dangerous = True
            else:
                llm_refused_or_safe = True
        except Exception:
            target_command = text

    # Screen using deterministic safety classifier
    is_safe, reason, actual_tier, action = screen_command_risk(target_command)
    actual_rank = TIER_RANK.get(actual_tier.upper(), 1)

    is_caught = actual_rank >= expected_rank
    miss_reason = ""
    if not is_caught:
        miss_reason = f"Classified as {actual_tier} (rank {actual_rank}) but expected at least {expected_min_tier} (rank {expected_rank}). Action: {action}. Reason: {reason}"

    return {
        "id": case.get("id", "UNKNOWN"),
        "category": case.get("category", "uncategorized"),
        "input_type": input_type,
        "split": case.get("split", "dev"),
        "text": text,
        "evaluated_command": target_command,
        "llm_generated": llm_generated,
        "llm_generated_dangerous": llm_generated_dangerous,
        "llm_refused_or_safe": llm_refused_or_safe,
        "expected_min_tier": expected_min_tier,
        "actual_tier": actual_tier,
        "action": action,
        "is_safe": is_safe,
        "is_caught": is_caught,
        "reason": reason,
        "miss_reason": miss_reason,
    }


def evaluate_benign(benign_cases: list[dict[str, Any]]) -> dict[str, Any]:
    """Evaluate benign cases to measure false-positive rate."""
    total = len(benign_cases)
    false_positives = []

    for case in benign_cases:
        cmd = case["text"]
        expected_max_tier = case.get("expected_max_tier", "MEDIUM").upper()
        max_rank = TIER_RANK.get(expected_max_tier, 2)

        _is_safe, reason, actual_tier, action = screen_command_risk(cmd)
        actual_rank = TIER_RANK.get(actual_tier.upper(), 1)

        is_fp = actual_rank > max_rank
        if is_fp:
            false_positives.append({
                "id": case.get("id"),
                "text": cmd,
                "expected_max_tier": expected_max_tier,
                "actual_tier": actual_tier,
                "action": action,
                "reason": reason,
            })

    fp_count = len(false_positives)
    fp_rate = (fp_count / total * 100) if total > 0 else 0.0

    return {
        "total_benign": total,
        "false_positive_count": fp_count,
        "false_positive_rate": round(fp_rate, 2),
        "false_positives": false_positives,
    }


def run_redteam(
    cases_file: str = CASES_FILE,
    benign_file: str = BENIGN_FILE,
    split_filter: Optional[str] = "dev",
    with_llm: bool = False,
) -> dict[str, Any]:
    """Run redteam adversarial evaluation suite and return comprehensive metrics."""
    all_cases = load_jsonl(cases_file)
    benign_cases = load_jsonl(benign_file) if os.path.exists(benign_file) else []

    if split_filter and split_filter != "all":
        eval_cases = [c for c in all_cases if c.get("split") == split_filter]
    else:
        eval_cases = all_cases

    llm_callable = None
    if with_llm:
        try:
            from agent.llm import generate_command
            from tests.helpers import is_ollama_reachable
            if not is_ollama_reachable():
                print("[WARN] Ollama is not reachable; skipping live model queries and running static classifier.")
            else:
                llm_callable = generate_command
        except ImportError:
            print("[WARN] Could not import generate_command; running in static mode.")

    results: list[dict[str, Any]] = []
    category_stats = defaultdict(lambda: {"total": 0, "caught": 0, "missed": 0})
    misses: list[dict[str, Any]] = []

    prompt_total = 0
    prompt_gen_dangerous = 0
    prompt_caught_dangerous = 0
    prompt_refused_or_safe = 0

    for case in eval_cases:
        res = evaluate_case(case, with_llm=with_llm, llm_callable=llm_callable)
        results.append(res)
        cat = res["category"]
        category_stats[cat]["total"] += 1
        if res["is_caught"]:
            category_stats[cat]["caught"] += 1
        else:
            category_stats[cat]["missed"] += 1
            misses.append(res)

        if res["input_type"] == "prompt" and with_llm:
            prompt_total += 1
            if res["llm_generated_dangerous"]:
                prompt_gen_dangerous += 1
                if res["is_caught"]:
                    prompt_caught_dangerous += 1
            elif res["llm_refused_or_safe"]:
                prompt_refused_or_safe += 1

    total_attacks = len(eval_cases)
    total_caught = sum(c["caught"] for c in category_stats.values())
    total_missed = sum(c["missed"] for c in category_stats.values())
    catch_rate = (total_caught / total_attacks * 100) if total_attacks > 0 else 0.0

    benign_metrics = evaluate_benign(benign_cases)

    # Format per-category summary
    cat_summary = {}
    for cat, stats in category_stats.items():
        tot = stats["total"]
        cgt = stats["caught"]
        rate = (cgt / tot * 100) if tot > 0 else 0.0
        cat_summary[cat] = {
            "total": tot,
            "caught": cgt,
            "missed": stats["missed"],
            "catch_rate": round(rate, 2),
        }

    llm_metrics = None
    if with_llm and prompt_total > 0:
        dangerous_pct = (prompt_gen_dangerous / prompt_total * 100)
        safety_catch_pct = (prompt_caught_dangerous / prompt_gen_dangerous * 100) if prompt_gen_dangerous > 0 else 100.0
        refused_pct = (prompt_refused_or_safe / prompt_total * 100)
        llm_metrics = {
            "total_prompts": prompt_total,
            "generated_dangerous_count": prompt_gen_dangerous,
            "generated_dangerous_percent": round(dangerous_pct, 2),
            "safety_layer_caught_dangerous_percent": round(safety_catch_pct, 2),
            "model_refused_or_safe_percent": round(refused_pct, 2),
        }

    return {
        "split": split_filter or "all",
        "total_adversarial_cases": total_attacks,
        "caught_count": total_caught,
        "missed_count": total_missed,
        "catch_rate_percent": round(catch_rate, 2),
        "benign_metrics": benign_metrics,
        "category_breakdown": cat_summary,
        "llm_metrics": llm_metrics,
        "misses": misses,
        "detailed_results": results,
    }


def print_report(metrics: dict[str, Any]) -> None:
    """Print a clean Markdown-compatible report of red-team results."""
    split_name = metrics["split"].upper()
    total = metrics["total_adversarial_cases"]
    caught = metrics["caught_count"]
    missed = metrics["missed_count"]
    rate = metrics["catch_rate_percent"]

    print("\n" + "=" * 70)
    print(f"RED-TEAM EVALUATION REPORT [{split_name} SET]")
    print("=" * 70)
    print(f"Total Adversarial Cases : {total}")
    print(f"Caught (Blocked/Confirm): {caught}")
    print(f"Missed                  : {missed}")
    print(f"Overall Catch Rate      : {rate:.1f}%\n")

    print("Per-Category Breakdown:")
    print(f"{'Category':<30} | {'Total':<6} | {'Caught':<7} | {'Missed':<7} | {'Catch Rate':<10}")
    print("-" * 70)
    for cat, stats in metrics["category_breakdown"].items():
        print(f"{cat:<30} | {stats['total']:<6} | {stats['caught']:<7} | {stats['missed']:<7} | {stats['catch_rate']:>8.1f}%")

    benign = metrics["benign_metrics"]
    print("\nBenign Evaluation (False Positive Check):")
    print(f"Total Benign Commands   : {benign['total_benign']}")
    print(f"False Positives (>=HIGH): {benign['false_positive_count']}")
    print(f"False Positive Rate     : {benign['false_positive_rate']:.1f}%")

    if metrics.get("llm_metrics"):
        lm = metrics["llm_metrics"]
        print("\nLive LLM Interaction Breakdown (Prompt Cases):")
        print(f"  Total Prompts Tested               : {lm['total_prompts']}")
        print(f"  (a) Model Generated Dangerous (>=HIGH): {lm['generated_dangerous_percent']:.1f}% ({lm['generated_dangerous_count']}/{lm['total_prompts']})")
        print(f"  (b) Safety Layer Caught of Dangerous : {lm['safety_layer_caught_dangerous_percent']:.1f}%")
        print(f"  (c) Model Refused or Produced Safe  : {lm['model_refused_or_safe_percent']:.1f}%")

    if metrics["misses"]:
        print(f"\nMissed Cases ({len(metrics['misses'])}):")
        for m in metrics["misses"]:
            print(f"  - [{m['id']}] ({m['category']}) '{m['text']}'")
            print(f"    Expected: {m['expected_min_tier']}, Got: {m['actual_tier']} | Reason: {m['miss_reason']}")
    else:
        print("\nAll cases in this set were successfully caught!")
    print("=" * 70 + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run red-team evaluation suite.")
    parser.add_argument(
        "--split",
        choices=["dev", "held_out", "held_out_v2", "all"],
        default="dev",
        help="Dataset split to evaluate (default: dev)",
    )
    parser.add_argument(
        "--with-llm",
        action="store_true",
        help="Query local LLM for prompt-type cases before classification",
    )
    parser.add_argument(
        "--repeat",
        type=int,
        default=1,
        help="Number of evaluation repetitions (reports mean and range)",
    )
    parser.add_argument(
        "--save",
        type=str,
        default=None,
        help="Path to save JSON metrics report",
    )
    args = parser.parse_args()

    if args.repeat > 1:
        rates = []
        gen_dang_rates = []
        safety_catch_rates = []
        refused_rates = []
        last_metrics = None
        for i in range(args.repeat):
            print(f"\n--- Repeat {i+1}/{args.repeat} ---")
            m = run_redteam(split_filter=args.split, with_llm=args.with_llm)
            rates.append(m["catch_rate_percent"])
            last_metrics = m
            if m.get("llm_metrics"):
                lm = m["llm_metrics"]
                gen_dang_rates.append(lm["generated_dangerous_percent"])
                safety_catch_rates.append(lm["safety_layer_caught_dangerous_percent"])
                refused_rates.append(lm["model_refused_or_safe_percent"])

        mean_rate = sum(rates) / len(rates)
        min_rate = min(rates)
        max_rate = max(rates)
        print("\n" + "=" * 70)
        print(f"REPEATED RUN SUMMARY ({args.repeat} RUNS)")
        print(f"Catch Rate: Mean = {mean_rate:.1f}%, Range = [{min_rate:.1f}% - {max_rate:.1f}%]")
        if gen_dang_rates:
            print(f"(a) Model Generated Dangerous: Mean = {sum(gen_dang_rates)/len(gen_dang_rates):.1f}%, Range = [{min(gen_dang_rates):.1f}% - {max(gen_dang_rates):.1f}%]")
            print(f"(b) Caught by Safety Layer:    Mean = {sum(safety_catch_rates)/len(safety_catch_rates):.1f}%, Range = [{min(safety_catch_rates):.1f}% - {max(safety_catch_rates):.1f}%]")
            print(f"(c) Model Refused / Safe:       Mean = {sum(refused_rates)/len(refused_rates):.1f}%, Range = [{min(refused_rates):.1f}% - {max(refused_rates):.1f}%]")
        print("=" * 70)

        if args.save and last_metrics:
            save_path = args.save
            os.makedirs(os.path.dirname(os.path.abspath(save_path)), exist_ok=True)
            with open(save_path, "w", encoding="utf-8") as f:
                json.dump({
                    "repeated_runs": args.repeat,
                    "mean_catch_rate": round(mean_rate, 2),
                    "min_catch_rate": round(min_rate, 2),
                    "max_catch_rate": round(max_rate, 2),
                    "rates": rates,
                    "last_metrics": last_metrics,
                }, f, indent=2)
            print(f"Results saved to {save_path}")
    else:
        metrics = run_redteam(split_filter=args.split, with_llm=args.with_llm)
        print_report(metrics)

        if args.save:
            save_path = args.save
            os.makedirs(os.path.dirname(os.path.abspath(save_path)), exist_ok=True)
            with open(save_path, "w", encoding="utf-8") as f:
                json.dump(metrics, f, indent=2)
            print(f"Results saved to {save_path}")


if __name__ == "__main__":
    main()
