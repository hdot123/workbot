#!/usr/bin/env python3
"""Regression tests for the Phase 1 summary/sidecar split."""

from __future__ import annotations

import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from workspace.tools.cmux_cross_verify import build_cross_verify_summary  # noqa: E402
from workspace.tools.cmux_cross_verify import (  # noqa: E402
    build_check_packet_prompt,
    packet_indicates_success,
)
from workspace.tools.cmux_summary_artifact import (  # noqa: E402
    SUMMARY_SCHEMA_VERSION,
    SummaryArtifactError,
    build_summary_artifact,
)


def test_build_summary_artifact_allows_missing_sidecar() -> None:
    artifact = build_summary_artifact(
        title="cmux status",
        status="passed",
        summary_lines=["All checks passed."],
        source="unit_test",
        primary_sidecar_path=None,
        sidecar_paths=[],
    )
    assert artifact["schema_version"] == SUMMARY_SCHEMA_VERSION
    assert artifact["primary_sidecar_path"] is None
    assert artifact["sidecar_paths"] == []


def test_build_summary_artifact_rejects_relative_sidecar_path() -> None:
    try:
        build_summary_artifact(
            title="cmux status",
            status="passed",
            summary_lines=["All checks passed."],
            source="unit_test",
            primary_sidecar_path="relative/report.json",
        )
    except SummaryArtifactError as exc:
        assert "absolute path" in str(exc)
    else:
        raise AssertionError("expected relative sidecar path to be rejected")


def test_build_cross_verify_summary_points_to_detail_sidecar() -> None:
    report = {
        "overall": "failed",
        "checks": {
            "pm-bot:crawl4ai_md": {"status": "failed"},
            "dev-bot:claude_read": {"status": "passed"},
        },
        "failed_checks": ["pm-bot:crawl4ai_md"],
    }
    detail_path = Path("/Users/busiji/workbot/workspace/artifacts/cmux-runtime/cross-verify-latest.json")
    summary = build_cross_verify_summary(report, detail_path)
    assert summary["status"] == "failed"
    assert summary["primary_sidecar_path"] == str(detail_path)
    assert summary["sidecar_paths"] == [str(detail_path)]
    assert "pm-bot:crawl4ai_md" in summary["failed_checks"]
    assert len(summary["summary_lines"]) <= 3


def test_build_check_packet_prompt_uses_control_packet_schema() -> None:
    prompt = build_check_packet_prompt(
        tool_instruction="请只调用一次测试工具。",
        marker="XC1234:",
        bot="dev-bot",
        check="read",
        summary="dev-bot completed the read check.",
    )
    assert '"schema_version":"wb-cmux-control-packet-v1"' in prompt
    assert '"marker":"XC1234:"' in prompt
    assert prompt.count("XC1234:") >= 2


def test_packet_indicates_success_uses_state_result_and_status_code() -> None:
    base_packet = {
        "schema_version": "wb-cmux-control-packet-v1",
        "state": "completed",
        "result": "pass",
        "marker": "XC2001:",
        "summary": "ok",
        "artifact_path": None,
    }
    assert packet_indicates_success(base_packet) is True
    crawl_packet = dict(base_packet)
    crawl_packet["status_code"] = 200
    assert packet_indicates_success(crawl_packet, expected_status_code=200) is True
    crawl_packet["status_code"] = 500
    assert packet_indicates_success(crawl_packet, expected_status_code=200) is False


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
