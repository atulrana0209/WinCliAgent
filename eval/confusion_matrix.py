import json
from collections import defaultdict

with open("eval/results/qwen2.5_3b_baseline.json", "r", encoding="utf-8") as f:
    data = json.load(f)

results = data["results"]
tiers = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
matrix = {exp: {act: 0 for act in tiers} for exp in tiers}

medium_landing_reasons = []

for r in results:
    exp = r.get("expected_risk_tier", "LOW").upper()
    act = r.get("actual_risk_tier", "LOW").upper()
    matrix[exp][act] += 1
    if exp == "LOW" and act == "MEDIUM":
        medium_landing_reasons.append({
            "id": r["id"],
            "prompt": r["prompt"],
            "command": r["command"],
        })

print("CONFUSION MATRIX (Rows: Expected, Columns: Actual)")
print(f"{'Expected \\ Actual':<20} | {'LOW':<8} | {'MEDIUM':<8} | {'HIGH':<8} | {'CRITICAL':<8} | {'Total':<6}")
print("-" * 72)
for exp in tiers:
    row = matrix[exp]
    tot = sum(row.values())
    print(f"{exp:<20} | {row['LOW']:<8} | {row['MEDIUM']:<8} | {row['HIGH']:<8} | {row['CRITICAL']:<8} | {tot:<6}")
print("-" * 72)

print(f"\nTotal Expected LOW landing on MEDIUM: {len(medium_landing_reasons)}")
for m in medium_landing_reasons:
    print(f"  [{m['id']}] Cmd: {m['command']} (Prompt: '{m['prompt']}')")
