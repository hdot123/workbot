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
CONTROL_STATE_RULE = ReadRule(
    name="control_state",
    priority=80,
    normal_path_allowed=True,
    escalation_required=False,
    reason="runtime control-state artifact that can be read when no summary exists",
)
STARTUP_SMOKE_RULE = ReadRule(
    name="startup_smoke",
    priority=85,
    normal_path_allowed=True,
    escalation_required=False,
    reason="startup smoke result artifact used as formal bootstrap acceptance signal",
)
SIDE_STATE_RULE = ReadRule(
    name="side_state_shadow",
    priority=20,
    normal_path_allowed=False,
    escalation_required=True,
    reason="side-state artifact that must not outrank summary or control-state truth",
)
OVERVIEW_RULE = ReadRule(
    name="overview_sidecar",
    priority=15,
    normal_path_allowed=False,
    escalation_required=True,
    reason="overview artifact can drift from runtime truth; use only by explicit escalation",
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
    if name == "cmux-assignment.json" or name == "current-runtime.json" or name.startswith("runtime-launch-manifest-"):
        return ClassifiedArtifact(path=rendered, rule=CONTROL_STATE_RULE)
    if name.endswith("-smoke-report.json"):
        return ClassifiedArtifact(path=rendered, rule=STARTUP_SMOKE_RULE)
    if name == "hook-state.json" or name == "pm-bot-watch.json":
        return ClassifiedArtifact(path=rendered, rule=SIDE_STATE_RULE)
    if "overview" in name:
        return ClassifiedArtifact(path=rendered, rule=OVERVIEW_RULE)
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
