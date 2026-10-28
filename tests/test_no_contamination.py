"""Contamination check test suite.

Ensures few-shot examples do not duplicate or closely match any dev task,
reference command, held-out task, or red-team case across all evaluation files.
Runs hermetically without logging or printing held-out contents.
"""

from __future__ import annotations

import json
import os
import re
import unittest
from typing import Any

# Import few-shot examples from agent.few_shots
try:
    from agent.few_shots import FEW_SHOT_EXAMPLES
except ImportError:
    FEW_SHOT_EXAMPLES = []


EVAL_FILES = [
    "eval/tasks.jsonl",
    "eval/tasks_heldout_v2.jsonl",
    "eval/redteam_heldout_v3.jsonl",
    "tests/redteam/cases.jsonl",
    "tests/redteam/benign.jsonl",
]


def _normalize_text(text: str) -> str:
    """Normalize text for semantic similarity checks."""
    cleaned = text.lower()
    cleaned = re.sub(r"[^a-z0-9\s]", " ", cleaned)
    return " ".join(cleaned.split())


def _extract_intent_keywords(text: str) -> set[str]:
    """Extract significant keywords from intent text."""
    stop_words = {
        "the", "a", "an", "in", "on", "of", "to", "for", "with", "all", "and", "or",
        "by", "is", "are", "from", "my", "this", "that", "it", "at", "as", "using",
        "please", "can", "you", "me", "show", "get", "list", "find", "display"
    }
    words = _normalize_text(text).split()
    return {w for w in words if len(w) > 2 and w not in stop_words}


def _extract_cmdlets_and_params(cmd: str) -> tuple[set[str], set[str]]:
    """Extract cmdlets and parameter flags from a command."""
    tokens = cmd.strip().split()
    cmdlets = set()
    params = set()
    for t in tokens:
        clean_t = t.strip("()`{}[]|,;").lower()
        if clean_t.startswith("-") and len(clean_t) > 1:
            params.add(clean_t.split(":")[0])
        elif "-" in clean_t and not clean_t.startswith("$"):
            cmdlets.add(clean_t)
        elif clean_t in {"dir", "ls", "gci", "cat", "gc", "type", "del", "rm", "rmdir", "ipconfig", "ping", "whoami", "hostname"}:
            cmdlets.add(clean_t)
    return cmdlets, params


def _load_benchmark_items() -> list[dict[str, Any]]:
    """Load all items from dev and held-out files for contamination checking."""
    items = []
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    for rel_path in EVAL_FILES:
        full_path = os.path.join(base_dir, rel_path)
        if not os.path.exists(full_path):
            continue
        with open(full_path, "r", encoding="utf-8") as f:
            for line_idx, line in enumerate(f, 1):
                line_str = line.strip()
                if not line_str or line_str.startswith("#"):
                    continue
                try:
                    data = json.loads(line_str)
                    cmd = (
                        data.get("command")
                        or data.get("reference_command")
                        or (data.get("text") if data.get("input_type") == "command" else "")
                        or ""
                    )
                    items.append({
                        "file": rel_path,
                        "line": line_idx,
                        "id": data.get("id", f"{rel_path}:{line_idx}"),
                        "prompt": data.get("prompt") or data.get("text") or "",
                        "command": cmd,
                    })
                except Exception:
                    pass

    # Also include reference commands from baseline dev results if present
    baseline_path = os.path.join(base_dir, "eval/results/qwen2.5_3b_baseline.json")
    if os.path.exists(baseline_path):
        try:
            with open(baseline_path, "r", encoding="utf-8") as bf:
                b_data = json.load(bf)
            for r in b_data.get("results", []):
                items.append({
                    "file": "eval/results/qwen2.5_3b_baseline.json",
                    "line": 0,
                    "id": r.get("id", "baseline_ref"),
                    "prompt": r.get("prompt", ""),
                    "command": r.get("command", ""),
                })
        except Exception:
            pass

    return items


def check_example_against_items(example: dict[str, str], benchmark_items: list[dict[str, Any]]) -> list[str]:
    """Check a single few-shot example for contamination against all benchmark items.

    Returns:
        List of failure messages (redacted identifiers only, no held-out text printed).
    """
    ex_prompt = example.get("prompt", "")
    ex_cmd = example.get("command", "")

    ex_norm_prompt = _normalize_text(ex_prompt)
    ex_norm_cmd = _normalize_text(ex_cmd)
    ex_keywords = _extract_intent_keywords(ex_prompt)
    ex_cmdlets, ex_params = _extract_cmdlets_and_params(ex_cmd)

    violations = []

    for item in benchmark_items:
        target_id = item["id"]
        target_file = item["file"]
        target_prompt = item["prompt"]
        target_cmd = item["command"]

        target_norm_prompt = _normalize_text(target_prompt)
        target_norm_cmd = _normalize_text(target_cmd)

        # 1. Exact or near-exact prompt match
        if ex_norm_prompt and target_norm_prompt:
            if ex_norm_prompt == target_norm_prompt:
                violations.append(f"Prompt exact match against {target_file}:{target_id}")
                continue

        # 2. Exact or near-exact command match
        if ex_norm_cmd and target_norm_cmd:
            if ex_norm_cmd == target_norm_cmd:
                violations.append(f"Command exact match against {target_file}:{target_id}")
                continue

        # 3. High keyword overlap (Jaccard similarity > 0.65 on significant intent keywords)
        target_keywords = _extract_intent_keywords(target_prompt)
        if ex_keywords and target_keywords:
            common = ex_keywords.intersection(target_keywords)
            union = ex_keywords.union(target_keywords)
            jaccard = len(common) / len(union) if union else 0.0
            if jaccard > 0.65:
                violations.append(f"Prompt high intent similarity (Jaccard={jaccard:.2f}) against {target_file}:{target_id}")
                continue

        # 4. Same primary cmdlet + identical parameter set
        if target_cmd:
            t_cmdlets, t_params = _extract_cmdlets_and_params(target_cmd)
            if ex_cmdlets and t_cmdlets and (ex_cmdlets == t_cmdlets):
                if ex_params and t_params and (ex_params == t_params):
                    violations.append(f"Identical cmdlet & parameter signature ({ex_cmdlets}, {ex_params}) against {target_file}:{target_id}")
                    continue

    return violations


class TestNoContamination(unittest.TestCase):
    """Hermetic unit tests verifying zero contamination in few-shot examples."""

    def setUp(self):
        self.benchmark_items = _load_benchmark_items()

    def test_empty_set_passes(self):
        """Empty few-shot set must pass without any violations."""
        violations = []
        for ex in []:
            violations.extend(check_example_against_items(ex, self.benchmark_items))
        self.assertEqual(violations, [])

    def test_detector_catches_synthetic_contamination(self):
        """Verify the test detector correctly flags identical or high-overlap examples."""
        # Synthetic exact prompt match
        fake_exact = {"prompt": "list all files in the current directory", "command": "Get-Item *"}
        v1 = check_example_against_items(fake_exact, self.benchmark_items)
        self.assertTrue(len(v1) > 0, "Detector failed to catch exact prompt duplication.")

        # Synthetic exact command match
        fake_cmd = {"prompt": "do something completely random", "command": "Get-ChildItem -File"}
        v2 = check_example_against_items(fake_cmd, self.benchmark_items)
        self.assertTrue(len(v2) > 0, "Detector failed to catch exact command duplication.")

        # Synthetic identical cmdlet + parameter signature match
        fake_sig = {"prompt": "unrelated intent", "command": "Get-ChildItem -Recurse"}
        v3 = check_example_against_items(fake_sig, self.benchmark_items)
        self.assertTrue(len(v3) > 0, "Detector failed to catch identical cmdlet + parameter set.")

    def test_registered_few_shot_examples_have_zero_contamination(self):
        """Active few-shot examples must have ZERO matches across all eval and held-out sets."""
        all_violations = []
        for idx, ex in enumerate(FEW_SHOT_EXAMPLES, 1):
            violations = check_example_against_items(ex, self.benchmark_items)
            for v in violations:
                all_violations.append(f"Example #{idx} '{ex.get('prompt', '')[:30]}...': {v}")

        self.assertEqual(all_violations, [], f"Contamination detected in few-shot examples:\n" + "\n".join(all_violations))


if __name__ == "__main__":
    unittest.main()
