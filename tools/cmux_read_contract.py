#!/usr/bin/env python3
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from workspace.tools.cmux_control_packet import ControlPacketError, validate_control_packet


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


@dataclass(frozen=True)
class VerificationPacketEntry:
    slot: str
    path: str
    via_rule: str
    extraction: str | None


SUMMARY_RULE = ReadRule(
    name="commander_summary",
    priority=100,
    normal_path_allowed=True,
    escalation_required=False,
    reason="short commander-facing summary artifact",
)
WORKFLOW_LOG_RULE = ReadRule(
    name="workflow_log",
    priority=95,
    normal_path_allowed=True,
    escalation_required=False,
    reason="curated end-to-end workflow log artifact for commander and governance review",
)
CONTROL_PACKET_RULE = ReadRule(
    name="control_packet_artifact",
    priority=90,
    normal_path_allowed=True,
    escalation_required=False,
    reason="machine-readable control packet artifact",
)
CONSUMER_STATE_RULE = ReadRule(
    name="consumer_state",
    priority=80,
    normal_path_allowed=True,
    escalation_required=False,
    reason="consumer-state artifact with auxiliary runtime state; embedded control_packet data does not satisfy the standalone control-packet slot",
)
FINISH_RECEIPT_RULE = ReadRule(
    name="finish_receipt_journal",
    priority=75,
    normal_path_allowed=True,
    escalation_required=False,
    reason="A7 finish-cycle receipt journal",
)
MAIN_THREAD_ACTION_RULE = ReadRule(
    name="main_thread_action_journal",
    priority=70,
    normal_path_allowed=True,
    escalation_required=False,
    reason="A8/A9 main-thread action journal",
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
ARCHIVE_ONLY_RULE = ReadRule(
    name="archive_only",
    priority=5,
    normal_path_allowed=False,
    escalation_required=True,
    reason="historical archive artifact; evidence-only and never a legal current task source",
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

REQUIRED_VERIFICATION_PACKET_SLOTS = (
    "control_packet",
    "consumer_state",
    "finish_receipt",
    "workflow_log",
    "main_thread_actions",
)
VERIFICATION_PACKET_PROOF_BASIS = "fresh_native_pass_only"
CONSUMER_STATE_CONTROL_PACKET_EXTRACTION = "assignments[*].control_packet"


def describe_verification_packet_contract() -> dict[str, object]:
    return {
        "proof_basis": VERIFICATION_PACKET_PROOF_BASIS,
        "slot_order": list(REQUIRED_VERIFICATION_PACKET_SLOTS),
    }


def consumer_state_covers_control_packet(payload: Any) -> bool:
    if not isinstance(payload, dict):
        return False
    assignments = payload.get("assignments")
    if not isinstance(assignments, dict):
        return False
    for entry in assignments.values():
        if not isinstance(entry, dict):
            continue
        control_packet = entry.get("control_packet")
        if isinstance(control_packet, dict) and control_packet:
            return True
    return False


def _load_json_payload(path: str | Path) -> Any | None:
    candidate = Path(path)
    if not candidate.exists() or not candidate.is_file():
        return None
    try:
        return json.loads(candidate.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _standalone_control_packet_exists(path: str | None) -> bool:
    if not path:
        return False
    payload = _load_json_payload(path)
    if not isinstance(payload, dict) or not payload:
        return False
    try:
        validate_control_packet(payload)
    except ControlPacketError:
        return False
    return True


def classify_runtime_artifact(path: str | Path) -> ClassifiedArtifact:
    rendered = str(path)
    lowered = rendered.lower()
    name = Path(rendered).name.lower()

    if "/workflow-runs/" in lowered or name == "workflow-run-index.json":
        return ClassifiedArtifact(path=rendered, rule=ARCHIVE_ONLY_RULE)
    if "summary" in name and name.endswith(".json"):
        return ClassifiedArtifact(path=rendered, rule=SUMMARY_RULE)
    if "workflow-log" in name and name.endswith(".json"):
        return ClassifiedArtifact(path=rendered, rule=WORKFLOW_LOG_RULE)
    if "control-packet" in name and name.endswith(".json"):
        return ClassifiedArtifact(path=rendered, rule=CONTROL_PACKET_RULE)
    if name == "cmux-consumer-state-latest.json":
        return ClassifiedArtifact(path=rendered, rule=CONSUMER_STATE_RULE)
    if name == "cmux-finish-receipts.jsonl":
        return ClassifiedArtifact(path=rendered, rule=FINISH_RECEIPT_RULE)
    if name == "cmux-main-thread-actions.jsonl":
        return ClassifiedArtifact(path=rendered, rule=MAIN_THREAD_ACTION_RULE)
    if name.startswith("runtime-launch-manifest-"):
        return ClassifiedArtifact(path=rendered, rule=SIDE_STATE_RULE)
    if name == "cmux-assignment.json" or name == "current-runtime.json":
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


def choose_verification_packet_sources(
    paths: Iterable[str | Path],
) -> list[VerificationPacketEntry]:
    classified = [classify_runtime_artifact(path) for path in paths]
    by_rule: dict[str, list[ClassifiedArtifact]] = {}
    for item in classified:
        by_rule.setdefault(item.rule.name, []).append(item)

    def first_path(rule_name: str) -> str | None:
        candidates = sorted(by_rule.get(rule_name, []), key=lambda item: item.path)
        if not candidates:
            return None
        return candidates[0].path

    def first_valid_control_packet_path() -> str | None:
        explicit_candidates = [item.path for item in sorted(by_rule.get("control_packet_artifact", []), key=lambda item: item.path)]
        fallback_candidates = sorted(
            item.path
            for item in classified
            if Path(item.path).suffix.lower() == ".json" and item.path not in explicit_candidates
        )
        for candidate_path in [*explicit_candidates, *fallback_candidates]:
            if _standalone_control_packet_exists(candidate_path):
                return candidate_path
        return None

    entries: list[VerificationPacketEntry] = []
    control_packet_path = first_valid_control_packet_path()
    consumer_state_path = first_path("consumer_state")
    if control_packet_path:
        entries.append(
            VerificationPacketEntry(
                slot="control_packet",
                path=control_packet_path,
                via_rule="control_packet_artifact",
                extraction=None,
            )
        )
    if consumer_state_path:
        entries.append(
            VerificationPacketEntry(
                slot="consumer_state",
                path=consumer_state_path,
                via_rule="consumer_state",
                extraction=None,
            )
        )
    finish_receipt_path = first_path("finish_receipt_journal")
    if finish_receipt_path:
        entries.append(
            VerificationPacketEntry(
                slot="finish_receipt",
                path=finish_receipt_path,
                via_rule="finish_receipt_journal",
                extraction=None,
            )
        )
    workflow_log_path = first_path("workflow_log")
    if workflow_log_path:
        entries.append(
            VerificationPacketEntry(
                slot="workflow_log",
                path=workflow_log_path,
                via_rule="workflow_log",
                extraction=None,
            )
        )
    main_thread_actions_path = first_path("main_thread_action_journal")
    if main_thread_actions_path:
        entries.append(
            VerificationPacketEntry(
                slot="main_thread_actions",
                path=main_thread_actions_path,
                via_rule="main_thread_action_journal",
                extraction=None,
            )
        )
    return entries


def render_verification_packet_sources(
    paths: Iterable[str | Path],
) -> list[dict[str, str]]:
    rendered: list[dict[str, str]] = []
    for entry in choose_verification_packet_sources(paths):
        payload = {
            "slot": entry.slot,
            "path": entry.path,
            "via_rule": entry.via_rule,
        }
        if entry.extraction:
            payload["extraction"] = entry.extraction
        rendered.append(payload)
    return rendered


def explain_forensic_requirement(path: str | Path) -> str:
    classified = classify_runtime_artifact(path)
    if classified.rule.normal_path_allowed:
        return f"{classified.path} is normal-path readable as {classified.rule.name}."
    return (
        f"{classified.path} is {classified.rule.name}; escalation is required because "
        f"{classified.rule.reason}."
    )
