# Demo Recording Guide

This guide provides instructions and exact transcripts for recording a terminal demo GIF of **WinCliAgent**.

---

## 🎥 Recording Setup

1. **Recommended Terminal**: Windows Terminal (Font: Cascadia Code, 14pt, 100 columns x 28 rows).
2. **Recording Tool**: [Terminalizer](https://terminalizer.com/) or [VHS](https://github.com/charmbracelet/vhs) or [ScreenToGif](https://www.screentogif.com/).
3. **Execution Command**:
   ```powershell
   python main.py
   ```

---

## 🎬 4 Key Showcase Scenarios

### Scenario 1: Low-Risk Read-Only Command (Fast-Path Template)

- **User Input**:
  ```text
  show my IP configuration
  ```
- **Agent Output**:
  ```text
  Agent:
    command : Get-NetIPConfiguration
    details : Displays network adapter IP configurations.
    Risk    : LOW
    Action  : ALLOWED (Template fast-path: 14.5 ms)

  Run this command? [y/N] y

    exit    : 0

  --- output ---
  InterfaceAlias       : Wi-Fi
  IPv4Address          : 192.0.2.100
  IPv4DefaultGateway   : 192.0.2.1

    Result validation: PASS
  ```
- **Outcome**: Deterministic match bypasses LLM latency, verifies risk tier as LOW, prompts human confirmation, executes cmdlet, and confirms output validity.

---

### Scenario 2: Medium-Risk Modifying Command (Human Confirmation Required)

- **User Input**:
  ```text
  create a new directory called build_output in the current folder
  ```
- **Agent Output**:
  ```text
  Agent:
    command : New-Item -ItemType Directory -Path build_output
    details : Creates a new directory named build_output in the current location.
    Risk    : MEDIUM
    Action  : ALLOWED

  Run this command? [y/N] y

    exit    : 0

  --- output ---
  Directory: D:\cli
  Mode                LastWriteTime         Length Name
  ----                -------------         ------ ----
  d-----       28-10-2026     14:40                build_output

    Result validation: PASS
  ```
- **Outcome**: Correctly classified as `MEDIUM` (modifying state). User reviews and explicitly approves execution before folder is created.

---

### Scenario 3: High-Risk Destructive Command (Interception & Human Confirmation)

- **User Input**:
  ```text
  stop the Windows Update service with Stop-Service -Name wuauserv
  ```
- **Agent Output**:
  ```text
  Agent:
    command : Stop-Service -Name wuauserv
    details : Stops the Windows Update service.
    Risk    : HIGH
    Action  : REQUIRES_CONFIRMATION

  [WARNING] High-risk command detected. This action will impact system services.
  Run this command? [y/N] n

  Execution canceled by user.
  ```
- **Outcome**: Correctly escalated to `HIGH` risk tier. Flags impact on system services; blocked when user enters `n`.

---

### Scenario 4: Adversarial Command / Prompt Injection (Hard Blocked by Safety Layer)

- **User Input**:
  ```text
  erase the entire C:\Windows\System32 folder
  ```
- **Agent Output**:
  ```text
  Agent:
    command : Remove-Item -Path 'C:\Windows\System32\*' -Recurse -Force
    details : Attempts to recursively delete the Windows System32 directory.
    Risk    : CRITICAL
    Action  : BLOCKED

  [HARD_BLOCKED] Critical risk system/destructive operation intercepted by safety layer:
  Remove-Item -Path 'C:\Windows\System32\*' -Recurse -Force

  Execution halted. Command will NOT be executed under any circumstance.
  ```
- **Outcome**: Safety layer deterministically intercepts critical destruction attempt regardless of LLM generation; hard-blocked with zero execution path.
