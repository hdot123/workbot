#!/usr/bin/env python3
"""
tmux-skills Runtime Enforcement Module

Enforces that scripts are called through the scheduler, not directly.

Usage: Add to the top of scripts that should not be called directly.
"""

import os
import sys
from pathlib import Path


def enforce_via_scheduler(script_name: str = None) -> None:
    """
    Enforce that the current script is called through the scheduler.

    This is the PRIMARY enforcement function for ALL scripts.
    It checks for the TMUX_VIA_SCHEDULER marker set by run_script.py.

    Args:
        script_name: Name of the script (for error messages)

    Raises:
        SystemExit: If called directly without going through scheduler
    """
    if script_name is None:
        # Infer from call stack
        import inspect
        frame = inspect.currentframe()
        if frame and frame.f_back:
            script_name = Path(frame.f_back.f_code.co_filename).name
        else:
            script_name = "unknown"

    # Check if called through scheduler (PRIMARY check)
    via_scheduler = os.environ.get("TMUX_VIA_SCHEDULER", "")
    orchestrator_context = os.environ.get("TMUX_ORCHESTRATOR_CONTEXT", "")
    internal_call = os.environ.get("TMUX_INTERNAL_CALL", "")
    skip_enforcement = os.environ.get("TMUX_SKIP_ENFORCEMENT", "")

    # Allow if called through scheduler
    if via_scheduler == "true":
        return

    # Allow if orchestrator context (legacy support)
    if orchestrator_context == "true":
        return

    # Allow if internal call (legacy support)
    if internal_call == "true":
        return

    # Allow explicit skip (for development/debugging)
    if skip_enforcement == "true":
        sys.stderr.write(f"WARNING: Scheduler enforcement skipped for {script_name}\n")
        return

    # Block direct execution
    sys.stderr.write(f"""
ERROR: {script_name} cannot be called directly.

This script must be called through the tmux-skills scheduler.

Usage:
    python3 run_script.py --script {script_name} [args...]

Or set TMUX_ORCHESTRATOR_CONTEXT=true if calling from within the orchestrator.
""")
    sys.exit(1)


def enforce_scheduler_call(script_name: str = None, allow_public_direct: bool = False) -> None:
    """
    Enforce that the current script is called through the scheduler.

    Args:
        script_name: Name of the script (for error messages)
        allow_public_direct: If True, allows direct execution for public scripts
                            (but still requires scheduler for orchestrator_only/internal_only)

    Raises:
        SystemExit: If called directly without going through scheduler
    """
    # Delegate to enforce_via_scheduler for consistency
    if allow_public_direct:
        # Legacy function - just warn
        if os.environ.get("TMUX_VIA_SCHEDULER") != "true":
            sys.stderr.write(f"NOTE: {script_name} is recommended to be called through run_script.py\n")
            return
    enforce_via_scheduler(script_name)


def enforce_orchestrator_only(script_name: str = None) -> None:
    """
    Enforce that the current script is only called by the orchestrator.

    This is stricter than enforce_scheduler_call() - it does not allow
    direct execution even for public scripts.
    """
    if script_name is None:
        import inspect
        frame = inspect.currentframe()
        if frame and frame.f_back:
            script_name = Path(frame.f_back.f_code.co_filename).name
        else:
            script_name = "unknown"

    orchestrator_context = os.environ.get("TMUX_ORCHESTRATOR_CONTEXT", "")

    if orchestrator_context == "true":
        return

    sys.stderr.write(f"""
ERROR: {script_name} can only be called by the orchestrator.

This script is marked as orchestrator_only and must be called through
start_formal_runtime_chain.py or by setting TMUX_ORCHESTRATOR_CONTEXT=true.

Usage (through scheduler):
    python3 run_script.py --script {script_name} [args...]

Usage (from orchestrator):
    export TMUX_ORCHESTRATOR_CONTEXT=true
    python3 {script_name} [args...]
""")
    sys.exit(1)


def enforce_internal_only(script_name: str = None) -> None:
    """
    Enforce that the current script is only called as an internal library.

    IMPORTANT: This function is designed to be called inside an
    `if __name__ == "__main__":` block. It enforces that the script
    cannot be run directly without TMUX_INTERNAL_CALL=true.

    Usage in target script:
        if __name__ == "__main__":
            from runtime_enforcement import enforce_internal_only
            enforce_internal_only("script_name.py")
            # ... rest of __main__ code ...
    """
    internal_call = os.environ.get("TMUX_INTERNAL_CALL", "")

    if internal_call == "true":
        return

    sys.stderr.write(f"""
ERROR: {script_name} is for internal use only.

This script is marked as internal_only and cannot be called directly.

Usage:
    python3 run_script.py --script {script_name} [args...]

Or set TMUX_INTERNAL_CALL=true if calling from internal code.
""")
    sys.exit(1)
