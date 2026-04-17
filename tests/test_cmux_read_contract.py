#!/usr/bin/env python3
"""Regression tests for the main-thread token contract."""

from __future__ import annotations

import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from workspace.tools.cmux_read_contract import (  # noqa: E402
    choose_commander_default_sources,
    classify_runtime_artifact,
    explain_forensic_requirement,
)


def test_summary_artifact_is_default_commander_source() -> None:
    classified = classify_runtime_artifact(
        "/Users/busiji/workbot/workspace/artifacts/cmux-runtime/cross-verify-summary-latest.json"
    )
    assert classified.rule.name == "commander_summary"
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


def test_forensic_explanation_mentions_escalation() -> None:
    message = explain_forensic_requirement(
        "/Users/busiji/workbot/workspace/artifacts/cmux-runtime/watch_cmux_assignments.log"
    )
    assert "escalation is required" in message


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
