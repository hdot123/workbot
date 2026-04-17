#!/usr/bin/env python3
"""Regression tests for the Phase 1 control packet schema."""

from __future__ import annotations

import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from workspace.tools.cmux_control_packet import (  # noqa: E402
    ControlPacketError,
    EXAMPLE_PACKETS,
    SCHEMA_VERSION,
    extract_latest_control_packet,
    validate_control_packet,
)


def render_packet(packet: dict[str, object]) -> str:
    marker = str(packet["marker"])
    return f"{marker}{json.dumps(packet, ensure_ascii=False)}"


def test_validates_example_packets_for_each_state() -> None:
    for state, packet in EXAMPLE_PACKETS.items():
        validated = validate_control_packet(packet)
        assert validated["schema_version"] == SCHEMA_VERSION
        assert validated["state"] == state
        assert validated["marker"] == packet["marker"]


def test_extracts_latest_valid_packet_from_screen_text() -> None:
    running_packet = dict(EXAMPLE_PACKETS["running"])
    completed_packet = dict(EXAMPLE_PACKETS["completed"])
    screen = "\n".join(
        [
            "noise before packet",
            render_packet(running_packet),
            "intermediate log line",
            render_packet(completed_packet),
        ]
    )
    parsed = extract_latest_control_packet(screen)
    assert parsed["state"] == "completed"
    assert parsed["result"] == "pass"
    assert parsed["artifact_path"] == completed_packet["artifact_path"]


def test_rejects_prose_only_completion_output() -> None:
    try:
        extract_latest_control_packet("交付结论：已完成，测试通过。")
    except ControlPacketError as exc:
        assert "prose-only completion output" in str(exc)
    else:
        raise AssertionError("expected prose-only completion output to be rejected")


def test_rejects_marker_prefix_mismatch() -> None:
    packet = dict(EXAMPLE_PACKETS["completed"])
    packet["marker"] = "XCmismatch:"
    try:
        extract_latest_control_packet(f"XCactual01:{json.dumps(packet, ensure_ascii=False)}")
    except ControlPacketError as exc:
        assert "marker prefix mismatch" in str(exc)
    else:
        raise AssertionError("expected mismatched marker to be rejected")


def test_rejects_placeholder_terminal_summary() -> None:
    packet = dict(EXAMPLE_PACKETS["completed"])
    packet["summary"] = "done"
    try:
        validate_control_packet(packet)
    except ControlPacketError as exc:
        assert "placeholder-only" in str(exc)
    else:
        raise AssertionError("expected placeholder summary to be rejected")


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
