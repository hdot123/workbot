#!/usr/bin/env python3
"""Run the public tmux-skills flow: generate panes, label them, and arm stopped-pane reporting."""

from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

from runtime_ledger import DEFAULT_FORMAL_SESSION_NAME


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
    ):
        if safe_unlink(path):
            removed_files.append(str(path))
    removed_files.extend(clear_directory(DELIVERY_QUEUE_DIR))
    unset_tmux_env("CODEX_THREAD_ID")
    return {
        "removed_files": removed_files,
        "stopped_watcher_pids": stop_existing_watchers(),
        "tmux_env": {
            "CODEX_THREAD_ID": unset_tmux_env("CODEX_THREAD_ID"),
        },
    }


def ensure_attached_formal_session(snapshot: dict[str, Any], formal_session: str) -> None:
    formal_client_count = int(snapshot.get("formal_client_count", 0) or 0)
    if formal_client_count <= 0:
        raise RuntimeError(
            f"formal session '{formal_session}' has no attached tmux client; foreground tmux is not visible"
        )
    if formal_client_count != 1:
        raise RuntimeError(
            f"formal session '{formal_session}' must have exactly one visible tmux client; got {formal_client_count}"
        )
    if not bool(snapshot.get("current_visible_formal_client")):
        raise RuntimeError(
            f"current caller is not inside the visible formal session '{formal_session}'"
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


def preflight_formal_session_cleanup(formal_session: str) -> dict[str, Any]:
    try:
        snapshot = run_json([sys.executable, str(INSPECT_SCRIPT), "--pretty"], step="tmux_preflight_inspect")
    except Exception as exc:
        return {"attempted": False, "reason": f"inspect_failed: {exc}"}

    current_client = snapshot.get("current_client") or {}
    formal_sessions = [
        str(name).strip()
        for name in snapshot.get("formal_sessions", [])
        if str(name).strip()
    ]
    formal_exists = formal_session in formal_sessions
    current_in_formal = bool(
        current_client.get("inside_tmux") and current_client.get("session_name") == formal_session
    )
    stale_formal_session = formal_exists and not bool(snapshot.get("current_visible_formal_client"))
    result: dict[str, Any] = {
        "attempted": False,
        "formal_session": formal_session,
        "formal_exists": formal_exists,
        "current_visible_formal_client": bool(snapshot.get("current_visible_formal_client")),
        "current_in_formal": current_in_formal,
    }
    if not stale_formal_session:
        result["reason"] = "no_stale_formal_session"
        return result
    if current_in_formal:
        result["reason"] = "defer_current_formal_cleanup"
        result["pending_cleanup"] = True
        return result

    kill_proc = run(["tmux", "kill-session", "-t", formal_session])
    result["attempted"] = True
    result["kill_returncode"] = kill_proc.returncode
    result["kill_detail"] = (kill_proc.stderr or kill_proc.stdout or "").strip()
    result["cleaned"] = kill_proc.returncode == 0
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
    try:
        steps["tmux_preflight"] = preflight_formal_session_cleanup(args.formal_session)
        steps["cleanup"] = cleanup_previous_runtime_state()
        steps["env"] = run_json(
            [
                sys.executable,
                str(ENV_SCRIPT),
                "--formal-session",
                args.formal_session,
                "--formal-cwd",
                str(ROOT),
                "--create-formal-session",
                "--kill-detached",
                "--initialize-formal-surfaces",
                "--formal-window-title",
                args.formal_session,
                "--pretty",
            ],
            step="env",
        )

        inspect_after_env = run_json(
            [sys.executable, str(INSPECT_SCRIPT), "--pretty"],
            step="inspect_after_env",
        )
        ensure_attached_formal_session(inspect_after_env, args.formal_session)
        steps["inspect_after_env"] = {
            "formal_session_count": inspect_after_env.get("formal_session_count"),
            "attached_formal": True,
        }

        set_env_proc = run(["tmux", "set-environment", "-g", "CODEX_THREAD_ID", args.codex_thread_id])
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
        if bound_value != args.codex_thread_id:
            raise RuntimeError(
                "CODEX_THREAD_ID binding did not persist into tmux: "
                f"expected={args.codex_thread_id}, actual={bound_value or '<empty>'}"
            )
        steps["thread_binding"] = {"CODEX_THREAD_ID": args.codex_thread_id}

        steps["topology"] = run_json(
            [
                sys.executable,
                str(TOPOLOGY_SCRIPT),
                "--formal-session",
                args.formal_session,
                "--target-pane-count",
                str(pane_count),
                "--pretty",
            ],
            step="topology",
        )

        inspect_after_topology = run_json(
            [sys.executable, str(INSPECT_SCRIPT), "--pretty"],
            step="inspect_after_topology",
        )
        ensure_attached_formal_session(inspect_after_topology, args.formal_session)
        targets = select_formal_targets(inspect_after_topology, args.formal_session)
        batch_plan = build_batch_plan(targets, pane_titles)
        steps["inspect_after_topology"] = {"targets": targets}

        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".json",
            prefix="tmux-pane-plan-",
            delete=False,
            encoding="utf-8",
        ) as handle:
            json.dump(batch_plan, handle, ensure_ascii=False, indent=2)
            plan_path = handle.name

        title_application = run_json(
            [
                sys.executable,
                str(PANE_INIT_SCRIPT),
                "--batch-file",
                plan_path,
                "--pretty",
            ],
            step="pane-title-application",
        )
        steps["titles"] = title_application
        if not bool(title_application.get("verified")):
            raise RuntimeError("pane title application did not fully verify")

        inspect_after_titles = run_json(
            [sys.executable, str(INSPECT_SCRIPT), "--pretty"],
            step="inspect_after_titles",
        )
        ensure_attached_formal_session(inspect_after_titles, args.formal_session)
        topology_fingerprint = str(inspect_after_titles.get("topology_fingerprint", "")).strip()
        steps["inspect_after_titles"] = {
            "targets": select_formal_targets(inspect_after_titles, args.formal_session),
            "topology_fingerprint": topology_fingerprint,
        }
        ledger_command = [
            sys.executable,
            str(LEDGER_SCRIPT),
            "--task-id",
            args.task_id,
            "--formal-session-name",
            args.formal_session,
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
            args.formal_session,
            "--pretty",
        ]
        for target in targets:
            watcher_command.extend(["--target", target])
        steps["watcher"] = run_json(watcher_command, step="watcher")

        ready_check_command = [
            sys.executable,
            str(READY_CHECK_SCRIPT),
            "--formal-session-name",
            args.formal_session,
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
