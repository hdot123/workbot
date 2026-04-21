#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
from typing import Any

TASK_SOURCE_SCHEMA_VERSION = "wb-current-task-source-v1"

TASK_TYPE_CMUX = "cmux"
TASK_TYPE_MAIN_THREAD = "main_thread"
TASK_TYPES = {TASK_TYPE_CMUX, TASK_TYPE_MAIN_THREAD}

ARCHIVE_ONLY_STATUS = "archive_only"


class TaskSourceContractError(ValueError):
    """Raised when a task source contract is missing or invalid."""


def _normalize_text(value: Any, field_name: str) -> str:
    if not isinstance(value, str):
        raise TaskSourceContractError(f"{field_name} must be a string")
    normalized = value.strip()
    if not normalized:
        raise TaskSourceContractError(f"{field_name} must not be empty")
    return normalized


def _normalize_path(value: Any, field_name: str) -> str:
    normalized = _normalize_text(value, field_name)
    if not normalized.startswith("/"):
        raise TaskSourceContractError(f"{field_name} must be an absolute path")
    return str(Path(normalized).expanduser())


def _normalize_status(value: Any) -> str:
    normalized = _normalize_text(value, "status").lower().replace(" ", "_")
    return normalized


def _main_thread_request_id_value(payload: dict[str, Any]) -> Any:
    return (
        payload.get("request_id")
        or payload.get("task_request_id")
        or payload.get("task_card_id")
    )


def task_source_id_for_cmux(assignment_id: str) -> str:
    assignment = _normalize_text(assignment_id, "assignment_id")
    return f"{TASK_TYPE_CMUX}:{assignment}"


def task_source_id_for_main_thread(request_id: str) -> str:
    request = _normalize_text(request_id, "request_id")
    return f"{TASK_TYPE_MAIN_THREAD}:{request}"


def build_cmux_task_source_ref(
    *,
    assignment_id: str,
    cycle_id: str,
    deliverable_path: str,
    evidence_path: str,
    status: str,
    acceptance_owner: str = "main-thread",
    task_source_id: str | None = None,
) -> dict[str, str]:
    return normalize_task_source_ref(
        {
            "schema_version": TASK_SOURCE_SCHEMA_VERSION,
            "task_type": TASK_TYPE_CMUX,
            "task_source_id": task_source_id or task_source_id_for_cmux(assignment_id),
            "deliverable_path": deliverable_path,
            "evidence_path": evidence_path,
            "status": status,
            "assignment_id": assignment_id,
            "cycle_id": cycle_id,
            "acceptance_owner": acceptance_owner,
        },
        expected_task_type=TASK_TYPE_CMUX,
    )


def build_main_thread_task_source_ref(
    *,
    request_id: str,
    deliverable_path: str,
    evidence_path: str,
    status: str,
    acceptance_owner: str,
    current_output_path: str | None = None,
    current_evidence_path: str | None = None,
    task_source_id: str | None = None,
) -> dict[str, str]:
    return normalize_task_source_ref(
        {
            "schema_version": TASK_SOURCE_SCHEMA_VERSION,
            "task_type": TASK_TYPE_MAIN_THREAD,
            "task_source_id": task_source_id or task_source_id_for_main_thread(request_id),
            "deliverable_path": deliverable_path,
            "evidence_path": evidence_path,
            "status": status,
            "request_id": request_id,
            "acceptance_owner": acceptance_owner,
            "current_output_path": current_output_path or deliverable_path,
            "current_evidence_path": current_evidence_path or evidence_path,
        },
        expected_task_type=TASK_TYPE_MAIN_THREAD,
    )


def maybe_normalize_task_source_ref(
    payload: Any,
    *,
    expected_task_type: str | None = None,
    allow_archive_only: bool = False,
) -> dict[str, str] | None:
    if payload is None:
        return None
    if not isinstance(payload, dict):
        raise TaskSourceContractError("task_source_ref must be a JSON object when present")
    return normalize_task_source_ref(
        payload,
        expected_task_type=expected_task_type,
        allow_archive_only=allow_archive_only,
    )


def normalize_task_source_ref(
    payload: dict[str, Any],
    *,
    expected_task_type: str | None = None,
    allow_archive_only: bool = False,
) -> dict[str, str]:
    if not isinstance(payload, dict):
        raise TaskSourceContractError("task_source_ref must be a JSON object")

    task_type = _normalize_text(payload.get("task_type"), "task_type").lower()
    if task_type not in TASK_TYPES:
        raise TaskSourceContractError(f"unsupported task_type: {task_type}")
    if expected_task_type is not None and task_type != expected_task_type:
        raise TaskSourceContractError(
            f"task_type mismatch: expected {expected_task_type} actual {task_type}"
        )

    deliverable_path = _normalize_path(payload.get("deliverable_path"), "deliverable_path")
    evidence_path = _normalize_path(payload.get("evidence_path"), "evidence_path")
    status = _normalize_status(payload.get("status"))

    normalized: dict[str, str] = {
        "schema_version": TASK_SOURCE_SCHEMA_VERSION,
        "task_type": task_type,
        "task_source_id": _normalize_text(
            payload.get("task_source_id")
            or (
                task_source_id_for_cmux(str(payload.get("assignment_id") or ""))
                if task_type == TASK_TYPE_CMUX
                else task_source_id_for_main_thread(str(_main_thread_request_id_value(payload) or ""))
            ),
            "task_source_id",
        ),
        "deliverable_path": deliverable_path,
        "evidence_path": evidence_path,
        "status": status,
    }

    if status == ARCHIVE_ONLY_STATUS and not allow_archive_only:
        raise TaskSourceContractError("archive_only task sources are evidence-only and not legal current sources")

    acceptance_owner = _normalize_text(
        payload.get("acceptance_owner") or "main-thread",
        "acceptance_owner",
    )
    if acceptance_owner != "main-thread":
        raise TaskSourceContractError("acceptance_owner must remain main-thread")

    if task_type == TASK_TYPE_CMUX:
        assignment_id = _normalize_text(payload.get("assignment_id"), "assignment_id")
        cycle_id = _normalize_text(payload.get("cycle_id"), "cycle_id")
        normalized.update(
            {
                "assignment_id": assignment_id,
                "cycle_id": cycle_id,
                "acceptance_owner": acceptance_owner,
            }
        )
        if normalized["task_source_id"] != task_source_id_for_cmux(assignment_id):
            raise TaskSourceContractError(
                "cmux task_source_id must be derived from assignment_id"
            )
        return normalized

    request_id = _normalize_text(_main_thread_request_id_value(payload), "request_id")
    current_output_path = _normalize_path(
        payload.get("current_output_path") or deliverable_path,
        "current_output_path",
    )
    current_evidence_path = _normalize_path(
        payload.get("current_evidence_path") or evidence_path,
        "current_evidence_path",
    )
    normalized.update(
        {
            "request_id": request_id,
            "acceptance_owner": acceptance_owner,
            "current_output_path": current_output_path,
            "current_evidence_path": current_evidence_path,
        }
    )
    if normalized["task_source_id"] != task_source_id_for_main_thread(request_id):
        raise TaskSourceContractError(
            "main_thread task_source_id must be derived from request_id"
        )
    return normalized


def task_source_id_from_ref(payload: Any, *, expected_task_type: str | None = None) -> str:
    normalized = maybe_normalize_task_source_ref(payload, expected_task_type=expected_task_type)
    if normalized is None:
        return ""
    return normalized["task_source_id"]
