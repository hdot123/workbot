#!/usr/bin/env python3
"""Phase-1 tmux environment setup for tmux-skills."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import time
from typing import Any

from tmux_runtime_common import inspect_runtime


def run_tmux(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["tmux", *args], capture_output=True, text=True, check=False)


def list_sessions() -> list[dict[str, Any]]:
    snapshot = inspect_runtime()
    return snapshot["sessions"]


def kill_detached_sessions() -> list[str]:
    removed: list[str] = []
    for session in list_sessions():
        if session["attached"] != 0:
            continue
        proc = run_tmux("kill-session", "-t", session["session_name"])
        if proc.returncode == 0:
            removed.append(session["session_name"])
    return removed


def reject_background_session_creation(session_name: str) -> None:
    raise RuntimeError(
        "foreground-only tmux policy forbids creating detached/background sessions: "
        f"{session_name}. Prepare and attach the formal session manually first."
    )


def create_or_switch_visible_formal_session(session_name: str, cwd: str) -> dict[str, Any]:
    proc = run_tmux("new-session", "-Ad", "-s", session_name, "-c", cwd)
    if proc.returncode != 0:
        raise RuntimeError(
            proc.stderr.strip() or proc.stdout.strip() or f"failed to create tmux session {session_name}"
        )
    switch_proc = run_tmux("switch-client", "-t", session_name)
    if switch_proc.returncode != 0:
        raise RuntimeError(
            switch_proc.stderr.strip()
            or switch_proc.stdout.strip()
            or f"failed to switch current client to {session_name}"
        )
    return {
        "transport": "current_tmux_client",
        "session_name": session_name,
        "cwd": cwd,
    }


def require_tmux_client_for_formal_session_change(
    snapshot: dict[str, Any],
    formal_session: str,
) -> dict[str, Any]:
    current_client = snapshot.get("current_client") or {}
    if not current_client.get("inside_tmux"):
        raise RuntimeError(
            "foreground tmux changes must run from inside the visible tmux client; "
            f"refusing to create or switch {formal_session} from a non-tmux context"
        )
    if not current_client.get("visible_terminal_client"):
        reason = str(current_client.get("visibility_reason") or "invisible_terminal_client")
        raise RuntimeError(
            "foreground tmux changes must run from a real visible terminal client; "
            f"refusing to create or switch {formal_session} from {reason}"
        )
    return current_client


def wait_for_attached_formal_session(session_name: str, timeout_seconds: float = 8.0) -> dict[str, Any]:
    deadline = time.monotonic() + max(0.1, timeout_seconds)
    last_snapshot: dict[str, Any] = inspect_runtime()
    while time.monotonic() < deadline:
        snapshot = inspect_runtime()
        last_snapshot = snapshot
        if bool(snapshot.get("current_visible_formal_client")):
            return snapshot
        time.sleep(0.25)
    raise RuntimeError(
        f"formal session {session_name} did not become the current visible tmux client within {timeout_seconds:.1f}s"
    )


def enforce_destroy_unattached(session_name: str) -> str:
    proc = run_tmux("set-option", "-t", session_name, "destroy-unattached", "on")
    if proc.returncode != 0:
        raise RuntimeError(
            proc.stderr.strip() or proc.stdout.strip() or "failed to enable destroy-unattached"
        )
    return "destroy_unattached=on"


def kill_session(session_name: str) -> bool:
    proc = run_tmux("kill-session", "-t", session_name)
    return proc.returncode == 0


def find_bootstrap_panel_path(snapshot: dict[str, Any], bootstrap_name: str) -> str | None:
    for pane in snapshot.get("panes", []):
        if pane.get("session_name") == bootstrap_name:
            path = pane.get("current_path")
            if path:
                return path
    return None


def resolve_formal_cwd(cli_value: str | None, default_cwd: str, snapshot: dict[str, Any], bootstrap_name: str) -> str:
    if cli_value:
        return os.path.abspath(cli_value)
    bootstrap_path = find_bootstrap_panel_path(snapshot, bootstrap_name)
    if bootstrap_path:
        return os.path.abspath(bootstrap_path)
    return os.path.abspath(default_cwd)


def find_primary_pane_target(snapshot: dict[str, Any], session_name: str) -> str | None:
    panes = [pane for pane in snapshot.get("panes", []) if pane.get("session_name") == session_name]
    if not panes:
        return None
    panes.sort(key=lambda pane: (int(pane.get("window_index", "0")), int(pane.get("pane_index", "0"))))
    return panes[0].get("target")


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


def cleanup_bootstrap_sessions() -> list[str]:
    removed: list[str] = []
    for session in list_sessions():
        if not session["is_bootstrap"]:
            continue
        if kill_session(session["session_name"]):
            removed.append(session["session_name"])
    return removed


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create or normalize the tmux environment for tmux-skills.")
    parser.add_argument("--bootstrap-name", default="tbot", help="Bootstrap temporary session name.")
    parser.add_argument("--cwd", default="/Users/busiji/workbot", help="Working directory for a new session.")
    parser.add_argument(
        "--create-if-missing",
        action="store_true",
        help="Deprecated. Foreground-only policy no longer allows creating detached bootstrap sessions.",
    )
    parser.add_argument("--formal-session", help="Formal session name (single official runtime session).")
    parser.add_argument("--formal-cwd", help="Working directory for the formal session.")
    parser.add_argument(
        "--create-formal-session",
        action="store_true",
        help="Create or attach the formal session using the current visible tmux client.",
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
    parser.add_argument("--cleanup-bootstrap", action="store_true", help="Kill bootstrap sessions after optional formal sessions are in place.")
    parser.add_argument("--kill-detached", action="store_true", help="Kill detached sessions before inspecting the environment.")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    create_formal_session = args.create_formal_session
    formal_session = (args.formal_session or "formal-session").strip() or "formal-session"
    formal_cwd_cli = (args.formal_cwd or "").strip()
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

    removed = kill_detached_sessions() if args.kill_detached else []
    snapshot_before = inspect_runtime()
    snapshot_current = snapshot_before
    created_bootstrap = None
    if args.create_if_missing and snapshot_before["session_count"] == 0:
        reject_background_session_creation(args.bootstrap_name)

    formal_cwd = resolve_formal_cwd(
        formal_cwd_cli or None, args.cwd, snapshot_current, args.bootstrap_name
    )

    created_formal: dict[str, Any] | None = None
    if create_formal_session:
        current_client = require_tmux_client_for_formal_session_change(snapshot_current, formal_session)
        if formal_session not in snapshot_current["session_names"]:
            created_formal = create_or_switch_visible_formal_session(formal_session, formal_cwd)
            snapshot_current = wait_for_attached_formal_session(formal_session)
        elif current_client.get("session_name") != formal_session:
            created_formal = create_or_switch_visible_formal_session(formal_session, formal_cwd)
            snapshot_current = wait_for_attached_formal_session(formal_session)

    formal_session_policy_actions: list[str] = []
    if any(
        session.get("session_name") == formal_session and int(session.get("attached", 0)) > 0
        for session in snapshot_current.get("sessions", [])
    ):
        formal_session_policy_actions.append(enforce_destroy_unattached(formal_session))
        snapshot_current = inspect_runtime()

    initialized_formal: dict[str, Any] | None = None
    if init_requested and formal_session in snapshot_current["session_names"]:
        initialized_formal = initialize_formal_surface(
            snapshot_current,
            formal_session,
            formal_window_title,
            formal_pane_title or None,
            formal_startup_command or None,
        )
        snapshot_current = inspect_runtime()

    removed_bootstrap: list[str] = []
    if args.cleanup_bootstrap:
        removed_bootstrap = cleanup_bootstrap_sessions()
        snapshot_current = inspect_runtime()

    snapshot_after = snapshot_current
    formal_session_exists = formal_session in snapshot_after["session_names"]
    active_formal_sessions = [name for name in snapshot_after["formal_sessions"] if name]
    extra_formal_sessions = [name for name in active_formal_sessions if name != formal_session]
    formal_attached = any(
        session.get("session_name") == formal_session and int(session.get("attached", 0)) > 0
        for session in snapshot_after.get("sessions", [])
    )
    formal_client_count = int(snapshot_after.get("formal_client_count", 0) or 0)
    current_visible_formal_client = bool(snapshot_after.get("current_visible_formal_client"))
    single_attached_formal = (
        formal_session_exists
        and not extra_formal_sessions
        and formal_attached
        and formal_client_count == 1
        and current_visible_formal_client
    )
    if snapshot_after["session_count"] == 0:
        runtime_status = "BLOCKED"
        formal_surface_status = "NONE"
    elif single_attached_formal:
        runtime_status = "INIT_IN_PROGRESS"
        formal_surface_status = "COMPLETE"
    elif snapshot_after["bootstrap_sessions"]:
        runtime_status = "BOOTSTRAP"
        formal_surface_status = "NONE"
    else:
        runtime_status = "BLOCKED"
        formal_surface_status = "NONE"

    result = {
        "phase": "env",
        "removed_detached_sessions": removed,
        "removed_bootstrap_sessions": removed_bootstrap,
        "created_bootstrap_session": created_bootstrap,
        "created_formal_session": created_formal,
        "initialized_formal_session": initialized_formal,
        "session_count_before": snapshot_before["session_count"],
        "session_count_after": snapshot_after["session_count"],
        "bootstrap_sessions": snapshot_after["bootstrap_sessions"],
        "formal_sessions": snapshot_after["formal_sessions"],
        "bootstrap_primary_cwd": find_bootstrap_panel_path(snapshot_after, args.bootstrap_name),
        "formal_session": formal_session,
        "formal_session_exists": formal_session_exists,
        "formal_session_attached": formal_attached,
        "formal_client_count": formal_client_count,
        "current_visible_formal_client": current_visible_formal_client,
        "extra_formal_sessions": extra_formal_sessions,
        "single_attached_formal_session": single_attached_formal,
        "formal_cwd": formal_cwd,
        "formal_surface_status": formal_surface_status,
        "runtime_status": runtime_status,
        "formal_session_policy_actions": formal_session_policy_actions,
    }
    if args.pretty:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(json.dumps(result, ensure_ascii=False))
    return 0 if single_attached_formal else 1


if __name__ == "__main__":
    raise SystemExit(main())
