# WinCliAgent

A local AI-powered Windows CLI agent that converts natural-language requests into PowerShell commands, validates them, checks for destructive behavior, executes them with user approval, and evaluates output quality.

Built with **LangGraph + Ollama + Qwen 2.5:3B**.

---

## 🚀 Key Demos

### 1. Normal Execution Flow (Information Request)

```text
User: show my IP configuration

Agent:
  command : Get-NetIPConfiguration
  details : Displays network adapter IP configurations.

Run this command? [y/N] y

  exit    : 0

--- output ---
InterfaceAlias       : Wi-Fi
InterfaceIndex       : 16
InterfaceDescription : MediaTek Wi-Fi 6E MT7922 (RZ616) 160MHz PCIe Adapter
IPv4Address          : 10.22.2.207
IPv4DefaultGateway   : 10.22.0.1

  Result validation: PASS
```

### 2. Safety Interception (Destructive Command Blocked)

```text
User: delete all files in the current directory

Agent:
  command : Remove-Item -Path * -Recurse
  details : Deletes all files and subdirectories recursively.

  [BLOCKED] Potentially destructive command detected: remove-item
```
*(The command is intercepted by the safety screening layer and never executed).*

### 3. Agentic Self-Correction (Error Recovery & Retry)

```text
User: show disk usage

Agent Attempt 1:
  command : Get-PSDrive -PSProvider FileSystem | Measure-Object -Property Used -Sum
  details : Calculates total disk usage.

Run this command? [y/N] y

  exit    : 0

--- output ---
Count : 1
Sum   : 152063172608

  Result validation: FAILED
  reason  : Command completed but did not clearly provide useful disk usage information.

Retrying (attempt 2/2)...

Agent Attempt 2:
  command : Get-PSDrive -PSProvider FileSystem | Select-Object Name, Used, Free
  details : Displays used and free space for filesystem drives.

Run this command? [y/N] y

  exit    : 0

--- output ---
Name         Used         Free
----         ----         ----
C    150436229120  72236220416
D      1659539456 286697807872

  Result validation: PASS
```
*(The agent detects that Attempt 1 produced incomplete summary data, passes the failure context back to local Qwen, generates a better command, requires human re-approval, and achieves PASS).*

---

## ✨ Features

- **Natural Language ➔ PowerShell**: Converts free-form requests into valid PowerShell cmdlets.
- **100% Local LLM Inference**: Runs locally via Ollama (`qwen2.5:3b`) without requiring paid APIs or `OPENAI_API_KEY`.
- **LangGraph Agentic Architecture**: State graph pipeline managing command generation, validation, safety screening, human confirmation, execution, and semantic result evaluation.
- **Rule-Based Command Validator**: Validates cmdlet syntax and catches common object property hallucinations before execution.
- **Layered Safety Screening**: Intercepts destructive cmdlets (`Remove-Item`, `Stop-Process`, `format`, `shutdown`, etc.) and dangerous parameters (`-Force`, `-Recurse`, `/s`, `/q`).
- **Human-in-the-Loop Confirmation**: Pauses before execution to allow the user to review and approve/reject proposed commands.
- **Semantic Result Validator**: Verifies that execution stdout actually answers the user's intent rather than relying solely on `exit_code == 0`. Handles GUI commands (like `winver`) gracefully.
- **Error-Aware Auto-Recovery**: Feeds execution errors and validation failure reasons back to Qwen to attempt self-correction.
- **Duplicate Command Prevention**: Tracks `previous_commands` across retries to prevent repeating failed attempts.
- **Strict Retry Boundary (`MAX_RETRIES = 2`)**: Enforces a maximum retry limit of 2 to avoid infinite loops.
- **Structured Output**: LLM returns schema-validated JSON with fallback text parsing.
- **Comprehensive Unit & Integration Test Suite**: 34 automated tests covering all modules and graph state transitions.

---

## 📐 Architecture & Flow

```text
                  ┌──────────────────┐
                  │   User Request   │
                  └────────┬─────────┘
                           ↓
                  ┌──────────────────┐
                  │   Qwen 2.5:3B   │
                  │     (Ollama)     │
                  └────────┬─────────┘
                           ↓
                  ┌──────────────────┐
                  │ Command Validator│
                  └────────┬─────────┘
                           ↓
                  ┌──────────────────┐
                  │  Safety Checker  │
                  └────────┬─────────┘
                           ↓
                  ┌──────────────────┐
                  │ Human Confirmation│
                  └────────┬─────────┘
                           ↓
                  ┌──────────────────┐
                  │    PowerShell    │
                  │     Executor     │
                  └────────┬─────────┘
                           ↓
                  ┌──────────────────┐
                  │ Result Validator │
                  └────────┬─────────┘
                           ↓
                    ┌──────┴──────┐
                    │             │
                  PASS          FAIL
                    │             │
                    ↓             ↓
                   END       Retry ≤ 2
                                  │
                                  ↓
                              Qwen Again
```

---

## 🛠️ How It Works

1. **Command Generation**: Local Qwen model translates natural language requests into structured JSON containing the PowerShell command, explanation, and risk level.
2. **Command Validation**: Checks cmdlet correctness and filters out hallucinated parameters/properties.
3. **Safety Validation**: Blocks dangerous commands (`Remove-Item`, `Stop-Process`, `Stop-Service`, `Restart-Computer`, `shutdown`, `format`, `clear-content`, `del`, `erase`, `rmdir`) and dangerous parameters (`-Force`, `-Recurse`, `/s`, `/q`, `-Confirm:$false`).
4. **Human Confirmation**: Prompts `Run this command? [y/N]` before execution. Automated `--auto` mode is available for trusted testing.
5. **PowerShell Execution**: Executes the command using native PowerShell (`pwsh` / `powershell`) and captures stdout, stderr, and return exit codes.
6. **Semantic Result Validation**: Evaluates the output for quality and relevance (e.g. verifying disk usage outputs display drive names, used space, and free space). Recognizes legitimate GUI app launches (`winver`).
7. **Error Recovery & Retry**: When validation or execution fails, feeds the original request, failed command, exit code, stdout, stderr, and failure reason back to Qwen to generate a different command. Enforces `MAX_RETRIES = 2`.

---

## 📁 Project Structure

```text
WinCliAgent/
│
├── agent/
│   ├── __init__.py
│   ├── executor.py         # PowerShell process execution & output capture
│   ├── graph.py            # LangGraph workflow wiring & checkpointing
│   ├── llm.py              # ChatOllama interface & structured JSON parser
│   ├── nodes.py            # LangGraph state nodes & routing logic
│   ├── result_validator.py # Semantic output quality & relevance validator
│   ├── safety.py           # Destructive cmdlet & parameter safety screen
│   ├── state.py            # TypedDict AgentState definition
│   └── validator.py        # Rule-based command pre-validation
│
├── tests/
│   ├── __init__.py
│   ├── test_agent.py            # Integration tests for agent graph flow
│   ├── test_executor.py         # PowerShell execution unit tests
│   ├── test_llm.py              # LLM response parser unit tests
│   ├── test_result_validator.py # Semantic result validation unit tests
│   ├── test_safety.py           # Safety screening unit tests
│   └── test_validator.py        # Pre-execution command validator unit tests
│
├── .env.example
├── .gitignore
├── Dockerfile
├── docker-compose.yml
├── main.py                 # CLI entry point & interactive REPL
├── README.md
└── requirements.txt
```

---

## ⚡ Setup & Installation

### Prerequisites
- Windows OS
- Python 3.10+
- PowerShell
- Ollama (`ollama pull qwen2.5:3b`)

### Quickstart

1. **Clone the repository**:
   ```powershell
   git clone https://github.com/YOUR_USERNAME/WinCliAgent.git
   cd WinCliAgent
   ```

2. **Set up virtual environment**:
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

3. **Install dependencies**:
   ```powershell
   pip install -r requirements.txt
   ```

4. **Prepare Ollama & Qwen**:
   ```powershell
   ollama pull qwen2.5:3b
   ```

5. **Configure `.env`**:
   ```powershell
   Copy-Item .env.example .env
   ```
   *(Ensure `OLLAMA_MODEL=qwen2.5:3b` is set in `.env`)*

---

## 💻 Running the Agent

### Single Command Mode
```powershell
python main.py "show my IP configuration"
```

### Interactive REPL Mode
```powershell
python main.py
```
```text
WinCliAgent — type a request, or 'exit' to quit.

> show my IP configuration
> show disk usage
> list Python files
> show running processes
> exit
```

### Automated Mode (Bypass Confirmation Prompt)
```powershell
python main.py --auto "show my IP configuration"
```
*Note: Use `--auto` only for trusted, read-only testing.*

---

## 🧪 Testing

Run the full automated test suite:
```powershell
python -m unittest discover tests
```

**Verification Output**:
```text
..................................
----------------------------------------------------------------------
Ran 34 tests in 7.518s

OK
```

---

## 🛡️ Safety Model

WinCliAgent enforces multi-layer defensive screening:

```text
Generated Command ➔ Pre-Validation ➔ Risk Classification ➔ Destructive Interception ➔ Human Confirmation ➔ PowerShell Execution ➔ Result Validation
```

- **Read-Only Commands**: Proceed after human confirmation.
- **Destructive Commands**: Automatically blocked before execution.
- **Retries**: Every retry command passes through safety screening and requires human re-approval.

*Disclaimer: WinCliAgent is designed for local development and learning purposes.*

---

## 📊 Current Limitations

- **GUI Window Interactivity**: Commands launching external GUI applications (such as `winver`) exit with code `0`. The agent accurately verifies GUI execution but cannot inspect visual content rendered inside external Windows frames.
- **Heuristic Relevance Matching**: Administrative tasks have strong concept rules. Unseen domain requests rely on deterministic keyword relevance matching.
- **Local Model Scope**: `qwen2.5:3b` is lightweight for local execution; complex multi-stage PowerShell pipelines may occasionally trigger a retry attempt.

---

## 🧰 Tech Stack

- **Python 3.14**
- **LangGraph** (StateGraph, Checkpointing, MemorySaver)
- **LangChain Core & LangChain Ollama**
- **Ollama + Qwen 2.5:3B**
- **Windows PowerShell**
- **unittest**

---

## 📜 License

MIT License.
