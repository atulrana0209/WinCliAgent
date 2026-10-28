# WinCliAgent

[![CI](https://github.com/atulrana0209/WinCliAgent/actions/workflows/ci.yml/badge.svg)](https://github.com/atulrana0209/WinCliAgent/actions/workflows/ci.yml)

A local AI-powered Windows CLI agent that converts natural-language requests into PowerShell commands, normalizes syntax, evaluates 4-tier risk levels, enforces process execution timeouts, requires human confirmation, records audit logs, and validates result quality.

Built with **LangGraph + Ollama + Qwen 2.5:3B**.

---

## 🚀 Key Demos

### 1. 4-Tier Risk Assessment & Information Request (Low Risk)

```text
User: show my IP configuration

Agent:
  command : Get-NetIPConfiguration
  details : Displays network adapter IP configurations.
  Risk    : LOW
  Action  : ALLOWED

Run this command? [y/N] y

  exit    : 0

--- output ---
InterfaceAlias       : Wi-Fi
IPv4Address          : 192.0.2.100
IPv4DefaultGateway   : 192.0.2.1

  Result validation: PASS
```

### 2. Safety Interception (Critical/High Risk Blocked)

```text
User: delete all files in the current directory

Agent:
  command : Remove-Item -Path * -Recurse
  details : Deletes all files and subdirectories recursively.
  Risk    : CRITICAL
  Action  : BLOCKED

  [BLOCKED] Critical risk system/destructive operation: Remove-Item -Path * -Recurse
```
*(The command is intercepted by the safety screening layer and never executed).*

### 3. Agentic Self-Correction & Audit Log

```text
User: show disk usage

Agent Attempt 1:
  command : Get-PSDrive -PSProvider FileSystem | Measure-Object -Property Used -Sum
  Risk    : LOW
  Action  : ALLOWED

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
  Risk    : LOW
  Action  : ALLOWED

Run this command? [y/N] y

  exit    : 0

--- output ---
Name         Used         Free
----         ----         ----
C    150436229120  72236220416
D      1659539456 286697807872

  Result validation: PASS
```

---

## ✨ Advanced Features

- **4-Tier Risk Engine**: Classifies commands into `LOW` (read-only), `MEDIUM` (modifications), `HIGH` (dangerous cmdlets/parameters), and `CRITICAL` (destructive system operations).
- **Process Execution Timeout (`10s`)**: Enforces a strict 10-second timeout on PowerShell process execution to prevent hanging pipelines.
- **Structured Audit Logging (`logs/agent.log`)**: Records ISO timestamped JSON log entries capturing user prompts, generated commands, risk levels, human approval, exit code, validation status, and retry counts.
- **Command Alias Normalization**: Automatically converts PowerShell aliases (`gci`, `dir`, `ls`, `gps`, `ps`, `rm`, `del`, `cd`, `pwd`, etc.) to canonical cmdlet names before evaluation.
- **Dry-Run Mode (`--dry-run`)**: Translates and screens requests with risk assessment without executing commands.
- **Explain Mode (`--explain`)**: Displays generated command, explanation, and risk assessment without executing.
- **Verbose Workflow Logging (`--verbose`)**: Prints detailed step-by-step pipeline execution logs (`[GENERATE]`, `[VALIDATE]`, `[SAFETY]`, `[EXECUTE]`, `[RESULT]`).
- **Interactive History Commands**: Supports `> history` (view past runs) and `> history <N>` (inspect detailed execution record for item N).
- **100% Local Inference**: Runs locally via Ollama (`qwen2.5:3b`) without requiring paid APIs or `OPENAI_API_KEY`.
- **Duplicate Command Prevention**: Tracks `previous_commands` across retries to prevent repeating failed attempts.
- **Strict Retry Boundary (`MAX_RETRIES = 2`)**: Enforces a maximum retry limit of 2 to avoid infinite loops.
- **Automated Test Suite**: 40 automated unit and integration tests covering risk classification, normalizers, audit logs, timeouts, and graph state transitions.

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
                  │ Alias Normalizer │
                  └────────┬─────────┘
                           ↓
                  ┌──────────────────┐
                  │ 4-Tier Risk &    │
                  │ Safety Checker   │
                  └────────┬─────────┘
                           ↓
                  ┌──────────────────┐
                  │ Human Confirmation│
                  └────────┬─────────┘
                           ↓
                  ┌──────────────────┐
                  │ PowerShell Exec  │
                  │ (10s Timeout)    │
                  └────────┬─────────┘
                           ↓
                  ┌──────────────────┐
                  │ Result Validator │
                  └────────┬─────────┘
                           ↓
                  ┌──────────────────┐
                  │ Audit Logger     │
                  │ (logs/agent.log) │
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

## 📁 Project Structure

```text
WinCliAgent/
│
├── agent/
│   ├── __init__.py
│   ├── executor.py         # PowerShell process execution & 10s timeout control
│   ├── graph.py            # LangGraph workflow wiring & checkpointing
│   ├── llm.py              # ChatOllama interface & structured JSON parser
│   ├── logger.py           # Structured JSON audit log recorder (logs/agent.log)
│   ├── nodes.py            # LangGraph state nodes & routing logic
│   ├── normalizer.py       # Alias normalization & AST-like command parsing
│   ├── result_validator.py # Semantic output quality & relevance validator
│   ├── safety.py           # 4-tier risk classification & safety screening
│   ├── state.py            # TypedDict AgentState definition
│   └── validator.py        # Rule-based command pre-validation
│
├── logs/
│   └── agent.log           # JSON Lines audit log file
│
├── tests/
│   ├── __init__.py
│   ├── test_agent.py            # Integration tests for agent graph flow
│   ├── test_executor.py         # PowerShell execution & timeout unit tests
│   ├── test_features.py         # Risk tiers, normalizer & audit log unit tests
│   ├── test_llm.py              # LLM response parser unit tests
│   ├── test_result_validator.py # Semantic result validation unit tests
│   ├── test_safety.py           # 4-tier safety screening unit tests
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

---

## 💻 Running the Agent

### Command Modes & CLI Flags

- **Standard Execution**:
  ```powershell
  python main.py "show my IP configuration"
  ```
- **Dry-Run Mode** (Translate and screen without executing):
  ```powershell
  python main.py --dry-run "show my IP configuration"
  ```
- **Explain Mode** (Display command, explanation, and risk without executing):
  ```powershell
  python main.py --explain "show my IP configuration"
  ```
- **Verbose Mode** (Detailed step-by-step workflow logs):
  ```powershell
  python main.py --verbose "show my IP configuration"
  ```
- **Automated Mode** (Bypass confirmation prompt for read-only testing):
  ```powershell
  python main.py --auto "show my IP configuration"
  ```

### Interactive REPL Mode
```powershell
python main.py
```
```text
WinCliAgent — type a request, 'history' to view past runs, or 'exit' to quit.

> show my IP configuration
> show disk usage
> history
> history 1
> exit
```

---

## 🧪 Testing

The test suite is structured into three clear tiers for reliability and CI speed:

1. **Hermetic Tests (Default CI Suite)**:
   - Completely offline with mocked LLM and mocked executor. Runs in under 15 seconds.
   - Run command:
     ```powershell
     python -m unittest discover tests
     ```
   - **Verification**: 99 hermetic tests passing (6 skipped host-dependent / live tests).

2. **Host-Dependent Tests (Live Windows / PowerShell)**:
   - Validates live subprocess invocation, timeout termination (code 124), and output stream truncation (> 100 KB).
   - Run command:
     ```powershell
     $env:RUN_HOST_TESTS="1"; python -m unittest discover tests; Remove-Item Env:\RUN_HOST_TESTS
     ```
   - **Count**: 4 tests in `tests/test_executor.py`.

3. **Live-LLM Integration Tests (Live Ollama)**:
   - Validates end-to-end inference and safety checks against a running Ollama daemon.
   - Run command:
     ```powershell
     $env:RUN_INTEGRATION_TESTS="1"; python -m unittest discover tests; Remove-Item Env:\RUN_INTEGRATION_TESTS
     ```
   - **Count**: 2 tests in `tests/test_integration.py`.

**Total Test Count**: 105 tests across 14 test modules (99 hermetic, 4 host-dependent, 2 live-LLM).

---

## 🛡️ Risk & Safety Model

| Risk Level | Target Commands & Operations | Default Action |
| :--- | :--- | :--- |
| **LOW** | Read-only cmdlets (`Get-ChildItem`, `Get-Process`, `Get-NetIPConfiguration`, `pwd`, `ipconfig`) | `ALLOWED` (Requires Human Confirmation) |
| **MEDIUM** | Operational modifications (`Start-Process`, `Set-Location`, `New-Item`, `Copy-Item`) | `ALLOWED` (Requires Human Confirmation) |
| **HIGH** | Potentially destructive cmdlets (`Remove-Item`, `Stop-Process`, `Stop-Service`, `Restart-Computer`) | `BLOCKED` (Intercepted by Safety Layer) |
| **CRITICAL** | Destructive system operations (`Format-Volume`, `Clear-Disk`, `Diskpart`, `Remove-Item * -Recurse`) | `BLOCKED` (Intercepted by Safety Layer) |

---

## 📜 Audit Logging

Every execution or dry-run event is appended as a JSON record to `logs/agent.log`:

```json
{
  "timestamp": "2026-08-03T08:02:24.978095+00:00",
  "user_prompt": "show my IP configuration",
  "generated_command": "Get-NetIPConfiguration",
  "risk": "LOW",
  "action": "ALLOWED",
  "approved": true,
  "exit_code": 0,
  "validation": "PASS",
  "retry_count": 0
}
```

---

## 🔬 Model Comparison: `qwen2.5:3b` vs `qwen2.5:1.5b`

Evaluated on the 65-task development benchmark under identical conditions (LLM-only mode without deterministic templates, temperature = 0.0, seed = 42, `num_thread = 8`, AMD Ryzen 16 logical cores, Windows 11):

| Metric | `qwen2.5:3b` | `qwen2.5:1.5b` | Delta |
| :--- | :--- | :--- | :--- |
| **Final Success Rate** | **86.15%** (56/65) | **78.46%** (50/65) | -7.69% |
| **Wilson 95% Confidence Interval** | [75.73% – 92.54%] | [67.03% – 86.71%] | — |
| **First-Attempt Success Rate** | 81.54% (53/65) | 75.38% (49/65) | -6.16% |
| **Average Retries per Task** | 0.11 | 0.11 | 0.00 |
| **Avg Total Latency** | **6.82s** | **24.86s** | +18.04s |
| **Avg LLM Generation Latency** | 3.13s | 21.39s | +18.26s |
| **Avg Execution Latency** | 1.29s | 1.24s | -0.05s |
| **Peak Ollama Host RAM** | **2225.38 MB** | **1470.38 MB** | **-755.00 MB (-33.9%)** |
| **Average Ollama Host RAM** | 2224.46 MB | 1396.74 MB | -827.72 MB (-37.2%) |
| **Model Size on Disk** | 1.9 GB | 986 MB | **-914 MB (-48.1%)** |
| **Parameter Count / Quantization** | 3.1B / Q4_K_M | 1.5B / Q4_K_M | — |
| **JSON Schema Validation Failure Rate** | 0.0% (0/65) | 1.54% (1/65) | +1.54% |

### Paired Task Flips

- **Tasks 3B Solves but 1.5B Fails (11)**: `TASK-15`, `TASK-23`, `TASK-24`, `TASK-25`, `TASK-32`, `TASK-39`, `TASK-51`, `TASK-53`, `TASK-55`, `TASK-60`, `TASK-61`
- **Tasks 1.5B Solves but 3B Fails (6)**: `TASK-17`, `TASK-18`, `TASK-22`, `TASK-35`, `TASK-36`, `TASK-37`

### Conclusion: Trade-Off Analysis on Low-Resource Hardware

While `qwen2.5:1.5b` achieves significant resource reductions—slashing disk footprint by 48.1% (986 MB vs 1.9 GB) and peak host memory by 33.9% (1,470 MB vs 2,225 MB)—it is **not** currently recommended as an unconditional drop-in replacement for `qwen2.5:3b`. Accuracy drops by 7.69 percentage points (78.46% vs 86.15%), but the more critical defect is generation stability: on complex filtering tasks (e.g. `TASK-12`), 1.5B is prone to repetitive token loops that skew average latency to 24.86s (vs 6.82s for 3B) until hitting Ollama token repeat limits. However, for severely memory-constrained devices with < 8 GB RAM where 3B cannot fit alongside user workloads, 1.5B remains viable when combined with the Step 4.3 deterministic command templates (which intercept common queries in ~15 ms and reduce exposure to repetition bugs).

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
