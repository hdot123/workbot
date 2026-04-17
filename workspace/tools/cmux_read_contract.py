#!/usr/bin/env python3
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class ReadRule:
    name: str
    priority: int
    normal_path_allowed: bool
    escalation_required: bool
    reason: str


@dataclass(frozen=True)
class ClassifiedArtifact:
    path: str
    rule: ReadRule


SUMMARY_RULE = ReadRule(
    name="commander_summary",
    priority=100,
    normal_path_allowed=True,
    escalation_required=False,
    reason="short commander-facing summary artifact",
)
CONTROL_PACKET_RULE = ReadRule(
    name="control_packet_artifact",
    priority=90,
    normal_path_allowed=True,
    escalation_required=False,
    reason="machine-readable control packet artifact",
)
DETAIL_SIDECAR_RULE = ReadRule(
    name="detail_sidecar",
    priority=50,
    normal_path_allowed=False,
    escalation_required=True,
    reason="detail JSON sidecar for explicit follow-up reads only",
)
FORENSIC_RULE = ReadRule(
    name="forensic_only",
    priority=0,
    normal_path_allowed=False,
    escalation_required=True,
    reason="log or transcript artifact; not part of the normal commander path",
)
UNKNOWN_RULE = ReadRule(
    name="unknown_sidecar",
    priority=10,
    normal_path_allowed=False,
    escalation_required=True,
    reason="unclassified runtime artifact; treat as explicit sidecar only",
)


def classify_runtime_artifact(path: str | Path) -> ClassifiedArtifact:
    rendered = str(path)
    lowered = rendered.lower()
    name = Path(rendered).name.lower()

    if "summary" in name and name.endswith(".json"):
        return ClassifiedArtifact(path=rendered, rule=SUMMARY_RULE)
    if "control-packet" in name and name.endswith(".json"):
        return ClassifiedArtifact(path=rendered, rule=CONTROL_PACKET_RULE)
    if name.endswith(".log") or "transcript" in name or "screen" in name or "tail" in name:
        return ClassifiedArtifact(path=rendered, rule=FORENSIC_RULE)
    if name.endswith(".json") and ("latest" in name or "report" in name or "detail" in name):
        return ClassifiedArtifact(path=rendered, rule=DETAIL_SIDECAR_RULE)
    return ClassifiedArtifact(path=rendered, rule=UNKNOWN_RULE)


def choose_commander_default_sources(paths: Iterable[str | Path]) -> list[ClassifiedArtifact]:
    ranked = [classify_runtime_artifact(path) for path in paths]
    allowed = [item for item in ranked if item.rule.normal_path_allowed]
    return sorted(allowed, key=lambda item: item.rule.priority, reverse=True)


def explain_forensic_requirement(path: str | Path) -> str:
    classified = classify_runtime_artifact(path)
    if classified.rule.normal_path_allowed:
        return f"{classified.path} is normal-path readable as {classified.rule.name}."
    return (
        f"{classified.path} is {classified.rule.name}; escalation is required because "
        f"{classified.rule.reason}."
    )
