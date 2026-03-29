#!/usr/bin/env python3
"""Build or normalize the formal tmux runtime topology."""

from __future__ import annotations

import argparse
import json
import subprocess
from typing import Any

from runtime_ledger import DEFAULT_FORMAL_PANE_COUNT, DEFAULT_FORMAL_SESSION_NAME
from tmux_runtime_common import inspect_runtime


def run_tmux(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["tmux", *args], capture_output=True, text=True, check=False)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build or normalize tmux pane topology for tmux-skills.")
    parser.add_argument(
        "--session",
        help="Target tmux session name. Defaults to --formal-session when omitted.",
    )
    parser.add_argument(
        "--formal-session",
        help="Formal runtime session name.",
    )
    parser.add_argument(
        "--target-pane-count",
        type=int,
        default=DEFAULT_FORMAL_PANE_COUNT,
        help=f"Desired pane_count for the formal runtime session, defaults to {DEFAULT_FORMAL_PANE_COUNT}.",
    )
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output.")
    return parser.parse_args()


def session_targets(session_name: str) -> list[str]:
    snapshot = inspect_runtime()
    return [pane["target"] for pane in snapshot["panes"] if pane["session_name"] == session_name]


def parse_target(target: str) -> tuple[int, int]:
    pane = target.split(":", 1)[1]
    window_index, pane_index = pane.split(".", 1)
    return int(window_index), int(pane_index)


def layout_policy_for(pane_count: int) -> tuple[str, str] | None:
    if pane_count <= 1:
        return None
    if pane_count == 4:
        return ("tiled", "2x2")
    if pane_count == 6:
        return ("tiled", "3x2")
    return ("tiled", "grid")


def apply_layout(session_name: str, pane_count: int) -> str | None:
    policy = layout_policy_for(pane_count)
    if policy is None:
        return None
    layout, grid = policy
    proc = run_tmux("select-layout", "-t", session_name, layout)
    if proc.returncode != 0:
        raise SystemExit(proc.stderr.strip() or proc.stdout.strip() or "failed to apply tmux layout")
    return f"select-layout:{layout}:{grid}"


def reconcile_topology(session_name: str, target_pane_count: int) -> dict[str, Any]:
    if target_pane_count < 1:
        raise SystemExit("target-pane-count must be >= 1")

    before_targets = session_targets(session_name)
    if not before_targets:
        raise SystemExit(f"session not found or has no panes: {session_name}")

    current_count = len(before_targets)
    actions: list[str] = []
    if target_pane_count > current_count:
        anchor = sorted(before_targets, key=parse_target)[0]
        for _ in range(target_pane_count - current_count):
            proc = run_tmux("split-window", "-t", anchor)
            if proc.returncode != 0:
                raise SystemExit(proc.stderr.strip() or proc.stdout.strip() or "failed to split tmux pane")
            actions.append("split-window")
    elif target_pane_count < current_count:
        removable = sorted(before_targets, key=parse_target, reverse=True)
        for target in removable[: current_count - target_pane_count]:
            proc = run_tmux("kill-pane", "-t", target)
            if proc.returncode != 0:
                raise SystemExit(proc.stderr.strip() or proc.stdout.strip() or "failed to kill tmux pane")
            actions.append(f"kill-pane:{target}")

    snapshot = inspect_runtime()
    after_targets = [pane["target"] for pane in snapshot["panes"] if pane["session_name"] == session_name]
    after_targets.sort(key=parse_target)
    layout_action = apply_layout(session_name, len(after_targets))
    if layout_action:
        actions.append(layout_action)

    snapshot = inspect_runtime()
    after_targets = [pane["target"] for pane in snapshot["panes"] if pane["session_name"] == session_name]
    after_targets.sort(key=parse_target)
    return {
        "session_name": session_name,
        "target_pane_count": target_pane_count,
        "pane_count_before": current_count,
        "pane_count_after": len(after_targets),
        "actions": actions,
        "pane_targets": after_targets,
        "ok": len(after_targets) == target_pane_count,
    }


def resolve_single_value(label: str, values: list[str | None], default: str) -> str:
    normalized = [value.strip() for value in values if value and value.strip()]
    unique = sorted(set(normalized))
    if not unique:
        return default
    if len(unique) > 1:
        raise SystemExit(f"conflicting {label} values: {', '.join(unique)}")
    return unique[0]


def main() -> int:
    args = parse_args()
    formal_session = resolve_single_value(
        "formal-session",
        [args.session, args.formal_session],
        default=DEFAULT_FORMAL_SESSION_NAME,
    )
    entry = reconcile_topology(formal_session, args.target_pane_count)
    entry["session_mode"] = "formal-single"

    snapshot = inspect_runtime()
    success = bool(entry["ok"])
    result: dict[str, Any] = {
        "phase": "topology",
        "formal": True,
        "entries": [entry],
        "topology_fingerprint": snapshot["topology_fingerprint"],
        "runtime_status": "INIT_IN_PROGRESS" if success else "BLOCKED",
        "session_name": entry["session_name"],
        "session_mode": entry["session_mode"],
        "target_pane_count": entry["target_pane_count"],
        "pane_count_before": entry["pane_count_before"],
        "pane_count_after": entry["pane_count_after"],
        "actions": entry["actions"],
        "pane_targets": entry["pane_targets"],
    }

    if args.pretty:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
