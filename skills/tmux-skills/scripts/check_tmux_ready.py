#!/usr/bin/env python3
"""Evaluate whether the current Workbot tmux runtime is ready."""

from __future__ import annotations

import argparse
import json
import shlex
from typing import Any

from runtime_ledger import (
    DEFAULT_FORMAL_PANE_COUNT,
    DEFAULT_FORMAL_SESSION_NAME,
    WHITE_ROLE_TITLES,
    coerce_slot_bindings,
    evaluate_runtime_ledger_coherence,
)
from tmux_runtime_common import inspect_runtime


def resolve_formal_session_name(args: argparse.Namespace) -> str:
    explicit = str(getattr(args, "formal_session_name", "") or "").strip()
    if explicit:
        return explicit
    legacy_task = str(getattr(args, "task_session_name", "") or "").strip()
    if legacy_task:
        return legacy_task
    legacy_monitor = str(getattr(args, "monitor_session_name", "") or "").strip()
    if legacy_monitor:
        return legacy_monitor
    return DEFAULT_FORMAL_SESSION_NAME


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


def actual_formal_panes(
    panes: list[dict[str, Any]],
    formal_session_name: str,
) -> list[dict[str, Any]]:
    items = [pane for pane in panes if pane.get("session_name") == formal_session_name]
    items.sort(key=lambda pane: str(pane.get("target", "")))
    return items


def watcher_commands_for_targets(
    bell_processes: list[dict[str, Any]],
    expected_targets: list[str],
) -> list[str]:
    expected = set(expected_targets)
    if not expected:
        return []
    matched: list[str] = []
    for process in bell_processes:
        command = str(process.get("command", "")).strip()
        if not command:
            continue
        targets = set(extract_targets_from_command(command))
        if not targets:
            continue
        if expected.issubset(targets):
            matched.append(command)
    return matched


def watcher_commands_for_target(
    bell_processes: list[dict[str, Any]],
    target: str,
) -> list[str]:
    matched: list[str] = []
    if not target:
        return matched
    for process in bell_processes:
        command = str(process.get("command", "")).strip()
        if not command:
            continue
        if target in extract_targets_from_command(command):
            matched.append(command)
    return matched


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check whether the current Workbot tmux runtime is ready.")
    parser.add_argument("--expected-pane-count", type=int, help="Expected pane count for the current runtime topology.")
    parser.add_argument("--require-formal", action="store_true", help="Require the single formal non-bootstrap session.")
    parser.add_argument(
        "--require-bell",
        action="store_true",
        help="Require the tmux-skills handoff watcher to be armed.",
    )
    parser.add_argument(
        "--formal-session-name",
        default=DEFAULT_FORMAL_SESSION_NAME,
        help="Single formal session name that must exist when formal runtime readiness is enforced.",
    )
    parser.add_argument(
        "--task-session-name",
        default="",
        help="Deprecated alias for --formal-session-name.",
    )
    parser.add_argument(
        "--monitor-session-name",
        default="",
        help="Deprecated alias for --formal-session-name.",
    )
    parser.add_argument(
        "--allow-extra-formal-sessions",
        action="store_true",
        help="Deprecated and ignored: runtime now enforces exactly one formal session.",
    )
    parser.add_argument("--allow-bootstrap", action="store_true", help="Allow bootstrap-only status instead of treating it as not ready.")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output.")
    return parser.parse_args()


def evaluate(snapshot: dict[str, Any], args: argparse.Namespace) -> dict[str, Any]:
    reasons: list[str] = []
    warnings: list[str] = []
    next_action: list[str] = []

    formal_session_name = resolve_formal_session_name(args)
    panes = snapshot["panes"]
    bell_processes = snapshot["bell_processes"]
    codex_thread_id = str(snapshot["CODEX_THREAD_ID"] or "").strip()
    runtime_ledger = snapshot["runtime_ledger"]
    formal_panes = actual_formal_panes(panes, formal_session_name)
    actual_targets = [str(pane.get("target", "")).strip() for pane in formal_panes if str(pane.get("target", "")).strip()]

    if not runtime_ledger:
        reasons.append("runtime ledger is missing")
        next_action.append("initialize the current-runtime ledger before dispatch")
        slot_bindings = {}
    else:
        ledger_reasons, ledger_warnings = evaluate_runtime_ledger_coherence(runtime_ledger)
        reasons.extend(ledger_reasons)
        warnings.extend(ledger_warnings)
        slot_bindings = coerce_slot_bindings(runtime_ledger.get("slot_bindings"))

    expected_pane_count = args.expected_pane_count
    if expected_pane_count is None and runtime_ledger:
        try:
            expected_pane_count = int(runtime_ledger.get("pane_count"))
        except (TypeError, ValueError):
            expected_pane_count = None
    if expected_pane_count is None:
        expected_pane_count = int(snapshot.get("expected_formal_pane_count", DEFAULT_FORMAL_PANE_COUNT))

    sessions = snapshot.get("sessions", [])
    matching_formal_sessions = [
        session for session in sessions if session.get("session_name") == formal_session_name
    ]
    if args.require_formal:
        if len(matching_formal_sessions) != 1:
            reasons.append(
                f"runtime requires exactly one attached formal session named {formal_session_name}"
            )
            next_action.append(f"retain exactly one attached {formal_session_name}")
        elif int(matching_formal_sessions[0].get("attached", 0)) <= 0:
            reasons.append(f"formal session {formal_session_name} is not attached")
            next_action.append(f"attach {formal_session_name} before running formal runtime")

    if len(formal_panes) != expected_pane_count:
        reasons.append(
            f"formal pane_count mismatch: expected {expected_pane_count}, actual {len(formal_panes)}"
        )
        next_action.append("rebuild the formal topology to the expected pane count")

    expected_targets = sorted(
        {
            str(binding.get("target", "")).strip()
            for binding in slot_bindings.values()
            if str(binding.get("target", "")).strip()
        }
    )
    if expected_targets and sorted(actual_targets) != expected_targets:
        reasons.append("formal targets do not match runtime ledger slot_bindings")
        next_action.append("align runtime ledger slot_bindings with the live formal targets")

    actual_titles_by_target = {
        str(pane.get("target", "")): str(pane.get("pane_title_normalized", "")).strip()
        for pane in formal_panes
    }
    actual_claude_by_target = {
        str(pane.get("target", "")): bool(pane.get("claude_entered"))
        for pane in formal_panes
    }

    invalid_titles = [
        f"{target}={title or '<empty>'}"
        for target, title in actual_titles_by_target.items()
        if title not in WHITE_ROLE_TITLES
    ]
    if invalid_titles:
        reasons.append("formal panes include non-whitelist titles: " + ", ".join(invalid_titles))
        next_action.append("rename all formal panes to whitelist role titles")

    non_claude_targets = [
        target for target, entered in actual_claude_by_target.items() if not entered
    ]
    if non_claude_targets:
        reasons.append("formal panes are not all in Claude runtime: " + ", ".join(non_claude_targets))
        next_action.append("prepare existing whitelist Claude scenes in every formal pane")

    for slot_name, binding in slot_bindings.items():
        target = str(binding.get("target", "")).strip()
        role = str(binding.get("role", "")).strip()
        if not target or target not in actual_titles_by_target:
            reasons.append(f"slot_bindings.{slot_name}.target does not exist in live formal panes")
            continue
        actual_title = actual_titles_by_target[target]
        if role and actual_title != role:
            reasons.append(
                f"slot_bindings.{slot_name} expects {role} at {target}, actual title is {actual_title}"
            )

    if not codex_thread_id:
        reasons.append("CODEX_THREAD_ID is missing")
        next_action.append("bind CODEX_THREAD_ID before formal runtime verification")
    elif runtime_ledger and not bool(runtime_ledger.get("codex_thread_bound")):
        reasons.append("runtime ledger codex_thread_bound is false")
        next_action.append("update runtime ledger after CODEX_THREAD_ID binding")

    watcher_commands = watcher_commands_for_targets(bell_processes, expected_targets or actual_targets)
    if args.require_bell and not watcher_commands:
        reasons.append("bell runtime is required but not armed for the formal targets")
        next_action.append("arm the tmux-skills watcher for the formal targets")

    monitor_binding = slot_bindings.get("monitor", {})
    monitor_target = str(monitor_binding.get("target", "")).strip()
    monitor_commands = watcher_commands_for_target(bell_processes, monitor_target)
    monitor_bell_bound = bool(monitor_commands)
    if args.require_bell and not monitor_target:
        reasons.append("runtime ledger slot_bindings.monitor.target is missing")
        next_action.append("bind the monitor slot to one concrete qa-bot target")
    elif args.require_bell and not monitor_bell_bound:
        reasons.append("watcher is not provably bound to slot_bindings.monitor.target")
        next_action.append("restart the watcher with the monitor target included")

    if reasons:
        status = "BLOCKED"
    elif snapshot["bootstrap_pane_count"] and not snapshot["formal_sessions"] and not args.allow_bootstrap:
        status = "BOOTSTRAP"
    else:
        status = "READY"

    if not next_action:
        next_action.append("runtime may accept formal work")

    return build_result(
        status,
        snapshot,
        reasons,
        warnings,
        next_action,
        monitor_bell_bound,
        watcher_commands,
        expected_targets or actual_targets,
    )


def build_result(
    status: str,
    snapshot: dict[str, Any],
    reasons: list[str],
    warnings: list[str],
    next_action: list[str],
    monitor_bell_bound: bool,
    watcher_commands: list[str],
    watcher_targets: list[str],
) -> dict[str, Any]:
    return {
        "runtime_status": status,
        "session_count": snapshot["session_count"],
        "pane_count": snapshot["pane_count"],
        "official_formal_pane_count": snapshot.get("official_formal_pane_count", 0),
        "formal_sessions": snapshot["formal_sessions"],
        "bootstrap_sessions": snapshot["bootstrap_sessions"],
        "CODEX_THREAD_ID": snapshot["CODEX_THREAD_ID"],
        "bell_armed": snapshot["bell_armed"],
        "monitor_bell_bound": monitor_bell_bound,
        "watcher_targets": watcher_targets,
        "watcher_commands": watcher_commands,
        "runtime_ledger_present": snapshot["runtime_ledger_present"],
        "runtime_ledger_path": snapshot["runtime_ledger_path"],
        "topology_fingerprint": snapshot["topology_fingerprint"],
        "reasons": reasons,
        "warnings": warnings,
        "next_action": next_action,
    }


def main() -> int:
    args = parse_args()
    result = evaluate(inspect_runtime(resolve_formal_session_name(args)), args)
    if args.pretty:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
