#!/usr/bin/env python3
"""Regression tests for the main-thread token contract."""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from workspace.tools.cmux_control_packet import EXAMPLE_PACKETS  # noqa: E402
from workspace.tools.cmux_read_contract import (  # noqa: E402
    REQUIRED_VERIFICATION_PACKET_SLOTS,
    choose_commander_default_sources,
    choose_verification_packet_sources,
    classify_runtime_artifact,
    explain_forensic_requirement,
)


def test_summary_artifact_is_default_commander_source() -> None:
    classified = classify_runtime_artifact(
        "/Users/busiji/workbot/workspace/artifacts/cmux-runtime/cross-verify-summary-latest.json"
    )
    assert classified.rule.name == "commander_summary"
    assert classified.rule.normal_path_allowed is True


def test_workflow_summary_artifact_is_default_commander_source() -> None:
    classified = classify_runtime_artifact(
        "/Users/busiji/workbot/workspace/artifacts/cmux-runtime/cmux-workflow-summary-latest.json"
    )
    assert classified.rule.name == "commander_summary"
    assert classified.rule.normal_path_allowed is True


def test_workflow_log_is_normal_path_readable() -> None:
    classified = classify_runtime_artifact(
        "/Users/busiji/workbot/workspace/artifacts/cmux-runtime/cmux-full-workflow-log-latest.json"
    )
    assert classified.rule.name == "workflow_log"
    assert classified.rule.normal_path_allowed is True


def test_watcher_log_is_forensic_only() -> None:
    classified = classify_runtime_artifact(
        "/Users/busiji/workbot/workspace/artifacts/cmux-runtime/watch_cmux_assignments.log"
    )
    assert classified.rule.name == "forensic_only"
    assert classified.rule.normal_path_allowed is False


def test_control_state_artifact_is_secondary_but_normal_path_readable() -> None:
    classified = classify_runtime_artifact(
        "/Users/busiji/workbot/workspace/artifacts/cmux-runtime/cmux-assignment.json"
    )
    assert classified.rule.name == "control_state"
    assert classified.rule.normal_path_allowed is True


def test_runtime_launch_manifest_is_archive_only_side_state() -> None:
    classified = classify_runtime_artifact(
        "/Users/busiji/workbot/workspace/artifacts/cmux-runtime/runtime-launch-manifest-dev-bot.json"
    )
    assert classified.rule.name == "side_state_shadow"
    assert classified.rule.normal_path_allowed is False


def test_startup_smoke_report_is_normal_path_readable() -> None:
    classified = classify_runtime_artifact(
        "/Users/busiji/workbot/workspace/artifacts/cmux-runtime/pm-bot-smoke-report.json"
    )
    assert classified.rule.name == "startup_smoke"
    assert classified.rule.normal_path_allowed is True


def test_workflow_runs_bundle_is_archive_only() -> None:
    classified = classify_runtime_artifact(
        "/Users/busiji/workbot/workspace/artifacts/cmux-runtime/workflow-runs/2026-04-21/IDLE/run-002/workflow-summary.json"
    )
    assert classified.rule.name == "archive_only"
    assert classified.rule.normal_path_allowed is False


def test_consumer_state_is_normal_path_readable() -> None:
    classified = classify_runtime_artifact(
        "/Users/busiji/workbot/workspace/artifacts/cmux-runtime/cmux-consumer-state-latest.json"
    )
    assert classified.rule.name == "consumer_state"
    assert classified.rule.normal_path_allowed is True


def test_finish_receipt_journal_is_normal_path_readable() -> None:
    classified = classify_runtime_artifact(
        "/Users/busiji/workbot/workspace/artifacts/cmux-runtime/cmux-finish-receipts.jsonl"
    )
    assert classified.rule.name == "finish_receipt_journal"
    assert classified.rule.normal_path_allowed is True


def test_main_thread_action_journal_is_normal_path_readable() -> None:
    classified = classify_runtime_artifact(
        "/Users/busiji/workbot/workspace/artifacts/cmux-runtime/cmux-main-thread-actions.jsonl"
    )
    assert classified.rule.name == "main_thread_action_journal"
    assert classified.rule.normal_path_allowed is True


def test_hook_state_is_demoted_from_normal_path() -> None:
    classified = classify_runtime_artifact(
        "/Users/busiji/workbot/workspace/artifacts/cmux-runtime/hook-state.json"
    )
    assert classified.rule.name == "side_state_shadow"
    assert classified.rule.normal_path_allowed is False


def test_pm_bot_watch_is_demoted_from_normal_path() -> None:
    classified = classify_runtime_artifact(
        "/Users/busiji/workbot/workspace/artifacts/cmux-runtime/pm-bot-watch.json"
    )
    assert classified.rule.name == "side_state_shadow"
    assert classified.rule.normal_path_allowed is False


def test_overview_file_requires_explicit_escalation() -> None:
    classified = classify_runtime_artifact(
        "/Users/busiji/workbot/workspace/artifacts/cmux-runtime/runtime-overview.json"
    )
    assert classified.rule.name == "overview_sidecar"
    assert classified.rule.normal_path_allowed is False


def test_choose_commander_default_sources_prefers_summary_only() -> None:
    ranked = choose_commander_default_sources(
        [
            "/Users/busiji/workbot/workspace/artifacts/cmux-runtime/cross-verify-latest.json",
            "/Users/busiji/workbot/workspace/artifacts/cmux-runtime/cross-verify-summary-latest.json",
            "/Users/busiji/workbot/workspace/artifacts/cmux-runtime/watch_cmux_assignments.log",
        ]
    )
    assert [item.path for item in ranked] == [
        "/Users/busiji/workbot/workspace/artifacts/cmux-runtime/cross-verify-summary-latest.json"
    ]


def test_choose_commander_default_sources_prefers_summary_then_control_state() -> None:
    ranked = choose_commander_default_sources(
        [
            "/Users/busiji/workbot/workspace/artifacts/cmux-runtime/hook-state.json",
            "/Users/busiji/workbot/workspace/artifacts/cmux-runtime/cmux-assignment.json",
            "/Users/busiji/workbot/workspace/artifacts/cmux-runtime/cross-verify-summary-latest.json",
        ]
    )
    assert [item.path for item in ranked] == [
        "/Users/busiji/workbot/workspace/artifacts/cmux-runtime/cross-verify-summary-latest.json",
        "/Users/busiji/workbot/workspace/artifacts/cmux-runtime/cmux-assignment.json",
    ]


def test_choose_commander_default_sources_includes_workflow_log_before_control_state() -> None:
    ranked = choose_commander_default_sources(
        [
            "/Users/busiji/workbot/workspace/artifacts/cmux-runtime/hook-state.json",
            "/Users/busiji/workbot/workspace/artifacts/cmux-runtime/cmux-assignment.json",
            "/Users/busiji/workbot/workspace/artifacts/cmux-runtime/cmux-full-workflow-log-latest.json",
        ]
    )
    assert [item.path for item in ranked] == [
        "/Users/busiji/workbot/workspace/artifacts/cmux-runtime/cmux-full-workflow-log-latest.json",
        "/Users/busiji/workbot/workspace/artifacts/cmux-runtime/cmux-assignment.json",
    ]


def test_choose_commander_default_sources_prefers_summary_then_smoke_then_control_state() -> None:
    ranked = choose_commander_default_sources(
        [
            "/Users/busiji/workbot/workspace/artifacts/cmux-runtime/hook-state.json",
            "/Users/busiji/workbot/workspace/artifacts/cmux-runtime/cmux-assignment.json",
            "/Users/busiji/workbot/workspace/artifacts/cmux-runtime/pm-bot-smoke-report.json",
            "/Users/busiji/workbot/workspace/artifacts/cmux-runtime/cross-verify-summary-latest.json",
        ]
    )
    assert [item.path for item in ranked] == [
        "/Users/busiji/workbot/workspace/artifacts/cmux-runtime/cross-verify-summary-latest.json",
        "/Users/busiji/workbot/workspace/artifacts/cmux-runtime/pm-bot-smoke-report.json",
        "/Users/busiji/workbot/workspace/artifacts/cmux-runtime/cmux-assignment.json",
    ]


def test_forensic_explanation_mentions_escalation() -> None:
    message = explain_forensic_requirement(
        "/Users/busiji/workbot/workspace/artifacts/cmux-runtime/watch_cmux_assignments.log"
    )
    assert "escalation is required" in message


def test_choose_verification_packet_sources_keeps_consumer_state_auxiliary_when_only_embedded_packet_exists() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        runtime_dir = Path(tmpdir)
        consumer_state = runtime_dir / "cmux-consumer-state-latest.json"
        consumer_state.write_text(
            json.dumps(
                {
                    "assignments": {
                        "pm-bot": {
                            "control_packet": {
                                "state": "completed",
                                "result": "pass",
                            }
                        }
                    }
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

        packet = choose_verification_packet_sources(
            [
                consumer_state,
                runtime_dir / "cmux-finish-receipts.jsonl",
                runtime_dir / "cmux-full-workflow-log-latest.json",
                runtime_dir / "cmux-main-thread-actions.jsonl",
            ]
        )

        assert [entry.slot for entry in packet] == [
            "consumer_state",
            "finish_receipt",
            "workflow_log",
            "main_thread_actions",
        ]
        assert all(entry.slot != "control_packet" for entry in packet)
        assert packet[0].path == str(consumer_state)
        assert packet[0].via_rule == "consumer_state"
        assert packet[0].extraction is None


def test_choose_verification_packet_sources_prefers_standalone_control_packet_when_present() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        runtime_dir = Path(tmpdir)
        control_packet = runtime_dir / "pm-bot-control-packet.json"
        control_packet.write_text(
            json.dumps(dict(EXAMPLE_PACKETS["completed"]), ensure_ascii=False),
            encoding="utf-8",
        )

        packet = choose_verification_packet_sources(
            [
                control_packet,
                runtime_dir / "cmux-consumer-state-latest.json",
                runtime_dir / "cmux-finish-receipts.jsonl",
                runtime_dir / "cmux-full-workflow-log-latest.json",
                runtime_dir / "cmux-main-thread-actions.jsonl",
            ]
        )

        assert packet[0].slot == "control_packet"
        assert packet[0].path == str(control_packet)
        assert packet[0].via_rule == "control_packet_artifact"
        assert packet[0].extraction is None


def test_choose_verification_packet_sources_rejects_invalid_standalone_control_packet() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        runtime_dir = Path(tmpdir)
        control_packet = runtime_dir / "pm-bot-control-packet.json"
        control_packet.write_text(
            json.dumps({"state": "completed", "result": "pass"}, ensure_ascii=False),
            encoding="utf-8",
        )

        packet = choose_verification_packet_sources(
            [
                control_packet,
                runtime_dir / "cmux-consumer-state-latest.json",
                runtime_dir / "cmux-finish-receipts.jsonl",
                runtime_dir / "cmux-full-workflow-log-latest.json",
                runtime_dir / "cmux-main-thread-actions.jsonl",
            ]
        )

        assert [entry.slot for entry in packet] == [
            "consumer_state",
            "finish_receipt",
            "workflow_log",
            "main_thread_actions",
        ]


def test_choose_verification_packet_sources_uses_first_valid_control_packet_artifact() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        runtime_dir = Path(tmpdir)
        invalid_packet = runtime_dir / "a-control-packet.json"
        valid_packet = runtime_dir / "z-control-packet.json"
        invalid_packet.write_text(
            json.dumps({"state": "completed", "result": "pass"}, ensure_ascii=False),
            encoding="utf-8",
        )
        valid_packet.write_text(
            json.dumps(dict(EXAMPLE_PACKETS["completed"]), ensure_ascii=False),
            encoding="utf-8",
        )

        packet = choose_verification_packet_sources(
            [
                invalid_packet,
                valid_packet,
                runtime_dir / "cmux-consumer-state-latest.json",
                runtime_dir / "cmux-finish-receipts.jsonl",
                runtime_dir / "cmux-full-workflow-log-latest.json",
                runtime_dir / "cmux-main-thread-actions.jsonl",
            ]
        )

        assert packet[0].slot == "control_packet"
        assert packet[0].path == str(valid_packet)
        assert packet[0].via_rule == "control_packet_artifact"


def test_choose_verification_packet_sources_accepts_valid_control_packet_with_generic_json_name() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        runtime_dir = Path(tmpdir)
        generic_packet = runtime_dir / "artifact.json"
        generic_packet.write_text(
            json.dumps(dict(EXAMPLE_PACKETS["completed"]), ensure_ascii=False),
            encoding="utf-8",
        )

        packet = choose_verification_packet_sources(
            [
                generic_packet,
                runtime_dir / "cmux-consumer-state-latest.json",
                runtime_dir / "cmux-finish-receipts.jsonl",
                runtime_dir / "cmux-full-workflow-log-latest.json",
                runtime_dir / "cmux-main-thread-actions.jsonl",
            ]
        )

        assert packet[0].slot == "control_packet"
        assert packet[0].path == str(generic_packet)


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
