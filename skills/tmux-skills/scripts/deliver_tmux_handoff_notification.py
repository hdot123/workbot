#!/usr/bin/env python3
# ==============================================================================
# DEPRECATED: This script is deprecated as of 2026-03-31
# ==============================================================================
# Reason: Switched to window IPC bridge mechanism
# Alternative: Use tmux_handoff_app_bridge.py instead
# This file is retained for backward compatibility only.
# ==============================================================================

from __future__ import annotations

# ==============================================================================
# ENFORCEMENT: This script requires runtime owner authorization
# ==============================================================================
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from runtime_enforcement import enforce_runtime_owner_only
enforce_runtime_owner_only("deliver_tmux_handoff_notification.py")
# ==============================================================================

import argparse
import fcntl
import json
import os
import subprocess
import time
from typing import Any

from build_tmux_handoff_bundle import build_bundle
from tmux_handoff_app_bridge import (
    DEFAULT_LOCK_FILE as DEFAULT_BRIDGE_LOCK_FILE,
    DEFAULT_PID_FILE as DEFAULT_BRIDGE_PID_FILE,
    DEFAULT_QUEUE_DIR,
    DEFAULT_RECEIPTS_LOG as DEFAULT_BRIDGE_RECEIPTS_LOG,
    DEFAULT_STDOUT_LOG as DEFAULT_BRIDGE_STDOUT_LOG,
)


DEFAULT_BRIDGE_SCRIPT = Path(__file__).with_name("tmux_handoff_app_bridge.py")
DEFAULT_BRIDGE_START_TIMEOUT_SECONDS = 2.0
DEFAULT_BRIDGE_START_POLL_SECONDS = 0.1


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Deliver a tmux-skills handoff notification to the CODEX_THREAD_ID-bound Codex window thread."
    )
    parser.add_argument(
        "--event-file",
        help="Optional path to a JSON event file. If omitted, reads one JSON object from stdin.",
    )
    parser.add_argument(
        "--bundle-file",
        help="Optional path to a prebuilt tmux-skills handoff bundle. If omitted, accepts an event or bundle on stdin.",
    )
    parser.add_argument(
        "--session-mode",
        choices=("fixed", "new"),
        default="fixed",
        help="Compatibility input retained for bundle shape stability.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the delivery plan instead of executing it.",
    )
    parser.add_argument(
        "--queue-dir",
        default=str(DEFAULT_QUEUE_DIR),
        help="Queue directory consumed by the long-lived tmux handoff window IPC bridge.",
    )
    parser.add_argument(
        "--bridge-script",
        default=str(DEFAULT_BRIDGE_SCRIPT),
        help="Bridge/sidecar script responsible for Codex window IPC delivery.",
    )
    parser.add_argument(
        "--bridge-lock-file",
        default=str(DEFAULT_BRIDGE_LOCK_FILE),
        help="Stable lock file used for singleton bridge ownership.",
    )
    parser.add_argument(
        "--bridge-pid-file",
        default=str(DEFAULT_BRIDGE_PID_FILE),
        help="PID file used to detect the long-lived window IPC bridge.",
    )
    parser.add_argument(
        "--bridge-stdout-log",
        default=str(DEFAULT_BRIDGE_STDOUT_LOG),
        help="Stdout/stderr capture path for the long-lived window IPC bridge.",
    )
    parser.add_argument(
        "--bridge-receipts-log",
        default=str(DEFAULT_BRIDGE_RECEIPTS_LOG),
        help="JSONL receipt log written by the long-lived window IPC bridge.",
    )
    return parser.parse_args()


def load_json(path: str | None) -> dict[str, Any]:
    if path:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    raw = sys.stdin.read().strip()
    if not raw:
        raise ValueError("no input payload provided")
    return json.loads(raw)


def ensure_bundle(payload: dict[str, Any], *, session_mode: str) -> dict[str, Any]:
    if "tmux_skills_handoff" in payload:
        return payload
    return build_bundle(payload, table="tmux_notifications_raw", session_mode=session_mode)


def target_thread_id(bundle: dict[str, Any]) -> str:
    tmux_handoff = bundle.get("tmux_skills_handoff", {})
    target = tmux_handoff.get("target", {})
    payload = tmux_handoff.get("payload", {})
    for candidate in (target.get("thread_id"), payload.get("codex_thread_id")):
        normalized = str(candidate or "").strip()
        if normalized:
            return normalized
    return ""


def pid_is_running(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def read_bridge_pid(pid_file: Path) -> int | None:
    try:
        raw = pid_file.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        return None
    if not raw.isdigit():
        return None
    pid = int(raw)
    if pid_is_running(pid):
        return pid
    return None


def build_bridge_command(
    *,
    bridge_script: str,
    queue_dir: str,
    receipts_log: str,
    lock_file: str,
    pid_file: str,
) -> list[str]:
    return [
        sys.executable,
        bridge_script,
        "--queue-dir",
        queue_dir,
        "--receipts-log",
        receipts_log,
        "--lock-file",
        lock_file,
        "--pid-file",
        pid_file,
    ]


def acquire_lock(lock_path: Path, *, blocking: bool) -> object:
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    handle = lock_path.open("a+", encoding="utf-8")
    operation = fcntl.LOCK_EX
    if not blocking:
        operation |= fcntl.LOCK_NB
    try:
        fcntl.flock(handle.fileno(), operation)
    except OSError:
        handle.close()
        raise
    handle.seek(0)
    handle.truncate()
    handle.write(str(os.getpid()))
    handle.flush()
    return handle


def bridge_startup_lock_path(bridge_lock_file: str) -> Path:
    lock_path = Path(bridge_lock_file)
    suffix = lock_path.suffix or ".lock"
    stem = lock_path.stem if lock_path.suffix else lock_path.name
    return lock_path.with_name(f"{stem}-startup{suffix}")


def ensure_bridge_running(
    *,
    bridge_script: str,
    queue_dir: str,
    bridge_stdout_log: str,
    bridge_receipts_log: str,
    bridge_lock_file: str,
    bridge_pid_file: str,
) -> tuple[int, bool]:
    pid_file = Path(bridge_pid_file)
    existing_pid = read_bridge_pid(pid_file)
    if existing_pid is not None:
        return existing_pid, False

    try:
        startup_lock = acquire_lock(bridge_startup_lock_path(bridge_lock_file), blocking=True)
    except OSError as exc:
        raise RuntimeError(f"failed to acquire bridge startup lock: {exc}") from exc
    try:
        existing_pid = read_bridge_pid(pid_file)
        if existing_pid is not None:
            return existing_pid, False

        bridge_command = build_bridge_command(
            bridge_script=bridge_script,
            queue_dir=queue_dir,
            receipts_log=bridge_receipts_log,
            lock_file=bridge_lock_file,
            pid_file=bridge_pid_file,
        )
        stdout_log_path = Path(bridge_stdout_log)
        stdout_log_path.parent.mkdir(parents=True, exist_ok=True)
        handle = stdout_log_path.open("a", encoding="utf-8")
        try:
            process = subprocess.Popen(
                bridge_command,
                stdin=subprocess.DEVNULL,
                stdout=handle,
                stderr=subprocess.STDOUT,
                start_new_session=True,
                text=True,
            )
        finally:
            handle.close()

        deadline = time.monotonic() + DEFAULT_BRIDGE_START_TIMEOUT_SECONDS
        while time.monotonic() < deadline:
            pid = read_bridge_pid(pid_file)
            if pid is not None:
                return pid, True
            if process.poll() is not None:
                raise RuntimeError(
                    f"tmux handoff app bridge exited before startup finished (code {process.returncode})"
                )
            time.sleep(DEFAULT_BRIDGE_START_POLL_SECONDS)

        if process.poll() is not None:
            raise RuntimeError(
                f"tmux handoff app bridge exited before startup finished (code {process.returncode})"
            )
        return process.pid, True
    finally:
        startup_lock.close()


def queue_input_payload(
    *,
    payload: dict[str, Any],
    bundle: dict[str, Any],
    queue_dir: str,
) -> Path:
    queue_path = Path(queue_dir)
    queue_path.mkdir(parents=True, exist_ok=True)
    event_id = str(bundle.get("event_id") or "").strip()
    if not event_id:
        raise ValueError("tmux handoff bundle is missing event_id")
    timestamp = time.strftime("%Y%m%dT%H%M%S", time.gmtime())
    path = queue_path / f"{timestamp}-{event_id}.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def ensure_queue_event_file(
    *,
    payload: dict[str, Any],
    bundle: dict[str, Any],
    event_file: str | None,
    queue_dir: str,
) -> Path:
    if not event_file:
        return queue_input_payload(payload=payload, bundle=bundle, queue_dir=queue_dir)

    source_path = Path(event_file)
    queue_path = Path(queue_dir)
    try:
        if source_path.parent.resolve() == queue_path.resolve():
            return source_path
    except FileNotFoundError:
        pass
    return queue_input_payload(payload=payload, bundle=bundle, queue_dir=queue_dir)


def maybe_ack_event_file(path: str | None, *, enabled: bool) -> None:
    if not enabled or not path:
        return
    try:
        Path(path).unlink()
    except FileNotFoundError:
        return


def main() -> int:
    args = parse_args()
    try:
        payload = load_json(args.bundle_file or args.event_file)
        bundle = ensure_bundle(payload, session_mode=args.session_mode)
        tmux_handoff = bundle["tmux_skills_handoff"]
        session_mode = str(tmux_handoff.get("target", {}).get("session_mode", args.session_mode))
        notification = tmux_handoff.get("notification", {})
        deliverable = bool(notification.get("deliverable"))
        message = str(notification.get("message", "")).strip()
        codex_thread_id = target_thread_id(bundle)
        if not message:
            raise ValueError("tmux_skills_handoff.notification.message is empty")
        if not codex_thread_id:
            raise ValueError("CODEX_THREAD_ID is missing from tmux-skills handoff payload")
    except (ValueError, KeyError, json.JSONDecodeError) as exc:
        sys.stderr.write(f"{exc}\n")
        return 1

    if not deliverable:
        maybe_ack_event_file(args.event_file, enabled=True)
        json.dump(
            {
                "status": "skipped",
                "reason": "non_deliverable_event",
                "session_mode": session_mode,
                "codex_thread_id": codex_thread_id,
                "message": message,
            },
            sys.stdout,
            ensure_ascii=False,
            indent=2,
        )
        sys.stdout.write("\n")
        return 0

    if args.dry_run:
        bridge_command = build_bridge_command(
            bridge_script=args.bridge_script,
            queue_dir=args.queue_dir,
            receipts_log=args.bridge_receipts_log,
            lock_file=args.bridge_lock_file,
            pid_file=args.bridge_pid_file,
        )
        json.dump(
            {
                "status": "dry_run",
                "transport": "codex_window_ipc",
                "session_mode": session_mode,
                "codex_thread_id": codex_thread_id,
                "bridge_command": bridge_command,
                "bridge_lock_file": args.bridge_lock_file,
                "bridge_pid_file": args.bridge_pid_file,
                "bridge_receipts_log": args.bridge_receipts_log,
                "event_file": args.event_file,
                "message": message,
            },
            sys.stdout,
            ensure_ascii=False,
            indent=2,
        )
        sys.stdout.write("\n")
        return 0

    event_file = ensure_queue_event_file(
        payload=payload,
        bundle=bundle,
        event_file=args.event_file,
        queue_dir=args.queue_dir,
    )

    try:
        bridge_pid, bridge_started = ensure_bridge_running(
            bridge_script=args.bridge_script,
            queue_dir=args.queue_dir,
            bridge_stdout_log=args.bridge_stdout_log,
            bridge_receipts_log=args.bridge_receipts_log,
            bridge_lock_file=args.bridge_lock_file,
            bridge_pid_file=args.bridge_pid_file,
        )
    except RuntimeError as exc:
        sys.stderr.write(str(exc))
        sys.stderr.write("\n")
        return 1

    json.dump(
        {
            "status": "queued_for_bridge",
            "transport": "codex_window_ipc",
            "session_mode": session_mode,
            "codex_thread_id": codex_thread_id,
            "bridge_pid": bridge_pid,
            "bridge_started": bridge_started,
            "bridge_lock_file": args.bridge_lock_file,
            "bridge_pid_file": args.bridge_pid_file,
            "bridge_receipts_log": args.bridge_receipts_log,
            "event_file": str(event_file),
            "message": message,
        },
        sys.stdout,
        ensure_ascii=False,
        indent=2,
    )
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
