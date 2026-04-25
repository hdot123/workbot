#!/usr/bin/env python3
"""
tmux-runtime Script Scheduler

Unified script scheduler with registration-based validation.

Usage:
    python3 run_script.py --script <script_name> [--args <args>]

This scheduler enforces:
1. Registration check - only registered scripts can execute
2. Status check - disabled scripts are blocked, deprecated scripts show warnings
3. Visibility check - orchestrator_only scripts require orchestrator context
4. Environment check - environment constraints must be satisfied
5. Precondition check - preconditions must be met before execution

NOTE: This script re-exports tmux_scheduler module for backward compatibility.
All core logic (is_clean_state, check_precondition, etc.) is delegated to tmux_scheduler.py.
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

TMUX_RETIRED_ERROR = "tmux runtime is retired in workbot; use cmux runtime only"
CMUX_BOOTSTRAP_HINT = "/Users/busiji/.agents/skills/cmux/scripts/bootstrap_claude_runtime.py"

# Registry path
SCRIPT_REGISTRY_PATH = Path(__file__).parent.parent / "SCRIPT_REGISTRY.json"
SCRIPTS_DIR = Path(__file__).parent

# Re-export all public functions from tmux_scheduler for backward compatibility
# This ensures a single source of truth for all scheduler logic
sys.path.insert(0, str(Path(__file__).parent.parent))
from tmux_scheduler import (
    load_registry,
    is_hidden_pty,
    is_visible_terminal,
    is_inside_tmux,
    is_formal_session,
    is_clean_state,
    is_orchestrator_context,
    is_internal_call,
    check_precondition,
    validate_script,
    execute_script,
    run_script as run_script_via_scheduler,
    list_scripts,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="tmux-runtime Script Scheduler",
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
    parser.add_argument(
        "--legacy-allow-tmux",
        action="store_true",
        help="Bypass retirement guard for emergency legacy debugging only.",
    )

    args = parser.parse_args()

    if not args.legacy_allow_tmux:
        if args.list:
            sys.stderr.write(
                f"WARNING: {TMUX_RETIRED_ERROR}; listing historical scripts only.\n"
            )
        else:
            payload = {
                "status": "blocked",
                "error": TMUX_RETIRED_ERROR,
                "runtime": "cmux",
                "cmux_bootstrap": CMUX_BOOTSTRAP_HINT,
            }
            print(json.dumps(payload, ensure_ascii=False, indent=2))
            return 2

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

    return run_script_via_scheduler(args.script, extra_args)


if __name__ == "__main__":
    sys.exit(main())
