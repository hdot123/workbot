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
RUNTIME_ARTIFACT_DIR = REPO_ROOT / "workspace" / "artifacts" / "cmux-runtime"
DEFAULT_RUNTIME_BOT_NAMES = ("pm-bot", "dev-bot", "qa-bot", "doc-bot", "rea-bot")
BOARD_SLOT_IDENTITIES = {"empty", "cmux-browser"}
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


def _load_json_file(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    if not path.exists():
        return None, f"missing file: {path}"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return None, f"invalid json: {path} -> {exc}"
    if not isinstance(payload, dict):
        return None, f"payload must be object: {path}"
    return payload, None


def expected_runtime_bot_names(runtime_dir: Path) -> tuple[str, ...]:
    assignment_candidates = (
        runtime_dir / "cmux-assignment.json",
        runtime_dir / "pm-bot-watch.json",
    )
    discovered: list[str] = []
    for assignment_path in assignment_candidates:
        payload, error = _load_json_file(assignment_path)
        if payload is None or error is not None:
            continue
        raw_items = payload.get("assignments")
        if not isinstance(raw_items, list):
            continue
        for raw_item in raw_items:
            if not isinstance(raw_item, dict):
                continue
            status = str(raw_item.get("status") or "").strip().upper()
            if status not in {"ACTIVE", "RUNNING", "PENDING"}:
                continue
            bot_name = str(raw_item.get("bot_name") or raw_item.get("logical_target") or "").strip()
            if not bot_name:
                continue
            if bot_name in BOARD_SLOT_IDENTITIES:
                continue
            if bot_name not in discovered:
                discovered.append(bot_name)
    if discovered:
        ordered = [bot for bot in DEFAULT_RUNTIME_BOT_NAMES if bot in discovered]
        extras = [bot for bot in discovered if bot not in ordered]
        return tuple(ordered + extras)
    return DEFAULT_RUNTIME_BOT_NAMES


def collect_runtime_launch_manifest_problems(
    runtime_dir: Path,
    bot_names: tuple[str, ...],
) -> dict[str, list[str]]:
    problems: dict[str, list[str]] = {}
    for bot_name in bot_names:
        path = runtime_dir / f"runtime-launch-manifest-{bot_name}.json"
        payload, error = _load_json_file(path)
        if payload is None:
            problems[str(path)] = [error or f"missing manifest: {path}"]
            continue

        issues: list[str] = []
        if str(payload.get("bot_name") or "").strip() != bot_name:
            issues.append("bot_name mismatch")
        if not str(payload.get("workspace_ref") or "").strip():
            issues.append("workspace_ref missing")
        if not str(payload.get("surface_ref") or "").strip():
            issues.append("surface_ref missing")
        if not str(payload.get("permission_mode") or "").strip():
            issues.append("permission_mode missing")
        allowed_tools = payload.get("allowed_tools")
        if not isinstance(allowed_tools, list) or not allowed_tools:
            issues.append("allowed_tools missing_or_empty")
        runtime_settings_path = str(payload.get("runtime_settings_path") or "").strip()
        if not runtime_settings_path:
            issues.append("runtime_settings_path missing")
        elif not Path(runtime_settings_path).exists():
            issues.append(f"runtime_settings_path_missing: {runtime_settings_path}")
        if not str(payload.get("launch_command") or "").strip():
            issues.append("launch_command missing")
        if issues:
            problems[str(path)] = issues
    return problems


def collect_startup_smoke_report_problems(
    runtime_dir: Path,
    bot_names: tuple[str, ...],
) -> dict[str, list[str]]:
    problems: dict[str, list[str]] = {}
    for bot_name in bot_names:
        smoke_path = runtime_dir / f"{bot_name}-smoke-report.json"
        smoke_payload, smoke_error = _load_json_file(smoke_path)
        if smoke_payload is None:
            problems[str(smoke_path)] = [smoke_error or f"missing smoke report: {smoke_path}"]
            continue

        manifest_path = runtime_dir / f"runtime-launch-manifest-{bot_name}.json"
        manifest_payload, _ = _load_json_file(manifest_path)
        external_tokens: list[str] = []
        if isinstance(manifest_payload, dict):
            raw_tokens = manifest_payload.get("external_mcp_tokens")
            if isinstance(raw_tokens, list):
                external_tokens = [str(token).strip().lower() for token in raw_tokens if str(token).strip()]
        requires_crawl_smoke = "crawl4ai" in external_tokens

        issues: list[str] = []
        if str(smoke_payload.get("bot_name") or "").strip() != bot_name:
            issues.append("bot_name mismatch")
        status = str(smoke_payload.get("status") or "").strip().lower()
        if requires_crawl_smoke:
            if status != "passed":
                issues.append(f"status must be passed when crawl4ai is enabled (actual={status or 'missing'})")
            result = smoke_payload.get("result")
            if not isinstance(result, dict):
                issues.append("result missing when crawl4ai is enabled")
            else:
                success = bool(result.get("success"))
                status_code = str(result.get("status_code") or "").strip()
                if not success:
                    issues.append("result.success is false when crawl4ai is enabled")
                if status_code and status_code != "200":
                    issues.append(f"unexpected status_code for crawl4ai smoke: {status_code}")
        else:
            if status not in {"passed", "skipped"}:
                issues.append(f"status must be passed/skipped (actual={status or 'missing'})")
        if issues:
            problems[str(smoke_path)] = issues
    return problems


def build_readiness_receipt() -> dict[str, Any]:
    memory = validate_memory_system()
    doc_problems = collect_delivery_doc_anchor_problems(DELIVERY_DOCS)
    runtime_bot_names = expected_runtime_bot_names(RUNTIME_ARTIFACT_DIR)
    manifest_problems = collect_runtime_launch_manifest_problems(RUNTIME_ARTIFACT_DIR, runtime_bot_names)
    smoke_report_problems = collect_startup_smoke_report_problems(RUNTIME_ARTIFACT_DIR, runtime_bot_names)

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
        and not manifest_problems
        and not smoke_report_problems
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
        "runtime_artifact_validation": {
            "runtime_dir": str(RUNTIME_ARTIFACT_DIR),
            "expected_bot_names": list(runtime_bot_names),
            "runtime_launch_manifest_problems": manifest_problems,
            "startup_smoke_report_problems": smoke_report_problems,
        },
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
