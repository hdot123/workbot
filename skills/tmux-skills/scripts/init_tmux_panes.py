#!/usr/bin/env python3
"""Runtime-only pane labeling and existing-scene validation for tmux-skills."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any, TypedDict

from runtime_ledger import (
    DEFAULT_FORMAL_PANE_COUNT,
    WHITE_ROLE_TITLES,
    apply_slot_binding_updates,
    load_current_runtime_ledger,
)
from tmux_runtime_common import inspect_runtime
from verify_pane_identity import read_pane_runtime_signals, session_name_from_target


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


def maybe_set_titles(target: str, window_title: str | None, pane_title: str | None) -> list[str]:
    actions: list[str] = []
    if pane_title:
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


def capture_pane(target: str, lines: int = 120) -> str:
    proc = run_tmux("capture-pane", "-p", "-S", f"-{lines}", "-t", target)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or proc.stdout.strip() or "failed to capture pane")
    return proc.stdout


def build_visible_markers(role: str) -> list[str]:
    markers = [
        f"@{role}",
        role,
        f"已切换到 {role}",
        f"已切换到 {role}。",
        f"@{role} ·",
        f" {role} ·",
    ]
    return list(dict.fromkeys(marker for marker in markers if marker.strip()))


def validate_tmux_target(target: str) -> None:
    if ":" not in target or "." not in target.split(":", 1)[1]:
        raise ValueError(f"target must include session/window/pane: {target}")


def ensure_single_formal_runtime(expected_session_name: str | None) -> None:
    snapshot = inspect_runtime()
    formal_sessions = [name for name in snapshot.get("formal_sessions", []) if str(name).strip()]
    unique_formal = sorted(set(formal_sessions))
    if len(unique_formal) > 1:
        raise ValueError(
            "runtime has multiple formal sessions; pane validation requires exactly one: "
            + ", ".join(unique_formal)
        )
    if expected_session_name and unique_formal and expected_session_name not in unique_formal:
        raise ValueError(
            "target session does not match the current formal runtime session: "
            f"target={expected_session_name}, runtime={unique_formal[0]}"
        )


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
        if not target or not pane_title:
            raise ValueError("batch entry must include both target and pane_title")
        entry: PaneInitEntry = {
            "target": target,
            "slot": normalize_plan_value(item.get("slot")),
            "window_title": normalize_plan_value(item.get("window_title")),
            "pane_title": pane_title,
        }
        entries.append(entry)
    if not entries:
        raise ValueError("batch plan must contain at least one entry")
    return entries


def validate_plan_entries(entries: list[PaneInitEntry]) -> None:
    seen_targets: set[str] = set()
    session_names: set[str] = set()
    ledger = load_current_runtime_ledger()
    max_formal_panes = DEFAULT_FORMAL_PANE_COUNT
    try:
        ledger_pane_count = int(ledger.get("pane_count"))
        if ledger_pane_count > 0:
            max_formal_panes = ledger_pane_count
    except (TypeError, ValueError, AttributeError):
        pass
    if len(entries) > max_formal_panes:
        raise ValueError(
            f"batch plan exceeds formal runtime pane count: {len(entries)}>{max_formal_panes}"
        )
    for index, entry in enumerate(entries, start=1):
        target = entry["target"]
        pane_title = str(entry["pane_title"]).strip()
        validate_tmux_target(target)
        if pane_title not in WHITE_ROLE_TITLES:
            raise ValueError(
                f"batch entry {index} pane_title must be one of {', '.join(WHITE_ROLE_TITLES)}"
            )
        session_names.add(session_name_from_target(target))
        if target in seen_targets:
            raise ValueError(f"batch entry {index} duplicates target: {target}")
        seen_targets.add(target)
    if len(session_names) > 1:
        raise ValueError(
            "all pane targets must belong to one formal session; found: "
            + ", ".join(sorted(session_names))
        )
    only_session = next(iter(session_names)) if session_names else None
    ensure_single_formal_runtime(only_session)


def verify_existing_scene(target: str, expected_role: str) -> dict[str, Any]:
    runtime_signals = read_pane_runtime_signals(target)
    pane_output = capture_pane(target, 120)
    matched_visible_markers = [
        marker for marker in build_visible_markers(expected_role) if marker in pane_output
    ]
    title_ok = runtime_signals["pane_title_normalized"] == expected_role
    claude_running = bool(runtime_signals["claude_entered"])
    scene_visible = bool(matched_visible_markers)
    reasons: list[str] = []
    if not title_ok:
        reasons.append(
            f"pane title does not match expected role: expected={expected_role}, "
            f"actual={runtime_signals['pane_title_normalized'] or '<empty>'}"
        )
    if not claude_running:
        reasons.append(
            "pane is not running Claude yet (expected node/claude runtime, "
            f"actual={runtime_signals['pane_current_command'] or '<empty>'})"
        )
    if not scene_visible:
        reasons.append("missing visible role markers in pane output")
    return {
        "title_ok": title_ok,
        "claude_running": claude_running,
        "scene_visible": scene_visible,
        "scene_verified": title_ok and claude_running and scene_visible,
        "pane_current_command": runtime_signals["pane_current_command"],
        "pane_title": runtime_signals["pane_title"],
        "matched_visible_markers": matched_visible_markers,
        "verification_reasons": reasons,
    }


def initialize_entry(entry: PaneInitEntry) -> dict[str, Any]:
    target = entry["target"]
    expected_role = str(entry["pane_title"]).strip()
    actions = maybe_set_titles(target, entry.get("window_title"), expected_role)
    verification = verify_existing_scene(target, expected_role)
    result: dict[str, Any] = {
        "target": target,
        "expected_role": expected_role,
        "slot": entry.get("slot"),
        "actions": actions,
        "title_ok": verification["title_ok"],
        "claude_running": verification["claude_running"],
        "scene_visible": verification["scene_visible"],
        "scene_verified": verification["scene_verified"],
        "pane_current_command": verification["pane_current_command"],
        "pane_title": verification["pane_title"],
        "matched_visible_markers": verification["matched_visible_markers"],
        "verification_reasons": verification["verification_reasons"],
        "runtime_status": "INIT_IN_PROGRESS" if verification["scene_verified"] else "BLOCKED",
    }
    if not verification["scene_verified"]:
        result["error"] = "; ".join(verification["verification_reasons"]) or "pane scene verification failed"
    return result


def collect_slot_bindings(entry_results: list[dict[str, Any]]) -> dict[str, dict[str, str]]:
    bindings: dict[str, dict[str, str]] = {}
    for result in entry_results:
        slot_name = result.get("slot")
        if not result.get("scene_verified") or not slot_name:
            continue
        bindings[str(slot_name)] = {
            "role": str(result["expected_role"]),
            "target": str(result["target"]),
        }
    return bindings


def maybe_apply_slot_bindings(bindings: dict[str, dict[str, str]]) -> tuple[bool, str | None]:
    if not bindings:
        return False, None
    if not load_current_runtime_ledger():
        return False, None
    try:
        apply_slot_binding_updates(bindings, allow_reassign=False)
    except Exception as exc:  # pragma: no cover - defensive path
        return False, str(exc)
    return True, None


def build_plan_entries(args: argparse.Namespace) -> tuple[list[PaneInitEntry], bool]:
    if args.batch_file:
        return parse_batch_plan(args.batch_file), True
    entry: PaneInitEntry = {
        "target": args.target,
        "slot": normalize_plan_value(args.slot),
        "window_title": normalize_plan_value(args.window_title),
        "pane_title": normalize_plan_value(args.pane_title),
    }
    if not entry["target"] or not entry["pane_title"]:
        raise ValueError("--target and --pane-title are required when --batch-file is not set")
    return [entry], False


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Label one or more tmux panes and verify existing whitelist runtime scenes."
    )
    parser.add_argument("--target", help="tmux target such as session:window.pane")
    parser.add_argument("--slot", help="Optional slot name to record in the runtime ledger.")
    parser.add_argument("--window-title", help="Optional normalized window title.")
    parser.add_argument("--pane-title", help="Expected whitelist pane title.")
    parser.add_argument("--batch-file", type=Path, help="Path to a JSON array of pane validation entries.")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output.")
    args = parser.parse_args()
    if args.batch_file:
        single_fields = (args.target, args.slot, args.window_title, args.pane_title)
        if any(field is not None for field in single_fields):
            parser.error("single-pane options cannot be combined with --batch-file")
    else:
        if not args.target or not args.pane_title:
            parser.error("--target and --pane-title are required when --batch-file is not set")
    return args


def main() -> int:
    args = parse_args()
    entries, batch_mode = build_plan_entries(args)
    validate_plan_entries(entries)
    entry_results: list[dict[str, Any]] = []
    for entry in entries:
        try:
            entry_results.append(initialize_entry(entry))
        except Exception as exc:  # pragma: no cover - defensive path
            entry_results.append(
                {
                    "target": entry["target"],
                    "expected_role": entry["pane_title"],
                    "slot": entry.get("slot"),
                    "actions": [],
                    "scene_verified": False,
                    "runtime_status": "BLOCKED",
                    "error": str(exc),
                }
            )

    slot_bindings = collect_slot_bindings(entry_results)
    slot_bindings_applied = False
    slot_binding_error: str | None = None
    all_entries_verified = all(result.get("scene_verified") for result in entry_results)
    if all_entries_verified:
        slot_bindings_applied, slot_binding_error = maybe_apply_slot_bindings(slot_bindings)
        if slot_binding_error:
            for result in entry_results:
                result["runtime_status"] = "BLOCKED"
                result["error"] = slot_binding_error

    overall_verified = all(result.get("scene_verified") for result in entry_results) and slot_binding_error is None
    overall_status = "INIT_IN_PROGRESS" if overall_verified else "BLOCKED"
    formal_session = session_name_from_target(entry_results[0]["target"]) if entry_results else ""

    result: dict[str, Any] = {
        "phase": "pane-runtime-validation",
        "runtime_status": overall_status,
        "verified": overall_verified,
        "formal_session_name": formal_session,
        "formal_pane_count": len(entries),
        "slot_bindings": slot_bindings,
        "slot_bindings_applied": slot_bindings_applied,
        "slot_binding_error": slot_binding_error,
        "entries": entry_results,
    }

    if not batch_mode:
        first = entry_results[0]
        result.update(
            {
                "target": first["target"],
                "expected_role": first["expected_role"],
                "pane_title": first.get("pane_title"),
                "scene_verified": first.get("scene_verified"),
                "verification_reasons": first.get("verification_reasons"),
            }
        )

    if args.pretty:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(json.dumps(result, ensure_ascii=False))
    return 0 if overall_verified else 1


if __name__ == "__main__":
    raise SystemExit(main())
