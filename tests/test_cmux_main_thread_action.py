#!/usr/bin/env python3

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch


REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from workspace.tools import cmux_main_thread_action  # noqa: E402
from workspace.tools.current_task_source import build_cmux_task_source_ref  # noqa: E402


def write_json(path: Path, payload: dict[str, object]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def current_cmux_task_source(
    *,
    assignment_id: str,
    cycle_id: str,
    runtime_dir: Path,
) -> dict[str, str]:
    return build_cmux_task_source_ref(
        assignment_id=assignment_id,
        cycle_id=cycle_id,
        deliverable_path="/Users/busiji/workbot/workspace/projects/sample/current-task.md",
        evidence_path=str((runtime_dir / "cmux-assignment.json").resolve()),
        status="finished_local_writeback",
    )


def test_main_thread_action_script_appends_journal_and_refreshes_live_log() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        runtime_dir = Path(tmpdir)
        write_json(
            runtime_dir / "cmux-assignment.json",
            {
                "ready": True,
                "dispatch_ready": True,
                "runtime_status": "idle",
                "cycle_id": "workbot|2026-04-19T11:20:00+0800|PM-101",
                "updated_at": "2026-04-19T11:20:00+0800",
                "current_task_sources": [
                    current_cmux_task_source(
                        assignment_id="PM-101",
                        cycle_id="workbot|2026-04-19T11:20:00+0800|PM-101",
                        runtime_dir=runtime_dir,
                    )
                ],
                "assignments": [],
            },
        )
        args = [
            "cmux_main_thread_action.py",
            "--runtime-dir",
            str(runtime_dir),
            "--phase",
            "A9",
            "--kind",
            "main_thread_closure",
            "--summary",
            "main-thread closed the runtime after acceptance",
            "--logical-target",
            "pm-bot",
            "--assignment-id",
            "PM-101",
            "--details-json",
            "{\"result\":\"closed\"}",
        ]
        with patch.object(sys, "argv", args):
            exit_code = cmux_main_thread_action.main()

        assert exit_code == 0
        journal_path = runtime_dir / "cmux-main-thread-actions.jsonl"
        assert journal_path.exists()
        journal_lines = [line for line in journal_path.read_text(encoding="utf-8").splitlines() if line.strip()]
        assert len(journal_lines) == 1
        journal_payload = json.loads(journal_lines[0])
        assert journal_payload["kind"] == "main_thread_closure"
        assert journal_payload["phase"] == "A9"
        assert journal_payload["task_source_ref"]["task_source_id"] == "cmux:PM-101"
        assert journal_payload["details"]["result"] == "closed"

        live_log_path = runtime_dir / "cmux-full-workflow-log-latest.json"
        live_payload = json.loads(live_log_path.read_text(encoding="utf-8"))
        assert live_payload["summary"]["main_thread_closure_evidenced"] is True
        assert live_payload["events"][-1]["kind"] == "main_thread_closure"


def test_main_thread_action_script_rejects_native_pass_claim_without_legal_final_reviewers() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        runtime_dir = Path(tmpdir)
        write_json(
            runtime_dir / "cmux-assignment.json",
            {
                "ready": True,
                "dispatch_ready": True,
                "runtime_status": "idle",
                "cycle_id": "workbot|2026-04-19T11:20:00+0800|PM-101",
                "updated_at": "2026-04-19T11:20:00+0800",
                "current_task_sources": [
                    current_cmux_task_source(
                        assignment_id="PM-101",
                        cycle_id="workbot|2026-04-19T11:20:00+0800|PM-101",
                        runtime_dir=runtime_dir,
                    )
                ],
                "assignments": [],
            },
        )
        args = [
            "cmux_main_thread_action.py",
            "--runtime-dir",
            str(runtime_dir),
            "--phase",
            "A9",
            "--kind",
            "main_thread_closure",
            "--summary",
            "main-thread attempts native-pass closure without legal reviewers",
            "--details-json",
            "{\"result\":\"pass\",\"frozen_packet_id\":\"strict-gap-fix-v1\",\"final_reviewers\":[{\"reviewer\":\"qa-bot\",\"agent_id\":\"agent-qa-1\",\"fork_context\":false,\"frozen_packet_id\":\"strict-gap-fix-v1\",\"dispatch_transcript_path\":\"/tmp/dispatch-qa.md\"}]}",
        ]
        with patch.object(sys, "argv", args):
            try:
                cmux_main_thread_action.main()
            except ValueError as exc:
                assert "native-pass claim requires one frozen packet and 3 legal final reviewers" in str(exc)
            else:  # pragma: no cover - regression guard
                raise AssertionError("expected native-pass legality validation failure")
