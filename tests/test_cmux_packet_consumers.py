#!/usr/bin/env python3
"""Regression tests for Phase 1 P6 packet-first consumers."""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent
GLOBAL_CMUX_SCRIPTS = Path("/Users/busiji/.agents/skills/cmux/scripts")
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(GLOBAL_CMUX_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(GLOBAL_CMUX_SCRIPTS))

import cmux_finish_cycle  # noqa: E402
import watch_cmux_assignments  # noqa: E402
from workspace.tools.cmux_control_packet import EXAMPLE_PACKETS  # noqa: E402
from workspace.tools.current_task_source import build_cmux_task_source_ref  # noqa: E402


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


def make_cmux_task_source_ref(
    *,
    assignment_id: str,
    cycle_id: str,
    deliverable_path: str,
    evidence_path: str,
) -> dict[str, str]:
    return build_cmux_task_source_ref(
        assignment_id=assignment_id,
        cycle_id=cycle_id,
        deliverable_path=deliverable_path,
        evidence_path=evidence_path,
        status="active",
    )


def write_current_summary_artifact(
    path: Path,
    *,
    assignment_id: str,
    task_id: str,
    cycle_id: str,
    task_source_ref: dict[str, str],
    schema_version: str = "wb-pm-bot-summary-v1",
    summary: str = "current summary artifact",
) -> Path:
    payload = {
        "schema_version": schema_version,
        "assignment_id": assignment_id,
        "task_id": task_id,
        "cycle_id": cycle_id,
        "task_source_ref": dict(task_source_ref),
        "result": "completed",
        "summary": summary,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


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


def collect_outcome_contract(
    *,
    assignment_id: str = "doc-101",
    logical_target: str = "doc-bot",
    deliverable_path: str = "/Users/busiji/workbot/workspace/projects/sample/doc-101.md",
) -> dict[str, object]:
    return {
        "assignment_payload": {
            "assignments": [
                {
                    "assignment_id": assignment_id,
                    "logical_target": logical_target,
                    "deliverable": deliverable_path,
                }
            ]
        },
        "assignment_file": Path("/tmp/cmux-assignment.json"),
        "cycle_id": f"cmux-cycle:{assignment_id}:1",
    }


def test_watch_assignment_packet_helpers_prefer_control_packet() -> None:
    packet_text = render_packet(EXAMPLE_PACKETS["completed"])
    parsed, error = watch_cmux_assignments.try_extract_control_packet(packet_text)
    assert error == ""
    assert parsed is not None
    state, blocking, completed = watch_cmux_assignments.classify_control_packet_state(parsed)
    assert state == "awaiting_finish_cycle"
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
            **collect_outcome_contract(assignment_id="doc-101"),
            allow_forensic_read_pane=False,
        )
    mocked_read_screen.assert_not_called()
    assert outcome["task_id"] == "DOC-101"
    assert outcome["status"] == "doc_synced"
    assert "delivery note" in outcome["summary"]
    assert outcome["summary_source"] == "control_packet.summary"
    assert outcome["source"] == "control_packet"
    assert outcome["artifact_path"].endswith("doc-bot-summary.json")


def test_finish_cycle_collect_outcome_rejects_empty_terminal_packet_summary_even_with_runtime_summary() -> None:
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
        try:
            cmux_finish_cycle.collect_outcome(
                assignment,
                consumer_entry,
                **collect_outcome_contract(assignment_id="doc-102"),
                allow_forensic_read_pane=False,
            )
        except RuntimeError as exc:
            assert "summary must not be empty" in str(exc)
        else:
            raise AssertionError("expected empty terminal packet summary to be rejected")
    mocked_read_screen.assert_not_called()


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
    packet["assignment_id"] = "doc-999"
    packet["task_id"] = "DOC-105"
    packet["summary"] = "packet summary from control packet"
    packet["task_source_ref"] = make_cmux_task_source_ref(
        assignment_id="doc-999",
        cycle_id="cmux-cycle:doc-999:1",
        deliverable_path="/Users/busiji/workbot/workspace/projects/sample/doc-999.md",
        evidence_path=packet["artifact_path"],
    )
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
            **collect_outcome_contract(assignment_id="doc-999"),
            allow_forensic_read_pane=False,
        )
    mocked_read_screen.assert_not_called()
    assert outcome["task_id"] == "DOC-105"
    assert outcome["summary"] == "packet summary from control packet"
    assert outcome["summary_source"] == "control_packet.summary"
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
                **collect_outcome_contract(assignment_id="doc-101"),
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
                **collect_outcome_contract(assignment_id="doc-101"),
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
            **collect_outcome_contract(assignment_id="doc-101"),
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
        assert receipt_payload["outcomes"][0]["task_source_ref"]["status"] == "finished_local_writeback"

        finish_log_text = finish_log.read_text(encoding="utf-8")
        assert "finish_cycle_ok cycle_id=" in finish_log_text

        assignment_after = json.loads(assignment_file.read_text(encoding="utf-8"))
        assert assignment_after["assignments"][0]["status"] == "IDLE"
        assert assignment_after["assignments"][0]["runtime_status"] == "idle"
        assert assignment_after["assignments"][0]["last_completion_status"] == "doc_synced"
        assert assignment_after["current_task_sources"][0]["status"] == "finished_local_writeback"

        consumer_after = json.loads(consumer_state_file.read_text(encoding="utf-8"))
        entry = consumer_after["assignments"]["doc-bot"]
        assert entry["state"] == "finished_local_writeback"
        assert entry["state_source"] == "finish_cycle"
        assert entry["completed"] is True
        assert entry["locally_completed"] is True
        assert entry["finish_cycle_status"] == "doc_synced"
        assert entry["control_packet"]["task_id"] == "DOC-101"

        overview_path = base / "project-task-overview.txt"
        overview_text = overview_path.read_text(encoding="utf-8")
        assert "status: finished_local_writeback" in overview_text
        assert "DOC-101" in overview_text
        assert "doc-bot" in overview_text


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


def test_finish_cycle_main_rolls_back_when_receipt_write_fails() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        base = Path(temp_dir)
        assignment_file = base / "cmux-assignment.json"
        consumer_state_file = base / "cmux-consumer-state-latest.json"
        finish_log = base / "cmux-finish.log"
        receipts_file = base / "cmux-finish-receipts.jsonl"
        task_list = base / "doc-task-list.md"
        ce_sync_plan = base / "ce-sync-plan.md"
        overview_path = base / "project-task-overview.txt"

        write_assignment_payload(assignment_file)
        task_list.write_text(
            "| task_id | title | status | owner | write_scope | evidence | blocker | next_step |\n"
            "|---|---|---|---|---|---|---|---|\n"
            "| DOC-101 | Delivery | `todo` | `doc` | `docs/*` | - | - | old |\n",
            encoding="utf-8",
        )
        ce_sync_plan.write_text("# CE Sync Plan\n", encoding="utf-8")
        original_overview = "\n".join(
            [
                "# project-task-overview",
                "",
                "status: bootstrap-placeholder",
                "note: hook should refresh this file automatically.",
                "",
            ]
        )
        overview_path.write_text(original_overview, encoding="utf-8")
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

        original_assignment_text = assignment_file.read_text(encoding="utf-8")
        original_consumer_text = consumer_state_file.read_text(encoding="utf-8")
        original_task_list_text = task_list.read_text(encoding="utf-8")
        original_ce_sync_text = ce_sync_plan.read_text(encoding="utf-8")

        args = build_main_args(
            assignment_file=assignment_file,
            finish_log=finish_log,
            receipts_file=receipts_file,
            consumer_state_file=consumer_state_file,
            doc_task_list=task_list,
            ce_sync_plan=ce_sync_plan,
        )

        assignment = make_finish_cycle_assignment(assignment_id="doc-101")
        original_write_text_atomic = cmux_finish_cycle.write_text_atomic

        def flaky_write_text_atomic(path: Path, text: str) -> None:
            if path.resolve() == receipts_file.resolve():
                raise OSError("receipt write failed")
            original_write_text_atomic(path, text)

        with patch.object(cmux_finish_cycle, "parse_args", return_value=args), patch.object(
            cmux_finish_cycle, "load_assignment_file", return_value=[assignment]
        ), patch.object(cmux_finish_cycle, "write_text_atomic", side_effect=flaky_write_text_atomic):
            with pytest.raises(OSError, match="receipt write failed"):
                cmux_finish_cycle.main()

        assert assignment_file.read_text(encoding="utf-8") == original_assignment_text
        assert consumer_state_file.read_text(encoding="utf-8") == original_consumer_text
        assert task_list.read_text(encoding="utf-8") == original_task_list_text
        assert ce_sync_plan.read_text(encoding="utf-8") == original_ce_sync_text
        assert overview_path.read_text(encoding="utf-8") == original_overview
        assert not receipts_file.exists()


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


def test_watch_process_assignment_recovers_standalone_control_packet_artifact() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        runtime_dir = Path(temp_dir)
        cycle_id = "cmux-cycle:doc-101:1"
        summary_path = runtime_dir / "doc-bot-summary.json"
        current_task_source_ref = make_cmux_task_source_ref(
            assignment_id="doc-101",
            cycle_id=cycle_id,
            deliverable_path="/Users/busiji/workbot/workspace/projects/sample/doc-101.md",
            evidence_path=str(summary_path),
        )
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
            identity_payload={"task_source_ref": current_task_source_ref},
        )
        state = watch_cmux_assignments.RuntimeState(assignment_id="doc-101")
        state.task_dispatched = True
        state.observed_running = True
        state.observed_session_id = "s-1"
        hook_state = {
            "session_start_count": 0,
            "prompt_submit_count": 1,
            "stop_count": 0,
            "notification_count": 0,
            "last_session_id": "s-1",
        }
        artifact_path = runtime_dir / "doc-bot-control-packet.json"
        packet = dict(EXAMPLE_PACKETS["completed"])
        packet["assignment_id"] = "doc-101"
        packet["task_id"] = "DOC-101"
        packet["logical_target"] = "doc-bot"
        packet["marker"] = "XCP14PMR1:"
        packet["artifact_path"] = str(summary_path)
        packet["task_source_ref"] = dict(current_task_source_ref)
        write_current_summary_artifact(
            summary_path,
            assignment_id="doc-101",
            task_id="DOC-101",
            cycle_id=cycle_id,
            task_source_ref=packet["task_source_ref"],
        )
        artifact_path.write_text(json.dumps(packet, ensure_ascii=False), encoding="utf-8")

        args = SimpleNamespace(
            assignment_file=str(runtime_dir / "cmux-assignment.json"),
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
        broken_screen_packet = (
            'XCP14PMR1:{"schema_version":"wb-cmux-control-packet-v1",'
            '"assignment_id":"doc-101","logical_target":"doc-bot",'
            '"state":"completed","result":"pass","marker":"XCP14PMR1:",'
            '"summary":"bad\nwrap","artifact_path":"/tmp/doc-bot-summary.json"}'
        )
        with patch.object(watch_cmux_assignments, "load_active_surface_hook_state", return_value=hook_state), patch.object(
            watch_cmux_assignments, "surface_snapshot", return_value={"ok": True}
        ), patch.object(
            watch_cmux_assignments, "read_screen", return_value=broken_screen_packet
        ), patch.object(
            watch_cmux_assignments, "format_snapshot_meta", return_value="meta"
        ), patch.object(
            watch_cmux_assignments, "classify_assignment_state", return_value=("waiting_input", False)
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
    assert state.last_state_source == "control_packet"
    assert state.last_control_packet_error == ""
    assert state.last_control_packet is not None
    assert state.last_control_packet["assignment_id"] == "doc-101"


def test_watch_process_assignment_accepts_current_live_control_packet_with_current_summary_artifact() -> None:
    cycle_id = "workbot|2026-04-21T23:42:22+0800|doc-101"
    with tempfile.TemporaryDirectory() as temp_dir:
        runtime_dir = Path(temp_dir)
        summary_path = runtime_dir / "doc-bot-summary.json"
        current_task_source_ref = make_cmux_task_source_ref(
            assignment_id="doc-101",
            cycle_id=cycle_id,
            deliverable_path="/Users/busiji/workbot/workspace/projects/sample/doc-101.md",
            evidence_path=str(summary_path),
        )
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
            identity_payload={"task_source_ref": current_task_source_ref},
        )
        state = watch_cmux_assignments.RuntimeState(assignment_id="doc-101")
        state.task_dispatched = True
        state.observed_running = True
        state.observed_session_id = "s-1"
        hook_state = {
            "session_start_count": 0,
            "prompt_submit_count": 1,
            "stop_count": 0,
            "notification_count": 0,
            "last_session_id": "s-1",
        }
        packet = dict(EXAMPLE_PACKETS["completed"])
        packet["assignment_id"] = "doc-101"
        packet["task_id"] = "DOC-101"
        packet["logical_target"] = "doc-bot"
        packet["marker"] = "XCP14PMR1:"
        packet["artifact_path"] = str(summary_path)
        packet["task_source_ref"] = dict(current_task_source_ref)
        write_current_summary_artifact(
            summary_path,
            assignment_id="doc-101",
            task_id="DOC-101",
            cycle_id=cycle_id,
            task_source_ref=current_task_source_ref,
        )
        args = SimpleNamespace(
            assignment_file=str(runtime_dir / "cmux-assignment.json"),
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
        with patch.object(watch_cmux_assignments, "load_active_surface_hook_state", return_value=hook_state), patch.object(
            watch_cmux_assignments, "surface_snapshot", return_value={"ok": True}
        ), patch.object(
            watch_cmux_assignments, "read_screen", return_value=render_packet(packet)
        ), patch.object(
            watch_cmux_assignments, "format_snapshot_meta", return_value="meta"
        ), patch.object(
            watch_cmux_assignments, "classify_assignment_state", return_value=("waiting_input", False)
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
    assert state.last_state == "awaiting_finish_cycle"
    assert state.last_state_source == "control_packet"
    assert state.last_control_packet_error == ""
    assert state.last_control_packet is not None
    assert state.last_control_packet["marker"] == "XCP14PMR1:"


def test_watch_process_assignment_completed_packet_bypasses_pending_audit_and_marks_awaiting_finish_cycle() -> None:
    cycle_id = "workbot|2026-04-22T10:12:00+0800|doc-101"
    with tempfile.TemporaryDirectory() as temp_dir:
        runtime_dir = Path(temp_dir)
        summary_path = runtime_dir / "doc-bot-summary.json"
        current_task_source_ref = make_cmux_task_source_ref(
            assignment_id="doc-101",
            cycle_id=cycle_id,
            deliverable_path="/Users/busiji/workbot/workspace/projects/sample/doc-101.md",
            evidence_path=str(summary_path),
        )
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
            audit_round_1_status="pending",
            audit_round_2_owner="codex",
            audit_round_2_status="pending",
            status="ACTIVE",
            allow_intervene=False,
            identity_payload={"task_source_ref": current_task_source_ref},
        )
        state = watch_cmux_assignments.RuntimeState(assignment_id="doc-101")
        state.task_dispatched = True
        state.observed_running = True
        state.observed_session_id = "s-1"
        hook_state = {
            "session_start_count": 0,
            "prompt_submit_count": 1,
            "stop_count": 0,
            "notification_count": 0,
            "last_session_id": "s-1",
        }
        packet = dict(EXAMPLE_PACKETS["completed"])
        packet["assignment_id"] = "doc-101"
        packet["task_id"] = "DOC-101"
        packet["logical_target"] = "doc-bot"
        packet["marker"] = "XCP14PMR1:"
        packet["artifact_path"] = str(summary_path)
        packet["task_source_ref"] = dict(current_task_source_ref)
        write_current_summary_artifact(
            summary_path,
            assignment_id="doc-101",
            task_id="DOC-101",
            cycle_id=cycle_id,
            task_source_ref=current_task_source_ref,
        )
        args = SimpleNamespace(
            assignment_file=str(runtime_dir / "cmux-assignment.json"),
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
        with patch.object(watch_cmux_assignments, "load_active_surface_hook_state", return_value=hook_state), patch.object(
            watch_cmux_assignments, "surface_snapshot", return_value={"ok": True}
        ), patch.object(
            watch_cmux_assignments, "read_screen", return_value=render_packet(packet)
        ), patch.object(
            watch_cmux_assignments, "format_snapshot_meta", return_value="meta"
        ), patch.object(
            watch_cmux_assignments, "classify_assignment_state", return_value=("waiting_input", False)
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
    assert state.last_state == "awaiting_finish_cycle"
    assert state.last_state_source == "control_packet"
    assert state.last_control_packet_error == ""


def test_watch_recover_control_packet_ignores_archive_only_artifact_for_new_task_source() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        runtime_dir = Path(temp_dir)
        assignment_file = runtime_dir / "cmux-assignment.json"
        current_packet_path = runtime_dir / "doc-bot-summary-rt4.json"
        current_task_source_ref = make_cmux_task_source_ref(
            assignment_id="doc-rt4",
            cycle_id="workbot|2026-04-21T19:44:33+0800|doc-rt4",
            deliverable_path="/Users/busiji/workbot/workspace/projects/sample/doc-rt4.md",
            evidence_path=str(current_packet_path),
        )
        assignment = watch_cmux_assignments.WatchAssignment(
            logical_target="doc-bot",
            workspace_ref="workspace:1",
            pane_ref="pane:1",
            surface_ref="surface:1",
            assignment_id="doc-rt4",
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
            identity_payload={"task_source_ref": current_task_source_ref},
        )

        stale_packet = dict(EXAMPLE_PACKETS["completed"])
        stale_packet["assignment_id"] = "doc-rt3"
        stale_packet["logical_target"] = "doc-bot"
        stale_packet["artifact_path"] = str(runtime_dir / "doc-bot-summary-rt3.json")
        stale_packet["task_source_ref"] = make_cmux_task_source_ref(
            assignment_id="doc-rt3",
            cycle_id="workbot|2026-04-21T17:30:40+0800|doc-rt3",
            deliverable_path="/Users/busiji/workbot/workspace/projects/sample/doc-rt4.md",
            evidence_path=stale_packet["artifact_path"],
        )
        (runtime_dir / "doc-bot-control-packet.json").write_text(
            json.dumps(stale_packet, ensure_ascii=False),
            encoding="utf-8",
        )

        recovered, error = watch_cmux_assignments.try_recover_control_packet_from_artifact(
            assignment,
            str(assignment_file),
        )

    assert recovered is None
    assert "archive-only control packet artifact" in error
    assert "assignment mismatch" in error or "task_source mismatch" in error


def test_watch_recover_control_packet_accepts_current_task_source_artifact() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        runtime_dir = Path(temp_dir)
        assignment_file = runtime_dir / "cmux-assignment.json"
        current_packet_path = runtime_dir / "doc-bot-summary-rt4.json"
        current_task_source_ref = make_cmux_task_source_ref(
            assignment_id="doc-rt4",
            cycle_id="workbot|2026-04-21T19:44:33+0800|doc-rt4",
            deliverable_path="/Users/busiji/workbot/workspace/projects/sample/doc-rt4.md",
            evidence_path=str(current_packet_path),
        )
        assignment = watch_cmux_assignments.WatchAssignment(
            logical_target="doc-bot",
            workspace_ref="workspace:1",
            pane_ref="pane:1",
            surface_ref="surface:1",
            assignment_id="doc-rt4",
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
            identity_payload={"task_source_ref": current_task_source_ref},
        )

        current_packet = dict(EXAMPLE_PACKETS["completed"])
        current_packet["assignment_id"] = "doc-rt4"
        current_packet["task_id"] = "DOC-104"
        current_packet["logical_target"] = "doc-bot"
        current_packet["artifact_path"] = str(current_packet_path)
        current_packet["task_source_ref"] = dict(current_task_source_ref)
        (runtime_dir / "doc-bot-control-packet.json").write_text(
            json.dumps(current_packet, ensure_ascii=False),
            encoding="utf-8",
        )

        recovered, error = watch_cmux_assignments.try_recover_control_packet_from_artifact(
            assignment,
            str(assignment_file),
        )

    assert error == ""
    assert recovered is not None
    assert recovered["assignment_id"] == "doc-rt4"
    assert recovered["task_source_ref"]["task_source_id"] == current_task_source_ref["task_source_id"]


def test_watch_resolve_control_packet_fail_closed_on_invalid_marker_payload_without_current_artifact() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        runtime_dir = Path(temp_dir)
        current_task_source_ref = make_cmux_task_source_ref(
            assignment_id="doc-101",
            cycle_id="workbot|2026-04-21T23:42:22+0800|doc-101",
            deliverable_path="/Users/busiji/workbot/workspace/projects/sample/doc-101.md",
            evidence_path=str(runtime_dir / "doc-bot-summary.json"),
        )
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
            identity_payload={"task_source_ref": current_task_source_ref},
        )

        packet, error = watch_cmux_assignments.resolve_control_packet(
            'XCP14PMR1:{"schema_version":"wb-cmux-control-packet-v1","assignment_id":"doc-101",'
            '"logical_target":"doc-bot","state":"completed","result":"pass","marker":"XCP14PMR1:",'
            '"summary":"bad\nwrap","artifact_path":"/tmp/doc-bot-summary.json"}',
            assignment,
            str(runtime_dir / "cmux-assignment.json"),
        )

    assert packet is None
    assert "invalid packet json after XCP14PMR1:" in error


def test_dispatch_task_overrides_stale_task_source_ref_with_current_assignment() -> None:
    current_task_source_ref = make_cmux_task_source_ref(
        assignment_id="pm-rt4",
        cycle_id="workbot|2026-04-21T19:44:33+0800|pm-rt4",
        deliverable_path="/Users/busiji/workbot/workspace/projects/sample/pm-rt4.md",
        evidence_path="/tmp/pm-bot-summary-rt4.json",
    )
    stale_task_source_ref = make_cmux_task_source_ref(
        assignment_id="pm-rt4",
        cycle_id="workbot|2026-04-21T19:35:23+0800|pm-rt4",
        deliverable_path=current_task_source_ref["deliverable_path"],
        evidence_path=current_task_source_ref["evidence_path"],
    )
    assignment = watch_cmux_assignments.WatchAssignment(
        logical_target="pm-bot",
        workspace_ref="workspace:1",
        pane_ref="pane:1",
        surface_ref="surface:1",
        assignment_id="pm-rt4",
        bot_name="pm-bot",
        title="Homepage inventory",
        goal="inventory homepage",
        task_kind="assignment",
        audit_round_1_owner="rea-bot",
        audit_round_1_status="pending",
        audit_round_2_owner="codex",
        audit_round_2_status="pending",
        status="ACTIVE",
        allow_intervene=True,
        identity_payload={"task_source_ref": current_task_source_ref},
    )
    prompt = (
        f"Task source ref JSON: {json.dumps(stale_task_source_ref, ensure_ascii=False)}\n"
        f"The control packet must use task_source_ref={json.dumps(stale_task_source_ref, ensure_ascii=False)}."
    )

    with patch.object(watch_cmux_assignments, "paste_text") as mocked_paste, patch.object(
        watch_cmux_assignments, "send_key"
    ) as mocked_send:
        watch_cmux_assignments.dispatch_task(assignment, prompt)

    mocked_send.assert_called_once_with("surface:1", "Enter")
    dispatched_text = mocked_paste.call_args.args[2]
    assert "Current active assignment task-source gate:" in dispatched_text
    assert current_task_source_ref["cycle_id"] in dispatched_text
    assert stale_task_source_ref["cycle_id"] not in dispatched_text


def test_finish_cycle_blocks_archive_only_embedded_consumer_packet() -> None:
    current_task_source_ref = make_cmux_task_source_ref(
        assignment_id="doc-rt4",
        cycle_id="workbot|2026-04-21T19:44:33+0800|doc-rt4",
        deliverable_path="/Users/busiji/workbot/workspace/projects/sample/doc-rt4.md",
        evidence_path="/tmp/doc-bot-summary-rt4.json",
    )
    assignment = make_finish_cycle_assignment(assignment_id="doc-rt4")
    assignment.identity_payload = {"task_source_ref": current_task_source_ref}

    stale_packet = dict(EXAMPLE_PACKETS["completed"])
    stale_packet["assignment_id"] = "doc-rt3"
    stale_packet["logical_target"] = "doc-bot"
    stale_packet["artifact_path"] = "/tmp/doc-bot-summary-rt3.json"
    stale_packet["task_source_ref"] = make_cmux_task_source_ref(
        assignment_id="doc-rt3",
        cycle_id="workbot|2026-04-21T17:30:40+0800|doc-rt3",
        deliverable_path=current_task_source_ref["deliverable_path"],
        evidence_path=stale_packet["artifact_path"],
    )

    try:
        cmux_finish_cycle.control_packet_from_consumer_entry(
            assignment,
            {
                "assignment_id": "doc-rt4",
                "state_source": "control_packet",
                "control_packet": stale_packet,
            },
        )
    except RuntimeError as exc:
        assert "archive-only control packet" in str(exc)
    else:
        raise AssertionError("expected stale embedded control packet to be blocked")


def test_finish_cycle_accepts_current_embedded_consumer_packet_with_current_summary_artifact() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        runtime_dir = Path(temp_dir)
        summary_path = runtime_dir / "doc-bot-summary.json"
        current_task_source_ref = make_cmux_task_source_ref(
            assignment_id="doc-rt4",
            cycle_id="workbot|2026-04-21T19:44:33+0800|doc-rt4",
            deliverable_path="/Users/busiji/workbot/workspace/projects/sample/doc-rt4.md",
            evidence_path=str(summary_path),
        )
        assignment = make_finish_cycle_assignment(assignment_id="doc-rt4")
        assignment.identity_payload = {"task_source_ref": current_task_source_ref}

        packet = dict(EXAMPLE_PACKETS["completed"])
        packet["assignment_id"] = "doc-rt4"
        packet["task_id"] = "DOC-104"
        packet["logical_target"] = "doc-bot"
        packet["marker"] = "XCP14PMR1:"
        packet["artifact_path"] = str(summary_path)
        packet["task_source_ref"] = dict(current_task_source_ref)
        write_current_summary_artifact(
            summary_path,
            assignment_id="doc-rt4",
            task_id="DOC-104",
            cycle_id=current_task_source_ref["cycle_id"],
            task_source_ref=current_task_source_ref,
        )

        accepted = cmux_finish_cycle.control_packet_from_consumer_entry(
            assignment,
            {
                "assignment_id": "doc-rt4",
                "state_source": "control_packet",
                "control_packet": packet,
            },
        )

    assert accepted is not None
    assert accepted["assignment_id"] == "doc-rt4"
    assert accepted["artifact_path"] == str(summary_path)


def test_finish_cycle_collect_outcome_blocks_forensic_task_source_cycle_mismatch() -> None:
    current_cycle_id = "workbot|2026-04-21T19:44:33+0800|doc-rt4"
    current_task_source_ref = make_cmux_task_source_ref(
        assignment_id="doc-rt4",
        cycle_id=current_cycle_id,
        deliverable_path="/Users/busiji/workbot/workspace/projects/sample/doc-rt4.md",
        evidence_path="/tmp/doc-bot-summary-rt4.json",
    )
    assignment = make_finish_cycle_assignment(assignment_id="doc-rt4")
    assignment.identity_payload = {"task_source_ref": current_task_source_ref}

    stale_packet = dict(EXAMPLE_PACKETS["completed"])
    stale_packet["assignment_id"] = "doc-rt4"
    stale_packet["logical_target"] = "doc-bot"
    stale_packet["artifact_path"] = "/tmp/doc-bot-summary-rt4.json"
    stale_packet["task_source_ref"] = make_cmux_task_source_ref(
        assignment_id="doc-rt4",
        cycle_id="workbot|2026-04-21T19:35:23+0800|doc-rt4",
        deliverable_path=current_task_source_ref["deliverable_path"],
        evidence_path=stale_packet["artifact_path"],
    )

    with patch.object(cmux_finish_cycle, "surface_snapshot", return_value={"ok": True}), patch.object(
        cmux_finish_cycle,
        "read_screen",
        return_value=render_packet(stale_packet),
    ), patch.object(cmux_finish_cycle, "format_snapshot_meta", return_value="meta"):
        try:
            cmux_finish_cycle.collect_outcome(
                assignment,
                consumer_entry=None,
                assignment_payload={"assignments": []},
                assignment_file=Path("/tmp/cmux-assignment.json"),
                cycle_id=current_cycle_id,
                allow_forensic_read_pane=True,
            )
        except RuntimeError as exc:
            assert "archive-only control packet during forensic read" in str(exc)
            assert "cycle_id expected=" in str(exc)
        else:
            raise AssertionError("expected forensic stale-cycle control packet to be blocked")


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
        assignment_file="/tmp/cmux-assignment.json",
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


def test_watch_process_assignment_blocks_task_source_cycle_mismatch() -> None:
    current_task_source_ref = make_cmux_task_source_ref(
        assignment_id="doc-101",
        cycle_id="workbot|2026-04-21T19:44:33+0800|doc-101",
        deliverable_path="/Users/busiji/workbot/workspace/projects/sample/doc-101.md",
        evidence_path="/tmp/doc-bot-summary-rt4.json",
    )
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
        identity_payload={"task_source_ref": current_task_source_ref},
    )
    state = watch_cmux_assignments.RuntimeState(assignment_id="doc-101")
    state.task_dispatched = True
    state.observed_running = True
    state.observed_session_id = "s-1"
    args = SimpleNamespace(
        assignment_file="/tmp/cmux-assignment.json",
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
    stale_packet = dict(EXAMPLE_PACKETS["completed"])
    stale_packet["assignment_id"] = "doc-101"
    stale_packet["logical_target"] = "doc-bot"
    stale_packet["artifact_path"] = current_task_source_ref["evidence_path"]
    stale_packet["task_source_ref"] = make_cmux_task_source_ref(
        assignment_id="doc-101",
        cycle_id="workbot|2026-04-21T19:35:23+0800|doc-101",
        deliverable_path=current_task_source_ref["deliverable_path"],
        evidence_path=current_task_source_ref["evidence_path"],
    )
    with patch.object(watch_cmux_assignments, "load_active_surface_hook_state", return_value=hook_state), patch.object(
        watch_cmux_assignments, "surface_snapshot", return_value={"ok": True}
    ), patch.object(
        watch_cmux_assignments, "read_screen", return_value=render_packet(stale_packet)
    ), patch.object(
        watch_cmux_assignments, "format_snapshot_meta", return_value="meta"
    ), patch.object(
        watch_cmux_assignments, "classify_assignment_state", return_value=("waiting_input", False)
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
    assert state.last_state == "task_blocked"
    assert state.last_state_source == "control_packet_error"
    assert state.last_control_packet is None
    assert "task_source mismatch" in state.last_control_packet_error
    assert "cycle_id expected=" in state.last_control_packet_error


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
        assignment_file="/tmp/cmux-assignment.json",
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
