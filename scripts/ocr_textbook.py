#!/usr/bin/env python3
"""OCR textbook PDF using local glm-ocr model."""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.models.ocr_interface import (
    OCRDocumentResult,
    OCRPageResult,
    OCRRequest,
    OCRTextBlock,
    build_ocr_service_from_env,
)


def run_ocr_on_textbook(
    pdf_path: str,
    output_path: str,
    document_type: str = "textbook",
) -> dict:
    """Run OCR on a textbook PDF and save results."""

    if not os.path.exists(pdf_path):
        return {
            "success": False,
            "error": f"PDF not found: {pdf_path}",
            "timestamp": datetime.now().isoformat(),
        }

    try:
        # Set up OCR service with glm-ocr
        env = os.environ.copy()
        env["LOCAL_OCR_PROVIDER"] = "ollama"
        env["LOCAL_OCR_MODEL"] = "glm-ocr"

        ocr_service = build_ocr_service_from_env(env=env)

        # Create OCR request
        request = OCRRequest(
            provider="local",
            raw_input_ref=f"raw:textbook_{os.path.basename(pdf_path)}",
            source_file_ref=pdf_path,
            trace_id=f"TRC_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            document_type_hint=document_type,
        )

        print(f"Starting OCR for: {pdf_path}")
        print(f"Output will be saved to: {output_path}")

        # Execute OCR
        result = ocr_service.recognize(request)

        # Prepare output
        output_data = {
            "success": True,
            "timestamp": datetime.now().isoformat(),
            "request": {
                "provider": request.provider,
                "source_file_ref": request.source_file_ref,
                "trace_id": request.trace_id,
                "document_type_hint": request.document_type_hint,
            },
            "result": {
                "provider": result.provider,
                "document_type": result.document_type,
                "event_status": result.event_status,
                "review_needed": result.review_needed,
                "overall_confidence": result.overall_confidence,
                "extracted_text": result.extracted_text,
                "extracted_text_length": len(result.extracted_text),
                "page_count": len(result.pages),
                "warnings": list(result.warnings),
                "review_reasons": list(result.review_reasons),
                "pages": [
                    {
                        "page_number": page.page_number,
                        "blocks": [
                            {
                                "text": block.text,
                                "confidence": block.confidence,
                                "page_number": block.page_number,
                            }
                            for block in page.blocks
                        ],
                    }
                    for page in result.pages
                ],
            },
        }

        # Save to output file
        output_dir = os.path.dirname(output_path)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)

        print(f"OCR completed. Results saved to: {output_path}")
        print(f"Extracted text length: {len(result.extracted_text)}")
        print(f"Event status: {result.event_status}")
        print(f"Review needed: {result.review_needed}")
        if result.warnings:
            print(f"Warnings: {result.warnings}")

        return output_data

    except Exception as e:
        error_data = {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__,
            "timestamp": datetime.now().isoformat(),
            "pdf_path": pdf_path,
        }
        print(f"OCR failed: {e}")
        return error_data


def main():
    pdf_path = "/Users/busiji/workbot/AEdu/13_原始资料库/教材 PDF/高中物理/人教版高中教科书物理必修第一册课本.pdf"
    output_path = "/Users/busiji/workbot/AEdu/13_原始资料库/OCR 结果/高中物理/人教版高中教科书物理必修第一册_OCR.json"

    result = run_ocr_on_textbook(pdf_path, output_path)

    print("\n" + "=" * 60)
    print("OCR SUMMARY")
    print("=" * 60)
    print(f"Success: {result.get('success', False)}")
    if result.get('success'):
        print(f"Extracted text length: {result.get('result', {}).get('extracted_text_length', 0)}")
        print(f"Event status: {result.get('result', {}).get('event_status', 'unknown')}")
    else:
        print(f"Error: {result.get('error', 'unknown')}")


if __name__ == "__main__":
    main()
