#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


SCRIPT_PATH = Path(__file__).resolve()
WORKSPACE_ROOT = SCRIPT_PATH.parents[1]
REPO_ROOT = SCRIPT_PATH.parents[2]
ARTIFACT_ROOT = WORKSPACE_ROOT / "artifacts" / "memory-hook"
CONTEXT_ROOT = ARTIFACT_ROOT / "contexts"
EVENT_LOG = ARTIFACT_ROOT / "events.jsonl"
ERROR_LOG = WORKSPACE_ROOT / "memory" / "system" / "errors.log"
PROJECT_MAP_ROOT = WORKSPACE_ROOT / "project-map"
TRUTH_MODEL = WORKSPACE_ROOT / "memory" / "kb" / "global" / "workbot-truth-model.md"
PROJECT_MAP_FILES = [
    PROJECT_MAP_ROOT / "INDEX.md",
    PROJECT_MAP_ROOT / "legal-core-map.md",
    PROJECT_MAP_ROOT / "ingestion-registry-map.md",
]
PROJECT_MAP_GOVERNANCE = WORKSPACE_ROOT / "memory" / "kb" / "global" / "workbot-project-map-governance.md"
LEGALITY_SOURCE_POLICY = "active-legal-map-only"
REGISTRATION_COMMIT_POLICY = "required-after-absorption-complete"
REGISTRATION_COMMIT_PHASE = "declared-not-enforced"
REGISTRATION_GIT_SCOPE = [
    WORKSPACE_ROOT / "INDEX.md",
    WORKSPACE_ROOT / "NOW.md",
    *PROJECT_MAP_FILES,
    PROJECT_MAP_GOVERNANCE,
    WORKSPACE_ROOT / "memory" / "kb" / "global" / "workbot-hook-contract.md",
]
LEGAL_CORE_MARKERS = [
    str(TRUTH_MODEL),
    str(WORKSPACE_ROOT / "memory" / "kb" / "global" / "workbot-memory-system.md"),
    str(WORKSPACE_ROOT / "memory" / "kb" / "decisions" / "**"),
    str(WORKSPACE_ROOT / "memory" / "kb" / "lessons" / "**"),
    str(WORKSPACE_ROOT / "memory" / "system" / "**"),
    str(WORKSPACE_ROOT / "memory" / "archive" / "**"),
    str(WORKSPACE_ROOT / "memory" / "inbox.md"),
]
REQUIRED_REGISTRY_SCOPES = [
    "workspace/memory/kb/global/projects/**",
    "workspace/memory/kb/global/memory-router-design.md",
    "workspace/memory/kb/global/memory-router-design-v2.1.1.md",
    "workspace/memory/kb/global/versions/**",
    "workspace/memory/kb/global/conflicts.md",
    "workspace/memory/kb/global/llm-tech-baseline.md",
    "workspace/memory/kb/global/multi-brand-protocol-baseline.md",
    "workspace/memory/kb/global/pve-docker-template-deployment-guide.md",
    "workspace/memory/docs/corrections/**",
    "workspace/memory/docs/research/**",
    "workspace/memory/docs/references/**",
    "workspace/memory/log/**",
    "workspace/projects/**",
    "workspace/artifacts/**",
    "/Users/busiji/workbot/docs/**",
    "/Users/busiji/workbot/scripts/**",
    "/Users/busiji/workbot/tests/**",
    "/Users/busiji/workbot/skills/**",
    "/Users/busiji/workbot/artifacts/**",
    "/Users/busiji/workbot/AEdu/**",
    "/Users/busiji/workbot/app/**",
    "/Users/busiji/workbot/agents/**",
    "/Users/busiji/workbot/gpt-web-to/**",
]
CLAUDE_HOOK_STATE_DIR = Path("/Users/busiji/.agents/skills/cmux/scripts")
if str(CLAUDE_HOOK_STATE_DIR) not in sys.path:
    sys.path.append(str(CLAUDE_HOOK_STATE_DIR))

from cmux_hook_state import default_hook_state_path, record_hook_event  # type: ignore  # noqa: E402


REQUIRED_CANONICAL = [
    WORKSPACE_ROOT / "INDEX.md",
    WORKSPACE_ROOT / "NOW.md",
    *PROJECT_MAP_FILES,
    WORKSPACE_ROOT / "memory" / "kb" / "INDEX.md",
    WORKSPACE_ROOT / "memory" / "docs" / "INDEX.md",
    WORKSPACE_ROOT / "memory" / "inbox.md",
    TRUTH_MODEL,
    WORKSPACE_ROOT / "memory" / "kb" / "global" / "workbot-memory-system.md",
    WORKSPACE_ROOT / "memory" / "kb" / "global" / "workbot-memory-routing.md",
    WORKSPACE_ROOT / "memory" / "kb" / "global" / "workbot-hook-contract.md",
    PROJECT_MAP_GOVERNANCE,
    WORKSPACE_ROOT / "memory" / "kb" / "projects" / "INDEX.md",
]

PROJECT_CANONICAL = {
    "workbot": WORKSPACE_ROOT / "memory" / "kb" / "projects" / "workbot.md",
    "AEdu": WORKSPACE_ROOT / "memory" / "kb" / "projects" / "AEdu.md",
    "platform-capabilities": WORKSPACE_ROOT / "memory" / "kb" / "projects" / "platform-capabilities.md",
}

PROJECT_RUNTIME_ROOT = {
    "workbot": WORKSPACE_ROOT / "projects",
    "AEdu": WORKSPACE_ROOT / "projects" / "AEdu",
    "platform-capabilities": WORKSPACE_ROOT / "projects",
}

PROJECT_DOC_REFS = {
    "workbot": [
        WORKSPACE_ROOT / "memory" / "docs" / "INDEX.md",
        WORKSPACE_ROOT / "memory" / "docs" / "记忆系统全景文档.md",
    ],
    "AEdu": [
        WORKSPACE_ROOT / "memory" / "docs" / "research" / "projects" / "AEdu" / "INDEX.md",
        WORKSPACE_ROOT / "projects" / "AEdu" / "INDEX.md",
    ],
    "platform-capabilities": [
        WORKSPACE_ROOT / "memory" / "docs" / "INDEX.md",
    ],
}

GLOBAL_CANONICAL = [
    TRUTH_MODEL,
    WORKSPACE_ROOT / "memory" / "kb" / "global" / "workbot-memory-system.md",
    WORKSPACE_ROOT / "memory" / "kb" / "global" / "workbot-memory-routing.md",
    WORKSPACE_ROOT / "memory" / "kb" / "global" / "workbot-hook-contract.md",
    PROJECT_MAP_GOVERNANCE,
]

AUTHORITY_ALLOWED_PATHS = {
    PROJECT_MAP_ROOT / "INDEX.md",
    PROJECT_MAP_ROOT / "legal-core-map.md",
}

LOWER_EVIDENCE_ROOTS = [
    WORKSPACE_ROOT / "projects",
    WORKSPACE_ROOT / "artifacts",
    WORKSPACE_ROOT / "tools",
    WORKSPACE_ROOT / "memory" / "log",
    WORKSPACE_ROOT / "memory" / "system",
    REPO_ROOT / "app",
    REPO_ROOT / "agents",
    REPO_ROOT / "gpt-web-to",
]

DEFAULT_DECISION_REFS = [
    WORKSPACE_ROOT / "memory" / "kb" / "decisions" / "INDEX.md",
]

PROJECT_DECISION_REFS = {
    "workbot": [],
    "AEdu": [
        WORKSPACE_ROOT / "memory" / "kb" / "decisions" / "2026-04-02-aedu-ce-lifecycle-rule.md",
        WORKSPACE_ROOT / "memory" / "kb" / "decisions" / "2026-04-02-aedu-commander-task-routing.md",
    ],
    "platform-capabilities": [],
}

AEDU_ROOT = REPO_ROOT / "AEdu"
GOVERNANCE_FROZEN_TUPLE_FILES = [
    AEDU_ROOT / "00_导航与管理" / "KB+INGEST 模块级开发准入评审单.md",
    AEDU_ROOT / "00_导航与管理" / "SIM模块级开发准入评审单.md",
    AEDU_ROOT / "12_实施与试点运营" / "09_KB+INGEST 试点范围与责任边界.md",
    AEDU_ROOT / "scripts" / "validate_kb_closure.py",
]
EVENT_CONTRACT_FILES = {
    "upstream_standard": AEDU_ROOT / "06_数据接入与事件流" / "07_学习事件生成标准.md",
    "upstream_mapping": AEDU_ROOT / "06_数据接入与事件流" / "12_输入源映射表.md",
    "formal_contract": AEDU_ROOT / "11_系统架构与工程实现" / "22_KB+INGEST-TWIN输入契约.md",
    "upstream_samples": AEDU_ROOT / "11_系统架构与工程实现" / "21_KB+INGEST 端到端样例集.md",
    "downstream_samples": AEDU_ROOT / "11_系统架构与工程实现" / "24_TWIN端到端样例集.md",
}
FROZEN_TUPLE_EXPECTED = {
    "province=安徽",
    "region_id=CN_AH",
    "rule_package=AH_RULE_V1",
    "kb_version_prefix=KB_CN_AH_",
}
FROZEN_TUPLE_LEGACY_MARKERS = {
    "CN_GD_SZ",
    "KB_CN_GD_SZ",
}
FORMAL_SOURCE_TYPES = {
    "parent_text",
    "teacher_feedback_text",
    "scan_ocr",
    "reviewed_event",
}
FORMAL_EVENT_TYPES = {
    "homework_result_event",
    "correction_followup_event",
    "teacher_feedback_event",
    "parent_feedback_event",
    "scan_ocr_result_event",
    "reviewed_learning_event",
}
FORMAL_EVENT_STATUSES = {
    "success",
    "degraded",
    "review_needed",
    "rejected",
}
FORMAL_FIELD_KEYS = {
    "event_summary",
    "raw_input_ref",
}
LEGACY_FIELD_KEYS = {
    "summary",
    "raw_input_id",
    "accepted",
}

DEFAULT_LESSON_REFS = [
    WORKSPACE_ROOT / "memory" / "kb" / "lessons" / "memory-docs-immutable.md",
]

PROJECT_LESSON_REFS = {
    "workbot": [
        WORKSPACE_ROOT / "memory" / "kb" / "lessons" / "pm-bot-crawl4ai-runtime-path.md",
    ],
    "AEdu": [],
    "platform-capabilities": [],
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Workbot memory hook gateway.")
    parser.add_argument("--host", required=True, choices=("codex", "claude"))
    parser.add_argument("--event", required=True, choices=("session-start", "prompt-submit", "stop", "notification"))
    parser.add_argument("--no-delegate", action="store_true", help="Generate gateway artifacts only.")
    return parser.parse_args()


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def read_payload(raw_payload: str) -> dict[str, Any]:
    if not raw_payload.strip():
        return {}
    try:
        loaded = json.loads(raw_payload)
    except json.JSONDecodeError:
        return {}
    return loaded if isinstance(loaded, dict) else {"payload": loaded}


def payload_cwd(payload: dict[str, Any]) -> Path | None:
    value = payload.get("cwd")
    if isinstance(value, str) and value:
        return Path(value).expanduser()
    return None


def environment_cwd() -> Path | None:
    env_pwd = os.environ.get("PWD")
    return Path(env_pwd).expanduser() if env_pwd else None


def path_within_repo(path: Path) -> bool:
    try:
        path.resolve().relative_to(REPO_ROOT.resolve())
        return True
    except ValueError:
        return False


def discover_cwd(payload: dict[str, Any]) -> Path:
    provided_cwd = payload_cwd(payload)
    if provided_cwd and path_within_repo(provided_cwd):
        return provided_cwd
    env_cwd = environment_cwd()
    if env_cwd and path_within_repo(env_cwd):
        return env_cwd
    if env_cwd:
        return env_cwd
    if provided_cwd:
        return provided_cwd
    return REPO_ROOT


def should_noop_for_external_context(payload: dict[str, Any]) -> bool:
    if os.environ.get("WORKBOT_FORCE_HOOK"):
        return False
    env_cwd = environment_cwd()
    provided_cwd = payload_cwd(payload)
    env_in_repo = bool(env_cwd and path_within_repo(env_cwd))
    payload_in_repo = bool(provided_cwd and path_within_repo(provided_cwd))
    return not env_in_repo and not payload_in_repo


def noop_for_external_host(host: str) -> int:
    if host == "codex":
        sys.stdout.write("{}\n")
    return 0


def determine_project_scope(cwd: Path) -> str:
    if not path_within_repo(cwd):
        return "workbot"
    cwd_str = str(cwd)
    if "/workspace/projects/AEdu" in cwd_str or cwd == REPO_ROOT / "AEdu" or "/workbot/AEdu" in cwd_str:
        return "AEdu"
    if any(segment in cwd_str for segment in ("/workbot/app", "/workbot/agents", "/workbot/gpt-web-to", "/workspace/projects/app", "/workspace/projects/agents", "/workspace/projects/skills")):
        return "platform-capabilities"
    return "workbot"


def extract_excerpt(path: Path, max_lines: int = 12) -> list[str]:
    if not path.exists():
        return []
    lines = []
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        lines.append(stripped)
        if len(lines) >= max_lines:
            break
    return lines


def section_bullets(text: str, heading: str) -> list[str]:
    lines = text.splitlines()
    bullets: list[str] = []
    in_section = False
    for line in lines:
        stripped = line.strip()
        if stripped == heading or stripped.endswith(heading.replace("## ", "").replace("### ", "")):
            in_section = True
            continue
        if in_section and stripped.startswith("#"):
            break
        if in_section and line.strip().startswith("- "):
            bullets.append(line.strip()[2:].strip().strip("`"))
    return bullets


def section_body(text: str, heading: str) -> str:
    lines = text.splitlines()
    start_idx: int | None = None
    for idx, line in enumerate(lines):
        if line.strip() == heading:
            start_idx = idx + 1
            break
    if start_idx is None:
        return ""
    body: list[str] = []
    for line in lines[start_idx:]:
        if line.strip().startswith("## "):
            break
        body.append(line)
    return "\n".join(body)


def markdown_code_tokens(text: str) -> set[str]:
    return {match.group(1) for match in re.finditer(r"`([^`]+)`", text)}


def json_string_values(text: str, key: str) -> set[str]:
    pattern = rf'"{re.escape(key)}"\s*:\s*"([^"]+)"'
    return {match.group(1) for match in re.finditer(pattern, text)}


def json_object_keys(text: str) -> set[str]:
    return {match.group(1) for match in re.finditer(r'"([^"]+)"\s*:', text)}


def governance_frozen_tuple_blocker_errors() -> list[str]:
    texts: dict[Path, str] = {}
    missing_files: list[str] = []
    for path in GOVERNANCE_FROZEN_TUPLE_FILES:
        if not path.exists():
            missing_files.append(str(path))
            continue
        texts[path] = path.read_text(encoding="utf-8")
    if missing_files:
        return ["missing governance files: " + ", ".join(missing_files)]
    combined_text = "\n".join(texts.values())
    errors: list[str] = []
    missing_expected = sorted(marker for marker in FROZEN_TUPLE_EXPECTED if marker not in combined_text)
    if missing_expected:
        errors.append("missing expected tuple markers: " + ", ".join(missing_expected))
    legacy_hits = {
        str(path): sorted(marker for marker in FROZEN_TUPLE_LEGACY_MARKERS if marker in text)
        for path, text in texts.items()
        if any(marker in text for marker in FROZEN_TUPLE_LEGACY_MARKERS)
    }
    if legacy_hits:
        rendered = ", ".join(f"{path} -> {', '.join(hits)}" for path, hits in legacy_hits.items())
        errors.append("legacy frozen tuple markers still present: " + rendered)
    return errors


def event_contract_blocker_errors() -> list[str]:
    texts: dict[str, str] = {}
    missing_files: list[str] = []
    for name, path in EVENT_CONTRACT_FILES.items():
        if not path.exists():
            missing_files.append(str(path))
            continue
        texts[name] = path.read_text(encoding="utf-8")
    if missing_files:
        return ["missing event contract files: " + ", ".join(missing_files)]

    upstream_standard = texts["upstream_standard"]
    upstream_mapping = texts["upstream_mapping"]
    formal_contract = texts["formal_contract"]
    upstream_samples = texts["upstream_samples"]
    downstream_samples = texts["downstream_samples"]

    formal_sets = {
        "upstream_standard": {
            "source_types": sorted(
                markdown_code_tokens(section_body(upstream_standard, "## 3. 正式输入源")) & FORMAL_SOURCE_TYPES
            ),
            "event_types": sorted(
                markdown_code_tokens(section_body(upstream_standard, "## 4. 正式事件类型")) & FORMAL_EVENT_TYPES
            ),
            "event_statuses": sorted(
                markdown_code_tokens(section_body(upstream_standard, "## 6. event_status 标准")) & FORMAL_EVENT_STATUSES
            ),
        },
        "upstream_mapping": {
            "source_types": sorted(
                markdown_code_tokens(section_body(upstream_mapping, "## 2. 正式输入源范围")) & FORMAL_SOURCE_TYPES
            ),
            "event_types": sorted(
                markdown_code_tokens(section_body(upstream_mapping, "## 3. 输入源到正式事件的映射主表")) & FORMAL_EVENT_TYPES
            ),
            "event_statuses": sorted(
                (markdown_code_tokens(section_body(upstream_mapping, "## 4. 主路由规则"))
                 | markdown_code_tokens(section_body(upstream_mapping, "## 5. 错误码与原因码")))
                & FORMAL_EVENT_STATUSES
            ),
        },
        "formal_contract": {
            "source_types": sorted(
                markdown_code_tokens(section_body(formal_contract, "## 3. source_type 正式白名单")) & FORMAL_SOURCE_TYPES
            ),
            "event_types": sorted(
                markdown_code_tokens(section_body(formal_contract, "## 4. event_type 正式清单")) & FORMAL_EVENT_TYPES
            ),
            "event_statuses": sorted(
                markdown_code_tokens(section_body(formal_contract, "## 6. event_status 正式取值")) & FORMAL_EVENT_STATUSES
            ),
        },
    }

    expected_formal_sets = {
        "source_types": sorted(FORMAL_SOURCE_TYPES),
        "event_types": sorted(FORMAL_EVENT_TYPES),
        "event_statuses": sorted(FORMAL_EVENT_STATUSES),
    }
    errors: list[str] = []
    for doc_name, observed in formal_sets.items():
        for key, expected in expected_formal_sets.items():
            if observed[key] != expected:
                errors.append(f"{doc_name} {key} mismatch: expected {expected}, got {observed[key]}")

    sample_sets = {
        "upstream_samples": {
            "source_types": sorted(json_string_values(upstream_samples, "source_type")),
            "event_types": sorted(json_string_values(upstream_samples, "event_type")),
            "event_statuses": sorted(json_string_values(upstream_samples, "event_status")),
            "field_keys": sorted(json_object_keys(upstream_samples) & (FORMAL_FIELD_KEYS | LEGACY_FIELD_KEYS)),
        },
        "downstream_samples": {
            "source_types": sorted(json_string_values(downstream_samples, "source_type")),
            "event_types": sorted(json_string_values(downstream_samples, "event_type")),
            "event_statuses": sorted(json_string_values(downstream_samples, "event_status")),
            "field_keys": sorted(json_object_keys(downstream_samples) & (FORMAL_FIELD_KEYS | LEGACY_FIELD_KEYS)),
        },
    }
    for doc_name, observed in sample_sets.items():
        unknown_source_types = sorted(set(observed["source_types"]) - FORMAL_SOURCE_TYPES)
        unknown_event_types = sorted(set(observed["event_types"]) - FORMAL_EVENT_TYPES)
        unknown_event_statuses = sorted(set(observed["event_statuses"]) - FORMAL_EVENT_STATUSES)
        missing_formal_fields = sorted(FORMAL_FIELD_KEYS - set(observed["field_keys"]))
        legacy_fields = sorted(set(observed["field_keys"]) & LEGACY_FIELD_KEYS)
        if unknown_source_types:
            errors.append(f"{doc_name} contains out-of-contract source_type values: " + ", ".join(unknown_source_types))
        if unknown_event_types:
            errors.append(f"{doc_name} contains out-of-contract event_type values: " + ", ".join(unknown_event_types))
        if unknown_event_statuses:
            errors.append(
                f"{doc_name} contains out-of-contract event_status values: " + ", ".join(unknown_event_statuses)
            )
        if missing_formal_fields:
            errors.append(f"{doc_name} sample JSON missing formal field keys: " + ", ".join(missing_formal_fields))
        if legacy_fields:
            errors.append(f"{doc_name} sample JSON still uses legacy field keys: " + ", ".join(legacy_fields))
    return errors


def path_is_under(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def classify_truth_ref(path: Path) -> str:
    if path == PROJECT_MAP_ROOT / "legal-core-map.md":
        return "legal-core"
    if path == PROJECT_MAP_ROOT / "INDEX.md":
        return "project-map-index"
    if path in GLOBAL_CANONICAL:
        return "global-canonical"
    if path_is_under(path, WORKSPACE_ROOT / "memory" / "kb" / "global" / "projects"):
        return "compatibility-only"
    if path_is_under(path, WORKSPACE_ROOT / "memory" / "kb" / "projects"):
        return "project-canonical"
    if path_is_under(path, WORKSPACE_ROOT / "memory" / "docs"):
        return "docs"
    if path_is_under(path, WORKSPACE_ROOT / "projects"):
        return "project-runtime"
    if path_is_under(path, WORKSPACE_ROOT / "artifacts"):
        return "artifact"
    if path_is_under(path, WORKSPACE_ROOT / "tools"):
        return "tooling"
    if path_is_under(path, WORKSPACE_ROOT / "memory" / "log"):
        return "log"
    if path_is_under(path, WORKSPACE_ROOT / "memory" / "system"):
        return "system"
    if path_is_under(path, REPO_ROOT / "app"):
        return "app"
    if path_is_under(path, REPO_ROOT / "agents"):
        return "agents"
    if path_is_under(path, REPO_ROOT / "gpt-web-to"):
        return "gpt-web-to"
    if path == REPO_ROOT / "AGENTS.md":
        return "repo-policy"
    if path == WORKSPACE_ROOT / "INDEX.md":
        return "workspace-entry"
    return "other"


def authority_ref_allowed(path: Path) -> bool:
    return path in AUTHORITY_ALLOWED_PATHS or path in GLOBAL_CANONICAL


def lower_evidence_ref(path: Path) -> bool:
    return any(path_is_under(path, root) for root in LOWER_EVIDENCE_ROOTS)


def truth_basis_sections_for(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    return {
        "source_refs": section_bullets(text, "### Source Refs"),
        "authority_refs": section_bullets(text, "### Authority Refs"),
        "evidence_refs": section_bullets(text, "### Evidence Refs"),
        "conflict_status": section_bullets(text, "### Conflict Status"),
    }


def truth_basis_errors_for(path: Path) -> list[str]:
    errors: list[str] = []
    if not path.exists():
        return [f"missing truth canonical: {path}"]
    text = path.read_text(encoding="utf-8")
    if "Truth Basis" not in text:
        return [f"truth basis section missing: {path}"]
    sections = truth_basis_sections_for(path)
    source_refs = sections["source_refs"]
    authority_refs = sections["authority_refs"]
    evidence_refs = sections["evidence_refs"]
    conflict = sections["conflict_status"]
    if not source_refs:
        errors.append(f"source refs missing: {path}")
    if not authority_refs:
        errors.append(f"authority refs missing: {path}")
    if not evidence_refs:
        errors.append(f"evidence refs missing: {path}")
    if not conflict:
        errors.append(f"conflict status missing: {path}")
    elif conflict != ["resolved"]:
        errors.append(f"conflict status unresolved: {path}")
    source_paths = [Path(item).expanduser() for item in source_refs]
    authority_paths = [Path(item).expanduser() for item in authority_refs]
    evidence_paths = [Path(item).expanduser() for item in evidence_refs]
    for ref_path in [*source_paths, *authority_paths, *evidence_paths]:
        if not ref_path.is_absolute():
            errors.append(f"truth ref must be absolute: {ref_path}")
        if not path_is_under(ref_path, REPO_ROOT):
            errors.append(f"truth ref outside repository: {ref_path}")
        if not ref_path.exists():
            errors.append(f"truth ref missing on disk: {ref_path}")
    if set(source_refs) == set(evidence_refs):
        errors.append(f"source refs and evidence refs must not be identical: {path}")
    if set(source_refs) & set(authority_refs):
        errors.append(f"source refs overlap authority refs: {path}")
    if set(authority_refs) & set(evidence_refs):
        errors.append(f"authority refs overlap evidence refs: {path}")
    for authority_path in authority_paths:
        if not authority_ref_allowed(authority_path):
            errors.append(f"authority ref is not formal canonical: {authority_path}")
    if source_paths and all(classify_truth_ref(source_path) in {"global-canonical", "legal-core", "project-map-index"} for source_path in source_paths):
        errors.append(f"source refs do not include a non-canonical origin: {path}")
    if evidence_paths and not any(lower_evidence_ref(evidence_path) for evidence_path in evidence_paths):
        errors.append(f"evidence refs do not include lower-layer support: {path}")
    return errors


def existing_paths(paths: list[Path]) -> list[str]:
    return [str(path) for path in paths if path.exists()]


def normalize_repo_scope_entry(value: str | Path) -> str | None:
    path = Path(value).expanduser()
    try:
        return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
    except ValueError:
        return None


def registration_payload_paths(payload: dict[str, Any]) -> list[str]:
    raw = payload.get("registration_paths")
    if isinstance(raw, str):
        raw_values = [raw]
    elif isinstance(raw, list):
        raw_values = [item for item in raw if isinstance(item, str)]
    else:
        return []
    normalized: list[str] = []
    for item in raw_values:
        normalized_item = normalize_repo_scope_entry(item)
        if normalized_item and normalized_item not in normalized:
            normalized.append(normalized_item)
    return normalized


def git_name_only(*args: str) -> list[str]:
    proc = subprocess.run(
        ["git", "-C", str(REPO_ROOT), *args],
        text=True,
        capture_output=True,
        check=False,
    )
    if proc.returncode != 0:
        return []
    return [line.strip() for line in (proc.stdout or "").splitlines() if line.strip()]


def path_matches_scope(candidate: str, scope_entry: str) -> bool:
    normalized_scope = scope_entry.rstrip("/")
    return candidate == normalized_scope or candidate.startswith(f"{normalized_scope}/")


def git_registration_probe(event: str, payload: dict[str, Any]) -> dict[str, Any]:
    map_scope = [str(path) for path in REGISTRATION_GIT_SCOPE]
    registration_paths = registration_payload_paths(payload)
    tracked_scope = map_scope + [str(REPO_ROOT / item) for item in registration_paths]
    proc = subprocess.run(
        ["git", "-C", str(REPO_ROOT), "status", "--short", "--", *tracked_scope],
        text=True,
        capture_output=True,
        check=False,
    )
    entries = [line for line in (proc.stdout or "").splitlines() if line.strip()]
    head_commit = subprocess.run(
        ["git", "-C", str(REPO_ROOT), "rev-parse", "HEAD"],
        text=True,
        capture_output=True,
        check=False,
    )
    latest_commit = (head_commit.stdout or "").strip()
    commit_scope = [normalize_repo_scope_entry(path) for path in REGISTRATION_GIT_SCOPE]
    commit_scope = [path for path in commit_scope if path]
    commit_scope.extend(registration_paths)
    head_touched = git_name_only("diff-tree", "--no-commit-id", "--name-only", "-r", "HEAD", "--", *commit_scope)
    map_touched = any(any(path_matches_scope(item, scope) for scope in commit_scope[: len(REGISTRATION_GIT_SCOPE)]) for item in head_touched)
    registration_touched = any(any(path_matches_scope(item, scope) for scope in registration_paths) for item in head_touched)
    if entries:
        status = "pending-commit"
    elif not registration_paths:
        status = "awaiting-registration-payload"
    elif map_touched and registration_touched:
        status = "committed-coupled"
    else:
        status = "committed-not-proven"
    return {
        "phase": REGISTRATION_COMMIT_PHASE,
        "policy": REGISTRATION_COMMIT_POLICY,
        "gate_event": "stop",
        "triggered_on_current_event": event == "stop",
        "status": status,
        "tracked_scope": tracked_scope,
        "registration_paths": registration_paths,
        "changed_entries": entries,
        "latest_commit": latest_commit,
        "latest_commit_touched": head_touched,
        "map_scope_touched_in_latest_commit": map_touched,
        "registration_scope_touched_in_latest_commit": registration_touched,
        "scope_clean": not entries,
        "would_pass_if_enforced": status == "committed-coupled",
        "probe_ok": proc.returncode == 0,
        "stderr": proc.stderr.strip(),
    }


def project_map_refs() -> list[str]:
    return [str(path) for path in PROJECT_MAP_FILES]


def read_text_if_exists(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def validate_project_map_files() -> list[str]:
    errors: list[str] = []
    index_text = read_text_if_exists(PROJECT_MAP_FILES[0])
    core_text = read_text_if_exists(PROJECT_MAP_FILES[1])
    registry_text = read_text_if_exists(PROJECT_MAP_FILES[2])
    governance_text = read_text_if_exists(PROJECT_MAP_GOVERNANCE)

    if "唯一合法入口" not in index_text:
        errors.append("project-map index does not declare the unique legal entry")
    if "只有出现在合法目录地图中并被标为 `active-legal` 的条目或目录，才是合法资料。" not in index_text:
        errors.append("project-map index does not declare active-legal map-only legality")
    if "同次 `git commit` 提交后才生效" not in index_text:
        errors.append("project-map index does not declare the future registration git-commit gate")
    if "round-" in index_text or "waves/" in index_text:
        errors.append("project-map index still references transition round files")
    if "active-legal" not in core_text:
        errors.append("legal-core-map does not declare active-legal status")
    if "只有本图列出的 `active-legal` 条目或目录，才是当前合法资料。" not in core_text:
        errors.append("legal-core-map does not declare map-only legality")
    if str(WORKSPACE_ROOT / "memory" / "kb" / "global" / "workbot-memory-system.md") not in core_text:
        errors.append("legal-core-map does not anchor the new memory system core")
    if "round-" in core_text or "waves/" in core_text:
        errors.append("legal-core-map still references transition round files")
    if "incoming-raw" not in registry_text or "compatibility-only" not in registry_text:
        errors.append("ingestion-registry-map does not classify raw and compatibility-only scopes")
    if "`absorbed`" not in registry_text or "`retired`" not in registry_text:
        errors.append("ingestion-registry-map does not define absorbed and retired statuses")
    if "同次 `git commit` 提交后才生效" not in registry_text:
        errors.append("ingestion-registry-map does not declare the future registration git-commit gate")
    if "未经过唯一真相系统清洗" not in governance_text:
        errors.append("project-map governance does not declare the legality cleaning rule")
    if "只有地图中被明确标为 `active-legal` 的条目或目录，才授予合法性。" not in governance_text:
        errors.append("project-map governance does not declare that the map grants legality")
    if "未完成同次 `git commit` 的目录登记，不得视为生效。" not in governance_text:
        errors.append("project-map governance does not declare the future atomic registration git-commit rule")
    if "按 wave 推进" in governance_text or "round-" in governance_text:
        errors.append("project-map governance still references transition wave files")
    return errors


def validate_unique_legal_system_contract() -> list[str]:
    errors: list[str] = []
    workspace_index = read_text_if_exists(WORKSPACE_ROOT / "INDEX.md")
    docs_index = read_text_if_exists(WORKSPACE_ROOT / "memory" / "docs" / "INDEX.md")
    overview_doc = read_text_if_exists(WORKSPACE_ROOT / "memory" / "docs" / "记忆系统全景文档.md")
    global_index = read_text_if_exists(WORKSPACE_ROOT / "memory" / "kb" / "global" / "INDEX.md")
    core_text = read_text_if_exists(PROJECT_MAP_FILES[1])
    registry_text = read_text_if_exists(PROJECT_MAP_FILES[2])
    hook_contract = read_text_if_exists(WORKSPACE_ROOT / "memory" / "kb" / "global" / "workbot-hook-contract.md")

    if "project-map/INDEX.md" not in workspace_index:
        errors.append("workspace index does not load the project-map entry")
    if "只有被地图标为 `active-legal` 的条目或目录，才是合法资料；仅进入登记册不授予合法性。" not in workspace_index:
        errors.append("workspace index does not declare active-legal map-only legality")
    if "目录登记和目录状态迁移必须与相关文件同次 `git commit` 才生效。" not in workspace_index:
        errors.append("workspace index does not declare the future registration git-commit rule")
    if "memory/kb/global/workbot-truth-model.md" not in workspace_index:
        errors.append("workspace index does not reference the truth model canonical")
    if "project-map/INDEX.md" not in overview_doc:
        errors.append("overview doc does not reference the project-map entry")
    if "incoming-raw" not in docs_index or "未被地图明确吸收" not in docs_index:
        errors.append("docs index does not demote docs subtrees to project-map controlled raw material")
    if "Non-Legal Material" not in global_index or "ingestion-registry-map.md" not in global_index:
        errors.append("global index does not demote non-local-canonical files into the legality registry")
    if "workbot-truth-model.md" not in global_index:
        errors.append("global index does not register the truth model canonical")
    for marker in LEGAL_CORE_MARKERS:
        if marker not in core_text:
            errors.append(f"legal-core-map is missing legal core marker: {marker}")
    for scope in REQUIRED_REGISTRY_SCOPES:
        if scope not in registry_text:
            errors.append(f"ingestion-registry-map is missing scope: {scope}")
    if "gateway 只承认 `project-map/` 中被明确标为 `active-legal` 的条目或目录是合法上下文来源。" not in hook_contract:
        errors.append("hook contract does not declare map-only legal context sources")
    if "未完成提交的登记不得生效" not in hook_contract:
        errors.append("hook contract does not declare the future registration git-commit gate")
    return errors


def decision_refs_for_scope(project_scope: str) -> list[str]:
    refs = DEFAULT_DECISION_REFS + PROJECT_DECISION_REFS.get(project_scope, [])
    return existing_paths(refs)


def lesson_refs_for_scope(project_scope: str) -> list[str]:
    refs = DEFAULT_LESSON_REFS + PROJECT_LESSON_REFS.get(project_scope, [])
    return existing_paths(refs)


def docs_refs_for_scope(project_scope: str) -> list[str]:
    refs = PROJECT_DOC_REFS.get(project_scope, [])
    return existing_paths(refs)


def truth_basis_for_scope(project_scope: str) -> dict[str, Any]:
    project_file = PROJECT_CANONICAL[project_scope]
    truth_basis_refs = [str(path) for path in GLOBAL_CANONICAL] + [str(project_file)]
    errors: list[str] = []
    for path in GLOBAL_CANONICAL:
        errors.extend(truth_basis_errors_for(path))
    project_sections = truth_basis_sections_for(project_file) if project_file.exists() else {
        "source_refs": [],
        "authority_refs": [],
        "evidence_refs": [],
        "conflict_status": [],
    }
    errors.extend(truth_basis_errors_for(project_file))
    return {
        "policy": "source-authority-evidence-conflict",
        "refs": truth_basis_refs,
        "global_refs": [str(path) for path in GLOBAL_CANONICAL],
        "project_ref": str(project_file),
        "source_refs": project_sections["source_refs"],
        "authority_refs": project_sections["authority_refs"],
        "evidence_refs": project_sections["evidence_refs"],
        "conflict_status": project_sections["conflict_status"],
        "errors": errors,
        "validation": "pass" if not errors else "fail",
    }


def write_targets() -> dict[str, Any]:
    today_log = WORKSPACE_ROOT / "memory" / "log" / f"{datetime.now().date().isoformat()}.md"
    return {
        "fact": str(today_log),
        "global_canonical": str(WORKSPACE_ROOT / "memory" / "kb" / "global"),
        "project_canonical": str(WORKSPACE_ROOT / "memory" / "kb" / "projects"),
        "decision": str(WORKSPACE_ROOT / "memory" / "kb" / "decisions"),
        "lesson": str(WORKSPACE_ROOT / "memory" / "kb" / "lessons"),
        "docs": str(WORKSPACE_ROOT / "memory" / "docs"),
        "action": str(WORKSPACE_ROOT / "memory" / "inbox.md"),
        "project_runtime": str(WORKSPACE_ROOT / "projects"),
        "artifacts": str(WORKSPACE_ROOT / "artifacts"),
        "system_error": str(ERROR_LOG),
        "invalid_memory": str(WORKSPACE_ROOT / "memory" / "archive" / "invalid"),
        "kb_policy": {
            "mode": "read-first-CRUD",
            "overwrite_allowed": False,
            "conflict_strategy": "preserve-and-escalate",
        },
    }


def resolve_route_target(kind: str) -> str:
    targets = write_targets()
    route_map = {
        "fact": targets["fact"],
        "global-rule": str(WORKSPACE_ROOT / "memory" / "kb" / "global" / "workbot-memory-routing.md"),
        "source-material": str(WORKSPACE_ROOT / "memory" / "docs" / "references"),
        "project-runtime": str(PROJECT_RUNTIME_ROOT["AEdu"]),
        "system-error": targets["system_error"],
        "invalid-memory": targets["invalid_memory"],
    }
    try:
        return str(route_map[kind])
    except KeyError as exc:
        raise ValueError(f"unsupported route kind: {kind}") from exc


def build_context_package(host: str, event: str, payload: dict[str, Any]) -> dict[str, Any]:
    cwd = discover_cwd(payload)
    project_scope = determine_project_scope(cwd)
    missing_paths = [str(path) for path in REQUIRED_CANONICAL if not path.exists()]
    project_map_errors = validate_project_map_files()
    contract_errors = validate_unique_legal_system_contract()
    governance_tuple_errors = governance_frozen_tuple_blocker_errors() if project_scope == "AEdu" else []
    event_contract_errors = event_contract_blocker_errors() if project_scope == "AEdu" else []
    registration_commit_gate = git_registration_probe(event, payload)
    project_file = PROJECT_CANONICAL[project_scope]
    if not project_file.exists():
        missing_paths.append(str(project_file))

    decisions = decision_refs_for_scope(project_scope)
    lessons = lesson_refs_for_scope(project_scope)
    docs_refs = docs_refs_for_scope(project_scope)
    truth_basis = truth_basis_for_scope(project_scope)
    truth_basis_refs = truth_basis["refs"]
    truth_basis_errors = list(truth_basis["errors"])
    reads = [
        str(WORKSPACE_ROOT / "NOW.md"),
        *project_map_refs(),
        str(WORKSPACE_ROOT / "memory" / "kb" / "INDEX.md"),
        str(WORKSPACE_ROOT / "memory" / "docs" / "INDEX.md"),
        *truth_basis_refs,
        *decisions,
        *lessons,
        *docs_refs,
    ]
    read_set = set(reads)
    truth_basis_set = set(truth_basis_refs)
    if not truth_basis_set.issubset(read_set):
        truth_basis_errors.append("allowed_reads does not cover all truth basis refs")
    if set(decisions) & truth_basis_set:
        truth_basis_errors.append("decision refs overlap with truth basis refs")
    if set(lessons) & truth_basis_set:
        truth_basis_errors.append("lesson refs overlap with truth basis refs")
    if set(docs_refs) & truth_basis_set:
        truth_basis_errors.append("docs refs overlap with truth basis refs")
    blocker_errors = [*governance_tuple_errors, *event_contract_errors]
    status = (
        "ok"
        if not missing_paths and not project_map_errors and not contract_errors and not truth_basis_errors and not blocker_errors
        else "degraded"
    )
    project_truth_status = "truth-ready" if truth_basis["validation"] == "pass" and not truth_basis_errors else "truth-incomplete"
    package = {
        "schema_version": "wb-hook-v2",
        "generated_at": now_iso(),
        "host": host,
        "event": event,
        "repo_root": str(REPO_ROOT),
        "workspace_root": str(WORKSPACE_ROOT),
        "cwd": str(cwd),
        "project_scope": project_scope,
        "status": status,
        "missing_paths": missing_paths,
        "validation_errors": [*project_map_errors, *contract_errors, *truth_basis_errors, *blocker_errors],
        "system_context": {
            "boot_entry": str(WORKSPACE_ROOT / "INDEX.md"),
            "state_entry": str(WORKSPACE_ROOT / "NOW.md"),
            "state_summary": extract_excerpt(WORKSPACE_ROOT / "NOW.md"),
            "project_map_refs": project_map_refs(),
            "project_map_validation": "pass" if not project_map_errors else "fail",
            "legality_contract_validation": "pass" if not contract_errors else "fail",
            "legality_source_policy": LEGALITY_SOURCE_POLICY,
            "registration_commit_policy": REGISTRATION_COMMIT_POLICY,
            "registration_commit_gate": registration_commit_gate,
            "global_canonical": [str(path) for path in GLOBAL_CANONICAL],
            "truth_basis_policy": truth_basis["policy"],
            "truth_basis_validation": truth_basis["validation"] if not truth_basis_errors else "fail",
            "truth_basis_refs": truth_basis_refs,
            "truth_basis_errors": truth_basis_errors,
            "governance_frozen_tuple_validation": "pass" if not governance_tuple_errors else "fail",
            "governance_frozen_tuple_errors": governance_tuple_errors,
            "event_contract_alignment_validation": "pass" if not event_contract_errors else "fail",
            "event_contract_alignment_errors": event_contract_errors,
            "decision_refs": decisions,
            "lesson_refs": lessons,
            "docs_refs": docs_refs,
            "hook_contract": str(WORKSPACE_ROOT / "memory" / "kb" / "global" / "workbot-hook-contract.md"),
        },
        "project_context": {
            "scope": project_scope,
            "canonical": str(project_file),
            "truth_basis_canonical": truth_basis["project_ref"],
            "truth_status": project_truth_status,
            "runtime_root": str(PROJECT_RUNTIME_ROOT[project_scope]),
            "source_refs": truth_basis["source_refs"],
            "authority_refs": truth_basis["authority_refs"],
            "evidence_refs": truth_basis["evidence_refs"],
            "conflict_status": truth_basis["conflict_status"],
        },
        "task_context": {
            "event": event,
            "task_ref": str(payload.get("task_ref") or f"{project_scope}:{event}"),
            "session_id": str(payload.get("session_id") or ""),
            "surface_id": os.environ.get("CMUX_SURFACE_ID", ""),
            "workspace_id": os.environ.get("CMUX_WORKSPACE_ID", ""),
            "payload_keys": sorted(payload.keys()),
        },
        "allowed_reads": reads,
        "allowed_writes": write_targets(),
        "evidence_refs": [
            *project_map_refs(),
            str(WORKSPACE_ROOT / "memory" / "kb" / "global" / "workbot-memory-system.md"),
            str(WORKSPACE_ROOT / "memory" / "kb" / "global" / "workbot-memory-routing.md"),
            str(WORKSPACE_ROOT / "memory" / "kb" / "global" / "workbot-hook-contract.md"),
            str(PROJECT_MAP_GOVERNANCE),
            str(EVENT_LOG),
        ],
    }
    return package


def ensure_artifact_dirs() -> None:
    CONTEXT_ROOT.mkdir(parents=True, exist_ok=True)


def append_error_log(component: str, message: str, context: dict[str, Any]) -> None:
    ERROR_LOG.parent.mkdir(parents=True, exist_ok=True)
    rendered = json.dumps(context, ensure_ascii=False, sort_keys=True)
    with ERROR_LOG.open("a", encoding="utf-8") as handle:
        handle.write(f"[{now_iso()}] [{component}] [error] {message} | context={rendered}\n")


def write_artifacts(package: dict[str, Any]) -> dict[str, str]:
    ensure_artifact_dirs()
    timestamp = datetime.now().strftime("%Y%m%dT%H%M%S%f")
    snapshot_path = CONTEXT_ROOT / f"{timestamp}-{package['host']}-{package['event']}.json"
    suffix = 1
    while snapshot_path.exists():
        snapshot_path = CONTEXT_ROOT / f"{timestamp}-{suffix:02d}-{package['host']}-{package['event']}.json"
        suffix += 1
    latest_path = CONTEXT_ROOT / f"latest-{package['host']}-{package['event']}.json"
    package["artifact_refs"] = {
        "snapshot": str(snapshot_path),
        "latest": str(latest_path),
        "event_log": str(EVENT_LOG),
    }
    rendered = json.dumps(package, ensure_ascii=False, indent=2) + "\n"
    snapshot_path.write_text(rendered, encoding="utf-8")
    latest_path.write_text(rendered, encoding="utf-8")
    with EVENT_LOG.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(package, ensure_ascii=False) + "\n")
    return {"snapshot": str(snapshot_path), "latest": str(latest_path)}


def require_env(name: str) -> str:
    value = os.environ.get(name, "")
    if not value:
        raise RuntimeError(f"missing required env: {name}")
    return value


def canonicalize_cmux_refs(workspace_ref: str, surface_ref: str) -> tuple[str, str]:
    proc = subprocess.run(
        ["cmux", "identify", "--workspace", workspace_ref, "--surface", surface_ref],
        text=True,
        capture_output=True,
        check=False,
    )
    if proc.returncode != 0:
        return workspace_ref, surface_ref
    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return workspace_ref, surface_ref
    caller = payload.get("caller")
    if not isinstance(caller, dict):
        return workspace_ref, surface_ref
    return (
        str(caller.get("workspace_ref") or workspace_ref),
        str(caller.get("surface_ref") or surface_ref),
    )


def delegate_codex(event: str, raw_payload: str) -> subprocess.CompletedProcess[str]:
    if shutil.which("cmux") is None:
        raise RuntimeError("cmux not found in PATH")
    require_env("CMUX_SURFACE_ID")
    return subprocess.run(
        ["cmux", "codex-hook", event],
        input=raw_payload,
        text=True,
        capture_output=True,
        check=False,
    )


def delegate_claude(event: str, raw_payload: str, payload: dict[str, Any]) -> subprocess.CompletedProcess[str]:
    if shutil.which("cmux") is None:
        raise RuntimeError("cmux not found in PATH")
    workspace_ref = require_env("CMUX_WORKSPACE_ID")
    surface_ref = require_env("CMUX_SURFACE_ID")
    state_file = os.environ.get("CMUX_HOOK_STATE_FILE") or str(default_hook_state_path(REPO_ROOT))
    workspace_ref, surface_ref = canonicalize_cmux_refs(workspace_ref, surface_ref)
    record_hook_event(
        Path(state_file),
        event_name=event,
        workspace_ref=workspace_ref,
        surface_ref=surface_ref,
        payload=payload,
    )
    return subprocess.run(
        ["cmux", "claude-hook", event, "--workspace", workspace_ref, "--surface", surface_ref],
        input=raw_payload or "{}",
        text=True,
        capture_output=True,
        check=False,
    )


def main() -> int:
    args = parse_args()
    raw_payload = sys.stdin.read()
    payload = read_payload(raw_payload)
    cwd = discover_cwd(payload)

    if should_noop_for_external_context(payload):
        return noop_for_external_host(args.host)

    package = build_context_package(args.host, args.event, payload)
    artifact_paths = write_artifacts(package)

    if package["status"] != "ok":
        append_error_log(
            "memory-hook-gateway",
            "missing canonical prerequisites or project-map validation failed",
            {
                "host": args.host,
                "event": args.event,
                "missing_paths": package["missing_paths"],
                "validation_errors": package.get("validation_errors", []),
            },
        )
        print(
            "[memory-hook-gateway] degraded: "
            f"missing canonical paths: {', '.join(package['missing_paths']) or 'none'}; "
            f"project-map errors: {', '.join(package.get('validation_errors', [])) or 'none'}",
            file=sys.stderr,
        )
        return 1

    if args.no_delegate:
        sys.stdout.write(json.dumps(package, ensure_ascii=False) + "\n")
        return 0

    try:
        proc = delegate_codex(args.event, raw_payload) if args.host == "codex" else delegate_claude(args.event, raw_payload, payload)
    except RuntimeError as exc:
        append_error_log(
            "memory-hook-gateway",
            "delegate preflight failed",
            {"host": args.host, "event": args.event, "error": str(exc), "cwd": str(cwd)},
        )
        print(f"[memory-hook-gateway] {exc}", file=sys.stderr)
        return 1

    if proc.returncode != 0:
        append_error_log(
            "memory-hook-gateway",
            "delegate command failed",
            {
                "host": args.host,
                "event": args.event,
                "returncode": proc.returncode,
                "stderr": proc.stderr,
                "stdout": proc.stdout,
                "artifact_latest": artifact_paths["latest"],
            },
        )

    if proc.stdout:
        sys.stdout.write(proc.stdout)
    elif args.host == "codex":
        sys.stdout.write("{}\n")
    if proc.stderr:
        sys.stderr.write(proc.stderr)
    return proc.returncode


if __name__ == "__main__":
    raise SystemExit(main())
