"""Frozen constants for the ARCH-022 TWIN ingest contract."""

from __future__ import annotations

FROZEN_REGION_IDS = frozenset({"安徽", "安徽省"})
FROZEN_REGION_ID_CANONICAL = "安徽"
FROZEN_STAGE_LEVEL = "高中"
FROZEN_GRADE_LEVEL = "高一"
FROZEN_SUBJECT = "物理"
FROZEN_CURRICULUM_VERSION_ID = "PHY_PEP_G1_V1"

ALLOWED_EVENT_TYPES = frozenset(
    {
        "homework_result_event",
        "correction_followup_event",
        "teacher_feedback_event",
        "parent_feedback_event",
        "scan_ocr_result_event",
        "reviewed_learning_event",
    }
)

ALLOWED_SOURCE_TYPES = frozenset(
    {
        "parent_text",
        "teacher_feedback_text",
        "scan_ocr",
        "reviewed_event",
    }
)

ALLOWED_EVENT_STATUSES = frozenset(
    {
        "success",
        "degraded",
        "review_needed",
        "rejected",
    }
)

CONSUMABLE_EVENT_STATUSES = frozenset({"success", "degraded"})
NON_CONSUMABLE_EVENT_STATUSES = frozenset({"review_needed", "rejected"})

SCAN_OCR_REVIEW_THRESHOLD = 0.70
TEXT_REVIEW_THRESHOLD = 0.65

REQUIRED_FIELDS = (
    "event_id",
    "student_id",
    "event_type",
    "source_type",
    "event_time",
    "region_id",
    "stage_level",
    "grade_level",
    "subject",
    "curriculum_version_id",
    "event_status",
    "confidence_score",
    "event_summary",
    "raw_input_ref",
    "trace_id",
)

EXECUTION_SCOPE_ALLOWED_VALUES = {
    "region_id": FROZEN_REGION_IDS,
    "stage_level": FROZEN_STAGE_LEVEL,
    "grade_level": FROZEN_GRADE_LEVEL,
    "subject": FROZEN_SUBJECT,
    "curriculum_version_id": FROZEN_CURRICULUM_VERSION_ID,
}

EXECUTION_SCOPE_CANONICAL_VALUES = {
    "region_id": FROZEN_REGION_ID_CANONICAL,
    "stage_level": FROZEN_STAGE_LEVEL,
    "grade_level": FROZEN_GRADE_LEVEL,
    "subject": FROZEN_SUBJECT,
    "curriculum_version_id": FROZEN_CURRICULUM_VERSION_ID,
}

LOW_CONFIDENCE_REVIEW_THRESHOLDS = {
    "scan_ocr": SCAN_OCR_REVIEW_THRESHOLD,
    "parent_text": TEXT_REVIEW_THRESHOLD,
    "teacher_feedback_text": TEXT_REVIEW_THRESHOLD,
}

EVENT_SOURCE_ALLOWLIST = {
    "homework_result_event": frozenset({"teacher_feedback_text", "scan_ocr"}),
    "correction_followup_event": frozenset({"teacher_feedback_text", "parent_text"}),
    "teacher_feedback_event": frozenset({"teacher_feedback_text"}),
    "parent_feedback_event": frozenset({"parent_text"}),
    "scan_ocr_result_event": frozenset({"scan_ocr"}),
    "reviewed_learning_event": frozenset({"reviewed_event"}),
}
