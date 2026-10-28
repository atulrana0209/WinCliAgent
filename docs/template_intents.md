# Deterministic Command Templates: Intent Catalog

This document defines the deterministic fast-path template intents for WinCliAgent.
Templates provide sub-millisecond, guaranteed-correct command generation for standard, unambiguous, read-only system queries before falling back to local LLM generation.

---

## 1. Principles & Design Constraints

1. **Read-Only Exclusivity**:
   Every template maps strictly to a non-modifying, non-destructive observational command. The expected risk tier is always `LOW`.
2. **Zero Safety Bypass**:
   Templates do not bypass safety checks. Every template-generated command passes through:
   - Tokenization & AST safety classifier (`agent.safety.classify_risk_tier`).
   - Command validation (`agent.validator.validate_command`).
   - JSON structured audit logger (`agent.audit.AuditLogger`).
3. **Conservative Parameter-Free Matching**:
   Templates only trigger on clean, parameter-free inquiries. If a request contains any conditional logic, filters, qualifiers, named targets, specific paths, thresholds, counts, or modifiers, the template **must not match** and must fall through to the LLM.
4. **No Dev/Held-out Contamination**:
   Triggers are defined from general everyday administrative requests and idioms. Exact task sentences from benchmark splits are not used as hardcoded triggers.

---

## 2. Intent Specifications

### Intent 1: `current_directory`
- **Description**: Query the current working directory path.
- **Fixed Command**: `Get-Location`
- **Expected Risk Tier**: `LOW`
- **Trigger Patterns**:
  - `^(?:what is |get |show |print )?(?:my )?(?:current )?(?:working )?(?:directory|dir|path|folder|pwd)$`
  - `^where am i$`
- **Exclusion Conditions**:
  - Mentions target path or subfolder (e.g., "in src", "of temp").
  - Mentions changing, moving, or setting directory.

### Intent 2: `free_disk_space`
- **Description**: Inspect free storage space across file system drives.
- **Fixed Command**: `Get-PSDrive -PSProvider FileSystem`
- **Expected Risk Tier**: `LOW`
- **Trigger Patterns**:
  - `^(?:show |get |check |display )?(?:free )?disk (?:space|usage)$`
  - `^(?:show |get |check )?drive (?:space|usage)$`
- **Exclusion Conditions**:
  - Specific drive letter targeted (e.g., "C:", "drive D").
  - Formatting or threshold requests (e.g., "> 10GB", "sorted by free space").

### Intent 3: `current_user`
- **Description**: Check current logged-in user identity.
- **Fixed Command**: `whoami`
- **Expected Risk Tier**: `LOW`
- **Trigger Patterns**:
  - `^whoami$`
  - `^(?:who am i|what is my username|show current user|get current user)$`
- **Exclusion Conditions**:
  - Mentions other user accounts, groups, privileges, or active directory queries.

### Intent 4: `hostname`
- **Description**: Query the local machine network name.
- **Fixed Command**: `hostname`
- **Expected Risk Tier**: `LOW`
- **Trigger Patterns**:
  - `^hostname$`
  - `^(?:get |show |what is )?(?:computer|machine|host) name$`
- **Exclusion Conditions**:
  - Remote hostnames, DNS lookups, or domain join operations.

### Intent 5: `datetime`
- **Description**: Query the current local system timestamp.
- **Fixed Command**: `Get-Date`
- **Expected Risk Tier**: `LOW`
- **Trigger Patterns**:
  - `^(?:get |show |what is )?(?:the )?(?:current )?(?:date and time|date|time)$`
  - `^what time is it$`
  - `^what is today's date$`
- **Exclusion Conditions**:
  - Relative date calculation (e.g., "yesterday", "last 24 hours").
  - Date format conversions or time zone adjustments.

### Intent 6: `running_processes`
- **Description**: List all active OS processes.
- **Fixed Command**: `Get-Process`
- **Expected Risk Tier**: `LOW`
- **Trigger Patterns**:
  - `^(?:get|show|list) (?:running |active )?processes$`
  - `^what processes are running$`
- **Exclusion Conditions**:
  - Specific process names (e.g., "svchost", "chrome").
  - Resource filters or limits (e.g., "top 5 by CPU", "using most memory").
  - Kill / stop / priority modification intents.

### Intent 7: `os_version`
- **Description**: Display Windows operating system name and version.
- **Fixed Command**: `Get-CimInstance Win32_OperatingSystem`
- **Expected Risk Tier**: `LOW`
- **Trigger Patterns**:
  - `^(?:get |show |what is )?(?:my )?(?:os|operating system) version$`
  - `^(?:show |what is )?windows version$`
- **Exclusion Conditions**:
  - Specific build number registry queries or updates/hotfix histories.

### Intent 8: `ip_address`
- **Description**: Inspect network adapter IP configuration.
- **Fixed Command**: `Get-NetIPConfiguration`
- **Expected Risk Tier**: `LOW`
- **Trigger Patterns**:
  - `^(?:get |show |what is )?(?:my )?(?:ip address|ip config|ip configuration)$`
- **Exclusion Conditions**:
  - Specific adapter naming (e.g., "Ethernet", "Wi-Fi").
  - Pinging, traceroutes, or gateway/DNS modifications.
  - MAC address queries.

### Intent 9: `list_files`
- **Description**: List files and subdirectories in the current folder.
- **Fixed Command**: `Get-ChildItem`
- **Expected Risk Tier**: `LOW`
- **Trigger Patterns**:
  - `^(?:list |show )?files(?: in (?:this|current) (?:folder|directory))?$`
  - `^(?:list |show )?(?:all )?contents of (?:this|current) (?:folder|directory)$`
  - `^dir$`
  - `^ls$`
- **Exclusion Conditions**:
  - File extension filters (e.g., "*.py", "*.txt", "*.log").
  - Path parameters (e.g., "in src", "in logs").
  - Sorting criteria (e.g., "by size", "by date").
  - Recursive search flags (`-Recurse`).
  - Size/count constraints (e.g., "> 1KB", "largest", "how many").
