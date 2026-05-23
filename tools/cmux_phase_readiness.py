#!/usr/bin/env python3
from __future__ import annotations

import argparse
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
from workspace.tools.cmux_read_contract import (
    REQUIRED_VERIFICATION_PACKET_SLOTS,
    classify_runtime_artifact,
    choose_commander_default_sources,
    consumer_state_covers_control_packet,
    render_verification_packet_sources,
)
from workspace.tools.current_task_source import (
    TaskSourceContractError,
    maybe_normalize_task_source_ref,
)


ARTIFACT_DIR = REPO_ROOT / "workspace" / "artifacts" / "project-readiness"
LATEST_RECEIPT = ARTIFACT_DIR / "phase2-preflight-latest.json"
PROJECT_OWNER = "hdot123"
PROJECT_NUMBER = 8
PROJECT_URL = "https://github.com/users/hdot123/projects/8"
CURRENT_TASK_TITLE = "[Phase 4] P14 CI, regression, and anchor cleanup"
REQUIRED_DONE_TITLES = (
    "[Phase 0] P10-core Dispatch gate contract",
    "[Phase 0] P12-core Commander semantics core",
    "[Phase 1] P1 Control packet schema",
    "[Phase 1] P2 Summary and sidecar split",
    "[Phase 1] P6 Migrate direct cmux consumers",
    "[Phase 1] P9 Main-thread token contract",
    "[Phase 1] P13 Artifact hygiene and read priority",
    "[Phase 2] P0-preflight Readiness gate and blocker repair",
    "[Phase 2] P3 Memory-hook slimming",
    "[Phase 2] P4 Hook-state materialization",
    "[Phase 2] P7 Hook mainline and preflight gates",
    "[Phase 2] P8 Health checks and special paths",
    "[Phase 3] P5 Active truth convergence",
    "[Phase 3] P10-rest Bootstrap and dispatch remainder",
    "[Phase 3] P11-rest Governance writeback migration",
    "[Phase 3] P11-text Special pane-text consumers",
    "[Phase 3] P12-rest Commander docs and truth mapping",
)
CURRENT_TASK_FILES = (
    REPO_ROOT / ".github" / "workflows" / "memory-hook-external-core-only.yml",
    REPO_ROOT / ".github" / "workflows" / "memory-core-auto-sync-deploy.yml",
    REPO_ROOT / "docs" / "project-management" / "workbot-cmux-p14-ci-regression-anchor-cleanup-2026-04-18.md",
    REPO_ROOT / "docs" / "project-management" / "workbot-cmux-p8-health-checks-and-special-paths-2026-04-18.md",
    REPO_ROOT / "docs" / "project-management" / "workbot-cmux-p11-text-special-pane-consumers-2026-04-18.md",
    REPO_ROOT / "workspace" / "tools" / "cmux_phase_readiness.py",
)
RUNTIME_ARTIFACT_DIR = REPO_ROOT / "workspace" / "artifacts" / "cmux-runtime"
DEFAULT_RUNTIME_BOT_NAMES = ("pm-bot", "dev-bot", "qa-bot", "doc-bot", "rea-bot")
BOARD_SLOT_IDENTITIES = {"empty", "cmux-browser"}
DELIVERY_DOCS = tuple(sorted((REPO_ROOT / "docs" / "project-management").glob("workbot-cmux-*.md")))


@dataclass(frozen=True)
class CommandResult:
    code: int
    stdout: str
    stderr: str


def resolve_task_scope_files(task_files: tuple[str | Path, ...] | None = None) -> tuple[Path, ...]:
    if task_files is None:
        return CURRENT_TASK_FILES
    normalized: list[Path] = []
    for raw_path in task_files:
        path = raw_path if isinstance(raw_path, Path) else Path(raw_path)
        normalized.append(path if path.is_absolute() else REPO_ROOT / path)
    return tuple(normalized)


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


def _collect_git_status(*, include_branch: bool = False, paths: tuple[Path, ...] = ()) -> dict[str, Any]:
    args = ["git", "-C", str(REPO_ROOT), "status", "--short"]
    if include_branch:
        args.append("--branch")
    if paths:
        args.extend(["--", *[str(path) for path in paths]])
    result = run_command(args)
    lines = [line for line in result.stdout.splitlines() if line.strip()]
    return {
        "ok": result.code == 0,
        "lines": lines,
        "stderr": result.stderr.strip(),
    }


def collect_git_status() -> dict[str, Any]:
    return _collect_git_status(include_branch=True)


def collect_scope_git_status(paths: tuple[Path, ...]) -> dict[str, Any]:
    return _collect_git_status(paths=paths)


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


def _load_jsonl_objects(path: Path) -> tuple[list[dict[str, Any]] | None, str | None]:
    if not path.exists():
        return [], None
    try:
        raw_lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        return None, f"invalid jsonl: {path} -> {exc}"
    items: list[dict[str, Any]] = []
    for index, raw_line in enumerate(raw_lines, start=1):
        rendered = raw_line.strip()
        if not rendered:
            continue
        try:
            payload = json.loads(rendered)
        except json.JSONDecodeError as exc:
            return None, f"invalid jsonl: {path}:{index} -> {exc}"
        if not isinstance(payload, dict):
            return None, f"jsonl payload must be object: {path}:{index}"
        items.append(payload)
    return items, None


def _ordered_bot_names(bot_names: list[str] | set[str]) -> list[str]:
    ordered = [bot_name for bot_name in DEFAULT_RUNTIME_BOT_NAMES if bot_name in bot_names]
    extras = [bot_name for bot_name in bot_names if bot_name not in ordered]
    return ordered + extras


def _infer_runtime_bot_name(value: Any) -> str | None:
    normalized = str(value or "").strip().upper().replace("_", "-")
    if not normalized or normalized.startswith("IDLE-"):
        return None
    if "PMBOT" in normalized or normalized.startswith("PM-"):
        return "pm-bot"
    if "DEVBOT" in normalized or normalized.startswith("DEV-"):
        return "dev-bot"
    if "QABOT" in normalized or normalized.startswith("QA-"):
        return "qa-bot"
    if "DOCBOT" in normalized or normalized.startswith("DOC-"):
        return "doc-bot"
    if "REABOT" in normalized or normalized.startswith("REA-"):
        return "rea-bot"
    return None


def _derive_required_a7_targets(current_task_sources: Any) -> tuple[list[str], bool]:
    if not isinstance(current_task_sources, list) or not current_task_sources:
        return [], False
    cycle_ids: set[str] = set()
    for raw_source in current_task_sources:
        try:
            normalized = maybe_normalize_task_source_ref(raw_source, expected_task_type="cmux")
        except TaskSourceContractError:
            return [], False
        if normalized is None:
            return [], False
        cycle_ids.add(normalized["cycle_id"])
    if len(cycle_ids) != 1:
        return [], False
    scope_tokens = [token.strip() for token in next(iter(cycle_ids)).split("|")[-1].split(",")]
    required = {
        bot_name
        for token in scope_tokens
        if token
        for bot_name in [_infer_runtime_bot_name(token)]
        if bot_name is not None
    }
    if not required:
        return [], False
    return _ordered_bot_names(required), True


def _collect_present_a7_targets(receipt_payload: dict[str, Any]) -> list[str]:
    raw_outcomes = receipt_payload.get("outcomes")
    if not isinstance(raw_outcomes, list):
        return []
    present: set[str] = set()
    for raw_outcome in raw_outcomes:
        if not isinstance(raw_outcome, dict):
            continue
        bot_name = _infer_runtime_bot_name(raw_outcome.get("logical_target"))
        if bot_name is None:
            task_source_ref = raw_outcome.get("task_source_ref")
            if isinstance(task_source_ref, dict):
                bot_name = _infer_runtime_bot_name(task_source_ref.get("assignment_id"))
        if bot_name is None:
            bot_name = _infer_runtime_bot_name(raw_outcome.get("assignment_id") or raw_outcome.get("task_id"))
        if bot_name is not None:
            present.add(bot_name)
    return _ordered_bot_names(present)


def collect_a7_writeback_targets(
    receipt_payloads: list[dict[str, Any]],
    *,
    current_task_sources: Any = None,
) -> dict[str, Any]:
    default_result = {
        "required_targets": [],
        "present_targets": [],
        "missing_targets": [],
        "evaluated_cycle_id": "",
        "complete": True,
        "scope_confirmed": True,
        "scope_issue": "",
    }
    if not receipt_payloads:
        return default_result

    required_targets, scope_confirmed = _derive_required_a7_targets(current_task_sources)
    if not scope_confirmed:
        return {
            **default_result,
            "complete": False,
            "scope_confirmed": False,
            "scope_issue": (
                "A7 dispatch scope is unconfirmed; required writeback targets could not be derived "
                "from current task source bindings"
            ),
        }

    latest_receipt = receipt_payloads[-1]
    present_targets = _collect_present_a7_targets(latest_receipt)
    missing_targets = [target for target in required_targets if target not in present_targets]
    return {
        "required_targets": required_targets,
        "present_targets": present_targets,
        "missing_targets": missing_targets,
        "evaluated_cycle_id": str(latest_receipt.get("cycle_id") or ""),
        "complete": not missing_targets,
        "scope_confirmed": True,
        "scope_issue": "",
    }

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


def collect_commander_read_contract_validation(runtime_dir: Path) -> dict[str, Any]:
    runtime_files = sorted(path for path in runtime_dir.glob("*") if path.is_file())
    rendered_paths = [str(path) for path in runtime_files]
    classified = [classify_runtime_artifact(path) for path in rendered_paths]
    default_sources = choose_commander_default_sources(rendered_paths)
    assignment_path = runtime_dir / "cmux-assignment.json"
    assignment_payload, _ = _load_json_file(assignment_path)
    current_task_sources = assignment_payload.get("current_task_sources") if isinstance(assignment_payload, dict) else None
    consumer_state_path = runtime_dir / "cmux-consumer-state-latest.json"
    consumer_state_payload, _ = _load_json_file(consumer_state_path)
    receipts_path = runtime_dir / "cmux-finish-receipts.jsonl"
    receipt_payloads, receipt_error = _load_jsonl_objects(receipts_path)
    a7_writeback = collect_a7_writeback_targets(
        receipt_payloads or [],
        current_task_sources=current_task_sources,
    )
    verification_packet_sources = render_verification_packet_sources(rendered_paths)
    verification_slots = [item["slot"] for item in verification_packet_sources]
    verification_missing_slots = [
        slot for slot in REQUIRED_VERIFICATION_PACKET_SLOTS if slot not in verification_slots
    ]

    summary_candidates = [item for item in classified if item.rule.name == "commander_summary"]
    fallback_candidates = [item for item in classified if item.rule.name in {"startup_smoke", "control_state"}]
    blocked_sources = [item for item in classified if not item.rule.normal_path_allowed]

    problems: list[str] = []
    if rendered_paths and not default_sources:
        problems.append("no normal-path commander read sources discovered")
    if summary_candidates and default_sources and default_sources[0].rule.name != "commander_summary":
        problems.append("summary exists but first commander default source is not commander_summary")
    if any(item.rule.name == "forensic_only" for item in default_sources):
        problems.append("forensic/log artifacts leaked into normal-path commander sources")
    if not summary_candidates and fallback_candidates:
        fallback_selected = any(item.rule.name in {"startup_smoke", "control_state"} for item in default_sources)
        if not fallback_selected:
            problems.append("summary missing but fallback sources (startup_smoke/control_state) were not selected")
    if receipt_error:
        problems.append(receipt_error)
    elif receipt_payloads and not a7_writeback["scope_confirmed"]:
        problems.append(a7_writeback["scope_issue"])
    elif receipt_payloads and not a7_writeback["complete"]:
        problems.append(
            "A7 local writeback is partial; missing mandatory targets: "
            + ", ".join(str(item) for item in a7_writeback["missing_targets"])
        )

    return {
        "ok": not problems,
        "runtime_dir": str(runtime_dir),
        "available_paths": rendered_paths,
        "default_sources": [
            {
                "path": item.path,
                "rule": item.rule.name,
                "priority": item.rule.priority,
                "normal_path_allowed": item.rule.normal_path_allowed,
            }
            for item in default_sources
        ],
        "blocked_normal_path_sources": [
            {
                "path": item.path,
                "rule": item.rule.name,
                "priority": item.rule.priority,
                "reason": item.rule.reason,
            }
            for item in blocked_sources
        ],
        "verification_packet": {
            "required_slots": list(REQUIRED_VERIFICATION_PACKET_SLOTS),
            "available_slots": verification_slots,
            "missing_slots": verification_missing_slots,
            "read_order": verification_packet_sources,
            "a7_required_writeback_targets": a7_writeback["required_targets"],
            "a7_present_writeback_targets": a7_writeback["present_targets"],
            "a7_missing_writeback_targets": a7_writeback["missing_targets"],
            "a7_evaluated_cycle_id": a7_writeback["evaluated_cycle_id"],
            "a7_writeback_complete": a7_writeback["complete"],
            "a7_scope_confirmed": a7_writeback["scope_confirmed"],
            "a7_scope_issue": a7_writeback["scope_issue"],
            "consumer_state_embeds_control_packet_auxiliary": bool(
                consumer_state_path.exists() and consumer_state_covers_control_packet(consumer_state_payload)
            ),
        },
        "problems": problems,
    }


def build_readiness_receipt(*, task_files: tuple[str | Path, ...] | None = None) -> dict[str, Any]:
    memory = validate_memory_system()
    doc_problems = collect_delivery_doc_anchor_problems(DELIVERY_DOCS)
    runtime_bot_names = expected_runtime_bot_names(RUNTIME_ARTIFACT_DIR)
    manifest_problems = collect_runtime_launch_manifest_problems(RUNTIME_ARTIFACT_DIR, runtime_bot_names)
    smoke_report_problems = collect_startup_smoke_report_problems(RUNTIME_ARTIFACT_DIR, runtime_bot_names)
    read_contract_validation = collect_commander_read_contract_validation(RUNTIME_ARTIFACT_DIR)
    resolved_task_files = resolve_task_scope_files(task_files)

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
    current_task_git_status = collect_scope_git_status(resolved_task_files)

    implemented = (
        memory["status"] == "ok"
        and not memory["missing_paths"]
        and not memory["validation_errors"]
        and not doc_problems
        and not manifest_problems
        and not smoke_report_problems
        and read_contract_validation["ok"]
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
            "commander_read_contract_validation": read_contract_validation,
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


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build the cmux phase readiness receipt.")
    parser.add_argument(
        "--task-file",
        dest="task_files",
        action="append",
        default=None,
        help="Explicit current-task scope file. Repeat this flag to pass multiple files.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    task_files = tuple(args.task_files) if args.task_files else None
    receipt = build_readiness_receipt(task_files=task_files)
    output_path = write_receipt(receipt)
    payload = dict(receipt)
    payload["receipt_path"] = str(output_path)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if receipt["ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
