#!/usr/bin/env python3
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

repo_root = Path(__file__).resolve().parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from workspace.tools.memory_hook_impls import ArtifactSinkImpl


def _base_package() -> dict[str, object]:
    return {
        "status": "ok",
        "host": "codex",
        "event": "prompt-submit",
        "project_scope": "workbot",
        "generated_at": "2026-04-18T10:00:00+08:00",
        "missing_paths": [],
        "validation_errors": [],
        "rules_read": ["/Users/busiji/workbot/AGENTS.md"],
        "legal_basis": ["/Users/busiji/workbot/workspace/memory/docs/INDEX.md"],
        "truth_basis": ["/Users/busiji/workbot/workspace/memory/kb/projects/workbot.md"],
        "system_context": {
            "project_map_validation": "pass",
            "legality_contract_validation": "pass",
            "truth_basis_validation": "pass",
            "core_provider": "external-core",
            "core_provider_requested": "external-core",
            "warnings": ["uses shared payload compaction"],
            "truth_basis_refs": [
                "/Users/busiji/workbot/workspace/memory/kb/projects/workbot.md",
                "/Users/busiji/workbot/workspace/memory/kb/decisions/2026-03-25-workbot-project-agents-and-runtime-surfaces.md",
            ],
            "decision_refs": [
                "/Users/busiji/workbot/workspace/memory/kb/decisions/2026-03-25-workbot-project-agents-and-runtime-surfaces.md"
            ],
            "lesson_refs": [
                "/Users/busiji/workbot/workspace/memory/kb/lessons/example.md"
            ],
            "docs_refs": [
                "/Users/busiji/workbot/workspace/memory/docs/记忆系统全景文档.md"
            ],
            "registration_commit_gate": {
                "status": "active",
                "enforcement_result": "pass",
                "triggered_on_current_event": False,
                "scope_clean": True,
                "would_pass_if_enforced": True,
            },
            "nested_context": {
                "surfaces": ["pm-bot", "dev-bot", "qa-bot"],
                "facts": {"formal_session": "formal-session"},
            },
        },
        "project_context": {
            "scope": "workbot",
            "truth_basis_canonical": "/Users/busiji/workbot/workspace/memory/kb/projects/workbot.md",
            "truth_status": "ok",
            "runtime_root": "/Users/busiji/workbot/workspace/projects",
            "conflict_status": "clear",
            "source_refs": [
                "/Users/busiji/workbot/AGENTS.md",
                "/Users/busiji/workbot/workspace/memory/kb/projects/workbot.md",
            ],
            "authority_refs": [
                "/Users/busiji/workbot/workspace/memory/kb/decisions/2026-03-25-workbot-project-agents-and-runtime-surfaces.md"
            ],
            "evidence_refs": [
                "/Users/busiji/workbot/workspace/log/memory-hook/contexts/latest-codex-prompt-submit.json",
                "/Users/busiji/workbot/workspace/log/memory-hook/events.jsonl",
            ],
        },
        "allowed_reads": [
            "/Users/busiji/workbot/AGENTS.md",
            "/Users/busiji/workbot/workspace/memory/kb/projects/workbot.md",
            "/Users/busiji/workbot/workspace/memory/kb/decisions/2026-03-25-workbot-project-agents-and-runtime-surfaces.md",
            "/Users/busiji/workbot/workspace/memory/docs/记忆系统全景文档.md",
        ],
        "allowed_writes": {
            "artifacts": [
                "/Users/busiji/workbot/workspace/log/memory-hook/contexts",
                "/Users/busiji/workbot/workspace/log/memory-hook/shared",
            ],
            "kb_policy": {
                "mode": "append",
                "targets": ["decisions", "lessons"],
            },
        },
        "evidence_refs": [
            "/Users/busiji/workbot/workspace/log/memory-hook/contexts/latest-codex-prompt-submit.json",
            "/Users/busiji/workbot/workspace/log/memory-hook/events.jsonl",
            "/Users/busiji/workbot/workspace/memory/kb/projects/workbot.md",
        ],
    }


def _load_json(path: str | Path) -> dict[str, object]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _load_jsonl(path: str | Path) -> list[dict[str, object]]:
    return [
        json.loads(line)
        for line in Path(path).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def test_write_compacts_heavy_payload_into_shared_artifact(tmp_path: Path) -> None:
    context_root = tmp_path / "log" / "memory-hook" / "contexts"
    event_log = tmp_path / "log" / "memory-hook" / "events.jsonl"
    sink = ArtifactSinkImpl(context_root, event_log)

    package = _base_package()
    artifact_paths = sink.write(package)

    snapshot_doc = _load_json(artifact_paths["snapshot"])
    latest_doc = _load_json(artifact_paths["latest"])
    event_docs = _load_jsonl(event_log)

    assert len(event_docs) == 1
    assert snapshot_doc == latest_doc == event_docs[0]

    shared_ref = snapshot_doc["artifact_refs"]["shared_payload"]
    shared_doc = _load_json(shared_ref["path"])
    raw_size = len(json.dumps(package, ensure_ascii=False, separators=(",", ":")))
    event_size = len(Path(event_log).read_text(encoding="utf-8").splitlines()[0])

    assert shared_ref["schema_version"] == ArtifactSinkImpl.SHARED_PAYLOAD_SCHEMA_VERSION
    assert shared_doc["schema_version"] == ArtifactSinkImpl.SHARED_PAYLOAD_SCHEMA_VERSION
    assert shared_doc["digest"] == shared_ref["digest"]
    assert shared_doc["fields"] == list(ArtifactSinkImpl.HEAVY_PAYLOAD_KEYS)
    assert shared_doc["payload"]["system_context"] == package["system_context"]
    assert shared_doc["payload"]["project_context"] == package["project_context"]
    assert shared_doc["payload"]["allowed_reads"] == package["allowed_reads"]
    assert shared_doc["payload"]["allowed_writes"] == package["allowed_writes"]
    assert shared_doc["payload"]["evidence_refs"] == package["evidence_refs"]

    assert snapshot_doc["compaction"] == {
        "mode": "shared-payload-ref",
        "fields": list(ArtifactSinkImpl.HEAVY_PAYLOAD_KEYS),
        "digest": shared_ref["digest"],
    }
    assert snapshot_doc["system_context"]["core_provider"] == "external-core"
    assert snapshot_doc["project_context"]["scope"] == "workbot"
    assert snapshot_doc["allowed_reads"]["count"] == len(package["allowed_reads"])
    assert snapshot_doc["allowed_writes"]["keys"] == ["artifacts", "kb_policy"]
    assert snapshot_doc["evidence_refs"]["count"] == len(package["evidence_refs"])
    assert snapshot_doc["system_context"] != package["system_context"]
    assert snapshot_doc["project_context"] != package["project_context"]
    assert event_size < raw_size


def test_write_reuses_existing_shared_artifact_when_heavy_payload_is_unchanged(tmp_path: Path) -> None:
    context_root = tmp_path / "log" / "memory-hook" / "contexts"
    event_log = tmp_path / "log" / "memory-hook" / "events.jsonl"
    sink = ArtifactSinkImpl(context_root, event_log)

    first_package = _base_package()
    first_paths = sink.write(first_package)
    first_snapshot = _load_json(first_paths["snapshot"])
    first_shared_ref = first_snapshot["artifact_refs"]["shared_payload"]

    second_package = copy.deepcopy(_base_package())
    second_package["generated_at"] = "2026-04-18T10:05:00+08:00"
    second_package["validation_errors"] = ["non-heavy field changed"]
    second_paths = sink.write(second_package)
    second_snapshot = _load_json(second_paths["snapshot"])
    second_latest = _load_json(second_paths["latest"])
    event_docs = _load_jsonl(event_log)

    assert first_paths["snapshot"] != second_paths["snapshot"]
    assert first_shared_ref["path"] == second_snapshot["artifact_refs"]["shared_payload"]["path"]
    assert first_shared_ref["digest"] == second_snapshot["artifact_refs"]["shared_payload"]["digest"]
    assert second_latest["artifact_refs"]["shared_payload"] == second_snapshot["artifact_refs"]["shared_payload"]
    assert event_docs[0]["artifact_refs"]["shared_payload"] == event_docs[1]["artifact_refs"]["shared_payload"]
    assert len(list((context_root.parent / "shared").glob("*.json"))) == 1
