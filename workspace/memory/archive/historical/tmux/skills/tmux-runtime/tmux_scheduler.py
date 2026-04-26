#!/usr/bin/env python3
"""
tmux-runtime Scheduler Module

Reusable scheduler module with registration-based validation.
Can be imported by other scripts (e.g., start_formal_runtime_chain.py) to execute phase scripts through the scheduler.

This module enforces:
1. Registration check - only registered scripts can execute
2. Status check - disabled scripts are blocked, deprecated scripts show warnings
3. Visibility check - orchestrator_only/internal_only scripts require proper context
4. Environment check - environment constraints must be satisfied
5. Precondition check - preconditions must be met before execution
"""

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

# Registry path - relative to this module's parent directory
SCRIPT_REGISTRY_PATH = Path(__file__).parent / "SCRIPT_REGISTRY.json"
SCRIPTS_DIR = Path(__file__).parent / "scripts"


def load_registry() -> dict[str, Any]:
    """Load the script registration table."""
    if not SCRIPT_REGISTRY_PATH.exists():
        raise FileNotFoundError(f"Script registry not found: {SCRIPT_REGISTRY_PATH}")

    with open(SCRIPT_REGISTRY_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def get_script_meta(script_name: str, registry: dict[str, Any]) -> dict[str, Any] | None:
    """Get metadata for a registered script."""
    return registry["scripts"].get(script_name)


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
    # Unified ledger path - same source of truth across all modules
    from runtime_ledger import CURRENT_RUNTIME_LEDGER_PATH

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

        # Check for existing ledger - use unified path
        if CURRENT_RUNTIME_LEDGER_PATH.exists():
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
    # This is set by start_formal_runtime_chain.py when calling phase scripts
    orchestrator_marker = os.environ.get("TMUX_ORCHESTRATOR_CONTEXT", "")
    return orchestrator_marker == "true"


def is_internal_call() -> bool:
    """Check if this is an internal library call (not for external users)."""
    # Internal calls are marked with TMUX_INTERNAL_CALL
    internal_marker = os.environ.get("TMUX_INTERNAL_CALL", "")
    return internal_marker == "true"


def check_precondition(precondition: str, script_meta: dict[str, Any]) -> bool:
    """Check if a precondition is satisfied."""
    # Unified ledger path - same source of truth across all modules
    from runtime_ledger import CURRENT_RUNTIME_LEDGER_PATH

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
            # Check ledger for slot_bindings - use unified path
            if not CURRENT_RUNTIME_LEDGER_PATH.exists():
                return False
            with open(CURRENT_RUNTIME_LEDGER_PATH, "r", encoding="utf-8") as f:
                ledger = json.load(f)
            slot_bindings = ledger.get("slot_bindings", [])
            return len(slot_bindings) > 0

        elif precondition == "watcher_armed":
            # Check ledger for watcher status - use unified path
            if not CURRENT_RUNTIME_LEDGER_PATH.exists():
                return False
            with open(CURRENT_RUNTIME_LEDGER_PATH, "r", encoding="utf-8") as f:
                ledger = json.load(f)
            watcher = ledger.get("watcher", {})
            return watcher.get("armed", False) is True

        elif precondition == "ledger_initialized":
            # Use unified path
            return CURRENT_RUNTIME_LEDGER_PATH.exists()

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
            # Check if specific pane exists (simplified - same as panes_exist for now)
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


def validate_script(script_name: str, registry: dict[str, Any], skip_orchestrator_check: bool = False) -> tuple[bool, list[str], list[str]]:
    """
    Validate a script request against the registry.

    Args:
        script_name: Name of the script to validate
        registry: Loaded registry dictionary
        skip_orchestrator_check: If True, skip orchestrator context check (used when caller is already the orchestrator)

    Returns:
        tuple[bool, list[str], list[str]]: (success, list of error messages, list of warnings)
    """
    errors: list[str] = []
    warnings: list[str] = []

    # Step 1: Check if script is registered
    if script_name not in registry["scripts"]:
        errors.append(f"Script '{script_name}' is not registered")
        return False, errors, warnings

    script_meta = registry["scripts"][script_name]

    # Step 2: Check status
    status = script_meta["status"]
    if status == "disabled":
        errors.append(f"Script '{script_name}' is disabled")
        return False, errors, warnings
    elif status == "deprecated":
        warnings.append(f"Script '{script_name}' is deprecated")
        if script_meta.get("deprecation", {}).get("alternative"):
            alt = script_meta["deprecation"]["alternative"]
            warnings.append(f"  -> Use '{alt}' instead")

    # Step 3: Check visibility
    visibility = script_meta["visibility"]
    if visibility == "orchestrator_only":
        if not skip_orchestrator_check and not is_orchestrator_context():
            errors.append(f"Script '{script_name}' can only be called by orchestrator")
            return False, errors, warnings

    if visibility == "internal_only":
        if not is_internal_call():
            errors.append(f"Script '{script_name}' is for internal use only")
            return False, errors, warnings

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

    return len(errors) == 0, errors, warnings


def execute_script(script_name: str, script_meta: dict[str, Any], args: list[str], capture_output: bool = False) -> tuple[int, str, str]:
    """
    Execute a script with the given arguments.

    Args:
        script_name: Name of the script
        script_meta: Script metadata from registry
        args: Command line arguments
        capture_output: If True, capture stdout/stderr; if False, pass through to terminal

    Returns:
        tuple[int, str, str]: (returncode, stdout, stderr)
    """
    entry_point = SCRIPTS_DIR / script_meta["entry_point"]

    if not entry_point.exists():
        return 1, "", f"Script entry point not found: {entry_point}"

    # Build command
    cmd = [sys.executable, str(entry_point)] + args

    # Set scheduler context markers
    env = os.environ.copy()
    env["TMUX_VIA_SCHEDULER"] = "true"  # Primary marker for runtime_enforcement
    if is_orchestrator_context():
        env["TMUX_ORCHESTRATOR_CONTEXT"] = "true"

    try:
        if capture_output:
            result = subprocess.run(cmd, env=env, capture_output=True, text=True)
        else:
            result = subprocess.run(cmd, env=env)
        return result.returncode, result.stdout, result.stderr
    except subprocess.SubprocessError as e:
        return 1, "", f"Failed to execute script: {e}"


def run_script_via_scheduler(script_name: str, args: list[str], capture_output: bool = False) -> tuple[bool, dict[str, Any]]:
    """
    Run a script through the scheduler with full validation.

    Args:
        script_name: Name of the script to run
        args: Command line arguments
        capture_output: If True, capture output; if False, pass through

    Returns:
        tuple[bool, dict[str, Any]]: (success, result dictionary)
    """
    result: dict[str, Any] = {
        "script_name": script_name,
        "success": False,
        "errors": [],
        "warnings": [],
        "returncode": None,
        "stdout": "",
        "stderr": "",
    }

    # Step 1: Load registry
    try:
        registry = load_registry()
    except FileNotFoundError as e:
        result["errors"].append(f"Registry not found: {e}")
        return False, result
    except json.JSONDecodeError as e:
        result["errors"].append(f"Invalid registry JSON: {e}")
        return False, result

    # Step 2: Validate script
    success, errors, warnings = validate_script(script_name, registry)
    result["warnings"] = warnings

    if not success:
        result["errors"] = errors
        return False, result

    script_meta = registry["scripts"][script_name]

    # Print warnings
    for warning in warnings:
        sys.stderr.write(f"WARNING: {warning}\n")

    # Step 3: Execute script
    returncode, stdout, stderr = execute_script(script_name, script_meta, args, capture_output)
    result["returncode"] = returncode
    result["stdout"] = stdout
    result["stderr"] = stderr

    if returncode != 0:
        result["errors"].append(f"Script exited with code {returncode}")
        if stderr:
            result["errors"].append(stderr)
        return False, result

    result["success"] = True
    return True, result


def run_json_script(script_name: str, args: list[str], step: str) -> dict[str, Any]:
    """
    Run a script and parse its JSON output.

    Args:
        script_name: Name of the script
        args: Command line arguments
        step: Step name for error reporting

    Returns:
        dict[str, Any]: Parsed JSON output

    Raises:
        RuntimeError: If validation fails or script returns non-JSON/non-zero
    """
    # Add --pretty to args for better JSON output
    if "--pretty" not in args:
        args = args + ["--pretty"]

    success, result = run_script_via_scheduler(script_name, args, capture_output=True)

    if not success:
        error_msg = "; ".join(result.get("errors", []))
        raise RuntimeError(f"{step} failed: {error_msg}")

    # Parse JSON output
    try:
        return json.loads(result["stdout"])
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"{step} returned non-JSON output: {exc}") from exc


def list_scripts(registry: dict[str, Any]) -> None:
    """List all registered scripts in a formatted table."""
    print("\n=== tmux-runtime Script Registry ===\n")
    print(f"{'Script':<40} {'Status':<12} {'Visibility':<18} {'Preconditions':<30}")
    print("-" * 100)

    for script_name, script_meta in sorted(registry["scripts"].items()):
        status = script_meta.get("status", "unknown")
        visibility = script_meta.get("visibility", "unknown")
        preconditions = script_meta.get("preconditions", [])
        precond_str = ", ".join(preconditions) if preconditions else "-"

        # Add status indicators
        if status == "disabled":
            status = "DISABLED"
        elif status == "deprecated":
            status = "DEPRECATED"

        print(f"{script_name:<40} {status:<12} {visibility:<18} {precond_str:<30}")

    print(f"\nTotal: {len(registry['scripts'])} scripts")


def run_script(script_name: str, args: list[str]) -> int:
    """
    Run a script through the scheduler (main entry point).

    Args:
        script_name: Name of the script to run
        args: Command line arguments

    Returns:
        int: Exit code (0 for success, 1 for failure)
    """
    success, result = run_script_via_scheduler(script_name, args, capture_output=False)

    if success:
        return 0
    else:
        for error in result.get("errors", []):
            sys.stderr.write(f"ERROR: {error}\n")
        return 1


# Convenience functions for orchestrator usage
def set_orchestrator_context():
    """Set the orchestrator context environment variable."""
    os.environ["TMUX_ORCHESTRATOR_CONTEXT"] = "true"


def clear_orchestrator_context():
    """Clear the orchestrator context environment variable."""
    os.environ.pop("TMUX_ORCHESTRATOR_CONTEXT", None)
