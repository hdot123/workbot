#!/usr/bin/env python3

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from workspace.tools.cmux_control_packet import EXAMPLE_PACKETS  # noqa: E402
from workspace.tools.current_task_source import build_cmux_task_source_ref  # noqa: E402
from workspace.tools.cmux_full_workflow_log import (  # noqa: E402
    DEFAULT_LIVE_JSON_NAME,
    DEFAULT_LIVE_SUMMARY_NAME,
    append_main_thread_action,
    build_live_workflow_log,
    build_sample_three_round_five_bot_workflow,
    materialize_live_workflow_log,
)


def write_json(path: Path, payload: dict[str, object]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def current_cmux_task_source(
    *,
    assignment_id: str,
    cycle_id: str,
    runtime_dir: Path,
    status: str = "finished_local_writeback",
    deliverable_path: str = "/Users/busiji/workbot/workspace/projects/sample/current-task.md",
) -> dict[str, str]:
    return build_cmux_task_source_ref(
        assignment_id=assignment_id,
        cycle_id=cycle_id,
        deliverable_path=deliverable_path,
        evidence_path=str((runtime_dir / "cmux-assignment.json").resolve()),
        status=status,
    )


def write_full_a7_receipt(path: Path, runtime_dir: Path) -> None:
    cycle_id = "workbot|2026-04-19T13:51:00+0800|strict-gap-fix"
    path.write_text(
        json.dumps(
            {
                "cycle_id": cycle_id,
                "task_sources": [
                    current_cmux_task_source(
                        assignment_id="PM-101",
                        cycle_id=cycle_id,
                        runtime_dir=runtime_dir,
                    )
                ],
                "outcomes": [
                    {
                        "assignment_id": "PM-101",
                        "logical_target": "pm-bot",
                        "task_id": "PM-101",
                        "prefix": "PM",
                        "status": "pm_completed",
                        "summary": "pm writeback complete",
                        "artifact_path": "/tmp/pm-summary.json",
                        "source": "control_packet",
                        "task_source_ref": current_cmux_task_source(
                            assignment_id="PM-101",
                            cycle_id=cycle_id,
                            runtime_dir=runtime_dir,
                        ),
                    },
                    {
                        "assignment_id": "DEV-101",
                        "logical_target": "dev-bot",
                        "task_id": "DEV-101",
                        "prefix": "DEV",
                        "status": "dev_completed",
                        "summary": "dev writeback complete",
                        "artifact_path": "/tmp/dev-summary.json",
                        "source": "control_packet",
                        "task_source_ref": current_cmux_task_source(
                            assignment_id="DEV-101",
                            cycle_id=cycle_id,
                            runtime_dir=runtime_dir,
                        ),
                    },
                    {
                        "assignment_id": "QA-101",
                        "logical_target": "qa-bot",
                        "task_id": "QA-101",
                        "prefix": "QA",
                        "status": "qa_completed",
                        "summary": "qa writeback complete",
                        "artifact_path": "/tmp/qa-summary.json",
                        "source": "control_packet",
                        "task_source_ref": current_cmux_task_source(
                            assignment_id="QA-101",
                            cycle_id=cycle_id,
                            runtime_dir=runtime_dir,
                        ),
                    },
                    {
                        "assignment_id": "DOC-101",
                        "logical_target": "doc-bot",
                        "task_id": "DOC-101",
                        "prefix": "DOC",
                        "status": "doc_synced",
                        "summary": "doc writeback complete",
                        "artifact_path": "/tmp/doc-summary.json",
                        "source": "control_packet",
                        "task_source_ref": current_cmux_task_source(
                            assignment_id="DOC-101",
                            cycle_id=cycle_id,
                            runtime_dir=runtime_dir,
                        ),
                    },
                    {
                        "assignment_id": "REA-101",
                        "logical_target": "rea-bot",
                        "task_id": "REA-101",
                        "prefix": "REA",
                        "status": "rea_completed",
                        "summary": "rea writeback complete",
                        "artifact_path": "/tmp/rea-summary.json",
                        "source": "control_packet",
                        "task_source_ref": current_cmux_task_source(
                            assignment_id="REA-101",
                            cycle_id=cycle_id,
                            runtime_dir=runtime_dir,
                        ),
                    },
                ],
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )


def write_native_pass_prerequisites(runtime_dir: Path) -> None:
    cycle_id = "workbot|2026-04-19T13:51:00+0800|strict-gap-fix"
    write_json(
        runtime_dir / "cmux-assignment.json",
        {
            "ready": True,
            "dispatch_ready": True,
            "runtime_status": "idle",
            "cycle_id": cycle_id,
            "updated_at": "2026-04-19T13:50:00+0800",
            "current_task_sources": [
                current_cmux_task_source(
                    assignment_id="PM-101",
                    cycle_id=cycle_id,
                    runtime_dir=runtime_dir,
                )
            ],
            "assignments": [],
        },
    )
    packet = dict(EXAMPLE_PACKETS["completed"])
    packet["assignment_id"] = "PM-101"
    packet["artifact_path"] = str((runtime_dir / "pm-bot-control-packet.json").resolve())
    packet["task_source_ref"] = current_cmux_task_source(
        assignment_id="PM-101",
        cycle_id=cycle_id,
        runtime_dir=runtime_dir,
    )
    packet["task_source_ref"]["evidence_path"] = str((runtime_dir / "pm-bot-control-packet.json").resolve())
    write_json(runtime_dir / "pm-bot-control-packet.json", packet)
    write_json(
        runtime_dir / "cmux-consumer-state-latest.json",
        {
            "schema_version": "wb-cmux-consumer-state-v1",
            "assignments": {
                "pm-bot": {
                    "assignment_id": "PM-101",
                    "state": "completed",
                    "control_packet": packet,
                }
            },
        },
    )
    write_full_a7_receipt(runtime_dir / "cmux-finish-receipts.jsonl", runtime_dir)


def test_build_live_workflow_log_collects_dispatch_and_pending_handoff() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        runtime_dir = Path(tmpdir)
        write_json(
            runtime_dir / "cmux-assignment.json",
            {
                "ready": True,
                "dispatch_ready": True,
                "runtime_status": "running",
                "updated_at": "2026-04-19T10:00:00+0800",
                "assignments": [
                    {
                        "logical_target": "pm-bot",
                        "bot_name": "pm-bot",
                        "assignment_id": "PM-101",
                        "status": "ACTIVE",
                        "title": "Freeze scope",
                        "goal": "Freeze round scope",
                        "workspace_ref": "workspace:1",
                        "pane_ref": "pane:2",
                        "surface_ref": "surface:2",
                    }
                ],
            },
        )
        write_json(
            runtime_dir / "hook-state.json",
            {
                "surfaces": {
                    "surface:2": {
                        "prompt_submit_count": 1,
                        "last_prompt_submit_at": "2026-04-19T10:00:00+0800",
                        "stop_count": 1,
                        "last_stop_at": "2026-04-19T10:05:00+0800",
                        "notification_count": 1,
                        "last_notification_at": "2026-04-19T10:06:00+0800",
                        "last_event": "notification",
                        "adhoc_prompt_count": 0,
                    }
                }
            },
        )
        (runtime_dir / "watch_cmux_assignments.log").write_text(
            "\n".join(
                [
                    "[action] logical_target=pm-bot assignment_id=PM-101 display_name=pm-bot / Freeze scope dispatch_task",
                    "=" * 80,
                    "2026-04-19 10:00:00",
                    "logical_target=pm-bot workspace=workspace:1 pane=pane:2 surface=surface:2",
                    "assignment_id=PM-101 display_name=pm-bot / Freeze scope bot_name=pm-bot status=ACTIVE allow_intervene=yes",
                    "workspace=workspace:1 pane=pane:2 surface=surface:2 title=pm-bot cmd=claude active=1 dead=0 path=/Users/busiji/workbot tty=ttys001",
                    "state=running blocking=no idle_polls=0 alert=change",
                    "-" * 80,
                    "screen body omitted",
                ]
            )
            + "\n",
            encoding="utf-8",
        )

        payload = build_live_workflow_log(runtime_dir)

        assert payload["mode"] == "live_runtime"
        assert payload["summary"]["active_assignment_count"] == 1
        assert payload["summary"]["consumer_state_present"] is False
        assert payload["verification_packet"]["read_order"][0]["slot"] == "workflow_log"
        assert payload["verification_packet"]["missing_slots"] == [
            "control_packet",
            "consumer_state",
            "finish_receipt",
            "main_thread_actions",
        ]
        assert payload["pending_handoffs"] == [
            {
                "logical_target": "pm-bot",
                "assignment_id": "PM-101",
                "phase": "A6",
                "reason": "surface_stop_or_notification_requires_commander_review",
                "stop_count": 1,
                "notification_count": 1,
                "last_event": "notification",
                "last_prompt_submit_at": "2026-04-19T10:00:00+0800",
                "last_stop_at": "2026-04-19T10:05:00+0800",
                "last_notification_at": "2026-04-19T10:06:00+0800",
            }
        ]
        assert any(event["kind"] == "main_thread_dispatch" for event in payload["events"])
        assert any(event["kind"] == "main_thread_handoff_pending" for event in payload["events"])
        assert any("consumer state missing" in warning for warning in payload["warnings"])


def test_build_live_workflow_log_collects_finish_cycle_receipts() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        runtime_dir = Path(tmpdir)
        cycle_id = "workbot|2026-04-19T10:30:00+0800|pm-101"
        write_json(
            runtime_dir / "cmux-assignment.json",
            {
                "ready": True,
                "dispatch_ready": True,
                "runtime_status": "idle",
                "cycle_id": cycle_id,
                "updated_at": "2026-04-19T10:30:00+0800",
                "current_task_sources": [
                    current_cmux_task_source(
                        assignment_id="pm-101",
                        cycle_id=cycle_id,
                        runtime_dir=runtime_dir,
                    )
                ],
                "assignments": [],
            },
        )
        (runtime_dir / "cmux-finish-receipts.jsonl").write_text(
            json.dumps(
                {
                    "cycle_id": cycle_id,
                    "outcomes": [
                        {
                            "assignment_id": "pm-101",
                            "logical_target": "pm-bot",
                            "task_id": "PM-101",
                            "prefix": "PM",
                            "status": "pm_completed",
                            "summary": "scope packet written",
                            "summary_source": "control_packet.summary",
                            "artifact_path": "/tmp/pm-summary.json",
                            "source": "control_packet",
                            "task_source_ref": current_cmux_task_source(
                                assignment_id="pm-101",
                                cycle_id=cycle_id,
                                runtime_dir=runtime_dir,
                            ),
                        }
                    ],
                },
                ensure_ascii=False,
            )
            + "\n",
            encoding="utf-8",
        )
        (runtime_dir / "cmux-finish.log").write_text(
            "finish_cycle_ok cycle_id=workbot|2026-04-19T10:30:00+0800|pm-101\n",
            encoding="utf-8",
        )

        payload = build_live_workflow_log(runtime_dir)
        finish_events = [event for event in payload["events"] if event["kind"] == "finish_cycle_local_writeback"]
        assert len(finish_events) == 1
        assert finish_events[0]["actor"] == "finish-cycle"
        assert finish_events[0]["phase"] == "A7"
        assert payload["summary"]["finish_receipt_count"] == 1
        assert payload["summary"]["a7_writeback_complete"] is True
        assert payload["summary"]["a7_missing_writeback_targets"] == []
        assert payload["verification_packet"]["read_order"] == [
            {
                "slot": "finish_receipt",
                "path": str((runtime_dir / "cmux-finish-receipts.jsonl").resolve()),
                "via_rule": "finish_receipt_journal",
            },
            {
                "slot": "workflow_log",
                "path": str((runtime_dir / DEFAULT_LIVE_JSON_NAME).resolve()),
                "via_rule": "workflow_log",
            },
        ]


def test_build_live_workflow_log_accepts_valid_generic_control_packet_file() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        runtime_dir = Path(tmpdir)
        cycle_id = "cmux-cycle:doc-101:1"
        write_json(
            runtime_dir / "cmux-assignment.json",
            {
                "ready": True,
                "dispatch_ready": True,
                "runtime_status": "idle",
                "cycle_id": cycle_id,
                "updated_at": "2026-04-19T10:30:00+0800",
                "current_task_sources": [
                    current_cmux_task_source(
                        assignment_id="doc-101",
                        cycle_id=cycle_id,
                        runtime_dir=runtime_dir,
                    )
                ],
                "assignments": [],
            },
        )
        packet = dict(EXAMPLE_PACKETS["completed"])
        packet["assignment_id"] = "doc-101"
        packet["task_source_ref"] = current_cmux_task_source(
            assignment_id="doc-101",
            cycle_id=cycle_id,
            runtime_dir=runtime_dir,
        )
        packet["artifact_path"] = str((runtime_dir / "artifact.json").resolve())
        packet["task_source_ref"]["evidence_path"] = str((runtime_dir / "artifact.json").resolve())
        write_json(runtime_dir / "artifact.json", packet)
        write_json(
            runtime_dir / "cmux-consumer-state-latest.json",
            {
                "schema_version": "wb-cmux-consumer-state-v1",
                "assignments": {
                    "doc-bot": {
                        "assignment_id": "doc-101",
                        "state": "completed",
                        "control_packet": packet,
                    }
                },
            },
        )
        payload = build_live_workflow_log(runtime_dir)

        assert payload["verification_packet"]["missing_slots"] == [
            "finish_receipt",
            "main_thread_actions",
        ]
        assert payload["verification_packet"]["read_order"][0] == {
            "slot": "control_packet",
            "path": str((runtime_dir / "artifact.json").resolve()),
            "via_rule": "control_packet_artifact",
        }


def test_build_live_workflow_log_includes_main_thread_action_journal() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        runtime_dir = Path(tmpdir)
        cycle_id = "workbot|2026-04-19T11:00:00+0800|PM-101"
        write_json(
            runtime_dir / "cmux-assignment.json",
            {
                "ready": True,
                "dispatch_ready": True,
                "runtime_status": "idle",
                "cycle_id": cycle_id,
                "updated_at": "2026-04-19T11:00:00+0800",
                "current_task_sources": [
                    current_cmux_task_source(
                        assignment_id="PM-101",
                        cycle_id=cycle_id,
                        runtime_dir=runtime_dir,
                    )
                ],
                "assignments": [],
            },
        )
        (runtime_dir / "cmux-main-thread-actions.jsonl").write_text(
            "\n".join(
                [
                    json.dumps(
                        {
                            "schema_version": "wb-cmux-main-thread-action-v1",
                            "at": "2026-04-19T11:03:00+0800",
                            "actor": "main-thread",
                            "phase": "A8",
                            "kind": "main_thread_acceptance",
                            "logical_target": "pm-bot",
                            "assignment_id": "PM-101",
                            "task_source_ref": current_cmux_task_source(
                                assignment_id="PM-101",
                                cycle_id=cycle_id,
                                runtime_dir=runtime_dir,
                            ),
                            "summary": "main-thread accepted the pm-bot delivery packet",
                        },
                        ensure_ascii=False,
                    ),
                    json.dumps(
                        {
                            "schema_version": "wb-cmux-main-thread-action-v1",
                            "at": "2026-04-19T11:05:00+0800",
                            "actor": "main-thread",
                            "phase": "A9",
                            "kind": "main_thread_closure",
                            "logical_target": "pm-bot",
                            "assignment_id": "PM-101",
                            "task_source_ref": current_cmux_task_source(
                                assignment_id="PM-101",
                                cycle_id=cycle_id,
                                runtime_dir=runtime_dir,
                            ),
                            "summary": "main-thread closed the workflow after acceptance",
                        },
                        ensure_ascii=False,
                    ),
                ]
            )
            + "\n",
            encoding="utf-8",
        )

        payload = build_live_workflow_log(runtime_dir)

        assert any(event["kind"] == "main_thread_acceptance" for event in payload["events"])
        assert any(event["kind"] == "main_thread_closure" for event in payload["events"])
        assert payload["summary"]["main_thread_closure_evidenced"] is True
        assert payload["summary"]["final_reviewer_legality_ok"] is False
        assert payload["verification_packet"]["read_order"] == [
            {
                "slot": "workflow_log",
                "path": str((runtime_dir / DEFAULT_LIVE_JSON_NAME).resolve()),
                "via_rule": "workflow_log",
            },
            {
                "slot": "main_thread_actions",
                "path": str((runtime_dir / "cmux-main-thread-actions.jsonl").resolve()),
                "via_rule": "main_thread_action_journal",
            },
        ]


def test_append_main_thread_action_refreshes_live_workflow_log_artifact() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        runtime_dir = Path(tmpdir)
        cycle_id = "workbot|2026-04-19T11:10:00+0800|PM-101"
        write_json(
            runtime_dir / "cmux-assignment.json",
            {
                "ready": True,
                "dispatch_ready": True,
                "runtime_status": "idle",
                "cycle_id": cycle_id,
                "updated_at": "2026-04-19T11:10:00+0800",
                "current_task_sources": [
                    current_cmux_task_source(
                        assignment_id="PM-101",
                        cycle_id=cycle_id,
                        runtime_dir=runtime_dir,
                    )
                ],
                "assignments": [],
            },
        )

        output_path = materialize_live_workflow_log(runtime_dir)
        assert output_path == (runtime_dir / DEFAULT_LIVE_JSON_NAME).resolve()
        initial_payload = json.loads(output_path.read_text(encoding="utf-8"))
        assert initial_payload["summary"]["main_thread_closure_evidenced"] is False
        initial_summary = json.loads((runtime_dir / DEFAULT_LIVE_SUMMARY_NAME).read_text(encoding="utf-8"))
        assert initial_summary["artifact_type"] == "commander_summary"
        assert initial_summary["task_run_number"] == 1
        archive_dir = Path(initial_summary["archive_bundle_dir"])
        assert archive_dir.exists()
        assert (archive_dir / "workflow-log.json").exists()
        assert (archive_dir / "workflow-summary.json").exists()

        append_main_thread_action(
            runtime_dir,
            phase="A9",
            kind="main_thread_closure",
            summary="main-thread closed the assignment after acceptance",
            logical_target="pm-bot",
            assignment_id="PM-101",
        )

        refreshed_payload = json.loads(output_path.read_text(encoding="utf-8"))
        assert refreshed_payload["summary"]["main_thread_closure_evidenced"] is True
        assert refreshed_payload["events"][-1]["kind"] == "main_thread_closure"
        refreshed_summary = json.loads((runtime_dir / DEFAULT_LIVE_SUMMARY_NAME).read_text(encoding="utf-8"))
        assert refreshed_summary["task_run_number"] == 1
        assert refreshed_summary["archive_bundle_dir"] == str(archive_dir)


def test_materialize_live_workflow_log_isolates_runs_by_date_task_and_run_number() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        runtime_dir = Path(tmpdir)
        assignment_path = runtime_dir / "cmux-assignment.json"
        write_json(
            assignment_path,
            {
                "ready": True,
                "dispatch_ready": True,
                "runtime_status": "running",
                "updated_at": "2026-04-19T11:30:00+0800",
                "assignments": [
                    {
                        "logical_target": "pm-bot",
                        "bot_name": "pm-bot",
                        "assignment_id": "P10-PHASE0A-ISSUE16-PM",
                        "status": "ACTIVE",
                        "title": "Freeze scope",
                        "goal": "Freeze round scope",
                        "workspace_ref": "workspace:1",
                        "pane_ref": "pane:2",
                        "surface_ref": "surface:2",
                    }
                ],
            },
        )

        materialize_live_workflow_log(runtime_dir)
        summary_one = json.loads((runtime_dir / DEFAULT_LIVE_SUMMARY_NAME).read_text(encoding="utf-8"))
        assert summary_one["task_date"] == "2026-04-19"
        assert summary_one["assignment_id"] == "P10-PHASE0A-ISSUE16-PM"
        assert summary_one["task_run_number"] == 1
        archive_one = Path(summary_one["archive_bundle_dir"])
        assert archive_one.name == "run-001"

        materialize_live_workflow_log(runtime_dir)
        summary_same_run = json.loads((runtime_dir / DEFAULT_LIVE_SUMMARY_NAME).read_text(encoding="utf-8"))
        assert summary_same_run["task_run_number"] == 1
        assert summary_same_run["archive_bundle_dir"] == str(archive_one)

        write_json(
            assignment_path,
            {
                "ready": True,
                "dispatch_ready": True,
                "runtime_status": "running",
                "updated_at": "2026-04-19T12:00:00+0800",
                "assignments": [
                    {
                        "logical_target": "pm-bot",
                        "bot_name": "pm-bot",
                        "assignment_id": "P10-PHASE0A-ISSUE16-PM",
                        "status": "ACTIVE",
                        "title": "Freeze scope retry",
                        "goal": "Freeze round scope again",
                        "workspace_ref": "workspace:1",
                        "pane_ref": "pane:2",
                        "surface_ref": "surface:2",
                    }
                ],
            },
        )
        materialize_live_workflow_log(runtime_dir)
        summary_two = json.loads((runtime_dir / DEFAULT_LIVE_SUMMARY_NAME).read_text(encoding="utf-8"))
        assert summary_two["task_run_number"] == 2
        archive_two = Path(summary_two["archive_bundle_dir"])
        assert archive_two.name == "run-002"
        assert archive_two.parent.name == "P10-PHASE0A-ISSUE16-PM"


def test_live_summary_marks_direct_reject_as_failed_even_with_closure_evidence() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        runtime_dir = Path(tmpdir)
        cycle_id = "workbot|2026-04-19T13:10:00+0800|PM-101"
        write_json(
            runtime_dir / "cmux-assignment.json",
            {
                "ready": True,
                "dispatch_ready": True,
                "runtime_status": "idle",
                "cycle_id": cycle_id,
                "updated_at": "2026-04-19T13:10:00+0800",
                "current_task_sources": [
                    current_cmux_task_source(
                        assignment_id="PM-101",
                        cycle_id=cycle_id,
                        runtime_dir=runtime_dir,
                    )
                ],
                "assignments": [],
            },
        )
        (runtime_dir / "cmux-main-thread-actions.jsonl").write_text(
            "\n".join(
                [
                    json.dumps(
                        {
                            "schema_version": "wb-cmux-main-thread-action-v1",
                            "at": "2026-04-19T13:11:00+0800",
                            "actor": "main-thread",
                            "phase": "A8",
                            "kind": "main_thread_review",
                            "logical_target": "pm-bot",
                            "assignment_id": "PM-101",
                            "task_source_ref": current_cmux_task_source(
                                assignment_id="PM-101",
                                cycle_id=cycle_id,
                                runtime_dir=runtime_dir,
                            ),
                            "summary": "main-thread decision recorded",
                            "details": {
                                "decision": "direct_reject",
                                "reason": "evidence packet contradicts baseline",
                            },
                        },
                        ensure_ascii=False,
                    ),
                    json.dumps(
                        {
                            "schema_version": "wb-cmux-main-thread-action-v1",
                            "at": "2026-04-19T13:12:00+0800",
                            "actor": "main-thread",
                            "phase": "A9",
                            "kind": "main_thread_closure",
                            "logical_target": "pm-bot",
                            "assignment_id": "PM-101",
                            "task_source_ref": current_cmux_task_source(
                                assignment_id="PM-101",
                                cycle_id=cycle_id,
                                runtime_dir=runtime_dir,
                            ),
                            "summary": "main-thread closed this rejected attempt",
                        },
                        ensure_ascii=False,
                    ),
                ]
            )
            + "\n",
            encoding="utf-8",
        )

        materialize_live_workflow_log(runtime_dir)
        summary = json.loads((runtime_dir / DEFAULT_LIVE_SUMMARY_NAME).read_text(encoding="utf-8"))

        assert summary["current_phase"] == "A9"
        assert summary["status"] == "failed"
        assert summary["outcome"] == "direct_reject"
        assert summary["native_pass"] is False
        assert summary["direct_reject_count"] == 1
        assert summary["direct_reject_details"][0]["reason"] == "evidence packet contradicts baseline"


def test_explicit_direct_reject_invalidates_same_attempt_acceptance_and_closure() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        runtime_dir = Path(tmpdir)
        cycle_id = "workbot|2026-04-19T13:41:00+0800|PM-101"
        write_json(
            runtime_dir / "cmux-assignment.json",
            {
                "ready": True,
                "dispatch_ready": True,
                "runtime_status": "idle",
                "cycle_id": cycle_id,
                "updated_at": "2026-04-19T13:40:00+0800",
                "current_task_sources": [
                    current_cmux_task_source(
                        assignment_id="PM-101",
                        cycle_id=cycle_id,
                        runtime_dir=runtime_dir,
                    )
                ],
                "assignments": [],
            },
        )
        write_json(
            runtime_dir / "cmux-consumer-state-latest.json",
            {
                "schema_version": "wb-cmux-consumer-state-v1",
                "assignments": {
                    "pm-bot": {
                        "assignment_id": "PM-101",
                        "state": "completed",
                        "control_packet": {
                            "task_id": "PM-101",
                            "state": "completed",
                            "result": "pass",
                        },
                    }
                },
            },
        )
        (runtime_dir / "cmux-finish-receipts.jsonl").write_text(
            json.dumps(
                {
                    "cycle_id": cycle_id,
                    "task_sources": [
                        current_cmux_task_source(
                            assignment_id="PM-101",
                            cycle_id=cycle_id,
                            runtime_dir=runtime_dir,
                        )
                    ],
                    "outcomes": [
                        {
                            "assignment_id": "PM-101",
                            "logical_target": "pm-bot",
                            "task_id": "PM-101",
                            "status": "pm_completed",
                            "summary": "packet writeback completed",
                            "task_source_ref": current_cmux_task_source(
                                assignment_id="PM-101",
                                cycle_id=cycle_id,
                                runtime_dir=runtime_dir,
                            ),
                        }
                    ],
                },
                ensure_ascii=False,
            )
            + "\n",
            encoding="utf-8",
        )
        (runtime_dir / "cmux-main-thread-actions.jsonl").write_text(
            "\n".join(
                [
                    json.dumps(
                        {
                            "schema_version": "wb-cmux-main-thread-action-v1",
                            "at": "2026-04-19T13:42:00+0800",
                            "actor": "main-thread",
                            "phase": "A8",
                            "kind": "main_thread_acceptance",
                            "logical_target": "pm-bot",
                            "assignment_id": "PM-101",
                            "task_source_ref": current_cmux_task_source(
                                assignment_id="PM-101",
                                cycle_id=cycle_id,
                                runtime_dir=runtime_dir,
                            ),
                            "summary": "main-thread accepted the pm-bot delivery packet",
                        },
                        ensure_ascii=False,
                    ),
                    json.dumps(
                        {
                            "schema_version": "wb-cmux-main-thread-action-v1",
                            "at": "2026-04-19T13:43:00+0800",
                            "actor": "main-thread",
                            "phase": "A9",
                            "kind": "main_thread_direct_reject",
                            "logical_target": "pm-bot",
                            "assignment_id": "PM-101",
                            "task_source_ref": current_cmux_task_source(
                                assignment_id="PM-101",
                                cycle_id=cycle_id,
                                runtime_dir=runtime_dir,
                            ),
                            "summary": "main-thread rejected this attempt after full evidence review",
                            "details": {
                                "decision": "direct_reject",
                                "reason": "same-attempt acceptance is void once the run is rejected",
                            },
                        },
                        ensure_ascii=False,
                    ),
                    json.dumps(
                        {
                            "schema_version": "wb-cmux-main-thread-action-v1",
                            "at": "2026-04-19T13:44:00+0800",
                            "actor": "main-thread",
                            "phase": "A9",
                            "kind": "main_thread_closure",
                            "logical_target": "pm-bot",
                            "assignment_id": "PM-101",
                            "task_source_ref": current_cmux_task_source(
                                assignment_id="PM-101",
                                cycle_id=cycle_id,
                                runtime_dir=runtime_dir,
                            ),
                            "summary": "main-thread closed the rejected attempt",
                        },
                        ensure_ascii=False,
                    ),
                ]
            )
            + "\n",
            encoding="utf-8",
        )

        materialize_live_workflow_log(runtime_dir)

        log_payload = json.loads((runtime_dir / DEFAULT_LIVE_JSON_NAME).read_text(encoding="utf-8"))
        summary = json.loads((runtime_dir / DEFAULT_LIVE_SUMMARY_NAME).read_text(encoding="utf-8"))
        journal_lines = [
            json.loads(line)
            for line in (runtime_dir / "cmux-main-thread-actions.jsonl").read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]

        assert log_payload["summary"]["main_thread_acceptance_evidenced"] is False
        assert log_payload["summary"]["main_thread_closure_evidenced"] is False
        assert log_payload["summary"]["direct_reject_count"] == 1
        assert log_payload["summary"]["main_thread_action_count"] == 1
        assert log_payload["verification_packet"]["missing_slots"] == ["control_packet"]
        assert any("cannot coexist with reject" in warning for warning in log_payload["warnings"])
        assert any("invalid same-attempt coexistence" in warning for warning in log_payload["warnings"])
        assert journal_lines[1]["kind"] == "main_thread_direct_reject"
        assert summary["status"] == "failed"
        assert summary["outcome"] == "direct_reject"
        assert summary["native_pass"] is False
        assert summary["legal_verdict"] == "direct_reject"
        assert summary["missing_evidence"] == []
        assert summary["direct_reject_details"][0]["kind"] == "main_thread_direct_reject"
        assert summary["direct_reject_details"][0]["reason"] == "same-attempt acceptance is void once the run is rejected"


def test_live_summary_keeps_closure_blocked_when_hard_gaps_exist() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        runtime_dir = Path(tmpdir)
        cycle_id = "workbot|2026-04-19T13:20:00+0800|PM-101"
        write_json(
            runtime_dir / "cmux-assignment.json",
            {
                "ready": True,
                "dispatch_ready": True,
                "runtime_status": "idle",
                "cycle_id": cycle_id,
                "updated_at": "2026-04-19T13:20:00+0800",
                "current_task_sources": [
                    current_cmux_task_source(
                        assignment_id="PM-101",
                        cycle_id=cycle_id,
                        runtime_dir=runtime_dir,
                    )
                ],
                "assignments": [],
            },
        )
        write_json(
            runtime_dir / "hook-state.json",
            {
                "surfaces": {
                    "surface:2": {
                        "adhoc_prompt_count": 2,
                        "prompt_submit_count": 0,
                        "stop_count": 0,
                        "notification_count": 0,
                    }
                }
            },
        )
        (runtime_dir / "cmux-main-thread-actions.jsonl").write_text(
            json.dumps(
                {
                    "schema_version": "wb-cmux-main-thread-action-v1",
                    "at": "2026-04-19T13:21:00+0800",
                    "actor": "main-thread",
                    "phase": "A9",
                    "kind": "main_thread_closure",
                    "assignment_id": "PM-101",
                    "task_source_ref": current_cmux_task_source(
                        assignment_id="PM-101",
                        cycle_id=cycle_id,
                        runtime_dir=runtime_dir,
                    ),
                    "summary": "closure recorded before evidence chain completed",
                },
                ensure_ascii=False,
            )
            + "\n",
            encoding="utf-8",
        )

        materialize_live_workflow_log(runtime_dir)
        summary = json.loads((runtime_dir / DEFAULT_LIVE_SUMMARY_NAME).read_text(encoding="utf-8"))

        assert summary["current_phase"] == "A9"
        assert summary["status"] == "blocked"
        assert summary["outcome"] == "closure_blocked_by_hard_gaps"
        assert summary["native_pass"] is False
        assert "hook provenance clean state" in summary["missing_evidence"]
        assert "hook provenance violation" in summary["hard_gap_reasons"]


def test_verification_packet_keeps_control_slot_missing_without_embedded_packet() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        runtime_dir = Path(tmpdir)
        write_json(
            runtime_dir / "cmux-assignment.json",
            {
                "ready": True,
                "dispatch_ready": True,
                "runtime_status": "idle",
                "updated_at": "2026-04-19T13:50:00+0800",
                "assignments": [],
            },
        )
        write_json(
            runtime_dir / "cmux-consumer-state-latest.json",
            {
                "schema_version": "wb-cmux-consumer-state-v1",
                "assignments": {
                    "pm-bot": {
                        "assignment_id": "PM-101",
                        "state": "completed",
                        "runtime_summary": "worker summary without embedded control packet",
                    }
                },
            },
        )
        (runtime_dir / "cmux-finish-receipts.jsonl").write_text(
            json.dumps({"cycle_id": "workbot|2026-04-19T13:51:00+0800|pm-101"}, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        (runtime_dir / "cmux-main-thread-actions.jsonl").write_text(
            json.dumps(
                {
                    "schema_version": "wb-cmux-main-thread-action-v1",
                    "at": "2026-04-19T13:52:00+0800",
                    "actor": "main-thread",
                    "phase": "A8",
                    "kind": "main_thread_acceptance",
                    "summary": "main-thread accepted the available finish receipt",
                },
                ensure_ascii=False,
            )
            + "\n",
            encoding="utf-8",
        )

        payload = build_live_workflow_log(runtime_dir)

        assert payload["summary"]["consumer_state_present"] is True
        assert payload["verification_packet"]["read_order"] == [
            {
                "slot": "consumer_state",
                "path": str((runtime_dir / "cmux-consumer-state-latest.json").resolve()),
                "via_rule": "consumer_state",
            },
            {
                "slot": "finish_receipt",
                "path": str((runtime_dir / "cmux-finish-receipts.jsonl").resolve()),
                "via_rule": "finish_receipt_journal",
            },
            {
                "slot": "workflow_log",
                "path": str((runtime_dir / DEFAULT_LIVE_JSON_NAME).resolve()),
                "via_rule": "workflow_log",
            },
            {
                "slot": "main_thread_actions",
                "path": str((runtime_dir / "cmux-main-thread-actions.jsonl").resolve()),
                "via_rule": "main_thread_action_journal",
            },
        ]
        assert all(item["slot"] != "control_packet" for item in payload["verification_packet"]["read_order"])
        assert payload["verification_packet"]["missing_slots"] == ["control_packet"]


def test_live_workflow_log_ignores_archive_only_embedded_consumer_packet() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        runtime_dir = Path(tmpdir)
        current_cycle_id = "workbot|2026-04-21T19:44:33+0800|PM-RT4"
        current_task_source = current_cmux_task_source(
            assignment_id="PM-RT4",
            cycle_id=current_cycle_id,
            runtime_dir=runtime_dir,
            status="active",
            deliverable_path="/Users/busiji/workbot/workspace/projects/sample/current-task.md",
        )
        write_json(
            runtime_dir / "cmux-assignment.json",
            {
                "ready": True,
                "dispatch_ready": True,
                "runtime_status": "running",
                "cycle_id": current_cycle_id,
                "updated_at": "2026-04-21T19:44:33+0800",
                "current_task_sources": [current_task_source],
                "assignments": [
                    {
                        "logical_target": "pm-bot",
                        "bot_name": "pm-bot",
                        "assignment_id": "PM-RT4",
                        "status": "ACTIVE",
                        "deliverable": "/Users/busiji/workbot/workspace/projects/sample/current-task.md",
                        "task_source_ref": current_task_source,
                        "title": "Freeze scope",
                        "goal": "Freeze round scope",
                        "workspace_ref": "workspace:1",
                        "pane_ref": "pane:2",
                        "surface_ref": "surface:2",
                    }
                ],
            },
        )
        stale_packet = dict(EXAMPLE_PACKETS["completed"])
        stale_packet["assignment_id"] = "PM-RT3"
        stale_packet["artifact_path"] = str((runtime_dir / "pm-bot-summary-rt3.json").resolve())
        stale_packet["task_source_ref"] = current_cmux_task_source(
            assignment_id="PM-RT3",
            cycle_id="workbot|2026-04-21T17:30:40+0800|PM-RT3",
            runtime_dir=runtime_dir,
            status="active",
            deliverable_path="/Users/busiji/workbot/workspace/projects/sample/current-task.md",
        )
        stale_packet["task_source_ref"]["evidence_path"] = stale_packet["artifact_path"]
        write_json(
            runtime_dir / "cmux-consumer-state-latest.json",
            {
                "schema_version": "wb-cmux-consumer-state-v1",
                "assignments": {
                    "pm-bot": {
                        "assignment_id": "PM-RT4",
                        "state": "audit_pending",
                        "state_source": "control_packet",
                        "control_packet": stale_packet,
                    }
                },
            },
        )

        payload = build_live_workflow_log(runtime_dir)

        assert all(
            item.get("reason") != "completed_control_packet_requires_finish_cycle"
            for item in payload["pending_handoffs"]
        )
        assert all(
            event.get("kind") != "control_packet_completed" for event in payload["events"]
        )
        assert any(
            "archive-only consumer control packet" in warning for warning in payload["warnings"]
        )
        assert payload["summary"]["archive_only_consumer_control_packet_count"] == 1


def test_live_workflow_log_ignores_standalone_packet_when_linked_summary_cycle_is_stale() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        runtime_dir = Path(tmpdir)
        current_cycle_id = "workbot|2026-04-21T19:44:33+0800|PM-RT4"
        summary_path = runtime_dir / "pm-bot-summary.json"
        current_task_source = build_cmux_task_source_ref(
            assignment_id="PM-RT4",
            cycle_id=current_cycle_id,
            deliverable_path="/Users/busiji/workbot/workspace/projects/sample/current-task.md",
            evidence_path=str(summary_path),
            status="active",
        )
        write_json(
            runtime_dir / "cmux-assignment.json",
            {
                "ready": True,
                "dispatch_ready": True,
                "runtime_status": "running",
                "cycle_id": current_cycle_id,
                "updated_at": "2026-04-21T19:44:33+0800",
                "current_task_sources": [current_task_source],
                "assignments": [
                    {
                        "logical_target": "pm-bot",
                        "bot_name": "pm-bot",
                        "assignment_id": "PM-RT4",
                        "status": "ACTIVE",
                        "deliverable": "/Users/busiji/workbot/workspace/projects/sample/current-task.md",
                        "task_source_ref": current_task_source,
                        "title": "Freeze scope",
                        "goal": "Freeze round scope",
                        "workspace_ref": "workspace:1",
                        "pane_ref": "pane:2",
                        "surface_ref": "surface:2",
                    }
                ],
            },
        )
        packet = dict(EXAMPLE_PACKETS["completed"])
        packet["assignment_id"] = "PM-RT4"
        packet["logical_target"] = "pm-bot"
        packet["artifact_path"] = str(summary_path)
        packet["task_source_ref"] = dict(current_task_source)
        write_json(runtime_dir / "pm-bot-control-packet.json", packet)

        stale_summary = dict(packet)
        stale_summary["task_source_ref"] = build_cmux_task_source_ref(
            assignment_id="PM-RT4",
            cycle_id="workbot|2026-04-21T19:35:23+0800|PM-RT4",
            deliverable_path=current_task_source["deliverable_path"],
            evidence_path=str(summary_path),
            status="active",
        )
        write_json(summary_path, stale_summary)

        payload = build_live_workflow_log(runtime_dir)

        assert all(
            item.get("slot") != "control_packet"
            for item in payload["verification_packet"]["read_order"]
        )
        assert any(
            "archive-only control packet artifacts" in warning
            for warning in payload["warnings"]
        )


def test_live_workflow_log_accepts_standalone_packet_when_linked_summary_matches_current_task_source() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        runtime_dir = Path(tmpdir)
        current_cycle_id = "workbot|2026-04-21T23:42:22+0800|PM-RT5"
        summary_path = runtime_dir / "pm-bot-summary.json"
        current_task_source = build_cmux_task_source_ref(
            assignment_id="PM-RT5",
            cycle_id=current_cycle_id,
            deliverable_path="/Users/busiji/workbot/workspace/projects/sample/current-task.md",
            evidence_path=str(summary_path),
            status="active",
        )
        write_json(
            runtime_dir / "cmux-assignment.json",
            {
                "ready": True,
                "dispatch_ready": True,
                "runtime_status": "running",
                "cycle_id": current_cycle_id,
                "updated_at": "2026-04-21T23:42:22+0800",
                "current_task_sources": [current_task_source],
                "assignments": [
                    {
                        "logical_target": "pm-bot",
                        "bot_name": "pm-bot",
                        "assignment_id": "PM-RT5",
                        "status": "ACTIVE",
                        "deliverable": "/Users/busiji/workbot/workspace/projects/sample/current-task.md",
                        "task_source_ref": current_task_source,
                        "title": "Freeze scope",
                        "goal": "Freeze round scope",
                        "workspace_ref": "workspace:1",
                        "pane_ref": "pane:2",
                        "surface_ref": "surface:2",
                    }
                ],
            },
        )
        packet = dict(EXAMPLE_PACKETS["completed"])
        packet["assignment_id"] = "PM-RT5"
        packet["task_id"] = "PM-005"
        packet["logical_target"] = "pm-bot"
        packet["marker"] = "XCP14PMR1:"
        packet["artifact_path"] = str(summary_path)
        packet["task_source_ref"] = dict(current_task_source)
        write_json(runtime_dir / "pm-bot-control-packet.json", packet)
        write_json(
            summary_path,
            {
                "schema_version": "wb-pm-bot-summary-v1",
                "assignment_id": "PM-RT5",
                "task_id": "PM-005",
                "cycle_id": current_cycle_id,
                "task_source_ref": current_task_source,
                "result": "completed",
                "summary": "current linked summary",
            },
        )

        payload = build_live_workflow_log(runtime_dir)

        assert any(
            item.get("slot") == "control_packet"
            and item.get("path") == str((runtime_dir / "pm-bot-control-packet.json").resolve())
            for item in payload["verification_packet"]["read_order"]
        )
        assert "control_packet" not in payload["verification_packet"]["missing_slots"]
        assert str((runtime_dir / "pm-bot-control-packet.json").resolve()) in payload["sources"]["control_packet_artifacts"]


def test_live_summary_keeps_direct_reject_terminal_even_with_pending_handoff() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        runtime_dir = Path(tmpdir)
        cycle_id = "workbot|2026-04-19T13:30:00+0800|PM-101"
        write_json(
            runtime_dir / "cmux-assignment.json",
            {
                "ready": True,
                "dispatch_ready": True,
                "runtime_status": "running",
                "cycle_id": cycle_id,
                "updated_at": "2026-04-19T13:30:00+0800",
                "assignments": [
                    {
                        "logical_target": "pm-bot",
                        "bot_name": "pm-bot",
                        "assignment_id": "PM-101",
                        "status": "ACTIVE",
                        "deliverable": "/Users/busiji/workbot/workspace/projects/sample/current-task.md",
                        "task_source_ref": current_cmux_task_source(
                            assignment_id="PM-101",
                            cycle_id=cycle_id,
                            runtime_dir=runtime_dir,
                            status="active",
                        ),
                        "title": "Freeze scope",
                        "goal": "Freeze round scope",
                        "workspace_ref": "workspace:1",
                        "pane_ref": "pane:2",
                        "surface_ref": "surface:2",
                    }
                ],
            },
        )
        write_json(
            runtime_dir / "hook-state.json",
            {
                "surfaces": {
                    "surface:2": {
                        "prompt_submit_count": 1,
                        "last_prompt_submit_at": "2026-04-19T13:30:00+0800",
                        "stop_count": 1,
                        "last_stop_at": "2026-04-19T13:31:00+0800",
                        "notification_count": 1,
                        "last_notification_at": "2026-04-19T13:32:00+0800",
                        "last_event": "notification",
                        "adhoc_prompt_count": 0,
                    }
                }
            },
        )
        (runtime_dir / "cmux-main-thread-actions.jsonl").write_text(
            json.dumps(
                {
                    "schema_version": "wb-cmux-main-thread-action-v1",
                    "at": "2026-04-19T13:33:00+0800",
                    "actor": "main-thread",
                    "phase": "A9",
                    "kind": "main_thread_direct_reject",
                    "assignment_id": "PM-101",
                    "task_source_ref": current_cmux_task_source(
                        assignment_id="PM-101",
                        cycle_id=cycle_id,
                        runtime_dir=runtime_dir,
                    ),
                    "summary": "main-thread rejected this run after strict review",
                    "details": {
                        "decision": "direct_reject",
                        "reason": "strict gate failed on control packet legality",
                    },
                },
                ensure_ascii=False,
            )
            + "\n",
            encoding="utf-8",
        )

        materialize_live_workflow_log(runtime_dir)
        summary = json.loads((runtime_dir / DEFAULT_LIVE_SUMMARY_NAME).read_text(encoding="utf-8"))

        assert summary["current_phase"] == "A9"
        assert summary["status"] == "failed"
        assert summary["outcome"] == "direct_reject"
        assert "terminal" in summary["next_action"]
        assert "rejected" in summary["summary_lines"][0]


def test_live_summary_blocks_a8_until_all_required_a7_targets_exist() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        runtime_dir = Path(tmpdir)
        cycle_id = "workbot|2026-04-19T13:41:00+0800|PM-101,DEV-101,QA-101,DOC-101,REA-101"
        write_json(
            runtime_dir / "cmux-assignment.json",
            {
                "ready": True,
                "dispatch_ready": True,
                "runtime_status": "idle",
                "cycle_id": cycle_id,
                "updated_at": "2026-04-19T13:40:00+0800",
                "current_task_sources": [
                    current_cmux_task_source(
                        assignment_id="pm-101",
                        cycle_id=cycle_id,
                        runtime_dir=runtime_dir,
                    )
                ],
                "assignments": [],
            },
        )
        (runtime_dir / "cmux-finish-receipts.jsonl").write_text(
            json.dumps(
                {
                    "cycle_id": cycle_id,
                    "task_sources": [
                        current_cmux_task_source(
                            assignment_id="pm-101",
                            cycle_id=cycle_id,
                            runtime_dir=runtime_dir,
                        )
                    ],
                    "outcomes": [
                        {
                            "assignment_id": "pm-101",
                            "logical_target": "pm-bot",
                            "task_id": "PM-101",
                            "prefix": "PM",
                            "status": "pm_completed",
                            "summary": "pm writeback complete",
                            "task_source_ref": current_cmux_task_source(
                                assignment_id="pm-101",
                                cycle_id=cycle_id,
                                runtime_dir=runtime_dir,
                            ),
                        }
                    ],
                },
                ensure_ascii=False,
            )
            + "\n",
            encoding="utf-8",
        )

        materialize_live_workflow_log(runtime_dir)
        summary = json.loads((runtime_dir / DEFAULT_LIVE_SUMMARY_NAME).read_text(encoding="utf-8"))

        assert summary["current_phase"] == "A7"
        assert summary["status"] == "blocked"
        assert summary["outcome"] == "a7_partial_writeback"
        assert summary["a7_writeback_complete"] is False
        assert summary["a7_missing_writeback_targets"] == [
            "dev-bot",
            "qa-bot",
            "doc-bot",
            "rea-bot",
        ]
        assert "partial" in summary["next_action"]


def test_live_summary_accepts_explicit_lane_scoped_single_target_a7_receipt() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        runtime_dir = Path(tmpdir)
        scoped_cycle_id = (
            "workbot|2026-04-21T09:25:27+0800|"
            "P14-PMBOT-R1-HOMEPAGE-INVENTORY,idle-dev-bot,idle-qa-bot,idle-doc-bot,idle-rea-bot"
        )
        receipt_cycle_id = "workbot|2026-04-21T09:30:40+0800|P14-PMBOT-R1-HOMEPAGE-INVENTORY"
        write_json(
            runtime_dir / "cmux-assignment.json",
            {
                "ready": True,
                "dispatch_ready": True,
                "runtime_status": "idle",
                "cycle_id": receipt_cycle_id,
                "updated_at": "2026-04-21T09:41:06+0800",
                "current_task_sources": [
                    current_cmux_task_source(
                        assignment_id="P14-PMBOT-R1-HOMEPAGE-INVENTORY",
                        cycle_id=scoped_cycle_id,
                        runtime_dir=runtime_dir,
                    )
                ],
                "assignments": [],
            },
        )
        packet = dict(EXAMPLE_PACKETS["completed"])
        packet["assignment_id"] = "P14-PMBOT-R1-HOMEPAGE-INVENTORY"
        packet["artifact_path"] = str((runtime_dir / "pm-bot-control-packet.json").resolve())
        packet["task_source_ref"] = current_cmux_task_source(
            assignment_id="P14-PMBOT-R1-HOMEPAGE-INVENTORY",
            cycle_id=scoped_cycle_id,
            runtime_dir=runtime_dir,
        )
        packet["task_source_ref"]["evidence_path"] = str((runtime_dir / "pm-bot-control-packet.json").resolve())
        write_json(runtime_dir / "pm-bot-control-packet.json", packet)
        write_json(
            runtime_dir / "cmux-consumer-state-latest.json",
            {
                "schema_version": "wb-cmux-consumer-state-v1",
                "assignments": {
                    "pm-bot": {
                        "assignment_id": "P14-PMBOT-R1-HOMEPAGE-INVENTORY",
                        "state": "completed",
                        "control_packet": packet,
                    }
                },
            },
        )
        (runtime_dir / "cmux-finish-receipts.jsonl").write_text(
            json.dumps(
                {
                    "cycle_id": receipt_cycle_id,
                    "task_sources": [
                        current_cmux_task_source(
                            assignment_id="P14-PMBOT-R1-HOMEPAGE-INVENTORY",
                            cycle_id=scoped_cycle_id,
                            runtime_dir=runtime_dir,
                        )
                    ],
                    "outcomes": [
                        {
                            "assignment_id": "P14-PMBOT-R1-HOMEPAGE-INVENTORY",
                            "logical_target": "pm-bot",
                            "task_id": "PM-001",
                            "status": "pm_ready",
                            "summary": "pm writeback complete",
                            "task_source_ref": current_cmux_task_source(
                                assignment_id="P14-PMBOT-R1-HOMEPAGE-INVENTORY",
                                cycle_id=scoped_cycle_id,
                                runtime_dir=runtime_dir,
                            ),
                        }
                    ],
                },
                ensure_ascii=False,
            )
            + "\n",
            encoding="utf-8",
        )

        payload = build_live_workflow_log(runtime_dir)
        materialize_live_workflow_log(runtime_dir)
        summary = json.loads((runtime_dir / DEFAULT_LIVE_SUMMARY_NAME).read_text(encoding="utf-8"))

        assert payload["summary"]["a7_required_writeback_targets"] == ["pm-bot"]
        assert payload["summary"]["a7_present_writeback_targets"] == ["pm-bot"]
        assert payload["summary"]["a7_missing_writeback_targets"] == []
        assert payload["summary"]["a7_writeback_complete"] is True
        assert summary["current_phase"] == "A8"
        assert summary["status"] == "blocked"
        assert summary["outcome"] == "awaiting_main_thread_acceptance"
        assert summary["a7_writeback_complete"] is True
        assert summary["a7_missing_writeback_targets"] == []


def test_live_summary_uses_current_task_sources_for_three_target_a7_scope() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        runtime_dir = Path(tmpdir)
        scoped_cycle_id = "workbot|2026-04-21T10:00:00+0800|PM-301,DEV-301,QA-301,idle-doc-bot,idle-rea-bot"
        receipt_cycle_id = "workbot|2026-04-21T10:05:00+0800|three-bot-batch"
        current_sources = [
            current_cmux_task_source(assignment_id="PM-301", cycle_id=scoped_cycle_id, runtime_dir=runtime_dir),
            current_cmux_task_source(assignment_id="DEV-301", cycle_id=scoped_cycle_id, runtime_dir=runtime_dir),
            current_cmux_task_source(assignment_id="QA-301", cycle_id=scoped_cycle_id, runtime_dir=runtime_dir),
        ]
        write_json(
            runtime_dir / "cmux-assignment.json",
            {
                "ready": True,
                "dispatch_ready": True,
                "runtime_status": "idle",
                "cycle_id": receipt_cycle_id,
                "updated_at": "2026-04-21T10:06:00+0800",
                "current_task_sources": current_sources,
                "assignments": [],
            },
        )
        (runtime_dir / "cmux-finish-receipts.jsonl").write_text(
            json.dumps(
                {
                    "cycle_id": receipt_cycle_id,
                    "task_sources": current_sources,
                    "outcomes": [
                        {
                            "assignment_id": "PM-301",
                            "logical_target": "pm-bot",
                            "task_id": "PM-301",
                            "status": "pm_ready",
                            "task_source_ref": current_sources[0],
                        },
                        {
                            "assignment_id": "DEV-301",
                            "logical_target": "dev-bot",
                            "task_id": "DEV-301",
                            "status": "dev_ready",
                            "task_source_ref": current_sources[1],
                        },
                        {
                            "assignment_id": "QA-301",
                            "logical_target": "qa-bot",
                            "task_id": "QA-301",
                            "status": "qa_ready",
                            "task_source_ref": current_sources[2],
                        },
                    ],
                },
                ensure_ascii=False,
            )
            + "\n",
            encoding="utf-8",
        )

        payload = build_live_workflow_log(runtime_dir)

        assert payload["summary"]["a7_required_writeback_targets"] == ["pm-bot", "dev-bot", "qa-bot"]
        assert payload["summary"]["a7_present_writeback_targets"] == ["pm-bot", "dev-bot", "qa-bot"]
        assert payload["summary"]["a7_missing_writeback_targets"] == []
        assert payload["summary"]["a7_writeback_complete"] is True


def test_live_summary_fails_closed_when_a7_scope_cannot_be_confirmed() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        runtime_dir = Path(tmpdir)
        cycle_id = "workbot|2026-04-21T10:30:00+0800|task-401"
        task_source = current_cmux_task_source(
            assignment_id="TASK-401",
            cycle_id=cycle_id,
            runtime_dir=runtime_dir,
        )
        write_json(
            runtime_dir / "cmux-assignment.json",
            {
                "ready": True,
                "dispatch_ready": True,
                "runtime_status": "idle",
                "cycle_id": cycle_id,
                "updated_at": "2026-04-21T10:31:00+0800",
                "current_task_sources": [task_source],
                "assignments": [],
            },
        )
        (runtime_dir / "cmux-finish-receipts.jsonl").write_text(
            json.dumps(
                {
                    "cycle_id": cycle_id,
                    "task_sources": [task_source],
                    "outcomes": [
                        {
                            "assignment_id": "TASK-401",
                            "task_id": "TASK-401",
                            "status": "completed",
                            "task_source_ref": task_source,
                        }
                    ],
                },
                ensure_ascii=False,
            )
            + "\n",
            encoding="utf-8",
        )

        payload = build_live_workflow_log(runtime_dir)
        materialize_live_workflow_log(runtime_dir)
        summary = json.loads((runtime_dir / DEFAULT_LIVE_SUMMARY_NAME).read_text(encoding="utf-8"))

        assert payload["summary"]["a7_required_writeback_targets"] == []
        assert payload["summary"]["a7_scope_confirmed"] is False
        assert payload["summary"]["a7_writeback_complete"] is False
        assert any("dispatch scope is unconfirmed" in warning for warning in payload["warnings"])
        assert summary["current_phase"] == "A7"
        assert summary["status"] == "blocked"
        assert summary["a7_scope_confirmed"] is False
        assert "A7 dispatch scope" in summary["missing_evidence"]


def test_live_summary_uses_latest_receipt_for_a7_completeness() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        runtime_dir = Path(tmpdir)
        partial_cycle_id = "workbot|2026-04-20T10:00:00+0800|PM-101,DEV-101,QA-101,DOC-201,REA-101"
        write_json(
            runtime_dir / "cmux-assignment.json",
            {
                "ready": True,
                "dispatch_ready": True,
                "runtime_status": "idle",
                "cycle_id": partial_cycle_id,
                "updated_at": "2026-04-19T13:50:00+0800",
                "current_task_sources": [
                    current_cmux_task_source(
                        assignment_id="DOC-201",
                        cycle_id=partial_cycle_id,
                        runtime_dir=runtime_dir,
                    )
                ],
                "assignments": [],
            },
        )
        write_json(runtime_dir / "pm-bot-control-packet.json", dict(EXAMPLE_PACKETS["completed"]))
        write_json(
            runtime_dir / "cmux-consumer-state-latest.json",
            {
                "schema_version": "wb-cmux-consumer-state-v1",
                "assignments": {
                    "doc-bot": {
                        "assignment_id": "DOC-201",
                        "state": "completed",
                        "control_packet": dict(EXAMPLE_PACKETS["completed"]),
                    }
                },
            },
        )
        full_receipt = {
            "cycle_id": "workbot|2026-04-19T13:51:00+0800|strict-gap-fix-full",
            "outcomes": [
                {"logical_target": "pm-bot", "task_id": "PM-101", "status": "pm_completed"},
                {"logical_target": "dev-bot", "task_id": "DEV-101", "status": "dev_completed"},
                {"logical_target": "qa-bot", "task_id": "QA-101", "status": "qa_completed"},
                {"logical_target": "doc-bot", "task_id": "DOC-101", "status": "doc_synced"},
                {"logical_target": "rea-bot", "task_id": "REA-101", "status": "rea_completed"},
            ],
        }
        partial_receipt = {
            "cycle_id": partial_cycle_id,
            "task_sources": [
                current_cmux_task_source(
                    assignment_id="DOC-201",
                    cycle_id=partial_cycle_id,
                    runtime_dir=runtime_dir,
                )
            ],
            "outcomes": [
                {
                    "assignment_id": "DOC-201",
                    "logical_target": "doc-bot",
                    "task_id": "DOC-201",
                    "status": "doc_synced",
                    "task_source_ref": current_cmux_task_source(
                        assignment_id="DOC-201",
                        cycle_id=partial_cycle_id,
                        runtime_dir=runtime_dir,
                    ),
                },
            ],
        }
        (runtime_dir / "cmux-finish-receipts.jsonl").write_text(
            json.dumps(full_receipt, ensure_ascii=False)
            + "\n"
            + json.dumps(partial_receipt, ensure_ascii=False)
            + "\n",
            encoding="utf-8",
        )

        payload = build_live_workflow_log(runtime_dir)
        summary = payload["summary"]

        assert summary["finish_receipt_count"] == 1
        assert summary["a7_evaluated_cycle_id"] == partial_receipt["cycle_id"]
        assert summary["a7_writeback_complete"] is False
        assert summary["a7_present_writeback_targets"] == ["doc-bot"]
        assert summary["a7_missing_writeback_targets"] == [
            "pm-bot",
            "dev-bot",
            "qa-bot",
            "rea-bot",
        ]


def test_live_summary_blocks_native_pass_without_final_reviewer_legality() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        runtime_dir = Path(tmpdir)
        write_native_pass_prerequisites(runtime_dir)
        cycle_id = "workbot|2026-04-19T13:51:00+0800|strict-gap-fix"
        (runtime_dir / "cmux-main-thread-actions.jsonl").write_text(
            "\n".join(
                [
                    json.dumps(
                        {
                            "schema_version": "wb-cmux-main-thread-action-v1",
                            "at": "2026-04-19T13:52:00+0800",
                            "actor": "main-thread",
                            "phase": "A8",
                            "kind": "main_thread_acceptance",
                            "assignment_id": "PM-101",
                            "task_source_ref": current_cmux_task_source(
                                assignment_id="PM-101",
                                cycle_id=cycle_id,
                                runtime_dir=runtime_dir,
                            ),
                            "summary": "main-thread accepted the frozen packet for closure review",
                        },
                        ensure_ascii=False,
                    ),
                    json.dumps(
                        {
                            "schema_version": "wb-cmux-main-thread-action-v1",
                            "at": "2026-04-19T13:53:00+0800",
                            "actor": "main-thread",
                            "phase": "A9",
                            "kind": "main_thread_closure",
                            "assignment_id": "PM-101",
                            "task_source_ref": current_cmux_task_source(
                                assignment_id="PM-101",
                                cycle_id=cycle_id,
                                runtime_dir=runtime_dir,
                            ),
                            "summary": "main-thread claims native pass without legal final reviewers",
                            "details": {
                                "result": "pass",
                                "frozen_packet_id": "strict-gap-fix-v1",
                                "final_reviewers": [
                                    {
                                        "reviewer": "qa-bot",
                                        "agent_id": "agent-qa-1",
                                        "fork_context": False,
                                        "frozen_packet_id": "strict-gap-fix-v1",
                                        "dispatch_transcript_path": "/tmp/review-dispatch-qa.md",
                                    }
                                ],
                            },
                        },
                        ensure_ascii=False,
                    ),
                ]
            )
            + "\n",
            encoding="utf-8",
        )

        materialize_live_workflow_log(runtime_dir)
        summary = json.loads((runtime_dir / DEFAULT_LIVE_SUMMARY_NAME).read_text(encoding="utf-8"))

        assert summary["current_phase"] == "A9"
        assert summary["status"] == "blocked"
        assert summary["outcome"] == "closure_blocked_by_final_reviewer_legality"
        assert summary["native_pass"] is False
        assert "final reviewer legality" in summary["missing_evidence"]
        assert "final reviewer legality" in summary["hard_gap_reasons"]
        assert summary["final_reviewer_legality_ok"] is False


def test_live_summary_allows_non_native_pass_acceptance_and_closure_after_lane_scoped_a7() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        runtime_dir = Path(tmpdir)
        cycle_id = "workbot|2026-04-21T09:25:27+0800|P14-PMBOT-R1-HOMEPAGE-INVENTORY,idle-dev-bot,idle-qa-bot,idle-doc-bot,idle-rea-bot"
        write_json(
            runtime_dir / "cmux-assignment.json",
            {
                "ready": True,
                "dispatch_ready": True,
                "runtime_status": "idle",
                "cycle_id": cycle_id,
                "updated_at": "2026-04-21T09:41:06+0800",
                "current_task_sources": [
                    current_cmux_task_source(
                        assignment_id="P14-PMBOT-R1-HOMEPAGE-INVENTORY",
                        cycle_id=cycle_id,
                        runtime_dir=runtime_dir,
                    )
                ],
                "assignments": [],
            },
        )
        packet = dict(EXAMPLE_PACKETS["completed"])
        packet["assignment_id"] = "P14-PMBOT-R1-HOMEPAGE-INVENTORY"
        packet["artifact_path"] = str((runtime_dir / "pm-bot-control-packet.json").resolve())
        packet["task_source_ref"] = current_cmux_task_source(
            assignment_id="P14-PMBOT-R1-HOMEPAGE-INVENTORY",
            cycle_id=cycle_id,
            runtime_dir=runtime_dir,
        )
        packet["task_source_ref"]["evidence_path"] = str((runtime_dir / "pm-bot-control-packet.json").resolve())
        write_json(runtime_dir / "pm-bot-control-packet.json", packet)
        write_json(
            runtime_dir / "cmux-consumer-state-latest.json",
            {
                "schema_version": "wb-cmux-consumer-state-v1",
                "assignments": {
                    "pm-bot": {
                        "assignment_id": "P14-PMBOT-R1-HOMEPAGE-INVENTORY",
                        "state": "completed",
                        "control_packet": packet,
                    }
                },
            },
        )
        (runtime_dir / "cmux-finish-receipts.jsonl").write_text(
            json.dumps(
                {
                    "cycle_id": cycle_id,
                    "task_sources": [
                        current_cmux_task_source(
                            assignment_id="P14-PMBOT-R1-HOMEPAGE-INVENTORY",
                            cycle_id=cycle_id,
                            runtime_dir=runtime_dir,
                        )
                    ],
                    "outcomes": [
                        {
                            "assignment_id": "P14-PMBOT-R1-HOMEPAGE-INVENTORY",
                            "logical_target": "pm-bot",
                            "task_id": "PM-001",
                            "status": "pm_ready",
                            "summary": "pm writeback complete",
                            "task_source_ref": current_cmux_task_source(
                                assignment_id="P14-PMBOT-R1-HOMEPAGE-INVENTORY",
                                cycle_id=cycle_id,
                                runtime_dir=runtime_dir,
                            ),
                        }
                    ],
                },
                ensure_ascii=False,
            )
            + "\n",
            encoding="utf-8",
        )
        (runtime_dir / "cmux-main-thread-actions.jsonl").write_text(
            "\n".join(
                [
                    json.dumps(
                        {
                            "schema_version": "wb-cmux-main-thread-action-v1",
                            "at": "2026-04-21T09:42:00+0800",
                            "actor": "main-thread",
                            "phase": "A8",
                            "kind": "main_thread_acceptance",
                            "logical_target": "pm-bot",
                            "assignment_id": "P14-PMBOT-R1-HOMEPAGE-INVENTORY",
                            "task_source_ref": current_cmux_task_source(
                                assignment_id="P14-PMBOT-R1-HOMEPAGE-INVENTORY",
                                cycle_id=cycle_id,
                                runtime_dir=runtime_dir,
                            ),
                            "summary": "main-thread accepted the pm-bot R1 receipt",
                            "details": {"cycle_id": cycle_id},
                        },
                        ensure_ascii=False,
                    ),
                    json.dumps(
                        {
                            "schema_version": "wb-cmux-main-thread-action-v1",
                            "at": "2026-04-21T09:43:00+0800",
                            "actor": "main-thread",
                            "phase": "A9",
                            "kind": "main_thread_closure",
                            "logical_target": "pm-bot",
                            "assignment_id": "P14-PMBOT-R1-HOMEPAGE-INVENTORY",
                            "task_source_ref": current_cmux_task_source(
                                assignment_id="P14-PMBOT-R1-HOMEPAGE-INVENTORY",
                                cycle_id=cycle_id,
                                runtime_dir=runtime_dir,
                            ),
                            "summary": "main-thread closed the R1 card after acceptance",
                            "details": {"cycle_id": cycle_id, "project_card_state": "Done"},
                        },
                        ensure_ascii=False,
                    ),
                ]
            )
            + "\n",
            encoding="utf-8",
        )

        materialize_live_workflow_log(runtime_dir)
        summary = json.loads((runtime_dir / DEFAULT_LIVE_SUMMARY_NAME).read_text(encoding="utf-8"))

        assert summary["current_phase"] == "A9"
        assert summary["status"] == "passed"
        assert summary["outcome"] == "accepted_and_closed"
        assert summary["native_pass"] is False
        assert summary["legal_verdict"] == "accepted"
        assert summary["main_thread_acceptance_evidenced"] is True
        assert summary["main_thread_closure_evidenced"] is True
        assert summary["missing_evidence"] == []


def test_live_summary_allows_native_pass_with_one_frozen_packet_and_three_reviewers() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        runtime_dir = Path(tmpdir)
        write_native_pass_prerequisites(runtime_dir)
        cycle_id = "workbot|2026-04-19T13:51:00+0800|strict-gap-fix"
        valid_reviewers = [
            {
                "reviewer": "qa-bot",
                "agent_id": "agent-qa-1",
                "fork_context": False,
                "frozen_packet_id": "strict-gap-fix-v2",
                "dispatch_transcript_path": "/tmp/review-dispatch-qa.md",
                "review_transcript_path": "/tmp/review-result-qa.md",
            },
            {
                "reviewer": "doc-bot",
                "agent_id": "agent-doc-1",
                "fork_context": False,
                "frozen_packet_id": "strict-gap-fix-v2",
                "dispatch_transcript_path": "/tmp/review-dispatch-doc.md",
                "review_transcript_path": "/tmp/review-result-doc.md",
            },
            {
                "reviewer": "rea-bot",
                "agent_id": "agent-rea-1",
                "fork_context": False,
                "frozen_packet_id": "strict-gap-fix-v2",
                "dispatch_transcript_path": "/tmp/review-dispatch-rea.md",
                "review_transcript_path": "/tmp/review-result-rea.md",
            },
        ]
        (runtime_dir / "cmux-main-thread-actions.jsonl").write_text(
            "\n".join(
                [
                    json.dumps(
                        {
                            "schema_version": "wb-cmux-main-thread-action-v1",
                            "at": "2026-04-19T13:52:00+0800",
                            "actor": "main-thread",
                            "phase": "A8",
                            "kind": "main_thread_acceptance",
                            "assignment_id": "PM-101",
                            "task_source_ref": current_cmux_task_source(
                                assignment_id="PM-101",
                                cycle_id=cycle_id,
                                runtime_dir=runtime_dir,
                            ),
                            "summary": "main-thread accepted the frozen packet for closure review",
                        },
                        ensure_ascii=False,
                    ),
                    json.dumps(
                        {
                            "schema_version": "wb-cmux-main-thread-action-v1",
                            "at": "2026-04-19T13:53:00+0800",
                            "actor": "main-thread",
                            "phase": "A9",
                            "kind": "main_thread_closure",
                            "assignment_id": "PM-101",
                            "task_source_ref": current_cmux_task_source(
                                assignment_id="PM-101",
                                cycle_id=cycle_id,
                                runtime_dir=runtime_dir,
                            ),
                            "summary": "main-thread closed the run with legal final-reviewer proof",
                            "details": {
                                "result": "native_pass",
                                "frozen_packet_id": "strict-gap-fix-v2",
                                "final_reviewers": valid_reviewers,
                            },
                        },
                        ensure_ascii=False,
                    ),
                ]
            )
            + "\n",
            encoding="utf-8",
        )

        materialize_live_workflow_log(runtime_dir)
        summary = json.loads((runtime_dir / DEFAULT_LIVE_SUMMARY_NAME).read_text(encoding="utf-8"))

        assert summary["current_phase"] == "A9"
        assert summary["status"] == "passed"
        assert summary["outcome"] == "native_pass"
        assert summary["native_pass"] is True
        assert summary["legal_verdict"] == "native_pass"
        assert summary["final_reviewer_legality_ok"] is True


def test_build_sample_three_round_five_bot_workflow_preserves_main_thread_closure() -> None:
    payload = build_sample_three_round_five_bot_workflow()
    assert payload["mode"] == "sample_three_round_five_bot"
    assert payload["summary"]["round_count"] == 3
    assert payload["summary"]["bot_count"] == 5
    assert payload["governance"]["closure_authority"] == "main-thread"
    assert len(payload["rounds"]) == 3
    assert all(len(round_payload["assignments"]) == 5 for round_payload in payload["rounds"])
    assert any(event["kind"] == "finish_cycle_local_writeback" for event in payload["events"])
    assert any(event["kind"] == "main_thread_acceptance" for event in payload["events"])
    assert payload["events"][-1]["kind"] == "main_thread_closure"
