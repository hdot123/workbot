#!/usr/bin/env python3
from __future__ import annotations

import json
import shlex
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent
GLOBAL_CMUX_SCRIPTS = Path("/Users/busiji/.agents/skills/cmux/scripts")
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(GLOBAL_CMUX_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(GLOBAL_CMUX_SCRIPTS))

import watch_cmux_assignments  # noqa: E402
from cmux_hook_state import write_assignment_watcher_manifest  # noqa: E402


def _runtime_dir(tmp_path: Path) -> Path:
    runtime_dir = tmp_path / "workspace" / "artifacts" / "cmux-runtime"
    runtime_dir.mkdir(parents=True)
    return runtime_dir


def _build_task_source_ref(*, assignment_id: str, cycle_id: str, deliverable_path: str, evidence_path: str, status: str) -> dict[str, str]:
    return {
        "schema_version": "wb-current-task-source-v1",
        "task_type": "cmux",
        "task_source_id": f"cmux:{assignment_id}",
        "deliverable_path": deliverable_path,
        "evidence_path": evidence_path,
        "status": status,
        "assignment_id": assignment_id,
        "cycle_id": cycle_id,
        "acceptance_owner": "main-thread",
    }


def _write_assignment_and_manifest(
    tmp_path: Path,
    *,
    current_assignment_id: str,
    manifest_assignment_id: str,
    launch_assignment_id: str,
    command_assignment_id: str,
) -> Path:
    runtime_dir = _runtime_dir(tmp_path)
    assignment_file = runtime_dir / "cmux-assignment.json"
    runtime_settings_path = runtime_dir / "runtime-settings-pm-bot.json"
    runtime_settings_path.write_text("{}", encoding="utf-8")
    task_source_ref = _build_task_source_ref(
        assignment_id=current_assignment_id,
        cycle_id="cycle-001",
        deliverable_path="/Users/busiji/workbot/workspace/memory/tmp/pm-current-summary.json",
        evidence_path=str(assignment_file),
        status="active",
    )
    current_runtime_identity = {
        "assignment_id": current_assignment_id,
        "lane_identity": "pm-bot",
        "lane_justification": "main-thread dispatch for current source",
        "project_pack": {"project_scope": "workbot", "ownership": "main-thread", "project_kind": "repo"},
        "assignment_class": "已批准执行方案",
        "tool_profile_id": "pm-current",
        "tool_profile": {
            "tool_profile_id": "pm-current",
            "allowed_tools": ["Read", "Bash"],
            "forbidden_tools": [],
            "allowed_write_target": "/Users/busiji/workbot/workspace",
            "error_route": "report blocker in terminal and stop",
        },
        "permission_mode": "default",
        "session_class": "formal_cmux_worker",
        "workspace_root": "/Users/busiji/workbot",
        "bot_name": "pm-bot",
        "logical_target": "pm-bot",
        "status": "ACTIVE",
        "audit_round_1_owner": "rea-bot",
    }
    assignment_payload = {
        "runtime": "cmux",
        "ready": True,
        "dispatch_ready": True,
        "workspace_name": "workbot",
        "workspace_ref": "workspace:1",
        "runtime_status": "running",
        "active_assignment_count": 1,
        "updated_at": "2026-04-21T10:00:00+0800",
        "cycle_id": "cycle-001",
        "current_task_sources": [task_source_ref],
        "assignments": [
            {
                "logical_target": "pm-bot",
                "bot_name": "pm-bot",
                "assignment_id": current_assignment_id,
                "title": "Launch gate regression",
                "goal": "reject stale launch task source",
                "task_kind": "assignment",
                "lane_identity": "pm-bot",
                "lane_justification": "main-thread dispatch for current source",
                "worker_role": "pm",
                "workspace_root": "/Users/busiji/workbot",
                "project_scope": "workbot",
                "project_pack": {"project_scope": "workbot", "ownership": "main-thread", "project_kind": "repo"},
                "assignment_class": "已批准执行方案",
                "assignment_contract": {
                    "assignment_class": "已批准执行方案",
                    "lane_justification": "main-thread dispatch for current source",
                    "target_object": "launch gate",
                    "scope_boundary": "entry only",
                    "deliverable": "/Users/busiji/workbot/workspace/memory/tmp/pm-current-summary.json",
                    "verification_goal": "fail closed on stale launch source",
                    "truth_basis_refs": ["/Users/busiji/workbot/AGENTS.md"],
                },
                "target_object": "launch gate",
                "scope_boundary": "entry only",
                "deliverable": "/Users/busiji/workbot/workspace/memory/tmp/pm-current-summary.json",
                "verification_goal": "fail closed on stale launch source",
                "truth_basis_refs": ["/Users/busiji/workbot/AGENTS.md"],
                "tool_profile_id": "pm-current",
                "tool_profile": current_runtime_identity["tool_profile"],
                "allowed_tools": ["Read", "Bash"],
                "forbidden_tools": [],
                "allowed_write_target": "/Users/busiji/workbot/workspace",
                "error_route": "report blocker in terminal and stop",
                "permission_mode": "default",
                "dispatch_owner": "codex",
                "conflict_status": "resolved",
                "ownership": "main-thread",
                "project_kind": "repo",
                "official_source_links": [],
                "local_verification_basis": [],
                "missing_validated_deltas": [],
                "rejected_or_stale_points": [],
                "promotion_target": "",
                "webpage_fact_required": False,
                "approved_retrieval_path": "",
                "memory_pack_refs": [],
                "audit_round_1_owner": "rea-bot",
                "audit_round_1_status": "pending",
                "audit_round_2_owner": "codex",
                "audit_round_2_status": "pending",
                "task_text": "Continue current assignment",
                "continue_text": "Continue current assignment",
                "status": "ACTIVE",
                "session_class": "formal_cmux_worker",
                "pane_ref": "pane:1",
                "surface_ref": "surface:1",
                "workspace_ref": "workspace:1",
                "runtime_status": "running",
                "allow_intervene": True,
                "runtime_identity": current_runtime_identity,
                "effective_permission_mode": "default",
                "dispatch_ready": True,
                "task_source_ref": task_source_ref,
            }
        ],
    }
    assignment_file.write_text(json.dumps(assignment_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    launch_identity = dict(current_runtime_identity)
    launch_identity["assignment_id"] = launch_assignment_id
    command_identity = dict(current_runtime_identity)
    command_identity["assignment_id"] = command_assignment_id
    manifest_payload = {
        "bot_name": "pm-bot",
        "assignment_id": manifest_assignment_id,
        "lane_identity": "pm-bot",
        "lane_justification": "main-thread dispatch for current source",
        "logical_target": "pm-bot",
        "workspace_ref": "workspace:1",
        "surface_ref": "surface:1",
        "permission_mode": "default",
        "allowed_tools": ["Read", "Bash"],
        "forbidden_tools": [],
        "runtime_settings_path": str(runtime_settings_path),
        "external_mcp_tokens": [],
        "resolved_mcp_servers": [],
        "mcp_config": {},
        "derived_identity": dict(current_runtime_identity),
        "identity_source": "assignment_top_level_sync",
        "launch_assignment_id": launch_assignment_id,
        "launch_lane_identity": "pm-bot",
        "launch_lane_justification": "main-thread dispatch for current source",
        "launch_logical_target": "pm-bot",
        "launch_workspace_ref": "workspace:1",
        "launch_surface_ref": "surface:1",
        "launch_permission_mode": "default",
        "launch_derived_identity": launch_identity,
        "launch_identity_source": "assignment_top_level_at_bootstrap",
        "launch_recorded_at": "2026-04-21T10:00:00+0800",
        "launch_command": " ".join(
            [
                f"CMUX_DERIVED_IDENTITY_JSON={shlex.quote(json.dumps(command_identity, ensure_ascii=False))}",
                "claude",
                "--agent",
                "pm-bot",
            ]
        ),
    }
    (runtime_dir / "runtime-launch-manifest-pm-bot.json").write_text(
        json.dumps(manifest_payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return assignment_file


def test_self_reap_watcher_artifacts_removes_owned_pid_and_manifest(tmp_path: Path) -> None:
    runtime_dir = _runtime_dir(tmp_path)
    assignment_file = runtime_dir / "cmux-assignment.json"
    assignment_file.write_text(json.dumps({"assignments": []}, ensure_ascii=False), encoding="utf-8")
    pid_file = runtime_dir / "watch_cmux_assignments.pid"
    pid_file.write_text(f"{123}\n", encoding="utf-8")
    write_assignment_watcher_manifest(
        tmp_path,
        pid=123,
        assignment_file=assignment_file,
        workspace_ref="workspace:1",
        runtime_mode="pm_only",
    )

    result = watch_cmux_assignments.self_reap_watcher_artifacts(str(assignment_file), expected_pid=123)

    assert result["removed_pid_file"] is True
    assert result["removed_manifest"] is True
    assert not pid_file.exists()
    assert not (runtime_dir / "watch_cmux_assignments.manifest.json").exists()


def test_self_reap_watcher_artifacts_keeps_foreign_pid_and_manifest(tmp_path: Path) -> None:
    runtime_dir = _runtime_dir(tmp_path)
    assignment_file = runtime_dir / "cmux-assignment.json"
    assignment_file.write_text(json.dumps({"assignments": []}, ensure_ascii=False), encoding="utf-8")
    pid_file = runtime_dir / "watch_cmux_assignments.pid"
    pid_file.write_text(f"{456}\n", encoding="utf-8")
    write_assignment_watcher_manifest(
        tmp_path,
        pid=456,
        assignment_file=assignment_file,
        workspace_ref="workspace:1",
        runtime_mode="pm_only",
    )

    result = watch_cmux_assignments.self_reap_watcher_artifacts(str(assignment_file), expected_pid=123)

    assert result["removed_pid_file"] is False
    assert result["removed_manifest"] is False
    assert pid_file.exists()
    assert (runtime_dir / "watch_cmux_assignments.manifest.json").exists()


def test_watch_main_once_self_reaps_owned_artifacts_on_no_active_assignments(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    runtime_dir = _runtime_dir(tmp_path)
    assignment_file = runtime_dir / "cmux-assignment.json"
    assignment_file.write_text(json.dumps({"assignments": []}, ensure_ascii=False), encoding="utf-8")
    hook_state_file = runtime_dir / "hook-state.json"
    hook_state_file.write_text("{}", encoding="utf-8")
    consumer_state_file = runtime_dir / "consumer.json"
    pid_file = runtime_dir / "watch_cmux_assignments.pid"
    current_pid = 78901
    pid_file.write_text(f"{current_pid}\n", encoding="utf-8")
    write_assignment_watcher_manifest(
        tmp_path,
        pid=current_pid,
        assignment_file=assignment_file,
        workspace_ref="workspace:1",
        runtime_mode="pm_only",
    )

    monkeypatch.setattr(
        watch_cmux_assignments,
        "parse_args",
        lambda: SimpleNamespace(
            assignment_file=str(assignment_file),
            task_file=None,
            task_text=None,
            consumer_state_file=str(consumer_state_file),
            hook_state_file=str(hook_state_file),
            once=True,
            exit_when_idle=False,
            interval=0.0,
        ),
    )
    monkeypatch.setattr(watch_cmux_assignments, "install_shutdown_signal_handlers", lambda: None)
    monkeypatch.setattr(watch_cmux_assignments.os, "getpid", lambda: current_pid)

    rc = watch_cmux_assignments.main()

    assert rc == 0
    assert not pid_file.exists()
    assert not (runtime_dir / "watch_cmux_assignments.manifest.json").exists()


def test_load_assignment_file_accepts_matching_launch_task_source_manifest(tmp_path: Path) -> None:
    assignment_file = _write_assignment_and_manifest(
        tmp_path,
        current_assignment_id="PM-CURRENT-101",
        manifest_assignment_id="PM-CURRENT-101",
        launch_assignment_id="PM-CURRENT-101",
        command_assignment_id="PM-CURRENT-101",
    )

    assignments = watch_cmux_assignments.load_assignment_file(str(assignment_file))

    assert [assignment.assignment_id for assignment in assignments] == ["PM-CURRENT-101"]


def test_load_assignment_file_blocks_stale_launch_assignment_residue(tmp_path: Path) -> None:
    assignment_file = _write_assignment_and_manifest(
        tmp_path,
        current_assignment_id="PM-CURRENT-102",
        manifest_assignment_id="PM-CURRENT-102",
        launch_assignment_id="PM-OLD-102",
        command_assignment_id="PM-OLD-102",
    )

    with pytest.raises(ValueError, match="launch task-source gate blocked"):
        watch_cmux_assignments.load_assignment_file(str(assignment_file))


def test_load_assignment_file_blocks_stale_launch_command_only(tmp_path: Path) -> None:
    assignment_file = _write_assignment_and_manifest(
        tmp_path,
        current_assignment_id="PM-CURRENT-103",
        manifest_assignment_id="PM-CURRENT-103",
        launch_assignment_id="PM-CURRENT-103",
        command_assignment_id="PM-OLD-103",
    )

    with pytest.raises(ValueError, match="launch task-source gate blocked"):
        watch_cmux_assignments.load_assignment_file(str(assignment_file))


def test_validate_active_assignments_ready_rejects_non_formal_session_class() -> None:
    assignment = watch_cmux_assignments.WatchAssignment(
        logical_target="pm-bot",
        workspace_ref="workspace:1",
        pane_ref="pane:1",
        surface_ref="surface:1",
        assignment_id="pm-1",
        bot_name="pm-bot",
        title="Phase 0",
        goal="Finish scope freeze",
        task_kind="assignment",
        audit_round_1_owner="rea-bot",
        audit_round_1_status="pending",
        audit_round_2_owner="codex",
        audit_round_2_status="pending",
        status="ACTIVE",
        allow_intervene=True,
        task_text="Do the work",
        session_class="external_session",
        identity_payload={
            "lane_identity": "pm-bot",
            "lane_justification": "Scope and requirement lane",
            "workspace_root": "/Users/busiji/workbot",
            "project_scope": "workbot",
            "assignment_class": "已批准执行方案",
            "target_object": "Project #8 runtime tail items",
            "scope_boundary": "Project #8 control plane only",
            "deliverable": "Watcher and session classification patch",
            "verification_goal": "Targeted regression tests pass",
            "truth_basis_refs": ["/Users/busiji/workbot/AGENTS.md"],
            "tool_profile_id": "phase0",
            "allowed_tools": ["Read", "Bash"],
            "forbidden_tools": [],
            "allowed_write_target": "/Users/busiji/workbot",
            "worker_role": "pm",
            "permission_mode": "default",
            "dispatch_owner": "codex",
            "conflict_status": "resolved",
            "project_pack": {"project_scope": "workbot", "ownership": "hdot123", "project_kind": "repo"},
        },
    )

    with pytest.raises(ValueError, match="session_class=formal_cmux_worker"):
        watch_cmux_assignments.validate_active_assignments_ready([assignment])


def test_validate_active_assignments_ready_rejects_dispatch_ready_false() -> None:
    assignment = watch_cmux_assignments.WatchAssignment(
        logical_target="pm-bot",
        workspace_ref="workspace:1",
        pane_ref="pane:1",
        surface_ref="surface:1",
        assignment_id="pm-1",
        bot_name="pm-bot",
        title="Phase 0",
        goal="Finish scope freeze",
        task_kind="assignment",
        audit_round_1_owner="rea-bot",
        audit_round_1_status="pending",
        audit_round_2_owner="codex",
        audit_round_2_status="pending",
        status="ACTIVE",
        allow_intervene=True,
        dispatch_ready=False,
        task_text="Do the work",
        session_class="formal_cmux_worker",
        identity_payload={
            "lane_identity": "pm-bot",
            "lane_justification": "Scope and requirement lane",
            "workspace_root": "/Users/busiji/workbot",
            "project_scope": "workbot",
            "assignment_class": "已批准执行方案",
            "target_object": "Project #10 issue #16",
            "scope_boundary": "Phase 0A only",
            "deliverable": "Scope-freeze packet",
            "verification_goal": "Acceptance checklist is fully covered",
            "truth_basis_refs": ["/Users/busiji/workbot/AGENTS.md"],
            "tool_profile_id": "phase0",
            "allowed_tools": ["Read", "Bash"],
            "forbidden_tools": [],
            "allowed_write_target": "/Users/busiji/workbot",
            "worker_role": "pm",
            "permission_mode": "default",
            "dispatch_owner": "codex",
            "conflict_status": "resolved",
            "project_pack": {"project_scope": "workbot", "ownership": "hdot123", "project_kind": "repo"},
        },
    )

    with pytest.raises(ValueError, match="dispatch_ready=true"):
        watch_cmux_assignments.validate_active_assignments_ready([assignment])
