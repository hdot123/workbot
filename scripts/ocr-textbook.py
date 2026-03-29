#!/usr/bin/env python3
"""
OCR 教材处理脚本 - 使用 ollama glm-ocr 模型
"""

import base64
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen

import fitz


def pdf_to_images_base64(pdf_path: str, start_page: int = 1, end_page: int = None, max_pages: int = None) -> list[tuple[int, str]]:
    """Convert PDF pages to base64-encoded images."""
    doc = fitz.open(pdf_path)
    total_pages = len(doc)

    if end_page is None:
        end_page = total_pages
    if max_pages:
        end_page = min(end_page, start_page + max_pages - 1)

    images = []
    for page_num in range(start_page - 1, min(end_page, total_pages)):
        page = doc[page_num]
        mat = fitz.Matrix(2, 2)
        pix = page.get_pixmap(matrix=mat)
        img_bytes = pix.tobytes("png")
        img_base64 = base64.b64encode(img_bytes).decode("ascii")
        images.append((page_num + 1, img_base64))

    doc.close()
    return images


def run_ollama_ocr(base64_image: str, model: str = "glm-ocr", timeout: int = 180) -> str:
    """Run OCR on a base64-encoded image using ollama."""
    prompt = "请识别这张图片中的所有文字内容，按原样输出，不要添加任何解释或评论。"

    payload = {
        "model": model,
        "prompt": prompt,
        "images": [base64_image],
        "stream": False,
    }

    ollama_url = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
    if not ollama_url.startswith("http"):
        ollama_url = f"http://{ollama_url}:11434"

    endpoint = f"{ollama_url}/api/generate"
    data = json.dumps(payload).encode("utf-8")

    request = Request(endpoint, data=data, headers={"Content-Type": "application/json"}, method="POST")

    with urlopen(request, timeout=timeout) as response:
        result = json.loads(response.read().decode("utf-8"))
        return result.get("response", "").strip()


def ocr_textbook(pdf_path: str, output_dir: str, start_page: int = 1, end_page: int = None, model: str = "glm-ocr"):
    """OCR 处理整本教材."""
    pdf_path = Path(pdf_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # 获取 PDF 信息
    doc = fitz.open(pdf_path)
    total_pages = len(doc)

    if end_page is None:
        end_page = total_pages
    end_page = min(end_page, total_pages)

    print(f"PDF 文件：{pdf_path}")
    print(f"总页数：{total_pages}")
    print(f"处理范围：第 {start_page} 页 - 第 {end_page} 页")
    print(f"使用模型：{model}")
    print()

    # 结果存储
    results = {
        "source_file": str(pdf_path),
        "total_pages": total_pages,
        "processed_pages": [],
        "start_time": datetime.now().isoformat(),
        "end_time": None,
        "status": "processing",
        "warnings": [],
    }

    # 逐页处理
    for page_num in range(start_page, end_page + 1):
        print(f"处理第 {page_num} 页...", end=" ")
        sys.stdout.flush()

        try:
            # 转换单页为图片
            page = doc[page_num - 1]
            mat = fitz.Matrix(2, 2)
            pix = page.get_pixmap(matrix=mat)
            img_bytes = pix.tobytes("png")
            img_base64 = base64.b64encode(img_bytes).decode("ascii")

            # 执行 OCR
            text = run_ollama_ocr(img_base64, model, timeout=180)

            if text:
                print(f"识别到 {len(text)} 字")
                results["processed_pages"].append({
                    "page_number": page_num,
                    "text": text,
                    "char_count": len(text),
                    "status": "success",
                })
            else:
                print("无文字内容")
                results["processed_pages"].append({
                    "page_number": page_num,
                    "text": "",
                    "char_count": 0,
                    "status": "empty",
                })
                results["warnings"].append(f"page_{page_num}_empty")

        except Exception as e:
            print(f"失败：{e}")
            results["processed_pages"].append({
                "page_number": page_num,
                "text": "",
                "char_count": 0,
                "status": "error",
                "error": str(e),
            })
            results["warnings"].append(f"page_{page_num}_error:{str(e)[:50]}")

    doc.close()

    # 完成
    results["end_time"] = datetime.now().isoformat()
    results["status"] = "completed"
    results["total_processed"] = len([p for p in results["processed_pages"] if p["status"] == "success"])
    results["total_empty"] = len([p for p in results["processed_pages"] if p["status"] == "empty"])
    results["total_errors"] = len([p for p in results["processed_pages"] if p["status"] == "error"])

    # 保存结果
    output_file = output_dir / f"{pdf_path.stem}_ocr_result.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    # 保存纯文本版本
    text_file = output_dir / f"{pdf_path.stem}_ocr_text.txt"
    with open(text_file, "w", encoding="utf-8") as f:
        for page_result in results["processed_pages"]:
            if page_result["text"]:
                f.write(f"=== 第 {page_result['page_number']} 页 ===\n")
                f.write(page_result["text"])
                f.write("\n\n")

    print()
    print(f"处理完成!")
    print(f"成功：{results['total_processed']} 页")
    print(f"空白：{results['total_empty']} 页")
    print(f"失败：{results['total_errors']} 页")
    print(f"结果文件：{output_file}")
    print(f"文本文件：{text_file}")

    return results


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="OCR 教材处理脚本")
    parser.add_argument("pdf_path", help="PDF 文件路径")
    parser.add_argument("--output-dir", default="/Users/busiji/workbot/AEdu/13_原始资料库/OCR 结果/高中物理", help="输出目录")
    parser.add_argument("--start-page", type=int, default=1, help="起始页码")
    parser.add_argument("--end-page", type=int, help="结束页码")
    parser.add_argument("--model", default="glm-ocr", help="OCR 模型")

    args = parser.parse_args()

    ocr_textbook(
        args.pdf_path,
        args.output_dir,
        args.start_page,
        args.end_page,
        args.model,
    )
