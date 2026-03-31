#!/usr/bin/env python3
"""Apply pane titles for tmux-skills without any Claude/scene validation."""

from __future__ import annotations

# ==============================================================================
# ENFORCEMENT: This script is orchestrator_only - cannot be called directly
# ==============================================================================
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from runtime_enforcement import enforce_orchestrator_only
enforce_orchestrator_only("init_tmux_panes.py")
# ==============================================================================

import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any, TypedDict

from runtime_ledger import apply_slot_binding_updates, load_current_runtime_ledger
from tmux_runtime_common import inspect_runtime


class PaneInitEntry(TypedDict, total=False):
    target: str
    slot: str | None
    window_title: str | None
    pane_title: str


def run_tmux(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["tmux", *args], capture_output=True, text=True, check=False)


def normalize_plan_value(value: Any | None) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None


def validate_tmux_target(target: str) -> None:
    if ":" not in target or "." not in target.split(":", 1)[1]:
        raise ValueError(f"target must include session/window/pane: {target}")


def parse_batch_plan(path: Path) -> list[PaneInitEntry]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError("batch plan must be a JSON array of entries")
    entries: list[PaneInitEntry] = []
    for index, item in enumerate(raw, start=1):
        if not isinstance(item, dict):
            raise ValueError(f"batch entry {index} must be an object")
        target = normalize_plan_value(item.get("target"))
        pane_title = normalize_plan_value(item.get("pane_title"))
        if not target or pane_title is None:
            raise ValueError("batch entry must include both target and pane_title")
        entries.append(
            {
                "target": target,
                "slot": normalize_plan_value(item.get("slot")),
                "window_title": normalize_plan_value(item.get("window_title")),
                "pane_title": pane_title,
            }
        )
    if not entries:
        raise ValueError("batch plan must contain at least one entry")
    return entries


def build_plan_entries(args: argparse.Namespace) -> tuple[list[PaneInitEntry], bool]:
    if args.batch_file:
        return parse_batch_plan(args.batch_file), True
    target = normalize_plan_value(args.target)
    pane_title = normalize_plan_value(args.pane_title)
    if not target or pane_title is None:
        raise ValueError("--target and --pane-title are required when --batch-file is not set")
    return [
        {
            "target": target,
            "slot": normalize_plan_value(args.slot),
            "window_title": normalize_plan_value(args.window_title),
            "pane_title": pane_title,
        }
    ], False


def validate_plan_entries(entries: list[PaneInitEntry]) -> None:
    seen_targets: set[str] = set()
    session_names: set[str] = set()
    for index, entry in enumerate(entries, start=1):
        target = str(entry["target"]).strip()
        pane_title = str(entry["pane_title"])
        validate_tmux_target(target)
        if target in seen_targets:
            raise ValueError(f"batch entry {index} duplicates target: {target}")
        if not pane_title:
            raise ValueError(f"batch entry {index} pane_title cannot be empty")
        seen_targets.add(target)
        session_names.add(target.partition(":")[0].strip())
    if len(session_names) > 1:
        raise ValueError(
            "all pane targets must belong to one formal session; found: "
            + ", ".join(sorted(session_names))
        )


def maybe_set_titles(target: str, window_title: str | None, pane_title: str | None) -> list[str]:
    actions: list[str] = []
    if pane_title is not None:
        proc = run_tmux("select-pane", "-t", target, "-T", pane_title)
        if proc.returncode != 0:
            raise RuntimeError(proc.stderr.strip() or proc.stdout.strip() or "failed to set pane title")
        actions.append(f"pane_title={pane_title}")
    if window_title:
        session, rest = target.split(":", 1)
        window_index = rest.split(".", 1)[0]
        proc = run_tmux("rename-window", "-t", f"{session}:{window_index}", window_title)
        if proc.returncode != 0:
            raise RuntimeError(proc.stderr.strip() or proc.stdout.strip() or "failed to set window title")
        actions.append(f"window_title={window_title}")
    return actions


def read_runtime_signals(target: str) -> dict[str, str]:
    proc = run_tmux(
        "display-message",
        "-p",
        "-t",
        target,
        "#{pane_title}\t#{session_name}\t#{window_index}\t#{pane_index}\t#{window_name}",
    )
    if proc.returncode != 0:
        raise RuntimeError(
            proc.stderr.strip() or proc.stdout.strip() or "failed to read pane runtime signals"
        )
    parts = proc.stdout.rstrip("\n").split("\t")
    if len(parts) != 5:
        raise RuntimeError("failed to parse pane runtime signals")
    pane_title, session_name, window_index, pane_index, window_name = parts
    return {
        "pane_title": pane_title.strip(),
        "session_name": session_name.strip(),
        "window_index": window_index.strip(),
        "pane_index": pane_index.strip(),
        "window_name": window_name.strip(),
    }


def read_runtime_signals_for_targets(targets: list[str]) -> dict[str, dict[str, str]]:
    if not targets:
        return {}
    proc = run_tmux(
        "list-panes",
        "-a",
        "-F",
        "#{session_name}:#{window_index}.#{pane_index}\t#{pane_title}\t#{session_name}\t#{window_index}\t#{pane_index}\t#{window_name}",
    )
    if proc.returncode != 0:
        raise RuntimeError(
            proc.stderr.strip() or proc.stdout.strip() or "failed to read pane runtime signals"
        )
    wanted = set(targets)
    signals_by_target: dict[str, dict[str, str]] = {}
    for raw in proc.stdout.splitlines():
        if not raw.strip():
            continue
        target, pane_title, session_name, window_index, pane_index, window_name = raw.rstrip("\n").split("\t")
        target = target.strip()
        if target not in wanted:
            continue
        signals_by_target[target] = {
            "pane_title": pane_title.strip(),
            "session_name": session_name.strip(),
            "window_index": window_index.strip(),
            "pane_index": pane_index.strip(),
            "window_name": window_name.strip(),
        }
    return signals_by_target


def build_desired_state_rows(entries: list[PaneInitEntry]) -> list[tuple[str, str, str]]:
    rows: list[tuple[str, str, str]] = []
    for entry in entries:
        rows.append(
            (
                str(entry["target"]).strip(),
                str(entry["pane_title"]).strip(),
                str(entry.get("window_title") or "").strip(),
            )
        )
    return sorted(rows)


def build_live_state_rows(entries: list[PaneInitEntry], signals_by_target: dict[str, dict[str, str]]) -> list[tuple[str, str, str]]:
    rows: list[tuple[str, str, str]] = []
    for entry in entries:
        target = str(entry["target"]).strip()
        signals = signals_by_target.get(target, {})
        rows.append(
            (
                target,
                str(signals.get("pane_title", "")).strip(),
                str(signals.get("window_name", "")).strip(),
            )
        )
    return sorted(rows)


def compute_state_hash(rows: list[tuple[str, str, str]]) -> str:
    return hashlib.sha1(json.dumps(rows, ensure_ascii=False).encode("utf-8")).hexdigest()


def compute_topology_fingerprint(formal_session: str) -> str:
    session_proc = run_tmux(
        "display-message",
        "-p",
        "-t",
        formal_session,
        "#{session_name}\t#{session_attached}\t#{session_windows}",
    )
    if session_proc.returncode != 0:
        raise RuntimeError(
            session_proc.stderr.strip() or session_proc.stdout.strip() or "failed to read tmux session fingerprint state"
        )
    session_line = session_proc.stdout.strip()
    if not session_line:
        raise RuntimeError("failed to read tmux session fingerprint state")
    session_name, attached_text, windows_text = session_line.split("\t")

    panes_proc = run_tmux(
        "list-panes",
        "-t",
        formal_session,
        "-F",
        "#{session_name}:#{window_index}.#{pane_index}\t#{pane_title}\t#{window_name}\t#{pane_current_command}",
    )
    if panes_proc.returncode != 0:
        raise RuntimeError(
            panes_proc.stderr.strip() or panes_proc.stdout.strip() or "failed to read tmux pane fingerprint state"
        )
    pane_rows: list[tuple[str, str, str, str]] = []
    for raw in panes_proc.stdout.splitlines():
        if not raw.strip():
            continue
        target, pane_title, window_name, current_command = raw.rstrip("\n").split("\t")
        pane_rows.append((target.strip(), pane_title.strip(), window_name.strip(), current_command.strip()))
    payload = {
        "official_session": {
            "session_name": session_name.strip(),
            "attached": int(attached_text or 0),
            "windows": int(windows_text or 0),
        },
        "panes": sorted(pane_rows),
    }
    return hashlib.sha1(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()


def apply_entry_title(
    entry: PaneInitEntry,
    live_signals: dict[str, str] | None = None,
) -> tuple[str, str, list[str], str | None]:
    target = str(entry["target"]).strip()
    expected_title = str(entry["pane_title"])
    desired_window_title = str(entry.get("window_title") or "").strip() or None
    current_title = str((live_signals or {}).get("pane_title", "")).strip()
    current_window_title = str((live_signals or {}).get("window_name", "")).strip()
    pane_title_to_apply = expected_title if current_title != expected_title else None
    window_title_to_apply = desired_window_title if desired_window_title and current_window_title != desired_window_title else None
    actions = maybe_set_titles(target, window_title_to_apply, pane_title_to_apply)
    if not actions:
        actions.append("noop:state_hash_match")
    return target, expected_title, actions, str(entry.get("slot") or "").strip() or None


def initialize_entry(
    target: str,
    expected_title: str,
    actions: list[str],
    slot: str | None,
    signals: dict[str, str] | None,
) -> dict[str, Any]:
    if signals is None:
        signals = read_runtime_signals(target)
    title_applied = signals["pane_title"] == expected_title
    result: dict[str, Any] = {
        "target": target,
        "slot": slot,
        "pane_title": expected_title,
        "actual_pane_title": signals["pane_title"],
        "session_name": signals["session_name"],
        "window_index": signals["window_index"],
        "pane_index": signals["pane_index"],
        "actions": actions,
        "title_applied": title_applied,
        "runtime_status": "INIT_IN_PROGRESS" if title_applied else "BLOCKED",
    }
    if not title_applied:
        result["error"] = (
            f"pane title does not match requested title: expected={expected_title}, "
            f"actual={signals['pane_title'] or '<empty>'}"
        )
    return result


def collect_slot_bindings(entry_results: list[dict[str, Any]]) -> dict[str, dict[str, str]]:
    bindings: dict[str, dict[str, str]] = {}
    for result in entry_results:
        slot_name = result.get("slot")
        if not slot_name or not result.get("title_applied"):
            continue
        bindings[str(slot_name)] = {
            "pane_title": str(result["pane_title"]),
            "target": str(result["target"]),
        }
    return bindings


def maybe_apply_slot_bindings(bindings: dict[str, dict[str, str]]) -> tuple[bool, str | None]:
    if not bindings or not load_current_runtime_ledger():
        return False, None
    try:
        apply_slot_binding_updates(bindings, allow_reassign=False)
    except Exception as exc:  # pragma: no cover
        return False, str(exc)
    return True, None


def require_visible_formal_client(snapshot: dict[str, Any], formal_session: str) -> None:
    current_client = snapshot.get("current_client") or {}
    if not snapshot.get("current_visible_formal_client"):
        reason = str(current_client.get("visibility_reason") or "not_visible_formal_client")
        raise RuntimeError(
            "tmux-skills positive flow requires current_visible_formal_client=true; "
            f"refusing to proceed from {reason}"
        )
    if not current_client.get("inside_tmux"):
        raise RuntimeError("tmux-skills positive flow requires current client to be inside tmux")
    if current_client.get("session_name") != formal_session:
        raise RuntimeError(
            f"tmux-skills positive flow requires current session={formal_session}; "
            f"got {current_client.get('session_name') or '<none>'}"
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Label one or more tmux panes without any Claude or scene validation."
    )
    parser.add_argument("--target", help="tmux target such as session:window.pane")
    parser.add_argument("--slot", help="Optional slot name to record in the runtime ledger.")
    parser.add_argument("--window-title", help="Optional window title to apply.")
    parser.add_argument("--pane-title", help="Pane title to apply.")
    parser.add_argument("--batch-file", type=Path, help="JSON array describing multiple pane title operations.")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        entries, batched = build_plan_entries(args)
        validate_plan_entries(entries)
        formal_session = str(entries[0]["target"]).split(":", 1)[0]
        pre_snapshot = inspect_runtime(formal_session, include_bell_processes=False)
        require_visible_formal_client(pre_snapshot, formal_session)
        live_signals_before = read_runtime_signals_for_targets([str(entry["target"]).strip() for entry in entries])
        desired_state_hash = compute_state_hash(build_desired_state_rows(entries))
        live_state_hash_before = compute_state_hash(build_live_state_rows(entries, live_signals_before))
        prepared_entries = [
            apply_entry_title(entry, live_signals_before.get(str(entry["target"]).strip()))
            for entry in entries
        ]
        target_signals = read_runtime_signals_for_targets([item[0] for item in prepared_entries])
        entry_results = [
            initialize_entry(target, expected_title, actions, slot, target_signals.get(target))
            for target, expected_title, actions, slot in prepared_entries
        ]
    except (RuntimeError, ValueError) as exc:
        result = {
            "verified": False,
            "runtime_status": "BLOCKED",
            "error": str(exc),
            "entries": [],
        }
        print(json.dumps(result, ensure_ascii=False, indent=2 if args.pretty else None))
        return 1

    slot_bindings = collect_slot_bindings(entry_results)
    slot_bindings_applied, slot_binding_error = maybe_apply_slot_bindings(slot_bindings)
    verified = all(bool(result.get("title_applied")) for result in entry_results)
    result: dict[str, Any] = {
        "verified": verified and slot_binding_error is None,
        "runtime_status": "INIT_IN_PROGRESS" if verified and slot_binding_error is None else "BLOCKED",
        "batch_mode": batched,
        "formal_pane_count": len(entries),
        "entries": entry_results,
        "slot_bindings": slot_bindings,
        "slot_bindings_applied": slot_bindings_applied,
        "topology_fingerprint": compute_topology_fingerprint(formal_session) if verified else "",
        "desired_state_hash": desired_state_hash if 'desired_state_hash' in locals() else "",
        "live_state_hash_before": live_state_hash_before if 'live_state_hash_before' in locals() else "",
        "state_hash_match": (
            desired_state_hash == live_state_hash_before
            if 'desired_state_hash' in locals() and 'live_state_hash_before' in locals()
            else False
        ),
    }
    if slot_binding_error:
        result["slot_binding_error"] = slot_binding_error
    if not result["verified"]:
        result["error"] = "one or more pane title operations failed"
    if args.pretty:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(json.dumps(result, ensure_ascii=False))
    return 0 if result["verified"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
