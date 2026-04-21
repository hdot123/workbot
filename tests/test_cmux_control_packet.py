#!/usr/bin/env python3
"""Regression tests for the Phase 1 control packet schema."""

from __future__ import annotations

import json
import sys
import tempfile
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
    validate_control_packet_for_current_assignment,
)
from workspace.tools.current_task_source import build_cmux_task_source_ref  # noqa: E402


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


def test_rejects_missing_task_source_ref() -> None:
    packet = dict(EXAMPLE_PACKETS["completed"])
    packet.pop("task_source_ref", None)
    try:
        validate_control_packet(packet)
    except ControlPacketError as exc:
        assert "task_source_ref is required" in str(exc)
    else:
        raise AssertionError("expected missing task_source_ref to be rejected")


def test_accepts_current_assignment_packet_and_linked_summary_when_cycle_matches() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        runtime_dir = Path(temp_dir)
        summary_path = runtime_dir / "pm-bot-summary.json"
        current_task_source_ref = build_cmux_task_source_ref(
            assignment_id="P14-PMBOT-R1-HOMEPAGE-INVENTORY-RT4",
            cycle_id="workbot|2026-04-21T19:44:33+0800|P14-PMBOT-R1-HOMEPAGE-INVENTORY-RT4",
            deliverable_path="/Users/busiji/workbot/workspace/projects/YouzyReplica/phase0/project14-pm-r1-homepage-inventory.md",
            evidence_path=str(summary_path),
            status="active",
        )
        packet = dict(EXAMPLE_PACKETS["completed"])
        packet["assignment_id"] = current_task_source_ref["assignment_id"]
        packet["artifact_path"] = str(summary_path)
        packet["task_source_ref"] = dict(current_task_source_ref)
        summary_path.write_text(
            json.dumps(packet, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

        validated = validate_control_packet_for_current_assignment(
            packet,
            expected_assignment_id=current_task_source_ref["assignment_id"],
            expected_task_source_ref=current_task_source_ref,
        )

    assert validated["task_source_ref"]["cycle_id"] == current_task_source_ref["cycle_id"]
    assert validated["artifact_path"] == str(summary_path)


def test_rejects_linked_summary_when_cycle_id_is_stale() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        runtime_dir = Path(temp_dir)
        summary_path = runtime_dir / "pm-bot-summary.json"
        current_task_source_ref = build_cmux_task_source_ref(
            assignment_id="P14-PMBOT-R1-HOMEPAGE-INVENTORY-RT4",
            cycle_id="workbot|2026-04-21T19:44:33+0800|P14-PMBOT-R1-HOMEPAGE-INVENTORY-RT4",
            deliverable_path="/Users/busiji/workbot/workspace/projects/YouzyReplica/phase0/project14-pm-r1-homepage-inventory.md",
            evidence_path=str(summary_path),
            status="active",
        )
        packet = dict(EXAMPLE_PACKETS["completed"])
        packet["assignment_id"] = current_task_source_ref["assignment_id"]
        packet["artifact_path"] = str(summary_path)
        packet["task_source_ref"] = dict(current_task_source_ref)

        stale_summary = dict(packet)
        stale_summary["task_source_ref"] = build_cmux_task_source_ref(
            assignment_id=current_task_source_ref["assignment_id"],
            cycle_id="workbot|2026-04-21T19:35:23+0800|P14-PMBOT-R1-HOMEPAGE-INVENTORY-RT4",
            deliverable_path=current_task_source_ref["deliverable_path"],
            evidence_path=str(summary_path),
            status="active",
        )
        summary_path.write_text(
            json.dumps(stale_summary, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

        try:
            validate_control_packet_for_current_assignment(
                packet,
                expected_assignment_id=current_task_source_ref["assignment_id"],
                expected_task_source_ref=current_task_source_ref,
            )
        except ControlPacketError as exc:
            assert "linked summary artifact rejected" in str(exc)
            assert "cycle_id expected=" in str(exc)
        else:
            raise AssertionError("expected stale linked summary cycle_id to be rejected")


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
