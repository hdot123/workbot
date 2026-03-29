#!/usr/bin/env python3
"""Shared runtime inspection helpers for tmux-skills."""

from __future__ import annotations

import hashlib
import json
import os
import shlex
import subprocess
from pathlib import Path
from typing import Any

from runtime_ledger import (
    CURRENT_RUNTIME_LEDGER_PATH,
    DEFAULT_FORMAL_PANE_COUNT,
    DEFAULT_FORMAL_SESSION_NAME,
    WHITE_ROLE_TITLES,
    coerce_slot_bindings,
    load_current_runtime_ledger,
)


IDENTITY_CATALOG_PATH = Path("/Users/busiji/workbot/skills/tmux-skills/identities/catalog.json")
WATCHER_SCRIPT_NAME = "watch_tmux_handoff.py"

TMUX_RUNTIME_COMMAND = [
    "tmux",
    "list-panes",
    "-a",
    "-F",
    "#{session_name}\t#{window_index}\t#{pane_index}\t#{pane_id}\t#{pane_title}\t#{window_name}\t#{pane_current_command}\t#{pane_current_path}\t#{window_id}\t#{pane_active}",
]

TMUX_SESSION_COMMAND = [
    "tmux",
    "list-sessions",
    "-F",
    "#{session_name}\t#{session_attached}\t#{session_windows}\t#{session_id}",
]


def run(command: list[str]) -> str:
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip() or "command failed")
    return result.stdout


def normalize_pane_title(value: str) -> str:
    return value.lstrip("✳* ").strip()


def is_claude_runtime_command(command: str) -> bool:
    normalized = str(command or "").strip().lower()
    return normalized in {"node", "claude", "claude-code"}


def resolve_formal_session_name(
    runtime_ledger: dict[str, Any] | None = None,
    override: str | None = None,
) -> str:
    if override:
        normalized = str(override).strip()
        if normalized:
            return normalized
    if runtime_ledger:
        ledger_name = str(runtime_ledger.get("formal_session_name", "")).strip()
        if ledger_name:
            return ledger_name
    return DEFAULT_FORMAL_SESSION_NAME


def list_sessions(formal_session_name: str = DEFAULT_FORMAL_SESSION_NAME) -> list[dict[str, Any]]:
    try:
        output = run(TMUX_SESSION_COMMAND)
    except RuntimeError:
        return []

    sessions: list[dict[str, Any]] = []
    for raw in output.splitlines():
        if not raw.strip():
            continue
        session_name, attached, windows, session_id = raw.split("\t")
        sessions.append(
            {
                "session_name": session_name,
                "attached": int(attached or 0),
                "windows": int(windows or 0),
                "session_id": session_id,
                "is_bootstrap": session_name == "tbot",
                "is_formal": session_name == formal_session_name,
            }
        )
    return sessions


def list_panes(formal_session_name: str = DEFAULT_FORMAL_SESSION_NAME) -> list[dict[str, Any]]:
    try:
        output = run(TMUX_RUNTIME_COMMAND)
    except RuntimeError:
        return []

    panes: list[dict[str, Any]] = []
    for raw in output.splitlines():
        if not raw.strip():
            continue
        (
            session_name,
            window_index,
            pane_index,
            pane_id,
            pane_title,
            window_name,
            current_command,
            current_path,
            window_id,
            pane_active,
        ) = raw.split("\t")
        target = f"{session_name}:{window_index}.{pane_index}"
        normalized_title = normalize_pane_title(pane_title)
        panes.append(
            {
                "target": target,
                "session_name": session_name,
                "window_index": window_index,
                "pane_index": pane_index,
                "pane_id": pane_id,
                "pane_title": pane_title,
                "pane_title_normalized": normalized_title,
                "window_name": window_name,
                "current_command": current_command,
                "pane_current_command": current_command,
                "current_path": current_path,
                "window_id": window_id,
                "pane_active": int(pane_active or 0),
                "is_bootstrap": session_name == "tbot",
                "is_formal": session_name == formal_session_name,
                "is_bot_named": normalized_title in WHITE_ROLE_TITLES,
                "claude_entered": is_claude_runtime_command(current_command),
            }
        )
    return panes


def get_tmux_env(name: str) -> str:
    try:
        output = run(["tmux", "show-environment", "-g"])
    except RuntimeError:
        return os.environ.get(name, "")
    prefix = f"{name}="
    for line in output.splitlines():
        if line.startswith(prefix):
            return line[len(prefix) :]
    return os.environ.get(name, "")


def command_invokes_watcher(command: str) -> bool:
    try:
        tokens = shlex.split(command)
    except ValueError:
        tokens = command.split()
    for index, token in enumerate(tokens):
        if Path(token).name != WATCHER_SCRIPT_NAME:
            continue
        if index == 0:
            return True
        previous = Path(tokens[index - 1]).name.lower()
        if previous.startswith("python"):
            return True
    return False


def get_bell_processes() -> list[dict[str, Any]]:
    result = subprocess.run(
        ["ps", "ax", "-o", "pid=,command="],
        capture_output=True,
        text=True,
        check=False,
    )
    processes: list[dict[str, Any]] = []
    current_pid = os.getpid()
    for line in result.stdout.splitlines():
        raw = line.strip()
        if not raw:
            continue
        parts = raw.split(None, 1)
        if len(parts) != 2:
            continue
        pid_text, command = parts
        if not pid_text.isdigit():
            continue
        pid = int(pid_text)
        normalized_command = command.strip()
        if pid == current_pid or not normalized_command:
            continue
        if not command_invokes_watcher(normalized_command):
            continue
        processes.append({"pid": pid, "command": normalized_command})
    return processes


def select_official_formal_session(
    sessions: list[dict[str, Any]],
    formal_session_name: str,
) -> dict[str, Any] | None:
    attached_formal_sessions = [
        session
        for session in sessions
        if session.get("session_name") == formal_session_name and session.get("attached", 0) > 0
    ]
    if len(attached_formal_sessions) != 1:
        return None
    return attached_formal_sessions[0]


def build_topology_fingerprint(
    official_session: dict[str, Any] | None,
    official_panes: list[dict[str, Any]],
) -> str:
    payload = {
        "official_session": (
            {
                "session_name": official_session["session_name"],
                "attached": official_session["attached"],
                "windows": official_session["windows"],
            }
            if official_session
            else {}
        ),
        "panes": sorted(
            (
                pane["target"],
                pane["pane_title_normalized"],
                pane["window_name"],
                pane["current_command"],
            )
            for pane in official_panes
        ),
    }
    return hashlib.sha1(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()


def inspect_runtime(formal_session_name: str | None = None) -> dict[str, Any]:
    runtime_ledger = load_current_runtime_ledger()
    configured_formal_session_name = resolve_formal_session_name(runtime_ledger, formal_session_name)
    expected_formal_pane_count = DEFAULT_FORMAL_PANE_COUNT
    try:
        ledger_pane_count = int(runtime_ledger.get("pane_count"))
        if ledger_pane_count > 0:
            expected_formal_pane_count = ledger_pane_count
    except (TypeError, ValueError, AttributeError):
        pass
    sessions = list_sessions(configured_formal_session_name)
    panes = list_panes(configured_formal_session_name)
    bell_processes = get_bell_processes()
    session_names = [session["session_name"] for session in sessions]
    formal_sessions = [session["session_name"] for session in sessions if session["is_formal"]]
    bootstrap_sessions = [session["session_name"] for session in sessions if session["is_bootstrap"]]
    formal_session_count = len(formal_sessions)
    official_formal_session = select_official_formal_session(sessions, configured_formal_session_name)
    primary_formal_session = (
        str(official_formal_session["session_name"]) if official_formal_session else ""
    )
    formal_panes = [pane for pane in panes if pane["is_formal"]]
    official_formal_panes = [
        pane for pane in formal_panes if pane["session_name"] == primary_formal_session
    ]
    formal_pane_count_by_session: dict[str, int] = {}
    for pane in formal_panes:
        session_name = pane["session_name"]
        formal_pane_count_by_session[session_name] = (
            formal_pane_count_by_session.get(session_name, 0) + 1
        )

    slot_bindings = coerce_slot_bindings(runtime_ledger.get("slot_bindings"))
    expected_targets = sorted(
        binding.get("target", "")
        for binding in slot_bindings.values()
        if str(binding.get("target", "")).strip()
    )

    return {
        "session_count": len(sessions),
        "pane_count": len(panes),
        "sessions": sessions,
        "panes": panes,
        "session_names": session_names,
        "configured_formal_session_name": configured_formal_session_name,
        "formal_sessions": formal_sessions,
        "formal_session": primary_formal_session,
        "formal_session_count": formal_session_count,
        "single_formal_session": formal_session_count == 1 and bool(primary_formal_session),
        "bootstrap_sessions": bootstrap_sessions,
        "formal_pane_count": len(formal_panes),
        "official_formal_pane_count": len(official_formal_panes),
        "formal_pane_count_by_session": formal_pane_count_by_session,
        "expected_formal_pane_count": expected_formal_pane_count,
        "expected_formal_targets": expected_targets,
        "bootstrap_pane_count": sum(1 for pane in panes if pane["is_bootstrap"]),
        "bot_named_pane_count": sum(1 for pane in panes if pane["is_bot_named"]),
        "claude_entered_pane_count": sum(1 for pane in panes if pane["claude_entered"]),
        "CODEX_THREAD_ID": get_tmux_env("CODEX_THREAD_ID"),
        "bell_processes": bell_processes,
        "bell_armed": bool(bell_processes),
        "identity_catalog_path": str(IDENTITY_CATALOG_PATH),
        "identity_catalog_present": IDENTITY_CATALOG_PATH.exists(),
        "runtime_ledger_path": str(CURRENT_RUNTIME_LEDGER_PATH),
        "runtime_ledger_present": bool(runtime_ledger),
        "runtime_ledger": runtime_ledger,
        "topology_fingerprint": build_topology_fingerprint(
            official_formal_session,
            official_formal_panes,
        ),
    }
