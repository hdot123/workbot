from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pytest

from app.models.twin_ingest_contract import TwinIngestContract


def build_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "event_id": "EVT_TWIN_001",
        "student_id": "STU_AH_G1_PHY_001",
        "event_type": "correction_followup_event",
        "source_type": "teacher_feedback_text",
        "event_time": "2026-03-21T10:20:00+08:00",
        "region_id": "安徽",
        "stage_level": "高中",
        "grade_level": "高一",
        "subject": "物理",
        "curriculum_version_id": "PHY_PEP_G1_V1",
        "event_status": "success",
        "confidence_score": 0.91,
        "event_summary": "作业订正完成，但加速度方向判断仍有重复错误，课堂响应偏慢。",
        "chapter_refs": ["PHY_PEP_G1_V1_SEC_03_01"],
        "knowledge_refs": ["PHY_PEP_G1_KP_021"],
        "anchor_refs": ["PHY_ANCHOR_020"],
        "behavior_tags": ["correction_completed", "repeat_error", "slow_response"],
        "score_payload": {"completion_rate": 1.0, "accuracy_rate": 0.8},
        "raw_input_ref": "RAW_EVT_TWIN_001",
        "trace_id": "TRACE_TWIN_001",
    }
    payload.update(overrides)
    return payload


def test_accepts_valid_anhui_mock_case() -> None:
    contract = TwinIngestContract.from_dict(build_payload())

    decision = contract.validate()

    assert contract.student_id == "STU_AH_G1_PHY_001"
    assert contract.region_id == "安徽"
    assert decision.accepted is True
    assert decision.final_status == "success"
    assert decision.should_consume is True
    assert contract.allows_mainline_consumption is True
    assert contract.requires_degraded_consumption is False


def test_rejects_mismatched_event_type_and_source_type() -> None:
    contract = TwinIngestContract.from_dict(
        build_payload(
            event_type="parent_feedback_event",
            source_type="scan_ocr",
        )
    )

    decision = contract.validate()

    assert decision.accepted is False
    assert decision.final_status == "rejected"
    assert decision.reason == "invalid_event_source_combination"


def test_ocr_below_threshold_must_be_review_needed() -> None:
    contract = TwinIngestContract.from_dict(
        build_payload(
            event_id="EVT_TWIN_003",
            event_type="scan_ocr_result_event",
            source_type="scan_ocr",
            event_status="success",
            confidence_score=0.69,
            event_summary="OCR 文本片段不足，候选引用不稳定。",
            source_file_ref="SRC_FILE_003",
        )
    )

    decision = contract.validate()

    assert decision.accepted is False
    assert decision.final_status == "review_needed"
    assert decision.reason == "low_confidence"
    assert decision.review_needed is True


def test_text_below_threshold_must_be_review_needed() -> None:
    contract = TwinIngestContract.from_dict(
        build_payload(
            event_id="EVT_TWIN_004",
            event_status="degraded",
            confidence_score=0.64,
        )
    )

    decision = contract.validate()

    assert decision.accepted is False
    assert decision.final_status == "review_needed"
    assert decision.reason == "low_confidence"
    assert decision.review_needed is True


def test_review_needed_requires_review_ticket_ref() -> None:
    contract = TwinIngestContract.from_dict(
        build_payload(
            event_id="EVT_TWIN_005",
            event_status="review_needed",
            confidence_score=0.91,
        )
    )

    decision = contract.validate()

    assert decision.accepted is False
    assert decision.final_status == "review_needed"
    assert decision.reason == "missing_review_ticket_ref"


def test_rejected_status_is_blocked_upstream() -> None:
    contract = TwinIngestContract.from_dict(
        build_payload(
            event_id="EVT_TWIN_005B",
            event_status="rejected",
        )
    )

    with pytest.raises(ValueError, match="不能进入 TWIN 输入契约"):
        contract.validate()


def test_missing_knowledge_refs_with_chapter_clues_degrades() -> None:
    payload = deepcopy(build_payload())
    payload["event_id"] = "EVT_TWIN_006"
    payload["knowledge_refs"] = []
    payload["event_status"] = "success"

    contract = TwinIngestContract.from_dict(payload)
    decision = contract.validate()

    assert decision.accepted is True
    assert decision.final_status == "degraded"
    assert decision.should_consume is True
    assert decision.degraded is True


def test_missing_knowledge_refs_with_behavior_clues_degrades() -> None:
    contract = TwinIngestContract.from_dict(
        build_payload(
            event_id="EVT_TWIN_007",
            event_type="parent_feedback_event",
            source_type="parent_text",
            event_status="degraded",
            chapter_refs=[],
            knowledge_refs=[],
            anchor_refs=[],
            behavior_tags=["late_homework", "repeat_correction"],
            parent_context_summary="家长观察到学生完成作业较慢，但已开始主动订正。",
        )
    )

    decision = contract.validate()

    assert decision.accepted is True
    assert decision.final_status == "degraded"
    assert decision.should_consume is True
    assert decision.degraded is True
    assert contract.allows_mainline_consumption is False
    assert contract.requires_degraded_consumption is True


def test_execution_scope_rejects_non_anhui_region() -> None:
    contract = TwinIngestContract.from_dict(build_payload(region_id="GD_SZ"))

    decision = contract.validate()

    assert decision.accepted is False
    assert decision.final_status == "rejected"
    assert decision.reason == "out_of_scope_region_id"


def test_allows_anhui_province_alias_and_normalizes_to_anhui() -> None:
    contract = TwinIngestContract.from_dict(build_payload(region_id="安徽省"))

    decision = contract.validate()

    assert decision.accepted is True
    assert contract.region_id == "安徽"


def test_accepts_review_needed_ocr_mock_case() -> None:
    contract = TwinIngestContract.from_dict(
        build_payload(
            event_id="EVT_TWIN_008",
            event_type="scan_ocr_result_event",
            source_type="scan_ocr",
            event_time="2026-03-21T19:40:00+08:00",
            event_status="review_needed",
            confidence_score=0.56,
            event_summary="OCR 文本片段不足，章节与知识点候选冲突。",
            chapter_refs=["PHY_PEP_G1_V1_SEC_03_01", "PHY_PEP_G1_V1_SEC_04_02"],
            knowledge_refs=[],
            anchor_refs=["PHY_ANCHOR_044"],
            review_ticket_ref="REVIEW_TWIN_003",
            source_file_ref="SRC_FILE_003",
        )
    )

    decision = contract.validate()

    assert decision.accepted is False
    assert decision.final_status == "review_needed"
    assert decision.reason == "explicit_review_needed"
    assert decision.review_needed is True
    assert contract.region_id == "安徽"


def test_required_fields_still_raise_validation_error() -> None:
    payload = deepcopy(build_payload())
    payload.pop("trace_id")

    with pytest.raises(ValueError, match="trace_id"):
        TwinIngestContract.from_dict(payload)


def test_invalid_event_status_is_rejected() -> None:
    contract = TwinIngestContract.from_dict(build_payload(event_status="queued"))

    decision = contract.validate()

    assert decision.accepted is False
    assert decision.final_status == "rejected"
    assert decision.reason == "invalid_event_status"
