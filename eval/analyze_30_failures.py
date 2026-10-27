import json
import re

with open("eval/results/qwen2.5_3b_baseline.json", "r", encoding="utf-8") as f:
    data = json.load(f)

tasks_map = {t["id"]: t for t in [json.loads(line) for line in open("eval/tasks.jsonl", encoding="utf-8") if line.strip()]}

failures = [r for r in data["results"] if not r["final_success"]]

print(f"Total failures to categorize: {len(failures)}\n")

for r in failures:
    tid = r["id"]
    t = tasks_map.get(tid, {})
    cmd = r["command"]
    prompt = r["prompt"]
    ft = r["failure_type"]
    reason = r["check_reason"]
    check = t.get("success_check", {})
    
    print(f"ID: {tid} | Split: {r['split']} | Category: {r['category']}")
    print(f"  Prompt : {prompt}")
    print(f"  Command: {cmd}")
    print(f"  Exit   : {r['exit_code']} | Executed: {r['executed']}")
    print(f"  Check  : {check}")
    print(f"  Reason : {reason}")
    print()
