"""CLI entry point for the Windows CLI agent.

Usage:
    python main.py "show my IP configuration"
    python main.py --dry-run "show my IP configuration"
    python main.py --explain "show my IP configuration"
    python main.py --verbose "show my IP configuration"
    python main.py --auto "..."
    python main.py  # Interactive REPL
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime

from dotenv import load_dotenv

from agent.graph import build_graph, new_thread_config
from agent.state import AgentState

load_dotenv()

# In-memory history for interactive sessions
history_records: list[dict] = []


def _print_output(state: AgentState) -> None:
    if state.get("executed"):
        print(f"  exit    : {state.get('exit_code')}")
        stdout = state.get("stdout", "")
        stderr = state.get("stderr", "")
        if stdout:
            print("\n--- output ---")
            print(stdout.rstrip("\n"))
        if stderr:
            print("\n--- errors ---")
            print(stderr.rstrip("\n"))
    print()


def _run_once(
    graph,
    prompt: str,
    auto: bool = False,
    dry_run: bool = False,
    explain_mode: bool = False,
    verbose: bool = False,
) -> None:
    """Run agent graph for a prompt."""
    config = new_thread_config()

    initial_input: AgentState = {
        "prompt": prompt,
        "dry_run": dry_run,
        "explain_mode": explain_mode,
        "verbose": verbose,
    }

    graph.invoke(initial_input, config)

    while True:
        state: AgentState = graph.get_state(config).values

        command = state.get("command", "")
        if not command:
            print("Could not generate a command for that request.\n")
            return

        risk = state.get("risk_level", "LOW")
        action = state.get("action", "ALLOWED")

        # Explain mode output
        if explain_mode:
            print(f"\nRequest : {prompt}")
            print(f"Command : {command}")
            if state.get("explanation"):
                print(f"Why     : {state['explanation']}")
            print(f"Risk    : {risk}")
            print("Action  : ALLOWED (EXPLAIN — command was NOT executed)\n")
            history_records.append({
                "prompt": prompt,
                "command": command,
                "risk": risk,
                "status": "EXPLAINED",
                "timestamp": datetime.now().isoformat(),
            })
            return

        # Dry run output
        if dry_run:
            print(f"\nRequest : {prompt}")
            print(f"Command : {command}")
            print(f"Risk    : {risk}")
            print(f"Action  : {action}")
            print("Execution: DRY RUN — command was NOT executed\n")
            history_records.append({
                "prompt": prompt,
                "command": command,
                "risk": risk,
                "status": "DRY_RUN",
                "timestamp": datetime.now().isoformat(),
            })
            return

        # Handle CRITICAL hard block (no override allowed)
        if risk == "CRITICAL":
            print(f"\n  command : {command}")
            print(f"  Risk    : CRITICAL")
            print(f"  Action  : BLOCKED")
            print(f"  [HARD BLOCKED] {state.get('safety_reason', 'Critical risk system destructive command.')}\n")
            history_records.append({
                "prompt": prompt,
                "command": command,
                "risk": risk,
                "status": "HARD_BLOCKED",
                "timestamp": datetime.now().isoformat(),
            })
            return

        # Handle Invalid commands
        if not state.get("is_valid", True):
            print(f"\n  command : {command}")
            print(f"  Risk    : {risk}")
            print(f"  [INVALID] {state.get('validation_reason', '')}\n")
            if state.get("retry_count", 0) >= 2:
                print("Command failed after 2 attempts.\n")
            return

        # Display proposed command
        print(f"\n  command : {command}")
        if state.get("explanation"):
            print(f"  details : {state['explanation']}")
        print(f"  Risk    : {risk}")
        print(f"  Action  : {action}")

        # Human-in-the-loop confirmation logic per tier
        approved = False
        if risk == "HIGH":
            print("  [HIGH RISK] This command can modify or delete resources.")
            confirm_input = input("\nType 'CONFIRM' or 'YES' to execute this command: ").strip()
            if confirm_input in {"CONFIRM", "YES"}:
                approved = True
            else:
                print("Skipped (explicit confirmation not provided).\n")
                history_records.append({
                    "prompt": prompt,
                    "command": command,
                    "risk": risk,
                    "status": "REJECTED_EXPLICIT",
                    "timestamp": datetime.now().isoformat(),
                })
                return
        elif risk == "MEDIUM":
            answer = input("\nRun this modifying command? [y/N] ").strip().lower()
            if answer in {"y", "yes"}:
                approved = True
            else:
                print("Skipped.\n")
                history_records.append({
                    "prompt": prompt,
                    "command": command,
                    "risk": risk,
                    "status": "SKIPPED",
                    "timestamp": datetime.now().isoformat(),
                })
                return
        else:  # LOW
            if auto and state.get("is_allowlisted", True):
                approved = True
            else:
                answer = input("\nRun this command? [y/N] ").strip().lower()
                if answer in {"y", "yes"}:
                    approved = True
                else:
                    print("Skipped.\n")
                    history_records.append({
                        "prompt": prompt,
                        "command": command,
                        "risk": risk,
                        "status": "SKIPPED",
                        "timestamp": datetime.now().isoformat(),
                    })
                    return

        # Set approved in state and resume execution
        graph.update_state(config, {"approved": approved})
        graph.invoke(None, config)
        new_state: AgentState = graph.get_state(config).values

        if new_state.get("executed") and new_state.get("semantic_valid") is True:
            _print_output(new_state)
            print("  Result validation: PASS\n")
            history_records.append({
                "prompt": prompt,
                "command": command,
                "risk": risk,
                "status": "SUCCESS",
                "timestamp": datetime.now().isoformat(),
            })
            return
        elif new_state.get("executed") and new_state.get("semantic_valid") is False and new_state.get("retry_count", 0) >= 2:
            _print_output(new_state)
            print("  Result validation: FAILED")
            print(f"  reason  : {new_state.get('semantic_reason', 'Unknown reason')}\n")
            print("Command failed after 2 attempts.\n")
            history_records.append({
                "prompt": prompt,
                "command": command,
                "risk": risk,
                "status": "FAILED",
                "timestamp": datetime.now().isoformat(),
            })
            return
        elif not new_state.get("executed"):
            retry_num = new_state.get("retry_count", 1) + 1
            reason = new_state.get("semantic_reason") or new_state.get("validation_reason") or "Execution failed"
            print(f"\n  Result validation: FAILED")
            print(f"  reason  : {reason}")
            print(f"\nRetrying (attempt {retry_num}/2)...")


def _interactive(
    graph,
    auto: bool = False,
    dry_run: bool = False,
    explain_mode: bool = False,
    verbose: bool = False,
) -> None:
    print("WinCliAgent — type a request, 'history' to view past runs, or 'exit' to quit.")
    while True:
        try:
            prompt = input("\n> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if prompt.lower() in {"exit", "quit", "q"}:
            break

        if prompt.lower() == "history":
            if not history_records:
                print("No commands in history yet.")
            else:
                print("\nCommand History:")
                for idx, item in enumerate(history_records, 1):
                    print(f"  {idx}. [{item['status']}] {item['prompt']} -> {item['command']} (Risk: {item['risk']})")
            continue

        if prompt.lower().startswith("history "):
            try:
                item_idx = int(prompt.split()[1]) - 1
                if 0 <= item_idx < len(history_records):
                    rec = history_records[item_idx]
                    print(f"\nHistory Item #{item_idx + 1}:")
                    print(f"  Timestamp : {rec['timestamp']}")
                    print(f"  Prompt    : {rec['prompt']}")
                    print(f"  Command   : {rec['command']}")
                    print(f"  Risk      : {rec['risk']}")
                    print(f"  Status    : {rec['status']}")
                else:
                    print(f"Invalid history index. Range is 1 to {len(history_records)}.")
            except ValueError:
                print("Usage: history <number>")
            continue

        if not prompt:
            continue

        _run_once(
            graph,
            prompt,
            auto=auto,
            dry_run=dry_run,
            explain_mode=explain_mode,
            verbose=verbose,
        )


def main() -> int:
    parser = argparse.ArgumentParser(description="Natural language to Windows CLI agent.")
    parser.add_argument("prompt", nargs="*", help="The request to translate and run.")
    parser.add_argument(
        "--auto",
        action="store_true",
        help="Execute the generated command without asking for confirmation.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Generate and screen command without executing.",
    )
    parser.add_argument(
        "--explain",
        action="store_true",
        help="Display generated command, explanation, and risk without executing.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print detailed step-by-step workflow logs.",
    )
    args = parser.parse_args()

    graph = build_graph()

    if args.prompt:
        _run_once(
            graph,
            " ".join(args.prompt),
            auto=args.auto,
            dry_run=args.dry_run,
            explain_mode=args.explain,
            verbose=args.verbose,
        )
    else:
        _interactive(
            graph,
            auto=args.auto,
            dry_run=args.dry_run,
            explain_mode=args.explain,
            verbose=args.verbose,
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())