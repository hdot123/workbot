#!/usr/bin/env python3
"""Build or normalize the formal tmux runtime topology."""

from __future__ import annotations

# ==============================================================================
# ENFORCEMENT: This script is orchestrator_only - cannot be called directly
# ==============================================================================
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from runtime_enforcement import enforce_orchestrator_only
enforce_orchestrator_only("build_tmux_topology.py")
# ==============================================================================

import argparse
import json
import subprocess
from typing import Any

from runtime_ledger import DEFAULT_FORMAL_PANE_COUNT, DEFAULT_FORMAL_SESSION_NAME
from tmux_runtime_common import inspect_runtime


def run_tmux(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["tmux", *args], capture_output=True, text=True, check=False)


def require_visible_formal_client(snapshot: dict[str, Any], formal_session: str) -> None:
    current_client = snapshot.get("current_client") or {}
    if not snapshot.get("current_visible_formal_client"):
        reason = str(current_client.get("visibility_reason") or "not_visible_formal_client")
        raise SystemExit(
            "tmux-runtime positive flow requires current_visible_formal_client=true; "
            f"refusing to proceed from {reason}"
        )
    if not current_client.get("inside_tmux"):
        raise SystemExit("tmux-runtime positive flow requires current client to be inside tmux")
    if current_client.get("session_name") != formal_session:
        raise SystemExit(
            f"tmux-runtime positive flow requires current session={formal_session}; "
            f"got {current_client.get('session_name') or '<none>'}"
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build or normalize tmux pane topology for tmux-runtime.")
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
    proc = run_tmux(
        "list-panes",
        "-t",
        session_name,
        "-F",
        "#{session_name}:#{window_index}.#{pane_index}",
    )
    if proc.returncode != 0:
        raise SystemExit(proc.stderr.strip() or proc.stdout.strip() or "failed to list tmux pane targets")
    targets = [raw.strip() for raw in proc.stdout.splitlines() if raw.strip()]
    targets.sort(key=parse_target)
    return targets


def session_panes(session_name: str) -> list[dict[str, int | str]]:
    proc = run_tmux(
        "list-panes",
        "-t",
        session_name,
        "-F",
        "#{session_name}:#{window_index}.#{pane_index}\t#{pane_width}\t#{pane_height}",
    )
    if proc.returncode != 0:
        raise SystemExit(proc.stderr.strip() or proc.stdout.strip() or "failed to list tmux panes")

    panes: list[dict[str, int | str]] = []
    for raw in proc.stdout.splitlines():
        if not raw.strip():
            continue
        target, width_text, height_text = raw.split("\t")
        panes.append(
            {
                "target": target.strip(),
                "width": int(width_text),
                "height": int(height_text),
            }
        )
    panes.sort(key=lambda pane: parse_target(str(pane["target"])))
    return panes


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


def split_flag_for_pane(pane: dict[str, int | str]) -> str:
    width = int(pane["width"])
    height = int(pane["height"])
    return "-h" if width >= (height * 2) else "-v"


def preferred_split_step(
    session_name: str,
    target_pane_count: int,
    next_pane_count: int,
    available_targets: list[str],
) -> tuple[str, str] | None:
    plans: dict[int, dict[int, tuple[str, str]]] = {
        4: {
            2: (f"{session_name}:1.1", "-h"),
            3: (f"{session_name}:1.1", "-v"),
            4: (f"{session_name}:1.2", "-v"),
        },
        6: {
            2: (f"{session_name}:1.1", "-h"),
            3: (f"{session_name}:1.1", "-v"),
            4: (f"{session_name}:1.1", "-v"),
            5: (f"{session_name}:1.2", "-v"),
            6: (f"{session_name}:1.2", "-v"),
        },
    }
    preferred = plans.get(target_pane_count, {}).get(next_pane_count)
    if preferred is None:
        return None
    if preferred[0] not in available_targets:
        return None
    return preferred


def select_split_pane(panes: list[dict[str, int | str]]) -> dict[str, int | str]:
    if not panes:
        raise SystemExit("cannot split tmux topology without panes")
    return max(
        panes,
        key=lambda pane: (
            int(pane["width"]) * int(pane["height"]),
            int(pane["width"]),
            int(pane["height"]),
            tuple(-part for part in parse_target(str(pane["target"]))),
        ),
    )


def reconcile_topology(session_name: str, target_pane_count: int) -> dict[str, Any]:
    if target_pane_count < 1:
        raise SystemExit("target-pane-count must be >= 1")

    before_targets = session_targets(session_name)
    if not before_targets:
        raise SystemExit(f"session not found or has no panes: {session_name}")

    current_count = len(before_targets)
    actions: list[str] = []
    if target_pane_count > current_count:
        live_targets = sorted(before_targets, key=parse_target)
        for next_pane_count in range(current_count + 1, target_pane_count + 1):
            preferred = preferred_split_step(
                session_name,
                target_pane_count,
                next_pane_count,
                live_targets,
            )
            if preferred is None:
                candidate = select_split_pane(session_panes(session_name))
                anchor = str(candidate["target"])
                split_flag = split_flag_for_pane(candidate)
            else:
                anchor, split_flag = preferred
            proc = run_tmux("split-window", split_flag, "-t", anchor)
            if proc.returncode != 0:
                raise SystemExit(proc.stderr.strip() or proc.stdout.strip() or "failed to split tmux pane")
            actions.append(f"split-window:{split_flag}:{anchor}")
            live_targets = session_targets(session_name)
            live_targets.sort(key=parse_target)
    elif target_pane_count < current_count:
        removable = sorted(before_targets, key=parse_target, reverse=True)
        for target in removable[: current_count - target_pane_count]:
            proc = run_tmux("kill-pane", "-t", target)
            if proc.returncode != 0:
                raise SystemExit(proc.stderr.strip() or proc.stdout.strip() or "failed to kill tmux pane")
            actions.append(f"kill-pane:{target}")

    after_targets = session_targets(session_name)
    layout_action = apply_layout(session_name, len(after_targets))
    if layout_action:
        actions.append(layout_action)
        after_targets = session_targets(session_name)

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
    pre_snapshot = inspect_runtime(formal_session, include_bell_processes=False)
    require_visible_formal_client(pre_snapshot, formal_session)
    entry = reconcile_topology(formal_session, args.target_pane_count)
    entry["session_mode"] = "formal-single"

    snapshot = inspect_runtime(formal_session, include_bell_processes=False)
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
