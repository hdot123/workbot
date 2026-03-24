"""Minimal TWIN ingest contract model and validation helpers."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.models.constants import (
    ALLOWED_EVENT_STATUSES,
    ALLOWED_EVENT_TYPES,
    ALLOWED_SOURCE_TYPES,
    CONSUMABLE_EVENT_STATUSES,
    EVENT_SOURCE_ALLOWLIST,
    EXECUTION_SCOPE_ALLOWED_VALUES,
    EXECUTION_SCOPE_CANONICAL_VALUES,
    LOW_CONFIDENCE_REVIEW_THRESHOLDS,
    REQUIRED_FIELDS,
)


def _has_items(values: list[str]) -> bool:
    return bool(values)


def _has_text(value: str | None) -> bool:
    return bool(value and value.strip())


@dataclass
class TwinIngestDecision:
    accepted: bool
    final_status: str
    should_consume: bool
    reason: str
    missing_fields: list[str] = field(default_factory=list)
    degraded: bool = False
    review_needed: bool = False
    knowledge_state_allowed: bool = False
    behavior_state_allowed: bool = False


@dataclass
class TwinIngestContract:
    event_id: str
    student_id: str
    event_type: str
    source_type: str
    event_time: str
    region_id: str
    stage_level: str
    grade_level: str
    subject: str
    curriculum_version_id: str
    event_status: str
    confidence_score: float
    event_summary: str
    raw_input_ref: str
    trace_id: str
    chapter_refs: list[str] = field(default_factory=list)
    knowledge_refs: list[str] = field(default_factory=list)
    anchor_refs: list[str] = field(default_factory=list)
    ability_refs: list[str] = field(default_factory=list)
    behavior_tags: list[str] = field(default_factory=list)
    teacher_context_summary: str | None = None
    parent_context_summary: str | None = None
    review_ticket_ref: str | None = None
    source_file_ref: str | None = None
    score_payload: dict[str, Any] | None = None

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "TwinIngestContract":
        missing_fields = [name for name in REQUIRED_FIELDS if name not in payload]
        if missing_fields:
            missing_fields_text = ", ".join(missing_fields)
            raise ValueError(f"missing required fields: {missing_fields_text}")

        data = dict(payload)
        data.setdefault("chapter_refs", [])
        data.setdefault("knowledge_refs", [])
        data.setdefault("anchor_refs", [])
        data.setdefault("ability_refs", [])
        data.setdefault("behavior_tags", [])
        data.setdefault("teacher_context_summary", None)
        data.setdefault("parent_context_summary", None)
        data.setdefault("review_ticket_ref", None)
        data.setdefault("source_file_ref", None)
        data.setdefault("score_payload", None)
        return cls(**data)

    def _normalize_execution_scope(self) -> TwinIngestDecision | None:
        for field_name, expected in EXECUTION_SCOPE_ALLOWED_VALUES.items():
            actual = getattr(self, field_name)
            canonical = EXECUTION_SCOPE_CANONICAL_VALUES[field_name]

            if isinstance(expected, frozenset):
                if actual not in expected:
                    return TwinIngestDecision(False, "rejected", False, f"out_of_scope_{field_name}")
                setattr(self, field_name, canonical)
                continue

            if actual != expected:
                return TwinIngestDecision(False, "rejected", False, f"out_of_scope_{field_name}")

        return None

    @property
    def allows_mainline_consumption(self) -> bool:
        return self.event_status in CONSUMABLE_EVENT_STATUSES and _has_items(self.knowledge_refs)

    @property
    def requires_degraded_consumption(self) -> bool:
        has_behavior_clues = (
            _has_items(self.behavior_tags)
            or _has_text(self.teacher_context_summary)
            or _has_text(self.parent_context_summary)
        )
        return not _has_items(self.knowledge_refs) and (_has_items(self.chapter_refs) or has_behavior_clues)

    def validate(self) -> TwinIngestDecision:
        if self.event_type not in ALLOWED_EVENT_TYPES:
            return TwinIngestDecision(False, "rejected", False, "invalid_event_type")

        if self.source_type not in ALLOWED_SOURCE_TYPES:
            return TwinIngestDecision(False, "rejected", False, "invalid_source_type")

        if self.event_status not in ALLOWED_EVENT_STATUSES:
            return TwinIngestDecision(False, "rejected", False, "invalid_event_status")

        if self.event_status == "rejected":
            raise ValueError(
                "event_status 为 rejected 的事件必须在上游 reject，不能进入 TWIN 输入契约"
            )

        allowed_sources = EVENT_SOURCE_ALLOWLIST[self.event_type]
        if self.source_type not in allowed_sources:
            return TwinIngestDecision(False, "rejected", False, "invalid_event_source_combination")

        if not 0.0 <= self.confidence_score <= 1.0:
            return TwinIngestDecision(False, "rejected", False, "invalid_confidence_score")

        scope_result = self._normalize_execution_scope()
        if scope_result is not None:
            return scope_result

        if self.event_status == "review_needed":
            if not self.review_ticket_ref:
                return TwinIngestDecision(
                    False,
                    "review_needed",
                    False,
                    "missing_review_ticket_ref",
                    review_needed=True,
                )
            return TwinIngestDecision(
                False,
                "review_needed",
                False,
                "explicit_review_needed",
                review_needed=True,
            )

        threshold = LOW_CONFIDENCE_REVIEW_THRESHOLDS.get(self.source_type)
        if threshold is not None and self.confidence_score < threshold:
            return TwinIngestDecision(
                False,
                "review_needed",
                False,
                "low_confidence",
                review_needed=True,
            )

        if _has_items(self.knowledge_refs):
            return TwinIngestDecision(
                accepted=True,
                final_status=self.event_status,
                should_consume=self.event_status in CONSUMABLE_EVENT_STATUSES,
                reason="accepted_with_knowledge_refs",
                knowledge_state_allowed=True,
                behavior_state_allowed=True,
            )

        if _has_items(self.chapter_refs) or _has_text(self.teacher_context_summary) or _has_text(
            self.parent_context_summary
        ) or _has_items(self.behavior_tags):
            return TwinIngestDecision(
                accepted=True,
                final_status="degraded",
                should_consume=True,
                reason="accepted_degraded_without_knowledge_refs",
                degraded=True,
                knowledge_state_allowed=False,
                behavior_state_allowed=True,
            )

        if _has_items(self.anchor_refs):
            return TwinIngestDecision(
                False,
                "review_needed",
                False,
                "anchor_only_requires_review",
                review_needed=True,
            )

        return TwinIngestDecision(
            False,
            "review_needed",
            False,
            "insufficient_refs_for_twin",
            review_needed=True,
        )
