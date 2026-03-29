#!/usr/bin/env python3
"""百炼大模型视觉理解测试 - 8 张教材截图样本识别。

使用百炼 API (qwen-vl 或 qwen2.5-vl) 进行视觉理解，
识别书名、页码、页面类型、A 组/B 组、图号/结构信息。
"""

from __future__ import annotations

import base64
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

# 百炼 API 配置
# 优先使用环境中的 BAILIAN_API_KEY，其次兼容 DASHSCOPE_API_KEY
BAILIAN_API_KEY = os.environ.get("BAILIAN_API_KEY") or os.environ.get("DASHSCOPE_API_KEY") or "sk-sp-fdf3de2a9f4a4bc4a00cd98052343a8d"
DASHSCOPE_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"

# 使用 qwen2.5-vl 进行视觉理解
VISION_MODEL = "qwen2.5-vl-72b-instruct"

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

VISION_PROMPT = """请仔细分析这张教材页面图片，提取以下信息：

1. **书名**：识别课本名称（如"普通高中教科书 物理 必修 第一册"）
2. **页码**：识别页面底部或角落的页码数字
3. **页面类型**：判断是封面、版权页、目录、序言、章节起始页、正文页、习题页中的哪一种
4. **主标题/小标题**：识别章节标题、小节标题
5. **图号/图注**：识别"图 X-X"形式的图号和图注文字
6. **习题结构**：识别是否有"练习与应用"、"复习与提高"、"A 组"、"B 组"等

请以 JSON 格式返回结果，格式如下：
{
    "book_title": "书名或 null",
    "page_number": "页码数字或 null",
    "page_type": "页面类型",
    "main_title": "主标题或 null",
    "subtitles": ["小标题列表"],
    "figure_captions": ["图注列表"],
    "exercise_sections": ["习题栏目列表"],
    "confidence": 0.0-1.0 置信度
}

如果某项信息不存在，请返回 null 或空列表。"""


def image_to_base64(image_path: str) -> str:
    """Convert image to base64 data URL."""
    with open(image_path, "rb") as f:
        image_data = base64.b64encode(f.read()).decode("utf-8")
    return f"data:image/png;base64,{image_data}"


def call_bailian_vision(image_path: str) -> dict[str, Any]:
    """Call Bailian API for vision understanding."""
    import urllib.request
    import ssl

    if not BAILIAN_API_KEY:
        raise RuntimeError("BAILIAN_API_KEY 未配置")

    # 直接传文件路径，让 API 服务端拉取
    # Build request payload for OpenAI-compatible API
    payload = {
        "model": VISION_MODEL,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": VISION_PROMPT},
                    {"type": "image_url", "image_url": {"url": image_path}},
                ],
            }
        ],
        "max_tokens": 1024,
        "temperature": 0.1,
    }

    # Create request
    req = urllib.request.Request(
        f"{DASHSCOPE_BASE_URL}/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {BAILIAN_API_KEY}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    # Ignore SSL certificate verification (for local testing)
    context = ssl.create_default_context()
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE

    try:
        with urllib.request.urlopen(req, context=context, timeout=120) as response:
            result = json.loads(response.read().decode("utf-8"))
            content = result["choices"][0]["message"]["content"]
            return {"success": True, "content": content, "raw_response": result}
    except Exception as e:
        return {"success": False, "error": str(e), "raw_response": None}


def parse_vision_result(content: str) -> dict[str, Any]:
    """Parse vision result JSON from model output."""
    # Try to extract JSON from the content
    import re

    # Look for JSON object in the response
    json_match = re.search(r"\{[^{}]*\}", content, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group())
        except json.JSONDecodeError:
            pass

    # Fallback: return raw content with parsed fields
    return {
        "raw_content": content,
        "parse_status": "json_not_found",
    }


def run_bailian_vision_test(sample_dir: str, output_path: str) -> dict:
    """Run Bailian vision test on 8 sample pages."""

    results = {
        "test_name": "百炼视觉理解 - 高中物理必修第一册 8 张样本截图测试",
        "timestamp": datetime.now().isoformat(),
        "model": VISION_MODEL,
        "api_provider": "百炼 (DashScope)",
        "sample_count": len(SAMPLE_PAGES),
        "pages": [],
        "summary": {
            "success_count": 0,
            "book_title_detected": 0,
            "page_number_detected": 0,
            "page_type_detected": 0,
            "main_title_detected": 0,
            "structure_info_detected": 0,
        },
    }

    if not BAILIAN_API_KEY:
        print("=" * 60)
        print("百炼视觉理解测试 - 前置检查")
        print("=" * 60)
        print(f"\n[警告] BAILIAN_API_KEY 未配置")
        print(f"请在环境变量中设置 BAILIAN_API_KEY 后重试")
        print(f"\n测试无法继续，返回空结果")

        results["error"] = "BAILIAN_API_KEY 未配置"
        results["summary"]["success_count"] = -1

        # Save results anyway
        output_dir = os.path.dirname(output_path)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)

        return results

    print("=" * 60)
    print("百炼视觉理解测试 - 8 张教材截图样本")
    print(f"模型：{VISION_MODEL}")
    print(f"API: 百炼 (DashScope)")
    print("=" * 60)

    for page_file, page_type_hint in SAMPLE_PAGES:
        image_path = os.path.join(sample_dir, f"{page_file}.png")

        if not os.path.exists(image_path):
            print(f"\n[跳过] 文件不存在：{image_path}")
            results["pages"].append({
                "page_name": page_file,
                "page_type_hint": page_type_hint,
                "status": "文件不存在",
            })
            continue

        print(f"\n[处理] {page_file} ({page_type_hint})")

        # Call Bailian Vision API
        api_result = call_bailian_vision(image_path)

        if api_result["success"]:
            parsed = parse_vision_result(api_result["content"])
            parsed["page_name"] = page_file
            parsed["page_type_hint"] = page_type_hint
            parsed["status"] = "success"
            parsed["vision_raw_preview"] = api_result["content"][:300]

            results["pages"].append(parsed)

            # Update summary
            if parsed.get("book_title"):
                results["summary"]["book_title_detected"] += 1
            if parsed.get("page_number"):
                results["summary"]["page_number_detected"] += 1
            if parsed.get("page_type"):
                results["summary"]["page_type_detected"] += 1
            if parsed.get("main_title"):
                results["summary"]["main_title_detected"] += 1
            if parsed.get("subtitles") or parsed.get("figure_captions") or parsed.get("exercise_sections"):
                results["summary"]["structure_info_detected"] += 1

            results["summary"]["success_count"] += 1

            print(f"  状态：✅ success")
            print(f"  书名：{parsed.get('book_title', '未识别')}")
            print(f"  页码：{parsed.get('page_number', '未识别')}")
            print(f"  页面类型：{parsed.get('page_type', '未识别')}")
            if parsed.get("main_title"):
                print(f"  主标题：{parsed.get('main_title')}")
        else:
            print(f"  [失败] {api_result['error']}")
            results["pages"].append({
                "page_name": page_file,
                "page_type_hint": page_type_hint,
                "status": "failed",
                "error": api_result["error"],
            })

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
    print(f"成功识别：{results['summary']['success_count']}/{results['sample_count']}")
    print(f"书名识别：{results['summary']['book_title_detected']}/{results['sample_count']}")
    print(f"页码识别：{results['summary']['page_number_detected']}/{results['sample_count']}")
    print(f"页面类型识别：{results['summary']['page_type_detected']}/{results['sample_count']}")
    print(f"主标题识别：{results['summary']['main_title_detected']}/{results['sample_count']}")
    print(f"结构信息识别：{results['summary']['structure_info_detected']}/{results['sample_count']}")

    return results


def main():
    sample_dir = "/Users/busiji/workbot/AEdu/13_原始资料库/OCR/高中物理/样本截图"
    output_path = "/Users/busiji/workbot/AEdu/13_原始资料库/OCR 结果/高中物理/百炼视觉理解_8 张样本测试结果.json"

    results = run_bailian_vision_test(sample_dir, output_path)
    return results


if __name__ == "__main__":
    main()
