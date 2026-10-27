import subprocess
from agent.result_validator import validate_result

tests = [
    ("show current date and time", "Get-Date"),
    ("what is my current username", "whoami"),
    ("get current working directory path", "Get-Location"),
    ("show running processes", "Get-Process"),
    ("show all services on this computer", "Get-Service"),
    ("show my IP configuration", "Get-NetIPConfiguration"),
    ("show network adapters", "Get-NetAdapter"),
]

for p, cmd in tests:
    res = subprocess.run(["powershell", "-NoProfile", "-Command", cmd], capture_output=True, text=True)
    val = validate_result(p, cmd, res.stdout, res.stderr, res.returncode)
    print(f"Prompt: {p}")
    print(f"Cmd: {cmd} | Exit: {res.returncode}")
    print(f"Stdout preview: {repr(res.stdout[:60])}")
    print(f"Valid: {val['valid']} | Quality: {val['quality']} | Reason: {val['reason']}")
    print("-" * 50)
