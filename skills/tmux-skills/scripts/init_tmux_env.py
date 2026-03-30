#!/usr/bin/env python3
"""Phase-1 tmux environment setup for tmux-skills."""

from __future__ import annotations

import argparse
import json
import os
import shlex
import subprocess
from typing import Any

from tmux_runtime_common import inspect_runtime


def run_tmux(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["tmux", *args], capture_output=True, text=True, check=False)


def require_visible_terminal_launcher(snapshot: dict[str, Any], formal_session: str) -> dict[str, Any]:
    current_client = snapshot.get("current_client") or {}
    if current_client.get("inside_tmux"):
        raise RuntimeError(
            "new tmux-skills tasks must start from a fresh visible terminal, "
            f"not from inside an existing tmux session when creating {formal_session}"
        )
    if not current_client.get("visible_terminal_client"):
        reason = str(current_client.get("visibility_reason") or "invisible_terminal_client")
        raise RuntimeError(
            "new tmux-skills tasks must start from a real visible terminal client; "
            f"refusing startup from {reason}"
        )
    return current_client


def require_empty_tmux_runtime(snapshot: dict[str, Any]) -> None:
    session_names = [
        str(session.get("session_name") or "").strip()
        for session in snapshot.get("sessions", [])
        if str(session.get("session_name") or "").strip()
    ]
    if session_names:
        raise RuntimeError(
            "tmux residue must be cleared before formal env setup: " + ", ".join(session_names)
        )


def resolve_formal_cwd(cli_value: str | None, default_cwd: str) -> str:
    if cli_value:
        return os.path.abspath(cli_value)
    return os.path.abspath(default_cwd)


def create_detached_formal_session(session_name: str, cwd: str) -> dict[str, Any]:
    proc = run_tmux("new-session", "-d", "-s", session_name, "-c", cwd)
    if proc.returncode != 0:
        raise RuntimeError(
            proc.stderr.strip() or proc.stdout.strip() or f"failed to create tmux session {session_name}"
        )
    return {
        "transport": "fresh_visible_terminal",
        "session_name": session_name,
        "cwd": cwd,
    }


def find_primary_pane_target(snapshot: dict[str, Any], session_name: str) -> str | None:
    panes = [pane for pane in snapshot.get("panes", []) if pane.get("session_name") == session_name]
    if not panes:
        return None
    panes.sort(key=lambda pane: (int(pane.get("window_index", "0")), int(pane.get("pane_index", "0"))))
    return str(panes[0].get("target") or "").strip() or None


def rename_primary_window(session_name: str, window_index: str, title: str) -> str:
    proc = run_tmux("rename-window", "-t", f"{session_name}:{window_index}", title)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or proc.stdout.strip() or "failed to rename tmux window")
    return f"window_title={title}"


def set_pane_title(target: str, title: str) -> str:
    proc = run_tmux("select-pane", "-t", target, "-T", title)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or proc.stdout.strip() or "failed to set pane title")
    return f"pane_title={title}"


def send_startup_command(target: str, command: str) -> str:
    proc = run_tmux("send-keys", "-t", target, "C-c", command, "Enter")
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or proc.stdout.strip() or "failed to send startup command")
    return f"startup_command={shlex.quote(command)}"


def initialize_formal_surface(
    snapshot: dict[str, Any],
    session_name: str,
    default_window_title: str,
    pane_title: str | None,
    startup_command: str | None,
) -> dict[str, Any]:
    actions: list[str] = []
    pane_target = find_primary_pane_target(snapshot, session_name)
    if not pane_target:
        raise RuntimeError(f"no panes found for formal session: {session_name}")
    window_index = pane_target.split(":", 1)[1].split(".", 1)[0]
    actions.append(rename_primary_window(session_name, window_index, default_window_title))
    if pane_title:
        actions.append(set_pane_title(pane_target, pane_title))
    if startup_command:
        actions.append(send_startup_command(pane_target, startup_command))
    return {
        "session_name": session_name,
        "primary_target": pane_target,
        "actions": actions,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create or normalize the tmux environment for tmux-skills.")
    parser.add_argument("--cwd", default="/Users/busiji/workbot", help="Working directory for a new session.")
    parser.add_argument("--formal-session", help="Formal session name (single official runtime session).")
    parser.add_argument("--formal-cwd", help="Working directory for the formal session.")
    parser.add_argument(
        "--create-formal-session",
        action="store_true",
        help="Create a new formal session for a fresh tmux-skills task startup.",
    )
    parser.add_argument(
        "--initialize-formal-surfaces",
        action="store_true",
        help="Initialize the formal session surface (window/pane title, optional startup command).",
    )
    parser.add_argument(
        "--formal-window-title",
        help="Window title used for formal session initialization.",
    )
    parser.add_argument("--formal-pane-title", help="Optional pane title for the primary pane in the formal session.")
    parser.add_argument(
        "--formal-startup-command",
        help="Optional startup command sent to the primary formal pane after session initialization.",
    )
    parser.add_argument(
        "--kill-detached",
        action="store_true",
        help="Deprecated no-op kept for compatibility with older callers.",
    )
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    create_formal_session = args.create_formal_session
    formal_session = (args.formal_session or "formal-session").strip() or "formal-session"
    formal_cwd = resolve_formal_cwd((args.formal_cwd or "").strip() or None, args.cwd)
    formal_window_title = (args.formal_window_title or formal_session).strip() or formal_session
    formal_pane_title = (args.formal_pane_title or "").strip()
    formal_startup_command = (args.formal_startup_command or "").strip()
    init_requested = any(
        (
            args.initialize_formal_surfaces,
            create_formal_session,
            formal_window_title != formal_session,
            bool(formal_pane_title),
            bool(formal_startup_command),
        )
    )

    snapshot_before = inspect_runtime()
    snapshot_current = snapshot_before

    created_formal: dict[str, Any] | None = None
    if create_formal_session:
        require_visible_terminal_launcher(snapshot_current, formal_session)
        require_empty_tmux_runtime(snapshot_current)
        created_formal = create_detached_formal_session(formal_session, formal_cwd)
        snapshot_current = inspect_runtime()

    initialized_formal: dict[str, Any] | None = None
    if init_requested and formal_session in snapshot_current.get("session_names", []):
        initialized_formal = initialize_formal_surface(
            snapshot_current,
            formal_session,
            formal_window_title,
            formal_pane_title or None,
            formal_startup_command or None,
        )
        snapshot_current = inspect_runtime()

    snapshot_after = snapshot_current
    formal_session_exists = formal_session in snapshot_after.get("session_names", [])
    active_formal_sessions = [name for name in snapshot_after.get("formal_sessions", []) if name]
    extra_formal_sessions = [name for name in active_formal_sessions if name != formal_session]
    single_prepared_formal = (
        create_formal_session
        and formal_session_exists
        and not extra_formal_sessions
        and int(snapshot_after.get("session_count", 0) or 0) == 1
    )
    continuation_surface_prepared = (
        not create_formal_session
        and init_requested
        and formal_session_exists
        and initialized_formal is not None
        and not extra_formal_sessions
    )
    env_ok = single_prepared_formal or continuation_surface_prepared

    result = {
        "phase": "env",
        "removed_detached_sessions": [],
        "removed_bootstrap_sessions": [],
        "created_formal_session": created_formal,
        "initialized_formal_session": initialized_formal,
        "session_count_before": snapshot_before.get("session_count", 0),
        "session_count_after": snapshot_after.get("session_count", 0),
        "bootstrap_sessions": snapshot_after.get("bootstrap_sessions", []),
        "formal_sessions": snapshot_after.get("formal_sessions", []),
        "formal_session": formal_session,
        "formal_session_exists": formal_session_exists,
        "formal_session_attached": False,
        "formal_client_count": 0,
        "current_visible_formal_client": False,
        "extra_formal_sessions": extra_formal_sessions,
        "single_attached_formal_session": False,
        "formal_cwd": formal_cwd,
        "formal_surface_status": "PREPARED" if env_ok else "NONE",
        "runtime_status": "ATTACH_PENDING"
        if single_prepared_formal
        else ("SURFACE_READY" if continuation_surface_prepared else "BLOCKED"),
        "formal_session_policy_actions": [],
    }
    if args.pretty:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(json.dumps(result, ensure_ascii=False))
    return 0 if env_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
