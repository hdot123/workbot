#!/usr/bin/env python3
"""
tmux-skills Script Scheduler

Unified script scheduler with registration-based validation.

Usage:
    python3 run_script.py --script <script_name> [--args <args>]

This scheduler enforces:
1. Registration check - only registered scripts can execute
2. Status check - disabled scripts are blocked, deprecated scripts show warnings
3. Visibility check - orchestrator_only scripts require orchestrator context
4. Environment check - environment constraints must be satisfied
5. Precondition check - preconditions must be met before execution
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

# Registry path
SCRIPT_REGISTRY_PATH = Path(__file__).parent.parent / "SCRIPT_REGISTRY.json"
SCRIPTS_DIR = Path(__file__).parent


def load_registry() -> dict[str, Any]:
    """Load the script registration table."""
    if not SCRIPT_REGISTRY_PATH.exists():
        raise FileNotFoundError(f"Script registry not found: {SCRIPT_REGISTRY_PATH}")

    with open(SCRIPT_REGISTRY_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def is_hidden_pty() -> bool:
    """Check if running in a hidden PTY context."""
    # Check for Claude Code hidden context markers
    # 1. CODEX_THREAD_ID without visible terminal
    codex_thread_id = os.environ.get("CODEX_THREAD_ID", "")

    # 2. Check for hidden_context file (Claude Code hidden context indicator)
    hidden_context_file = Path.home() / ".claude" / "hidden_context"
    if hidden_context_file.exists():
        return True

    # 3. Check for tmux session named "hidden" or starting with "_"
    if "TMUX" in os.environ:
        try:
            result = subprocess.run(
                ["tmux", "display-message", "-p", "#S"],
                capture_output=True,
                text=True,
                timeout=5
            )
            session_name = result.stdout.strip()
            if session_name.startswith("_") or session_name == "hidden":
                return True
        except (subprocess.SubprocessError, FileNotFoundError):
            pass

    # 4. If CODEX_THREAD_ID is set but we can't verify visible terminal, assume hidden
    if codex_thread_id:
        # Try to verify visible terminal
        if not _verify_visible_terminal():
            return True

    return False


def _verify_visible_terminal() -> bool:
    """Verify this is a real visible terminal (not hidden PTY)."""
    # Check for standard terminal environment variables
    term = os.environ.get("TERM", "")
    if term and "dumb" not in term:
        # Check if stdin is a TTY
        import tty
        import termios
        try:
            # Try to get terminal settings
            termios.tcgetattr(sys.stdin.fileno())
            return True
        except (tty.error, termios.error, AttributeError, OSError):
            # Not a real TTY or stdin not available
            return False
    return False


def is_visible_terminal() -> bool:
    """Check if running in a visible terminal."""
    # Visible terminal means user can see the output
    # For now, we assume non-hidden-PTY is visible
    return not is_hidden_pty()


def is_inside_tmux() -> bool:
    """Check if running inside a tmux session."""
    return "TMUX" in os.environ


def is_formal_session(formal_session_name: str = "formal-session") -> bool:
    """Check if running inside the formal session."""
    if not is_inside_tmux():
        return False

    try:
        result = subprocess.run(
            ["tmux", "display-message", "-p", "#S"],
            capture_output=True,
            text=True,
            timeout=5
        )
        current_session = result.stdout.strip()
        return current_session == formal_session_name
    except (subprocess.SubprocessError, FileNotFoundError):
        return False


def is_clean_state() -> bool:
    """Check if the runtime state is clean (no old sessions/ledger/watcher)."""
    try:
        # Check for existing tmux sessions
        result = subprocess.run(
            ["tmux", "list-sessions"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.stdout.strip():
            # Check if any session is not "hidden" or internal
            for line in result.stdout.splitlines():
                session_name = line.split(":")[0].strip()
                # Ignore hidden/internal sessions
                if not session_name.startswith("_") and session_name != "hidden":
                    return False

        # Check for existing ledger
        ledger_path = SCRIPTS_DIR / "current-runtime.json"
        if ledger_path.exists():
            return False

        # Check for existing watcher processes
        ps_result = subprocess.run(
            ["ps", "ax", "-o", "pid=,command="],
            capture_output=True,
            text=True,
            timeout=5
        )
        for line in ps_result.stdout.splitlines():
            if "watch_tmux_handoff.py" in line and "grep" not in line:
                return False

        # Check for CODEX_THREAD_ID environment variable in tmux
        env_result = subprocess.run(
            ["tmux", "show-environment", "-g", "CODEX_THREAD_ID"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if env_result.returncode == 0 and env_result.stdout.strip():
            return False

        # Check for bridge processes
        for line in ps_result.stdout.splitlines():
            if "tmux_handoff_app_bridge.py" in line and "grep" not in line:
                return False

        return True
    except (subprocess.SubprocessError, FileNotFoundError):
        return True  # If tmux is not available, consider it clean


def is_orchestrator_context() -> bool:
    """Check if called by the orchestrator (start_formal_runtime_chain.py)."""
    # Check if the parent process is the orchestrator
    # This can be implemented via environment variable or process inspection
    orchestrator_marker = os.environ.get("TMUX_ORCHESTRATOR_CONTEXT", "")
    return orchestrator_marker == "true"


def is_internal_call() -> bool:
    """Check if this is an internal library call (not for external users)."""
    # Internal calls are marked with TMUX_INTERNAL_CALL
    internal_marker = os.environ.get("TMUX_INTERNAL_CALL", "")
    return internal_marker == "true"


def check_precondition(precondition: str, script_meta: dict[str, Any]) -> bool:
    """Check if a precondition is satisfied."""
    try:
        if precondition == "formal_session_exists":
            result = subprocess.run(
                ["tmux", "list-sessions"],
                capture_output=True,
                text=True,
                timeout=5
            )
            return "formal-session" in result.stdout

        elif precondition == "pane_titles_applied":
            # Check ledger for slot_bindings
            ledger_path = SCRIPTS_DIR / "current-runtime.json"
            if not ledger_path.exists():
                return False
            with open(ledger_path, "r", encoding="utf-8") as f:
                ledger = json.load(f)
            slot_bindings = ledger.get("slot_bindings", [])
            return len(slot_bindings) > 0

        elif precondition == "watcher_armed":
            ledger_path = SCRIPTS_DIR / "current-runtime.json"
            if not ledger_path.exists():
                return False
            with open(ledger_path, "r", encoding="utf-8") as f:
                ledger = json.load(f)
            watcher = ledger.get("watcher", {})
            return watcher.get("armed", False) is True

        elif precondition == "ledger_initialized":
            ledger_path = SCRIPTS_DIR / "current-runtime.json"
            return ledger_path.exists()

        elif precondition == "session_exists":
            result = subprocess.run(
                ["tmux", "list-sessions"],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0 and result.stdout.strip() != ""

        elif precondition == "panes_exist":
            # Check if there are panes in the current window
            if not is_inside_tmux():
                return False
            result = subprocess.run(
                ["tmux", "list-panes"],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0 and result.stdout.strip() != ""

        elif precondition == "pane_exists":
            # Similar to panes_exist
            if not is_inside_tmux():
                return False
            result = subprocess.run(
                ["tmux", "list-panes"],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0 and result.stdout.strip() != ""

        else:
            # Unknown precondition - treat as not satisfied
            sys.stderr.write(f"WARNING: Unknown precondition '{precondition}'\n")
            return False

    except (subprocess.SubprocessError, FileNotFoundError, json.JSONDecodeError, KeyError):
        return False


def validate_script(script_name: str, registry: dict[str, Any]) -> tuple[bool, list[str]]:
    """
    Validate a script request against the registry.

    Returns:
        tuple[bool, list[str]]: (success, list of error messages)
    """
    errors: list[str] = []
    warnings: list[str] = []

    # Step 1: Check if script is registered
    if script_name not in registry["scripts"]:
        errors.append(f"Script '{script_name}' is not registered")
        return False, errors

    script_meta = registry["scripts"][script_name]

    # Step 2: Check status
    status = script_meta["status"]
    if status == "disabled":
        errors.append(f"Script '{script_name}' is disabled")
        return False, errors
    elif status == "deprecated":
        warnings.append(f"Script '{script_name}' is deprecated")
        if script_meta.get("deprecation", {}).get("alternative"):
            alt = script_meta["deprecation"]["alternative"]
            warnings.append(f"  -> Use '{alt}' instead")

    # Step 3: Check visibility
    visibility = script_meta["visibility"]
    if visibility == "orchestrator_only":
        if not is_orchestrator_context():
            errors.append(f"Script '{script_name}' can only be called by orchestrator")
            return False, errors

    if visibility == "internal_only":
        if not is_internal_call():
            errors.append(f"Script '{script_name}' is for internal use only")
            return False, errors

    # Step 4: Check environment constraints
    env_constraints = script_meta.get("environment_constraints", {})

    if env_constraints.get("forbidden_in_hidden_pty") and is_hidden_pty():
        errors.append(f"Script '{script_name}' cannot run in hidden PTY")

    if env_constraints.get("requires_visible_terminal") and not is_visible_terminal():
        errors.append(f"Script '{script_name}' requires visible terminal")

    if env_constraints.get("requires_inside_tmux") and not is_inside_tmux():
        errors.append(f"Script '{script_name}' requires running inside tmux")

    if env_constraints.get("requires_formal_session") and not is_formal_session():
        errors.append(f"Script '{script_name}' requires formal-session")

    if env_constraints.get("requires_clean_state") and not is_clean_state():
        errors.append(f"Script '{script_name}' requires clean state")

    # Step 5: Check preconditions
    preconditions = script_meta.get("preconditions", [])
    for precondition in preconditions:
        if not check_precondition(precondition, script_meta):
            errors.append(f"Precondition '{precondition}' not met")

    # Print warnings
    for warning in warnings:
        sys.stderr.write(f"WARNING: {warning}\n")

    return len(errors) == 0, errors


def execute_script(script_name: str, script_meta: dict[str, Any], args: list[str]) -> int:
    """Execute a script with the given arguments."""
    entry_point = SCRIPTS_DIR / script_meta["entry_point"]

    if not entry_point.exists():
        sys.stderr.write(f"ERROR: Script entry point not found: {entry_point}\n")
        return 1

    # Build command
    cmd = [sys.executable, str(entry_point)] + args

    # Set scheduler context marker - proves this call went through scheduler validation
    env = os.environ.copy()
    env["TMUX_VIA_SCHEDULER"] = "true"

    # Also set legacy markers for backwards compatibility
    if is_orchestrator_context():
        env["TMUX_ORCHESTRATOR_CONTEXT"] = "true"

    try:
        result = subprocess.run(cmd, env=env)
        return result.returncode
    except subprocess.SubprocessError as e:
        sys.stderr.write(f"ERROR: Failed to execute script: {e}\n")
        return 1


def run_script(script_name: str, args: list[str]) -> int:
    """Main entry point for running a script."""
    # Step 1: Load registry
    try:
        registry = load_registry()
    except FileNotFoundError as e:
        sys.stderr.write(f"ERROR: {e}\n")
        return 1
    except json.JSONDecodeError as e:
        sys.stderr.write(f"ERROR: Invalid registry JSON: {e}\n")
        return 1

    # Step 2: Validate script
    success, messages = validate_script(script_name, registry)
    if not success:
        for msg in messages:
            sys.stderr.write(f"ERROR: {msg}\n")
        return 1

    script_meta = registry["scripts"][script_name]

    # Step 3: Execute script
    return execute_script(script_name, script_meta, args)


def list_scripts(registry: dict[str, Any]) -> None:
    """List all registered scripts."""
    print("\nRegistered Scripts:")
    print("=" * 80)

    # Group by category
    categories: dict[str, list[dict[str, Any]]] = {}
    for script_name, script_meta in registry["scripts"].items():
        category = script_meta["category"]
        if category not in categories:
            categories[category] = []
        categories[category].append({"name": script_name, **script_meta})

    # Print by category
    category_order = [
        "orchestrator",
        "verifier",
        "watcher_arm",
        "watcher_worker",
        "topology",
        "pane_init",
        "env_init",
        "ledger",
        "bridge",
        "support_library",
        "deprecated",
    ]

    for category in category_order:
        if category not in categories:
            continue

        scripts = categories[category]
        print(f"\n[{category.upper()}]")
        print("-" * 60)

        for script in scripts:
            status_icon = {
                "stable": "🟢",
                "testing": "🟡",
                "deprecated": "🔴",
                "disabled": "⚫",
            }.get(script["status"], "⚪")

            visibility_icon = {
                "public": "🌍",
                "orchestrator_only": "🎯",
                "internal_only": "🔒",
            }.get(script["visibility"], "❓")

            print(f"  {status_icon} {visibility_icon} {script['name']}")
            print(f"      {script['description']}")
            if script.get("deprecation"):
                alt = script["deprecation"].get("alternative", "None")
                print(f"      ⚠️  Alternative: {alt}")
            print()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="tmux-skills Script Scheduler",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 run_script.py --script start_formal_runtime_chain.py --args "--pane-count 4"
  python3 run_script.py --script check_tmux_ready.py --args "--require-formal"
  python3 run_script.py --list
        """
    )

    parser.add_argument(
        "--script",
        type=str,
        help="Name of the script to run"
    )

    parser.add_argument(
        "--args",
        type=str,
        default="",
        help="Arguments to pass to the script (space-separated)"
    )

    parser.add_argument(
        "--list",
        action="store_true",
        help="List all registered scripts"
    )

    args = parser.parse_args()

    if args.list:
        try:
            registry = load_registry()
            list_scripts(registry)
            return 0
        except Exception as e:
            sys.stderr.write(f"ERROR: {e}\n")
            return 1

    if not args.script:
        parser.print_help()
        return 1

    # Parse additional arguments
    extra_args = args.args.split() if args.args else []

    return run_script(args.script, extra_args)


if __name__ == "__main__":
    sys.exit(main())
