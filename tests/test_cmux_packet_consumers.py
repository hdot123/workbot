#!/usr/bin/env python3
"""Regression tests for Phase 1 P6 packet-first consumers."""

from __future__ import annotations

import json
import sys
import tempfile
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
    consumer_entry = {
        "assignment_id": "doc-101",
        "state_source": "control_packet",
        "control_packet": dict(EXAMPLE_PACKETS["completed"]),
    }
    with patch.object(cmux_finish_cycle, "read_screen") as mocked_read_screen:
        outcome = cmux_finish_cycle.collect_outcome(
            assignment,
            consumer_entry,
            allow_forensic_read_pane=False,
        )
    mocked_read_screen.assert_not_called()
    assert outcome["task_id"] == "DOC-101"
    assert outcome["status"] == "doc_synced"
    assert "delivery note" in outcome["summary"]
    assert outcome["source"] == "control_packet"
    assert outcome["artifact_path"].endswith("doc-bot-summary.json")


def test_finish_cycle_collect_outcome_requires_packet_without_forensic() -> None:
    assignment = SimpleNamespace(
        workspace_ref="workspace:1",
        pane_ref="pane:1",
        surface_ref="surface:1",
        screen_lines=None,
        tail_lines=None,
        assignment_id="doc-101",
        logical_target="doc-bot",
    )
    with patch.object(cmux_finish_cycle, "read_screen") as mocked_read_screen:
        try:
            cmux_finish_cycle.collect_outcome(
                assignment,
                consumer_entry=None,
                allow_forensic_read_pane=False,
            )
        except RuntimeError as exc:
            assert "missing control packet in consumer state" in str(exc)
        else:
            raise AssertionError("expected missing consumer control packet to be blocked")
    mocked_read_screen.assert_not_called()


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
            cmux_finish_cycle.collect_outcome(
                assignment,
                consumer_entry=None,
                allow_forensic_read_pane=True,
            )
        except RuntimeError as exc:
            assert "prose-only completion output" in str(exc)
        else:
            raise AssertionError("expected prose-only completion output to be blocked")


def test_watch_consumer_state_file_records_control_packet() -> None:
    assignment = watch_cmux_assignments.WatchAssignment(
        logical_target="doc-bot",
        workspace_ref="workspace:1",
        pane_ref="pane:1",
        surface_ref="surface:1",
        assignment_id="doc-101",
        bot_name="doc-bot",
        title="Doc delivery",
        goal="sync docs",
        task_kind="assignment",
        audit_round_1_owner="rea-bot",
        audit_round_1_status="passed",
        audit_round_2_owner="codex",
        audit_round_2_status="passed",
        status="ACTIVE",
        allow_intervene=True,
    )
    runtime_state = watch_cmux_assignments.RuntimeState(assignment_id="doc-101")
    runtime_state.last_state = "running"
    runtime_state.last_state_source = "control_packet"
    runtime_state.last_state_updated_at = "2026-04-18T03:00:00+0800"
    runtime_state.last_control_packet = dict(EXAMPLE_PACKETS["completed"])
    runtime_state.last_completed = True

    with tempfile.TemporaryDirectory() as temp_dir:
        target = Path(temp_dir) / "consumer-state.json"
        watch_cmux_assignments.write_consumer_state_file(
            target,
            assignment_file=str(Path(temp_dir) / "cmux-assignment.json"),
            selected_workspace_ref="workspace:1",
            assignments=[assignment],
            state_by_target={"doc-bot": runtime_state},
        )
        payload = json.loads(target.read_text(encoding="utf-8"))
        assert payload["schema_version"] == "wb-cmux-consumer-state-v1"
        assert payload["selected_workspace_ref"] == "workspace:1"
        entry = payload["assignments"]["doc-bot"]
        assert entry["state_source"] == "control_packet"
        assert entry["completed"] is True
        assert entry["control_packet"]["task_id"] == "DOC-101"


def test_watch_process_assignment_blocks_non_packet_completion_without_forensic() -> None:
    assignment = watch_cmux_assignments.WatchAssignment(
        logical_target="doc-bot",
        workspace_ref="workspace:1",
        pane_ref="pane:1",
        surface_ref="surface:1",
        assignment_id="doc-101",
        bot_name="doc-bot",
        title="Doc delivery",
        goal="sync docs",
        task_kind="assignment",
        audit_round_1_owner="rea-bot",
        audit_round_1_status="passed",
        audit_round_2_owner="codex",
        audit_round_2_status="passed",
        status="ACTIVE",
        allow_intervene=False,
    )
    state = watch_cmux_assignments.RuntimeState(assignment_id="doc-101")
    state.task_dispatched = True
    state.observed_running = True
    state.observed_session_id = "s-1"
    args = SimpleNamespace(
        screen_lines=120,
        tail_lines=20,
        same_hash_threshold=2,
        blocked_remind_polls=2,
        completion_regex=None,
        dispatch_initial_task=False,
        auto_approve=False,
        auto_continue=False,
        action_cooldown=0.0,
        approval_stuck_polls=3,
        sop_followup_delay=0.0,
        stable_screen_refresh_polls=3,
        native_notify=False,
        forensic_read_pane=False,
    )
    hook_state = {
        "session_start_count": 0,
        "prompt_submit_count": 1,
        "stop_count": 0,
        "notification_count": 0,
        "last_session_id": "s-1",
    }
    with patch.object(watch_cmux_assignments, "load_active_surface_hook_state", return_value=hook_state), patch.object(
        watch_cmux_assignments, "surface_snapshot", return_value={"ok": True}
    ), patch.object(
        watch_cmux_assignments, "read_screen", return_value="done"
    ), patch.object(
        watch_cmux_assignments, "format_snapshot_meta", return_value="meta"
    ), patch.object(
        watch_cmux_assignments, "classify_assignment_state", return_value=("waiting_input", False)
    ), patch.object(
        watch_cmux_assignments, "try_extract_control_packet", return_value=(None, "")
    ), patch.object(
        watch_cmux_assignments, "is_assignment_complete", return_value=True
    ):
        completed = watch_cmux_assignments.process_assignment(
            assignment,
            state,
            args,
            fallback_task_text=None,
            hook_state_file=Path("/tmp/hook-state.json"),
        )
    assert completed is False
    assert state.last_completed is False
    assert state.last_state_source == "control_packet_missing"


def test_watch_process_assignment_allows_forensic_tail_completion_when_enabled() -> None:
    assignment = watch_cmux_assignments.WatchAssignment(
        logical_target="doc-bot",
        workspace_ref="workspace:1",
        pane_ref="pane:1",
        surface_ref="surface:1",
        assignment_id="doc-101",
        bot_name="doc-bot",
        title="Doc delivery",
        goal="sync docs",
        task_kind="assignment",
        audit_round_1_owner="rea-bot",
        audit_round_1_status="passed",
        audit_round_2_owner="codex",
        audit_round_2_status="passed",
        status="ACTIVE",
        allow_intervene=False,
    )
    state = watch_cmux_assignments.RuntimeState(assignment_id="doc-101")
    state.task_dispatched = True
    state.observed_running = True
    state.observed_session_id = "s-1"
    args = SimpleNamespace(
        screen_lines=120,
        tail_lines=20,
        same_hash_threshold=2,
        blocked_remind_polls=2,
        completion_regex=None,
        dispatch_initial_task=False,
        auto_approve=False,
        auto_continue=False,
        action_cooldown=0.0,
        approval_stuck_polls=3,
        sop_followup_delay=0.0,
        stable_screen_refresh_polls=3,
        native_notify=False,
        forensic_read_pane=True,
    )
    hook_state = {
        "session_start_count": 0,
        "prompt_submit_count": 1,
        "stop_count": 0,
        "notification_count": 0,
        "last_session_id": "s-1",
    }
    with patch.object(watch_cmux_assignments, "load_active_surface_hook_state", return_value=hook_state), patch.object(
        watch_cmux_assignments, "surface_snapshot", return_value={"ok": True}
    ), patch.object(
        watch_cmux_assignments, "read_screen", return_value="done"
    ), patch.object(
        watch_cmux_assignments, "format_snapshot_meta", return_value="meta"
    ), patch.object(
        watch_cmux_assignments, "classify_assignment_state", return_value=("waiting_input", False)
    ), patch.object(
        watch_cmux_assignments, "try_extract_control_packet", return_value=(None, "")
    ), patch.object(
        watch_cmux_assignments, "is_assignment_complete", return_value=True
    ):
        completed = watch_cmux_assignments.process_assignment(
            assignment,
            state,
            args,
            fallback_task_text=None,
            hook_state_file=Path("/tmp/hook-state.json"),
        )
    assert completed is True
    assert state.last_completed is True
    assert state.last_state_source == "raw_pane_tail"


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
