"""CLI entry point for the Windows CLI agent.

Usage:
    python main.py "list files in the current directory"
    python main.py                # interactive REPL
    python main.py --auto "..."   # skip the confirmation prompt
"""

from __future__ import annotations

import argparse
import sys

from dotenv import load_dotenv

from agent.graph import build_graph, new_thread_config
from agent.state import AgentState

load_dotenv()


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


def _run_once(graph, prompt: str, auto: bool) -> None:
    """Generate + screen (graph pauses), optionally confirm, then execute."""
    config = new_thread_config()

    # First leg: invoke graph with prompt
    graph.invoke({"prompt": prompt}, config)

    while True:
        state: AgentState = graph.get_state(config).values

        command = state.get("command", "")
        if not command:
            print("Could not generate a command for that request.\n")
            return

        # If already executed and result validation has completed
        if state.get("executed") and state.get("semantic_valid") is not None:
            _print_output(state)
            if state.get("semantic_valid"):
                print("  Result validation: PASS\n")
            else:
                print("  Result validation: FAILED")
                print(f"  reason  : {state.get('semantic_reason', 'Unknown reason')}\n")
                if state.get("retry_count", 0) >= 2:
                    print("Command failed after 2 attempts.\n")
            return

        # If blocked by command validation
        if not state.get("is_valid", True):
            print(f"\n  command : {command}")
            if state.get("explanation"):
                print(f"  details : {state['explanation']}")
            print(f"  [INVALID] {state.get('validation_reason', '')}\n")
            if state.get("retry_count", 0) >= 2:
                print("Command failed after 2 attempts.\n")
            return

        # If blocked by safety screen
        if not state.get("is_safe", True):
            print(f"\n  command : {command}")
            if state.get("explanation"):
                print(f"  details : {state['explanation']}")
            print(f"  [BLOCKED] {state.get('safety_reason', '')}\n")
            return

        # Display proposed command
        print(f"\n  command : {command}")
        if state.get("explanation"):
            print(f"  details : {state['explanation']}")

        if not auto:
            answer = input("\nRun this command? [y/N] ").strip().lower()
            if answer not in {"y", "yes"}:
                print("Skipped.\n")
                return

        # Resume graph execution
        graph.invoke(None, config)
        new_state: AgentState = graph.get_state(config).values

        if new_state.get("executed") and new_state.get("semantic_valid") is True:
            _print_output(new_state)
            print("  Result validation: PASS\n")
            return
        elif new_state.get("executed") and new_state.get("semantic_valid") is False and new_state.get("retry_count", 0) >= 2:
            _print_output(new_state)
            print("  Result validation: FAILED")
            print(f"  reason  : {new_state.get('semantic_reason', 'Unknown reason')}\n")
            print("Command failed after 2 attempts.\n")
            return
        elif not new_state.get("executed"):
            retry_num = new_state.get("retry_count", 1) + 1
            reason = new_state.get("semantic_reason") or new_state.get("validation_reason") or "PowerShell command failed"
            print(f"\n  Result validation: FAILED")
            print(f"  reason  : {reason}")
            print(f"\nRetrying (attempt {retry_num}/2)...")


def _interactive(graph, auto: bool) -> None:
    print("WinCliAgent — type a request, or 'exit' to quit.")
    while True:
        try:
            prompt = input("\n> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if prompt.lower() in {"exit", "quit", "q"}:
            break
        if not prompt:
            continue
        _run_once(graph, prompt, auto)


def main() -> int:
    parser = argparse.ArgumentParser(description="Natural language to Windows CLI agent.")
    parser.add_argument("prompt", nargs="*", help="The request to translate and run.")
    parser.add_argument(
        "--auto",
        action="store_true",
        help="Execute the generated command without asking for confirmation.",
    )
    args = parser.parse_args()

    graph = build_graph()

    if args.prompt:
        _run_once(graph, " ".join(args.prompt), args.auto)
    else:
        _interactive(graph, args.auto)
    return 0


if __name__ == "__main__":
    sys.exit(main())