#!/usr/bin/env python3
from __future__ import annotations

import datetime as dt
import hashlib
import re
from typing import Any

EVENT_ID_PATTERN = re.compile(r"^[0-9a-f]{16}$")
SIGNATURE_PATTERN = re.compile(r"^[0-9a-f]{12}$")
REQUIRED_NON_EMPTY_FIELDS = (
    "identity_id",
    "event_id",
    "event_type",
    "detected_at",
    "pane_id",
    "pane_title",
    "prompt",
    "prompt_headline",
    "recent_output",
    "signature",
    "source",
)


def event_id_for(event: dict[str, Any]) -> str:
    key = "|".join(
        [
            str(event.get("event", event.get("event_type", ""))),
            str(event.get("session", "")),
            str(event.get("window", "")),
            str(event.get("pane_id", "")),
            str(event.get("signature", "")),
            str(event.get("detected_at", "")),
        ]
    )
    return hashlib.sha1(key.encode("utf-8")).hexdigest()[:16]


def build_db_record(event: dict[str, Any]) -> dict[str, Any]:
    option_lines = event.get("option_lines") or []
    event_id = event.get("event_id") or event_id_for(event)
    return {
        "schema_version": "tmux_notification_record_v1",
        "identity_id": event_id,
        "event_id": event_id,
        "event_type": event.get("event", event.get("event_type")),
        "detected_at": event.get("detected_at"),
        "session": event.get("session"),
        "window": event.get("window"),
        "pane_id": event.get("pane_id"),
        "pane_title": event.get("pane_title"),
        "cwd": event.get("cwd"),
        "current_command": event.get("current_command"),
        "prompt": event.get("prompt"),
        "prompt_headline": event.get("prompt_headline"),
        "option_lines": option_lines,
        "option_count": len(option_lines),
        "recent_output": event.get("recent_output"),
        "signature": event.get("signature"),
        "classification_status": event.get("classification_status", "unclassified"),
        "classification_labels": event.get("classification_labels", []),
        "source": event.get("source", "tmux-goto"),
    }


def validate_db_record(record: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []

    for field in REQUIRED_NON_EMPTY_FIELDS:
        value = record.get(field)
        if value is None or (isinstance(value, str) and not value.strip()):
            errors.append(f"missing_or_empty:{field}")

    event_id = str(record.get("event_id", ""))
    if event_id and not EVENT_ID_PATTERN.match(event_id):
        errors.append("invalid:event_id_format")

    identity_id = str(record.get("identity_id", ""))
    if identity_id and not EVENT_ID_PATTERN.match(identity_id):
        errors.append("invalid:identity_id_format")
    if identity_id and event_id and identity_id != event_id:
        errors.append("invalid:identity_id_mismatch")

    signature = str(record.get("signature", ""))
    if signature and not SIGNATURE_PATTERN.match(signature):
        errors.append("invalid:signature_format")

    option_lines = record.get("option_lines")
    if not isinstance(option_lines, list):
        errors.append("invalid:option_lines_type")
    else:
        if not all(isinstance(item, str) and item.strip() for item in option_lines):
            errors.append("invalid:option_lines_items")
        if record.get("option_count") != len(option_lines):
            errors.append("invalid:option_count_mismatch")

    labels = record.get("classification_labels")
    if not isinstance(labels, list):
        errors.append("invalid:classification_labels_type")

    if record.get("classification_status") not in {"unclassified", "classified"}:
        errors.append("invalid:classification_status")

    prompt = str(record.get("prompt", ""))
    prompt_headline = str(record.get("prompt_headline", ""))
    if prompt_headline and prompt_headline not in prompt:
        warnings.append("prompt_headline_not_in_prompt")

    if len(prompt) < 10:
        warnings.append("prompt_too_short")

    return {
        "schema": "tmux_notification_record_v1",
        "validated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "valid": not errors,
        "errors": errors,
        "warnings": warnings,
    }
