#!/usr/bin/env python3
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any


SUMMARY_SCHEMA_VERSION = "wb-cmux-summary-v1"
ALLOWED_STATUSES = {"passed", "failed", "blocked", "running"}
MAX_SUMMARY_LINES = 3
MAX_SUMMARY_LINE_LENGTH = 160


class SummaryArtifactError(ValueError):
    """Raised when a commander summary artifact is invalid."""


def _normalize_required_text(value: Any, field_name: str) -> str:
    if not isinstance(value, str):
        raise SummaryArtifactError(f"{field_name} must be a string")
    normalized = value.strip()
    if not normalized:
        raise SummaryArtifactError(f"{field_name} must not be empty")
    return normalized


def _normalize_summary_lines(lines: list[str] | tuple[str, ...]) -> list[str]:
    normalized: list[str] = []
    for index, line in enumerate(lines, start=1):
        text = _normalize_required_text(line, f"summary_lines[{index}]")
        if len(text) > MAX_SUMMARY_LINE_LENGTH:
            raise SummaryArtifactError(
                f"summary_lines[{index}] exceeds {MAX_SUMMARY_LINE_LENGTH} characters"
            )
        normalized.append(text)
    if not normalized:
        raise SummaryArtifactError("summary_lines must contain at least one short line")
    if len(normalized) > MAX_SUMMARY_LINES:
        raise SummaryArtifactError(
            f"summary_lines must contain at most {MAX_SUMMARY_LINES} lines"
        )
    return normalized


def _normalize_sidecar_path(value: Any, field_name: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise SummaryArtifactError(f"{field_name} must be a string or null")
    normalized = value.strip()
    if not normalized:
        return None
    if not normalized.startswith("/"):
        raise SummaryArtifactError(f"{field_name} must be an absolute path when present")
    return normalized


def _normalize_sidecar_paths(paths: list[str] | tuple[str, ...] | None) -> list[str]:
    if paths is None:
        return []
    normalized: list[str] = []
    for index, path in enumerate(paths, start=1):
        rendered = _normalize_sidecar_path(path, f"sidecar_paths[{index}]")
        if rendered:
            normalized.append(rendered)
    return normalized


def build_summary_artifact(
    *,
    title: str,
    status: str,
    summary_lines: list[str] | tuple[str, ...],
    source: str,
    primary_sidecar_path: str | None = None,
    sidecar_paths: list[str] | tuple[str, ...] | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    normalized_status = _normalize_required_text(status, "status").lower()
    if normalized_status not in ALLOWED_STATUSES:
        raise SummaryArtifactError(f"unsupported status: {status}")

    normalized_title = _normalize_required_text(title, "title")
    normalized_source = _normalize_required_text(source, "source")
    normalized_lines = _normalize_summary_lines(summary_lines)
    normalized_primary_sidecar = _normalize_sidecar_path(
        primary_sidecar_path, "primary_sidecar_path"
    )
    normalized_sidecars = _normalize_sidecar_paths(sidecar_paths)

    if normalized_primary_sidecar and normalized_primary_sidecar not in normalized_sidecars:
        normalized_sidecars = [normalized_primary_sidecar, *normalized_sidecars]

    artifact = {
        "schema_version": SUMMARY_SCHEMA_VERSION,
        "artifact_type": "commander_summary",
        "source": normalized_source,
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "title": normalized_title,
        "status": normalized_status,
        "summary_lines": normalized_lines,
        "primary_sidecar_path": normalized_primary_sidecar,
        "sidecar_paths": normalized_sidecars,
    }
    if extra:
        artifact.update(extra)
    return artifact


def write_summary_artifact(path: str | Path, artifact: dict[str, Any]) -> Path:
    output_path = Path(path).expanduser().resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(artifact, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return output_path
