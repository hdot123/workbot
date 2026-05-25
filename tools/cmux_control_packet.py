#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

from workspace.tools.current_task_source import (
    TASK_TYPE_CMUX,
    TaskSourceContractError,
    build_cmux_task_source_ref,
    maybe_normalize_task_source_ref,
)


SCHEMA_VERSION = "wb-cmux-control-packet-v1"
STATE_RESULT_MAP = {
    "running": "in_progress",
    "waiting_input": "needs_input",
    "blocked": "blocked",
    "completed": "pass",
    "failed": "fail",
}
TERMINAL_STATES = {"completed", "failed"}
MARKER_RE = re.compile(r"(?P<marker>[A-Za-z][A-Za-z0-9_-]{3,23}:)")
PLACEHOLDER_SUMMARIES = {
    "blocked",
    "completed",
    "done",
    "failed",
    "in progress",
    "needs input",
    "ok",
    "pass",
    "running",
    "waiting",
    "完成",
    "已完成",
    "失败",
    "等待",
    "通过",
    "阻塞",
    "运行中",
}
PROSE_ONLY_COMPLETION_RE = re.compile(
    r"\b(done|completed|pass|passed|failed|failure)\b|完成|已完成|通过|失败",
    re.IGNORECASE,
)
TASK_SOURCE_LIVE_IDENTITY_FIELDS = (
    "task_source_id",
    "assignment_id",
    "cycle_id",
    "deliverable_path",
    "evidence_path",
)

EXAMPLE_PACKETS: dict[str, dict[str, Any]] = {
    "running": {
        "schema_version": SCHEMA_VERSION,
        "state": "running",
        "result": "in_progress",
        "marker": "XCp1run01:",
        "assignment_id": "dev-101",
        "logical_target": "dev-bot",
        "summary": "dev-bot is applying the approved patch set.",
        "artifact_path": None,
        "task_source_ref": build_cmux_task_source_ref(
            assignment_id="dev-101",
            cycle_id="cmux-cycle:dev-101:1",
            deliverable_path="/Users/busiji/workbot/workspace/projects/sample/dev-101-deliverable.md",
            evidence_path="/Users/busiji/workbot/workspace/artifacts/cmux-runtime/dev-101-running.json",
            status="running",
        ),
    },
    "waiting_input": {
        "schema_version": SCHEMA_VERSION,
        "state": "waiting_input",
        "result": "needs_input",
        "marker": "XCp1wait1:",
        "assignment_id": "qa-101",
        "logical_target": "qa-bot",
        "summary": "qa-bot is waiting for the commander to approve the next prompt.",
        "artifact_path": None,
        "task_source_ref": build_cmux_task_source_ref(
            assignment_id="qa-101",
            cycle_id="cmux-cycle:qa-101:1",
            deliverable_path="/Users/busiji/workbot/workspace/projects/sample/qa-101-deliverable.md",
            evidence_path="/Users/busiji/workbot/workspace/artifacts/cmux-runtime/qa-101-waiting.json",
            status="needs_input",
        ),
    },
    "blocked": {
        "schema_version": SCHEMA_VERSION,
        "state": "blocked",
        "result": "blocked",
        "marker": "XCp1block:",
        "assignment_id": "pm-101",
        "logical_target": "pm-bot",
        "summary": "pm-bot is blocked by a missing validated upstream source.",
        "artifact_path": "/Users/busiji/workbot/workspace/artifacts/cmux-runtime/pm-bot-blocked.json",
        "evidence_refs": [
            "/Users/busiji/workbot/workspace/artifacts/cmux-runtime/pm-bot-blocked.json"
        ],
        "task_source_ref": build_cmux_task_source_ref(
            assignment_id="pm-101",
            cycle_id="cmux-cycle:pm-101:1",
            deliverable_path="/Users/busiji/workbot/workspace/projects/sample/pm-101-deliverable.md",
            evidence_path="/Users/busiji/workbot/workspace/artifacts/cmux-runtime/pm-bot-blocked.json",
            status="blocked",
        ),
    },
    "completed": {
        "schema_version": SCHEMA_VERSION,
        "state": "completed",
        "result": "pass",
        "marker": "XCp1done1:",
        "assignment_id": "doc-101",
        "logical_target": "doc-bot",
        "task_id": "DOC-101",
        "summary": "doc-bot finished the delivery note and recorded the evidence path.",
        "artifact_path": "/Users/busiji/workbot/workspace/artifacts/cmux-runtime/doc-bot-summary.json",
        "completed_at": "2026-04-17T22:30:00+0800",
        "evidence_refs": [
            "/Users/busiji/workbot/workspace/artifacts/cmux-runtime/doc-bot-summary.json"
        ],
        "task_source_ref": build_cmux_task_source_ref(
            assignment_id="doc-101",
            cycle_id="cmux-cycle:doc-101:1",
            deliverable_path="/Users/busiji/workbot/workspace/projects/sample/doc-101-deliverable.md",
            evidence_path="/Users/busiji/workbot/workspace/artifacts/cmux-runtime/doc-bot-summary.json",
            status="completed",
        ),
    },
    "failed": {
        "schema_version": SCHEMA_VERSION,
        "state": "failed",
        "result": "fail",
        "marker": "XCp1fail1:",
        "assignment_id": "rea-101",
        "logical_target": "rea-bot",
        "task_id": "REA-101",
        "summary": "rea-bot rejected the packet because the evidence artifact was missing.",
        "artifact_path": "/Users/busiji/workbot/workspace/artifacts/cmux-runtime/rea-bot-failure.json",
        "completed_at": "2026-04-17T22:31:00+0800",
        "evidence_refs": [
            "/Users/busiji/workbot/workspace/artifacts/cmux-runtime/rea-bot-failure.json"
        ],
        "task_source_ref": build_cmux_task_source_ref(
            assignment_id="rea-101",
            cycle_id="cmux-cycle:rea-101:1",
            deliverable_path="/Users/busiji/workbot/workspace/projects/sample/rea-101-deliverable.md",
            evidence_path="/Users/busiji/workbot/workspace/artifacts/cmux-runtime/rea-bot-failure.json",
            status="failed",
        ),
    },
}


class ControlPacketError(ValueError):
    """Raised when a control packet is missing or invalid."""


def _extract_first_json_object(text: str) -> str | None:
    start = text.find("{")
    if start < 0:
        return None
    depth = 0
    in_string = False
    escaped = False
    for pos in range(start, len(text)):
        ch = text[pos]
        if in_string:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[start : pos + 1]
    return None


def _normalize_text_field(packet: dict[str, Any], field_name: str) -> str:
    value = packet.get(field_name)
    if not isinstance(value, str):
        raise ControlPacketError(f"{field_name} must be a string")
    normalized = value.strip()
    if not normalized:
        raise ControlPacketError(f"{field_name} must not be empty")
    return normalized


def _normalize_artifact_path(value: Any) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ControlPacketError("artifact_path must be a string or null")
    normalized = value.strip()
    if not normalized:
        raise ControlPacketError("artifact_path must be null or an absolute path")
    if not normalized.startswith("/"):
        raise ControlPacketError("artifact_path must be an absolute path when present")
    return normalized


def _summary_is_placeholder(summary: str) -> bool:
    return summary.strip().lower() in PLACEHOLDER_SUMMARIES


def validate_control_packet(packet: dict[str, Any], *, expected_marker: str | None = None) -> dict[str, Any]:
    if not isinstance(packet, dict):
        raise ControlPacketError("control packet must be a JSON object")

    schema_version = _normalize_text_field(packet, "schema_version")
    if schema_version != SCHEMA_VERSION:
        raise ControlPacketError(
            f"unsupported schema_version: {schema_version} (expected {SCHEMA_VERSION})"
        )

    state = _normalize_text_field(packet, "state")
    if state not in STATE_RESULT_MAP:
        raise ControlPacketError(f"unsupported state: {state}")

    result = _normalize_text_field(packet, "result")
    expected_result = STATE_RESULT_MAP[state]
    if result != expected_result:
        raise ControlPacketError(
            f"state/result mismatch: state={state} result={result} expected={expected_result}"
        )

    marker = _normalize_text_field(packet, "marker")
    if not MARKER_RE.fullmatch(marker):
        raise ControlPacketError(f"invalid marker format: {marker}")
    if expected_marker is not None and marker != expected_marker:
        raise ControlPacketError(
            f"marker prefix mismatch: expected {expected_marker} actual {marker}"
        )

    summary = _normalize_text_field(packet, "summary")
    if state in TERMINAL_STATES and _summary_is_placeholder(summary):
        raise ControlPacketError("terminal packet summary must not be placeholder-only")

    artifact_path = _normalize_artifact_path(packet.get("artifact_path"))
    try:
        task_source_ref = maybe_normalize_task_source_ref(
            packet.get("task_source_ref"),
            expected_task_type=TASK_TYPE_CMUX,
        )
    except TaskSourceContractError as exc:
        raise ControlPacketError(str(exc)) from exc
    if task_source_ref is None:
        raise ControlPacketError("task_source_ref is required for all control packets")
    assignment_id = _normalize_text_field(packet, "assignment_id")
    if assignment_id != task_source_ref["assignment_id"]:
        raise ControlPacketError("assignment_id must match task_source_ref.assignment_id")
    if artifact_path is not None and artifact_path != task_source_ref["evidence_path"]:
        raise ControlPacketError("artifact_path must match task_source_ref.evidence_path")

    normalized = dict(packet)
    normalized["schema_version"] = schema_version
    normalized["state"] = state
    normalized["result"] = result
    normalized["marker"] = marker
    normalized["summary"] = summary
    normalized["artifact_path"] = artifact_path
    normalized["assignment_id"] = assignment_id
    normalized["task_source_ref"] = task_source_ref
    return normalized


def _normalize_required_cmux_task_source_ref(
    value: Any,
    *,
    invalid_message: str,
    missing_message: str,
) -> dict[str, str]:
    try:
        task_source_ref = maybe_normalize_task_source_ref(
            value,
            expected_task_type=TASK_TYPE_CMUX,
        )
    except TaskSourceContractError as exc:
        raise ControlPacketError(f"{invalid_message}: {exc}") from exc
    if task_source_ref is None:
        raise ControlPacketError(missing_message)
    return task_source_ref


def _collect_task_source_mismatches(
    *,
    expected_task_source_ref: dict[str, str],
    actual_task_source_ref: dict[str, str],
) -> list[str]:
    mismatches: list[str] = []
    for field_name in TASK_SOURCE_LIVE_IDENTITY_FIELDS:
        expected_value = expected_task_source_ref[field_name]
        actual_value = actual_task_source_ref[field_name]
        if actual_value != expected_value:
            mismatches.append(
                f"{field_name} expected={expected_value} actual={actual_value}"
            )
    return mismatches


def _load_json_object(path: Path, *, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ControlPacketError(f"{label} unreadable: {path} ({exc})") from exc
    except json.JSONDecodeError as exc:
        raise ControlPacketError(
            f"{label} invalid json: {path} ({exc.msg})"
        ) from exc
    if not isinstance(payload, dict):
        raise ControlPacketError(f"{label} must be a JSON object: {path}")
    return payload


def _validate_linked_summary_artifact_for_current_assignment(
    artifact_path: str | None,
    *,
    expected_assignment_id: str | None,
    expected_task_source_ref: dict[str, str],
) -> None:
    if artifact_path is None:
        return
    summary_path = Path(artifact_path).expanduser().resolve()
    if not summary_path.exists():
        return

    payload = _load_json_object(summary_path, label="linked summary artifact")
    schema_version = str(payload.get("schema_version") or "").strip()
    if schema_version == SCHEMA_VERSION:
        try:
            normalized_summary = _validate_control_packet_for_current_assignment(
                payload,
                expected_assignment_id=expected_assignment_id,
                expected_task_source_ref=expected_task_source_ref,
                validate_linked_artifact=False,
            )
        except ControlPacketError as exc:
            raise ControlPacketError(f"linked summary artifact rejected: {exc}") from exc

        normalized_artifact_path = str(Path(normalized_summary["artifact_path"]).expanduser().resolve())
        if normalized_artifact_path != str(summary_path):
            raise ControlPacketError(
                "linked summary artifact self-path mismatch: "
                f"expected {summary_path} actual {normalized_summary['artifact_path']}"
            )
        return

    if not schema_version:
        raise ControlPacketError(f"linked summary artifact missing schema_version: {summary_path}")

    linked_assignment_id = _normalize_text_field(payload, "assignment_id")
    linked_task_source_ref = _normalize_required_cmux_task_source_ref(
        payload.get("task_source_ref"),
        invalid_message="linked summary artifact invalid current task_source_ref",
        missing_message="linked summary artifact missing current task_source_ref",
    )
    if expected_assignment_id and linked_assignment_id != expected_assignment_id:
        raise ControlPacketError(
            "linked summary artifact assignment mismatch: "
            f"expected {expected_assignment_id} actual {linked_assignment_id}"
        )

    mismatches = _collect_task_source_mismatches(
        expected_task_source_ref=expected_task_source_ref,
        actual_task_source_ref=linked_task_source_ref,
    )
    if mismatches:
        raise ControlPacketError(
            "linked summary artifact task_source mismatch: " + "; ".join(mismatches)
        )

    top_level_cycle_id = str(payload.get("cycle_id") or "").strip()
    if top_level_cycle_id and top_level_cycle_id != expected_task_source_ref["cycle_id"]:
        raise ControlPacketError(
            "linked summary artifact cycle_id mismatch: "
            f"expected {expected_task_source_ref['cycle_id']} actual {top_level_cycle_id}"
        )

    normalized_evidence_path = str(Path(linked_task_source_ref["evidence_path"]).expanduser().resolve())
    if normalized_evidence_path != str(summary_path):
        raise ControlPacketError(
            "linked summary artifact evidence_path mismatch: "
            f"expected {summary_path} actual {linked_task_source_ref['evidence_path']}"
        )


def _validate_control_packet_for_current_assignment(
    packet: dict[str, Any],
    *,
    expected_assignment_id: str | None = None,
    expected_task_source_ref: dict[str, Any] | None = None,
    validate_linked_artifact: bool,
) -> dict[str, Any]:
    normalized = validate_control_packet(packet)

    expected_assignment = (expected_assignment_id or "").strip()
    if expected_assignment and normalized["assignment_id"] != expected_assignment:
        raise ControlPacketError(
            "control packet assignment mismatch: "
            f"expected current assignment {expected_assignment} "
            f"actual {normalized['assignment_id']}"
        )

    if expected_task_source_ref is None:
        return normalized
    current_task_source_ref = _normalize_required_cmux_task_source_ref(
        expected_task_source_ref,
        invalid_message="invalid current task_source_ref",
        missing_message="missing current task_source_ref",
    )

    packet_task_source_ref = normalized["task_source_ref"]
    mismatches = _collect_task_source_mismatches(
        expected_task_source_ref=current_task_source_ref,
        actual_task_source_ref=packet_task_source_ref,
    )
    if mismatches:
        raise ControlPacketError(
            "control packet task_source mismatch: " + "; ".join(mismatches)
        )

    if validate_linked_artifact:
        _validate_linked_summary_artifact_for_current_assignment(
            normalized["artifact_path"],
            expected_assignment_id=expected_assignment or current_task_source_ref["assignment_id"],
            expected_task_source_ref=current_task_source_ref,
        )

    return normalized


def validate_control_packet_for_current_assignment(
    packet: dict[str, Any],
    *,
    expected_assignment_id: str | None = None,
    expected_task_source_ref: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return _validate_control_packet_for_current_assignment(
        packet,
        expected_assignment_id=expected_assignment_id,
        expected_task_source_ref=expected_task_source_ref,
        validate_linked_artifact=True,
    )


def extract_latest_control_packet(screen_text: str) -> dict[str, Any]:
    last_error: ControlPacketError | None = None
    for match in reversed(list(MARKER_RE.finditer(screen_text))):
        marker = match.group("marker")
        payload = screen_text[match.end() :]
        json_candidate = _extract_first_json_object(payload)
        if not json_candidate:
            continue
        try:
            packet = json.loads(json_candidate)
        except json.JSONDecodeError as exc:
            last_error = ControlPacketError(f"invalid packet json after {marker}: {exc.msg}")
            continue
        try:
            return validate_control_packet(packet, expected_marker=marker)
        except ControlPacketError as exc:
            last_error = exc
            continue
    if last_error is not None:
        raise last_error
    if PROSE_ONLY_COMPLETION_RE.search(screen_text):
        raise ControlPacketError("prose-only completion output detected; control packet missing")
    raise ControlPacketError("control packet not found")


def load_screen_text(args: argparse.Namespace) -> str:
    if args.screen_file:
        return Path(args.screen_file).expanduser().read_text(encoding="utf-8")
    if not sys.stdin.isatty():
        return sys.stdin.read()
    raise ControlPacketError("provide --screen-file or pipe screen text via stdin")


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate or extract workbot cmux control packets from screen text."
    )
    parser.add_argument(
        "--screen-file",
        help="Read pane screen text from a file instead of stdin.",
    )
    parser.add_argument(
        "--print-examples",
        action="store_true",
        help="Print example packets for all supported states and exit.",
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print JSON output.",
    )
    return parser


def main() -> int:
    parser = build_arg_parser()
    args = parser.parse_args()

    if args.print_examples:
        indent = 2 if args.pretty else None
        print(json.dumps(EXAMPLE_PACKETS, ensure_ascii=False, indent=indent))
        return 0

    try:
        screen_text = load_screen_text(args)
        packet = extract_latest_control_packet(screen_text)
    except ControlPacketError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1

    indent = 2 if args.pretty else None
    print(json.dumps({"ok": True, "packet": packet}, ensure_ascii=False, indent=indent))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
