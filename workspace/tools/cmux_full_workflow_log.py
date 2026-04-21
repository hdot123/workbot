#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from workspace.tools.cmux_control_packet import (
    ControlPacketError,
    validate_control_packet,
    validate_control_packet_for_current_assignment,
)
from workspace.tools.current_task_source import (
    TASK_TYPE_CMUX,
    TaskSourceContractError,
    build_cmux_task_source_ref,
    maybe_normalize_task_source_ref,
    task_source_id_for_cmux,
)
from workspace.tools.cmux_read_contract import (
    CONSUMER_STATE_CONTROL_PACKET_EXTRACTION,
    REQUIRED_VERIFICATION_PACKET_SLOTS,
    consumer_state_covers_control_packet,
    describe_verification_packet_contract,
    render_verification_packet_sources,
)
from workspace.tools.cmux_summary_artifact import build_summary_artifact, write_summary_artifact


SCHEMA_VERSION = "wb-cmux-workflow-log-v1"
MAIN_THREAD_ACTION_SCHEMA_VERSION = "wb-cmux-main-thread-action-v1"
WORKFLOW_RUN_INDEX_SCHEMA_VERSION = "wb-cmux-workflow-run-index-v1"
ACTIVE_STATUSES = {"ACTIVE", "RUNNING", "IN_PROGRESS"}
A6_REVIEW_STATES = {
    "waiting_input",
    "task_blocked",
    "audit_pending",
    "audit_failed",
    "approval_prompt",
    "approval_stuck",
}
BOT_ORDER = ("pm-bot", "dev-bot", "qa-bot", "doc-bot", "rea-bot")
A7_MANDATORY_WRITEBACK_TARGETS = BOT_ORDER
A7_TARGET_BY_PREFIX = {
    "PM": "pm-bot",
    "DEV": "dev-bot",
    "QA": "qa-bot",
    "DOC": "doc-bot",
    "REA": "rea-bot",
}
A7_TARGET_TOKEN_MARKERS = {
    "PMBOT": "pm-bot",
    "DEVBOT": "dev-bot",
    "QABOT": "qa-bot",
    "DOCBOT": "doc-bot",
    "REABOT": "rea-bot",
}
A7_MANDATORY_WRITEBACK_LABEL = "A7 mandatory writeback targets"
FINAL_REVIEWER_REQUIRED_COUNT = 3
NATIVE_PASS_CLAIM_FIELDS = ("decision", "verdict", "result", "outcome", "status")
NATIVE_PASS_CLAIM_MARKERS = {"pass", "passed", "native_pass"}
LOCAL_TZ = timezone(timedelta(hours=8))

DEFAULT_LIVE_JSON_NAME = "cmux-full-workflow-log-latest.json"
DEFAULT_LIVE_SUMMARY_NAME = "cmux-workflow-summary-latest.json"
DEFAULT_SAMPLE_JSON_NAME = "cmux-three-round-five-bot-sample-workflow-log.json"
DEFAULT_MAIN_THREAD_ACTIONS_JSONL_NAME = "cmux-main-thread-actions.jsonl"
DEFAULT_WORKFLOW_RUNS_DIR_NAME = "workflow-runs"

TIMESTAMP_LINE_RE = re.compile(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$")
KEY_RE_TEMPLATE = r"(?:^|\s){key}=(.*?)(?=(?:\s+[A-Za-z_][A-Za-z0-9_]*=)|$)"
DIRECT_REJECT_VALUE_MARKERS = {
    "direct_reject",
    "main_thread_direct_reject",
    "reject",
    "rejected",
}
DIRECT_REJECT_DETAIL_FIELDS = ("decision", "verdict", "result", "outcome", "action", "status")
DIRECT_REJECT_CANONICAL_DETAIL_FIELDS = ("decision", "verdict", "result", "outcome")
MAIN_THREAD_ACCEPTANCE_KIND = "main_thread_acceptance"
MAIN_THREAD_CLOSURE_KIND = "main_thread_closure"
MAIN_THREAD_DIRECT_REJECT_KIND = "main_thread_direct_reject"
MAIN_THREAD_REVIEW_KIND = "main_thread_review"
MAIN_THREAD_A8_ONLY_KINDS = {MAIN_THREAD_ACCEPTANCE_KIND}
MAIN_THREAD_A9_ONLY_KINDS = {MAIN_THREAD_CLOSURE_KIND, MAIN_THREAD_DIRECT_REJECT_KIND}
MAIN_THREAD_VALID_KINDS_BY_PHASE = {
    "A6": {MAIN_THREAD_REVIEW_KIND},
    "A8": {MAIN_THREAD_ACCEPTANCE_KIND},
    "A9": {MAIN_THREAD_CLOSURE_KIND, MAIN_THREAD_DIRECT_REJECT_KIND},
}


def utc_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


def load_json_if_exists(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, dict):
        return payload
    raise ValueError(f"expected JSON object at {path}")


def load_jsonl_if_exists(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    items: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        rendered = line.strip()
        if not rendered:
            continue
        payload = json.loads(rendered)
        if isinstance(payload, dict):
            items.append(payload)
    return items


def write_json(path: Path, payload: dict[str, Any]) -> Path:
    output = path.expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return output


def append_jsonl(path: Path, payload: dict[str, Any]) -> Path:
    output = path.expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False) + "\n")
    return output


def discover_control_packet_artifacts(runtime_path: Path) -> list[Path]:
    candidates: list[Path] = []
    for candidate in sorted(runtime_path.glob("*.json")):
        if not candidate.is_file():
            continue
        try:
            payload = json.loads(candidate.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(payload, dict):
            continue
        try:
            validate_control_packet(payload)
        except ControlPacketError:
            continue
        candidates.append(candidate.resolve())
    return candidates


def sanitize_path_token(text: str, fallback: str = "UNKNOWN") -> str:
    rendered = re.sub(r"[^A-Za-z0-9._-]+", "-", str(text or "").strip()).strip("-._")
    return rendered or fallback


def shorten_summary_line(text: str, limit: int = 160) -> str:
    rendered = " ".join(str(text or "").split())
    if len(rendered) <= limit:
        return rendered
    return rendered[: max(0, limit - 3)].rstrip() + "..."


def parse_timestamp(text: str) -> datetime | None:
    rendered = str(text or "").strip()
    if not rendered:
        return None
    for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
        try:
            parsed = datetime.strptime(rendered, fmt)
        except ValueError:
            continue
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=LOCAL_TZ)
        return parsed
    return None


def event_sort_key(event: dict[str, Any]) -> tuple[int, str, int]:
    parsed = parse_timestamp(str(event.get("at") or "").strip())
    ordinal = int(event.get("order") or 0)
    if parsed is None:
        return (1, "", ordinal)
    return (0, parsed.isoformat(), ordinal)


def _legacy_cmux_task_source_id(assignment_id: Any) -> str:
    rendered = str(assignment_id or "").strip()
    if not rendered:
        return ""
    return task_source_id_for_cmux(rendered)


def _resolve_assignment_deliverable(assignment: dict[str, Any]) -> str:
    deliverable = str(assignment.get("deliverable") or "").strip()
    if deliverable:
        return deliverable
    assignment_contract = assignment.get("assignment_contract")
    if isinstance(assignment_contract, dict):
        return str(assignment_contract.get("deliverable") or "").strip()
    return ""


def _normalize_current_task_sources(
    current_task_sources: Any,
) -> tuple[list[dict[str, str]], list[str]]:
    normalized: list[dict[str, str]] = []
    issues: list[str] = []
    if not isinstance(current_task_sources, list):
        return normalized, issues
    for index, item in enumerate(current_task_sources, start=1):
        try:
            normalized_item = maybe_normalize_task_source_ref(
                item,
                expected_task_type=TASK_TYPE_CMUX,
            )
        except TaskSourceContractError as exc:
            issues.append(f"current_task_sources[{index}] invalid: {exc}")
            continue
        if normalized_item is None:  # pragma: no cover - defensive
            issues.append(f"current_task_sources[{index}] is empty")
            continue
        normalized.append(normalized_item)
    return normalized, issues


def _derive_current_task_sources_from_active_assignments(
    assignment_payload: dict[str, Any],
    assignment_path: Path,
    active_assignments: list[dict[str, Any]],
) -> tuple[list[dict[str, str]], list[str]]:
    normalized: list[dict[str, str]] = []
    issues: list[str] = []
    cycle_id = str(assignment_payload.get("cycle_id") or assignment_payload.get("updated_at") or "").strip()
    for assignment in active_assignments:
        try:
            task_source_ref = maybe_normalize_task_source_ref(
                assignment.get("task_source_ref"),
                expected_task_type=TASK_TYPE_CMUX,
            )
        except TaskSourceContractError as exc:
            issues.append(
                f"active assignment {assignment.get('assignment_id') or '<unknown>'} has invalid task_source_ref: {exc}"
            )
            task_source_ref = None
        if task_source_ref is not None:
            normalized.append(task_source_ref)
            continue
        assignment_id = str(assignment.get("assignment_id") or "").strip()
        deliverable_path = _resolve_assignment_deliverable(assignment)
        if not assignment_id or not deliverable_path or not cycle_id:
            issues.append(
                f"active assignment {assignment_id or '<unknown>'} is missing task source contract fields"
            )
            continue
        normalized.append(
            build_cmux_task_source_ref(
                assignment_id=assignment_id,
                cycle_id=cycle_id,
                deliverable_path=deliverable_path,
                evidence_path=str(assignment_path),
                status=str(assignment.get("status") or "").strip().lower() or "active",
            )
        )
    return normalized, issues


def _resolve_current_task_sources(
    assignment_payload: dict[str, Any],
    assignment_path: Path,
    active_assignments: list[dict[str, Any]],
) -> tuple[list[dict[str, str]], list[str]]:
    normalized, issues = _normalize_current_task_sources(assignment_payload.get("current_task_sources"))
    if normalized:
        return normalized, issues
    derived, derived_issues = _derive_current_task_sources_from_active_assignments(
        assignment_payload,
        assignment_path,
        active_assignments,
    )
    return derived, [*issues, *derived_issues]


def _current_task_source_ids(current_task_sources: list[dict[str, str]]) -> set[str]:
    return {
        str(item.get("task_source_id") or "").strip()
        for item in current_task_sources
        if str(item.get("task_source_id") or "").strip()
    }


def _event_matches_current_task_sources(
    event: dict[str, Any],
    current_task_source_ids: set[str],
) -> bool:
    if not current_task_source_ids:
        return False
    try:
        task_source_ref = maybe_normalize_task_source_ref(
            event.get("task_source_ref"),
            expected_task_type=TASK_TYPE_CMUX,
        )
    except TaskSourceContractError:
        task_source_ref = None
    if task_source_ref is not None:
        return task_source_ref["task_source_id"] in current_task_source_ids
    return _legacy_cmux_task_source_id(event.get("assignment_id")) in current_task_source_ids


def _receipt_matches_current_task_sources(
    receipt_payload: dict[str, Any],
    current_task_source_ids: set[str],
    current_cycle_ids: set[str],
) -> bool:
    if not current_task_source_ids and not current_cycle_ids:
        return False
    cycle_id = str(receipt_payload.get("cycle_id") or "").strip()
    if cycle_id and cycle_id in current_cycle_ids:
        return True
    task_sources = receipt_payload.get("task_sources")
    if isinstance(task_sources, list):
        for item in task_sources:
            try:
                task_source_ref = maybe_normalize_task_source_ref(
                    item,
                    expected_task_type=TASK_TYPE_CMUX,
                )
            except TaskSourceContractError:
                continue
            if task_source_ref is not None and task_source_ref["task_source_id"] in current_task_source_ids:
                return True
    outcomes = receipt_payload.get("outcomes")
    if not isinstance(outcomes, list):
        return False
    for outcome in outcomes:
        if not isinstance(outcome, dict):
            continue
        try:
            task_source_ref = maybe_normalize_task_source_ref(
                outcome.get("task_source_ref"),
                expected_task_type=TASK_TYPE_CMUX,
            )
        except TaskSourceContractError:
            task_source_ref = None
        if task_source_ref is not None:
            if task_source_ref["task_source_id"] in current_task_source_ids:
                return True
            continue
        if _legacy_cmux_task_source_id(outcome.get("assignment_id")) in current_task_source_ids:
            return True
    return False


def _filter_control_packet_artifacts_for_current_sources(
    paths: list[Path],
    current_task_source_ids: set[str],
    task_source_by_assignment_id: dict[str, dict[str, str]],
) -> list[Path]:
    if not task_source_by_assignment_id and not current_task_source_ids:
        return []
    matched: list[Path] = []
    for candidate in paths:
        payload = load_json_if_exists(candidate)
        if not isinstance(payload, dict):
            continue
        assignment_id = str(payload.get("assignment_id") or "").strip()
        expected_task_source_ref = task_source_by_assignment_id.get(assignment_id)
        if expected_task_source_ref is not None:
            try:
                validate_control_packet_for_current_assignment(
                    payload,
                    expected_assignment_id=assignment_id or None,
                    expected_task_source_ref=expected_task_source_ref,
                )
            except ControlPacketError:
                continue
        else:
            try:
                task_source_ref = maybe_normalize_task_source_ref(
                    payload.get("task_source_ref"),
                    expected_task_type=TASK_TYPE_CMUX,
                )
            except TaskSourceContractError:
                continue
            if task_source_ref is None or task_source_ref["task_source_id"] not in current_task_source_ids:
                continue
        matched.append(candidate)
    return matched


def _task_source_by_assignment_id(
    active_assignments: list[dict[str, Any]],
    current_task_sources: list[dict[str, str]],
) -> dict[str, dict[str, str]]:
    mapping: dict[str, dict[str, str]] = {}
    for assignment in active_assignments:
        assignment_id = str(assignment.get("assignment_id") or "").strip()
        if not assignment_id:
            continue
        try:
            task_source_ref = maybe_normalize_task_source_ref(
                assignment.get("task_source_ref"),
                expected_task_type=TASK_TYPE_CMUX,
            )
        except TaskSourceContractError:
            task_source_ref = None
        if task_source_ref is not None:
            mapping[assignment_id] = task_source_ref
    for item in current_task_sources:
        assignment_id = str(item.get("assignment_id") or "").strip()
        if assignment_id and assignment_id not in mapping:
            mapping[assignment_id] = item
    return mapping


def _filter_consumer_payload_for_current_sources(
    consumer_payload: dict[str, Any] | None,
    task_source_by_assignment_id: dict[str, dict[str, str]],
) -> tuple[dict[str, Any] | None, int, list[str]]:
    if not isinstance(consumer_payload, dict):
        return consumer_payload, 0, []

    assignments = consumer_payload.get("assignments")
    if not isinstance(assignments, dict):
        return consumer_payload, 0, []

    filtered_payload = dict(consumer_payload)
    filtered_assignments: dict[str, Any] = {}
    archive_only_count = 0
    issues: list[str] = []

    for logical_target, entry in assignments.items():
        if not isinstance(entry, dict):
            filtered_assignments[logical_target] = entry
            continue

        filtered_entry = dict(entry)
        assignment_id = str(filtered_entry.get("assignment_id") or "").strip()
        expected_task_source_ref = task_source_by_assignment_id.get(assignment_id)
        control_packet = filtered_entry.get("control_packet")
        if isinstance(control_packet, dict):
            try:
                filtered_entry["control_packet"] = validate_control_packet_for_current_assignment(
                    control_packet,
                    expected_assignment_id=assignment_id or None,
                    expected_task_source_ref=expected_task_source_ref,
                )
            except ControlPacketError as exc:
                archive_only_count += 1
                filtered_entry.pop("control_packet", None)
                message = f"archive-only embedded control packet ignored: {exc}"
                existing_error = str(filtered_entry.get("control_packet_error") or "").strip()
                filtered_entry["control_packet_error"] = (
                    message if not existing_error else f"{existing_error}; {message}"
                )
                target_label = str(logical_target or assignment_id or "<unknown>").strip()
                issues.append(f"ignored archive-only consumer control packet for {target_label}: {exc}")

        filtered_assignments[logical_target] = filtered_entry

    filtered_payload["assignments"] = filtered_assignments
    return filtered_payload, archive_only_count, issues


def extract_field(text: str, key: str) -> str:
    pattern = re.compile(KEY_RE_TEMPLATE.format(key=re.escape(key)))
    match = pattern.search(text)
    if not match:
        return ""
    return match.group(1).strip()


def build_event(
    *,
    order: int,
    at: str,
    actor: str,
    phase: str,
    kind: str,
    source: str,
    summary: str,
    logical_target: str = "",
    assignment_id: str = "",
    round_id: str = "",
    task_source_ref: dict[str, Any] | None = None,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    event: dict[str, Any] = {
        "order": order,
        "at": at,
        "actor": actor,
        "phase": phase,
        "kind": kind,
        "source": source,
        "summary": summary,
    }
    if logical_target:
        event["logical_target"] = logical_target
    if assignment_id:
        event["assignment_id"] = assignment_id
    if round_id:
        event["round_id"] = round_id
    if task_source_ref:
        event["task_source_ref"] = task_source_ref
    if details:
        event["details"] = details
    return event


def parse_watcher_log_events(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8").splitlines()
    events: list[dict[str, Any]] = []
    pending_action: dict[str, str] | None = None
    order = 1
    index = 0
    while index < len(lines):
        line = lines[index].rstrip()
        if line.startswith("[action] "):
            pending_action = {
                "logical_target": extract_field(line, "logical_target"),
                "assignment_id": extract_field(line, "assignment_id"),
                "display_name": extract_field(line, "display_name"),
                "action": line.split()[-1].strip(),
            }
            index += 1
            continue
        if not TIMESTAMP_LINE_RE.match(line.strip()):
            index += 1
            continue

        timestamp = line.strip()
        header_lines: list[str] = []
        cursor = index + 1
        while cursor < len(lines):
            current = lines[cursor].rstrip()
            if current.startswith("-" * 80):
                cursor += 1
                break
            header_lines.append(current)
            cursor += 1
        while cursor < len(lines):
            current = lines[cursor].rstrip()
            if current.startswith("[action] ") or TIMESTAMP_LINE_RE.match(current.strip()):
                break
            cursor += 1

        logical_target = ""
        assignment_id = ""
        state = ""
        alert = ""
        blocking = ""
        for header_line in header_lines:
            logical_target = logical_target or extract_field(header_line, "logical_target")
            assignment_id = assignment_id or extract_field(header_line, "assignment_id")
            state = state or extract_field(header_line, "state")
            alert = alert or extract_field(header_line, "alert")
            blocking = blocking or extract_field(header_line, "blocking")

        if pending_action is not None:
            dispatch_target = pending_action.get("logical_target", "") or logical_target
            dispatch_assignment_id = pending_action.get("assignment_id", "") or assignment_id
            display_name = pending_action.get("display_name", "")
            action_name = pending_action.get("action", "") or "dispatch_task"
            events.append(
                build_event(
                    order=order,
                    at=timestamp,
                    actor="main-thread",
                    phase="A3",
                    kind="main_thread_dispatch",
                    source=str(path),
                    logical_target=dispatch_target,
                    assignment_id=dispatch_assignment_id,
                    summary=f"main-thread {action_name} -> {dispatch_target or 'unknown-target'}",
                    details={"display_name": display_name, "action": action_name},
                )
            )
            order += 1
            pending_action = None

        if logical_target or assignment_id or state:
            phase = "A5"
            if state in A6_REVIEW_STATES:
                phase = "A6"
            elif state in {"completed", "failed"}:
                phase = "A7"
            events.append(
                build_event(
                    order=order,
                    at=timestamp,
                    actor=logical_target or "watcher",
                    phase=phase,
                    kind="worker_state_snapshot",
                    source=str(path),
                    logical_target=logical_target,
                    assignment_id=assignment_id,
                    summary=f"{logical_target or 'worker'} state={state or 'unknown'} alert={alert or 'n/a'}",
                    details={"state": state, "alert": alert, "blocking": blocking},
                )
            )
            order += 1

        index = cursor
    return events


def derive_pending_handoffs(
    active_assignments: list[dict[str, Any]],
    hook_payload: dict[str, Any] | None,
    consumer_payload: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    hook_surfaces = {}
    if isinstance(hook_payload, dict):
        hook_surfaces = hook_payload.get("surfaces") or {}
        if not isinstance(hook_surfaces, dict):
            hook_surfaces = {}

    consumer_assignments = {}
    if isinstance(consumer_payload, dict):
        consumer_assignments = consumer_payload.get("assignments") or {}
        if not isinstance(consumer_assignments, dict):
            consumer_assignments = {}

    pending: list[dict[str, Any]] = []
    for assignment in active_assignments:
        logical_target = str(assignment.get("logical_target") or assignment.get("bot_name") or "").strip()
        assignment_id = str(assignment.get("assignment_id") or "").strip()
        surface_ref = str(assignment.get("surface_ref") or "").strip()

        consumer_entry = consumer_assignments.get(logical_target)
        if not isinstance(consumer_entry, dict):
            consumer_entry = {}
        consumer_assignment_id = str(consumer_entry.get("assignment_id") or "").strip()
        if consumer_assignment_id and consumer_assignment_id != assignment_id:
            consumer_entry = {}

        control_packet = consumer_entry.get("control_packet")
        if isinstance(control_packet, dict):
            packet_state = str(control_packet.get("state") or "").strip()
            packet_result = str(control_packet.get("result") or "").strip()
            if packet_state == "completed" and packet_result == "pass":
                pending.append(
                    {
                        "logical_target": logical_target,
                        "assignment_id": assignment_id,
                        "phase": "A7",
                        "reason": "completed_control_packet_requires_finish_cycle",
                    }
                )
                continue

        consumer_state = str(consumer_entry.get("state") or "").strip()
        if consumer_state in A6_REVIEW_STATES:
            pending.append(
                {
                    "logical_target": logical_target,
                    "assignment_id": assignment_id,
                    "phase": "A6",
                    "reason": "consumer_state_requires_commander_review",
                    "state": consumer_state,
                }
            )
            continue

        surface_state = hook_surfaces.get(surface_ref)
        if not isinstance(surface_state, dict):
            continue
        stop_count = int(surface_state.get("stop_count") or 0)
        notification_count = int(surface_state.get("notification_count") or 0)
        if stop_count <= 0 and notification_count <= 0:
            continue
        last_prompt_submit_at = str(surface_state.get("last_prompt_submit_at") or "").strip()
        last_stop_at = str(surface_state.get("last_stop_at") or "").strip()
        last_notification_at = str(surface_state.get("last_notification_at") or "").strip()
        latest_handoff = max(
            [item for item in (parse_timestamp(last_stop_at), parse_timestamp(last_notification_at)) if item is not None],
            default=None,
        )
        last_prompt_submit = parse_timestamp(last_prompt_submit_at)
        requires_review = latest_handoff is None
        if latest_handoff is not None:
            requires_review = last_prompt_submit is None or latest_handoff > last_prompt_submit
        if not requires_review:
            continue
        pending.append(
            {
                "logical_target": logical_target,
                "assignment_id": assignment_id,
                "phase": "A6",
                "reason": "surface_stop_or_notification_requires_commander_review",
                "stop_count": stop_count,
                "notification_count": notification_count,
                "last_event": str(surface_state.get("last_event") or "").strip(),
                "last_prompt_submit_at": last_prompt_submit_at,
                "last_stop_at": last_stop_at,
                "last_notification_at": last_notification_at,
            }
        )
    return pending


def _normalize_verdict_token(value: Any) -> str:
    rendered = re.sub(r"[^a-z0-9]+", "_", str(value or "").strip().lower()).strip("_")
    return rendered


def _is_direct_reject_marker(value: Any) -> bool:
    token = _normalize_verdict_token(value)
    return token in DIRECT_REJECT_VALUE_MARKERS


def _collect_direct_reject_details(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    details: list[dict[str, Any]] = []
    for event in events:
        if str(event.get("actor") or "").strip() != "main-thread":
            continue
        kind = str(event.get("kind") or "").strip()
        summary = str(event.get("summary") or "").strip()
        payload = event.get("details")
        detail_payload = payload if isinstance(payload, dict) else {}

        matched = _is_direct_reject_marker(kind) or _is_direct_reject_marker(summary)
        decision_value = ""
        for field in DIRECT_REJECT_DETAIL_FIELDS:
            field_value = detail_payload.get(field)
            if _is_direct_reject_marker(field_value):
                matched = True
                decision_value = str(field_value or "").strip()
                break

        if not matched:
            continue

        reason = ""
        for field in ("reason", "message", "why", "note", "detail"):
            field_value = str(detail_payload.get(field) or "").strip()
            if field_value:
                reason = field_value
                break
        if not reason:
            reason = summary
        details.append(
            {
                "at": str(event.get("at") or "").strip(),
                "phase": str(event.get("phase") or "").strip(),
                "kind": kind,
                "logical_target": str(event.get("logical_target") or "").strip(),
                "assignment_id": str(event.get("assignment_id") or "").strip(),
                "decision": decision_value or "direct_reject",
                "reason": reason,
            }
        )
    return details


def _extract_frozen_packet_id(payload: dict[str, Any] | None) -> str:
    if not isinstance(payload, dict):
        return ""
    for field in ("frozen_packet_id", "frozen_packet_version", "packet_id", "packet_version"):
        rendered = str(payload.get(field) or "").strip()
        if rendered:
            return rendered
    frozen_packet = payload.get("frozen_packet")
    if isinstance(frozen_packet, str):
        return frozen_packet.strip()
    if isinstance(frozen_packet, dict):
        for field in ("id", "packet_id", "version"):
            rendered = str(frozen_packet.get(field) or "").strip()
            if rendered:
                return rendered
    return ""


def _extract_transcript_ref(payload: dict[str, Any], *, review: bool) -> str:
    direct_fields = (
        ("review_transcript_path", "review_transcript_ref", "review_transcript")
        if review
        else ("dispatch_transcript_path", "dispatch_transcript_ref", "dispatch_transcript")
    )
    for field in direct_fields:
        rendered = str(payload.get(field) or "").strip()
        if rendered:
            return rendered
    evidence = payload.get("dispatch_evidence" if not review else "review_evidence")
    if isinstance(evidence, dict):
        for field in ("transcript_path", "transcript_ref", "tool_call_ref", "message_ref"):
            rendered = str(evidence.get(field) or "").strip()
            if rendered:
                return rendered
    return ""


def _details_claim_native_pass(details: dict[str, Any] | None) -> bool:
    if not isinstance(details, dict):
        return False
    return any(_normalize_verdict_token(details.get(field)) in NATIVE_PASS_CLAIM_MARKERS for field in NATIVE_PASS_CLAIM_FIELDS)


def _resolve_a7_target_from_token(token: Any) -> str:
    rendered = str(token or "").strip()
    if not rendered:
        return ""
    if rendered in A7_MANDATORY_WRITEBACK_TARGETS:
        return rendered
    if rendered.lower().startswith("idle-"):
        return ""
    prefix = rendered.split("-", 1)[0].upper()
    mapped = A7_TARGET_BY_PREFIX.get(prefix, "")
    if mapped:
        return mapped
    collapsed = re.sub(r"[^A-Z0-9]+", "", rendered.upper())
    for marker, logical_target in A7_TARGET_TOKEN_MARKERS.items():
        if marker in collapsed:
            return logical_target
    return ""


def _collect_required_a7_targets_from_cycle_id(cycle_id: str) -> list[str]:
    scope = str(cycle_id or "").strip().rsplit("|", 1)[-1]
    if "," not in scope:
        return []
    targets: list[str] = []
    for raw_token in scope.split(","):
        logical_target = _resolve_a7_target_from_token(raw_token)
        if logical_target and logical_target not in targets:
            targets.append(logical_target)
    return targets


def _collect_required_a7_targets_from_task_sources(task_sources: Any) -> list[str]:
    targets: list[str] = []
    if not isinstance(task_sources, list):
        return targets
    for item in task_sources:
        if not isinstance(item, dict):
            continue
        for token in (item.get("assignment_id"), item.get("task_source_id")):
            logical_target = _resolve_a7_target_from_token(token)
            if logical_target and logical_target not in targets:
                targets.append(logical_target)
        for logical_target in _collect_required_a7_targets_from_cycle_id(str(item.get("cycle_id") or "").strip()):
            if logical_target not in targets:
                targets.append(logical_target)
    return targets


def collect_a7_writeback_targets(
    receipt_payloads: list[dict[str, Any]],
    *,
    current_task_sources: Any = None,
) -> dict[str, Any]:
    latest_receipt = receipt_payloads[-1] if receipt_payloads else None
    required_targets = _collect_required_a7_targets_from_task_sources(current_task_sources)
    if isinstance(latest_receipt, dict):
        for logical_target in _collect_required_a7_targets_from_task_sources(latest_receipt.get("task_sources")):
            if logical_target not in required_targets:
                required_targets.append(logical_target)
        outcomes = latest_receipt.get("outcomes")
        if isinstance(outcomes, list):
            outcome_task_sources = [
                outcome.get("task_source_ref") for outcome in outcomes if isinstance(outcome, dict)
            ]
            for logical_target in _collect_required_a7_targets_from_task_sources(outcome_task_sources):
                if logical_target not in required_targets:
                    required_targets.append(logical_target)
    scope_confirmed = bool(required_targets)
    scope_issue = ""
    if not scope_confirmed:
        scope_issue = (
            "A7 dispatch scope is unconfirmed; required writeback targets could not be derived "
            "from current task source bindings"
        )
    present_targets: list[str] = []
    receipt_scope = [latest_receipt] if isinstance(latest_receipt, dict) else []
    for receipt in receipt_scope:
        outcomes = receipt.get("outcomes")
        if not isinstance(outcomes, list):
            continue
        for outcome in outcomes:
            if not isinstance(outcome, dict):
                continue
            logical_target = _resolve_a7_target_from_token(outcome.get("logical_target"))
            if not logical_target:
                prefix = str(outcome.get("prefix") or "").strip().upper()
                if not prefix:
                    task_id = str(outcome.get("task_id") or "").strip()
                    prefix = task_id.split("-", 1)[0].upper() if "-" in task_id else task_id.upper()
                logical_target = _resolve_a7_target_from_token(prefix)
            if logical_target in required_targets and logical_target not in present_targets:
                present_targets.append(logical_target)
    missing_targets = [target for target in required_targets if target not in present_targets]
    return {
        "required_targets": required_targets,
        "present_targets": present_targets,
        "missing_targets": missing_targets,
        "evaluated_cycle_id": str(latest_receipt.get("cycle_id") or "").strip()
        if isinstance(latest_receipt, dict)
        else "",
        "scope_confirmed": scope_confirmed,
        "scope_issue": scope_issue,
        "complete": isinstance(latest_receipt, dict) and scope_confirmed and not missing_targets,
    }


def _collect_final_reviewer_legality(events: list[dict[str, Any]]) -> dict[str, Any]:
    closure_event = None
    for event in events:
        if (
            str(event.get("actor") or "").strip() == "main-thread"
            and str(event.get("kind") or "").strip() == MAIN_THREAD_CLOSURE_KIND
        ):
            closure_event = event
    details = closure_event.get("details") if isinstance(closure_event, dict) else None
    closure_details = details if isinstance(details, dict) else {}
    frozen_packet_id = _extract_frozen_packet_id(closure_details)
    raw_reviewers = closure_details.get("final_reviewers")
    if not isinstance(raw_reviewers, list):
        raw_reviewers = []

    valid_reviewers: list[dict[str, Any]] = []
    invalid_reviewers: list[dict[str, Any]] = []
    reasons: list[str] = []
    seen_agent_ids: set[str] = set()

    if closure_event is not None and not frozen_packet_id:
        reasons.append("missing_frozen_packet")
    if closure_event is not None and len(raw_reviewers) < FINAL_REVIEWER_REQUIRED_COUNT:
        reasons.append("fewer_than_3_reviewers")

    for index, reviewer in enumerate(raw_reviewers, start=1):
        if not isinstance(reviewer, dict):
            invalid_reviewers.append({"index": index, "issues": ["invalid_reviewer_payload"]})
            continue
        reviewer_name = str(reviewer.get("reviewer") or reviewer.get("name") or reviewer.get("bot_name") or "").strip()
        agent_id = str(reviewer.get("agent_id") or "").strip()
        reviewer_packet_id = _extract_frozen_packet_id(reviewer)
        dispatch_transcript = _extract_transcript_ref(reviewer, review=False)
        review_transcript = _extract_transcript_ref(reviewer, review=True)
        reviewer_issues: list[str] = []
        if not reviewer_name or not agent_id:
            reviewer_issues.append("missing_reviewer_identity")
        if agent_id and agent_id in seen_agent_ids:
            reviewer_issues.append("duplicate_reviewer_agent_id")
            reasons.append("reviewer_identity_not_unique")
        if frozen_packet_id and reviewer_packet_id != frozen_packet_id:
            reviewer_issues.append("frozen_packet_mismatch")
            reasons.append("reviewers_not_on_same_frozen_packet")
        if reviewer.get("fork_context") is not False:
            reviewer_issues.append("fork_context_not_false")
            reasons.append("reviewer_fork_context_not_false")
        if not dispatch_transcript or not review_transcript:
            reviewer_issues.append("transcript_unverifiable")
            reasons.append("dispatch_transcript_unverifiable")
        reviewer_payload = {
            "reviewer": reviewer_name,
            "agent_id": agent_id,
            "frozen_packet_id": reviewer_packet_id,
            "fork_context": reviewer.get("fork_context"),
            "dispatch_transcript_path": dispatch_transcript,
            "review_transcript_path": review_transcript,
        }
        if reviewer_issues:
            reviewer_payload["issues"] = reviewer_issues
            invalid_reviewers.append(reviewer_payload)
            continue
        seen_agent_ids.add(agent_id)
        valid_reviewers.append(reviewer_payload)

    if closure_event is not None and len(valid_reviewers) < FINAL_REVIEWER_REQUIRED_COUNT:
        reasons.append("insufficient_legal_final_reviewers")

    deduped_reasons: list[str] = []
    for reason in reasons:
        if reason and reason not in deduped_reasons:
            deduped_reasons.append(reason)

    return {
        "closure_present": closure_event is not None,
        "closure_claims_native_pass": _details_claim_native_pass(closure_details),
        "required_reviewer_count": FINAL_REVIEWER_REQUIRED_COUNT,
        "frozen_packet_id": frozen_packet_id,
        "present_reviewer_count": len(raw_reviewers),
        "valid_reviewer_count": len(valid_reviewers),
        "valid_reviewers": valid_reviewers,
        "invalid_reviewers": invalid_reviewers,
        "missing_reasons": deduped_reasons,
        "ok": bool(closure_event is not None and frozen_packet_id and len(valid_reviewers) >= FINAL_REVIEWER_REQUIRED_COUNT),
    }


def _main_thread_acceptance_evidenced(events: list[dict[str, Any]]) -> bool:
    for event in events:
        if str(event.get("actor") or "").strip() != "main-thread":
            continue
        if str(event.get("kind") or "").strip() == MAIN_THREAD_ACCEPTANCE_KIND:
            return True
    return False


def _canonicalize_direct_reject_details(details: dict[str, Any] | None) -> dict[str, Any]:
    normalized = dict(details or {})
    for field in DIRECT_REJECT_CANONICAL_DETAIL_FIELDS:
        normalized.setdefault(field, "direct_reject")
    return normalized


def _details_contain_direct_reject(details: dict[str, Any] | None) -> bool:
    if not isinstance(details, dict):
        return False
    return any(_is_direct_reject_marker(details.get(field)) for field in DIRECT_REJECT_DETAIL_FIELDS)


def _validate_main_thread_action_payload(
    payload: dict[str, Any],
    *,
    path: Path,
    line_number: int,
    order: int,
) -> tuple[dict[str, Any] | None, list[str]]:
    issues: list[str] = []
    at = str(payload.get("at") or payload.get("generated_at") or "").strip()
    actor = str(payload.get("actor") or "").strip()
    phase = str(payload.get("phase") or "").strip().upper()
    kind = str(payload.get("kind") or "").strip()
    summary = str(payload.get("summary") or "").strip()
    details = payload.get("details")
    normalized_details = dict(details) if isinstance(details, dict) else None
    normalized_task_source_ref: dict[str, str] | None = None

    if not actor:
        return None, [
            f"{path}:{line_number} missing actor; main-thread journal entries must declare actor explicitly"
        ]
    if actor != "main-thread":
        return None, [f"{path}:{line_number} actor must be main-thread, got {actor!r}"]

    if kind == MAIN_THREAD_REVIEW_KIND and _details_contain_direct_reject(normalized_details):
        issues.append(
            f"{path}:{line_number} legacy direct reject normalized from main_thread_review to main_thread_direct_reject"
        )
        kind = MAIN_THREAD_DIRECT_REJECT_KIND
        phase = "A9"
        normalized_details = _canonicalize_direct_reject_details(normalized_details)

    if not phase:
        return None, [f"{path}:{line_number} missing phase for kind={kind or 'unknown'}"]
    if phase not in MAIN_THREAD_VALID_KINDS_BY_PHASE:
        return None, [f"{path}:{line_number} invalid phase {phase!r} for main-thread journal"]
    if not kind:
        return None, [f"{path}:{line_number} missing kind for phase={phase}"]

    allowed_kinds = MAIN_THREAD_VALID_KINDS_BY_PHASE.get(phase, set())
    if kind not in allowed_kinds:
        return None, [f"{path}:{line_number} kind={kind!r} is not legal in phase={phase!r}"]
    if not summary:
        return None, [f"{path}:{line_number} missing summary for kind={kind}"]

    if kind == MAIN_THREAD_DIRECT_REJECT_KIND:
        normalized_details = _canonicalize_direct_reject_details(normalized_details)
    try:
        normalized_task_source_ref = maybe_normalize_task_source_ref(
            payload.get("task_source_ref"),
            expected_task_type=TASK_TYPE_CMUX,
        )
    except TaskSourceContractError as exc:
        issues.append(f"{path}:{line_number} invalid task_source_ref: {exc}")
    if normalized_task_source_ref is not None:
        assignment_id = str(payload.get("assignment_id") or "").strip()
        if assignment_id and assignment_id != normalized_task_source_ref["assignment_id"]:
            issues.append(
                f"{path}:{line_number} assignment_id does not match task_source_ref.assignment_id"
            )

    event = build_event(
        order=order,
        at=at,
        actor=actor,
        phase=phase,
        kind=kind,
        source=str(payload.get("source") or path),
        logical_target=str(payload.get("logical_target") or "").strip(),
        assignment_id=str(payload.get("assignment_id") or "").strip(),
        round_id=str(payload.get("round_id") or "").strip(),
        task_source_ref=normalized_task_source_ref,
        summary=summary,
        details=normalized_details,
    )
    return event, issues


def _filter_terminal_direct_reject_conflicts(
    events: list[dict[str, Any]],
    *,
    path: Path,
) -> tuple[list[dict[str, Any]], list[str]]:
    if not any(str(event.get("kind") or "").strip() == MAIN_THREAD_DIRECT_REJECT_KIND for event in events):
        return events, []

    filtered: list[dict[str, Any]] = []
    issues: list[str] = []
    for event in events:
        kind = str(event.get("kind") or "").strip()
        if kind in {MAIN_THREAD_ACCEPTANCE_KIND, MAIN_THREAD_CLOSURE_KIND}:
            issues.append(
                f"{path} invalid same-attempt coexistence: {kind} cannot coexist with terminal main_thread_direct_reject"
            )
            continue
        filtered.append(event)
    return filtered, issues


def _normalize_main_thread_action_inputs(
    *,
    phase: str,
    kind: str,
    details: dict[str, Any] | None,
) -> tuple[str, str, dict[str, Any] | None]:
    normalized_phase = str(phase).strip().upper()
    normalized_kind = str(kind).strip()
    normalized_details = dict(details or {})

    if normalized_kind == MAIN_THREAD_REVIEW_KIND and normalized_phase != "A6":
        raise ValueError(f"{normalized_kind} must use phase A6")
    if normalized_kind in MAIN_THREAD_A8_ONLY_KINDS and normalized_phase != "A8":
        raise ValueError(f"{normalized_kind} must use phase A8")
    if normalized_kind in MAIN_THREAD_A9_ONLY_KINDS and normalized_phase != "A9":
        raise ValueError(f"{normalized_kind} must use phase A9")
    if normalized_kind == MAIN_THREAD_DIRECT_REJECT_KIND:
        normalized_details = _canonicalize_direct_reject_details(normalized_details)

    return normalized_phase, normalized_kind, normalized_details or None


def _workflow_next_action(
    pending: dict[str, Any] | None,
    *,
    finish_receipt_count: int,
    a7_writeback_complete: bool,
    a7_scope_confirmed: bool,
    a7_scope_issue: str,
    a7_missing_writeback_targets: list[str],
    acceptance_evidenced: bool,
    closure_evidenced: bool,
    closure_claims_native_pass: bool,
    has_direct_reject: bool,
    final_reviewer_legality_ok: bool,
    hard_gap_reasons: list[str],
) -> str:
    if has_direct_reject:
        return "Direct reject is recorded; this run/thread is terminal and must not be reopened or retried."
    if finish_receipt_count > 0 and not a7_writeback_complete:
        if not a7_scope_confirmed:
            return a7_scope_issue or (
                "A7 writeback cannot be accepted until current task dispatch scope is confirmed"
            )
        rendered_targets = ", ".join(a7_missing_writeback_targets) if a7_missing_writeback_targets else "unknown-targets"
        return f"A7 local writeback is partial; mandatory targets still missing: {rendered_targets}."
    if closure_evidenced and not acceptance_evidenced:
        return "Main-thread closure is recorded, but the matching A8 acceptance is still required."
    if closure_evidenced and closure_claims_native_pass and not final_reviewer_legality_ok:
        return (
            "Closure is recorded but final reviewer legality is invalid; native-pass remains unavailable "
            "until one frozen packet is reviewed by 3 fork_context=false reviewers with transcript-backed dispatch proof."
        )
    if closure_evidenced and hard_gap_reasons:
        return "Closure is evidenced but blocked by hard gaps; backfill missing evidence and clear provenance violations."
    if closure_evidenced and not closure_claims_native_pass:
        return "No action required; main-thread acceptance and closure are already evidenced."
    if closure_evidenced and not hard_gap_reasons:
        return "No action required; main-thread closure is already evidenced."
    if pending:
        reason = str(pending.get("reason") or "").strip()
        if reason == "completed_control_packet_requires_finish_cycle":
            return "Run finish-cycle to complete A7 local writeback for the completed control packet."
        if reason in {"consumer_state_requires_commander_review", "surface_stop_or_notification_requires_commander_review"}:
            return "Main-thread should review the pending worker state; no A8/A9 pass claim is legal yet."
    if acceptance_evidenced and not closure_evidenced:
        return "Main-thread acceptance is recorded; A9 closure is still required."
    if finish_receipt_count > 0:
        return "Main-thread should record A8 acceptance and then A9 closure."
    return "Wait for worker completion or refresh watcher evidence before commander review."


def build_live_workflow_summary(log_payload: dict[str, Any], log_path: Path) -> dict[str, Any]:
    summary = log_payload.get("summary") or {}
    if not isinstance(summary, dict):
        summary = {}
    pending_handoffs = log_payload.get("pending_handoffs") or []
    if not isinstance(pending_handoffs, list):
        pending_handoffs = []
    active_assignments = log_payload.get("active_assignments") or []
    if not isinstance(active_assignments, list):
        active_assignments = []
    current_task_sources = log_payload.get("current_task_sources") or []
    if not isinstance(current_task_sources, list):
        current_task_sources = []

    active_assignment_count = int(summary.get("active_assignment_count") or 0)
    current_task_source_count = int(summary.get("current_task_source_count") or len(current_task_sources) or 0)
    finish_receipt_count = int(summary.get("finish_receipt_count") or 0)
    a7_writeback_complete = bool(summary.get("a7_writeback_complete"))
    a7_scope_confirmed = bool(summary.get("a7_scope_confirmed", True))
    a7_scope_issue = str(summary.get("a7_scope_issue") or "").strip()
    a7_missing_writeback_targets = summary.get("a7_missing_writeback_targets") or []
    if not isinstance(a7_missing_writeback_targets, list):
        a7_missing_writeback_targets = []
    main_thread_action_count = int(summary.get("main_thread_action_count") or 0)
    main_thread_action_validation_issue_count = int(summary.get("main_thread_action_validation_issue_count") or 0)
    acceptance_evidenced = bool(summary.get("main_thread_acceptance_evidenced"))
    consumer_state_present = bool(summary.get("consumer_state_present"))
    hook_violation_count = int(summary.get("hook_provenance_violation_count") or 0)
    closure_evidenced = bool(summary.get("main_thread_closure_evidenced"))
    final_reviewer_legality = summary.get("final_reviewer_legality") or {}
    if not isinstance(final_reviewer_legality, dict):
        final_reviewer_legality = {}
    closure_claims_native_pass = bool(final_reviewer_legality.get("closure_claims_native_pass"))
    final_reviewer_legality_ok = bool(summary.get("final_reviewer_legality_ok"))
    direct_reject_details = summary.get("direct_reject_details") or []
    if not isinstance(direct_reject_details, list):
        direct_reject_details = []

    verification_packet = log_payload.get("verification_packet") or {}
    if not isinstance(verification_packet, dict):
        verification_packet = {}
    verification_missing_slots = verification_packet.get("missing_slots") or []
    if not isinstance(verification_missing_slots, list):
        verification_missing_slots = []

    verification_contract = describe_verification_packet_contract()
    proof_basis = str(verification_contract.get("proof_basis") or "").strip()
    verification_slot_order = verification_contract.get("slot_order") or []
    if not isinstance(verification_slot_order, list):
        verification_slot_order = list(REQUIRED_VERIFICATION_PACKET_SLOTS)

    primary_pending = pending_handoffs[0] if pending_handoffs and isinstance(pending_handoffs[0], dict) else None
    primary_active = active_assignments[0] if active_assignments and isinstance(active_assignments[0], dict) else None
    primary_task_source = current_task_sources[0] if current_task_sources and isinstance(current_task_sources[0], dict) else None
    logical_target = ""
    assignment_id = ""
    if primary_pending:
        logical_target = str(primary_pending.get("logical_target") or "").strip()
        assignment_id = str(primary_pending.get("assignment_id") or "").strip()
    if primary_active and not logical_target:
        logical_target = str(primary_active.get("logical_target") or primary_active.get("bot_name") or "").strip()
        assignment_id = str(primary_active.get("assignment_id") or "").strip()
    if primary_task_source and not assignment_id:
        assignment_id = str(primary_task_source.get("assignment_id") or "").strip()

    has_direct_reject = bool(direct_reject_details)
    missing_evidence: list[str] = []
    if current_task_source_count <= 0:
        missing_evidence.append("current task source")
    if not consumer_state_present:
        missing_evidence.append("consumer-state")
    if finish_receipt_count <= 0:
        missing_evidence.append("finish receipt")
    elif not a7_writeback_complete:
        if not a7_scope_confirmed:
            missing_evidence.append("A7 dispatch scope")
        missing_evidence.append(A7_MANDATORY_WRITEBACK_LABEL)
    if not has_direct_reject and not acceptance_evidenced:
        missing_evidence.append("main-thread acceptance")
    if main_thread_action_count <= 0:
        missing_evidence.append("main-thread action")
    if hook_violation_count > 0:
        missing_evidence.append("hook provenance clean state")
    if closure_evidenced and closure_claims_native_pass and not final_reviewer_legality_ok:
        missing_evidence.append("final reviewer legality")

    slot_to_label = {
        "control_packet": "control packet",
        "consumer_state": "consumer-state",
        "finish_receipt": "finish receipt",
        "workflow_log": "workflow log",
        "main_thread_actions": "main-thread action",
    }
    for slot in verification_missing_slots:
        label = slot_to_label.get(str(slot), str(slot))
        if label and label not in missing_evidence:
            missing_evidence.append(label)

    hard_gap_reasons: list[str] = []
    if finish_receipt_count > 0 and not a7_writeback_complete:
        hard_gap_reasons.append("A7 dispatch scope unconfirmed" if not a7_scope_confirmed else "partial A7 writeback")
    if closure_evidenced and closure_claims_native_pass and not final_reviewer_legality_ok:
        hard_gap_reasons.append("final reviewer legality")
    if hook_violation_count > 0:
        hard_gap_reasons.append("hook provenance violation")
    if has_direct_reject:
        missing_evidence = []
        hard_gap_reasons = []
    non_final_reviewer_hard_gaps = [reason for reason in hard_gap_reasons if reason != "final reviewer legality"]

    native_pass = (
        closure_evidenced
        and closure_claims_native_pass
        and final_reviewer_legality_ok
        and not has_direct_reject
        and not missing_evidence
        and not hard_gap_reasons
    )
    accepted_and_closed = (
        closure_evidenced
        and acceptance_evidenced
        and not closure_claims_native_pass
        and not has_direct_reject
        and not missing_evidence
        and not hard_gap_reasons
    )
    legal_verdict = (
        "direct_reject"
        if has_direct_reject
        else "native_pass"
        if native_pass
        else "accepted"
        if accepted_and_closed
        else ""
    )

    current_phase = "A5"
    current_state = "running"
    outcome = "in_progress"
    if has_direct_reject:
        current_phase = "A9"
        current_state = "failed"
        outcome = "direct_reject"
    elif primary_pending:
        current_phase = str(primary_pending.get("phase") or "A6").strip() or "A6"
        current_state = "blocked"
        outcome = "pending_handoff"
    elif native_pass:
        current_phase = "A9"
        current_state = "passed"
        outcome = "native_pass"
    elif accepted_and_closed:
        current_phase = "A9"
        current_state = "passed"
        outcome = "accepted_and_closed"
    elif finish_receipt_count > 0 and not a7_writeback_complete:
        current_phase = "A7"
        current_state = "blocked"
        outcome = "a7_partial_writeback"
    elif closure_evidenced and closure_claims_native_pass and not final_reviewer_legality_ok and not non_final_reviewer_hard_gaps:
        current_phase = "A9"
        current_state = "blocked"
        outcome = "closure_blocked_by_final_reviewer_legality"
    elif closure_evidenced and hard_gap_reasons:
        current_phase = "A9"
        current_state = "blocked"
        outcome = "closure_blocked_by_hard_gaps"
    elif closure_evidenced and not acceptance_evidenced:
        current_phase = "A9"
        current_state = "blocked"
        outcome = "closure_missing_acceptance"
    elif main_thread_action_count > 0:
        current_phase = "A8"
        current_state = "running"
        outcome = "awaiting_closure"
    elif finish_receipt_count > 0:
        current_phase = "A8"
        current_state = "blocked"
        outcome = "awaiting_main_thread_acceptance"
    elif active_assignment_count <= 0:
        current_phase = "IDLE"
        current_state = "blocked"
        outcome = "idle_without_closure"

    if has_direct_reject:
        reject_detail = direct_reject_details[0] if isinstance(direct_reject_details[0], dict) else {}
        reject_reason = str(reject_detail.get("reason") or "direct reject recorded by main-thread").strip()
        line_one = f"{current_phase} rejected: main-thread direct reject terminates this run ({reject_reason})."
    elif native_pass:
        line_one = "A9 passed: fresh native-pass proof is complete and exclusive of any direct reject."
    elif accepted_and_closed:
        line_one = "A9 passed: main-thread acceptance and closure are evidenced for this run."
    elif finish_receipt_count > 0 and not a7_writeback_complete and not a7_scope_confirmed:
        line_one = "A7 blocked: current task dispatch scope is unconfirmed, so required writeback targets cannot be derived."
    elif finish_receipt_count > 0 and not a7_writeback_complete:
        rendered_targets = ", ".join(a7_missing_writeback_targets) if a7_missing_writeback_targets else "unknown-targets"
        line_one = f"A7 blocked: local writeback is partial; mandatory targets still missing ({rendered_targets})."
    elif closure_evidenced and closure_claims_native_pass and not final_reviewer_legality_ok and not non_final_reviewer_hard_gaps:
        line_one = "A9 blocked: closure is evidenced but frozen-packet final-reviewer legality is incomplete or invalid."
    elif closure_evidenced and hard_gap_reasons:
        line_one = "A9 blocked: closure is evidenced but hard evidence/provenance gaps still exist."
    elif closure_evidenced and not acceptance_evidenced:
        line_one = "A9 blocked: closure is recorded, but main-thread acceptance is still missing."
    elif current_phase == "A8" and finish_receipt_count > 0 and main_thread_action_count <= 0:
        line_one = "A8 blocked: A7 local writeback exists, but main-thread acceptance/closure evidence is still missing."
    elif primary_pending:
        reason = str(primary_pending.get("reason") or "commander handoff pending").strip()
        target_text = f"{logical_target} / {assignment_id}" if logical_target or assignment_id else "current active assignment"
        line_one = f"{current_phase} blocked on {target_text}: {reason}."
    elif active_assignment_count > 0:
        target_text = f"{logical_target} / {assignment_id}" if logical_target or assignment_id else f"{active_assignment_count} active assignments"
        line_one = f"A5 running: {target_text} is still in the worker execution chain."
    else:
        line_one = "Workflow is idle; no legal current task source is bound, and historical artifacts remain archive-only."

    if has_direct_reject:
        line_two = (
            f"Direct reject details: {', '.join(str(item.get('reason') or '').strip() for item in direct_reject_details[:2] if isinstance(item, dict)) or 'none'}."
        )
    elif missing_evidence:
        line_two = f"Missing evidence: {', '.join(missing_evidence[:4])}."
    else:
        line_two = (
            "Evidence chain is complete across control packet, consumer-state, finish receipt, "
            "workflow log, and main-thread journal."
        )

    next_action = _workflow_next_action(
        primary_pending,
        finish_receipt_count=finish_receipt_count,
        a7_writeback_complete=a7_writeback_complete,
        a7_scope_confirmed=a7_scope_confirmed,
        a7_scope_issue=a7_scope_issue,
        a7_missing_writeback_targets=a7_missing_writeback_targets,
        acceptance_evidenced=acceptance_evidenced,
        closure_evidenced=closure_evidenced,
        closure_claims_native_pass=closure_claims_native_pass,
        has_direct_reject=has_direct_reject,
        final_reviewer_legality_ok=final_reviewer_legality_ok,
        hard_gap_reasons=hard_gap_reasons,
    )
    line_three = f"Next: {next_action}"
    archive = log_payload.get("archive") or {}
    if not isinstance(archive, dict):
        archive = {}

    artifact = build_summary_artifact(
        title="cmux workflow status",
        status=current_state,
        summary_lines=[
            shorten_summary_line(line_one),
            shorten_summary_line(line_two),
            shorten_summary_line(line_three),
        ],
        source="cmux_full_workflow_log",
        primary_sidecar_path=str(log_path),
        sidecar_paths=[str(log_path)],
        extra={
            "outcome": outcome,
            "current_phase": current_phase,
            "current_state": current_state,
            "logical_target": logical_target,
            "assignment_id": assignment_id,
            "current_task_source_count": current_task_source_count,
            "active_assignment_count": active_assignment_count,
            "pending_handoff_count": len(pending_handoffs),
            "finish_receipt_count": finish_receipt_count,
            "a7_writeback_complete": a7_writeback_complete,
            "a7_scope_confirmed": a7_scope_confirmed,
            "a7_scope_issue": a7_scope_issue,
            "a7_missing_writeback_targets": a7_missing_writeback_targets,
            "main_thread_action_count": main_thread_action_count,
            "main_thread_action_validation_issue_count": main_thread_action_validation_issue_count,
            "main_thread_acceptance_evidenced": acceptance_evidenced,
            "main_thread_closure_evidenced": closure_evidenced,
            "missing_evidence": missing_evidence,
            "hard_gap_reasons": hard_gap_reasons,
            "proof_basis": proof_basis,
            "verification_slot_order": verification_slot_order,
            "verification_missing_slots": verification_missing_slots,
            "direct_reject_count": len(direct_reject_details),
            "direct_reject_details": direct_reject_details,
            "final_reviewer_legality": final_reviewer_legality,
            "final_reviewer_legality_ok": final_reviewer_legality_ok,
            "legal_verdict": legal_verdict,
            "native_pass": native_pass,
            "next_action": next_action,
            "archive_bundle_dir": str(archive.get("bundle_dir") or "").strip(),
            "archive_workflow_log_path": str(archive.get("workflow_log_path") or "").strip(),
            "archive_workflow_summary_path": str(archive.get("workflow_summary_path") or "").strip(),
            "task_date": str(archive.get("date") or "").strip(),
            "task_run_number": int(archive.get("run_number") or 0),
        },
    )
    return artifact


def load_main_thread_action_events(path: Path) -> tuple[list[dict[str, Any]], list[str]]:
    events: list[dict[str, Any]] = []
    issues: list[str] = []
    order = 1
    for line_number, payload in enumerate(load_jsonl_if_exists(path), start=1):
        event, event_issues = _validate_main_thread_action_payload(
            payload,
            path=path,
            line_number=line_number,
            order=order,
        )
        issues.extend(event_issues)
        if event is None:
            continue
        events.append(event)
        order += 1
    filtered_events, conflict_issues = _filter_terminal_direct_reject_conflicts(events, path=path)
    issues.extend(conflict_issues)
    return filtered_events, issues


def load_run_index(path: Path) -> dict[str, Any]:
    payload = load_json_if_exists(path)
    if payload is None:
        return {
            "schema_version": WORKFLOW_RUN_INDEX_SCHEMA_VERSION,
            "counters": {},
            "entries": {},
        }
    counters = payload.get("counters")
    entries = payload.get("entries")
    if not isinstance(counters, dict) or not isinstance(entries, dict):
        return {
            "schema_version": WORKFLOW_RUN_INDEX_SCHEMA_VERSION,
            "counters": {},
            "entries": {},
        }
    payload["schema_version"] = WORKFLOW_RUN_INDEX_SCHEMA_VERSION
    return payload


def resolve_archive_context(runtime_path: Path, log_payload: dict[str, Any]) -> dict[str, Any]:
    summary = log_payload.get("summary") or {}
    if not isinstance(summary, dict):
        summary = {}
    current_task_sources = log_payload.get("current_task_sources") or []
    if not isinstance(current_task_sources, list):
        current_task_sources = []
    active_assignments = log_payload.get("active_assignments") or []
    if not isinstance(active_assignments, list):
        active_assignments = []
    pending_handoffs = log_payload.get("pending_handoffs") or []
    if not isinstance(pending_handoffs, list):
        pending_handoffs = []

    primary_task_source = current_task_sources[0] if current_task_sources and isinstance(current_task_sources[0], dict) else None
    primary_assignment: dict[str, Any] | None = None
    if primary_task_source is None and pending_handoffs and isinstance(pending_handoffs[0], dict):
        primary_assignment = pending_handoffs[0]
    elif primary_task_source is None and active_assignments and isinstance(active_assignments[0], dict):
        primary_assignment = active_assignments[0]

    assignment_id = ""
    logical_target = ""
    task_token = ""
    if primary_task_source:
        assignment_id = str(primary_task_source.get("assignment_id") or "").strip()
        task_token = sanitize_path_token(
            str(primary_task_source.get("task_source_id") or ""),
            fallback="UNKNOWN-TASK",
        )
    elif primary_assignment:
        assignment_id = str(primary_assignment.get("assignment_id") or "").strip()
        logical_target = str(primary_assignment.get("logical_target") or primary_assignment.get("bot_name") or "").strip()

    assignment_updated_at = str(summary.get("assignment_updated_at") or "").strip()
    generated_at = str(log_payload.get("generated_at") or "").strip()
    date_token = sanitize_path_token((assignment_updated_at or generated_at)[:10], fallback="unknown-date")
    if task_token:
        pass
    elif assignment_id:
        task_token = sanitize_path_token(assignment_id, fallback="UNKNOWN-TASK")
    elif logical_target:
        task_token = sanitize_path_token(logical_target, fallback="UNKNOWN-TASK")
    else:
        active_count = int(summary.get("active_assignment_count") or 0)
        task_token = f"MULTI-{active_count}-ACTIVE" if active_count > 1 else "IDLE"

    run_base_key = f"{date_token}::{task_token}"
    run_instance_key = f"{run_base_key}::{sanitize_path_token(assignment_updated_at or generated_at, fallback='unknown-instance')}"
    index_path = runtime_path / DEFAULT_WORKFLOW_RUNS_DIR_NAME / "workflow-run-index.json"
    index_payload = load_run_index(index_path)
    counters = index_payload.setdefault("counters", {})
    entries = index_payload.setdefault("entries", {})
    if run_instance_key in entries and isinstance(entries[run_instance_key], dict):
        entry = entries[run_instance_key]
        run_number = int(entry.get("run_number") or 1)
        bundle_dir = Path(
            str(
                entry.get("bundle_dir")
                or runtime_path / DEFAULT_WORKFLOW_RUNS_DIR_NAME / date_token / task_token / f"run-{run_number:03d}"
            )
        )
    else:
        current_counter = int(counters.get(run_base_key) or 0) + 1
        counters[run_base_key] = current_counter
        run_number = current_counter
        bundle_dir = runtime_path / DEFAULT_WORKFLOW_RUNS_DIR_NAME / date_token / task_token / f"run-{run_number:03d}"
        entries[run_instance_key] = {
            "date": date_token,
            "task_token": task_token,
            "run_number": run_number,
            "bundle_dir": str(bundle_dir),
            "assignment_id": assignment_id,
            "logical_target": logical_target,
            "assignment_updated_at": assignment_updated_at,
        }
        write_json(index_path, index_payload)

    return {
        "date": date_token,
        "task_token": task_token,
        "run_number": run_number,
        "bundle_dir": str(bundle_dir),
        "workflow_log_path": str(bundle_dir / "workflow-log.json"),
        "workflow_summary_path": str(bundle_dir / "workflow-summary.json"),
        "assignment_id": assignment_id,
        "logical_target": logical_target,
    }


def _resolve_main_thread_action_task_source_ref(
    runtime_path: Path,
    *,
    task_source_ref: dict[str, Any] | None,
    assignment_id: str,
) -> dict[str, str]:
    if task_source_ref is not None:
        normalized = maybe_normalize_task_source_ref(
            task_source_ref,
            expected_task_type=TASK_TYPE_CMUX,
        )
        if normalized is None:  # pragma: no cover - defensive
            raise ValueError("task_source_ref normalization returned None")
        return normalized

    assignment_path = runtime_path / "cmux-assignment.json"
    assignment_payload = load_json_if_exists(assignment_path)
    if assignment_payload is None:
        raise ValueError("cmux-assignment.json is required to derive current task source")
    assignments = assignment_payload.get("assignments") or []
    if not isinstance(assignments, list):
        raise ValueError("cmux-assignment.json assignments payload is invalid")
    active_assignments = [
        item
        for item in assignments
        if isinstance(item, dict)
        and str(item.get("status") or "").strip().upper() in ACTIVE_STATUSES
    ]
    current_task_sources, issues = _resolve_current_task_sources(
        assignment_payload,
        assignment_path,
        active_assignments,
    )
    if issues:
        raise ValueError("; ".join(issues))
    if assignment_id:
        for item in current_task_sources:
            if item["assignment_id"] == assignment_id:
                return item
        raise ValueError(f"assignment_id {assignment_id} is not a legal current task source")
    if len(current_task_sources) != 1:
        raise ValueError("main-thread action requires exactly one current task source when assignment_id is omitted")
    return current_task_sources[0]


def build_live_workflow_log(runtime_dir: str | Path) -> dict[str, Any]:
    runtime_path = Path(runtime_dir).expanduser().resolve()
    assignment_path = runtime_path / "cmux-assignment.json"
    assignment_payload = load_json_if_exists(assignment_path)
    if assignment_payload is None:
        raise FileNotFoundError(f"assignment file missing: {assignment_path}")

    assignments = assignment_payload.get("assignments") or []
    if not isinstance(assignments, list):
        raise ValueError(f"invalid assignments payload: {assignment_path}")
    active_assignments = [
        item
        for item in assignments
        if isinstance(item, dict) and str(item.get("status") or "").strip().upper() in ACTIVE_STATUSES
    ]
    current_task_sources, current_task_source_issues = _resolve_current_task_sources(
        assignment_payload,
        assignment_path,
        active_assignments,
    )
    current_task_source_ids = _current_task_source_ids(current_task_sources)
    current_cycle_ids = {
        str(item.get("cycle_id") or "").strip()
        for item in current_task_sources
        if str(item.get("cycle_id") or "").strip()
    }
    task_source_by_assignment_id = (
        _task_source_by_assignment_id(
            active_assignments,
            current_task_sources,
        )
        if active_assignments
        else {}
    )

    hook_path = runtime_path / "hook-state.json"
    consumer_path = runtime_path / "cmux-consumer-state-latest.json"
    watcher_log_path = runtime_path / "watch_cmux_assignments.log"
    finish_log_path = runtime_path / "cmux-finish.log"
    receipts_path = runtime_path / "cmux-finish-receipts.jsonl"
    main_thread_actions_path = runtime_path / DEFAULT_MAIN_THREAD_ACTIONS_JSONL_NAME

    hook_payload = load_json_if_exists(hook_path)
    consumer_payload = load_json_if_exists(consumer_path)
    all_receipt_payloads = load_jsonl_if_exists(receipts_path)
    all_main_thread_action_events, main_thread_action_issues = load_main_thread_action_events(main_thread_actions_path)
    archive_only_consumer_control_packet_count = 0
    consumer_control_packet_issues: list[str] = []
    if consumer_payload is not None:
        (
            consumer_payload,
            archive_only_consumer_control_packet_count,
            consumer_control_packet_issues,
        ) = _filter_consumer_payload_for_current_sources(
            consumer_payload,
            task_source_by_assignment_id,
        )
    receipt_payloads = [
        payload
        for payload in all_receipt_payloads
        if _receipt_matches_current_task_sources(payload, current_task_source_ids, current_cycle_ids)
    ]
    if current_task_source_ids:
        main_thread_action_events = [
            event
            for event in all_main_thread_action_events
            if _event_matches_current_task_sources(event, current_task_source_ids)
        ]
    elif active_assignments:
        main_thread_action_events = []
    else:
        # Once the worker set is empty, the latest live status must still surface
        # terminal main-thread actions such as direct reject or closure.
        main_thread_action_events = list(all_main_thread_action_events)
    archive_only_receipt_count = len(all_receipt_payloads) - len(receipt_payloads)
    archive_only_main_thread_action_count = len(all_main_thread_action_events) - len(main_thread_action_events)

    warnings: list[str] = []
    warnings.extend(current_task_source_issues)
    if hook_payload is None:
        warnings.append(f"hook state missing: {hook_path}")
    if consumer_payload is None:
        warnings.append(
            f"consumer state missing: {consumer_path}; A6/A7 proof is partial and commander handoff derives from hook-state only"
        )
    if not watcher_log_path.exists():
        warnings.append(f"watcher log missing: {watcher_log_path}")
    if not finish_log_path.exists():
        warnings.append(f"finish log missing: {finish_log_path}")
    if not receipts_path.exists():
        warnings.append(
            f"finish-cycle receipts missing: {receipts_path}; local writeback cannot be proven by receipt chain"
        )
    warnings.extend(main_thread_action_issues)
    warnings.extend(consumer_control_packet_issues)
    if main_thread_actions_path.exists() and not all_main_thread_action_events:
        warnings.append(
            f"main-thread action journal contains no valid main-thread records: {main_thread_actions_path}"
        )
    if archive_only_receipt_count > 0:
        warnings.append(
            f"ignored {archive_only_receipt_count} archive-only finish receipts that do not match current_task_sources"
        )
    if archive_only_main_thread_action_count > 0:
        warnings.append(
            f"ignored {archive_only_main_thread_action_count} archive-only main-thread actions that do not match current_task_sources"
        )
    if archive_only_consumer_control_packet_count > 0:
        warnings.append(
            "consumer-state archived embedded control packets that do not match current_task_sources"
        )
    if active_assignments and not current_task_source_ids:
        warnings.append("active assignments exist but no legal current_task_sources are bound")

    pending_handoffs = derive_pending_handoffs(active_assignments, hook_payload, consumer_payload)
    if pending_handoffs:
        warnings.append("main-thread still has pending A6/A7 handoff actions")

    hook_surfaces = {}
    if isinstance(hook_payload, dict):
        hook_surfaces = hook_payload.get("surfaces") or {}
        if not isinstance(hook_surfaces, dict):
            hook_surfaces = {}

    consumer_assignments = {}
    if isinstance(consumer_payload, dict):
        consumer_assignments = consumer_payload.get("assignments") or {}
        if not isinstance(consumer_assignments, dict):
            consumer_assignments = {}

    events: list[dict[str, Any]] = []
    order = 1
    for assignment in active_assignments:
        logical_target = str(assignment.get("logical_target") or assignment.get("bot_name") or "").strip()
        assignment_id = str(assignment.get("assignment_id") or "").strip()
        events.append(
            build_event(
                order=order,
                at=str(assignment_payload.get("updated_at") or "").strip(),
                actor="main-thread",
                phase="A2",
                kind="active_assignment_snapshot",
                source=str(assignment_path),
                logical_target=logical_target,
                assignment_id=assignment_id,
                task_source_ref=task_source_by_assignment_id.get(assignment_id),
                summary=f"active assignment staged for {logical_target or 'unknown-target'}",
                details={
                    "title": str(assignment.get("title") or "").strip(),
                    "goal": str(assignment.get("goal") or "").strip(),
                    "dispatch_ready": bool(assignment_payload.get("dispatch_ready")),
                },
            )
        )
        order += 1

    watcher_events = parse_watcher_log_events(watcher_log_path)
    for event in watcher_events:
        event["order"] = order
        events.append(event)
        order += 1

    for event in main_thread_action_events:
        event["order"] = order
        events.append(event)
        order += 1

    for assignment in active_assignments:
        logical_target = str(assignment.get("logical_target") or assignment.get("bot_name") or "").strip()
        assignment_id = str(assignment.get("assignment_id") or "").strip()
        surface_ref = str(assignment.get("surface_ref") or "").strip()
        surface_state = hook_surfaces.get(surface_ref)
        if isinstance(surface_state, dict):
            latest_at = (
                str(surface_state.get("last_notification_at") or "").strip()
                or str(surface_state.get("last_stop_at") or "").strip()
                or str(surface_state.get("last_prompt_submit_at") or "").strip()
                or str(surface_state.get("last_session_start_at") or "").strip()
            )
            events.append(
                build_event(
                    order=order,
                    at=latest_at,
                    actor=logical_target or "worker",
                    phase="A6" if any(
                        str(surface_state.get(field) or "").strip()
                        for field in ("last_stop_at", "last_notification_at")
                    ) else "A5",
                    kind="surface_lifecycle_snapshot",
                    source=str(hook_path),
                    logical_target=logical_target,
                    assignment_id=assignment_id,
                    task_source_ref=task_source_by_assignment_id.get(assignment_id),
                    summary=(
                        f"surface={surface_ref} prompt_submit={int(surface_state.get('prompt_submit_count') or 0)} "
                        f"stop={int(surface_state.get('stop_count') or 0)} "
                        f"notification={int(surface_state.get('notification_count') or 0)}"
                    ),
                    details={
                        "surface_ref": surface_ref,
                        "last_event": str(surface_state.get("last_event") or "").strip(),
                        "adhoc_prompt_count": int(surface_state.get("adhoc_prompt_count") or 0),
                    },
                )
            )
            order += 1

        consumer_entry = consumer_assignments.get(logical_target)
        if isinstance(consumer_entry, dict):
            consumer_state = str(consumer_entry.get("state") or "").strip()
            control_packet = consumer_entry.get("control_packet")
            phase = "A5"
            kind = "consumer_state_snapshot"
            summary = f"{logical_target or 'worker'} consumer_state={consumer_state or 'unknown'}"
            if consumer_state in A6_REVIEW_STATES:
                phase = "A6"
            if isinstance(control_packet, dict):
                packet_state = str(control_packet.get("state") or "").strip()
                packet_result = str(control_packet.get("result") or "").strip()
                summary = f"{logical_target or 'worker'} control_packet={packet_state}/{packet_result}"
                if packet_state == "completed" and packet_result == "pass":
                    phase = "A7"
                    kind = "control_packet_completed"
            events.append(
                build_event(
                    order=order,
                    at=str(consumer_entry.get("state_updated_at") or "").strip(),
                    actor=logical_target or "worker",
                    phase=phase,
                    kind=kind,
                    source=str(consumer_path),
                    logical_target=logical_target,
                    assignment_id=assignment_id,
                    task_source_ref=task_source_by_assignment_id.get(assignment_id),
                    summary=summary,
                    details={
                        "state": consumer_state,
                        "state_source": str(consumer_entry.get("state_source") or "").strip(),
                    },
                )
            )
            order += 1

    for receipt in receipt_payloads:
        cycle_id = str(receipt.get("cycle_id") or "").strip()
        cycle_at = ""
        if "|" in cycle_id:
            parts = cycle_id.split("|")
            if len(parts) >= 2:
                cycle_at = parts[1]
        outcomes = receipt.get("outcomes") or []
        if not isinstance(outcomes, list):
            outcomes = []
        for outcome in outcomes:
            if not isinstance(outcome, dict):
                continue
            logical_target = str(outcome.get("logical_target") or "").strip()
            task_id = str(outcome.get("task_id") or "").strip()
            outcome_task_source_ref = None
            try:
                outcome_task_source_ref = maybe_normalize_task_source_ref(
                    outcome.get("task_source_ref"),
                    expected_task_type=TASK_TYPE_CMUX,
                )
            except TaskSourceContractError:
                outcome_task_source_ref = None
            events.append(
                build_event(
                    order=order,
                    at=cycle_at,
                    actor="finish-cycle",
                    phase="A7",
                    kind="finish_cycle_local_writeback",
                    source=str(receipts_path),
                    logical_target=logical_target,
                    assignment_id=str(
                        outcome.get("assignment_id")
                        or (outcome_task_source_ref or {}).get("assignment_id")
                        or ""
                    ).strip(),
                    task_source_ref=outcome_task_source_ref,
                    summary=f"finish-cycle local writeback for {logical_target or task_id or 'unknown-target'}",
                    details={
                        "cycle_id": cycle_id,
                        "status": str(outcome.get("status") or "").strip(),
                        "summary": str(outcome.get("summary") or "").strip(),
                        "artifact_path": str(outcome.get("artifact_path") or "").strip(),
                    },
                )
            )
            order += 1

    if finish_log_path.exists():
        for raw_line in finish_log_path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line:
                continue
            if line.startswith("finish_cycle_ok cycle_id="):
                cycle_id = line.partition("finish_cycle_ok cycle_id=")[2].strip()
                cycle_at = ""
                if "|" in cycle_id:
                    parts = cycle_id.split("|")
                    if len(parts) >= 2:
                        cycle_at = parts[1]
                events.append(
                    build_event(
                        order=order,
                        at=cycle_at,
                        actor="finish-cycle",
                        phase="A7",
                        kind="finish_cycle_log",
                        source=str(finish_log_path),
                        summary=line,
                    )
                )
                order += 1
            elif line.startswith("gitlab_comment_posted") or line.startswith("gitlab_comment_skipped"):
                events.append(
                    build_event(
                        order=order,
                        at="",
                        actor="finish-cycle",
                        phase="A7",
                        kind="finish_cycle_comment_log",
                        source=str(finish_log_path),
                        summary=line,
                    )
                )
                order += 1

    for pending in pending_handoffs:
        logical_target = str(pending.get("logical_target") or "").strip()
        assignment_id = str(pending.get("assignment_id") or "").strip()
        at = (
            str(pending.get("last_notification_at") or "").strip()
            or str(pending.get("last_stop_at") or "").strip()
            or str(pending.get("last_prompt_submit_at") or "").strip()
        )
        phase = str(pending.get("phase") or "").strip() or "A6"
        reason = str(pending.get("reason") or "").strip() or "commander review required"
        events.append(
            build_event(
                order=order,
                at=at,
                actor="main-thread",
                phase=phase,
                kind="main_thread_handoff_pending",
                source=str(hook_path if "surface_" in reason else consumer_path),
                logical_target=logical_target,
                assignment_id=assignment_id,
                task_source_ref=task_source_by_assignment_id.get(assignment_id),
                summary=f"main-thread handoff pending for {logical_target or 'unknown-target'}: {reason}",
                details=pending,
            )
        )
        order += 1

    events.sort(key=event_sort_key)
    for index, event in enumerate(events, start=1):
        event["order"] = index

    closure_evidenced = any(str(event.get("kind") or "").strip() == "main_thread_closure" for event in events)
    acceptance_evidenced = _main_thread_acceptance_evidenced(events)
    direct_reject_details = _collect_direct_reject_details(events)
    a7_writeback = collect_a7_writeback_targets(
        receipt_payloads,
        current_task_sources=current_task_sources,
    )
    final_reviewer_legality = _collect_final_reviewer_legality(events)

    hook_violation_count = 0
    adhoc_surfaces: list[str] = []
    for surface_ref, surface_state in hook_surfaces.items():
        if not isinstance(surface_state, dict):
            continue
        adhoc_prompt_count = int(surface_state.get("adhoc_prompt_count") or 0)
        if adhoc_prompt_count > 0:
            hook_violation_count += adhoc_prompt_count
            adhoc_surfaces.append(str(surface_ref))
    if hook_violation_count:
        warnings.append(
            f"hook provenance violations detected across surfaces {sorted(adhoc_surfaces)} (adhoc_prompt_count={hook_violation_count})"
        )
    if direct_reject_details:
        warnings.append(
            "main-thread direct_reject recorded; same-attempt acceptance/closure cannot coexist with reject and the run is terminal"
        )
    if receipt_payloads and not a7_writeback["scope_confirmed"]:
        warnings.append(a7_writeback["scope_issue"])
    elif receipt_payloads and not a7_writeback["complete"]:
        warnings.append(
            "A7 local writeback is partial; missing mandatory targets: "
            + ", ".join(str(item) for item in a7_writeback["missing_targets"])
        )

    discovered_control_packet_artifacts = discover_control_packet_artifacts(runtime_path)
    control_packet_artifacts = _filter_control_packet_artifacts_for_current_sources(
        discovered_control_packet_artifacts,
        current_task_source_ids,
        task_source_by_assignment_id,
    )
    archive_only_control_packet_count = len(discovered_control_packet_artifacts) - len(
        control_packet_artifacts
    )
    if archive_only_control_packet_count > 0:
        warnings.append(
            f"ignored {archive_only_control_packet_count} archive-only control packet artifacts that do not match current_task_sources"
        )
    verification_paths: list[Path] = [runtime_path / DEFAULT_LIVE_JSON_NAME, *control_packet_artifacts]
    for candidate in (consumer_path, receipts_path, main_thread_actions_path):
        if candidate.exists():
            verification_paths.append(candidate)

    verification_contract = describe_verification_packet_contract()
    verification_read_order = render_verification_packet_sources(verification_paths)
    present_slots = [item["slot"] for item in verification_read_order]
    missing_slots = [slot for slot in REQUIRED_VERIFICATION_PACKET_SLOTS if slot not in present_slots]
    has_standalone_control_packet = any(
        str(item.get("slot") or "").strip() == "control_packet"
        and str(item.get("via_rule") or "").strip() == "control_packet_artifact"
        for item in verification_read_order
    )
    if consumer_payload is not None and not has_standalone_control_packet:
        if consumer_state_covers_control_packet(consumer_payload):
            warnings.append(
                "consumer-state embeds control_packet data, but the control_packet slot remains unsatisfied until a standalone legal packet artifact exists"
            )
        else:
            warnings.append(
                f"consumer-state is present but {CONSUMER_STATE_CONTROL_PACKET_EXTRACTION} is absent; control_packet slot is unsatisfied unless a standalone packet exists"
            )
    if closure_evidenced and not final_reviewer_legality["ok"]:
        warnings.append(
            "final reviewer legality is incomplete; native-pass is unavailable without one frozen packet and 3 transcript-backed fork_context=false reviewers"
        )

    log_payload: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "cmux_workflow_log",
        "mode": "live_runtime",
        "generated_at": utc_now(),
        "runtime_dir": str(runtime_path),
        "governance": {
            "p8_governance_gate": True,
            "finish_cycle_scope": "local_writeback_only",
            "closure_authority": "main-thread",
            "main_thread_required_for": [
                "dispatch",
                "A6_review",
                "A8_acceptance",
                "A9_closure",
                "A9_direct_reject",
            ],
        },
        "sources": {
            "assignment_file": str(assignment_path),
            "hook_state_file": str(hook_path),
            "consumer_state_file": str(consumer_path),
            "control_packet_artifacts": [str(path) for path in control_packet_artifacts],
            "watcher_log": str(watcher_log_path),
            "finish_log": str(finish_log_path),
            "finish_receipts_file": str(receipts_path),
            "main_thread_actions_file": str(main_thread_actions_path),
        },
        "verification_packet": {
            "proof_basis": str(verification_contract.get("proof_basis") or "").strip(),
            "required_slots": list(REQUIRED_VERIFICATION_PACKET_SLOTS),
            "slot_order": list(verification_contract.get("slot_order") or REQUIRED_VERIFICATION_PACKET_SLOTS),
            "read_order": verification_read_order,
            "missing_slots": missing_slots,
        },
        "summary": {
            "assignment_ready": bool(assignment_payload.get("ready")),
            "dispatch_ready": bool(assignment_payload.get("dispatch_ready")),
            "runtime_status": str(assignment_payload.get("runtime_status") or "").strip(),
            "assignment_updated_at": str(assignment_payload.get("updated_at") or "").strip(),
            "active_assignment_count": len(active_assignments),
            "current_task_source_count": len(current_task_sources),
            "current_task_source_ids": sorted(current_task_source_ids),
            "consumer_state_present": consumer_payload is not None,
            "finish_receipt_count": len(receipt_payloads),
            "archive_only_receipt_count": archive_only_receipt_count,
            "a7_required_writeback_targets": a7_writeback["required_targets"],
            "a7_present_writeback_targets": a7_writeback["present_targets"],
            "a7_missing_writeback_targets": a7_writeback["missing_targets"],
            "a7_evaluated_cycle_id": a7_writeback["evaluated_cycle_id"],
            "a7_writeback_complete": a7_writeback["complete"],
            "a7_scope_confirmed": a7_writeback["scope_confirmed"],
            "a7_scope_issue": a7_writeback["scope_issue"],
            "main_thread_action_count": len(main_thread_action_events),
            "archive_only_main_thread_action_count": archive_only_main_thread_action_count,
            "archive_only_consumer_control_packet_count": archive_only_consumer_control_packet_count,
            "main_thread_action_validation_issue_count": len(main_thread_action_issues),
            "main_thread_acceptance_evidenced": acceptance_evidenced,
            "hook_provenance_violation_count": hook_violation_count,
            "main_thread_closure_evidenced": closure_evidenced,
            "verification_missing_slots": missing_slots,
            "verification_missing_slot_count": len(missing_slots),
            "archive_only_control_packet_count": archive_only_control_packet_count,
            "direct_reject_count": len(direct_reject_details),
            "direct_reject_details": direct_reject_details,
            "final_reviewer_legality": final_reviewer_legality,
            "final_reviewer_legality_ok": final_reviewer_legality["ok"],
        },
        "validation": {
            "main_thread_action_issues": main_thread_action_issues,
            "current_task_source_issues": current_task_source_issues,
        },
        "current_task_sources": current_task_sources,
        "active_assignments": active_assignments,
        "pending_handoffs": pending_handoffs,
        "warnings": warnings,
        "events": events,
    }
    return log_payload


def build_sample_three_round_five_bot_workflow() -> dict[str, Any]:
    round_definitions = [
        (
            "R1",
            "Freeze replica scope, truth basis, and acceptance baseline",
            {
                "pm-bot": ("P8-SAMPLE-R1-PM", "Freeze round scope and must-cover pages"),
                "dev-bot": ("P8-SAMPLE-R1-DEV", "Map route inventory and DOM anchor list"),
                "qa-bot": ("P8-SAMPLE-R1-QA", "Build round-one acceptance matrix"),
                "doc-bot": ("P8-SAMPLE-R1-DOC", "Prepare evidence packet template"),
                "rea-bot": ("P8-SAMPLE-R1-REA", "Audit truth basis and source provenance"),
            },
        ),
        (
            "R2",
            "Execute capture and parity work across the five worker lanes",
            {
                "pm-bot": ("P8-SAMPLE-R2-PM", "Publish ordered execution packet for round two"),
                "dev-bot": ("P8-SAMPLE-R2-DEV", "Capture target page structures and route parity"),
                "qa-bot": ("P8-SAMPLE-R2-QA", "Validate parity matrix and regression checklist"),
                "doc-bot": ("P8-SAMPLE-R2-DOC", "Sync round-two evidence and delivery notes"),
                "rea-bot": ("P8-SAMPLE-R2-REA", "Review parity drift and residual governance risk"),
            },
        ),
        (
            "R3",
            "Run final delivery, evidence sync, and commander-controlled closure",
            {
                "pm-bot": ("P8-SAMPLE-R3-PM", "Issue final release packet and closure checklist"),
                "dev-bot": ("P8-SAMPLE-R3-DEV", "Finalize delivery artifacts and proof paths"),
                "qa-bot": ("P8-SAMPLE-R3-QA", "Execute final acceptance pass"),
                "doc-bot": ("P8-SAMPLE-R3-DOC", "Publish final evidence packet"),
                "rea-bot": ("P8-SAMPLE-R3-REA", "Perform final governance audit"),
            },
        ),
    ]

    rounds: list[dict[str, Any]] = []
    events: list[dict[str, Any]] = []
    order = 1
    current = datetime(2026, 4, 19, 9, 0, tzinfo=LOCAL_TZ)
    for round_id, objective, assignments in round_definitions:
        round_assignments: list[dict[str, Any]] = []
        events.append(
            build_event(
                order=order,
                at=current.strftime("%Y-%m-%dT%H:%M:%S%z"),
                actor="main-thread",
                phase="A3",
                kind="main_thread_round_dispatch",
                round_id=round_id,
                source="sample",
                summary=f"main-thread opened {round_id} and dispatched the five worker lanes",
            )
        )
        order += 1
        current += timedelta(minutes=2)
        for logical_target in BOT_ORDER:
            assignment_id, goal = assignments[logical_target]
            round_assignments.append(
                {
                    "logical_target": logical_target,
                    "assignment_id": assignment_id,
                    "goal": goal,
                    "dispatch_by": "main-thread",
                    "execute_by": logical_target,
                    "local_writeback_by": "finish-cycle",
                    "closure_by": "main-thread",
                }
            )
            events.append(
                build_event(
                    order=order,
                    at=current.strftime("%Y-%m-%dT%H:%M:%S%z"),
                    actor="main-thread",
                    phase="A3",
                    kind="main_thread_dispatch",
                    round_id=round_id,
                    source="sample",
                    logical_target=logical_target,
                    assignment_id=assignment_id,
                    summary=f"main-thread dispatched {assignment_id} to {logical_target}",
                )
            )
            order += 1
            current += timedelta(minutes=1)
            events.append(
                build_event(
                    order=order,
                    at=current.strftime("%Y-%m-%dT%H:%M:%S%z"),
                    actor=logical_target,
                    phase="A5",
                    kind="worker_execution",
                    round_id=round_id,
                    source="sample",
                    logical_target=logical_target,
                    assignment_id=assignment_id,
                    summary=f"{logical_target} executed {assignment_id}",
                )
            )
            order += 1
            current += timedelta(minutes=1)
            events.append(
                build_event(
                    order=order,
                    at=current.strftime("%Y-%m-%dT%H:%M:%S%z"),
                    actor=logical_target,
                    phase="A6",
                    kind="worker_control_packet_completed",
                    round_id=round_id,
                    source="sample",
                    logical_target=logical_target,
                    assignment_id=assignment_id,
                    summary=f"{logical_target} emitted completed/pass control packet for {assignment_id}",
                )
            )
            order += 1
            current += timedelta(minutes=1)
        rounds.append(
            {
                "round_id": round_id,
                "objective": objective,
                "assignments": round_assignments,
                "dispatch_by": "main-thread",
                "local_writeback_by": "finish-cycle",
                "acceptance_by": "main-thread",
                "closure_by": "main-thread",
            }
        )
        events.append(
            build_event(
                order=order,
                at=current.strftime("%Y-%m-%dT%H:%M:%S%z"),
                actor="finish-cycle",
                phase="A7",
                kind="finish_cycle_local_writeback",
                round_id=round_id,
                source="sample",
                summary=f"finish-cycle wrote local task-list and ce-sync-plan updates for {round_id}",
            )
        )
        order += 1
        current += timedelta(minutes=2)
        events.append(
            build_event(
                order=order,
                at=current.strftime("%Y-%m-%dT%H:%M:%S%z"),
                actor="main-thread",
                phase="A8",
                kind="main_thread_acceptance",
                round_id=round_id,
                source="sample",
                summary=f"main-thread reviewed {round_id} outcomes and approved the next step",
            )
        )
        order += 1
        current += timedelta(minutes=3)

    events.append(
        build_event(
            order=order,
            at=current.strftime("%Y-%m-%dT%H:%M:%S%z"),
            actor="main-thread",
            phase="A9",
            kind="main_thread_closure",
            source="sample",
            summary="main-thread closed the three-round workflow; closure authority never moved to finish-cycle",
        )
    )

    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "cmux_workflow_log",
        "mode": "sample_three_round_five_bot",
        "generated_at": utc_now(),
        "governance": {
            "p8_governance_gate": True,
            "finish_cycle_scope": "local_writeback_only",
            "closure_authority": "main-thread",
            "main_thread_required_for": [
                "dispatch",
                "A6_review",
                "A8_acceptance",
                "A9_closure",
                "A9_direct_reject",
            ],
        },
        "summary": {
            "round_count": 3,
            "bot_count": 5,
            "closure_authority": "main-thread",
            "sample_contract": "three_round_five_bot",
        },
        "rounds": rounds,
        "warnings": [],
        "events": events,
    }


def materialize_live_workflow_log(runtime_dir: str | Path, output_path: str | Path | None = None) -> Path:
    runtime_path = Path(runtime_dir).expanduser().resolve()
    payload = build_live_workflow_log(runtime_path)
    archive_context = resolve_archive_context(runtime_path, payload)
    payload["archive"] = archive_context
    target = Path(output_path).expanduser().resolve() if output_path is not None else runtime_path / DEFAULT_LIVE_JSON_NAME
    log_path = write_json(target, payload)
    summary_artifact = build_live_workflow_summary(payload, log_path)
    write_summary_artifact(runtime_path / DEFAULT_LIVE_SUMMARY_NAME, summary_artifact)
    write_json(Path(archive_context["workflow_log_path"]), payload)
    write_summary_artifact(Path(archive_context["workflow_summary_path"]), summary_artifact)
    return log_path


def append_main_thread_action(
    runtime_dir: str | Path,
    *,
    phase: str,
    kind: str,
    summary: str,
    logical_target: str = "",
    assignment_id: str = "",
    round_id: str = "",
    task_source_ref: dict[str, Any] | None = None,
    details: dict[str, Any] | None = None,
    at: str | None = None,
    output_path: str | Path | None = None,
) -> Path:
    runtime_path = Path(runtime_dir).expanduser().resolve()
    normalized_phase, normalized_kind, normalized_details = _normalize_main_thread_action_inputs(
        phase=phase,
        kind=kind,
        details=details,
    )
    normalized_task_source_ref = _resolve_main_thread_action_task_source_ref(
        runtime_path,
        task_source_ref=task_source_ref,
        assignment_id=str(assignment_id).strip(),
    )
    existing_events, _ = load_main_thread_action_events(runtime_path / DEFAULT_MAIN_THREAD_ACTIONS_JSONL_NAME)
    existing_kinds = {str(event.get("kind") or "").strip() for event in existing_events}
    if normalized_kind in {MAIN_THREAD_ACCEPTANCE_KIND, MAIN_THREAD_CLOSURE_KIND} and (
        MAIN_THREAD_DIRECT_REJECT_KIND in existing_kinds
    ):
        raise ValueError("main_thread_direct_reject is already recorded; acceptance/closure cannot coexist with reject")
    if normalized_kind == MAIN_THREAD_DIRECT_REJECT_KIND:
        if MAIN_THREAD_DIRECT_REJECT_KIND in existing_kinds:
            raise ValueError("main_thread_direct_reject is already recorded for the current run")
        if existing_kinds & {MAIN_THREAD_ACCEPTANCE_KIND, MAIN_THREAD_CLOSURE_KIND}:
            raise ValueError("main_thread_direct_reject cannot coexist with same-attempt acceptance/closure")
    if normalized_kind == MAIN_THREAD_CLOSURE_KIND and _details_claim_native_pass(normalized_details):
        legality = _collect_final_reviewer_legality(
            [
                build_event(
                    order=1,
                    at=str(at or utc_now()).strip(),
                    actor="main-thread",
                    phase=normalized_phase,
                    kind=normalized_kind,
                    source=str(runtime_path / DEFAULT_MAIN_THREAD_ACTIONS_JSONL_NAME),
                    logical_target=str(logical_target).strip(),
                    assignment_id=normalized_task_source_ref["assignment_id"],
                    round_id=str(round_id).strip(),
                    task_source_ref=normalized_task_source_ref,
                    summary=str(summary).strip(),
                    details=normalized_details,
                )
            ]
        )
        if not legality["ok"]:
            reasons = ", ".join(str(item) for item in legality["missing_reasons"]) or "final reviewer legality missing"
            raise ValueError(f"native-pass claim requires one frozen packet and 3 legal final reviewers; missing={reasons}")
    payload: dict[str, Any] = {
        "schema_version": MAIN_THREAD_ACTION_SCHEMA_VERSION,
        "generated_at": utc_now(),
        "at": str(at or utc_now()).strip(),
        "actor": "main-thread",
        "phase": normalized_phase,
        "kind": normalized_kind,
        "summary": str(summary).strip(),
        "task_source_ref": normalized_task_source_ref,
    }
    if logical_target:
        payload["logical_target"] = str(logical_target).strip()
    payload["assignment_id"] = normalized_task_source_ref["assignment_id"]
    if round_id:
        payload["round_id"] = str(round_id).strip()
    if normalized_details:
        payload["details"] = normalized_details
    append_jsonl(runtime_path / DEFAULT_MAIN_THREAD_ACTIONS_JSONL_NAME, payload)
    return materialize_live_workflow_log(runtime_path, output_path=output_path)


def resolve_output_path(runtime_dir: Path, mode: str, explicit_path: str | None) -> Path:
    if explicit_path:
        return Path(explicit_path).expanduser().resolve()
    if mode == "live":
        return runtime_dir / DEFAULT_LIVE_JSON_NAME
    return runtime_dir / DEFAULT_SAMPLE_JSON_NAME


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Materialize unified cmux workflow logs.")
    parser.add_argument(
        "--mode",
        choices=("live", "sample-three-round-five-bot"),
        default="live",
        help="Build a live runtime workflow log or a deterministic 3-round 5-bot sample log.",
    )
    parser.add_argument(
        "--runtime-dir",
        default="/Users/busiji/workbot/workspace/artifacts/cmux-runtime",
        help="cmux runtime artifact directory",
    )
    parser.add_argument(
        "--output-json",
        help="Optional explicit output path for the workflow log JSON artifact.",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    runtime_dir = Path(args.runtime_dir).expanduser().resolve()
    if args.mode == "live":
        payload = build_live_workflow_log(runtime_dir)
    else:
        payload = build_sample_three_round_five_bot_workflow()
        payload["runtime_dir"] = str(runtime_dir)
    output_path = resolve_output_path(runtime_dir, args.mode, args.output_json)
    write_json(output_path, payload)
    print(json.dumps({"output_json": str(output_path), "mode": args.mode}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
