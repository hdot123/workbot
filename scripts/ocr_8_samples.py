#!/usr/bin/env python3
"""OCR 8 sample textbook page images and analyze structure."""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.models.ocr_interface import (
    OCRRequest,
    build_ocr_service_from_env,
)


SAMPLE_PAGES = [
    ("01_封面", "封面页"),
    ("02_版权页", "版权信息页"),
    ("03_目录", "目录页"),
    ("04_序言", "序言/前言页"),
    ("05_第一章开头", "章节起始页"),
    ("06_正文概念", "正文（概念讲解）"),
    ("07_正文公式", "正文（公式推导）"),
    ("08_习题页", "练习/习题页"),
]


def analyze_page(text: str, page_name: str) -> dict[str, Any]:
    """Analyze OCR text for structure information."""
    result = {
        "page_name": page_name,
        "book_title": None,
        "page_number": None,
        "page_type": None,
        "main_title": None,
        "subtitles": [],
        "figure_captions": [],
        "exercise_sections": [],
        "raw_text_preview": text[:500] if text else None,
    }

    if not text:
        return result

    lines = text.strip().split("\n")

    # Detect book title
    title_keywords = ["普通高中教科书", "物理", "必修", "第一册", "人教版"]
    for line in lines[:20]:
        if any(kw in line for kw in title_keywords[:3]):
            if "普通高中教科书" in line:
                result["book_title"] = line.strip()
            elif "物理" in line and "必修" in line:
                result["book_title"] = line.strip()

    # Detect page number
    import re
    for line in lines:
        # Look for page numbers like "1", "2", etc. or "第 X 页"
        match = re.search(r"(\d+)\s*$", line.strip())
        if match and len(line.strip()) < 10:
            result["page_number"] = match.group(1)
            break

    # Detect page type
    if "目录" in text[:100]:
        result["page_type"] = "目录页"
    elif "序言" in text[:100] or "同学们好" in text:
        result["page_type"] = "序言页"
    elif "第一章" in text[:200]:
        result["page_type"] = "章节起始页"
    elif "练习与应用" in text or "复习与提高" in text:
        result["page_type"] = "习题页"
    elif "图" in text and "所示" in text:
        result["page_type"] = "正文（含图）"
    else:
        result["page_type"] = "正文页"

    # Detect main title (chapter/section title)
    for line in lines[:10]:
        if len(line.strip()) > 2 and len(line.strip()) < 50:
            if any(kw in line for kw in ["第一章", "第二章", "第三章", "第四章", "序言", "致同学们"]):
                result["main_title"] = line.strip()
                break

    # Detect subtitles
    for line in lines:
        line = line.strip()
        if len(line) > 2 and len(line) < 30:
            if any(kw in line for kw in ["问题", "实验", "思考与讨论", "科学方法", "练习与应用"]):
                if line not in result["subtitles"]:
                    result["subtitles"].append(line)

    # Detect figure captions (图 X-X-X)
    for line in lines:
        if "图" in line and ("所示" in line or ")" in line or "：" in line):
            if len(line) < 100:
                result["figure_captions"].append(line.strip())

    # Detect exercise sections
    if "练习与应用" in text:
        result["exercise_sections"].append("练习与应用")
    if "复习与提高" in text:
        result["exercise_sections"].append("复习与提高")
    if "A 组" in text:
        result["exercise_sections"].append("A 组")
    if "B 组" in text:
        result["exercise_sections"].append("B 组")

    return result


def run_sample_ocr_test(
    sample_dir: str,
    output_path: str,
) -> dict:
    """Run OCR on 8 sample pages and analyze structure."""

    # Set up OCR service
    ocr_service = build_ocr_service_from_env(env=os.environ.copy())

    results = {
        "test_name": "高中物理必修第一册_8 张样本截图识别测试",
        "timestamp": datetime.now().isoformat(),
        "sample_count": len(SAMPLE_PAGES),
        "pages": [],
        "summary": {
            "book_title_detected": False,
            "page_numbers_detected": 0,
            "page_types_detected": set(),
            "main_titles_detected": 0,
            "structure_info_detected": 0,
        },
    }

    print("=" * 60)
    print("8 张教材截图样本识别测试")
    print("=" * 60)

    for page_file, page_type in SAMPLE_PAGES:
        image_path = os.path.join(sample_dir, f"{page_file}.png")

        if not os.path.exists(image_path):
            print(f"\n[跳过] 文件不存在：{image_path}")
            results["pages"].append({
                "page_name": page_file,
                "page_type_hint": page_type,
                "status": "文件不存在",
            })
            continue

        print(f"\n[处理] {page_file} ({page_type})")

        try:
            # Create OCR request for image
            request = OCRRequest(
                provider="baidu",
                raw_input_ref=f"raw:sample_{page_file}",
                source_file_ref=image_path,
                trace_id=f"TRC_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{page_file}",
                document_type_hint="textbook",
            )

            # Execute OCR
            result = ocr_service.recognize(request)

            # Analyze structure
            analysis = analyze_page(result.extracted_text, page_file)
            analysis["page_type_hint"] = page_type
            analysis["status"] = "success" if result.extracted_text else "empty_text"
            analysis["ocr_confidence"] = result.overall_confidence
            analysis["extracted_text_length"] = len(result.extracted_text)

            results["pages"].append(analysis)

            # Update summary
            if analysis["book_title"]:
                results["summary"]["book_title_detected"] = True
            if analysis["page_number"]:
                results["summary"]["page_numbers_detected"] += 1
            if analysis["page_type"]:
                results["summary"]["page_types_detected"].add(analysis["page_type"])
            if analysis["main_title"]:
                results["summary"]["main_titles_detected"] += 1
            if analysis["subtitles"] or analysis["figure_captions"] or analysis["exercise_sections"]:
                results["summary"]["structure_info_detected"] += 1

            print(f"  状态：{analysis['status']}")
            print(f"  文本长度：{analysis['extracted_text_length']}")
            print(f"  置信度：{analysis['ocr_confidence']}")
            print(f"  页面类型：{analysis['page_type']}")
            if analysis["main_title"]:
                print(f"  主标题：{analysis['main_title']}")

        except Exception as e:
            print(f"  [失败] {e}")
            results["pages"].append({
                "page_name": page_file,
                "page_type_hint": page_type,
                "status": "failed",
                "error": str(e),
            })

    # Convert set to list for JSON serialization
    results["summary"]["page_types_detected"] = list(results["summary"]["page_types_detected"])

    # Save results
    output_dir = os.path.dirname(output_path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"\n结果已保存到：{output_path}")
    print("\n" + "=" * 60)
    print("测试汇总")
    print("=" * 60)
    print(f"样本总数：{results['sample_count']}")
    print(f"成功识别：{sum(1 for p in results['pages'] if p.get('status') == 'success')}")
    print(f"书名识别：{'是' if results['summary']['book_title_detected'] else '否'}")
    print(f"页码识别：{results['summary']['page_numbers_detected']}/{results['sample_count']}")
    print(f"主标题识别：{results['summary']['main_titles_detected']}/{results['sample_count']}")
    print(f"结构信息识别：{results['summary']['structure_info_detected']}/{results['sample_count']}")

    return results


def main():
    sample_dir = "/Users/busiji/workbot/AEdu/13_原始资料库/OCR/高中物理/样本截图"
    output_path = "/Users/busiji/workbot/AEdu/13_原始资料库/OCR 结果/高中物理/8 张样本截图识别结果.json"

    results = run_sample_ocr_test(sample_dir, output_path)
    return results


if __name__ == "__main__":
    main()
