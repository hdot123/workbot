#!/usr/bin/env python3
"""Apply pane titles for tmux-skills without any Claude/scene validation."""

from __future__ import annotations

import argparse
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
        "#{pane_title}\t#{session_name}\t#{window_index}\t#{pane_index}",
    )
    if proc.returncode != 0:
        raise RuntimeError(
            proc.stderr.strip() or proc.stdout.strip() or "failed to read pane runtime signals"
        )
    parts = proc.stdout.rstrip("\n").split("\t")
    if len(parts) != 4:
        raise RuntimeError("failed to parse pane runtime signals")
    pane_title, session_name, window_index, pane_index = parts
    return {
        "pane_title": pane_title.strip(),
        "session_name": session_name.strip(),
        "window_index": window_index.strip(),
        "pane_index": pane_index.strip(),
    }


def initialize_entry(entry: PaneInitEntry) -> dict[str, Any]:
    target = str(entry["target"]).strip()
    expected_title = str(entry["pane_title"])
    actions = maybe_set_titles(target, entry.get("window_title"), expected_title)
    signals = read_runtime_signals(target)
    title_applied = signals["pane_title"] == expected_title
    result: dict[str, Any] = {
        "target": target,
        "slot": entry.get("slot"),
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
        pre_snapshot = inspect_runtime(formal_session)
        require_visible_formal_client(pre_snapshot, formal_session)
        entry_results = [initialize_entry(entry) for entry in entries]
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
