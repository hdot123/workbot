"""OCR to event integration for converting OCR results to learning events."""

from __future__ import annotations

from typing import Any

from app.models.event_assembler import AssembledEvent, assemble_from_dict
from app.models.ocr_interface import OCRDocumentResult, OCRRequest, OCRService


def ocr_result_to_event_payload(
    ocr_result: OCRDocumentResult,
    student_id: str,
    input_time: str | None = None,
    chapter_hint: str | None = None,
    knowledge_hint: str | None = None,
) -> dict[str, Any]:
    """
    Convert OCR result to event assembler payload.

    Args:
        ocr_result: OCR recognition result
        student_id: Student ID
        input_time: Optional input time (defaults to OCR trace timestamp)
        chapter_hint: Optional chapter hint for mapping
        knowledge_hint: Optional knowledge hint for mapping

    Returns:
        Dictionary payload suitable for assemble_from_dict
    """
    # Determine source type based on document type
    source_type = "parent_text"  # Default fallback

    if ocr_result.document_type in {"homework_sheet", "exam_paper"}:
        # Homework/exam sheets typically come from teacher or scan
        source_type = "teacher_feedback_text"
    elif ocr_result.document_type == "teacher_feedback_sheet":
        source_type = "teacher_feedback_text"
    elif ocr_result.document_type in {"score_table", "student_profile_form"}:
        source_type = "teacher_feedback_text"

    # Use extracted text from OCR
    input_text = ocr_result.extracted_text

    # Determine event status based on OCR confidence
    # OCR results with low confidence should route to review
    if ocr_result.review_needed:
        event_status = "review_needed"
    elif ocr_result.event_status == "degraded":
        event_status = "degraded"
    else:
        event_status = "success"

    return {
        "student_id": student_id,
        "input_text": input_text,
        "input_time": input_time or ocr_result.trace_id,  # Use trace as time reference
        "source_type": source_type,
        "chapter_hint": chapter_hint,
        "knowledge_hint": knowledge_hint,
        "context_summary": f"OCR: {ocr_result.document_type}",
        "_ocr_metadata": {
            "provider": ocr_result.provider,
            "overall_confidence": ocr_result.overall_confidence,
            "event_status": ocr_result.event_status,
            "review_reasons": list(ocr_result.review_reasons),
            "warnings": list(ocr_result.warnings),
        },
        "_ocr_confidence": ocr_result.overall_confidence,  # Pass OCR confidence to event assembler
    }


def assemble_ocr_event(
    ocr_result: OCRDocumentResult,
    student_id: str,
    *,
    chapter_mapping: dict[str, str] | None = None,
    knowledge_mapping: dict[str, str] | None = None,
    chapter_hint: str | None = None,
    knowledge_hint: str | None = None,
) -> AssembledEvent:
    """
    Assemble OCR result into a learning event.

    This function:
    1. Converts OCR result to event payload
    2. Applies chapter/knowledge mappings
    3. Returns assembled event ready for TWIN ingest

    Args:
        ocr_result: OCR recognition result
        student_id: Student ID
        chapter_mapping: Optional chapter hint to ID mapping
        knowledge_mapping: Optional knowledge hint to ID mapping
        chapter_hint: Optional chapter hint
        knowledge_hint: Optional knowledge hint

    Returns:
        AssembledEvent ready for validation and TWIN ingest
    """
    payload = ocr_result_to_event_payload(
        ocr_result=ocr_result,
        student_id=student_id,
        chapter_hint=chapter_hint,
        knowledge_hint=knowledge_hint,
    )

    event = assemble_from_dict(
        payload,
        chapter_mapping=chapter_mapping,
        knowledge_mapping=knowledge_mapping,
    )

    return event


def process_ocr_request(
    ocr_service: OCRService,
    ocr_request: OCRRequest,
    student_id: str,
    *,
    chapter_mapping: dict[str, str] | None = None,
    knowledge_mapping: dict[str, str] | None = None,
    chapter_hint: str | None = None,
    knowledge_hint: str | None = None,
) -> tuple[AssembledEvent, dict[str, Any]]:
    """
    Process OCR request and return assembled event with metadata.

    This is the main entry point for OCR-to-event processing.

    Args:
        ocr_service: OCR service instance
        ocr_request: OCR request with file reference
        student_id: Student ID
        chapter_mapping: Optional chapter mapping
        knowledge_mapping: Optional knowledge mapping
        chapter_hint: Optional chapter hint
        knowledge_hint: Optional knowledge hint

    Returns:
        Tuple of (AssembledEvent, metadata_dict)
        metadata contains OCR results and routing decisions
    """
    # Step 1: Execute OCR
    ocr_result = ocr_service.recognize(ocr_request)

    # Step 2: Assemble event from OCR result
    event = assemble_ocr_event(
        ocr_result=ocr_result,
        student_id=student_id,
        chapter_mapping=chapter_mapping,
        knowledge_mapping=knowledge_mapping,
        chapter_hint=chapter_hint,
        knowledge_hint=knowledge_hint,
    )

    # Step 3: Collect metadata
    metadata = {
        "ocr_result": {
            "provider": ocr_result.provider,
            "overall_confidence": ocr_result.overall_confidence,
            "event_status": ocr_result.event_status,
            "review_needed": ocr_result.review_needed,
            "extracted_text_length": len(ocr_result.extracted_text),
            "page_count": len(ocr_result.pages),
            "warnings": list(ocr_result.warnings),
            "review_reasons": list(ocr_result.review_reasons),
        },
        "event": {
            "event_id": event.event_id,
            "event_type": event.event_type,
            "event_status": event.event_status,
            "confidence_score": event.confidence_score,
            "knowledge_refs": event.knowledge_refs,
            "chapter_refs": event.chapter_refs,
        },
    }

    return event, metadata
