#!/usr/bin/env python3
"""Audit whether the current tmux-runtime runtime matches the pure tmux contract."""

from __future__ import annotations

# ==============================================================================
# ENFORCEMENT: This script must be called through the scheduler
# ==============================================================================
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from runtime_enforcement import enforce_via_scheduler
enforce_via_scheduler("check_tmux_ready.py")
# ==============================================================================

import argparse
import json
import shlex
from typing import Any

from runtime_ledger import (
    DEFAULT_FORMAL_PANE_COUNT,
    DEFAULT_FORMAL_SESSION_NAME,
    coerce_slot_bindings,
    evaluate_runtime_ledger_coherence,
)
from tmux_runtime_common import inspect_runtime


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Audit pane count, pane titles, CODEX_THREAD_ID binding, and watcher arming for tmux-runtime."
    )
    parser.add_argument(
        "--expected-pane-count",
        type=int,
        help="Expected pane count for the formal tmux session. Defaults to the runtime ledger value.",
    )
    parser.add_argument(
        "--formal-session-name",
        default=DEFAULT_FORMAL_SESSION_NAME,
        help="Formal session name to audit.",
    )
    parser.add_argument(
        "--require-formal",
        action="store_true",
        help="Require exactly one attached formal session.",
    )
    parser.add_argument(
        "--require-watcher",
        action="store_true",
        help="Require the tmux-runtime stopped-pane watcher to be armed for the formal targets.",
    )
    parser.add_argument(
        "--summary",
        action="store_true",
        help="Emit a compact summary that agents can consume without loading the full audit payload.",
    )
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output.")
    return parser.parse_args()


def actual_formal_panes(
    panes: list[dict[str, Any]],
    formal_session_name: str,
) -> list[dict[str, Any]]:
    items = [pane for pane in panes if pane.get("session_name") == formal_session_name]
    items.sort(key=lambda pane: str(pane.get("target", "")))
    return items


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


def watcher_commands_for_targets(
    bell_processes: list[dict[str, Any]],
    expected_targets: list[str],
) -> list[str]:
    expected = set(expected_targets)
    if not expected:
        return []
    commands: list[str] = []
    for process in bell_processes:
        command = str(process.get("command", "")).strip()
        if not command:
            continue
        if expected.issubset(set(extract_targets_from_command(command))):
            commands.append(command)
    return commands


def evaluate(snapshot: dict[str, Any], args: argparse.Namespace) -> dict[str, Any]:
    reasons: list[str] = []
    warnings: list[str] = []
    next_action: list[str] = []

    runtime_ledger = snapshot.get("runtime_ledger") or {}
    bell_processes = snapshot.get("bell_processes", [])
    formal_panes = actual_formal_panes(snapshot.get("panes", []), args.formal_session_name)
    formal_clients = [
        client
        for client in snapshot.get("clients", [])
        if client.get("session_name") == args.formal_session_name
    ]
    current_client = snapshot.get("current_client") or {}
    actual_targets = [str(pane.get("target", "")).strip() for pane in formal_panes if str(pane.get("target", "")).strip()]
    codex_thread_id = str(snapshot.get("CODEX_THREAD_ID") or "").strip()

    if not runtime_ledger:
        reasons.append("runtime ledger is missing")
        next_action.append("initialize the runtime ledger after pane generation")
        slot_bindings: dict[str, dict[str, str]] = {}
    else:
        ledger_reasons, ledger_warnings = evaluate_runtime_ledger_coherence(runtime_ledger)
        reasons.extend(ledger_reasons)
        warnings.extend(ledger_warnings)
        slot_bindings = coerce_slot_bindings(runtime_ledger.get("slot_bindings"))

    expected_pane_count = args.expected_pane_count
    if expected_pane_count is None:
        try:
            expected_pane_count = int(runtime_ledger.get("pane_count"))
        except (TypeError, ValueError, AttributeError):
            expected_pane_count = DEFAULT_FORMAL_PANE_COUNT

    matching_sessions = [
        session
        for session in snapshot.get("sessions", [])
        if session.get("session_name") == args.formal_session_name
    ]
    if len(matching_sessions) != 1:
        reasons.append(
            f"expected exactly one formal session named {args.formal_session_name}, got {len(matching_sessions)}"
        )
        next_action.append(f"retain exactly one attached {args.formal_session_name}")
    elif int(matching_sessions[0].get("attached", 0)) <= 0:
        reasons.append(f"formal session {args.formal_session_name} is not attached")
        next_action.append(f"attach {args.formal_session_name} in the foreground")

    if not formal_clients:
        reasons.append(f"formal session {args.formal_session_name} has no attached tmux client")
        next_action.append(f"attach {args.formal_session_name} in the current visible terminal")
    elif len(formal_clients) != 1:
        reasons.append(
            f"formal session {args.formal_session_name} must have exactly one attached tmux client, got {len(formal_clients)}"
        )
        next_action.append(f"reduce {args.formal_session_name} to a single visible client")

    if not bool(snapshot.get("current_visible_formal_client")):
        if not current_client.get("inside_tmux"):
            reasons.append(f"current caller is not inside the visible formal session {args.formal_session_name}")
            next_action.append(f"run tmux-runtime from inside the visible {args.formal_session_name} client")
        else:
            reasons.append(f"current caller is not inside the visible formal session {args.formal_session_name}")
            next_action.append(f"switch the current tmux client to {args.formal_session_name}")

    if len(formal_panes) != expected_pane_count:
        reasons.append(
            f"formal pane_count mismatch: expected {expected_pane_count}, actual {len(formal_panes)}"
        )
        next_action.append("reconcile the formal topology to the requested pane count")

    empty_titles = [
        str(pane.get("target", "")).strip()
        for pane in formal_panes
        if not str(pane.get("pane_title_normalized", "")).strip()
    ]
    if empty_titles:
        reasons.append("formal panes include empty titles: " + ", ".join(empty_titles))
        next_action.append("apply pane titles for every formal pane")

    expected_targets = sorted(
        {
            str(binding.get("target", "")).strip()
            for binding in slot_bindings.values()
            if str(binding.get("target", "")).strip()
        }
    )
    if expected_targets and sorted(actual_targets) != expected_targets:
        reasons.append("formal targets do not match runtime ledger slot_bindings")
        next_action.append("refresh the runtime ledger after topology changes")

    actual_titles_by_target = {
        str(pane.get("target", "")).strip(): str(pane.get("pane_title_normalized", "")).strip()
        for pane in formal_panes
    }
    for slot_name, binding in slot_bindings.items():
        target = str(binding.get("target", "")).strip()
        pane_title = str(binding.get("pane_title", "")).strip()
        if not target or target not in actual_titles_by_target:
            reasons.append(f"slot_bindings.{slot_name}.target does not exist in live formal panes")
            continue
        if pane_title and actual_titles_by_target[target] != pane_title:
            reasons.append(
                f"slot_bindings.{slot_name} expects {pane_title} at {target}, actual title is {actual_titles_by_target[target]}"
            )

    codex_thread_bound = False
    if runtime_ledger:
        codex_thread_bound = bool(runtime_ledger.get("codex_thread_bound"))
    if not codex_thread_id:
        reasons.append("CODEX_THREAD_ID is missing")
        next_action.append("bind CODEX_THREAD_ID to the dedicated monitor-thread delivery target")
    elif runtime_ledger and not codex_thread_bound:
        reasons.append("runtime ledger codex_thread_bound is false")
        next_action.append("refresh the runtime ledger after CODEX_THREAD_ID binding")

    watcher = runtime_ledger.get("watcher") if runtime_ledger else {}
    if not isinstance(watcher, dict):
        watcher = {}
    watcher_targets = sorted(str(target).strip() for target in watcher.get("targets", []) if str(target).strip())
    watcher_commands = watcher_commands_for_targets(bell_processes, actual_targets or watcher_targets)
    if args.require_watcher and not bool(watcher.get("armed")):
        reasons.append("runtime watcher is not armed")
        next_action.append("arm the tmux-runtime stopped-pane watcher")
    elif args.require_watcher and watcher_targets and sorted(actual_targets) != watcher_targets:
        reasons.append("runtime watcher targets do not match live formal panes")
        next_action.append("re-arm the watcher for the current formal panes")
    elif args.require_watcher and not watcher_commands:
        reasons.append("runtime watcher process is not running for the formal targets")
        next_action.append("re-arm the tmux-runtime watcher")

    status = "READY" if not reasons else "BLOCKED"
    if not next_action:
        next_action.append("tmux-runtime runtime matches the current contract")

    return {
        "runtime_status": status,
        "formal_session_name": args.formal_session_name,
        "session_count": snapshot.get("session_count", 0),
        "pane_count": snapshot.get("pane_count", 0),
        "formal_pane_count": len(formal_panes),
        "formal_client_count": len(formal_clients),
        "expected_pane_count": expected_pane_count,
        "formal_targets": actual_targets,
        "watcher_targets": watcher_targets,
        "watcher_armed": bool(watcher.get("armed")) and bool(watcher_commands),
        "watcher_commands": watcher_commands,
        "CODEX_THREAD_ID": codex_thread_id,
        "reasons": reasons,
        "warnings": warnings,
        "next_action": next_action,
    }


def summarize(result: dict[str, Any], snapshot: dict[str, Any], args: argparse.Namespace) -> dict[str, Any]:
    runtime_ledger = snapshot.get("runtime_ledger") or {}
    current_client = snapshot.get("current_client") or {}
    formal_panes = actual_formal_panes(snapshot.get("panes", []), args.formal_session_name)
    formal_clients = [
        client
        for client in snapshot.get("clients", [])
        if client.get("session_name") == args.formal_session_name
    ]
    matching_sessions = [
        session
        for session in snapshot.get("sessions", [])
        if session.get("session_name") == args.formal_session_name
    ]
    formal_session_attached = bool(
        len(matching_sessions) == 1 and int(matching_sessions[0].get("attached", 0)) > 0
    )
    expected_pane_count = int(result.get("expected_pane_count") or 0)
    return {
        "mode": "ready_summary",
        "runtime_status": result.get("runtime_status"),
        "formal_session_name": args.formal_session_name,
        "client_visible": bool(current_client.get("visible_terminal_client")),
        "current_visible_formal_client": bool(snapshot.get("current_visible_formal_client")),
        "formal_session_attached": formal_session_attached,
        "formal_client_count": len(formal_clients),
        "formal_pane_count": len(formal_panes),
        "expected_pane_count": expected_pane_count,
        "pane_count_matches_expected": len(formal_panes) == expected_pane_count,
        "watcher_armed": bool(result.get("watcher_armed")),
        "watcher_target_count": len(result.get("watcher_targets", [])),
        "codex_thread_bound": bool(runtime_ledger.get("codex_thread_bound")) and bool(snapshot.get("CODEX_THREAD_ID")),
        "blockers": list(result.get("reasons", [])),
        "next_action": list(result.get("next_action", [])),
    }


def main() -> int:
    args = parse_args()
    snapshot = inspect_runtime(
        args.formal_session_name,
        include_bell_processes=args.require_watcher,
    )
    result = evaluate(snapshot, args)
    payload = summarize(result, snapshot, args) if args.summary else result
    print(json.dumps(payload, ensure_ascii=False, indent=2 if args.pretty else None))
    return 0 if result["runtime_status"] == "READY" else 1


if __name__ == "__main__":
    raise SystemExit(main())
