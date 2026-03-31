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
from typing import Any

# Phase timing tracking
_phase_timings = {}
_phase_start_time = None

# Add parent directory to path for module imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from runtime_ledger import DEFAULT_FORMAL_SESSION_NAME
from tmux_runtime_common import describe_formal_client_state, inspect_runtime
from tmux_scheduler import (
    run_json_script,
    set_orchestrator_context,
    is_hidden_pty,
)


ROOT = Path("/Users/busiji/workbot")
SCRIPTS_DIR = ROOT / "skills" / "tmux-skills" / "scripts"

ENV_SCRIPT = SCRIPTS_DIR / "init_tmux_env.py"
TOPOLOGY_SCRIPT = SCRIPTS_DIR / "build_tmux_topology.py"
PANE_INIT_SCRIPT = SCRIPTS_DIR / "init_tmux_panes.py"
LEDGER_SCRIPT = SCRIPTS_DIR / "init_runtime_ledger.py"
WATCHER_SCRIPT = SCRIPTS_DIR / "arm_tmux_handoff_watcher.py"
READY_CHECK_SCRIPT = SCRIPTS_DIR / "check_tmux_ready.py"
WATCHER_WORKER_SCRIPT = SCRIPTS_DIR / "watch_tmux_handoff.py"
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


def write_chain_context(steps: dict[str, Any]) -> str:
    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".json",
        prefix="tmux-chain-context-",
        delete=False,
        encoding="utf-8",
    ) as handle:
        json.dump(
            {
                "steps": steps,
                "phase_timings": get_phase_timings(),
            },
            handle,
            ensure_ascii=False,
            indent=2,
        )
        return handle.name


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
        description="Public tmux-skills flow: formal-session -> pane generation -> title application -> stopped-pane watcher"
    )
    parser.add_argument(
        "--codex-thread-id",
        dest="codex_thread_id",
        required=True,
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
    parser.add_argument("--pretty", action="store_true", help="Pretty-print result JSON.")
    return parser.parse_args()


def run(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, capture_output=True, text=True, check=False)


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
    for raw in proc.stdout.splitlines():
        if not raw.strip():
            continue
        pid_text, _, command = raw.strip().partition(" ")
        if not pid_text.isdigit():
            continue
        command = command.strip()
        if WATCHER_WORKER_SCRIPT.name not in command:
            continue
        processes.append({"pid": int(pid_text), "command": command})
    return processes


def stop_existing_watchers() -> list[int]:
    stopped: list[int] = []
    for process in list_existing_watcher_processes():
        pid = int(process["pid"])
        try:
            os.kill(pid, signal.SIGTERM)
        except ProcessLookupError:
            continue
        stopped.append(pid)
        wait_for_pid_exit(pid)
    return stopped


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
    removed_files: list[str] = []
    for path in (
        CURRENT_RUNTIME_LEDGER_PATH,
        LAST_RUNTIME_ISSUES_PATH,
        HANDOFF_LOG_PATH,
        HANDOFF_SQLITE_PATH,
        WATCHER_STDOUT_LOG_PATH,
        DELIVERY_STDOUT_LOG_PATH,
        CHAIN_STDOUT_LOG_PATH,
    ):
        if safe_unlink(path):
            removed_files.append(str(path))
    removed_files.extend(clear_directory(DELIVERY_QUEUE_DIR))
    tmux_env_status = unset_tmux_env("CODEX_THREAD_ID")
    return {
        "removed_files": removed_files,
        "stopped_watcher_pids": stop_existing_watchers(),
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


def parse_target(target: str) -> tuple[int, int]:
    pane = target.split(":", 1)[1]
    window_index, pane_index = pane.split(".", 1)
    return int(window_index), int(pane_index)


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
    error: str | None = None,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "status": status,
        "formal_session": steps.get("formal_session", DEFAULT_FORMAL_SESSION_NAME),
        "pane_count": len(pane_titles),
        "pane_titles": pane_titles,
        "chain": ["tmux_preflight", "cleanup", "env", "topology", "titles", "ledger", "watcher", "ready_check"],
        "steps": steps,
        "phase_timings": get_phase_timings(),
        "total_elapsed_ms": get_total_elapsed_ms(),
    }
    if error:
        result["error"] = error
    return result


def inspect_runtime_snapshot(*, step: str, formal_session: str | None = None) -> dict[str, Any]:
    """Inspect runtime in-process to avoid deprecated wrapper noise and subprocess overhead."""
    try:
        return inspect_runtime(formal_session)
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


def preflight_kill_all_tmux_sessions(formal_session: str) -> dict[str, Any]:
    try:
        snapshot = inspect_runtime_snapshot(step="tmux_preflight_inspect", formal_session=formal_session)
    except Exception as exc:
        return {"attempted": False, "reason": f"inspect_failed: {exc}"}

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
    phase_order = ["tmux_preflight", "cleanup", "env", "topology", "titles", "ledger", "watcher", "ready_check"]
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


def run_detect_phase(formal_session: str) -> dict[str, Any]:
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
        return report
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


def run_formal_env_setup(formal_session: str, steps: dict[str, Any]) -> dict[str, Any]:
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

    start_phase("env_inspect")
    inspect_after_env = inspect_visible_formal_session(
        formal_session,
        step="inspect_after_env",
    )
    steps["inspect_after_env"] = {
        "formal_session_count": inspect_after_env.get("formal_session_count"),
        "attached_formal": True,
        "session_count": inspect_after_env.get("session_count"),
    }
    end_phase("env_inspect", "ok")
    return inspect_after_env


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
        sys.executable,
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
    shell_path = os.environ.get("SHELL") or "/bin/zsh"
    env_prefix = (
        f"{CHAIN_CONTEXT_PATH_ENV}={shlex.quote(chain_context_path)} "
        if chain_context_path
        else ""
    )
    quoted_command = " ".join(shlex.quote(part) for part in command)
    # Preserve inner continuation failures while still keeping the pane alive on success.
    return (
        f"{env_prefix}{quoted_command}; rc=$?; if [ $rc -ne 0 ]; then exit $rc; fi; "
        f"exec {shlex.quote(shell_path)} -l"
    )


def launch_clean_formal_session(args: argparse.Namespace, steps: dict[str, Any]) -> int:
    start_phase("launcher_routing")
    launcher_snapshot = inspect_runtime_snapshot(
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
    steps["tmux_preflight"] = preflight_kill_all_tmux_sessions(args.formal_session)
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
) -> tuple[list[str], dict[str, Any]]:
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

    start_phase("topology_inspect")
    inspect_after_topology = inspect_visible_formal_session(
        formal_session,
        step="inspect_after_topology",
    )
    targets = select_formal_targets(inspect_after_topology, formal_session)
    steps["inspect_after_topology"] = {"targets": targets}
    end_phase("topology_inspect", "ok")

    return targets, inspect_after_topology


def run_pane_title_application(
    formal_session: str,
    targets: list[str],
    pane_titles: list[str],
    inspect_after_topology: dict[str, Any],
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

    start_phase("titles_inspect")
    inspect_after_titles = inspect_visible_formal_session(
        formal_session,
        step="inspect_after_titles",
    )
    topology_fingerprint = str(inspect_after_titles.get("topology_fingerprint", "")).strip()
    steps["inspect_after_titles"] = {
        "targets": select_formal_targets(inspect_after_titles, formal_session),
        "topology_fingerprint": topology_fingerprint,
    }
    end_phase("titles_inspect", "ok")
    return batch_plan, topology_fingerprint


def run_runtime_activation(
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

    # Watcher arm through scheduler (degraded - does not block ready)
    start_phase("watcher")
    watcher_args = [
        "--formal-session-name",
        formal_session,
    ]
    for target in targets:
        watcher_args.extend(["--target", target])
    try:
        steps["watcher"] = run_json_script(
            "arm_tmux_handoff_watcher.py",
            watcher_args,
            step="watcher",
        )
        end_phase("watcher", "ok")
    except Exception as e:
        # Watcher is degraded - mark but don't fail the main chain
        steps["watcher"] = {"status": "degraded", "error": str(e)}
        end_phase("watcher", "degraded", str(e))

    # Ready check through scheduler
    start_phase("ready_check")
    ready_check_result = run_json_script(
        "check_tmux_ready.py",
        [
            "--formal-session-name",
            formal_session,
            "--require-formal",
            # Note: watcher is degraded, do not require it for main ready gate
        ],
        step="ready_check",
    )
    steps["ready_check"] = ready_check_result
    if ready_check_result.get("runtime_status") != "READY":
        end_phase("ready_check", "failed", "; ".join(str(reason) for reason in ready_check_result.get("reasons", [])))
        raise RuntimeError(
            "ready_check failed: "
            + "; ".join(str(reason) for reason in ready_check_result.get("reasons", []))
        )
    end_phase("ready_check", "ok")


def main() -> int:
    args = parse_args()
    pane_titles = resolve_pane_titles(args)
    pane_count = args.pane_count or len(pane_titles)
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

    steps: dict[str, Any] = load_chain_context() if args.continue_inside_formal else {}
    steps.setdefault("formal_session", args.formal_session)

    # ========== GATE 0: HIDDEN PTY CHECK (first step, before any work) ==========
    # Hidden PTY must immediately route to visible terminal launcher
    if is_hidden_pty():
        result = build_result(
            "failed",
            steps,
            pane_titles,
            "Hidden PTY detected - tmux-skills must run from a visible terminal",
        )
        persist_chain_result(result)
        sys.stderr.write("ERROR: Hidden PTY detected - tmux-skills must run from a visible terminal\n")
        sys.stderr.write("Please run this command from a real terminal window, not from a hidden context.\n")
        return 1

    if not args.continue_inside_formal:
        # ========== GATE 1: detect_old_state (read-only) ==========
        detect_report = run_detect_phase(args.formal_session)
        steps["detect"] = detect_report
        try:
            return launch_clean_formal_session(args, steps)
        except Exception as exc:
            result = build_result("failed", steps, pane_titles, str(exc))
            persist_chain_result(result)
            print(json.dumps(result, ensure_ascii=False, indent=2 if args.pretty else None))
            sys.stdout.flush()
            record_failure_to_issues(str(exc), steps, pane_titles)  # Persist failure
            steps["failure_cleanup"] = cleanup_hidden_formal_session_on_failure(
                args.formal_session,
                str(exc),
            )
            return 1

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
        targets, inspect_after_topology = run_topology_setup(
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
            inspect_after_topology,
            steps,
        )
        end_phase("pane_title_application", "ok")

        # Phase 3: handoff_activation_phase
        # bind_tmux_thread_id + ledger + watcher + ready check
        start_phase("runtime_activation")
        run_runtime_activation(
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
        print(json.dumps(result, ensure_ascii=False, indent=2 if args.pretty else None))
        sys.stdout.flush()
        record_failure_to_issues(str(exc), steps, pane_titles)  # Persist failure
        steps["failure_cleanup"] = cleanup_hidden_formal_session_on_failure(
            args.formal_session,
            str(exc),
        )
        return 1

    result = build_result("ok", steps, pane_titles)
    persist_chain_result(result)
    print(json.dumps(result, ensure_ascii=False, indent=2 if args.pretty else None))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
