#!/usr/bin/env python3
"""Test OCR event bridge integration."""

from __future__ import annotations

import json
import os
import tempfile

from app.models.event_assembler import assemble_from_dict
from app.models.ocr_event_bridge import (
    assemble_ocr_event,
    ocr_result_to_event_payload,
    process_ocr_request,
)
from app.models.ocr_interface import (
    OCRDocumentResult,
    OCRPageResult,
    OCRRequest,
    OCRTextBlock,
    build_ocr_service_from_env,
    build_baidu_runner,
    BaiduOCRConfig,
)
from app.models.twin_ingest_contract import TwinIngestContract


def run_ocr_event_bridge_high_confidence() -> tuple[bool, str, dict]:
    """Test OCR event bridge with high confidence result (baidu provider)."""
    try:
        # Simulate high confidence OCR result from baidu provider
        ocr_result = OCRDocumentResult(
            provider="baidu",
            raw_input_ref="raw:OCR_HIGH_001",
            source_file_ref="/tmp/test.pdf",
            trace_id="TRC_OCR_HIGH_001",
            document_type="homework_sheet",
            pages=(
                OCRPageResult(
                    page_number=1,
                    blocks=(
                        OCRTextBlock(
                            text="质点运动的规律习题",
                            confidence=0.92,
                            page_number=1,
                        ),
                    ),
                ),
            ),
            overall_confidence=0.92,
            event_status="success",
            review_needed=False,
            extracted_text="质点运动的规律习题",
        )

        # Convert to event payload
        payload = ocr_result_to_event_payload(
            ocr_result=ocr_result,
            student_id="STU_001",
            chapter_hint="第一章 运动的描述",
            knowledge_hint="质点运动的规律",
        )

        # Assemble event
        chapter_mapping = {"第一章 运动的描述": "PHY_PEP_G1_V1_CH_01"}
        knowledge_mapping = {"质点运动的规律": "PHY_PEP_G1_V1_KP_002"}

        event = assemble_from_dict(payload, chapter_mapping, knowledge_mapping)
        contract = event.to_contract()
        decision = contract.validate()

        output = {
            "scenario": "high_confidence",
            "ocr_confidence": ocr_result.overall_confidence,
            "event_type": event.event_type,
            "event_status": event.event_status,
            "contract_accepted": decision.accepted,
            "should_consume": decision.should_consume,
            "review_needed": decision.review_needed,
            "knowledge_refs": event.knowledge_refs,
        }

        # Verify high confidence flow
        success = (
            decision.accepted and
            decision.should_consume and
            not decision.review_needed and
            len(event.knowledge_refs) > 0
        )

        if success:
            return True, "High confidence OCR event bridge passed", output
        else:
            return False, "High confidence OCR event bridge failed", output

    except Exception as e:
        return False, f"High confidence error: {e}", {}


def test_ocr_event_bridge_high_confidence() -> None:
    success, message, _ = run_ocr_event_bridge_high_confidence()
    assert success, message


def run_ocr_event_bridge_low_confidence() -> tuple[bool, str, dict]:
    """Test OCR event bridge with low confidence result (baidu provider, should route to review)."""
    try:
        # Simulate low confidence OCR result from baidu provider
        ocr_result = OCRDocumentResult(
            provider="baidu",
            raw_input_ref="raw:OCR_LOW_001",
            source_file_ref="/tmp/test2.pdf",
            trace_id="TRC_OCR_LOW_001",
            document_type="homework_sheet",
            pages=(
                OCRPageResult(
                    page_number=1,
                    blocks=(
                        OCRTextBlock(
                            text="模糊",
                            confidence=0.45,
                            page_number=1,
                        ),
                    ),
                ),
            ),
            overall_confidence=0.45,
            event_status="review_needed",
            review_needed=True,
            extracted_text="模糊",
            review_reasons=("low_confidence",),
        )

        # Convert to event payload
        payload = ocr_result_to_event_payload(
            ocr_result=ocr_result,
            student_id="STU_001",
            chapter_hint="第一章 运动的描述",
            knowledge_hint="质点运动的规律",
        )

        # Assemble event
        chapter_mapping = {"第一章 运动的描述": "PHY_PEP_G1_V1_CH_01"}
        knowledge_mapping = {"质点运动的规律": "PHY_PEP_G1_V1_KP_002"}

        event = assemble_from_dict(payload, chapter_mapping, knowledge_mapping)
        contract = event.to_contract()
        decision = contract.validate()

        output = {
            "scenario": "low_confidence",
            "ocr_confidence": ocr_result.overall_confidence,
            "event_type": event.event_type,
            "event_status": event.event_status,
            "contract_accepted": decision.accepted,
            "should_consume": decision.should_consume,
            "review_needed": decision.review_needed,
        }

        # Verify low confidence flow routes to review
        success = (
            not decision.accepted and
            not decision.should_consume and
            decision.review_needed
        )

        if success:
            return True, "Low confidence OCR event bridge passed (correctly routed to review)", output
        else:
            return False, "Low confidence OCR event bridge failed", output

    except Exception as e:
        return False, f"Low confidence error: {e}", {}


def test_ocr_event_bridge_low_confidence() -> None:
    success, message, _ = run_ocr_event_bridge_low_confidence()
    assert success, message


def run_ocr_event_bridge_degraded() -> tuple[bool, str, dict]:
    """Test OCR event bridge with degraded result (baidu provider, no knowledge refs)."""
    try:
        # Simulate degraded OCR result from baidu provider (no specific knowledge identified)
        ocr_result = OCRDocumentResult(
            provider="baidu",
            raw_input_ref="raw:OCR_DEGRADED_001",
            source_file_ref="/tmp/test3.pdf",
            trace_id="TRC_OCR_DEGRADED_001",
            document_type="score_table",
            pages=(
                OCRPageResult(
                    page_number=1,
                    blocks=(
                        OCRTextBlock(
                            text="本周学习状态有所提升",
                            confidence=0.88,
                            page_number=1,
                        ),
                    ),
                ),
            ),
            overall_confidence=0.88,
            event_status="degraded",
            review_needed=False,
            extracted_text="本周学习状态有所提升",
        )

        # Convert to event payload (no knowledge hint)
        payload = ocr_result_to_event_payload(
            ocr_result=ocr_result,
            student_id="STU_001",
        )

        # Assemble event
        chapter_mapping = {"第一章 运动的描述": "PHY_PEP_G1_V1_CH_01"}
        knowledge_mapping = {"质点运动的规律": "PHY_PEP_G1_V1_KP_002"}

        event = assemble_from_dict(payload, chapter_mapping, knowledge_mapping)
        contract = event.to_contract()
        decision = contract.validate()

        output = {
            "scenario": "degraded",
            "ocr_confidence": ocr_result.overall_confidence,
            "event_type": event.event_type,
            "event_status": event.event_status,
            "contract_accepted": decision.accepted,
            "should_consume": decision.should_consume,
            "review_needed": decision.review_needed,
            "degraded": decision.degraded,
            "knowledge_refs": event.knowledge_refs,
        }

        # Verify degraded flow is accepted but without knowledge state
        success = (
            decision.accepted and
            decision.should_consume and
            decision.degraded and
            not decision.knowledge_state_allowed
        )

        if success:
            return True, "Degraded OCR event bridge passed", output
        else:
            return False, "Degraded OCR event bridge failed", output

    except Exception as e:
        return False, f"Degraded error: {e}", {}


def test_ocr_event_bridge_degraded() -> None:
    success, message, _ = run_ocr_event_bridge_degraded()
    assert success, message


def run_baidu_ocr_end_to_end_with_mock() -> tuple[bool, str, dict]:
    """Test baidu OCR end-to-end flow with mocked HTTP calls."""
    try:
        import tempfile
        from pathlib import Path

        # Create a fake image file
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
            f.write(b"fake-png-image-data")
            image_path = f.name

        try:
            # Mock HTTP responses for baidu OCR
            responses = [
                {"access_token": "mocked-access-token"},
                {
                    "words_result": [
                        {"words": "质点运动的规律", "probability": {"average": 0.92}},
                        {"words": "习题练习", "probability": {"average": 0.88}},
                    ]
                },
            ]

            def mock_http_post(url: str, body: bytes, headers: dict[str, str]) -> dict[str, object]:
                return responses.pop(0)

            # Build baidu runner with mocked HTTP
            runner = build_baidu_runner(
                BaiduOCRConfig(api_key="test-key", secret_key="test-secret"),
                http_post=mock_http_post,
            )

            # Build OCR request
            request = OCRRequest(
                provider="baidu",
                raw_input_ref="raw:OCR_E2E_TEST_001",
                source_file_ref=image_path,
                trace_id="TRC_OCR_E2E_001",
                document_type_hint="homework_sheet",
            )

            # Execute OCR
            ocr_result = runner(request)

            # Verify OCR result
            assert ocr_result.provider == "baidu"
            assert ocr_result.event_status == "success"
            assert ocr_result.review_needed is False
            assert "质点运动的规律" in ocr_result.extracted_text
            assert ocr_result.overall_confidence > 0.8

            # Convert to event payload
            from app.models.ocr_event_bridge import ocr_result_to_event_payload, assemble_ocr_event

            payload = ocr_result_to_event_payload(
                ocr_result=ocr_result,
                student_id="STU_001",
                chapter_hint="第一章 运动的描述",
                knowledge_hint="质点运动的规律",
            )

            # Assemble event
            chapter_mapping = {"第一章 运动的描述": "PHY_PEP_G1_V1_CH_01"}
            knowledge_mapping = {"质点运动的规律": "PHY_PEP_G1_V1_KP_002"}

            event = assemble_from_dict(payload, chapter_mapping, knowledge_mapping)
            contract = event.to_contract()
            decision = contract.validate()

            # Verify end-to-end flow
            success = (
                decision.accepted and
                decision.should_consume and
                not decision.review_needed and
                len(event.knowledge_refs) > 0
            )

            output = {
                "scenario": "baidu_e2e",
                "ocr_provider": ocr_result.provider,
                "ocr_confidence": ocr_result.overall_confidence,
                "extracted_text": ocr_result.extracted_text,
                "event_type": event.event_type,
                "event_status": event.event_status,
                "contract_accepted": decision.accepted,
                "should_consume": decision.should_consume,
                "review_needed": decision.review_needed,
                "knowledge_refs": event.knowledge_refs,
            }

            if success:
                return True, "Baidu OCR end-to-end test passed", output
            else:
                return False, "Baidu OCR end-to-end test failed", output

        finally:
            os.unlink(image_path)

    except Exception as e:
        return False, f"Baidu OCR end-to-end error: {e}", {}


def test_baidu_ocr_end_to_end_with_mock() -> None:
    success, message, _ = run_baidu_ocr_end_to_end_with_mock()
    assert success, message


def run_baidu_ocr_low_confidence_end_to_end() -> tuple[bool, str, dict]:
    """Test baidu OCR low confidence flow routes to review."""
    try:
        import tempfile

        # Create a fake image file
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
            f.write(b"fake-png-image-data")
            image_path = f.name

        try:
            # Mock HTTP responses for baidu OCR with low confidence
            responses = [
                {"access_token": "mocked-access-token"},
                {
                    "words_result": [
                        {"words": "模糊文本", "probability": {"average": 0.45}},
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

            # Build OCR request
            request = OCRRequest(
                provider="baidu",
                raw_input_ref="raw:OCR_LOW_E2E_001",
                source_file_ref=image_path,
                trace_id="TRC_OCR_LOW_E2E_001",
                document_type_hint="homework_sheet",
            )

            # Execute OCR
            ocr_result = runner(request)

            # Verify low confidence triggers review
            assert ocr_result.review_needed is True
            assert "low_confidence" in ocr_result.review_reasons
            assert ocr_result.event_status == "review_needed"

            # Convert to event and validate
            from app.models.ocr_event_bridge import ocr_result_to_event_payload

            payload = ocr_result_to_event_payload(
                ocr_result=ocr_result,
                student_id="STU_001",
                chapter_hint="第一章 运动的描述",
                knowledge_hint="质点运动的规律",
            )

            event = assemble_from_dict(payload, {"第一章 运动的描述": "PHY_PEP_G1_V1_CH_01"}, {"质点运动的规律": "PHY_PEP_G1_V1_KP_002"})
            contract = event.to_contract()
            decision = contract.validate()

            # Verify low confidence routes to review
            success = (
                not decision.accepted and
                not decision.should_consume and
                decision.review_needed
            )

            output = {
                "scenario": "baidu_low_confidence_e2e",
                "ocr_confidence": ocr_result.overall_confidence,
                "contract_accepted": decision.accepted,
                "should_consume": decision.should_consume,
                "review_needed": decision.review_needed,
            }

            if success:
                return True, "Baidu OCR low confidence e2e test passed (correctly routed to review)", output
            else:
                return False, "Baidu OCR low confidence e2e test failed", output

        finally:
            os.unlink(image_path)

    except Exception as e:
        return False, f"Baidu OCR low confidence e2e error: {e}", {}


def test_baidu_ocr_low_confidence_end_to_end() -> None:
    success, message, _ = run_baidu_ocr_low_confidence_end_to_end()
    assert success, message


def run_all_tests() -> dict:
    """Run all OCR event bridge tests."""
    tests = [
        ("bridge_high_conf", run_ocr_event_bridge_high_confidence),
        ("bridge_low_conf", run_ocr_event_bridge_low_confidence),
        ("bridge_degraded", run_ocr_event_bridge_degraded),
        ("baidu_e2e", run_baidu_ocr_end_to_end_with_mock),
        ("baidu_low_conf_e2e", run_baidu_ocr_low_confidence_end_to_end),
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
