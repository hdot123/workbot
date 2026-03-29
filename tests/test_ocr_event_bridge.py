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
    build_local_provider,
    build_ocr_service_from_env,
)
from app.models.twin_ingest_contract import TwinIngestContract


def test_ocr_event_bridge_high_confidence() -> tuple[bool, str, dict]:
    """Test OCR event bridge with high confidence result."""
    try:
        # Simulate high confidence OCR result
        ocr_result = OCRDocumentResult(
            provider="local",
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


def test_ocr_event_bridge_low_confidence() -> tuple[bool, str, dict]:
    """Test OCR event bridge with low confidence result (should route to review)."""
    try:
        # Simulate low confidence OCR result
        ocr_result = OCRDocumentResult(
            provider="local",
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


def test_ocr_event_bridge_degraded() -> tuple[bool, str, dict]:
    """Test OCR event bridge with degraded result (no knowledge refs)."""
    try:
        # Simulate degraded OCR result (no specific knowledge identified)
        ocr_result = OCRDocumentResult(
            provider="local",
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


def test_local_ocr_with_pdf() -> tuple[bool, str, dict]:
    """Test local OCR with actual PDF file from AEdu materials."""
    try:
        # Check if PDF exists
        pdf_path = "/Users/busiji/workbot/AEdu/13_原始资料库/教材 PDF/高中物理/人教版高中教科书物理必修第一册课本.pdf"

        if not os.path.exists(pdf_path):
            return False, f"PDF not found: {pdf_path}", {}

        # Set up OCR service
        env = os.environ.copy()
        env["LOCAL_OCR_PROVIDER"] = "ollama"
        env["LOCAL_OCR_MODEL"] = "glm-ocr"

        ocr_service = build_ocr_service_from_env(env=env)

        # Create OCR request for PDF
        request = OCRRequest(
            provider="local",
            raw_input_ref="raw:OCR_PDF_TEST_001",
            source_file_ref=pdf_path,
            trace_id="TRC_OCR_PDF_001",
            document_type_hint="textbook",
        )

        # Execute OCR
        result = ocr_service.recognize(request)

        output = {
            "provider": result.provider,
            "document_type": result.document_type,
            "event_status": result.event_status,
            "review_needed": result.review_needed,
            "overall_confidence": result.overall_confidence,
            "extracted_text_preview": result.extracted_text[:100] if result.extracted_text else None,
            "warnings": list(result.warnings),
            "review_reasons": list(result.review_reasons),
        }

        return True, "Local OCR with PDF passed", output

    except Exception as e:
        return False, f"Local OCR PDF error: {e}", {}


def run_all_tests() -> dict:
    """Run all OCR event bridge tests."""
    tests = [
        ("bridge_high_conf", test_ocr_event_bridge_high_confidence),
        ("bridge_low_conf", test_ocr_event_bridge_low_confidence),
        ("bridge_degraded", test_ocr_event_bridge_degraded),
        ("local_ocr_pdf", test_local_ocr_with_pdf),
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
