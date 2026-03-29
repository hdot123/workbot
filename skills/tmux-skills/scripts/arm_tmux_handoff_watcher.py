#!/usr/bin/env python3
"""Arm the tmux-skills handoff watcher for the current formal runtime targets."""

from __future__ import annotations

import argparse
import json
import os
import shlex
import signal
import subprocess
import sys
from pathlib import Path
from typing import Any

from runtime_ledger import update_current_runtime_ledger
from tmux_runtime_common import inspect_runtime


WATCHER_SCRIPT = Path(__file__).with_name("watch_tmux_handoff.py")
DEFAULT_LOG_FILE = Path("/Users/busiji/workbot/workspace/artifacts/tmux-skills/handoff-notifications.jsonl")
DEFAULT_STDOUT_LOG = Path("/Users/busiji/workbot/workspace/artifacts/tmux-skills/watch-tmux-handoff.stdout.log")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Arm the internal tmux-skills watcher for the formal runtime targets."
    )
    parser.add_argument(
        "--formal-session-name",
        default="formal-session",
        help="Formal session name whose panes should be watched.",
    )
    parser.add_argument(
        "--target",
        action="append",
        dest="targets",
        default=[],
        help="Explicit target to watch. Repeatable. Defaults to all formal whitelist targets.",
    )
    parser.add_argument(
        "--pane-id",
        action="append",
        dest="pane_ids",
        default=[],
        help="Deprecated compatibility input. Converted to target immediately.",
    )
    parser.add_argument(
        "--include-non-bot-panes",
        action="store_true",
        help="Allow watching formal panes whose normalized title is not a whitelist bot role.",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=0.8,
        help="Polling interval for the watcher.",
    )
    parser.add_argument(
        "--proactive-interval",
        type=float,
        default=300.0,
        help="Proactive check-in interval for the watcher.",
    )
    parser.add_argument(
        "--session-mode",
        choices=("fixed", "new"),
        default="fixed",
        help="Delivery session mode passed through to the watcher.",
    )
    parser.add_argument(
        "--log-file",
        default=str(DEFAULT_LOG_FILE),
        help="Notification JSONL path for watcher output.",
    )
    parser.add_argument(
        "--stdout-log",
        default=str(DEFAULT_STDOUT_LOG),
        help="Stdout/stderr capture file for the watcher process.",
    )
    parser.add_argument(
        "--no-deliver",
        action="store_true",
        help="Disable immediate delivery and only emit watcher events/logs.",
    )
    parser.add_argument(
        "--keep-existing",
        action="store_true",
        help="Do not stop existing internal watcher processes that target the same panes.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the watcher plan without starting a new process.",
    )
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output.")
    return parser.parse_args()


def extract_targets_from_command(command: str) -> list[str]:
    try:
        tokens = shlex.split(command)
    except ValueError:
        tokens = command.split()
    targets: list[str] = []
    for index, token in enumerate(tokens):
        if token == "--target" and index + 1 < len(tokens):
            targets.append(tokens[index + 1])
    return targets


def discover_targets(snapshot: dict[str, Any], args: argparse.Namespace) -> list[str]:
    explicit_targets = [str(target).strip() for target in args.targets if str(target).strip()]
    pane_id_to_target = {
        str(pane.get("pane_id", "")).strip(): str(pane.get("target", "")).strip()
        for pane in snapshot.get("panes", [])
        if str(pane.get("pane_id", "")).strip() and str(pane.get("target", "")).strip()
    }
    explicit_targets.extend(
        pane_id_to_target[pane_id]
        for pane_id in args.pane_ids
        if str(pane_id).strip() in pane_id_to_target
    )
    if explicit_targets:
        return sorted(dict.fromkeys(explicit_targets))

    targets: list[str] = []
    for pane in snapshot.get("panes", []):
        if pane.get("session_name") != args.formal_session_name:
            continue
        if not args.include_non_bot_panes and not pane.get("is_bot_named"):
            continue
        target = str(pane.get("target", "")).strip()
        if target:
            targets.append(target)
    return sorted(dict.fromkeys(targets))


def list_existing_watchers() -> list[dict[str, Any]]:
    result = subprocess.run(
        ["pgrep", "-af", str(WATCHER_SCRIPT.name)],
        capture_output=True,
        text=True,
        check=False,
    )
    processes: list[dict[str, Any]] = []
    for raw in result.stdout.splitlines():
        if not raw.strip():
            continue
        pid_text, _, command = raw.partition(" ")
        if not pid_text.isdigit():
            continue
        processes.append({"pid": int(pid_text), "command": command})
    return processes


def stop_conflicting_watchers(targets: list[str]) -> list[int]:
    stopped: list[int] = []
    target_set = set(targets)
    for process in list_existing_watchers():
        command_targets = set(extract_targets_from_command(str(process.get("command", ""))))
        if not command_targets.intersection(target_set):
            continue
        pid = int(process["pid"])
        try:
            os.kill(pid, signal.SIGTERM)
        except ProcessLookupError:
            continue
        stopped.append(pid)
    return stopped


def build_watcher_command(args: argparse.Namespace, targets: list[str]) -> list[str]:
    command = [sys.executable, str(WATCHER_SCRIPT)]
    for target in targets:
        command.extend(["--target", target])
    command.extend(["--interval", str(args.interval)])
    command.extend(["--proactive-interval", str(args.proactive_interval)])
    command.extend(["--session-mode", args.session_mode])
    command.extend(["--log-file", str(args.log_file)])
    if not args.no_deliver:
        command.append("--deliver")
    return command


def ensure_tmux_thread_binding() -> str:
    result = subprocess.run(
        ["tmux", "show-environment", "-g", "CODEX_THREAD_ID"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return ""
    stdout = result.stdout.strip()
    prefix = "CODEX_THREAD_ID="
    if stdout.startswith(prefix):
        return stdout[len(prefix) :]
    return ""


def start_watcher(command: list[str], stdout_log: Path) -> int:
    stdout_log.parent.mkdir(parents=True, exist_ok=True)
    stdout_handle = stdout_log.open("a", encoding="utf-8")
    process = subprocess.Popen(
        command,
        stdout=stdout_handle,
        stderr=subprocess.STDOUT,
        stdin=subprocess.DEVNULL,
        preexec_fn=os.setsid,
        text=True,
    )
    stdout_handle.close()
    return process.pid


def enforce_destroy_unattached(formal_session_name: str) -> str:
    result = subprocess.run(
        ["tmux", "set-option", "-t", formal_session_name, "destroy-unattached", "on"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise SystemExit(
            result.stderr.strip()
            or result.stdout.strip()
            or f"failed to enable destroy-unattached for {formal_session_name}"
        )
    return "destroy_unattached=on"


def maybe_write_ledger(status: str, codex_thread_id: str, targets: list[str], watcher_pid: int | None) -> None:
    try:
        update_current_runtime_ledger(
            watcher={
                "armed": status == "armed",
                "targets": targets,
                "pid": watcher_pid,
                "transport": "codex",
            },
            codex_thread_bound=bool(codex_thread_id),
        )
    except FileNotFoundError:
        return


def main() -> int:
    args = parse_args()
    snapshot = inspect_runtime(args.formal_session_name)
    formal_session_attached = any(
        session.get("session_name") == args.formal_session_name
        and int(session.get("attached", 0)) > 0
        for session in snapshot.get("sessions", [])
    )
    if not formal_session_attached:
        raise SystemExit(
            f"formal session {args.formal_session_name} is not attached; refusing to arm watcher"
        )
    targets = discover_targets(snapshot, args)
    if not targets:
        raise SystemExit(
            f"no eligible targets found in formal session {args.formal_session_name}"
        )

    session_policy = enforce_destroy_unattached(args.formal_session_name)

    codex_thread_id = ensure_tmux_thread_binding()
    if not codex_thread_id and not args.no_deliver:
        raise SystemExit("CODEX_THREAD_ID is not bound in tmux; cannot arm delivery watcher")

    stopped_pids: list[int] = []
    if not args.keep_existing:
        stopped_pids = stop_conflicting_watchers(targets)

    command = build_watcher_command(args, targets)
    stdout_log = Path(args.stdout_log)

    result: dict[str, Any] = {
        "formal_session_name": args.formal_session_name,
        "targets": targets,
        "deliver_enabled": not args.no_deliver,
        "codex_thread_id_present": bool(codex_thread_id),
        "stopped_existing_watcher_pids": stopped_pids,
        "watcher_command": command,
        "stdout_log": str(stdout_log),
        "log_file": str(args.log_file),
        "formal_session_policy": session_policy,
    }

    if args.dry_run:
        result["status"] = "dry_run"
    else:
        pid = start_watcher(command, stdout_log)
        result["status"] = "armed"
        result["watcher_pid"] = pid
        maybe_write_ledger(result["status"], codex_thread_id, targets, pid)

    if args.pretty:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
