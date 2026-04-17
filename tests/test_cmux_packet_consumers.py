#!/usr/bin/env python3
"""Regression tests for Phase 1 P6 packet-first consumers."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


REPO_ROOT = Path(__file__).resolve().parent.parent
GLOBAL_CMUX_SCRIPTS = Path("/Users/busiji/.agents/skills/cmux/scripts")
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(GLOBAL_CMUX_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(GLOBAL_CMUX_SCRIPTS))

import cmux_finish_cycle  # noqa: E402
import watch_cmux_assignments  # noqa: E402
from workspace.tools.cmux_control_packet import EXAMPLE_PACKETS  # noqa: E402


def render_packet(packet: dict[str, object]) -> str:
    return f"{packet['marker']}{json.dumps(packet, ensure_ascii=False)}"


def test_watch_assignment_packet_helpers_prefer_control_packet() -> None:
    packet_text = render_packet(EXAMPLE_PACKETS["completed"])
    parsed, error = watch_cmux_assignments.try_extract_control_packet(packet_text)
    assert error == ""
    assert parsed is not None
    state, blocking, completed = watch_cmux_assignments.classify_control_packet_state(parsed)
    assert state == "running"
    assert blocking is False
    assert completed is True


def test_watch_assignment_packet_helpers_reject_prose_only_completion() -> None:
    parsed, error = watch_cmux_assignments.try_extract_control_packet("交付结论：已完成，测试通过。")
    assert parsed is None
    assert "prose-only completion output" in error


def test_finish_cycle_collect_outcome_uses_control_packet_path() -> None:
    assignment = SimpleNamespace(
        workspace_ref="workspace:1",
        pane_ref="pane:1",
        surface_ref="surface:1",
        screen_lines=None,
        tail_lines=None,
        assignment_id="doc-101",
        logical_target="doc-bot",
    )
    packet_text = render_packet(EXAMPLE_PACKETS["completed"])
    with patch.object(cmux_finish_cycle, "surface_snapshot", return_value={"ok": True}), patch.object(
        cmux_finish_cycle, "read_screen", return_value=packet_text
    ), patch.object(cmux_finish_cycle, "format_snapshot_meta", return_value="meta"):
        outcome = cmux_finish_cycle.collect_outcome(assignment)
    assert outcome["task_id"] == "DOC-101"
    assert outcome["status"] == "doc_synced"
    assert "delivery note" in outcome["summary"]


def test_finish_cycle_collect_outcome_blocks_prose_only_completion() -> None:
    assignment = SimpleNamespace(
        workspace_ref="workspace:1",
        pane_ref="pane:1",
        surface_ref="surface:1",
        screen_lines=None,
        tail_lines=None,
        assignment_id="doc-101",
        logical_target="doc-bot",
    )
    with patch.object(cmux_finish_cycle, "surface_snapshot", return_value={"ok": True}), patch.object(
        cmux_finish_cycle, "read_screen", return_value="交付结论：已完成，测试通过。"
    ), patch.object(cmux_finish_cycle, "format_snapshot_meta", return_value="meta"):
        try:
            cmux_finish_cycle.collect_outcome(assignment)
        except RuntimeError as exc:
            assert "prose-only completion output" in str(exc)
        else:
            raise AssertionError("expected prose-only completion output to be blocked")


if __name__ == "__main__":
    tests = [value for key, value in sorted(globals().items()) if key.startswith("test_")]
    passed = 0
    failed = 0
    for fn in tests:
        try:
            fn()
            passed += 1
            print(f"  PASS  {fn.__name__}")
        except Exception as exc:  # pragma: no cover - CLI helper
            failed += 1
            print(f"  FAIL  {fn.__name__}: {exc}")
    print(f"\n{passed} passed, {failed} failed out of {passed + failed}")
    sys.exit(1 if failed else 0)
