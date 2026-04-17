#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from workspace.tools.validate_memory_system import validate_memory_system


ARTIFACT_DIR = REPO_ROOT / "workspace" / "artifacts" / "project-readiness"
LATEST_RECEIPT = ARTIFACT_DIR / "phase2-preflight-latest.json"
PROJECT_OWNER = "hdot123"
PROJECT_NUMBER = 8
PROJECT_URL = "https://github.com/users/hdot123/projects/8"
CURRENT_TASK_TITLE = "[Phase 2] P0-preflight Readiness gate and blocker repair"
REQUIRED_DONE_TITLES = (
    "[Phase 0] P10-core Dispatch gate contract",
    "[Phase 0] P12-core Commander semantics core",
    "[Phase 1] P1 Control packet schema",
    "[Phase 1] P2 Summary and sidecar split",
    "[Phase 1] P6 Migrate direct cmux consumers",
    "[Phase 1] P9 Main-thread token contract",
    "[Phase 1] P13 Artifact hygiene and read priority",
)
CURRENT_TASK_FILES = (
    REPO_ROOT / "docs" / "project-management" / "workbot-cmux-p0-preflight-readiness-gate-and-blocker-repair-2026-04-17.md",
    REPO_ROOT / "docs" / "project-management" / "workbot-cmux-p10-core-delivery-2026-04-17.md",
    REPO_ROOT / "tests" / "test_cmux_phase_readiness.py",
    REPO_ROOT / "workspace" / "INDEX.md",
    REPO_ROOT / "workspace" / "memory" / "docs" / "INDEX.md",
    REPO_ROOT / "workspace" / "memory" / "docs" / "记忆系统全景文档.md",
    REPO_ROOT / "workspace" / "memory" / "inbox.md",
    REPO_ROOT / "workspace" / "memory" / "kb" / "global" / "INDEX.md",
    REPO_ROOT / "workspace" / "memory" / "kb" / "global" / "workbot-memory-routing.md",
    REPO_ROOT / "workspace" / "memory" / "kb" / "global" / "workbot-memory-system.md",
    REPO_ROOT / "workspace" / "memory" / "kb" / "global" / "workbot-project-map-governance.md",
    REPO_ROOT / "workspace" / "memory" / "kb" / "projects" / "workbot.md",
    REPO_ROOT / "workspace" / "project-map" / "INDEX.md",
    REPO_ROOT / "workspace" / "project-map" / "ingestion-registry-map.md",
    REPO_ROOT / "workspace" / "project-map" / "legal-core-map.md",
    REPO_ROOT / "workspace" / "tools" / "cmux_phase_readiness.py",
    REPO_ROOT / "workspace" / "tools" / "validate_memory_system.py",
)
DELIVERY_DOCS = (
    REPO_ROOT / "docs" / "project-management" / "workbot-cmux-p10-core-delivery-2026-04-17.md",
    REPO_ROOT / "docs" / "project-management" / "workbot-cmux-p12-core-delivery-2026-04-17.md",
    REPO_ROOT / "docs" / "project-management" / "workbot-cmux-p1-control-packet-schema-2026-04-17.md",
    REPO_ROOT / "docs" / "project-management" / "workbot-cmux-p2-summary-sidecar-split-2026-04-17.md",
    REPO_ROOT / "docs" / "project-management" / "workbot-cmux-p6-consumer-migration-2026-04-17.md",
    REPO_ROOT / "docs" / "project-management" / "workbot-cmux-p9-main-thread-token-contract-2026-04-17.md",
    REPO_ROOT / "docs" / "project-management" / "workbot-cmux-p13-artifact-read-priority-2026-04-17.md",
)


@dataclass(frozen=True)
class CommandResult:
    code: int
    stdout: str
    stderr: str


def run_command(args: list[str]) -> CommandResult:
    proc = subprocess.run(args, text=True, capture_output=True, check=False)
    return CommandResult(code=proc.returncode, stdout=proc.stdout, stderr=proc.stderr)


def extract_absolute_paths(text: str) -> list[str]:
    found: list[str] = []
    for candidate in re.findall(r"(/Users/[^\s`\",;]+)", text):
        normalized = candidate.rstrip("`.);:")
        if normalized not in found:
            found.append(normalized)
    return found


def section_body(text: str, heading: str) -> str:
    lines = text.splitlines()
    start_idx: int | None = None
    for idx, line in enumerate(lines):
        if line.strip() == heading:
            start_idx = idx + 1
            break
    if start_idx is None:
        return ""
    collected: list[str] = []
    for line in lines[start_idx:]:
        if line.strip().startswith("## "):
            break
        collected.append(line)
    return "\n".join(collected)


def extract_delivery_anchor_paths(text: str) -> list[str]:
    relevant_sections = (
        "## Repo Artifact Added by This Delivery",
        "## Repo Artifacts Added or Updated by This Delivery",
    )
    found: list[str] = []
    for heading in relevant_sections:
        body = section_body(text, heading)
        for candidate in extract_absolute_paths(body):
            if candidate not in found:
                found.append(candidate)
    return found


def collect_delivery_doc_anchor_problems(doc_paths: tuple[Path, ...]) -> dict[str, list[str]]:
    problems: dict[str, list[str]] = {}
    for doc_path in doc_paths:
        if not doc_path.exists():
            problems[str(doc_path)] = [f"missing delivery doc: {doc_path}"]
            continue
        missing_refs = []
        for rendered in extract_delivery_anchor_paths(doc_path.read_text(encoding="utf-8")):
            if not Path(rendered).exists():
                missing_refs.append(rendered)
        if missing_refs:
            problems[str(doc_path)] = missing_refs
    return problems


def collect_project_status_map(raw_json: str) -> dict[str, str]:
    payload = json.loads(raw_json)
    items = payload.get("items", [])
    status_map: dict[str, str] = {}
    for item in items:
        title = str(item.get("title") or "").strip()
        status = str(item.get("status") or "").strip()
        if title:
            status_map[title] = status
    return status_map


def collect_project_status_problems(status_map: dict[str, str], required_titles: tuple[str, ...]) -> list[str]:
    problems = []
    for title in required_titles:
        current = status_map.get(title)
        if current != "Done":
            problems.append(f"{title} => {current or 'missing'}")
    return problems


def collect_git_status() -> dict[str, Any]:
    result = run_command(["git", "-C", str(REPO_ROOT), "status", "--short", "--branch"])
    lines = [line for line in result.stdout.splitlines() if line.strip()]
    return {
        "ok": result.code == 0,
        "lines": lines,
        "stderr": result.stderr.strip(),
    }


def collect_scope_git_status(paths: tuple[Path, ...]) -> dict[str, Any]:
    result = run_command(
        ["git", "-C", str(REPO_ROOT), "status", "--short", "--", *[str(path) for path in paths]]
    )
    lines = [line for line in result.stdout.splitlines() if line.strip()]
    return {
        "ok": result.code == 0,
        "lines": lines,
        "stderr": result.stderr.strip(),
    }


def build_readiness_receipt() -> dict[str, Any]:
    memory = validate_memory_system()
    doc_problems = collect_delivery_doc_anchor_problems(DELIVERY_DOCS)

    project_cmd = run_command(
        [
            "gh",
            "project",
            "item-list",
            str(PROJECT_NUMBER),
            "--owner",
            PROJECT_OWNER,
            "--limit",
            "100",
            "--format",
            "json",
        ]
    )
    project_status_map: dict[str, str] = {}
    project_problems: list[str] = []
    if project_cmd.code == 0:
        project_status_map = collect_project_status_map(project_cmd.stdout)
        project_problems = collect_project_status_problems(project_status_map, REQUIRED_DONE_TITLES)
    else:
        project_problems = [project_cmd.stderr.strip() or "gh project item-list failed"]

    git_status = collect_git_status()
    current_task_status = project_status_map.get(CURRENT_TASK_TITLE, "")
    current_task_git_status = collect_scope_git_status(CURRENT_TASK_FILES)

    implemented = (
        memory["status"] == "ok"
        and not memory["missing_paths"]
        and not memory["validation_errors"]
        and not doc_problems
    )
    entry_ready = implemented and not project_problems
    delivered = (
        current_task_status == "Done"
        and current_task_git_status["ok"]
        and not current_task_git_status["lines"]
    )
    ready = entry_ready and delivered

    receipt = {
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "project_url": PROJECT_URL,
        "implemented": implemented,
        "entry_ready": entry_ready,
        "delivered": delivered,
        "ready": ready,
        "memory_validation": memory,
        "delivery_doc_anchor_problems": doc_problems,
        "project_status": {
            "required_done_titles": list(REQUIRED_DONE_TITLES),
            "current_task_title": CURRENT_TASK_TITLE,
            "current_task_status": current_task_status or "missing",
            "status_map": project_status_map,
            "problems": project_problems,
        },
        "git_status": git_status,
        "current_task_git_status": current_task_git_status,
    }
    return receipt


def write_receipt(receipt: dict[str, Any]) -> Path:
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    LATEST_RECEIPT.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return LATEST_RECEIPT


def main() -> int:
    receipt = build_readiness_receipt()
    output_path = write_receipt(receipt)
    payload = dict(receipt)
    payload["receipt_path"] = str(output_path)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if receipt["ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
