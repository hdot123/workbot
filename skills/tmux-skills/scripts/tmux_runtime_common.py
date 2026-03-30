#!/usr/bin/env python3
"""Shared tmux runtime inspection helpers for tmux-skills."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shlex
import subprocess
import sys
from pathlib import Path
from typing import Any

from runtime_ledger import (
    CURRENT_RUNTIME_LEDGER_PATH,
    DEFAULT_FORMAL_PANE_COUNT,
    DEFAULT_FORMAL_SESSION_NAME,
    coerce_slot_bindings,
    load_current_runtime_ledger,
)


WATCHER_SCRIPT_NAME = "watch_tmux_handoff.py"
CODex_PROCESS_TOKEN = "/Applications/Codex.app/"
KNOWN_TERMINAL_MARKERS = (
    "Apple_Terminal",
    "iTerm",
    "WezTerm",
    "Alacritty",
    "Ghostty",
    "kitty",
    "Warp",
    "Hyper",
    "Tabby",
    "Rio",
    "Terminal.app",
    "iTerm2.app",
    "WezTerm.app",
    "Ghostty.app",
    "kitty.app",
)
KNOWN_TERMINAL_BUNDLE_IDS = {
    "com.apple.Terminal": "Apple_Terminal",
    "com.googlecode.iterm2": "iTerm",
}
NON_VISIBLE_TERMINAL_PROGRAMS = {"tmux"}
LEGACY_BOOTSTRAP_SESSION_NAME = "tbot"

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

TMUX_CLIENT_COMMAND = [
    "tmux",
    "list-clients",
    "-F",
    "#{client_tty}\t#{session_name}\t#{client_pid}\t#{client_width}\t#{client_height}",
]


def run(command: list[str]) -> str:
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip() or "command failed")
    return result.stdout


def normalize_pane_title(value: str) -> str:
    return value.lstrip("✳* ").strip()


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


def is_legacy_bootstrap_session(session_name: str) -> bool:
    return session_name == LEGACY_BOOTSTRAP_SESSION_NAME


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
                "is_bootstrap": is_legacy_bootstrap_session(session_name),
                "is_formal": session_name == formal_session_name,
            }
        )
    return sessions


def list_clients(formal_session_name: str = DEFAULT_FORMAL_SESSION_NAME) -> list[dict[str, Any]]:
    try:
        output = run(TMUX_CLIENT_COMMAND)
    except RuntimeError:
        return []

    clients: list[dict[str, Any]] = []
    for raw in output.splitlines():
        if not raw.strip():
            continue
        client_tty, session_name, client_pid, width, height = raw.split("\t")
        clients.append(
            {
                "client_tty": client_tty,
                "session_name": session_name,
                "client_pid": int(client_pid or 0),
                "client_width": int(width or 0),
                "client_height": int(height or 0),
                "is_formal": session_name == formal_session_name,
            }
        )
    return clients


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
        panes.append(
            {
                "target": target,
                "session_name": session_name,
                "window_index": window_index,
                "pane_index": pane_index,
                "pane_id": pane_id,
                "pane_title": pane_title,
                "pane_title_normalized": normalize_pane_title(pane_title),
                "window_name": window_name,
                "current_command": current_command,
                "pane_current_command": current_command,
                "current_path": current_path,
                "window_id": window_id,
                "pane_active": int(pane_active or 0),
                "is_bootstrap": is_legacy_bootstrap_session(session_name),
                "is_formal": session_name == formal_session_name,
            }
        )
    return panes


def get_tmux_env(name: str, *, allow_os_fallback: bool = False) -> str:
    try:
        output = run(["tmux", "show-environment", "-g"])
    except RuntimeError:
        return os.environ.get(name, "") if allow_os_fallback else ""
    prefix = f"{name}="
    for line in output.splitlines():
        if line.startswith(prefix):
            return line[len(prefix) :]
    return os.environ.get(name, "") if allow_os_fallback else ""


def resolve_current_tty() -> str:
    for stream in (sys.stdin, sys.stdout, sys.stderr):
        try:
            fileno = stream.fileno()
        except (AttributeError, OSError, ValueError):
            continue
        try:
            return os.ttyname(fileno)
        except OSError:
            continue
    return ""


def process_ancestry_commands(start_pid: int | None = None, max_depth: int = 6) -> list[str]:
    ancestry: list[str] = []
    pid = int(start_pid or os.getpid())
    for _ in range(max(0, max_depth)):
        proc = subprocess.run(
            ["ps", "-o", "ppid=,command=", "-p", str(pid)],
            capture_output=True,
            text=True,
            check=False,
        )
        if proc.returncode != 0:
            break
        line = proc.stdout.strip()
        if not line:
            break
        ppid_text, _, command = line.partition(" ")
        command = command.strip()
        if command:
            ancestry.append(command)
        if not ppid_text.strip().isdigit():
            break
        next_pid = int(ppid_text.strip())
        if next_pid <= 1 or next_pid == pid:
            if next_pid == 1:
                root = subprocess.run(
                    ["ps", "-o", "command=", "-p", "1"],
                    capture_output=True,
                    text=True,
                    check=False,
                )
                root_command = root.stdout.strip()
                if root_command:
                    ancestry.append(root_command)
            break
        pid = next_pid
    return ancestry


def read_process_environment_values(pid: int | None, *names: str) -> dict[str, str]:
    if not pid or pid <= 0 or not names:
        return {}
    proc = subprocess.run(
        ["ps", "eww", "-o", "command=", "-p", str(pid)],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        return {}
    output = proc.stdout.strip()
    values: dict[str, str] = {}
    for name in names:
        match = re.search(rf"(?:^| ){re.escape(name)}=([^ ]*)", output)
        if match:
            values[name] = match.group(1).strip()
    return values


def resolve_terminal_provenance(client_pid: int | None = None) -> dict[str, Any]:
    process_env = read_process_environment_values(
        client_pid,
        "TERM_PROGRAM",
        "LC_TERMINAL",
        "TERM_PROGRAM_VERSION",
        "__CFBundleIdentifier",
    )
    term_program = str(process_env.get("TERM_PROGRAM") or os.environ.get("TERM_PROGRAM", "")).strip()
    lc_terminal = str(process_env.get("LC_TERMINAL") or os.environ.get("LC_TERMINAL", "")).strip()
    term_program_version = str(
        process_env.get("TERM_PROGRAM_VERSION") or os.environ.get("TERM_PROGRAM_VERSION", "")
    ).strip()
    bundle_identifier = str(
        process_env.get("__CFBundleIdentifier") or os.environ.get("__CFBundleIdentifier", "")
    ).strip()
    if term_program in NON_VISIBLE_TERMINAL_PROGRAMS:
        term_program = ""
    if lc_terminal in NON_VISIBLE_TERMINAL_PROGRAMS:
        lc_terminal = ""
    ancestry = process_ancestry_commands(start_pid=client_pid)

    known_terminal = ""
    for marker in KNOWN_TERMINAL_MARKERS:
        if term_program == marker or lc_terminal == marker:
            known_terminal = marker
            break
        if any(marker in command for command in ancestry):
            known_terminal = marker
            break
    if not known_terminal and bundle_identifier:
        known_terminal = KNOWN_TERMINAL_BUNDLE_IDS.get(bundle_identifier, "")

    codex_hosted = any(CODex_PROCESS_TOKEN in command for command in ancestry)
    if bundle_identifier == "com.openai.codex":
        codex_hosted = True
    visible_terminal_client = bool(term_program or lc_terminal or known_terminal)
    reason = "terminal_marker_detected" if visible_terminal_client else "missing_terminal_marker"
    if not visible_terminal_client and codex_hosted:
        reason = "codex_hidden_pty"

    return {
        "term_program": term_program,
        "lc_terminal": lc_terminal,
        "term_program_version": term_program_version,
        "bundle_identifier": bundle_identifier,
        "process_ancestry": ancestry,
        "known_terminal_marker": known_terminal,
        "codex_hosted": codex_hosted,
        "visible_terminal_client": visible_terminal_client,
        "visibility_reason": reason,
    }


def resolve_current_tmux_context() -> dict[str, Any]:
    context = {
        "inside_tmux": bool(os.environ.get("TMUX")),
        "client_tty": "",
        "client_pid": 0,
        "session_name": "",
        "window_index": "",
        "pane_index": "",
        "pane_id": "",
        "current_tty": resolve_current_tty(),
        "term_program": "",
        "lc_terminal": "",
        "term_program_version": "",
        "bundle_identifier": "",
        "known_terminal_marker": "",
        "codex_hosted": False,
        "visible_terminal_client": False,
        "visibility_reason": "",
        "process_ancestry": [],
    }
    if context["inside_tmux"]:
        try:
            output = run(
                [
                    "tmux",
                    "display-message",
                    "-p",
                    "#{client_tty}\t#{client_pid}\t#{session_name}\t#{window_index}\t#{pane_index}\t#{pane_id}",
                ]
            ).strip()
        except RuntimeError:
            output = ""
        if output:
            parts = output.split("\t")
            if len(parts) == 6:
                client_tty, client_pid, session_name, window_index, pane_index, pane_id = parts
                context.update(
                    {
                        "client_tty": client_tty,
                        "client_pid": int(client_pid or 0),
                        "session_name": session_name,
                        "window_index": window_index,
                        "pane_index": pane_index,
                        "pane_id": pane_id,
                    }
                )
    terminal_provenance = resolve_terminal_provenance(
        client_pid=int(context.get("client_pid") or 0) or None
    )
    context.update(
        {
            "term_program": terminal_provenance["term_program"],
            "lc_terminal": terminal_provenance["lc_terminal"],
            "term_program_version": terminal_provenance["term_program_version"],
            "bundle_identifier": terminal_provenance["bundle_identifier"],
            "known_terminal_marker": terminal_provenance["known_terminal_marker"],
            "codex_hosted": terminal_provenance["codex_hosted"],
            "visible_terminal_client": terminal_provenance["visible_terminal_client"],
            "visibility_reason": terminal_provenance["visibility_reason"],
            "process_ancestry": terminal_provenance["process_ancestry"],
        }
    )
    return context


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
    clients: list[dict[str, Any]],
    formal_session_name: str,
) -> dict[str, Any] | None:
    attached_formal_clients = [
        client for client in clients if client.get("session_name") == formal_session_name
    ]
    if len(attached_formal_clients) != 1:
        return None
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
    clients = list_clients(configured_formal_session_name)
    panes = list_panes(configured_formal_session_name)
    bell_processes = get_bell_processes()
    current_client = resolve_current_tmux_context()
    session_names = [session["session_name"] for session in sessions]
    formal_sessions = [session["session_name"] for session in sessions if session["is_formal"]]
    bootstrap_sessions = [session["session_name"] for session in sessions if session["is_bootstrap"]]
    formal_session_count = len(formal_sessions)
    formal_clients = [client for client in clients if client.get("session_name") == configured_formal_session_name]
    current_client_is_formal = bool(
        current_client.get("inside_tmux")
        and current_client.get("session_name") == configured_formal_session_name
        and any(
            client.get("client_tty") == current_client.get("client_tty")
            for client in formal_clients
        )
    )
    current_visible_formal_client = (
        current_client_is_formal
        and len(formal_clients) == 1
        and bool(current_client.get("visible_terminal_client"))
    )
    official_formal_session = select_official_formal_session(
        sessions,
        clients,
        configured_formal_session_name,
    )
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
        "clients": clients,
        "current_client": current_client,
        "panes": panes,
        "session_names": session_names,
        "configured_formal_session_name": configured_formal_session_name,
        "formal_sessions": formal_sessions,
        "formal_session": primary_formal_session,
        "formal_session_count": formal_session_count,
        "formal_clients": formal_clients,
        "formal_client_count": len(formal_clients),
        "current_client_is_formal": current_client_is_formal,
        "current_visible_formal_client": current_visible_formal_client,
        "single_formal_session": formal_session_count == 1 and bool(primary_formal_session),
        "bootstrap_sessions": bootstrap_sessions,
        "formal_pane_count": len(formal_panes),
        "official_formal_pane_count": len(official_formal_panes),
        "formal_pane_count_by_session": formal_pane_count_by_session,
        "expected_formal_pane_count": expected_formal_pane_count,
        "expected_formal_targets": expected_targets,
        "bootstrap_pane_count": sum(1 for pane in panes if pane["is_bootstrap"]),
        "CODEX_THREAD_ID": get_tmux_env("CODEX_THREAD_ID"),
        "bell_processes": bell_processes,
        "bell_armed": bool(bell_processes),
        "runtime_ledger_path": str(CURRENT_RUNTIME_LEDGER_PATH),
        "runtime_ledger_present": bool(runtime_ledger),
        "runtime_ledger": runtime_ledger,
        "topology_fingerprint": build_topology_fingerprint(
            official_formal_session,
            official_formal_panes,
        ),
    }
