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


def make_finish_cycle_assignment(
    *,
    assignment_id: str = "doc-101",
    logical_target: str = "doc-bot",
    title: str = "Doc delivery",
    goal: str = "sync docs",
) -> SimpleNamespace:
    return SimpleNamespace(
        workspace_ref="workspace:1",
        pane_ref="pane:1",
        surface_ref="surface:1",
        screen_lines=None,
        tail_lines=None,
        assignment_id=assignment_id,
        logical_target=logical_target,
        status="ACTIVE",
        title=title,
        goal=goal,
    )


def write_assignment_payload(path: Path, *, assignment_id: str = "doc-101", logical_target: str = "doc-bot") -> dict[str, object]:
    payload: dict[str, object] = {
        "workspace_name": "workspace:1",
        "updated_at": "2026-04-18T09:00:00+0800",
        "assignments": [
            {
                "assignment_id": assignment_id,
                "logical_target": logical_target,
                "bot_name": logical_target,
                "status": "ACTIVE",
                "title": "Doc delivery",
                "goal": "sync docs",
                "allow_intervene": True,
                "runtime_status": "running",
            }
        ],
        "ready": True,
        "active_assignment_count": 1,
        "runtime_status": "running",
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return payload


def build_main_args(
    *,
    assignment_file: Path,
    finish_log: Path,
    receipts_file: Path,
    consumer_state_file: Path,
    doc_task_list: Path,
    ce_sync_plan: Path,
) -> SimpleNamespace:
    return SimpleNamespace(
        assignment_file=str(assignment_file),
        finish_log=str(finish_log),
        receipts_file=str(receipts_file),
        consumer_state_file=str(consumer_state_file),
        forensic_read_pane=False,
        pm_task_list=str(doc_task_list),
        dev_task_list=str(doc_task_list),
        qa_task_list=str(doc_task_list),
        doc_task_list=str(doc_task_list),
        rea_task_list=str(doc_task_list),
        ce_sync_plan=str(ce_sync_plan),
        gitlab_base_url="http://example.invalid",
        gitlab_project_id=1,
        gitlab_issue_iid=1,
        post_gitlab=False,
        clear_to_idle=True,
    )


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
    assert outcome["summary_source"] == "control_packet.summary"
    assert outcome["source"] == "control_packet"
    assert outcome["artifact_path"].endswith("doc-bot-summary.json")


def test_finish_cycle_collect_outcome_uses_runtime_summary_when_packet_summary_missing() -> None:
    assignment = SimpleNamespace(
        workspace_ref="workspace:1",
        pane_ref="pane:1",
        surface_ref="surface:1",
        screen_lines=None,
        tail_lines=None,
        assignment_id="doc-102",
        logical_target="doc-bot",
    )
    packet = dict(EXAMPLE_PACKETS["completed"])
    packet["task_id"] = "DOC-102"
    packet["summary"] = ""
    consumer_entry = {
        "assignment_id": "doc-102",
        "state_source": "control_packet",
        "runtime_summary": "runtime summary from consumer state",
        "control_packet": packet,
    }
    with patch.object(cmux_finish_cycle, "read_screen") as mocked_read_screen:
        outcome = cmux_finish_cycle.collect_outcome(
            assignment,
            consumer_entry,
            allow_forensic_read_pane=False,
        )
    mocked_read_screen.assert_not_called()
    assert outcome["task_id"] == "DOC-102"
    assert outcome["summary"] == "runtime summary from consumer state"
    assert outcome["summary_source"] == "consumer.runtime_summary"
    assert outcome["source"] == "control_packet"


def test_finish_cycle_collect_outcome_control_path_does_not_use_evidence_line_extraction() -> None:
    assignment = SimpleNamespace(
        workspace_ref="workspace:1",
        pane_ref="pane:1",
        surface_ref="surface:1",
        screen_lines=None,
        tail_lines=None,
        assignment_id="doc-999",
        logical_target="doc-bot",
    )
    packet = dict(EXAMPLE_PACKETS["completed"])
    packet["task_id"] = ""
    packet["summary"] = ""
    consumer_entry = {
        "assignment_id": "doc-999",
        "state_source": "control_packet",
        "runtime_summary": "已完成 DOC-105 同步并回写。",
        "control_packet": packet,
    }
    with patch.object(
        cmux_finish_cycle,
        "extract_evidence_line",
        side_effect=AssertionError("control path should not call extract_evidence_line"),
    ), patch.object(cmux_finish_cycle, "read_screen") as mocked_read_screen:
        outcome = cmux_finish_cycle.collect_outcome(
            assignment,
            consumer_entry,
            allow_forensic_read_pane=False,
        )
    mocked_read_screen.assert_not_called()
    assert outcome["task_id"] == "DOC-105"
    assert outcome["summary_source"] == "consumer.runtime_summary"
    assert outcome["source"] == "control_packet"


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


def test_finish_cycle_collect_outcome_forensic_tail_keeps_evidence_line_fallback() -> None:
    assignment = SimpleNamespace(
        workspace_ref="workspace:1",
        pane_ref="pane:1",
        surface_ref="surface:1",
        screen_lines=None,
        tail_lines=None,
        assignment_id="doc-101",
        logical_target="doc-bot",
    )
    tail = "执行日志\n交付结论：DOC-101 已完成。\n下一步：同步 CE。\n"
    with patch.object(cmux_finish_cycle, "surface_snapshot", return_value={"ok": True}), patch.object(
        cmux_finish_cycle, "read_screen", return_value=tail
    ), patch.object(cmux_finish_cycle, "format_snapshot_meta", return_value="meta"), patch.object(
        cmux_finish_cycle, "try_extract_control_packet", return_value=(None, "")
    ), patch.object(cmux_finish_cycle, "classify_assignment_state", return_value=("waiting_input", False)), patch.object(
        cmux_finish_cycle, "is_assignment_complete", return_value=True
    ):
        outcome = cmux_finish_cycle.collect_outcome(
            assignment,
            consumer_entry=None,
            allow_forensic_read_pane=True,
        )
    assert outcome["source"] == "forensic_tail"
    assert outcome["summary"] == "交付结论：DOC-101 已完成。"
    assert outcome["summary_source"] == "forensic_tail.evidence_line"


def test_run_youzy_data_replica_hook_invokes_subprocess_safely() -> None:
    assignment = make_finish_cycle_assignment(assignment_id="doc-101")
    with patch.object(cmux_finish_cycle.subprocess, "run") as mocked_run:
        mocked_run.return_value = SimpleNamespace(returncode=0, stdout="hook ok\n", stderr="warning\n")
        succeeded, message = cmux_finish_cycle.run_youzy_data_replica_hook(
            assignment,
            artifact_path="/tmp/artifact.json",
            consumer_state_file=Path("/tmp/consumer-state.json"),
            allow_forensic_read_pane=True,
        )

    assert succeeded is True
    assert message == "hook ok\nwarning"
    mocked_run.assert_called_once()
    command = mocked_run.call_args.args[0]
    assert command[0] == sys.executable
    assert "--workspace" in command
    assert assignment.workspace_ref in command
    assert "--consumer-state-file" in command
    assert "/tmp/consumer-state.json" in command
    assert "--control-packet-artifact" in command
    assert "/tmp/artifact.json" in command
    assert "--forensic-read-pane" in command
    assert "--surface" in command
    assert assignment.surface_ref in command


def test_finish_cycle_main_writeback_updates_task_list_ce_log_and_receipt() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        base = Path(temp_dir)
        assignment_file = base / "cmux-assignment.json"
        consumer_state_file = base / "cmux-consumer-state-latest.json"
        finish_log = base / "cmux-finish.log"
        receipts_file = base / "cmux-finish-receipts.jsonl"
        task_list = base / "doc-task-list.md"
        ce_sync_plan = base / "ce-sync-plan.md"

        write_assignment_payload(assignment_file)
        task_list.write_text(
            "| task_id | title | status | owner | write_scope | evidence | blocker | next_step |\n"
            "|---|---|---|---|---|---|---|---|\n"
            "| DOC-101 | Delivery | `todo` | `doc` | `docs/*` | - | - | old |\n",
            encoding="utf-8",
        )
        ce_sync_plan.write_text("# CE Sync Plan\n", encoding="utf-8")
        packet = dict(EXAMPLE_PACKETS["completed"])
        packet["task_id"] = "DOC-101"
        packet["summary"] = "delivery summary from control packet"
        consumer_state_payload = {
            "schema_version": cmux_finish_cycle.CONSUMER_STATE_SCHEMA_VERSION,
            "assignments": {
                "doc-bot": {
                    "assignment_id": "doc-101",
                    "state_source": "control_packet",
                    "control_packet": packet,
                }
            },
        }
        consumer_state_file.write_text(
            json.dumps(consumer_state_payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

        args = build_main_args(
            assignment_file=assignment_file,
            finish_log=finish_log,
            receipts_file=receipts_file,
            consumer_state_file=consumer_state_file,
            doc_task_list=task_list,
            ce_sync_plan=ce_sync_plan,
        )

        assignment = make_finish_cycle_assignment(assignment_id="doc-101")
        with patch.object(cmux_finish_cycle, "parse_args", return_value=args), patch.object(
            cmux_finish_cycle, "load_assignment_file", return_value=[assignment]
        ):
            exit_code = cmux_finish_cycle.main()

        assert exit_code == 0
        task_list_text = task_list.read_text(encoding="utf-8")
        assert "`doc_synced`" in task_list_text
        assert "delivery summary from control packet" in task_list_text
        assert "指挥官在正式 CE issue 上执行生命周期评论" in task_list_text

        ce_sync_text = ce_sync_plan.read_text(encoding="utf-8")
        assert "`cmux_auto_finish`" in ce_sync_text
        assert "DOC-101->doc_synced" in ce_sync_text

        receipts_lines = [line for line in receipts_file.read_text(encoding="utf-8").splitlines() if line.strip()]
        assert len(receipts_lines) == 1
        receipt_payload = json.loads(receipts_lines[0])
        assert Path(receipt_payload["assignment_file"]).resolve() == assignment_file.resolve()
        assert receipt_payload["outcomes"][0]["task_id"] == "DOC-101"
        assert receipt_payload["outcomes"][0]["status"] == "doc_synced"

        finish_log_text = finish_log.read_text(encoding="utf-8")
        assert "finish_cycle_ok cycle_id=" in finish_log_text

        assignment_after = json.loads(assignment_file.read_text(encoding="utf-8"))
        assert assignment_after["assignments"][0]["status"] == "IDLE"
        assert assignment_after["assignments"][0]["runtime_status"] == "idle"
        assert assignment_after["assignments"][0]["last_completion_status"] == "doc_synced"


def test_finish_cycle_main_receipt_idempotency_skip() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        base = Path(temp_dir)
        assignment_file = base / "cmux-assignment.json"
        finish_log = base / "cmux-finish.log"
        receipts_file = base / "cmux-finish-receipts.jsonl"
        task_list = base / "doc-task-list.md"
        ce_sync_plan = base / "ce-sync-plan.md"
        consumer_state_file = base / "cmux-consumer-state-latest.json"

        payload = write_assignment_payload(assignment_file)
        cycle_id = cmux_finish_cycle.build_cycle_id(payload)
        receipts_file.write_text(json.dumps({"cycle_id": cycle_id}, ensure_ascii=False) + "\n", encoding="utf-8")
        task_list.write_text(
            "| task_id | title | status | owner | write_scope | evidence | blocker | next_step |\n"
            "|---|---|---|---|---|---|---|---|\n"
            "| DOC-101 | Delivery | `todo` | `doc` | `docs/*` | - | - | old |\n",
            encoding="utf-8",
        )
        ce_sync_plan.write_text("# CE Sync Plan\n", encoding="utf-8")

        args = build_main_args(
            assignment_file=assignment_file,
            finish_log=finish_log,
            receipts_file=receipts_file,
            consumer_state_file=consumer_state_file,
            doc_task_list=task_list,
            ce_sync_plan=ce_sync_plan,
        )

        with patch.object(cmux_finish_cycle, "parse_args", return_value=args), patch.object(
            cmux_finish_cycle, "load_assignment_file", side_effect=AssertionError("load_assignment_file should not run on idempotency skip")
        ):
            exit_code = cmux_finish_cycle.main()

        assert exit_code == 0
        assert "`todo`" in task_list.read_text(encoding="utf-8")
        assert ce_sync_plan.read_text(encoding="utf-8") == "# CE Sync Plan\n"
        finish_log_text = finish_log.read_text(encoding="utf-8")
        assert "finish_cycle_skip cycle_id=" in finish_log_text
        receipts_lines = [line for line in receipts_file.read_text(encoding="utf-8").splitlines() if line.strip()]
        assert len(receipts_lines) == 1


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
