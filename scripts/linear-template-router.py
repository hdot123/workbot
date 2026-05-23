#!/usr/bin/env python3
"""Linear Issue Template Router - Routes issues to tpl:* labels based on content.

Priority order:
  Rule 0: tpl:* by title prefix (exact match, highest priority)
  Rule 1: tpl:push-gate
  Rule 2: tpl:ci
  Rule 3: tpl:dev
  Rule 4: tpl:general    (fallback)

Design notes:
  - Rule 0 provides deterministic routing based on title prefix conventions.
  - Rules 1-3 use keyword matching with minimum signal thresholds to avoid
    false positives from template skeleton field names.
  - Table field names in markdown (e.g., "| GitHub Push | ... |") are weak
    signals. Rules require multiple strong signals or a title-level match.
  - The router intentionally ignores placeholder/template field rows when
    they appear in markdown table format (lines starting with |).
"""

import json
import re
import sys
from typing import Any


def _in_text(kw: str, title: str, description: str) -> bool:
    return kw.lower() in (title or "").lower() or kw.lower() in (description or "").lower()


def _in_desc(kw: str, description: str) -> bool:
    return kw.lower() in (description or "").lower()


def _in_title(kw: str, title: str) -> bool:
    return kw.lower() in (title or "").lower()


def _strip_markdown_tables(text: str) -> str:
    """Remove markdown table rows to avoid matching field-name artifacts."""
    return re.sub(r'^\|.*\|$', '', text, flags=re.MULTILINE)


def _body_text(description: str) -> str:
    """Get description with markdown tables stripped, for rule evaluation."""
    return _strip_markdown_tables(description or "")


def classify_issue(title: str, description: str, labels: list[str] | None = None) -> dict[str, Any]:
    desc = description or ""
    title_text = title or ""
    desc_lower = desc.lower()
    label_names = [l.lower() for l in (labels or [])]
    body = _body_text(desc)
    body_lower = body.lower()

    # === Rule 0: Title prefix exact match (deterministic) ===
    t = title_text.lower()
    if "push-gate" in t or "pushgate" in t:
        return {"issue_title": title_text, "rule_matched": "Rule 0", "label": "tpl:push-gate", "confidence": "high", "keywords_matched": ["title_prefix:push-gate"]}
    if t.startswith("test-t3") or "ci pipeline" in t or "pipeline 验收" in t:
        return {"issue_title": title_text, "rule_matched": "Rule 0", "label": "tpl:ci", "confidence": "high", "keywords_matched": ["title_prefix:ci"]}
    if t.startswith("test-t2") or any(k in t for k in ["feat(", "fix(", "refactor("]) or "开发任务" in t:
        return {"issue_title": title_text, "rule_matched": "Rule 0", "label": "tpl:dev", "confidence": "high", "keywords_matched": ["title_prefix:dev"]}

    # === Rule 1: tpl:push-gate ===
    # Require at least 2 strong signals from body (excluding table rows)
    pg_signals = 0
    pg_kw = []
    for kw in ["唯一允许路径", "唯一路径"]:
        if kw in body:
            pg_signals += 1; pg_kw.append(kw)
    if "push result" in body_lower:
        pg_signals += 1; pg_kw.append("push result (body)")
    if "禁止推送" in body or "禁止直接推送 github" in body_lower:
        pg_signals += 1; pg_kw.append("禁止推送 (body)")
    if "pipeline_status" in body_lower and "github" in body_lower:
        pg_signals += 1; pg_kw.append("pipeline_status+GitHub (body)")
    if "push gate" in title_text.lower():
        pg_signals += 2; pg_kw.append("push gate (title)")
    if "github" in title_text.lower() and ("sync" in title_text.lower() or "发布" in title_text or "同步" in title_text):
        pg_signals += 2; pg_kw.append("GitHub+sync/发布/同步 (title)")
    if any("type: gate" in l for l in label_names):
        pg_signals += 1; pg_kw.append("label:Type:Gate")
    # "GitHub push" in title is strong signal
    if "github push" in title_text.lower():
        pg_signals += 2; pg_kw.append("GitHub push (title)")

    if pg_signals >= 2:
        return {"issue_title": title_text, "rule_matched": "Rule 1", "label": "tpl:push-gate", "confidence": "high" if pg_signals >= 3 else "medium", "keywords_matched": pg_kw}

    # === Rule 2: tpl:ci ===
    ci_signals = 0
    ci_kw = []
    # "Pipeline 验收" in title
    if "pipeline" in title_text.lower() and "验收" in title_text:
        ci_signals += 2; ci_kw.append("Pipeline 验收 (title)")
    # CI or Pipeline in title
    if re.search(r'\bci\b', title_text, re.IGNORECASE):
        ci_signals += 1; ci_kw.append("CI (title)")
    if "pipeline" in title_text.lower():
        ci_signals += 1; ci_kw.append("Pipeline (title)")
    # pipeline failed/success in body (not table rows)
    for kw in ["pipeline failed", "pipeline success", "pipeline_status = success"]:
        if kw in body_lower:
            ci_signals += 1; ci_kw.append(f"{kw} (body)")
    # Job 清单 in body
    if "job 清单" in body:
        ci_signals += 1; ci_kw.append("Job 清单 (body)")
    # pipeline + 验收 in body
    if "pipeline" in body_lower and "验收" in body:
        ci_signals += 1; ci_kw.append("pipeline+验收 (body)")

    if ci_signals >= 2:
        return {"issue_title": title_text, "rule_matched": "Rule 2", "label": "tpl:ci", "confidence": "high" if ci_signals >= 3 else "medium", "keywords_matched": ci_kw}

    # === Rule 3: tpl:dev ===
    dev_signals = 0
    dev_kw = []
    # commit conventions in title
    for kw in ["feat(", "fix(", "refactor("]:
        if kw in title_text.lower():
            dev_signals += 2; dev_kw.append(f"title:{kw}")
    if "开发" in title_text:
        dev_signals += 1; dev_kw.append("开发 (title)")
    # branch-2 + GitLab CI in body
    if "branch-2" in body and "gitlab ci" in body_lower:
        dev_signals += 1; dev_kw.append("branch-2+GitLab CI (body)")
    # 变更范围 in body
    if "变更范围" in body:
        dev_signals += 1; dev_kw.append("变更范围 (body)")
    # 验收标准（硬性 in body
    if "验收标准（硬性" in body:
        dev_signals += 1; dev_kw.append("验收标准（硬性 (body)")
    # 回滚策略 in body
    if "回滚策略" in body:
        dev_signals += 1; dev_kw.append("回滚策略 (body)")

    if dev_signals >= 2:
        return {"issue_title": title_text, "rule_matched": "Rule 3", "label": "tpl:dev", "confidence": "high" if dev_signals >= 3 else "medium", "keywords_matched": dev_kw}

    # === Rule 4: tpl:general (fallback) ===
    return {"issue_title": title_text, "rule_matched": "Rule 4", "label": "tpl:general", "confidence": "low", "keywords_matched": []}


def dry_run(issues: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Run classification on a list of issues and return results."""
    results = []
    for issue in issues:
        title = issue.get("title", "")
        description = issue.get("description", "")
        labels = [l.get("name", "") for l in issue.get("labels", {}).get("nodes", [])]
        result = classify_issue(title, description, labels)
        result["issue_id"] = issue.get("id", "")
        results.append(result)
    return results


def main():
    """Main entry point. Accepts JSON from stdin or command line args."""
    if len(sys.argv) > 1 and sys.argv[1] == "--help":
        print("Usage:")
        print('  echo \'{"title": "...", "description": "..."}\' | python3 linear-template-router.py')
        print("  python3 linear-template-router.py < issues.json")
        print('  python3 linear-template-router.py "title" "description"')
        sys.exit(0)

    # Mode 1: positional args (title, description)
    if len(sys.argv) >= 3:
        title = sys.argv[1]
        description = sys.argv[2] if len(sys.argv) > 2 else ""
        result = classify_issue(title, description)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return

    # Mode 2: stdin JSON
    try:
        stdin_data = sys.stdin.read().strip()
        if not stdin_data:
            print("Error: No input provided. Use --help for usage.", file=sys.stderr)
            sys.exit(1)

        data = json.loads(stdin_data)

        if isinstance(data, list):
            # Batch mode
            results = dry_run(data)
            print(json.dumps(results, indent=2, ensure_ascii=False))
        else:
            # Single issue mode
            labels = [l.get("name", "") for l in data.get("labels", {}).get("nodes", [])]
            result = classify_issue(
                data.get("title", ""),
                data.get("description", ""),
                labels,
            )
            print(json.dumps(result, indent=2, ensure_ascii=False))
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON input: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
