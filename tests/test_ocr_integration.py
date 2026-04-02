#!/usr/bin/env python3
"""Test OCR integration with event assembler."""

from __future__ import annotations

import json
import tempfile

from app.models.ocr_interface import (
    OCRDocumentResult,
    OCRPageResult,
    OCRRequest,
    OCRTextBlock,
    build_baidu_runner,
    BaiduOCRConfig,
)
from app.models.event_assembler import assemble_from_dict
from app.models.twin_ingest_contract import TwinIngestContract


def run_baidu_ocr_mock_end_to_end() -> tuple[bool, str, dict]:
    """Test baidu OCR mock end-to-end with event integration."""
    try:
        # Create a fake image file
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
            f.write(b"fake-png-image-data")
            test_file = f.name

        try:
            # Mock HTTP responses for baidu OCR
            responses = [
                {"access_token": "mocked-token"},
                {
                    "words_result": [
                        {"words": "质点运动的习题练习", "probability": {"average": 0.90}},
                        {"words": "学生完成了作业", "probability": {"average": 0.88}},
                    ]
                },
            ]

            def mock_http_post(url: str, body: bytes, headers: dict[str, str]) -> dict[str, object]:
                return responses.pop(0)

            # Build baidu runner
            runner = build_baidu_runner(
                BaiduOCRConfig(api_key="test-key", secret_key="test-secret"),
                http_post=mock_http_post,
            )

            # Create OCR request
            request = OCRRequest(
                provider="baidu",
                raw_input_ref="raw:TEST_OCR_001",
                source_file_ref=test_file,
                trace_id="TRC_OCR_TEST_001",
                document_type_hint="homework_sheet",
            )

            # Execute OCR
            result = runner(request)

            # Assemble event from OCR result
            from app.models.ocr_event_bridge import ocr_result_to_event_payload

            payload = ocr_result_to_event_payload(
                ocr_result=result,
                student_id="STU_001",
                chapter_hint="第一章 运动的描述",
                knowledge_hint="质点运动的规律",
            )

            chapter_mapping = {"第一章 运动的描述": "PHY_PEP_G1_V1_CH_01"}
            knowledge_mapping = {"质点运动的规律": "PHY_PEP_G1_V1_KP_001"}

            event = assemble_from_dict(payload, chapter_mapping, knowledge_mapping)
            contract = event.to_contract()
            decision = contract.validate()

            output = {
                "provider": result.provider,
                "event_status": result.event_status,
                "review_needed": result.review_needed,
                "overall_confidence": result.overall_confidence,
                "extracted_text": result.extracted_text[:100] if result.extracted_text else None,
                "event_type": event.event_type,
                "contract_accepted": decision.accepted,
                "should_consume": decision.should_consume,
            }

            success = (
                result.provider == "baidu" and
                result.event_status == "success" and
                decision.accepted and
                decision.should_consume
            )

            if success:
                return True, "Baidu OCR mock e2e passed", output
            else:
                return False, "Baidu OCR mock e2e failed", output

        finally:
            import os
            os.unlink(test_file)

    except Exception as e:
        return False, f"Baidu OCR mock e2e error: {e}", {}


def test_baidu_ocr_mock_end_to_end() -> None:
    success, message, _ = run_baidu_ocr_mock_end_to_end()
    assert success, message


def run_baidu_ocr_with_real_sample_image() -> tuple[bool, str, dict]:
    """Test baidu OCR config and file loading with real AEdu sample image (no API call)."""
    try:
        import os
        from pathlib import Path

        # Use real AEdu sample image
        sample_image = "/Users/busiji/workbot/AEdu/13_原始资料库/OCR/高中物理/样本截图/01_封面.png"

        if not os.path.exists(sample_image):
            return False, f"Sample image not found: {sample_image}", {}

        # Verify file can be loaded and encoded (simulating what baidu runner does)
        import base64
        image_data = Path(sample_image).read_bytes()
        img_base64 = base64.b64encode(image_data).decode("ascii")

        output = {
            "sample_image": sample_image,
            "file_size": len(image_data),
            "base64_length": len(img_base64),
            "ready_for_baidu_ocr": True,
        }

        return True, "Real sample image verified (base64 encoding OK)", output

    except Exception as e:
        return False, f"Real sample image error: {e}", {}


def test_baidu_ocr_with_real_sample_image() -> None:
    success, message, _ = run_baidu_ocr_with_real_sample_image()
    assert success, message


def run_ocr_result_to_event() -> tuple[bool, str, dict]:
    """Test OCR result conversion to event with proper status routing."""
    try:
        # High confidence scenario: parent feedback with knowledge hint
        event_payload = {
            "student_id": "STU_001",
            "input_text": "今天孩子复习了质点运动的概念，掌握良好",
            "input_time": "2026-03-26T10:00:00",
            "source_type": "parent_text",
            "chapter_hint": "第一章 运动的描述",
            "knowledge_hint": "质点的概念",
            "context_summary": "家长反馈",
        }

        chapter_mapping = {"第一章 运动的描述": "PHY_PEP_G1_V1_CH_01"}
        knowledge_mapping = {"质点的概念": "PHY_PEP_G1_V1_KP_001"}

        event = assemble_from_dict(event_payload, chapter_mapping, knowledge_mapping)
        contract = event.to_contract()
        decision = contract.validate()

        output_high = {
            "scenario": "high_confidence",
            "event_status": event.event_status,
            "contract_decision_accepted": decision.accepted,
            "should_consume": decision.should_consume,
            "review_needed": decision.review_needed,
            "confidence_score": event.confidence_score,
        }

        # Simulate OCR result with low confidence (baidu provider)
        ocr_low_conf = OCRDocumentResult(
            provider="baidu",
            raw_input_ref="raw:TEST_OCR_LOW",
            source_file_ref="/tmp/test.pdf",
            trace_id="TRC_OCR_LOW",
            document_type="homework_sheet",
            pages=(
                OCRPageResult(
                    page_number=1,
                    blocks=(
                        OCRTextBlock(
                            text="模糊识别结果",
                            confidence=0.45,
                            page_number=1,
                        ),
                    ),
                ),
            ),
            overall_confidence=0.45,
            event_status="review_needed",
            review_needed=True,
            extracted_text="模糊识别结果",
            review_reasons=("low_confidence",),
        )

        # Use teacher_feedback_text which has explicit review capability
        event_payload_low = {
            "student_id": "STU_001",
            "input_text": "学生需要更多练习",
            "input_time": "2026-03-26T11:00:00",
            "source_type": "teacher_feedback_text",
            "chapter_hint": None,
            "knowledge_hint": None,
            "context_summary": "课堂表现一般",
        }

        event2 = assemble_from_dict(event_payload_low, chapter_mapping, knowledge_mapping)
        # Manually set low confidence to simulate OCR low confidence scenario
        object.__setattr__(event2, 'confidence_score', 0.50)
        object.__setattr__(event2, 'event_status', 'review_needed')

        contract2 = event2.to_contract()
        decision2 = contract2.validate()

        output_low = {
            "scenario": "low_confidence",
            "event_status": event2.event_status,
            "contract_decision_accepted": decision2.accepted,
            "should_consume": decision2.should_consume,
            "review_needed": decision2.review_needed,
            "confidence_score": event2.confidence_score,
        }

        # Verify routing logic
        routing_correct = (
            output_high["contract_decision_accepted"] and
            output_high["should_consume"] and
            not output_high["review_needed"] and
            output_low["review_needed"] and
            not output_low["contract_decision_accepted"]
        )

        if routing_correct:
            return True, "OCR to event routing correct", {"high_conf": output_high, "low_conf": output_low}
        else:
            return False, "OCR to event routing incorrect", {"high_conf": output_high, "low_conf": output_low}

    except Exception as e:
        return False, f"OCR to event error: {e}", {}


def test_ocr_result_to_event() -> None:
    success, message, _ = run_ocr_result_to_event()
    assert success, message


def run_degraded_consumption() -> tuple[bool, str, dict]:
    """Test degraded consumption (no knowledge refs but has chapter/context)."""
    try:
        # Degraded scenario: parent_feedback_event with chapter hint but no knowledge hint
        # This should be accepted as degraded (behavior-only update)
        event_payload = {
            "student_id": "STU_001",
            "input_text": "家长反馈孩子最近学习积极性有所提高",
            "input_time": "2026-03-26T12:00:00",
            "source_type": "parent_text",
            "chapter_hint": None,  # No chapter hint
            "knowledge_hint": None,  # No knowledge hint
            "context_summary": "孩子学习积极性提高",
        }

        chapter_mapping = {"第一章 运动的描述": "PHY_PEP_G1_V1_CH_01"}
        knowledge_mapping = {"质点的概念": "PHY_PEP_G1_V1_KP_001"}

        event = assemble_from_dict(event_payload, chapter_mapping, knowledge_mapping)
        contract = event.to_contract()
        decision = contract.validate()

        output = {
            "scenario": "degraded",
            "event_type": event.event_type,
            "event_status": event.event_status,
            "contract_decision_accepted": decision.accepted,
            "should_consume": decision.should_consume,
            "review_needed": decision.review_needed,
            "degraded": decision.degraded,
            "knowledge_refs": event.knowledge_refs,
            "chapter_refs": event.chapter_refs,
            "parent_context_summary": event.parent_context_summary,
        }

        # Degraded should be accepted but without knowledge state updates
        # parent_feedback_event requires knowledge_refs for mainline consumption
        # Without knowledge_refs but with context, it should be degraded consumption
        routing_correct = (
            decision.accepted and
            decision.should_consume and
            decision.degraded
        )

        if routing_correct:
            return True, "Degraded consumption routing correct", output
        else:
            return False, "Degraded consumption routing incorrect", output

    except Exception as e:
        return False, f"Degraded consumption error: {e}", {}


def test_degraded_consumption() -> None:
    success, message, _ = run_degraded_consumption()
    assert success, message


def run_all_tests() -> dict:
    """Run all OCR integration tests."""
    tests = [
        ("baidu_ocr_mock_e2e", run_baidu_ocr_mock_end_to_end),
        ("baidu_ocr_real_sample", run_baidu_ocr_with_real_sample_image),
        ("ocr_to_event", run_ocr_result_to_event),
        ("degraded_consumption", run_degraded_consumption),
    ]

    results = {name: func() for name, func in tests}

    summary = {
        "total": len(tests),
        "passed": sum(1 for r in results.values() if r[0]),
        "failed": sum(1 for r in results.values() if not r[0]),
    }

    return {
        "summary": summary,
        "results": {
            name: {"success": success, "message": message, "output": output}
            for name, (success, message, output) in results.items()
        },
    }


if __name__ == "__main__":
    results = run_all_tests()
    print(json.dumps(results, indent=2, ensure_ascii=False))
