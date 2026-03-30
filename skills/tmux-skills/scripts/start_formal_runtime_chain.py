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
from pathlib import Path
from typing import Any

from runtime_ledger import DEFAULT_FORMAL_SESSION_NAME
from tmux_runtime_common import describe_formal_client_state


ROOT = Path("/Users/busiji/workbot")
SCRIPTS_DIR = ROOT / "skills" / "tmux-skills" / "scripts"

ENV_SCRIPT = SCRIPTS_DIR / "init_tmux_env.py"
TOPOLOGY_SCRIPT = SCRIPTS_DIR / "build_tmux_topology.py"
PANE_INIT_SCRIPT = SCRIPTS_DIR / "init_tmux_panes.py"
INSPECT_SCRIPT = SCRIPTS_DIR / "inspect_tmux_runtime.py"
LEDGER_SCRIPT = SCRIPTS_DIR / "init_runtime_ledger.py"
WATCHER_SCRIPT = SCRIPTS_DIR / "arm_tmux_handoff_watcher.py"
READY_CHECK_SCRIPT = SCRIPTS_DIR / "check_tmux_ready.py"
WATCHER_WORKER_SCRIPT = SCRIPTS_DIR / "watch_tmux_handoff.py"
TMUX_RUNTIME_ARTIFACT_DIR = ROOT / "workspace" / "artifacts" / "tmux-runtime"
TMUX_SKILLS_ARTIFACT_DIR = ROOT / "workspace" / "artifacts" / "tmux-skills"
CURRENT_RUNTIME_LEDGER_PATH = TMUX_RUNTIME_ARTIFACT_DIR / "current-runtime.json"
LAST_RUNTIME_ISSUES_PATH = TMUX_RUNTIME_ARTIFACT_DIR / "last-runtime-issues.json"
HANDOFF_LOG_PATH = TMUX_SKILLS_ARTIFACT_DIR / "handoff-notifications.jsonl"
HANDOFF_SQLITE_PATH = TMUX_SKILLS_ARTIFACT_DIR / "handoff-notifications.sqlite3"
WATCHER_STDOUT_LOG_PATH = TMUX_SKILLS_ARTIFACT_DIR / "watch-tmux-handoff.stdout.log"
DELIVERY_STDOUT_LOG_PATH = TMUX_SKILLS_ARTIFACT_DIR / "deliver-tmux-handoff.stdout.log"
DELIVERY_QUEUE_DIR = TMUX_SKILLS_ARTIFACT_DIR / "delivery-queue"
CHAIN_STDOUT_LOG_PATH = TMUX_SKILLS_ARTIFACT_DIR / "start-formal-runtime-chain.stdout.log"


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


def run_json(command: list[str], *, step: str) -> dict[str, Any]:
    proc = run(command)
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or "command failed").strip()
        raise RuntimeError(f"{step} failed: {detail}")
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"{step} returned non-JSON output: {exc}") from exc


def run_json_with_status(command: list[str], *, step: str) -> tuple[dict[str, Any], int]:
    proc = run(command)
    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        detail = (proc.stderr or proc.stdout or "command failed").strip()
        raise RuntimeError(f"{step} returned non-JSON output: {detail or exc}") from exc
    return payload, proc.returncode


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
    }
    if error:
        result["error"] = error
    return result


def inspect_runtime_snapshot(*, step: str) -> dict[str, Any]:
    return run_json([sys.executable, str(INSPECT_SCRIPT), "--pretty"], step=step)


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


def preflight_kill_all_tmux_sessions() -> dict[str, Any]:
    try:
        snapshot = inspect_runtime_snapshot(step="tmux_preflight_inspect")
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
        snapshot = run_json([sys.executable, str(INSPECT_SCRIPT), "--pretty"], step="failure_inspect")
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


def inspect_visible_formal_session(
    formal_session: str,
    *,
    step: str,
) -> dict[str, Any]:
    snapshot = inspect_runtime_snapshot(step=step)
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
    steps["env"] = run_json(
        [
            sys.executable,
            str(ENV_SCRIPT),
            "--formal-session",
            formal_session,
            "--formal-cwd",
            str(ROOT),
            "--initialize-formal-surfaces",
            "--formal-window-title",
            formal_session,
            "--pretty",
        ],
        step="env",
    )
    inspect_after_env = inspect_visible_formal_session(
        formal_session,
        step="inspect_after_env",
    )
    steps["inspect_after_env"] = {
        "formal_session_count": inspect_after_env.get("formal_session_count"),
        "attached_formal": True,
        "session_count": inspect_after_env.get("session_count"),
    }
    return inspect_after_env


def apply_formal_session_policy(formal_session: str) -> list[str]:
    proc = run(["tmux", "set-option", "-t", formal_session, "destroy-unattached", "on"])
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or "failed to enable destroy-unattached").strip()
        raise RuntimeError(detail)
    return ["destroy_unattached=on"]


def verify_tmux_cleared() -> dict[str, Any]:
    snapshot = inspect_runtime_snapshot(step="tmux_preflight_verify")
    if int(snapshot.get("session_count", 0) or 0) != 0:
        raise RuntimeError(
            "tmux residue remains after preflight cleanup: "
            + ", ".join(str(session.get("session_name") or "") for session in snapshot.get("sessions", []))
        )
    return snapshot


def build_inside_formal_command(args: argparse.Namespace) -> str:
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
    quoted_command = " ".join(shlex.quote(part) for part in command)
    # Preserve inner continuation failures while still keeping the pane alive on success.
    return f"{quoted_command}; rc=$?; if [ $rc -ne 0 ]; then exit $rc; fi; exec {shlex.quote(shell_path)} -l"


def launch_clean_formal_session(args: argparse.Namespace, steps: dict[str, Any]) -> int:
    launcher_snapshot = inspect_runtime_snapshot(step="launcher_inspect")
    require_visible_terminal_launcher(launcher_snapshot)
    steps["launcher_visibility"] = {
        "mode": "verified_before_cleanup",
        "visible_terminal_client": (launcher_snapshot.get("current_client") or {}).get(
            "visible_terminal_client", False
        ),
    }
    steps["tmux_preflight"] = preflight_kill_all_tmux_sessions()
    if steps["tmux_preflight"].get("blocked"):
        raise RuntimeError(
            "new tmux-skills tasks must start from a fresh visible terminal, not from inside an existing tmux session"
        )
    verify_tmux_cleared()
    steps["cleanup"] = cleanup_previous_runtime_state()
    tmux_command = [
        "tmux",
        "new-session",
        "-s",
        args.formal_session,
        "-c",
        str(ROOT),
        build_inside_formal_command(args),
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
    return run_json(
        [
            sys.executable,
            str(PANE_INIT_SCRIPT),
            "--batch-file",
            plan_path,
            "--pretty",
        ],
        step="pane-title-application",
    )


def run_topology_setup(
    formal_session: str,
    pane_count: int,
    steps: dict[str, Any],
) -> tuple[list[str], dict[str, Any]]:
    steps["topology"] = run_json(
        [
            sys.executable,
            str(TOPOLOGY_SCRIPT),
            "--formal-session",
            formal_session,
            "--target-pane-count",
            str(pane_count),
            "--pretty",
        ],
        step="topology",
    )

    inspect_after_topology = inspect_visible_formal_session(
        formal_session,
        step="inspect_after_topology",
    )
    targets = select_formal_targets(inspect_after_topology, formal_session)
    steps["inspect_after_topology"] = {"targets": targets}

    return targets, inspect_after_topology


def run_pane_title_application(
    formal_session: str,
    targets: list[str],
    pane_titles: list[str],
    inspect_after_topology: dict[str, Any],
    steps: dict[str, Any],
) -> tuple[list[dict[str, str]], str]:
    batch_plan = build_batch_plan(targets, pane_titles)
    title_application = apply_pane_titles(batch_plan)
    steps["titles"] = title_application
    if not bool(title_application.get("verified")):
        raise RuntimeError("pane title application did not fully verify")

    inspect_after_titles = inspect_visible_formal_session(
        formal_session,
        step="inspect_after_titles",
    )
    topology_fingerprint = str(inspect_after_titles.get("topology_fingerprint", "")).strip()
    steps["inspect_after_titles"] = {
        "targets": select_formal_targets(inspect_after_titles, formal_session),
        "topology_fingerprint": topology_fingerprint,
    }
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
    steps["thread_binding"] = bind_tmux_thread_id(codex_thread_id)

    ledger_command = [
        sys.executable,
        str(LEDGER_SCRIPT),
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
        "--pretty",
    ]
    ledger_command.extend(build_slot_binding_args(batch_plan))
    steps["ledger"] = run_json(ledger_command, step="ledger")

    watcher_command = [
        sys.executable,
        str(WATCHER_SCRIPT),
        "--formal-session-name",
        formal_session,
        "--pretty",
    ]
    for target in targets:
        watcher_command.extend(["--target", target])
    steps["watcher"] = run_json(watcher_command, step="watcher")

    ready_check_command = [
        sys.executable,
        str(READY_CHECK_SCRIPT),
        "--formal-session-name",
        formal_session,
        "--require-formal",
        "--require-watcher",
        "--pretty",
    ]
    ready_check_result, ready_check_rc = run_json_with_status(
        ready_check_command,
        step="ready_check",
    )
    steps["ready_check"] = ready_check_result
    if ready_check_rc != 0:
        raise RuntimeError(
            "ready_check failed: "
            + "; ".join(str(reason) for reason in ready_check_result.get("reasons", []))
        )


def main() -> int:
    args = parse_args()
    pane_titles = resolve_pane_titles(args)
    pane_count = args.pane_count or len(pane_titles)
    if pane_count != len(pane_titles):
        sys.stderr.write(
            f"pane-count must be {len(pane_titles)} for this run (got {pane_count})\n"
        )
        return 2

    steps: dict[str, Any] = {"formal_session": args.formal_session}
    if not args.continue_inside_formal:
        try:
            return launch_clean_formal_session(args, steps)
        except Exception as exc:
            result = build_result("failed", steps, pane_titles, str(exc))
            print(json.dumps(result, ensure_ascii=False, indent=2 if args.pretty else None))
            return 1

    try:
        # Phase 1: pane_creation_phase
        # visible launcher check -> preflight cleanup -> env setup -> topology -> inspect_after_topology -> select_formal_targets
        run_formal_env_setup(args.formal_session, steps)
        steps["formal_session_policy"] = apply_formal_session_policy(args.formal_session)
        targets, inspect_after_topology = run_topology_setup(
            args.formal_session,
            pane_count,
            steps,
        )

        # Phase 2: pane_title_phase
        # apply_pane_titles() + validation
        batch_plan, topology_fingerprint = run_pane_title_application(
            args.formal_session,
            targets,
            pane_titles,
            inspect_after_topology,
            steps,
        )

        # Phase 3: handoff_activation_phase
        # bind_tmux_thread_id + ledger + watcher + ready check
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
    except Exception as exc:
        result = build_result("failed", steps, pane_titles, str(exc))
        print(json.dumps(result, ensure_ascii=False, indent=2 if args.pretty else None))
        sys.stdout.flush()
        steps["failure_cleanup"] = cleanup_hidden_formal_session_on_failure(
            args.formal_session,
            str(exc),
        )
        return 1

    result = build_result("ok", steps, pane_titles)
    print(json.dumps(result, ensure_ascii=False, indent=2 if args.pretty else None))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
