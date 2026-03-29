#!/usr/bin/env python3
"""
百度 OCR 教材处理脚本
"""

import base64
import json
import os
import sys
import requests
from datetime import datetime
from pathlib import Path

import fitz


def get_baidu_token(api_key: str, secret_key: str) -> str:
    """获取百度 OCR access token."""
    token_url = 'https://aip.baidubce.com/oauth/2.0/token'
    params = {'grant_type': 'client_credentials', 'client_id': api_key, 'client_secret': secret_key}
    resp = requests.post(token_url, params=params)
    data = resp.json()
    if 'access_token' not in data:
        raise Exception(f"获取 token 失败：{data}")
    return data['access_token']


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


def baidu_ocr_image(image_base64: str, access_token: str, timeout: int = 60) -> dict:
    """使用百度 OCR 识别单张图片."""
    url = f"https://aip.baidubce.com/rest/2.0/ocr/v1/accurate_basic?access_token={access_token}"
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    data = {'image': image_base64, 'probability': 'true'}

    resp = requests.post(url, headers=headers, data=data, timeout=timeout)
    result = resp.json()

    if 'error_code' in result:
        raise Exception(f"百度 OCR 错误：{result.get('error_code')} - {result.get('error_msg')}")

    return result


def ocr_textbook_baidu(pdf_path: str, output_dir: str, api_key: str, secret_key: str, start_page: int = 1, end_page: int = None):
    """使用百度 OCR 处理整本教材."""
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
    print(f"OCR 提供商：百度 OCR")
    print()

    # 获取 token
    print("正在获取百度 OCR token...")
    access_token = get_baidu_token(api_key, secret_key)
    print("Token 获取成功")
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
        "provider": "baidu",
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

            # 执行百度 OCR
            ocr_result = baidu_ocr_image(img_base64, access_token, timeout=120)

            # 提取文字
            words_result = ocr_result.get("words_result", [])
            text = "\n".join([item.get("words", "") for item in words_result])

            # 提取置信度
            avg_confidence = 0.0
            if words_result:
                confidences = []
                for item in words_result:
                    prob = item.get("probability", {})
                    if prob and "average" in prob:
                        confidences.append(prob["average"])
                if confidences:
                    avg_confidence = sum(confidences) / len(confidences)

            if text:
                print(f"识别到 {len(text)} 字 (置信度：{avg_confidence:.2f})")
                results["processed_pages"].append({
                    "page_number": page_num,
                    "text": text,
                    "char_count": len(text),
                    "confidence": avg_confidence,
                    "status": "success",
                })
            else:
                print("无文字内容")
                results["processed_pages"].append({
                    "page_number": page_num,
                    "text": "",
                    "char_count": 0,
                    "confidence": 0.0,
                    "status": "empty",
                })
                results["warnings"].append(f"page_{page_num}_empty")

        except Exception as e:
            print(f"失败：{e}")
            results["processed_pages"].append({
                "page_number": page_num,
                "text": "",
                "char_count": 0,
                "confidence": 0.0,
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
    output_file = output_dir / f"{pdf_path.stem}_baidu_ocr_result.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    # 保存纯文本版本
    text_file = output_dir / f"{pdf_path.stem}_baidu_ocr_text.txt"
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

    parser = argparse.ArgumentParser(description="百度 OCR 教材处理脚本")
    parser.add_argument("pdf_path", help="PDF 文件路径")
    parser.add_argument("--output-dir", default="/Users/busiji/workbot/AEdu/13_原始资料库/OCR 结果/高中物理", help="输出目录")
    parser.add_argument("--start-page", type=int, default=1, help="起始页码")
    parser.add_argument("--end-page", type=int, help="结束页码")
    parser.add_argument("--api-key", default=os.environ.get("BAIDU_OCR_API_KEY"), help="百度 API Key")
    parser.add_argument("--secret-key", default=os.environ.get("BAIDU_OCR_SECRET_KEY"), help="百度 Secret Key")

    args = parser.parse_args()

    if not args.api_key or not args.secret_key:
        print("错误：需要提供百度 API Key 和 Secret Key")
        print("可以通过 --api-key 和 --secret-key 参数提供，或设置环境变量 BAIDU_OCR_API_KEY 和 BAIDU_OCR_SECRET_KEY")
        sys.exit(1)

    ocr_textbook_baidu(
        args.pdf_path,
        args.output_dir,
        args.api_key,
        args.secret_key,
        args.start_page,
        args.end_page,
    )
