"""Evaluation harness for WinCliAgent.

Runs tasks through the full LangGraph pipeline in an isolated temporary
directory sandbox with deterministic ground-truth verification.
"""

from __future__ import annotations

import argparse
import datetime
import json
import os
import platform
import subprocess
import tempfile
import time
from collections import defaultdict
from typing import Any, Optional

import psutil

from agent.graph import build_graph, new_thread_config
from agent.safety import classify_risk_tier
from eval.fixture import create_deterministic_fixture
from eval.ground_truth import verify_success

TASKS_FILE = os.path.join(os.path.dirname(__file__), "tasks.jsonl")
RESULTS_DIR = os.path.join(os.path.dirname(__file__), "results")


def get_git_commit_hash() -> str:
    """Retrieve current git commit hash."""
    try:
        res = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            check=False,
        )
        return res.stdout.strip() or "unknown"
    except Exception:
        return "unknown"


def get_ollama_process_memory_mb() -> float:
    """Sum the Resident Set Size (RSS) memory in MB of all Ollama processes."""
    total_mb = 0.0
    for p in psutil.process_iter(["name", "memory_info"]):
        try:
            name = (p.info["name"] or "").lower()
            if "ollama" in name:
                rss = p.info["memory_info"].rss
                total_mb += rss / (1024 * 1024)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return round(total_mb, 2)


def get_ollama_version() -> str:
    """Retrieve installed Ollama version string."""
    try:
        res = subprocess.run(
            ["ollama", "--version"],
            capture_output=True,
            text=True,
            check=False,
        )
        return res.stdout.strip() or "unknown"
    except Exception:
        return "unknown"


def get_system_hardware_info() -> dict[str, Any]:
    """Capture hardware specifications for benchmark reproducibility."""
    mem = psutil.virtual_memory()
    return {
        "os": f"{platform.system()} {platform.release()} ({platform.version()})",
        "cpu": platform.processor() or platform.machine(),
        "cpu_count_logical": psutil.cpu_count(logical=True),
        "cpu_count_physical": psutil.cpu_count(logical=False),
        "total_ram_gb": round(mem.total / (1024**3), 2),
        "available_ram_gb": round(mem.available / (1024**3), 2),
        "gpu": "None (Low-resource CPU execution)",
        "python_version": platform.python_version(),
    }


def load_tasks(
    filepath: str = TASKS_FILE,
    split_filter: Optional[str] = None,
    category_filter: Optional[str] = None,
    difficulty_filter: Optional[str] = None,
    limit: Optional[int] = None,
) -> list[dict[str, Any]]:
    """Load and filter evaluation tasks."""
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Tasks file not found: {filepath}")

    tasks = []
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            line_str = line.strip()
            if line_str and not line_str.startswith("#"):
                tasks.append(json.loads(line_str))

    if split_filter and split_filter != "all":
        tasks = [t for t in tasks if t.get("split") == split_filter]

    if category_filter:
        tasks = [t for t in tasks if t.get("category") == category_filter]

    if difficulty_filter:
        tasks = [t for t in tasks if t.get("difficulty") == difficulty_filter]

    if limit:
        tasks = tasks[:limit]

    return tasks


def run_single_task(
    task: dict[str, Any],
    graph: Any,
    is_cold_start: bool = False,
) -> dict[str, Any]:
    """Execute a single evaluation task in an isolated temporary sandbox."""
    t0_total = time.perf_counter()

    # Pre-execution Ollama RAM
    ram_before = get_ollama_process_memory_mb()

    task_id = task["id"]
    prompt = task["prompt"]
    expected_risk = task.get("expected_risk_tier", "LOW").upper()

    with tempfile.TemporaryDirectory() as sandbox_dir:
        # Build fresh deterministic fixture
        ground_truth = create_deterministic_fixture(sandbox_dir)

        config = new_thread_config()
        initial_input = {
            "prompt": prompt,
            "cwd": sandbox_dir,
            "auto": True,
        }

        # Step 1: Run graph up to interrupt_before=["execute"]
        t0_llm = time.perf_counter()
        graph.invoke(initial_input, config)
        llm_gen_time = time.perf_counter() - t0_llm

        state_before_exec = graph.get_state(config).values

        command = state_before_exec.get("command", "")
        actual_risk = state_before_exec.get("risk_level", "LOW").upper()
        is_valid = state_before_exec.get("is_valid", False)
        validation_reason = state_before_exec.get("validation_reason", "")

        # Execution policy: Auto-approve LOW and MEDIUM only. NEVER execute HIGH or CRITICAL.
        executed = False
        exec_time = 0.0
        stdout = ""
        stderr = ""
        exit_code: int | None = None
        retries = 0

        if actual_risk in ("HIGH", "CRITICAL") or expected_risk in ("HIGH", "CRITICAL"):
            # Policy enforcement: do not resume execution
            executed = False
            stdout = ""
            stderr = f"HARNESS_SAFETY: Refused execution of {actual_risk} command."
            exit_code = None
            final_state = state_before_exec
        elif not is_valid:
            executed = False
            stdout = ""
            stderr = f"Validation failed: {validation_reason}"
            exit_code = None
            final_state = state_before_exec
        else:
            # Approve and resume execution
            graph.update_state(config, {"approved": True})
            t0_exec = time.perf_counter()
            graph.invoke(None, config)
            exec_time = time.perf_counter() - t0_exec

            final_state = graph.get_state(config).values
            executed = final_state.get("executed", False)
            stdout = final_state.get("stdout", "")
            stderr = final_state.get("stderr", "")
            exit_code = final_state.get("exit_code")
            retries = final_state.get("retry_count", 0)

        total_time = time.perf_counter() - t0_total
        ram_after = get_ollama_process_memory_mb()
        peak_ram = max(ram_before, ram_after)

        # Ground truth independent verification
        is_success, check_reason = verify_success(
            task=task,
            stdout=stdout,
            stderr=stderr,
            exit_code=exit_code,
            actual_risk_tier=actual_risk,
            executed=executed,
            sandbox_dir=sandbox_dir,
            ground_truth=ground_truth,
        )

        risk_tier_correct = (actual_risk == expected_risk)

        # Failure Taxonomy Diagnosis
        failure_type = "none"
        if not is_success:
            if not is_valid:
                failure_type = "validator_false_reject" if "hallucination" not in validation_reason.lower() else "wrong_command"
            elif exit_code == 124:
                failure_type = "timeout"
            elif exit_code != 0 and exit_code is not None:
                failure_type = "syntax_error"
            elif not risk_tier_correct and expected_risk in ("HIGH", "CRITICAL"):
                failure_type = "wrong_risk_tier"
            else:
                failure_type = "wrong_command"

        return {
            "id": task_id,
            "category": task.get("category", "uncategorized"),
            "difficulty": task.get("difficulty", "medium"),
            "split": task.get("split", "dev"),
            "prompt": prompt,
            "command": command,
            "expected_risk_tier": expected_risk,
            "actual_risk_tier": actual_risk,
            "risk_tier_correct": risk_tier_correct,
            "executed": executed,
            "exit_code": exit_code,
            "first_attempt_success": is_success if retries == 0 else False,
            "final_success": is_success,
            "retries": retries,
            "llm_gen_time_s": round(llm_gen_time, 3),
            "exec_time_s": round(exec_time, 3),
            "total_time_s": round(total_time, 3),
            "is_cold_start": is_cold_start,
            "peak_ollama_ram_mb": peak_ram,
            "failure_type": failure_type,
            "check_reason": check_reason,
        }


def run_evaluation_suite(
    tasks: list[dict[str, Any]],
    model_name: str,
    incremental_file: Optional[str] = None,
    resume: bool = False,
) -> list[dict[str, Any]]:
    """Run full task suite and record incremental progress."""
    graph = build_graph()

    completed_ids = set()
    results = []

    if resume and incremental_file and os.path.exists(incremental_file):
        with open(incremental_file, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    r = json.loads(line)
                    results.append(r)
                    completed_ids.add(r["id"])
        print(f"Resuming evaluation: {len(completed_ids)} tasks already completed.")

    first_task = True
    for idx, task in enumerate(tasks, 1):
        if task["id"] in completed_ids:
            continue

        print(f"[{idx}/{len(tasks)}] {task['id']} ({task['category']}) - {task['prompt'][:45]}... ", end="", flush=True)

        res = run_single_task(task, graph, is_cold_start=first_task)
        first_task = False

        status_str = "PASS" if res["final_success"] else f"FAIL ({res['failure_type']})"
        print(f"[{status_str}] ({res['total_time_s']}s)")

        results.append(res)

        # Incremental write
        if incremental_file:
            os.makedirs(os.path.dirname(os.path.abspath(incremental_file)), exist_ok=True)
            with open(incremental_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(res) + "\n")

    return results


def aggregate_metrics(results: list[dict[str, Any]], model_name: str) -> dict[str, Any]:
    """Compute aggregate statistics and breakdowns."""
    total = len(results)
    if total == 0:
        return {}

    final_successes = sum(1 for r in results if r["final_success"])
    first_successes = sum(1 for r in results if r["first_attempt_success"])
    risk_correct = sum(1 for r in results if r["risk_tier_correct"])
    total_retries = sum(r["retries"] for r in results)

    llm_times = [r["llm_gen_time_s"] for r in results]
    exec_times = [r["exec_time_s"] for r in results]
    total_times = [r["total_time_s"] for r in results]

    cold_latencies = [r["total_time_s"] for r in results if r["is_cold_start"]]
    warm_latencies = [r["total_time_s"] for r in results if not r["is_cold_start"]]

    rams = [r["peak_ollama_ram_mb"] for r in results if r["peak_ollama_ram_mb"] > 0]

    # Breakdowns
    by_category = defaultdict(list)
    by_difficulty = defaultdict(list)
    by_split = defaultdict(list)
    failure_taxonomy = defaultdict(int)

    for r in results:
        by_category[r["category"]].append(r)
        by_difficulty[r["difficulty"]].append(r)
        by_split[r["split"]].append(r)
        if not r["final_success"]:
            failure_taxonomy[r["failure_type"]] += 1

    def _summarize_group(items: list[dict[str, Any]]) -> dict[str, Any]:
        n = len(items)
        succ = sum(1 for x in items if x["final_success"])
        return {
            "total": n,
            "success": succ,
            "success_rate": round(succ / n * 100, 1) if n > 0 else 0.0,
            "avg_latency_s": round(sum(x["total_time_s"] for x in items) / n, 2) if n > 0 else 0.0,
        }

    cat_breakdown = {k: _summarize_group(v) for k, v in by_category.items()}
    diff_breakdown = {k: _summarize_group(v) for k, v in by_difficulty.items()}
    split_breakdown = {k: _summarize_group(v) for k, v in by_split.items()}

    return {
        "model": model_name,
        "total_tasks": total,
        "first_attempt_success_rate": round(first_successes / total * 100, 2),
        "final_success_rate": round(final_successes / total * 100, 2),
        "risk_tier_accuracy": round(risk_correct / total * 100, 2),
        "average_retries": round(total_retries / total, 2),
        "avg_llm_latency_s": round(sum(llm_times) / total, 2),
        "avg_exec_latency_s": round(sum(exec_times) / total, 2),
        "avg_total_latency_s": round(sum(total_times) / total, 2),
        "cold_start_latency_s": round(cold_latencies[0], 2) if cold_latencies else 0.0,
        "avg_warm_latency_s": round(sum(warm_latencies) / len(warm_latencies), 2) if warm_latencies else 0.0,
        "peak_ollama_ram_mb": max(rams) if rams else 0.0,
        "avg_ollama_ram_mb": round(sum(rams) / len(rams), 2) if rams else 0.0,
        "by_category": cat_breakdown,
        "by_difficulty": diff_breakdown,
        "by_split": split_breakdown,
        "failure_taxonomy": dict(failure_taxonomy),
    }


def print_markdown_summary(metrics: dict[str, Any], hardware: dict[str, Any]) -> str:
    """Generate and display markdown summary table."""
    md = []
    md.append(f"# Benchmark Baseline Report: `{metrics['model']}`\n")
    md.append(f"- **Date**: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    md.append(f"- **OS**: {hardware['os']}")
    md.append(f"- **CPU**: {hardware['cpu']} ({hardware['cpu_count_logical']} logical cores)")
    md.append(f"- **RAM**: {hardware['total_ram_gb']} GB total ({hardware['available_ram_gb']} GB available)")
    md.append(f"- **Ollama Version**: {get_ollama_version()}")
    md.append(f"- **Git Commit**: `{get_git_commit_hash()}`\n")

    md.append("## Overall Performance Summary\n")
    md.append("| Metric | Value |")
    md.append("| :--- | :--- |")
    md.append(f"| **Final Task Success Rate** | **{metrics['final_success_rate']}%** ({int(metrics['final_success_rate']*metrics['total_tasks']/100)}/{metrics['total_tasks']}) |")
    md.append(f"| **First-Attempt Success Rate** | **{metrics['first_attempt_success_rate']}%** |")
    md.append(f"| **Risk-Tier Accuracy** | **{metrics['risk_tier_accuracy']}%** |")
    md.append(f"| **Average Retries per Task** | **{metrics['average_retries']}** |")
    md.append(f"| **Avg Latency per Task** | **{metrics['avg_total_latency_s']}s** (LLM: {metrics['avg_llm_latency_s']}s, Exec: {metrics['avg_exec_latency_s']}s) |")
    md.append(f"| **Cold-Start Latency** | **{metrics['cold_start_latency_s']}s** (Warm Avg: {metrics['avg_warm_latency_s']}s) |")
    md.append(f"| **Ollama Peak RAM** | **{metrics['peak_ollama_ram_mb']} MB** (Avg: {metrics['avg_ollama_ram_mb']} MB) |\n")

    md.append("## Dataset Split Performance\n")
    md.append("| Split | Total Tasks | Success Rate | Avg Latency |")
    md.append("| :--- | :--- | :--- | :--- |")
    for s_name, s_data in metrics["by_split"].items():
        md.append(f"| `{s_name}` | {s_data['total']} | **{s_data['success_rate']}%** | {s_data['avg_latency_s']}s |")
    md.append("")

    md.append("## Category Breakdown\n")
    md.append("| Category | Total | Success Rate | Avg Latency |")
    md.append("| :--- | :--- | :--- | :--- |")
    for cat_name, cat_data in metrics["by_category"].items():
        md.append(f"| `{cat_name}` | {cat_data['total']} | {cat_data['success_rate']}% | {cat_data['avg_latency_s']}s |")
    md.append("")

    md.append("## Difficulty Breakdown\n")
    md.append("| Difficulty | Total | Success Rate | Avg Latency |")
    md.append("| :--- | :--- | :--- | :--- |")
    for diff_name, diff_data in metrics["by_difficulty"].items():
        md.append(f"| `{diff_name}` | {diff_data['total']} | {diff_data['success_rate']}% | {diff_data['avg_latency_s']}s |")
    md.append("")

    md.append("## Failure Taxonomy\n")
    if metrics["failure_taxonomy"]:
        md.append("| Failure Category | Count |")
        md.append("| :--- | :--- |")
        for f_name, f_count in metrics["failure_taxonomy"].items():
            md.append(f"| `{f_name}` | {f_count} |")
    else:
        md.append("Zero task failures recorded.")
    md.append("\n")

    report_str = "\n".join(md)
    print(report_str)
    return report_str


def main() -> None:
    parser = argparse.ArgumentParser(description="WinCliAgent Task Evaluation Harness.")
    parser.add_argument("--model", type=str, default="qwen2.5:3b", help="Model name (default: qwen2.5:3b)")
    parser.add_argument("--split", choices=["dev", "held_out", "all"], default="all", help="Dataset split (default: all)")
    parser.add_argument("--category", type=str, default=None, help="Filter by category")
    parser.add_argument("--difficulty", choices=["easy", "medium", "hard"], default=None, help="Filter by difficulty")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of tasks")
    parser.add_argument("--repeat", type=int, default=1, help="Repetitions for mean/range reporting")
    parser.add_argument("--resume", action="store_true", help="Resume previous run from JSONL")
    parser.add_argument("--save", type=str, default=None, help="Custom output JSON path")
    args = parser.parse_args()

    os.environ["OLLAMA_MODEL"] = args.model

    hardware_info = get_system_hardware_info()
    tasks = load_tasks(
        split_filter=args.split,
        category_filter=args.category,
        difficulty_filter=args.difficulty,
        limit=args.limit,
    )

    clean_model_name = args.model.replace(":", "_").replace("/", "_")
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    os.makedirs(RESULTS_DIR, exist_ok=True)

    jsonl_file = os.path.join(RESULTS_DIR, f"{clean_model_name}_{timestamp}.jsonl")
    json_summary_file = args.save or os.path.join(RESULTS_DIR, f"{clean_model_name}_baseline.json")
    md_summary_file = os.path.join(RESULTS_DIR, f"{clean_model_name}_baseline.md")

    print(f"\n=======================================================")
    print(f"WINCLIAGENT EVALUATION HARNESS: {args.model}")
    print(f"Tasks: {len(tasks)} (Split: {args.split}) | Repetitions: {args.repeat}")
    print(f"Ollama Version: {get_ollama_version()} | Git: {get_git_commit_hash()}")
    print(f"=======================================================\n")

    if args.repeat > 1:
        repeat_success = []
        repeat_first_success = []
        repeat_latencies = []
        last_metrics = None

        for r_idx in range(args.repeat):
            print(f"\n>>> REPETITION {r_idx + 1}/{args.repeat} <<<")
            iter_jsonl = os.path.join(RESULTS_DIR, f"{clean_model_name}_rep{r_idx+1}_{timestamp}.jsonl")
            results = run_evaluation_suite(tasks, args.model, incremental_file=iter_jsonl)
            m = aggregate_metrics(results, args.model)
            repeat_success.append(m["final_success_rate"])
            repeat_first_success.append(m["first_attempt_success_rate"])
            repeat_latencies.append(m["avg_total_latency_s"])
            last_metrics = m

        mean_final = sum(repeat_success) / len(repeat_success)
        mean_first = sum(repeat_first_success) / len(repeat_first_success)
        mean_lat = sum(repeat_latencies) / len(repeat_latencies)

        print("\n" + "=" * 70)
        print(f"REPEATED EVALUATION SUMMARY ({args.repeat} RUNS)")
        print(f"Final Success Rate:  Mean = {mean_final:.1f}%, Range = [{min(repeat_success):.1f}% - {max(repeat_success):.1f}%]")
        print(f"First-Attempt Rate:  Mean = {mean_first:.1f}%, Range = [{min(repeat_first_success):.1f}% - {max(repeat_first_success):.1f}%]")
        print(f"Avg Latency per Task: Mean = {mean_lat:.2f}s, Range = [{min(repeat_latencies):.2f}s - {max(repeat_latencies):.2f}s]")
        print("=" * 70 + "\n")

        full_output = {
            "model": args.model,
            "repetitions": args.repeat,
            "mean_final_success_rate": round(mean_final, 2),
            "final_success_rates": repeat_success,
            "mean_first_attempt_rate": round(mean_first, 2),
            "first_attempt_rates": repeat_first_success,
            "mean_latency_s": round(mean_lat, 2),
            "latencies_s": repeat_latencies,
            "hardware": hardware_info,
            "last_run_metrics": last_metrics,
        }
        with open(json_summary_file, "w", encoding="utf-8") as f:
            json.dump(full_output, f, indent=2)
        print_markdown_summary(last_metrics, hardware_info)
    else:
        results = run_evaluation_suite(tasks, args.model, incremental_file=jsonl_file, resume=args.resume)
        metrics = aggregate_metrics(results, args.model)

        full_output = {
            "metadata": {
                "model": args.model,
                "timestamp": timestamp,
                "git_commit": get_git_commit_hash(),
                "ollama_version": get_ollama_version(),
                "hardware": hardware_info,
            },
            "metrics": metrics,
            "results": results,
        }

        with open(json_summary_file, "w", encoding="utf-8") as f:
            json.dump(full_output, f, indent=2)

        md_content = print_markdown_summary(metrics, hardware_info)
        with open(md_summary_file, "w", encoding="utf-8") as f:
            f.write(md_content)

        print(f"\nArtifacts saved:")
        print(f"  - Incremental log : {jsonl_file}")
        print(f"  - Summary JSON    : {json_summary_file}")
        print(f"  - Summary Markdown: {md_summary_file}")


if __name__ == "__main__":
    main()
