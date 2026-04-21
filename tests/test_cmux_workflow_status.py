#!/usr/bin/env python3

from __future__ import annotations

import io
import json
import sys
import tempfile
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch


REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from workspace.tools import cmux_workflow_status  # noqa: E402


def write_json(path: Path, payload: dict[str, object]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def test_workflow_status_cli_prints_compact_status_and_archive_path() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        runtime_dir = Path(tmpdir)
        write_json(
            runtime_dir / "cmux-assignment.json",
            {
                "ready": True,
                "dispatch_ready": True,
                "runtime_status": "running",
                "updated_at": "2026-04-19T12:15:00+0800",
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
        buffer = io.StringIO()
        argv = ["cmux_workflow_status.py", "--runtime-dir", str(runtime_dir)]
        with patch.object(sys, "argv", argv), redirect_stdout(buffer):
            exit_code = cmux_workflow_status.main()

        assert exit_code == 0
        rendered = buffer.getvalue()
        assert "phase=A5 status=running" in rendered
        assert "task=P10-PHASE0A-ISSUE16-PM target=pm-bot active=1" in rendered
        assert "summary=" in rendered
        assert "detail=" in rendered
        assert "archive=" in rendered


def test_workflow_status_cli_keeps_direct_reject_terminal_language() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        runtime_dir = Path(tmpdir)
        write_json(
            runtime_dir / "cmux-assignment.json",
            {
                "ready": True,
                "dispatch_ready": True,
                "runtime_status": "idle",
                "updated_at": "2026-04-19T12:30:00+0800",
                "assignments": [],
            },
        )
        (runtime_dir / "cmux-main-thread-actions.jsonl").write_text(
            json.dumps(
                {
                    "schema_version": "wb-cmux-main-thread-action-v1",
                    "at": "2026-04-19T12:31:00+0800",
                    "actor": "main-thread",
                    "phase": "A9",
                    "kind": "main_thread_direct_reject",
                    "summary": "main-thread rejected this run after strict review",
                    "details": {
                        "decision": "direct_reject",
                        "reason": "strict gate remains unsatisfied",
                    },
                },
                ensure_ascii=False,
            )
            + "\n",
            encoding="utf-8",
        )
        buffer = io.StringIO()
        argv = ["cmux_workflow_status.py", "--runtime-dir", str(runtime_dir)]
        with patch.object(sys, "argv", argv), redirect_stdout(buffer):
            exit_code = cmux_workflow_status.main()

        assert exit_code == 0
        rendered = buffer.getvalue()
        assert "status=failed outcome=direct_reject" in rendered
        assert "terminal" in rendered
        assert "direct_reject=strict gate remains unsatisfied" in rendered
