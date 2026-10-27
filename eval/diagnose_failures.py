import json

with open("eval/results/qwen2.5_3b_baseline.json", "r", encoding="utf-8") as f:
    data = json.load(f)

tasks_map = {t["id"]: t for t in [json.loads(line) for line in open("eval/tasks.jsonl", encoding="utf-8") if line.strip()]}

results = data["results"]
failures = [r for r in results if not r["final_success"]]

print(f"Total Failures: {len(failures)} / {len(results)}\n")

for idx, r in enumerate(failures, 1):
    task_id = r["id"]
    task = tasks_map.get(task_id, {})
    check = task.get("success_check", {})
    print(f"[{idx}] {task_id} | Category: {r['category']} | Difficulty: {r['difficulty']}")
    print(f"    Prompt   : {r['prompt']}")
    print(f"    Command  : {r['command']}")
    print(f"    Fail Type: {r['failure_type']}")
    print(f"    Check    : {check}")
    print(f"    Reason   : {r['check_reason']}")
    print("-" * 70)
