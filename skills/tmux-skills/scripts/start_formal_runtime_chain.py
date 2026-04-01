#!/usr/bin/env python3
"""Run the public tmux-skills flow: generate panes, label them, and arm stopped-pane reporting."""

from __future__ import annotations

import argparse
import json
import os
import shlex
import signal
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

# Phase timing tracking
_phase_timings = {}
_phase_start_time = None

# Add parent directory to path for module imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from runtime_ledger import DEFAULT_FORMAL_SESSION_NAME
from tmux_runtime_common import (
    describe_formal_client_state,
    inspect_runtime,
    normalize_pane_title,
    pane_is_claude_runtime_surface,
)
from tmux_scheduler import (
    ensure_project_python,
    resolve_project_python,
    run_json_script,
    set_orchestrator_context,
    is_hidden_pty,
)


ROOT = Path("/Users/busiji/workbot")
SCRIPTS_DIR = ROOT / "skills" / "tmux-skills" / "scripts"
CLAUDE_PROJECT_AGENTS_DIR = ROOT / ".claude" / "agents"

ENV_SCRIPT = SCRIPTS_DIR / "init_tmux_env.py"
TOPOLOGY_SCRIPT = SCRIPTS_DIR / "build_tmux_topology.py"
PANE_INIT_SCRIPT = SCRIPTS_DIR / "init_tmux_panes.py"
LEDGER_SCRIPT = SCRIPTS_DIR / "init_runtime_ledger.py"
WATCHER_SCRIPT = SCRIPTS_DIR / "arm_tmux_handoff_watcher.py"
READY_CHECK_SCRIPT = SCRIPTS_DIR / "check_tmux_ready.py"
WATCHER_WORKER_SCRIPT = SCRIPTS_DIR / "watch_tmux_handoff.py"
DELIVERY_RUNNER_SCRIPT = SCRIPTS_DIR / "deliver_tmux_handoff_notification.py"
BRIDGE_WORKER_SCRIPT = SCRIPTS_DIR / "tmux_handoff_app_bridge.py"
TMUX_RUNTIME_ARTIFACT_DIR = ROOT / "workspace" / "artifacts" / "tmux-runtime"
TMUX_SKILLS_ARTIFACT_DIR = ROOT / "workspace" / "artifacts" / "tmux-skills"
CURRENT_RUNTIME_LEDGER_PATH = TMUX_RUNTIME_ARTIFACT_DIR / "current-runtime.json"
LAST_RUNTIME_ISSUES_PATH = TMUX_RUNTIME_ARTIFACT_DIR / "last-runtime-issues.json"
LAST_START_RESULT_PATH = TMUX_RUNTIME_ARTIFACT_DIR / "last-start-formal-runtime-result.json"
START_RESULT_PATH_ENV = "TMUX_START_RESULT_PATH"
START_TEST_START_MS_ENV = "TMUX_START_TEST_START_MS"
CHAIN_CONTEXT_PATH_ENV = "TMUX_CHAIN_CONTEXT_PATH"
HANDOFF_LOG_PATH = TMUX_SKILLS_ARTIFACT_DIR / "handoff-notifications.jsonl"
HANDOFF_SQLITE_PATH = TMUX_SKILLS_ARTIFACT_DIR / "handoff-notifications.sqlite3"
WATCHER_STDOUT_LOG_PATH = TMUX_SKILLS_ARTIFACT_DIR / "watch-tmux-handoff.stdout.log"
DELIVERY_STDOUT_LOG_PATH = TMUX_SKILLS_ARTIFACT_DIR / "deliver-tmux-handoff.stdout.log"
DELIVERY_QUEUE_DIR = TMUX_SKILLS_ARTIFACT_DIR / "delivery-queue"
CHAIN_STDOUT_LOG_PATH = TMUX_SKILLS_ARTIFACT_DIR / "start-formal-runtime-chain.stdout.log"
BRIDGE_STDOUT_LOG_PATH = TMUX_SKILLS_ARTIFACT_DIR / "tmux-handoff-window-ipc-bridge.stdout.log"
BRIDGE_PID_FILE_PATH = TMUX_SKILLS_ARTIFACT_DIR / "tmux-handoff-window-ipc-bridge.pid"
BRIDGE_LOCK_FILE_PATH = TMUX_SKILLS_ARTIFACT_DIR / "tmux-handoff-window-ipc-bridge.lock"
BRIDGE_STARTUP_LOCK_FILE_PATH = TMUX_SKILLS_ARTIFACT_DIR / "tmux-handoff-window-ipc-bridge-startup.lock"
BRIDGE_RECEIPTS_LOG_PATH = TMUX_SKILLS_ARTIFACT_DIR / "window-ipc-delivery-receipts.jsonl"
POST_LAUNCH_CONTEXT_PATH = TMUX_RUNTIME_ARTIFACT_DIR / "post-launch-context.json"
TERMINAL_APP_WINDOW_BOUNDS = (20, 40, 1720, 1120)
TERMINAL_APP_RESULT_TIMEOUT_SECONDS = 60.0
WATCHER_ATTACH_TIMEOUT_SECONDS = 15.0
WATCHER_ATTACH_POLL_INTERVAL_SECONDS = 0.2
FINAL_CHAIN = [
    "tmux_preflight",
    "cleanup",
    "env",
    "topology",
    "titles",
    "ledger",
    "surface_normalization",
    "claude_boot",
    "identity_injection",
]


# ==============================================================================
# Phase Timing Helpers - Machine readable JSON output
# ==============================================================================
def start_phase(phase_name: str) -> None:
    """Mark the start of a phase."""
    global _phase_start_time
    _phase_start_time = time.perf_counter()


def end_phase(phase_name: str, status: str = "ok", error: str = None) -> None:
    """Mark the end of a phase and record timing."""
    global _phase_start_time, _phase_timings
    if _phase_start_time is not None:
        elapsed = time.perf_counter() - _phase_start_time
        _phase_timings[phase_name] = {
            "phase": phase_name,
            "elapsed_ms": round(elapsed * 1000, 2),
            "status": status,
        }
        if error:
            _phase_timings[phase_name]["error"] = error
        _phase_start_time = None


def get_phase_timings() -> dict[str, Any]:
    """Get all recorded phase timings."""
    return _phase_timings


def get_total_elapsed_ms() -> float:
    """Get total elapsed time in milliseconds."""
    total = sum(t.get("elapsed_ms", 0) for t in _phase_timings.values())
    return round(total, 2)


def now_ms() -> int:
    return int(time.time() * 1000)


def result_output_path() -> Path:
    override = str(os.environ.get(START_RESULT_PATH_ENV, "")).strip()
    if override:
        return Path(override).expanduser()
    return LAST_START_RESULT_PATH


def persist_chain_result(result: dict[str, Any]) -> None:
    path = result_output_path()
    payload = dict(result)
    payload["result_path"] = str(path)
    payload["recorded_at"] = datetime.now(timezone.utc).isoformat()
    payload["recorded_at_ms"] = now_ms()

    start_ms_raw = str(os.environ.get(START_TEST_START_MS_ENV, "")).strip()
    if start_ms_raw.isdigit():
        payload["external_wall_elapsed_ms"] = payload["recorded_at_ms"] - int(start_ms_raw)

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def emit_surface_summary(result: dict[str, Any], *, continue_inside_formal: bool, pretty: bool) -> None:
    """Keep work panes clean: use concise summaries in the formal pane, full JSON elsewhere."""
    if continue_inside_formal:
        status = str(result.get("status", "")).strip() or "unknown"
        result_path = str(result.get("result_path", "")).strip() or str(result_output_path())
        if status == "ok":
            return

        error = str(result.get("error", "")).strip() or "unknown error"
        sys.stderr.write(f"tmux runtime startup failed: {error}\n")
        sys.stderr.write(f"details: {result_path}\n")
        return

    print(json.dumps(result, ensure_ascii=False, indent=2 if pretty else None))


def build_launch_path_explanation(
    args: argparse.Namespace,
    *,
    pane_titles: list[str],
    pane_count: int,
    hidden_pty: bool,
) -> dict[str, Any]:
    pane_count_matches_titles = pane_count == len(pane_titles)
    will_use_terminal_app = bool(hidden_pty and not args.continue_inside_formal)
    if hidden_pty:
        if args.continue_inside_formal:
            reason = "Hidden PTY detected - tmux-skills continuation must run from a visible terminal"
            next_step = "fail_fast"
        else:
            reason = "Public hidden PTY must route through Terminal.app to create a visible tmux client"
            next_step = "launch_via_terminal_app"
    elif args.continue_inside_formal:
        reason = "Continuation can run inside the already visible formal tmux client"
        next_step = "run_inside_formal"
    else:
        reason = "Public entry can continue in the current visible terminal"
        next_step = "launch_clean_formal_session"

    explanation = {
        "mode": "launch_path_explanation",
        "entry_mode": "inside_formal_continuation" if args.continue_inside_formal else "public_entry",
        "formal_session": args.formal_session,
        "pane_count": pane_count,
        "pane_titles": pane_titles,
        "pane_count_matches_titles": pane_count_matches_titles,
        "continue_inside_formal": bool(args.continue_inside_formal),
        "hidden_pty": bool(hidden_pty),
        "will_use_terminal_app": will_use_terminal_app,
        "terminal_app_window_bounds": list(TERMINAL_APP_WINDOW_BOUNDS) if will_use_terminal_app else [],
        "codex_thread_id_supplied": bool(str(args.codex_thread_id or "").strip()),
        "next_step": next_step,
        "reason": reason,
    }
    if not pane_count_matches_titles:
        explanation["input_issue"] = (
            f"pane-count must be {len(pane_titles)} for this run (got {pane_count})"
        )
    return explanation


def build_terminal_app_command(args: argparse.Namespace, *, result_path: Path, start_ms: str) -> str:
    command = [
        resolve_project_python(),
        str(Path(__file__).resolve()),
        "--codex-thread-id",
        args.codex_thread_id,
        "--formal-session",
        args.formal_session,
        "--task-id",
        args.task_id,
    ]
    if args.pane_count is not None:
        command.extend(["--pane-count", str(args.pane_count)])
    for title in args.pane_titles:
        command.extend(["--pane-title", str(title)])
    if args.pretty:
        command.append("--pretty")

    env_prefix = " ".join(
        [
            f"{START_RESULT_PATH_ENV}={shlex.quote(str(result_path))}",
            f"{START_TEST_START_MS_ENV}={shlex.quote(start_ms)}",
        ]
    )
    quoted_command = " ".join(shlex.quote(part) for part in command)
    shell_path = os.environ.get("SHELL") or "/bin/zsh"
    return (
        f"cd {shlex.quote(str(ROOT))} && "
        f"{env_prefix} {quoted_command}; rc=$?; "
        "printf '\\n__TMUX_SKILLS_EXIT__=%s\\n' \"$rc\"; "
        f"if [ $rc -ne 0 ]; then exec {shlex.quote(shell_path)} -l; fi"
    )


def wait_for_result_file(path: Path, timeout_seconds: float = TERMINAL_APP_RESULT_TIMEOUT_SECONDS) -> dict[str, Any]:
    deadline = time.monotonic() + max(1.0, timeout_seconds)
    while time.monotonic() < deadline:
        if path.exists():
            try:
                raw = path.read_text(encoding="utf-8").strip()
            except OSError:
                raw = ""
            if raw:
                try:
                    payload = json.loads(raw)
                except json.JSONDecodeError:
                    time.sleep(0.2)
                    continue
                if isinstance(payload, dict):
                    return payload
        time.sleep(0.2)
    raise TimeoutError(f"timed out waiting for startup result at {path}")


def launch_via_terminal_app(args: argparse.Namespace, steps: dict[str, Any]) -> dict[str, Any]:
    result_path = result_output_path()
    try:
        result_path.unlink()
    except FileNotFoundError:
        pass
    result_path.parent.mkdir(parents=True, exist_ok=True)

    start_ms = str(os.environ.get(START_TEST_START_MS_ENV, "")).strip()
    if not start_ms.isdigit():
        start_ms = str(now_ms())

    command_text = build_terminal_app_command(args, result_path=result_path, start_ms=start_ms)
    left, top, right, bottom = TERMINAL_APP_WINDOW_BOUNDS
    apple_script = f"""on run argv
  set commandText to item 1 of argv
  tell application "Terminal"
    activate
    do script ""
    delay 0.3
    set bounds of front window to {{{left}, {top}, {right}, {bottom}}}
    do script commandText in front window
  end tell
end run
"""
    steps["launcher_visibility"] = {
        "mode": "terminal_app_autoroute",
        "visible_terminal_client": False,
        "app": "Terminal.app",
    }
    steps["launcher"] = {
        "mode": "terminal_app_autoroute",
        "result_path": str(result_path),
        "window_bounds": [left, top, right, bottom],
        "command_text": command_text,
    }

    proc = subprocess.run(
        ["osascript", "-", command_text],
        input=apple_script,
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or "failed to launch Terminal.app").strip()
        raise RuntimeError(f"failed to launch Terminal.app: {detail}")

    launch_output = (proc.stdout or "").strip()
    if launch_output:
        steps["launcher"]["osascript_stdout"] = launch_output

    return wait_for_result_file(result_path)


def write_chain_context(steps: dict[str, Any], *, path: Optional[Path] = None) -> str:
    payload = {
        "steps": steps,
        "phase_timings": get_phase_timings(),
    }
    if path is None:
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".json",
            prefix="tmux-chain-context-",
            delete=False,
            encoding="utf-8",
        ) as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            return handle.name

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return str(path)


def load_chain_context() -> dict[str, Any]:
    context_path = str(os.environ.get(CHAIN_CONTEXT_PATH_ENV, "")).strip()
    if not context_path:
        return {}
    path = Path(context_path)
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    finally:
        safe_unlink(path)

    saved_timings = payload.get("phase_timings")
    if isinstance(saved_timings, dict):
        _phase_timings.update(saved_timings)

    saved_steps = payload.get("steps")
    return saved_steps if isinstance(saved_steps, dict) else {}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Public tmux-skills flow: formal-session -> pane generation -> title application -> Claude boot -> identity injection"
    )
    parser.add_argument(
        "--codex-thread-id",
        dest="codex_thread_id",
        help="Thread id of the dedicated monitor-thread delivery target. Bound into tmux as CODEX_THREAD_ID.",
    )
    parser.add_argument(
        "--formal-session",
        default=DEFAULT_FORMAL_SESSION_NAME,
        help=f"Formal tmux session name. Defaults to {DEFAULT_FORMAL_SESSION_NAME}.",
    )
    parser.add_argument(
        "--pane-count",
        type=int,
        help="Pane count to generate. Defaults to the number of pane titles provided.",
    )
    parser.add_argument(
        "--pane-title",
        action="append",
        dest="pane_titles",
        default=[],
        help="Pane title in display order. Repeat for each pane.",
    )
    parser.add_argument(
        "--task-id",
        default="tmux-skills-public-run",
        help="Task identifier stored in the runtime ledger.",
    )
    parser.add_argument(
        "--continue-inside-formal",
        action="store_true",
        help="Internal continuation mode that runs inside a freshly created visible formal-session.",
    )
    parser.add_argument(
        "--continue-post-launch",
        action="store_true",
        help="Internal post-launch mode that completes Claude boot and identity injection.",
    )
    parser.add_argument(
        "--explain-launch-path",
        action="store_true",
        help="Explain whether the current invocation will route through Terminal.app or continue directly.",
    )
    parser.add_argument("--pretty", action="store_true", help="Pretty-print result JSON.")
    args = parser.parse_args()
    if not args.explain_launch_path and not str(args.codex_thread_id or "").strip():
        parser.error("--codex-thread-id is required unless --explain-launch-path is set")
    return args


def run(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, capture_output=True, text=True, check=False)


def run_json_with_status(command: list[str], *, step: str) -> tuple[dict[str, Any], int]:
    proc = run(command)
    raw = (proc.stdout or "").strip()
    if not raw:
        raise RuntimeError(f"{step} returned empty output")
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"{step} returned non-JSON output: {exc}") from exc
    if not isinstance(payload, dict):
        raise RuntimeError(f"{step} returned non-object JSON output")
    return payload, int(proc.returncode)


def wait_for_pid_exit(pid: int, timeout_seconds: float = 3.0) -> None:
    deadline = time.monotonic() + max(0.1, timeout_seconds)
    while time.monotonic() < deadline:
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return
        time.sleep(0.05)
    try:
        os.kill(pid, signal.SIGKILL)
    except ProcessLookupError:
        return


def list_existing_watcher_processes() -> list[dict[str, Any]]:
    proc = run(["ps", "ax", "-o", "pid=,command="])
    processes: list[dict[str, Any]] = []
    watcher_path = str(WATCHER_WORKER_SCRIPT)
    for raw in proc.stdout.splitlines():
        if not raw.strip():
            continue
        pid_text, _, command = raw.strip().partition(" ")
        if not pid_text.isdigit():
            continue
        command = command.strip()
        if watcher_path not in command:
            continue
        processes.append({"pid": int(pid_text), "command": command})
    return processes


def stop_processes(processes: list[dict[str, Any]]) -> list[int]:
    stopped: list[int] = []
    for process in processes:
        pid = int(process["pid"])
        try:
            os.kill(pid, signal.SIGTERM)
        except ProcessLookupError:
            continue
        stopped.append(pid)
        wait_for_pid_exit(pid)
    return stopped


def stop_existing_watchers() -> list[int]:
    return stop_processes(list_existing_watcher_processes())


def list_existing_delivery_runner_processes() -> list[dict[str, Any]]:
    proc = run(["ps", "ax", "-o", "pid=,command="])
    processes: list[dict[str, Any]] = []
    delivery_path = str(DELIVERY_RUNNER_SCRIPT)
    for raw in proc.stdout.splitlines():
        if not raw.strip():
            continue
        pid_text, _, command = raw.strip().partition(" ")
        if not pid_text.isdigit():
            continue
        command = command.strip()
        if delivery_path not in command:
            continue
        processes.append({"pid": int(pid_text), "command": command})
    return processes


def list_existing_bridge_processes() -> list[dict[str, Any]]:
    proc = run(["ps", "ax", "-o", "pid=,command="])
    processes: list[dict[str, Any]] = []
    bridge_path = str(BRIDGE_WORKER_SCRIPT)
    for raw in proc.stdout.splitlines():
        if not raw.strip():
            continue
        pid_text, _, command = raw.strip().partition(" ")
        if not pid_text.isdigit():
            continue
        command = command.strip()
        if bridge_path not in command:
            continue
        processes.append({"pid": int(pid_text), "command": command})
    return processes


def stop_existing_bridges() -> list[int]:
    return stop_processes(list_existing_bridge_processes())


def list_runtime_cleanup_artifacts() -> dict[str, list[str]]:
    artifact_files: list[str] = []
    for path in (
        CURRENT_RUNTIME_LEDGER_PATH,
        LAST_RUNTIME_ISSUES_PATH,
        POST_LAUNCH_CONTEXT_PATH,
        HANDOFF_LOG_PATH,
        HANDOFF_SQLITE_PATH,
        WATCHER_STDOUT_LOG_PATH,
        DELIVERY_STDOUT_LOG_PATH,
        CHAIN_STDOUT_LOG_PATH,
        BRIDGE_STDOUT_LOG_PATH,
        BRIDGE_PID_FILE_PATH,
        BRIDGE_LOCK_FILE_PATH,
        BRIDGE_STARTUP_LOCK_FILE_PATH,
        BRIDGE_RECEIPTS_LOG_PATH,
    ):
        if path.exists():
            artifact_files.append(str(path))
    queue_files = sorted(str(path) for path in DELIVERY_QUEUE_DIR.glob("*.json") if path.is_file())
    return {
        "artifact_files": artifact_files,
        "delivery_queue_files": queue_files,
    }


def list_runtime_cleanup_inventory() -> dict[str, Any]:
    return {
        "watcher_processes": list_existing_watcher_processes(),
        "bridge_processes": list_existing_bridge_processes(),
        "delivery_runner_processes": list_existing_delivery_runner_processes(),
        **list_runtime_cleanup_artifacts(),
    }


def safe_unlink(path: Path) -> bool:
    try:
        path.unlink()
        return True
    except FileNotFoundError:
        return False


def clear_directory(path: Path) -> list[str]:
    removed: list[str] = []
    if not path.exists():
        return removed
    for child in sorted(path.iterdir()):
        if not child.is_file():
            continue
        if safe_unlink(child):
            removed.append(str(child))
    return removed


def unset_tmux_env(name: str) -> str:
    proc = run(["tmux", "set-environment", "-gu", name])
    if proc.returncode == 0:
        return "cleared"
    detail = (proc.stderr or proc.stdout or "").strip().lower()
    if "no server running" in detail or "failed to connect" in detail:
        return "no_tmux_server"
    return "not_cleared"


def cleanup_previous_runtime_state() -> dict[str, Any]:
    inventory = list_runtime_cleanup_inventory()
    stopped_watcher_pids = stop_processes(list(inventory["watcher_processes"]))
    stopped_bridge_pids = stop_processes(list(inventory["bridge_processes"]))
    stopped_delivery_runner_pids = stop_processes(list(inventory["delivery_runner_processes"]))
    removed_files: list[str] = []
    for path in (
        CURRENT_RUNTIME_LEDGER_PATH,
        LAST_RUNTIME_ISSUES_PATH,
        POST_LAUNCH_CONTEXT_PATH,
        HANDOFF_LOG_PATH,
        HANDOFF_SQLITE_PATH,
        WATCHER_STDOUT_LOG_PATH,
        DELIVERY_STDOUT_LOG_PATH,
        CHAIN_STDOUT_LOG_PATH,
        BRIDGE_STDOUT_LOG_PATH,
        BRIDGE_PID_FILE_PATH,
        BRIDGE_LOCK_FILE_PATH,
        BRIDGE_STARTUP_LOCK_FILE_PATH,
        BRIDGE_RECEIPTS_LOG_PATH,
    ):
        if safe_unlink(path):
            removed_files.append(str(path))
    removed_files.extend(clear_directory(DELIVERY_QUEUE_DIR))
    tmux_env_status = unset_tmux_env("CODEX_THREAD_ID")
    return {
        "existing_watcher_processes": inventory["watcher_processes"],
        "existing_bridge_processes": inventory["bridge_processes"],
        "existing_delivery_runner_processes": inventory["delivery_runner_processes"],
        "existing_artifact_files": inventory["artifact_files"],
        "existing_delivery_queue_files": inventory["delivery_queue_files"],
        "removed_files": removed_files,
        "stopped_watcher_pids": stopped_watcher_pids,
        "stopped_bridge_pids": stopped_bridge_pids,
        "stopped_delivery_runner_pids": stopped_delivery_runner_pids,
        "tmux_env": {
            "CODEX_THREAD_ID": tmux_env_status,
        },
    }


def ensure_attached_formal_session(snapshot: dict[str, Any], formal_session: str) -> None:
    formal_state = describe_formal_client_state(snapshot, formal_session)
    formal_client_count = int(formal_state["formal_client_count"])
    if formal_client_count <= 0:
        raise RuntimeError(
            f"formal session '{formal_session}' has no attached tmux client; foreground tmux is not visible"
        )
    visible_formal_client_count = int(formal_state["visible_formal_client_count"])
    if visible_formal_client_count != 1:
        raise RuntimeError(
            f"formal session '{formal_session}' must have exactly one visible tmux client; got {visible_formal_client_count}"
        )
    if not formal_state["startup_client_ready"]:
        raise RuntimeError(
            f"formal session '{formal_session}' is attached but not visible in a real terminal client"
        )


def wait_for_attached_formal_session(
    formal_session: str,
    *,
    timeout_seconds: float = WATCHER_ATTACH_TIMEOUT_SECONDS,
    poll_interval_seconds: float = WATCHER_ATTACH_POLL_INTERVAL_SECONDS,
) -> dict[str, Any]:
    deadline = time.monotonic() + max(timeout_seconds, poll_interval_seconds)
    started_at = time.monotonic()
    attempts = 0
    last_error = ""
    while True:
        attempts += 1
        snapshot = inspect_runtime_snapshot(step="watcher_attach_gate", formal_session=formal_session)
        try:
            ensure_attached_formal_session(snapshot, formal_session)
            return {
                "formal_session_name": formal_session,
                "status": "attached",
                "attempts": attempts,
                "waited_ms": round((time.monotonic() - started_at) * 1000, 2),
                "formal_client_state": describe_formal_client_state(snapshot, formal_session),
            }
        except RuntimeError as exc:
            last_error = str(exc)
            if time.monotonic() >= deadline:
                break
            time.sleep(max(0.05, poll_interval_seconds))
    raise RuntimeError(
        f"formal session '{formal_session}' did not become attached before watcher arm: "
        f"{last_error or 'unknown watcher attach gate failure'}"
    )


def parse_target(target: str) -> tuple[int, int]:
    pane = target.split(":", 1)[1]
    window_index, pane_index = pane.split(".", 1)
    return int(window_index), int(pane_index)


def resolve_project_claude_agent_path(pane_title: str) -> Optional[Path]:
    normalized = str(pane_title).strip()
    if not normalized:
        return None
    agent_path = CLAUDE_PROJECT_AGENTS_DIR / f"{normalized}.md"
    if not agent_path.is_file():
        return None
    return agent_path


def resolve_project_claude_agent_name(pane_title: str) -> Optional[str]:
    agent_path = resolve_project_claude_agent_path(pane_title)
    if not agent_path:
        return None
    return agent_path.stem


def build_login_shell_exec_command() -> str:
    shell_path = os.environ.get("SHELL") or "/bin/zsh"
    return f"exec {shlex.quote(shell_path)} -l"


def build_claude_exec_command() -> str:
    return (
        f"cd {shlex.quote(str(ROOT))} && "
        "exec claude"
    )


def build_current_pane_exec_command(pane_titles: list[str]) -> str:
    current_title = str(pane_titles[0]).strip() if pane_titles else ""
    agent_name = resolve_project_claude_agent_name(current_title)
    if agent_name:
        return build_claude_exec_command()
    return build_login_shell_exec_command()


def build_post_launch_command(args: argparse.Namespace) -> str:
    command: list[str] = [
        resolve_project_python(),
        str(Path(__file__)),
        "--codex-thread-id",
        args.codex_thread_id,
        "--formal-session",
        args.formal_session,
        "--task-id",
        args.task_id,
        "--continue-post-launch",
    ]
    if args.pane_count is not None:
        command.extend(["--pane-count", str(args.pane_count)])
    for title in args.pane_titles:
        command.extend(["--pane-title", str(title)])
    if args.pretty:
        command.append("--pretty")

    env_parts = [f"{CHAIN_CONTEXT_PATH_ENV}={shlex.quote(str(POST_LAUNCH_CONTEXT_PATH))}"]
    for env_name in (START_RESULT_PATH_ENV, START_TEST_START_MS_ENV):
        env_value = str(os.environ.get(env_name, "")).strip()
        if env_value:
            env_parts.append(f"{env_name}={shlex.quote(env_value)}")
    env_prefix = f"{' '.join(env_parts)} " if env_parts else ""
    quoted_command = " ".join(shlex.quote(part) for part in command)
    return f"{env_prefix}{quoted_command}"


def select_formal_targets(snapshot: dict[str, Any], formal_session: str) -> list[str]:
    panes = [
        pane
        for pane in snapshot.get("panes", [])
        if pane.get("session_name") == formal_session
    ]
    panes.sort(key=lambda pane: parse_target(str(pane.get("target", ""))))
    return [str(pane.get("target", "")).strip() for pane in panes if str(pane.get("target", "")).strip()]


def resolve_pane_titles(args: argparse.Namespace) -> list[str]:
    pane_titles = [str(title) for title in args.pane_titles]
    if not pane_titles:
        raise SystemExit("at least one --pane-title is required")
    return pane_titles


def build_batch_plan(targets: list[str], pane_titles: list[str]) -> list[dict[str, str]]:
    if len(targets) != len(pane_titles):
        raise RuntimeError(
            f"formal runtime must expose exactly {len(pane_titles)} panes; got {len(targets)}"
        )
    return [
        {
            "target": target,
            "slot": f"pane_{index}",
            "pane_title": title,
        }
        for index, (target, title) in enumerate(zip(targets, pane_titles), start=1)
    ]


def build_slot_binding_args(plan_entries: list[dict[str, str]]) -> list[str]:
    args: list[str] = []
    for entry in plan_entries:
        args.extend(
            [
                "--slot-binding",
                f"{entry['slot']}={entry['pane_title']}@{entry['target']}",
            ]
        )
    return args


def build_result(
    status: str,
    steps: dict[str, Any],
    pane_titles: list[str],
    error: Optional[str] = None,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "status": status,
        "formal_session": steps.get("formal_session", DEFAULT_FORMAL_SESSION_NAME),
        "pane_count": len(pane_titles),
        "pane_titles": pane_titles,
        "chain": FINAL_CHAIN,
        "steps": steps,
        "phase_timings": get_phase_timings(),
        "total_elapsed_ms": get_total_elapsed_ms(),
    }
    if error:
        result["error"] = error
    return result


def inspect_runtime_snapshot(
    *,
    step: str,
    formal_session: Optional[str] = None,
    include_bell_processes: bool = False,
) -> dict[str, Any]:
    """Inspect runtime in-process to avoid deprecated wrapper noise and subprocess overhead."""
    try:
        return inspect_runtime(formal_session, include_bell_processes=include_bell_processes)
    except Exception as exc:
        raise RuntimeError(f"{step} failed: {exc}") from exc


def require_visible_formal_client(snapshot: dict[str, Any], formal_session: str) -> None:
    """Fail-fast guard: require current_visible_formal_client == true before any positive changes.

    This enforces the rule that no topology/init_panes/ledger/watcher steps may proceed
    unless the current client is a visible formal client.
    """
    current_client = snapshot.get("current_client") or {}
    if not snapshot.get("current_visible_formal_client"):
        reason = str(current_client.get("visibility_reason") or "not_visible_formal_client")
        raise RuntimeError(
            f"tmux-skills positive flow requires current_visible_formal_client=true; "
            f"refusing to proceed from {reason}"
        )
    if not current_client.get("inside_tmux"):
        raise RuntimeError(
            "tmux-skills positive flow requires current client to be inside tmux"
        )
    if current_client.get("session_name") != formal_session:
        raise RuntimeError(
            f"tmux-skills positive flow requires current session={formal_session}; "
            f"got {current_client.get('session_name') or '<none>'}"
        )


def require_visible_terminal_launcher(snapshot: dict[str, Any]) -> None:
    current_client = snapshot.get("current_client") or {}
    if current_client.get("inside_tmux"):
        raise RuntimeError(
            "new tmux-skills tasks must start from a fresh visible terminal, not from inside an existing tmux session"
        )
    if not current_client.get("visible_terminal_client"):
        reason = str(current_client.get("visibility_reason") or "invisible_terminal_client")
        raise RuntimeError(
            "new tmux-skills tasks must start from a real visible terminal client; "
            f"refusing startup from {reason}"
        )


def preflight_kill_all_tmux_sessions(snapshot: dict[str, Any]) -> dict[str, Any]:
    current_client = snapshot.get("current_client") or {}
    if current_client.get("inside_tmux"):
        return {
            "attempted": False,
            "blocked": True,
            "reason": "current_tmux_launcher",
            "current_session_name": str(current_client.get("session_name") or "").strip(),
            "session_count_before": int(snapshot.get("session_count", 0) or 0),
            "session_names": [
                str(session.get("session_name") or "").strip()
                for session in snapshot.get("sessions", [])
                if str(session.get("session_name") or "").strip()
            ],
        }

    session_names = [
        str(session.get("session_name") or "").strip()
        for session in snapshot.get("sessions", [])
        if str(session.get("session_name") or "").strip()
    ]
    ordered_sessions: list[str] = []
    for session_name in session_names:
        if session_name not in ordered_sessions:
            ordered_sessions.append(session_name)

    result: dict[str, Any] = {
        "attempted": bool(ordered_sessions),
        "session_names": ordered_sessions,
        "session_count_before": int(snapshot.get("session_count", 0) or 0),
    }
    if not ordered_sessions:
        result["reason"] = "no_tmux_sessions"
        result["cleaned"] = True
        result["killed_sessions"] = []
        return result

    kill_results: list[dict[str, Any]] = []
    cleaned = True
    for session_name in ordered_sessions:
        kill_proc = run(["tmux", "kill-session", "-t", session_name])
        detail = (kill_proc.stderr or kill_proc.stdout or "").strip()
        kill_results.append(
            {
                "session_name": session_name,
                "returncode": kill_proc.returncode,
                "detail": detail,
            }
        )
        if kill_proc.returncode != 0:
            cleaned = False

    result["cleaned"] = cleaned
    result["killed_sessions"] = [item["session_name"] for item in kill_results]
    result["kill_results"] = kill_results
    if kill_results:
        result["kill_returncode"] = kill_results[-1]["returncode"]
        result["kill_detail"] = "; ".join(
            f"{item['session_name']}: {item['detail'] or item['returncode']}"
            for item in kill_results
        )
    return result


def cleanup_hidden_formal_session_on_failure(formal_session: str, error_text: str = "") -> dict[str, Any]:
    try:
        snapshot = inspect_runtime_snapshot(step="failure_inspect", formal_session=formal_session)
    except Exception as exc:
        return {"attempted": False, "reason": f"inspect_failed: {exc}"}

    current_client = snapshot.get("current_client") or {}
    residue_error = "historical formal-session residue" in error_text
    should_cleanup = bool(
        current_client.get("inside_tmux")
        and current_client.get("session_name") == formal_session
        and int(snapshot.get("formal_client_count", 0) or 0) == 1
        and (
            residue_error
            or (
                current_client.get("codex_hosted")
                and not current_client.get("visible_terminal_client")
            )
        )
    )
    result: dict[str, Any] = {
        "attempted": should_cleanup,
        "session_name": formal_session,
        "visibility_reason": current_client.get("visibility_reason", ""),
        "residue_error": residue_error,
    }
    if not should_cleanup:
        result["reason"] = "skip"
        return result

    kill_proc = run(["tmux", "kill-session", "-t", formal_session])
    result["kill_returncode"] = kill_proc.returncode
    result["kill_detail"] = (kill_proc.stderr or kill_proc.stdout or "").strip()
    result["runtime_cleanup"] = cleanup_previous_runtime_state()
    result["cleaned"] = kill_proc.returncode == 0
    return result


def record_failure_to_issues(error_text: str, steps: dict[str, Any], pane_titles: list[str]) -> None:
    """Persist failure details to last-runtime-issues.json for post-mortem analysis."""
    LAST_RUNTIME_ISSUES_PATH.parent.mkdir(parents=True, exist_ok=True)

    # Infer last completed phase from steps
    phase_order = FINAL_CHAIN
    last_completed_phase = "unknown"
    for phase in phase_order:
        if phase in steps:
            last_completed_phase = phase

    issue_record = {
        "failed_at": datetime.now(timezone.utc).isoformat(),
        "error": error_text,
        "steps_completed": {k: v for k, v in steps.items() if v and isinstance(v, (dict, list, str, int, bool))},
        "pane_titles_requested": pane_titles,
        "failure_context": {
            "formal_session": steps.get("formal_session"),
            "last_completed_phase": last_completed_phase,
        },
    }

    # Append to issues file (keep last 10 failures)
    existing_issues = []
    if LAST_RUNTIME_ISSUES_PATH.exists():
        try:
            existing_issues = json.loads(LAST_RUNTIME_ISSUES_PATH.read_text(encoding="utf-8"))
            if not isinstance(existing_issues, list):
                existing_issues = []
        except (json.JSONDecodeError, FileNotFoundError):
            existing_issues = []

    existing_issues.append(issue_record)
    LAST_RUNTIME_ISSUES_PATH.write_text(
        json.dumps(existing_issues[-10:], ensure_ascii=False, indent=2),
        encoding="utf-8"
    )


def run_detect_phase(formal_session: str) -> tuple[dict[str, Any], dict[str, Any]]:
    """Run detect_old_state phase and return detection report (read-only, no mutations)."""
    start_phase("detect")
    try:
        snapshot = inspect_runtime_snapshot(step="detect_old_state", formal_session=formal_session)

        # Build detection report
        formal_sessions = [
            s for s in snapshot.get("sessions", []) if s.get("session_name") == formal_session
        ]
        attached_formal_count = sum(1 for s in formal_sessions if int(s.get("attached", 0)) > 0)

        report = {
            "detection_status": "CLEAN",
            "tmux_server_exists": True,
            "sessions": snapshot.get("sessions", []),
            "session_count": snapshot.get("session_count", 0),
            "formal_session_detected": {
                "exists": len(formal_sessions) > 0,
                "count": len(formal_sessions),
                "attached_count": attached_formal_count,
            },
            "watcher_processes": snapshot.get("bell_processes", []),
            "state_files": {
                "ledger_exists": snapshot.get("runtime_ledger_present", False),
                "issues_exists": LAST_RUNTIME_ISSUES_PATH.exists(),
                "handoff_log_exists": HANDOFF_LOG_PATH.exists(),
            },
            "current_caller_context": snapshot.get("current_client", {}),
            "cleanup_required": bool(snapshot.get("sessions", [])),  # Cleanup if any sessions exist
        }

        # Determine detection status
        if snapshot.get("sessions", []):
            report["detection_status"] = "RESIDUE_DETECTED"
        elif not snapshot.get("runtime_ledger_present"):
            report["detection_status"] = "CLEAN"

        end_phase("detect", "ok")
        return report, snapshot
    except Exception as e:
        end_phase("detect", "failed", str(e))
        raise


def inspect_visible_formal_session(
    formal_session: str,
    *,
    step: str,
) -> dict[str, Any]:
    snapshot = inspect_runtime_snapshot(step=step, formal_session=formal_session)
    extra_sessions = [
        str(session_name).strip()
        for session_name in snapshot.get("session_names", [])
        if str(session_name).strip() and str(session_name).strip() != formal_session
    ]
    if extra_sessions:
        raise RuntimeError(
            "unexpected tmux residue remains after startup: " + ", ".join(extra_sessions)
        )
    ensure_attached_formal_session(snapshot, formal_session)
    return snapshot


def run_formal_env_setup(formal_session: str, steps: dict[str, Any]) -> None:
    start_phase("env")
    # Set orchestrator context before calling phase script
    set_orchestrator_context()

    steps["env"] = run_json_script(
        "init_tmux_env.py",
        [
            "--formal-session",
            formal_session,
            "--formal-cwd",
            str(ROOT),
            "--initialize-formal-surfaces",
            "--formal-window-title",
            formal_session,
        ],
        step="env",
    )
    end_phase("env", "ok")
    steps["inspect_after_env"] = {
        "skipped_full_inspect": True,
        "reason": "env phase only mutates window/pane metadata after visible formal guard",
        "formal_session_count": 1,
        "attached_formal": True,
    }


def apply_formal_session_policy(formal_session: str) -> list[str]:
    proc = run(["tmux", "set-option", "-t", formal_session, "destroy-unattached", "on"])
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or "failed to enable destroy-unattached").strip()
        raise RuntimeError(detail)
    return ["destroy_unattached=on"]


def verify_tmux_cleared(formal_session: str) -> dict[str, Any]:
    snapshot = inspect_runtime_snapshot(step="tmux_preflight_verify", formal_session=formal_session)
    if int(snapshot.get("session_count", 0) or 0) != 0:
        raise RuntimeError(
            "tmux residue remains after preflight cleanup: "
            + ", ".join(str(session.get("session_name") or "") for session in snapshot.get("sessions", []))
        )
    return snapshot


def build_inside_formal_command(args: argparse.Namespace, chain_context_path: str) -> str:
    command: list[str] = [
        resolve_project_python(),
        str(Path(__file__)),
        "--codex-thread-id",
        args.codex_thread_id,
        "--formal-session",
        args.formal_session,
        "--task-id",
        args.task_id,
        "--continue-inside-formal",
    ]
    if args.pane_count is not None:
        command.extend(["--pane-count", str(args.pane_count)])
    for title in args.pane_titles:
        command.extend(["--pane-title", str(title)])
    if args.pretty:
        command.append("--pretty")
    env_parts: list[str] = []
    if chain_context_path:
        env_parts.append(f"{CHAIN_CONTEXT_PATH_ENV}={shlex.quote(chain_context_path)}")
    for env_name in (START_RESULT_PATH_ENV, START_TEST_START_MS_ENV):
        env_value = str(os.environ.get(env_name, "")).strip()
        if env_value:
            env_parts.append(f"{env_name}={shlex.quote(env_value)}")
    env_prefix = f"{' '.join(env_parts)} " if env_parts else ""
    quoted_command = " ".join(shlex.quote(part) for part in command)
    next_command = build_current_pane_exec_command(args.pane_titles)
    post_launch_command = build_post_launch_command(args)
    # Preserve inner continuation failures while still keeping the pane alive on success.
    return (
        f"{env_prefix}{quoted_command}; rc=$?; if [ $rc -ne 0 ]; then exit $rc; fi; "
        f"{post_launch_command} >> {shlex.quote(str(CHAIN_STDOUT_LOG_PATH))} 2>&1 & "
        f"exec /bin/sh -lc {shlex.quote(next_command)}"
    )


def launch_clean_formal_session(args: argparse.Namespace, steps: dict[str, Any]) -> int:
    start_phase("launcher_routing")
    launcher_snapshot = steps.get("_detect_snapshot") or inspect_runtime_snapshot(
        step="launcher_inspect",
        formal_session=args.formal_session,
    )
    require_visible_terminal_launcher(launcher_snapshot)
    steps["launcher_visibility"] = {
        "mode": "verified_before_cleanup",
        "visible_terminal_client": (launcher_snapshot.get("current_client") or {}).get(
            "visible_terminal_client", False
        ),
    }
    end_phase("launcher_routing", "ok")

    start_phase("tmux_launch")
    steps["tmux_preflight"] = preflight_kill_all_tmux_sessions(launcher_snapshot)
    if steps["tmux_preflight"].get("blocked"):
        end_phase("tmux_launch", "blocked", "launcher not in fresh visible terminal")
        raise RuntimeError(
            "new tmux-skills tasks must start from a fresh visible terminal, not from inside an existing tmux session"
        )
    verify_tmux_cleared(args.formal_session)
    end_phase("tmux_launch", "ok")

    start_phase("cleanup")
    steps["cleanup"] = cleanup_previous_runtime_state()
    end_phase("cleanup", "ok")

    chain_context_path = write_chain_context(steps)
    tmux_command = [
        "tmux",
        "new-session",
        "-s",
        args.formal_session,
        "-c",
        str(ROOT),
        build_inside_formal_command(args, chain_context_path),
    ]
    steps["launcher"] = {
        "mode": "fresh_visible_terminal",
        "tmux_command": tmux_command,
    }
    return subprocess.run(tmux_command, check=False).returncode


def bind_tmux_thread_id(codex_thread_id: str) -> dict[str, str]:
    set_env_proc = run(["tmux", "set-environment", "-g", "CODEX_THREAD_ID", codex_thread_id])
    if set_env_proc.returncode != 0:
        detail = (set_env_proc.stderr or set_env_proc.stdout or "tmux set-environment failed").strip()
        raise RuntimeError(detail)
    verify_env_proc = run(["tmux", "show-environment", "-g", "CODEX_THREAD_ID"])
    if verify_env_proc.returncode != 0:
        detail = (
            verify_env_proc.stderr
            or verify_env_proc.stdout
            or "tmux show-environment failed after CODEX_THREAD_ID binding"
        ).strip()
        raise RuntimeError(detail)
    bound_value = verify_env_proc.stdout.strip().partition("=")[2].strip()
    if bound_value != codex_thread_id:
        raise RuntimeError(
            "CODEX_THREAD_ID binding did not persist into tmux: "
            f"expected={codex_thread_id}, actual={bound_value or '<empty>'}"
        )
    return {"CODEX_THREAD_ID": codex_thread_id}


def current_tmux_target() -> str:
    pane_target = str(os.environ.get("TMUX_PANE", "")).strip()
    if pane_target:
        proc = run(
            [
                "tmux",
                "display-message",
                "-p",
                "-t",
                pane_target,
                "#{session_name}:#{window_index}.#{pane_index}",
            ]
        )
        if proc.returncode == 0 and proc.stdout.strip():
            return proc.stdout.strip()
    proc = run(["tmux", "display-message", "-p", "#{session_name}:#{window_index}.#{pane_index}"])
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or proc.stdout.strip() or "failed to resolve current tmux target")
    return proc.stdout.strip()


def normalize_pane_surfaces(targets: list[str]) -> dict[str, Any]:
    current_target = current_tmux_target()
    normalized: list[dict[str, Any]] = []
    for target in targets:
        history_proc = run(["tmux", "clear-history", "-t", target])
        if history_proc.returncode != 0:
            detail = history_proc.stderr.strip() or history_proc.stdout.strip() or "failed to clear pane history"
            raise RuntimeError(f"{target}: {detail}")
        actions = ["clear-history"]
        if target != current_target:
            respawn_proc = run(
                [
                    "tmux",
                    "respawn-pane",
                    "-k",
                    "-t",
                    target,
                    "-c",
                    str(ROOT),
                    str(os.environ.get("SHELL") or "/bin/zsh"),
                    "-l",
                ]
            )
            if respawn_proc.returncode != 0:
                detail = respawn_proc.stderr.strip() or respawn_proc.stdout.strip() or "failed to respawn pane shell"
                raise RuntimeError(f"{target}: {detail}")
            actions.append("respawn-pane:login-shell")
        normalized.append({"target": target, "actions": actions})
    return {
        "current_target": current_target,
        "normalized_targets": normalized,
    }


def boot_project_claude_panes(
    batch_plan: list[dict[str, str]],
    *,
    current_target: str,
) -> dict[str, Any]:
    shell_path = os.environ.get("SHELL") or "/bin/zsh"
    booted: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    for entry in batch_plan:
        target = str(entry["target"]).strip()
        pane_title = str(entry["pane_title"]).strip()
        agent_path = resolve_project_claude_agent_path(pane_title)
        if not agent_path:
            skipped.append(
                {
                    "target": target,
                    "pane_title": pane_title,
                    "reason": "no_matching_project_agent",
                }
            )
            continue

        boot_entry = {
            "target": target,
            "pane_title": pane_title,
            "agent_name": agent_path.stem,
            "agent_path": str(agent_path),
        }
        if target == current_target:
            boot_entry["mode"] = "deferred_exec_after_chain"
            boot_entry["command_preview"] = build_claude_exec_command()
            booted.append(boot_entry)
            continue

        command = [
            "tmux",
            "respawn-pane",
            "-k",
            "-t",
            target,
            "-c",
            str(ROOT),
            shell_path,
            "-lc",
            build_claude_exec_command(),
        ]
        proc = run(command)
        if proc.returncode != 0:
            detail = proc.stderr.strip() or proc.stdout.strip() or "failed to start claude in pane"
            raise RuntimeError(f"{target}: {detail}")
        boot_entry["mode"] = "respawn-pane"
        boot_entry["command"] = command
        booted.append(boot_entry)

    return {
        "current_target": current_target,
        "booted": booted,
        "skipped": skipped,
    }


def query_pane_runtime(target: str) -> dict[str, str]:
    proc = run(
        [
            "tmux",
            "display-message",
            "-p",
            "-t",
            target,
            "#{pane_current_command}\t#{pane_title}",
        ]
    )
    if proc.returncode != 0:
        detail = proc.stderr.strip() or proc.stdout.strip() or "failed to query pane runtime"
        raise RuntimeError(f"{target}: {detail}")
    current_command, _, pane_title = proc.stdout.rstrip("\n").partition("\t")
    return {
        "target": target,
        "current_command": current_command.strip(),
        "pane_title": pane_title.strip(),
        "pane_title_normalized": normalize_pane_title(pane_title.strip()),
    }


def capture_pane_output(target: str, *, start: int = -40) -> str:
    proc = run(
        [
            "tmux",
            "capture-pane",
            "-p",
            "-t",
            target,
            "-S",
            str(start),
        ]
    )
    if proc.returncode != 0:
        detail = proc.stderr.strip() or proc.stdout.strip() or "failed to capture pane output"
        raise RuntimeError(f"{target}: {detail}")
    return proc.stdout.rstrip("\n")


def pane_has_claude_prompt(capture: str) -> bool:
    for raw_line in reversed(capture.splitlines()[-12:]):
        stripped = raw_line.strip()
        if not stripped:
            continue
        if stripped == "❯" or stripped.startswith("❯ "):
            return True
    return False


def wait_for_claude_prompt_after_submit(
    target: str,
    baseline_capture: str,
    *,
    timeout_seconds: float = 20.0,
    poll_interval_seconds: float = 0.2,
) -> Optional[dict[str, str]]:
    deadline = time.monotonic() + max(timeout_seconds, poll_interval_seconds)
    while time.monotonic() < deadline:
        state = query_pane_runtime(target)
        if pane_is_claude_runtime_surface(state, allow_empty_title=True):
            capture = capture_pane_output(target)
            if capture != baseline_capture and pane_has_claude_prompt(capture):
                return {
                    **state,
                    "prompt_ready": "true",
                }
        time.sleep(max(0.05, poll_interval_seconds))
    return None


def wait_for_claude_pane_ready(target: str, *, timeout_seconds: float = 30.0) -> dict[str, str]:
    deadline = time.monotonic() + max(1.0, timeout_seconds)
    last_state: dict[str, str] = {
        "target": target,
        "current_command": "",
        "pane_title": "",
        "pane_title_normalized": "",
    }
    last_capture = ""
    while time.monotonic() < deadline:
        state = query_pane_runtime(target)
        last_state = state
        if pane_is_claude_runtime_surface(state, allow_empty_title=True):
            capture = capture_pane_output(target)
            last_capture = capture
            if pane_has_claude_prompt(capture):
                time.sleep(0.2)
                return {
                    **state,
                    "prompt_ready": "true",
                }
        time.sleep(0.2)
    raise RuntimeError(
        f"{target}: timed out waiting for Claude pane readiness; "
        f"last_state={last_state['current_command'] or '<empty>'}/{last_state['pane_title'] or '<empty>'}; "
        f"prompt_visible={pane_has_claude_prompt(last_capture)}"
    )


def paste_text_into_pane(target: str, text: str) -> dict[str, Any]:
    if not text.strip():
        raise RuntimeError(f"{target}: empty identity payload")

    buffer_name = f"tmux-skills-{os.getpid()}-{now_ms()}"
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", prefix="tmux-agent-", delete=False, encoding="utf-8") as handle:
        handle.write(text)
        temp_path = Path(handle.name)

    try:
        load_proc = run(["tmux", "load-buffer", "-b", buffer_name, str(temp_path)])
        if load_proc.returncode != 0:
            detail = load_proc.stderr.strip() or load_proc.stdout.strip() or "failed to load tmux buffer"
            raise RuntimeError(f"{target}: {detail}")

        paste_proc = run(["tmux", "paste-buffer", "-t", target, "-b", buffer_name])
        if paste_proc.returncode != 0:
            detail = paste_proc.stderr.strip() or paste_proc.stdout.strip() or "failed to paste tmux buffer"
            raise RuntimeError(f"{target}: {detail}")

        # Give Claude's input box a beat to settle after the bracketed paste before submitting.
        time.sleep(0.15)
        baseline_capture = capture_pane_output(target)
        submit_attempts = 0
        submit_ready_state: Optional[dict[str, str]] = None
        for _ in range(2):
            submit_attempts += 1
            submit_proc = run(["tmux", "send-keys", "-t", target, "Enter"])
            if submit_proc.returncode != 0:
                detail = submit_proc.stderr.strip() or submit_proc.stdout.strip() or "failed to submit pasted payload"
                raise RuntimeError(f"{target}: {detail}")
            submit_ready_state = wait_for_claude_prompt_after_submit(target, baseline_capture)
            if submit_ready_state is not None:
                break
        if submit_ready_state is None:
            raise RuntimeError(f"{target}: pasted payload did not submit after {submit_attempts} Enter attempts")
    finally:
        run(["tmux", "delete-buffer", "-b", buffer_name])
        safe_unlink(temp_path)

    return {
        "target": target,
        "buffer_name": buffer_name,
        "payload_chars": len(text),
        "submit_attempts": submit_attempts,
        "submit_ready_state": submit_ready_state,
    }


def inject_project_agent_identities(
    batch_plan: list[dict[str, str]],
    *,
    current_target: str,
) -> dict[str, Any]:
    injected: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    for entry in batch_plan:
        target = str(entry["target"]).strip()
        pane_title = str(entry["pane_title"]).strip()
        agent_path = resolve_project_claude_agent_path(pane_title)
        if not agent_path:
            skipped.append(
                {
                    "target": target,
                    "pane_title": pane_title,
                    "reason": "no_matching_project_agent",
                }
            )
            continue

        payload = agent_path.read_text(encoding="utf-8")
        if not payload.strip():
            skipped.append(
                {
                    "target": target,
                    "pane_title": pane_title,
                    "reason": "empty_project_agent_file",
                    "agent_path": str(agent_path),
                }
            )
            continue

        ready_state = wait_for_claude_pane_ready(target)
        paste_result = paste_text_into_pane(target, payload)
        injected.append(
            {
                "target": target,
                "pane_title": pane_title,
                "agent_name": agent_path.stem,
                "agent_path": str(agent_path),
                "mode": "paste-buffer",
                "ready_state": ready_state,
                **paste_result,
            }
        )

    return {
        "current_target": current_target,
        "injected": injected,
        "skipped": skipped,
    }


def write_batch_plan_file(batch_plan: list[dict[str, str]]) -> str:
    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".json",
        prefix="tmux-pane-plan-",
        delete=False,
        encoding="utf-8",
    ) as handle:
        json.dump(batch_plan, handle, ensure_ascii=False, indent=2)
        return handle.name


def apply_pane_titles(batch_plan: list[dict[str, str]]) -> dict[str, Any]:
    plan_path = write_batch_plan_file(batch_plan)
    # Set orchestrator context before calling phase script
    set_orchestrator_context()

    return run_json_script(
        "init_tmux_panes.py",
        [
            "--batch-file",
            plan_path,
        ],
        step="pane-title-application",
    )


def run_topology_setup(
    formal_session: str,
    pane_count: int,
    steps: dict[str, Any],
) -> list[str]:
    start_phase("topology")
    # Set orchestrator context before calling phase script
    set_orchestrator_context()

    steps["topology"] = run_json_script(
        "build_tmux_topology.py",
        [
            "--formal-session",
            formal_session,
            "--target-pane-count",
            str(pane_count),
        ],
        step="topology",
    )
    end_phase("topology", "ok")
    targets = [
        str(target).strip()
        for target in steps["topology"].get("pane_targets", [])
        if str(target).strip()
    ]
    steps["inspect_after_topology"] = {
        "targets": targets,
        "skipped_full_inspect": True,
        "reason": "topology phase already returns pane_targets from the target session",
    }
    return targets


def run_pane_title_application(
    formal_session: str,
    targets: list[str],
    pane_titles: list[str],
    steps: dict[str, Any],
) -> tuple[list[dict[str, str]], str]:
    start_phase("titles")
    batch_plan = build_batch_plan(targets, pane_titles)
    title_application = apply_pane_titles(batch_plan)
    steps["titles"] = title_application
    if not bool(title_application.get("verified")):
        end_phase("titles", "failed", "pane title application did not fully verify")
        raise RuntimeError("pane title application did not fully verify")
    end_phase("titles", "ok")
    steps["inspect_after_titles"] = {
        "targets": [entry["target"] for entry in batch_plan],
        "topology_fingerprint": str(title_application.get("topology_fingerprint", "")).strip(),
        "skipped_full_inspect": True,
        "reason": "title application already verifies live pane titles and computes a lightweight topology fingerprint",
    }
    return batch_plan, str(title_application.get("topology_fingerprint", "")).strip()


def run_runtime_activation_prelaunch(
    formal_session: str,
    task_id: str,
    codex_thread_id: str,
    pane_count: int,
    batch_plan: list[dict[str, str]],
    topology_fingerprint: str,
    targets: list[str],
    steps: dict[str, Any],
) -> None:
    # Set orchestrator context before calling phase scripts
    set_orchestrator_context()

    start_phase("thread_binding")
    steps["thread_binding"] = bind_tmux_thread_id(codex_thread_id)
    end_phase("thread_binding", "ok")

    # Ledger initialization through scheduler
    start_phase("ledger")
    ledger_args = [
        "--task-id",
        task_id,
        "--formal-session-name",
        formal_session,
        "--pane-count",
        str(pane_count),
        "--topology-fingerprint",
        topology_fingerprint,
        "--codex-thread-bound",
        "--runtime-status",
        "READY",
    ]
    ledger_args.extend(build_slot_binding_args(batch_plan))
    steps["ledger"] = run_json_script(
        "init_runtime_ledger.py",
        ledger_args,
        step="ledger",
    )
    end_phase("ledger", "ok")

    start_phase("surface_normalization")
    steps["surface_normalization"] = normalize_pane_surfaces(targets)
    end_phase("surface_normalization", "ok")

    steps["post_launch_context"] = {
        "path": str(POST_LAUNCH_CONTEXT_PATH),
    }
    write_chain_context(steps, path=POST_LAUNCH_CONTEXT_PATH)


def run_runtime_activation_postlaunch(
    formal_session: str,
    batch_plan: list[dict[str, str]],
    targets: list[str],
    steps: dict[str, Any],
) -> None:
    del formal_session
    del targets
    start_phase("claude_boot")
    steps["claude_boot"] = boot_project_claude_panes(
        batch_plan,
        current_target=str(steps.get("surface_normalization", {}).get("current_target", "")).strip(),
    )
    end_phase("claude_boot", "ok")

    start_phase("identity_injection")
    steps["identity_injection"] = inject_project_agent_identities(
        batch_plan,
        current_target=str(steps.get("surface_normalization", {}).get("current_target", "")).strip(),
    )
    end_phase("identity_injection", "ok")


def main() -> int:
    ensure_project_python()
    args = parse_args()
    pane_titles = resolve_pane_titles(args)
    pane_count = args.pane_count or len(pane_titles)
    hidden_pty = is_hidden_pty()
    if args.explain_launch_path:
        print(
            json.dumps(
                build_launch_path_explanation(
                    args,
                    pane_titles=pane_titles,
                    pane_count=pane_count,
                    hidden_pty=hidden_pty,
                ),
                ensure_ascii=False,
                indent=2 if args.pretty else None,
            )
        )
        return 0
    if pane_count != len(pane_titles):
        result = build_result(
            "failed",
            {"formal_session": args.formal_session},
            pane_titles,
            f"pane-count must be {len(pane_titles)} for this run (got {pane_count})",
        )
        persist_chain_result(result)
        sys.stderr.write(result["error"] + "\n")
        return 2

    steps: dict[str, Any] = load_chain_context() if (args.continue_inside_formal or args.continue_post_launch) else {}
    steps.setdefault("formal_session", args.formal_session)

    # ========== GATE 0: HIDDEN PTY CHECK (first step, before any work) ==========
    # Hidden PTY must route the public entry through Terminal.app.
    if hidden_pty and not args.continue_post_launch:
        if not args.continue_inside_formal:
            try:
                result = launch_via_terminal_app(args, steps)
            except Exception as exc:
                result = build_result(
                    "failed",
                    steps,
                    pane_titles,
                    str(exc),
                )
                persist_chain_result(result)
            emit_surface_summary(result, continue_inside_formal=False, pretty=args.pretty)
            return 0 if result.get("status") == "ok" else 1
        result = build_result(
            "failed",
            steps,
            pane_titles,
            "Hidden PTY detected - tmux-skills continuation must run from a visible terminal",
        )
        persist_chain_result(result)
        sys.stderr.write("ERROR: Hidden PTY detected - tmux-skills continuation must run from a visible terminal\n")
        return 1

    if args.continue_post_launch:
        try:
            start_phase("post_launch_continuation")
            post_launch_snapshot = inspect_visible_formal_session(
                args.formal_session,
                step="post_launch_guard",
            )
            targets = select_formal_targets(post_launch_snapshot, args.formal_session)
            batch_plan = build_batch_plan(targets, pane_titles)
            end_phase("post_launch_continuation", "ok")

            start_phase("runtime_activation_postlaunch")
            run_runtime_activation_postlaunch(
                args.formal_session,
                batch_plan,
                targets,
                steps,
            )
            end_phase("runtime_activation_postlaunch", "ok")
        except Exception as exc:
            result = build_result("failed", steps, pane_titles, str(exc))
            persist_chain_result(result)
            emit_surface_summary(result, continue_inside_formal=False, pretty=args.pretty)
            sys.stdout.flush()
            record_failure_to_issues(str(exc), steps, pane_titles)
            return 1

        result = build_result("ok", steps, pane_titles)
        persist_chain_result(result)
        emit_surface_summary(result, continue_inside_formal=False, pretty=args.pretty)
        return 0

    if not args.continue_inside_formal:
        # ========== GATE 1: detect_old_state (read-only) ==========
        detect_report, detect_snapshot = run_detect_phase(args.formal_session)
        steps["detect"] = detect_report
        steps["_detect_snapshot"] = detect_snapshot
        try:
            return launch_clean_formal_session(args, steps)
        except Exception as exc:
            result = build_result("failed", steps, pane_titles, str(exc))
            persist_chain_result(result)
            emit_surface_summary(result, continue_inside_formal=args.continue_inside_formal, pretty=args.pretty)
            sys.stdout.flush()
            record_failure_to_issues(str(exc), steps, pane_titles)  # Persist failure
            steps["failure_cleanup"] = cleanup_hidden_formal_session_on_failure(
                args.formal_session,
                str(exc),
            )
            return 1
        finally:
            steps.pop("_detect_snapshot", None)

    try:
        # Rule 1: fail-fast guard - require current_visible_formal_client=true before any positive changes
        start_phase("inside_formal_continuation")
        pre_continuation_snapshot = inspect_runtime_snapshot(
            step="pre_continuation_guard",
            formal_session=args.formal_session,
        )
        require_visible_formal_client(pre_continuation_snapshot, args.formal_session)
        end_phase("inside_formal_continuation", "ok")

        # Phase 1: pane_creation_phase
        # visible launcher check -> preflight cleanup -> env setup -> topology -> inspect_after_topology -> select_formal_targets
        start_phase("env_setup")
        run_formal_env_setup(args.formal_session, steps)
        end_phase("env_setup", "ok")

        start_phase("formal_session_policy")
        steps["formal_session_policy"] = apply_formal_session_policy(args.formal_session)
        end_phase("formal_session_policy", "ok")

        start_phase("topology_setup")
        targets = run_topology_setup(
            args.formal_session,
            pane_count,
            steps,
        )
        end_phase("topology_setup", "ok")

        # Phase 2: pane_title_phase
        # apply_pane_titles() + validation
        start_phase("pane_title_application")
        batch_plan, topology_fingerprint = run_pane_title_application(
            args.formal_session,
            targets,
            pane_titles,
            steps,
        )
        end_phase("pane_title_application", "ok")

        # Phase 3: handoff_activation_phase_prelaunch
        # bind_tmux_thread_id + ledger + surface normalization + post-launch context
        start_phase("runtime_activation")
        run_runtime_activation_prelaunch(
            args.formal_session,
            args.task_id,
            args.codex_thread_id,
            pane_count,
            batch_plan,
            topology_fingerprint,
            targets,
            steps,
        )
        end_phase("runtime_activation", "ok")
    except Exception as exc:
        result = build_result("failed", steps, pane_titles, str(exc))
        persist_chain_result(result)
        emit_surface_summary(result, continue_inside_formal=args.continue_inside_formal, pretty=args.pretty)
        sys.stdout.flush()
        record_failure_to_issues(str(exc), steps, pane_titles)  # Persist failure
        steps["failure_cleanup"] = cleanup_hidden_formal_session_on_failure(
            args.formal_session,
            str(exc),
        )
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
