#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

repo_root = Path(__file__).resolve().parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

import workspace.tools.cmux_phase_readiness as phase_readiness
from workspace.tools.cmux_phase_readiness import (
    build_readiness_receipt,
    collect_commander_read_contract_validation,
    collect_runtime_launch_manifest_problems,
    collect_startup_smoke_report_problems,
    collect_delivery_doc_anchor_problems,
    collect_project_status_map,
    collect_project_status_problems,
    expected_runtime_bot_names,
    extract_delivery_anchor_paths,
    extract_absolute_paths,
)
from workspace.tools.cmux_control_packet import EXAMPLE_PACKETS
from workspace.tools.current_task_source import build_cmux_task_source_ref


def current_cmux_task_source(*, assignment_id: str, cycle_id: str, runtime_dir: Path) -> dict[str, str]:
    return build_cmux_task_source_ref(
        assignment_id=assignment_id,
        cycle_id=cycle_id,
        deliverable_path=str((runtime_dir / f"{assignment_id.lower()}-deliverable.md").resolve()),
        evidence_path=str((runtime_dir / "cmux-assignment.json").resolve()),
        status="finished_local_writeback",
    )


def build_ready_receipt_for_test(
    *,
    task_files: tuple[Path, ...] | None = None,
    statuses_by_scope: dict[tuple[Path, ...], dict[str, object]],
) -> tuple[dict[str, object], list[tuple[Path, ...]]]:
    seen_scopes: list[tuple[Path, ...]] = []
    project_payload = json.dumps(
        {
            "items": [
                {
                    "title": phase_readiness.CURRENT_TASK_TITLE,
                    "status": "Done",
                }
            ]
        },
        ensure_ascii=False,
    )

    def fake_collect_scope_git_status(paths: tuple[Path, ...]) -> dict[str, object]:
        scope = tuple(paths)
        seen_scopes.append(scope)
        if scope not in statuses_by_scope:
            raise AssertionError(f"unexpected scope: {scope}")
        return statuses_by_scope[scope]

    with (
        patch.object(
            phase_readiness,
            "validate_memory_system",
            return_value={"status": "ok", "missing_paths": [], "validation_errors": []},
        ),
        patch.object(phase_readiness, "collect_delivery_doc_anchor_problems", return_value={}),
        patch.object(phase_readiness, "expected_runtime_bot_names", return_value=("pm-bot",)),
        patch.object(phase_readiness, "collect_runtime_launch_manifest_problems", return_value={}),
        patch.object(phase_readiness, "collect_startup_smoke_report_problems", return_value={}),
        patch.object(phase_readiness, "collect_commander_read_contract_validation", return_value={"ok": True}),
        patch.object(phase_readiness, "collect_project_status_problems", return_value=[]),
        patch.object(phase_readiness, "collect_git_status", return_value={"ok": True, "lines": [], "stderr": ""}),
        patch.object(
            phase_readiness,
            "run_command",
            return_value=phase_readiness.CommandResult(code=0, stdout=project_payload, stderr=""),
        ),
        patch.object(
            phase_readiness,
            "collect_scope_git_status",
            side_effect=fake_collect_scope_git_status,
        ),
    ):
        receipt = build_readiness_receipt(task_files=task_files)

    return receipt, seen_scopes


def test_extract_absolute_paths_collects_unique_user_paths() -> None:
    text = """
    - `/Users/busiji/workbot/a.md`
    - `/Users/busiji/workbot/b.md`
    - `/Users/busiji/workbot/a.md`
    """
    assert extract_absolute_paths(text) == [
        "/Users/busiji/workbot/a.md",
        "/Users/busiji/workbot/b.md",
    ]


def test_collect_delivery_doc_anchor_problems_flags_missing_refs() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        present = repo_root / "workspace" / "INDEX.md"
        missing = repo_root / "workspace" / "does-not-exist.md"
        doc = root / "delivery.md"
        doc.write_text(
            "\n".join(
                [
                    "## Repo Artifact Added by This Delivery",
                    f"- `{present}`",
                    f"- `{missing}`",
                ]
            ),
            encoding="utf-8",
        )
        problems = collect_delivery_doc_anchor_problems((doc,))
        assert problems[str(doc)] == [str(missing)]


def test_extract_delivery_anchor_paths_ignores_non_delivery_sections() -> None:
    present = repo_root / "workspace" / "INDEX.md"
    text = "\n".join(
        [
            "## Remaining Omissions Not Fixed",
            f"- `{repo_root / 'workspace' / 'missing.md'}`",
            "## Repo Artifact Added by This Delivery",
            f"- `{present}`",
        ]
    )
    assert extract_delivery_anchor_paths(text) == [str(present)]


def test_collect_project_status_map_parses_title_and_status() -> None:
    raw = json.dumps(
        {
            "items": [
                {"title": "[Phase 0] P10-core Dispatch gate contract", "status": "Done"},
                {"title": "[Phase 1] P1 Control packet schema", "status": "Done"},
            ]
        }
    )
    status_map = collect_project_status_map(raw)
    assert status_map["[Phase 0] P10-core Dispatch gate contract"] == "Done"
    assert status_map["[Phase 1] P1 Control packet schema"] == "Done"


def test_collect_project_status_problems_reports_non_done_titles() -> None:
    status_map = {
        "[Phase 0] P10-core Dispatch gate contract": "Done",
        "[Phase 1] P1 Control packet schema": "Todo",
    }
    problems = collect_project_status_problems(
        status_map,
        (
            "[Phase 0] P10-core Dispatch gate contract",
            "[Phase 1] P1 Control packet schema",
            "[Phase 1] P2 Summary and sidecar split",
        ),
    )
    assert problems == [
        "[Phase 1] P1 Control packet schema => Todo",
        "[Phase 1] P2 Summary and sidecar split => missing",
    ]


def test_expected_runtime_bot_names_reads_active_assignments() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        runtime_dir = Path(tmpdir)
        assignment = runtime_dir / "cmux-assignment.json"
        assignment.write_text(
            json.dumps(
                {
                    "assignments": [
                        {"bot_name": "pm-bot", "status": "ACTIVE"},
                        {"bot_name": "dev-bot", "status": "ACTIVE"},
                        {"bot_name": "empty", "status": "ACTIVE"},
                        {"bot_name": "qa-bot", "status": "IDLE"},
                    ]
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        assert expected_runtime_bot_names(runtime_dir) == ("pm-bot", "dev-bot")


def test_collect_runtime_launch_manifest_problems_requires_all_five_default_targets() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        runtime_dir = Path(tmpdir)
        bot_names = expected_runtime_bot_names(runtime_dir)

        problems = collect_runtime_launch_manifest_problems(runtime_dir, bot_names)

        assert bot_names == ("pm-bot", "dev-bot", "qa-bot", "doc-bot", "rea-bot")
        assert set(problems) == {
            str(runtime_dir / f"runtime-launch-manifest-{bot_name}.json") for bot_name in bot_names
        }
        for bot_name in bot_names:
            path = str(runtime_dir / f"runtime-launch-manifest-{bot_name}.json")
            assert problems[path] == [f"missing file: {path}"]


def test_collect_runtime_launch_manifest_problems_flags_missing_and_invalid_fields() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        runtime_dir = Path(tmpdir)
        settings = runtime_dir / "runtime-settings-pm-bot.json"
        settings.write_text("{}", encoding="utf-8")
        manifest = runtime_dir / "runtime-launch-manifest-pm-bot.json"
        manifest.write_text(
            json.dumps(
                {
                    "bot_name": "pm-bot",
                    "workspace_ref": "workspace:1",
                    "surface_ref": "surface:1",
                    "permission_mode": "default",
                    "allowed_tools": ["Read", "Bash"],
                    "runtime_settings_path": str(settings),
                    "launch_command": "claude --agent pm-bot",
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        problems = collect_runtime_launch_manifest_problems(runtime_dir, ("pm-bot", "dev-bot"))
        assert str(runtime_dir / "runtime-launch-manifest-dev-bot.json") in problems
        assert str(manifest) not in problems


def test_collect_startup_smoke_report_problems_requires_pass_when_crawl4ai_enabled() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        runtime_dir = Path(tmpdir)
        settings = runtime_dir / "runtime-settings-pm-bot.json"
        settings.write_text("{}", encoding="utf-8")
        (runtime_dir / "runtime-launch-manifest-pm-bot.json").write_text(
            json.dumps(
                {
                    "bot_name": "pm-bot",
                    "workspace_ref": "workspace:1",
                    "surface_ref": "surface:1",
                    "permission_mode": "default",
                    "allowed_tools": ["Read", "mcp__crawl4ai__md"],
                    "runtime_settings_path": str(settings),
                    "launch_command": "claude --agent pm-bot",
                    "external_mcp_tokens": ["crawl4ai"],
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        (runtime_dir / "pm-bot-smoke-report.json").write_text(
            json.dumps(
                {
                    "bot_name": "pm-bot",
                    "status": "skipped",
                    "reason": "no external mcp tools in allowed_tools",
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        problems = collect_startup_smoke_report_problems(runtime_dir, ("pm-bot",))
        assert str(runtime_dir / "pm-bot-smoke-report.json") in problems
        assert any("status must be passed" in issue for issue in problems[str(runtime_dir / "pm-bot-smoke-report.json")])


def test_collect_startup_smoke_report_problems_allows_skipped_without_crawl4ai() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        runtime_dir = Path(tmpdir)
        settings = runtime_dir / "runtime-settings-dev-bot.json"
        settings.write_text("{}", encoding="utf-8")
        (runtime_dir / "runtime-launch-manifest-dev-bot.json").write_text(
            json.dumps(
                {
                    "bot_name": "dev-bot",
                    "workspace_ref": "workspace:1",
                    "surface_ref": "surface:2",
                    "permission_mode": "default",
                    "allowed_tools": ["Read", "Bash"],
                    "runtime_settings_path": str(settings),
                    "launch_command": "claude --agent dev-bot",
                    "external_mcp_tokens": [],
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        (runtime_dir / "dev-bot-smoke-report.json").write_text(
            json.dumps(
                {
                    "bot_name": "dev-bot",
                    "status": "skipped",
                    "reason": "no external mcp tools in allowed_tools",
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        problems = collect_startup_smoke_report_problems(runtime_dir, ("dev-bot",))
        assert problems == {}


def test_collect_commander_read_contract_validation_prefers_summary_first() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        runtime_dir = Path(tmpdir)
        (runtime_dir / "cross-verify-summary-latest.json").write_text("{}", encoding="utf-8")
        (runtime_dir / "pm-bot-smoke-report.json").write_text("{}", encoding="utf-8")
        (runtime_dir / "cmux-assignment.json").write_text("{}", encoding="utf-8")
        validation = collect_commander_read_contract_validation(runtime_dir)
        assert validation["ok"] is True
        assert validation["default_sources"][0]["rule"] == "commander_summary"


def test_collect_commander_read_contract_validation_excludes_forensic_from_normal_path() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        runtime_dir = Path(tmpdir)
        (runtime_dir / "watch_cmux_assignments.log").write_text("tail", encoding="utf-8")
        (runtime_dir / "pm-bot-smoke-report.json").write_text("{}", encoding="utf-8")
        validation = collect_commander_read_contract_validation(runtime_dir)
        assert validation["ok"] is True
        assert all(item["rule"] != "forensic_only" for item in validation["default_sources"])
        assert any(item["rule"] == "forensic_only" for item in validation["blocked_normal_path_sources"])


def test_collect_commander_read_contract_validation_falls_back_to_smoke_or_control_state() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        runtime_dir = Path(tmpdir)
        (runtime_dir / "pm-bot-smoke-report.json").write_text("{}", encoding="utf-8")
        (runtime_dir / "cmux-assignment.json").write_text("{}", encoding="utf-8")
        validation = collect_commander_read_contract_validation(runtime_dir)
        selected_rules = {item["rule"] for item in validation["default_sources"]}
        assert validation["ok"] is True
        assert selected_rules & {"startup_smoke", "control_state"}


def test_collect_commander_read_contract_validation_reports_verification_packet_read_order() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        runtime_dir = Path(tmpdir)
        (runtime_dir / "cmux-consumer-state-latest.json").write_text(
            json.dumps(
                {
                    "assignments": {
                        "pm-bot": {
                            "assignment_id": "PM-101",
                            "control_packet": {
                                "task_id": "PM-101",
                                "state": "completed",
                                "result": "pass",
                            },
                        }
                    }
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        (runtime_dir / "cmux-finish-receipts.jsonl").write_text("", encoding="utf-8")
        (runtime_dir / "cmux-full-workflow-log-latest.json").write_text("{}", encoding="utf-8")
        (runtime_dir / "cmux-main-thread-actions.jsonl").write_text("", encoding="utf-8")
        validation = collect_commander_read_contract_validation(runtime_dir)
        packet = validation["verification_packet"]
        assert packet["available_slots"] == [
            "consumer_state",
            "finish_receipt",
            "workflow_log",
            "main_thread_actions",
        ]
        assert packet["missing_slots"] == ["control_packet"]
        assert packet["read_order"][0]["via_rule"] == "consumer_state"
        assert packet["read_order"][0].get("extraction") is None
        assert packet["consumer_state_embeds_control_packet_auxiliary"] is True


def test_collect_commander_read_contract_validation_reports_missing_verification_slots() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        runtime_dir = Path(tmpdir)
        (runtime_dir / "cmux-full-workflow-log-latest.json").write_text("{}", encoding="utf-8")
        validation = collect_commander_read_contract_validation(runtime_dir)
        packet = validation["verification_packet"]
        assert packet["available_slots"] == ["workflow_log"]
        assert packet["missing_slots"] == [
            "control_packet",
            "consumer_state",
            "finish_receipt",
            "main_thread_actions",
        ]


def test_collect_commander_read_contract_validation_distinguishes_partial_a7_writeback() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        runtime_dir = Path(tmpdir)
        scoped_cycle_id = "workbot|2026-04-19T15:00:00+0800|PM-101,DEV-101,QA-101,DOC-101,REA-101"
        task_source = current_cmux_task_source(
            assignment_id="DOC-101",
            cycle_id=scoped_cycle_id,
            runtime_dir=runtime_dir,
        )
        (runtime_dir / "cmux-assignment.json").write_text(
            json.dumps(
                {
                    "current_task_sources": [task_source],
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        (runtime_dir / "cmux-consumer-state-latest.json").write_text(
            json.dumps(
                {
                    "assignments": {
                        "doc-bot": {
                            "assignment_id": "DOC-101",
                            "state": "completed",
                        }
                    }
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        (runtime_dir / "cmux-finish-receipts.jsonl").write_text(
            json.dumps(
                {
                    "cycle_id": "workbot|2026-04-19T15:00:00+0800|doc-101",
                    "outcomes": [
                        {
                            "logical_target": "doc-bot",
                            "task_id": "DOC-101",
                            "status": "doc_synced",
                            "task_source_ref": task_source,
                        }
                    ],
                },
                ensure_ascii=False,
            )
            + "\n",
            encoding="utf-8",
        )
        (runtime_dir / "cmux-full-workflow-log-latest.json").write_text("{}", encoding="utf-8")

        validation = collect_commander_read_contract_validation(runtime_dir)
        packet = validation["verification_packet"]

        assert packet["available_slots"] == [
            "consumer_state",
            "finish_receipt",
            "workflow_log",
        ]
        assert packet["missing_slots"] == [
            "control_packet",
            "main_thread_actions",
        ]
        assert packet["a7_writeback_complete"] is False
        assert packet["a7_present_writeback_targets"] == ["doc-bot"]
        assert packet["a7_missing_writeback_targets"] == [
            "pm-bot",
            "dev-bot",
            "qa-bot",
            "rea-bot",
        ]
        assert validation["ok"] is False
        assert validation["problems"] == [
            "A7 local writeback is partial; missing mandatory targets: pm-bot, dev-bot, qa-bot, rea-bot"
        ]


def test_collect_commander_read_contract_validation_uses_current_task_sources_for_single_bot_scope() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        runtime_dir = Path(tmpdir)
        scoped_cycle_id = (
            "workbot|2026-04-21T09:25:27+0800|"
            "P14-PMBOT-R1-HOMEPAGE-INVENTORY,idle-dev-bot,idle-qa-bot,idle-doc-bot,idle-rea-bot"
        )
        receipt_cycle_id = "workbot|2026-04-21T09:30:40+0800|P14-PMBOT-R1-HOMEPAGE-INVENTORY"
        task_source = current_cmux_task_source(
            assignment_id="P14-PMBOT-R1-HOMEPAGE-INVENTORY",
            cycle_id=scoped_cycle_id,
            runtime_dir=runtime_dir,
        )
        (runtime_dir / "cmux-assignment.json").write_text(
            json.dumps(
                {
                    "current_task_sources": [task_source],
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        (runtime_dir / "cmux-finish-receipts.jsonl").write_text(
            json.dumps(
                {
                    "cycle_id": receipt_cycle_id,
                    "task_sources": [task_source],
                    "outcomes": [
                        {
                            "assignment_id": "P14-PMBOT-R1-HOMEPAGE-INVENTORY",
                            "logical_target": "pm-bot",
                            "task_id": "PM-001",
                            "status": "pm_ready",
                            "task_source_ref": task_source,
                        }
                    ],
                },
                ensure_ascii=False,
            )
            + "\n",
            encoding="utf-8",
        )
        (runtime_dir / "cmux-full-workflow-log-latest.json").write_text("{}", encoding="utf-8")

        validation = collect_commander_read_contract_validation(runtime_dir)
        packet = validation["verification_packet"]

        assert packet["a7_required_writeback_targets"] == ["pm-bot"]
        assert packet["a7_present_writeback_targets"] == ["pm-bot"]
        assert packet["a7_missing_writeback_targets"] == []
        assert packet["a7_scope_confirmed"] is True
        assert packet["a7_writeback_complete"] is True


def test_collect_commander_read_contract_validation_uses_current_task_sources_for_three_bot_scope() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        runtime_dir = Path(tmpdir)
        scoped_cycle_id = "workbot|2026-04-21T10:00:00+0800|PM-301,DEV-301,QA-301,idle-doc-bot,idle-rea-bot"
        current_sources = [
            current_cmux_task_source(assignment_id="PM-301", cycle_id=scoped_cycle_id, runtime_dir=runtime_dir),
            current_cmux_task_source(assignment_id="DEV-301", cycle_id=scoped_cycle_id, runtime_dir=runtime_dir),
            current_cmux_task_source(assignment_id="QA-301", cycle_id=scoped_cycle_id, runtime_dir=runtime_dir),
        ]
        (runtime_dir / "cmux-assignment.json").write_text(
            json.dumps(
                {
                    "current_task_sources": current_sources,
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        (runtime_dir / "cmux-finish-receipts.jsonl").write_text(
            json.dumps(
                {
                    "cycle_id": "workbot|2026-04-21T10:05:00+0800|three-bot-batch",
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
        (runtime_dir / "cmux-full-workflow-log-latest.json").write_text("{}", encoding="utf-8")

        validation = collect_commander_read_contract_validation(runtime_dir)
        packet = validation["verification_packet"]

        assert packet["a7_required_writeback_targets"] == ["pm-bot", "dev-bot", "qa-bot"]
        assert packet["a7_present_writeback_targets"] == ["pm-bot", "dev-bot", "qa-bot"]
        assert packet["a7_missing_writeback_targets"] == []
        assert packet["a7_scope_confirmed"] is True
        assert packet["a7_writeback_complete"] is True


def test_collect_commander_read_contract_validation_fails_closed_without_current_task_scope() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        runtime_dir = Path(tmpdir)
        (runtime_dir / "cmux-assignment.json").write_text(
            json.dumps(
                {
                    "ready": True,
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        (runtime_dir / "cmux-finish-receipts.jsonl").write_text(
            json.dumps(
                {
                    "cycle_id": "workbot|2026-04-21T10:30:00+0800|task-401",
                    "outcomes": [
                        {
                            "assignment_id": "TASK-401",
                            "task_id": "TASK-401",
                            "status": "completed",
                        }
                    ],
                },
                ensure_ascii=False,
            )
            + "\n",
            encoding="utf-8",
        )
        (runtime_dir / "cmux-full-workflow-log-latest.json").write_text("{}", encoding="utf-8")

        validation = collect_commander_read_contract_validation(runtime_dir)
        packet = validation["verification_packet"]

        assert packet["a7_required_writeback_targets"] == []
        assert packet["a7_present_writeback_targets"] == []
        assert packet["a7_missing_writeback_targets"] == []
        assert packet["a7_scope_confirmed"] is False
        assert packet["a7_writeback_complete"] is False
        assert validation["ok"] is False
        assert validation["problems"] == [
            "A7 dispatch scope is unconfirmed; required writeback targets could not be derived from current task source bindings"
        ]


def test_collect_commander_read_contract_validation_rejects_partial_a7_with_full_packet_slots() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        runtime_dir = Path(tmpdir)
        scoped_cycle_id = "workbot|2026-04-19T15:00:00+0800|PM-101,DEV-101,QA-101,DOC-101,REA-101"
        task_source = current_cmux_task_source(
            assignment_id="DOC-101",
            cycle_id=scoped_cycle_id,
            runtime_dir=runtime_dir,
        )
        (runtime_dir / "cmux-assignment.json").write_text(
            json.dumps(
                {
                    "current_task_sources": [task_source],
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        (runtime_dir / "cmux-consumer-state-latest.json").write_text(
            json.dumps(
                {
                    "assignments": {
                        "doc-bot": {
                            "assignment_id": "DOC-101",
                            "state": "completed",
                            "control_packet": dict(EXAMPLE_PACKETS["completed"]),
                        }
                    }
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        (runtime_dir / "doc-bot-control-packet.json").write_text(
            json.dumps(dict(EXAMPLE_PACKETS["completed"]), ensure_ascii=False),
            encoding="utf-8",
        )
        (runtime_dir / "cmux-finish-receipts.jsonl").write_text(
            json.dumps(
                {
                    "cycle_id": "workbot|2026-04-19T15:00:00+0800|doc-101",
                    "outcomes": [
                        {
                            "logical_target": "doc-bot",
                            "task_id": "DOC-101",
                            "status": "doc_synced",
                            "task_source_ref": task_source,
                        }
                    ],
                },
                ensure_ascii=False,
            )
            + "\n",
            encoding="utf-8",
        )
        (runtime_dir / "cmux-full-workflow-log-latest.json").write_text("{}", encoding="utf-8")
        (runtime_dir / "cmux-main-thread-actions.jsonl").write_text("", encoding="utf-8")

        validation = collect_commander_read_contract_validation(runtime_dir)
        packet = validation["verification_packet"]

        assert packet["available_slots"] == [
            "control_packet",
            "consumer_state",
            "finish_receipt",
            "workflow_log",
            "main_thread_actions",
        ]
        assert packet["missing_slots"] == []
        assert packet["a7_writeback_complete"] is False
        assert packet["a7_present_writeback_targets"] == ["doc-bot"]
        assert packet["a7_missing_writeback_targets"] == [
            "pm-bot",
            "dev-bot",
            "qa-bot",
            "rea-bot",
        ]
        assert validation["ok"] is False
        assert validation["problems"] == [
            "A7 local writeback is partial; missing mandatory targets: pm-bot, dev-bot, qa-bot, rea-bot"
        ]


def test_collect_commander_read_contract_validation_uses_latest_receipt_for_a7_completeness() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        runtime_dir = Path(tmpdir)
        scoped_cycle_id = "workbot|2026-04-20T10:00:00+0800|PM-101,DEV-101,QA-101,DOC-201,REA-101"
        task_source = current_cmux_task_source(
            assignment_id="DOC-201",
            cycle_id=scoped_cycle_id,
            runtime_dir=runtime_dir,
        )
        (runtime_dir / "cmux-assignment.json").write_text(
            json.dumps(
                {
                    "current_task_sources": [task_source],
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        (runtime_dir / "cmux-consumer-state-latest.json").write_text(
            json.dumps(
                {
                    "assignments": {
                        "doc-bot": {
                            "assignment_id": "DOC-101",
                            "state": "completed",
                            "control_packet": dict(EXAMPLE_PACKETS["completed"]),
                        }
                    }
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        (runtime_dir / "doc-bot-control-packet.json").write_text(
            json.dumps(dict(EXAMPLE_PACKETS["completed"]), ensure_ascii=False),
            encoding="utf-8",
        )
        full_receipt = {
            "cycle_id": "workbot|2026-04-19T15:00:00+0800|strict-gap-fix-full",
            "outcomes": [
                {"logical_target": "pm-bot", "task_id": "PM-101", "status": "pm_completed"},
                {"logical_target": "dev-bot", "task_id": "DEV-101", "status": "dev_completed"},
                {"logical_target": "qa-bot", "task_id": "QA-101", "status": "qa_completed"},
                {"logical_target": "doc-bot", "task_id": "DOC-101", "status": "doc_synced"},
                {"logical_target": "rea-bot", "task_id": "REA-101", "status": "rea_completed"},
            ],
        }
        partial_receipt = {
            "cycle_id": "workbot|2026-04-20T10:00:00+0800|strict-gap-fix-partial",
            "outcomes": [
                {
                    "logical_target": "doc-bot",
                    "task_id": "DOC-201",
                    "status": "doc_synced",
                    "task_source_ref": task_source,
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
        (runtime_dir / "cmux-full-workflow-log-latest.json").write_text("{}", encoding="utf-8")
        (runtime_dir / "cmux-main-thread-actions.jsonl").write_text("", encoding="utf-8")

        validation = collect_commander_read_contract_validation(runtime_dir)
        packet = validation["verification_packet"]

        assert packet["missing_slots"] == []
        assert packet["a7_evaluated_cycle_id"] == partial_receipt["cycle_id"]
        assert packet["a7_writeback_complete"] is False
        assert packet["a7_present_writeback_targets"] == ["doc-bot"]
        assert packet["a7_missing_writeback_targets"] == [
            "pm-bot",
            "dev-bot",
            "qa-bot",
            "rea-bot",
        ]
        assert validation["ok"] is False


def test_build_readiness_receipt_uses_explicit_two_file_scope_for_delivery_status() -> None:
    package_scope = (
        repo_root / "workspace" / "tools" / "cmux_phase_readiness.py",
        repo_root / "tests" / "test_cmux_phase_readiness.py",
    )
    default_scope = phase_readiness.CURRENT_TASK_FILES
    receipt, seen_scopes = build_ready_receipt_for_test(
        task_files=package_scope,
        statuses_by_scope={
            default_scope: {"ok": True, "lines": [" M docs/project-management/out-of-scope.md"], "stderr": ""},
            package_scope: {"ok": True, "lines": [], "stderr": ""},
        },
    )

    assert seen_scopes == [package_scope]
    assert receipt["current_task_git_status"] == {"ok": True, "lines": [], "stderr": ""}
    assert receipt["delivered"] is True
    assert receipt["ready"] is True


def test_build_readiness_receipt_accepts_explicit_project_scope() -> None:
    project_scope = (
        repo_root / ".github" / "workflows" / "memory-hook-external-core-only.yml",
        repo_root / ".github" / "workflows" / "memory-core-auto-sync-deploy.yml",
        repo_root / "docs" / "project-management" / "workbot-cmux-p14-ci-regression-anchor-cleanup-2026-04-18.md",
        repo_root / "workspace" / "tools" / "cmux_phase_readiness.py",
        repo_root / "tests" / "test_cmux_phase_readiness.py",
    )
    dirty_status = {
        "ok": True,
        "lines": [" M docs/project-management/workbot-cmux-p14-ci-regression-anchor-cleanup-2026-04-18.md"],
        "stderr": "",
    }
    receipt, seen_scopes = build_ready_receipt_for_test(
        task_files=project_scope,
        statuses_by_scope={project_scope: dirty_status},
    )

    assert seen_scopes == [project_scope]
    assert receipt["current_task_git_status"] == dirty_status
    assert receipt["delivered"] is False
    assert receipt["ready"] is False


def test_build_readiness_receipt_defaults_scope_when_task_files_missing() -> None:
    default_scope = phase_readiness.CURRENT_TASK_FILES
    receipt, seen_scopes = build_ready_receipt_for_test(
        statuses_by_scope={default_scope: {"ok": True, "lines": [], "stderr": ""}},
    )

    assert seen_scopes == [default_scope]
    assert receipt["current_task_git_status"] == {"ok": True, "lines": [], "stderr": ""}
    assert receipt["delivered"] is True
    assert receipt["ready"] is True


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    passed = 0
    failed = 0
    for fn in tests:
        try:
            fn()
            passed += 1
            print(f"  PASS  {fn.__name__}")
        except Exception as exc:
            failed += 1
            print(f"  FAIL  {fn.__name__}: {exc}")
    print(f"\n{passed} passed, {failed} failed out of {passed + failed}")
    sys.exit(1 if failed else 0)
