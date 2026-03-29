"""Event assembler for converting text inputs to standardized learning events."""

from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from app.models.constants import (
    EXECUTION_SCOPE_CANONICAL_VALUES,
    LOW_CONFIDENCE_REVIEW_THRESHOLDS,
)
from app.models.twin_ingest_contract import TwinIngestContract


@dataclass(frozen=True)
class TextInput:
    """Raw text input from parent or teacher."""

    student_id: str
    input_text: str
    input_time: str
    source_type: str  # "parent_text" or "teacher_feedback_text"
    chapter_hint: str | None = None
    knowledge_hint: str | None = None
    behavior_hint: str | None = None
    context_summary: str | None = None

    def __post_init__(self) -> None:
        if self.source_type not in {"parent_text", "teacher_feedback_text"}:
            raise ValueError(f"invalid source_type: {self.source_type}")
        if not self.input_text.strip():
            raise ValueError("input_text must not be empty")


@dataclass
class AssembledEvent:
    """Assembled learning event ready for TWIN ingest."""

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

    def to_contract(self) -> TwinIngestContract:
        """Convert assembled event to TwinIngestContract."""
        return TwinIngestContract(
            event_id=self.event_id,
            student_id=self.student_id,
            event_type=self.event_type,
            source_type=self.source_type,
            event_time=self.event_time,
            region_id=self.region_id,
            stage_level=self.stage_level,
            grade_level=self.grade_level,
            subject=self.subject,
            curriculum_version_id=self.curriculum_version_id,
            event_status=self.event_status,
            confidence_score=self.confidence_score,
            event_summary=self.event_summary,
            raw_input_ref=self.raw_input_ref,
            trace_id=self.trace_id,
            chapter_refs=self.chapter_refs,
            knowledge_refs=self.knowledge_refs,
            anchor_refs=self.anchor_refs,
            ability_refs=self.ability_refs,
            behavior_tags=self.behavior_tags,
            teacher_context_summary=self.teacher_context_summary,
            parent_context_summary=self.parent_context_summary,
        )


def _generate_event_id(student_id: str, input_time: str, source_type: str) -> str:
    """Generate deterministic event ID from input components."""
    key = f"{student_id}:{input_time}:{source_type}"
    hash_hex = hashlib.sha256(key.encode("utf-8")).hexdigest()[:12]
    return f"EVT_{hash_hex.upper()}"


def _generate_trace_id() -> str:
    """Generate unique trace ID for request tracking."""
    return f"TRC_{uuid.uuid4().hex[:16].upper()}"


def _compute_confidence(
    input_text: str,
    has_chapter_hint: bool,
    has_knowledge_hint: bool,
    source_type: str,
) -> float:
    """Compute confidence score based on input quality indicators."""
    base_confidence = 0.75

    if len(input_text) >= 50:
        base_confidence += 0.10
    elif len(input_text) >= 20:
        base_confidence += 0.05

    if has_knowledge_hint:
        base_confidence += 0.10
    elif has_chapter_hint:
        base_confidence += 0.05

    if source_type == "teacher_feedback_text":
        base_confidence += 0.05

    return min(base_confidence, 1.0)


def _extract_keywords(text: str) -> list[str]:
    """Extract potential knowledge point keywords from text."""
    keywords = []
    keyword_markers = [
        "概念",
        "规律",
        "公式",
        "实验",
        "理解",
        "掌握",
        "应用",
        "分析",
        "判断",
        "计算",
    ]
    for marker in keyword_markers:
        if marker in text:
            keywords.append(marker)
    return keywords


def _determine_event_type(input_text: str, source_type: str) -> str:
    """Determine event type based on input content analysis."""
    text_lower = input_text.lower()

    homework_indicators = ["作业", "homework", "练习", "习题", "做题"]
    correction_indicators = ["订正", "改正", "错题", "correction", "改错"]
    feedback_indicators = ["反馈", "评价", "comment", "反馈", "建议"]

    if source_type == "teacher_feedback_text":
        if any(ind in text_lower for ind in correction_indicators):
            return "correction_followup_event"
        return "teacher_feedback_event"

    if any(ind in text_lower for ind in homework_indicators):
        if any(ind in text_lower for ind in correction_indicators):
            return "correction_followup_event"
        return "homework_result_event"

    if any(ind in text_lower for ind in feedback_indicators):
        return "parent_feedback_event"

    return "parent_feedback_event"


def _generate_summary(input_text: str, max_length: int = 100) -> str:
    """Generate event summary from input text."""
    if len(input_text) <= max_length:
        return input_text.strip()
    return input_text[: max_length - 3].strip() + "..."


def assemble_event(
    input_data: TextInput,
    *,
    chapter_mapping: dict[str, str] | None = None,
    knowledge_mapping: dict[str, str] | None = None,
    override_confidence: float | None = None,
) -> AssembledEvent:
    """
    Assemble a raw text input into a standardized learning event.

    Args:
        input_data: Raw text input from parent or teacher
        chapter_mapping: Optional mapping from chapter hints to chapter IDs
        knowledge_mapping: Optional mapping from knowledge hints to knowledge IDs
        override_confidence: Optional confidence score override (e.g., from OCR)

    Returns:
        AssembledEvent ready for TWIN ingest validation
    """
    event_id = _generate_event_id(input_data.student_id, input_data.input_time, input_data.source_type)
    trace_id = _generate_trace_id()
    event_type = _determine_event_type(input_data.input_text, input_data.source_type)

    has_chapter_hint = bool(input_data.chapter_hint)
    has_knowledge_hint = bool(input_data.knowledge_hint)

    # Use override confidence if provided (e.g., from OCR results)
    if override_confidence is not None:
        confidence = override_confidence
    else:
        confidence = _compute_confidence(
            input_data.input_text,
            has_chapter_hint,
            has_knowledge_hint,
            input_data.source_type,
        )

    chapter_refs: list[str] = []
    knowledge_refs: list[str] = []

    if chapter_mapping and input_data.chapter_hint:
        for hint in input_data.chapter_hint.split(","):
            hint = hint.strip()
            if hint in chapter_mapping:
                chapter_refs.append(chapter_mapping[hint])

    if knowledge_mapping and input_data.knowledge_hint:
        for hint in input_data.knowledge_hint.split(","):
            hint = hint.strip()
            if hint in knowledge_mapping:
                knowledge_refs.append(knowledge_mapping[hint])

    behavior_tags: list[str] = []
    if input_data.behavior_hint:
        behavior_tags = [tag.strip() for tag in input_data.behavior_hint.split(",")]

    event_summary = _generate_summary(input_data.input_text)

    event_status = "success"
    threshold = LOW_CONFIDENCE_REVIEW_THRESHOLDS.get(input_data.source_type, 0.65)
    if confidence < threshold:
        event_status = "review_needed"

    teacher_context_summary = None
    parent_context_summary = None
    if input_data.source_type == "teacher_feedback_text":
        teacher_context_summary = input_data.context_summary or input_data.input_text
    else:
        parent_context_summary = input_data.context_summary or input_data.input_text

    return AssembledEvent(
        event_id=event_id,
        student_id=input_data.student_id,
        event_type=event_type,
        source_type=input_data.source_type,
        event_time=input_data.input_time,
        region_id=EXECUTION_SCOPE_CANONICAL_VALUES["region_id"],
        stage_level=EXECUTION_SCOPE_CANONICAL_VALUES["stage_level"],
        grade_level=EXECUTION_SCOPE_CANONICAL_VALUES["grade_level"],
        subject=EXECUTION_SCOPE_CANONICAL_VALUES["subject"],
        curriculum_version_id=EXECUTION_SCOPE_CANONICAL_VALUES["curriculum_version_id"],
        event_status=event_status,
        confidence_score=confidence,
        event_summary=event_summary,
        raw_input_ref=f"raw:{event_id}",
        trace_id=trace_id,
        chapter_refs=chapter_refs,
        knowledge_refs=knowledge_refs,
        behavior_tags=behavior_tags,
        teacher_context_summary=teacher_context_summary,
        parent_context_summary=parent_context_summary,
    )


def assemble_from_dict(
    payload: dict[str, Any],
    chapter_mapping: dict[str, str] | None = None,
    knowledge_mapping: dict[str, str] | None = None,
) -> AssembledEvent:
    """
    Assemble event from raw dictionary payload.

    Args:
        payload: Raw event payload dictionary
        chapter_mapping: Optional chapter hint to ID mapping
        knowledge_mapping: Optional knowledge hint to ID mapping

    Returns:
        AssembledEvent ready for TWIN ingest validation
    """
    input_data = TextInput(
        student_id=str(payload["student_id"]),
        input_text=str(payload["input_text"]),
        input_time=str(payload.get("input_time", datetime.now().isoformat())),
        source_type=str(payload.get("source_type", "parent_text")),
        chapter_hint=payload.get("chapter_hint"),
        knowledge_hint=payload.get("knowledge_hint"),
        behavior_hint=payload.get("behavior_hint"),
        context_summary=payload.get("context_summary"),
    )
    # Extract OCR confidence if present (from ocr_event_bridge)
    override_confidence = payload.get("_ocr_confidence")
    return assemble_event(
        input_data,
        chapter_mapping=chapter_mapping,
        knowledge_mapping=knowledge_mapping,
        override_confidence=override_confidence,
    )
