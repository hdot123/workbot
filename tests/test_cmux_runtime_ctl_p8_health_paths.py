from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

CMUX_SCRIPT_DIR = Path.home() / ".agents" / "skills" / "cmux" / "scripts"
CMUX_RUNTIME_CTL_PATH = CMUX_SCRIPT_DIR / "cmux_runtime_ctl.py"
BOOTSTRAP_PATH = CMUX_SCRIPT_DIR / "bootstrap_claude_runtime.py"


def load_cmux_runtime_ctl_module():
    if not CMUX_RUNTIME_CTL_PATH.exists():
        pytest.skip(f"global cmux runtime controller missing: {CMUX_RUNTIME_CTL_PATH}")
    if str(CMUX_SCRIPT_DIR) not in sys.path:
        sys.path.insert(0, str(CMUX_SCRIPT_DIR))
    spec = importlib.util.spec_from_file_location("cmux_runtime_ctl", CMUX_RUNTIME_CTL_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load module spec for {CMUX_RUNTIME_CTL_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_bootstrap_module():
    if not BOOTSTRAP_PATH.exists():
        pytest.skip(f"global cmux bootstrap script missing: {BOOTSTRAP_PATH}")
    if str(CMUX_SCRIPT_DIR) not in sys.path:
        sys.path.insert(0, str(CMUX_SCRIPT_DIR))
    spec = importlib.util.spec_from_file_location("bootstrap_claude_runtime", BOOTSTRAP_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load module spec for {BOOTSTRAP_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def fake_assignment(
    *,
    logical_target: str,
    bot_name: str,
    assignment_id: str,
    workspace_ref: str,
    pane_ref: str,
    surface_ref: str,
    status: str = "ACTIVE",
):
    return SimpleNamespace(
        logical_target=logical_target,
        bot_name=bot_name,
        assignment_id=assignment_id,
        workspace_ref=workspace_ref,
        pane_ref=pane_ref,
        surface_ref=surface_ref,
        status=status,
    )


def fake_snapshot(
    *,
    workspace_ref: str,
    pane_ref: str,
    surface_ref: str,
    surface_type: str,
    title: str,
    dead: bool,
):
    return SimpleNamespace(
        workspace_ref=workspace_ref,
        pane_ref=pane_ref,
        surface_ref=surface_ref,
        surface_type=surface_type,
        title=title,
        current_command="codex",
        current_path="/Users/busiji/workbot",
        dead=dead,
    )


def write_runtime_launch_manifest(
    runtime_dir: Path,
    *,
    bot_name: str,
    assignment_id: str,
    workspace_ref: str,
    surface_ref: str,
    pane_ref: str = "",
    logical_target: str | None = None,
) -> None:
    logical_target = logical_target or bot_name
    derived_identity = {
        "assignment_id": assignment_id,
        "lane_identity": bot_name,
        "logical_target": logical_target,
        "bot_name": bot_name,
        "workspace_ref": workspace_ref,
        "surface_ref": surface_ref,
        "pane_ref": pane_ref,
    }
    manifest = {
        "bot_name": bot_name,
        "assignment_id": assignment_id,
        "lane_identity": bot_name,
        "lane_justification": f"launch for {bot_name}",
        "logical_target": logical_target,
        "workspace_ref": workspace_ref,
        "surface_ref": surface_ref,
        "permission_mode": "default",
        "allowed_tools": ["Read", "Bash"],
        "forbidden_tools": [],
        "runtime_settings_path": "",
        "external_mcp_tokens": [],
        "resolved_mcp_servers": [],
        "mcp_config": {},
        "derived_identity": derived_identity,
        "identity_source": "assignment_top_level_at_bootstrap",
        "launch_assignment_id": assignment_id,
        "launch_lane_identity": bot_name,
        "launch_lane_justification": f"launch for {bot_name}",
        "launch_logical_target": logical_target,
        "launch_workspace_ref": workspace_ref,
        "launch_surface_ref": surface_ref,
        "launch_permission_mode": "default",
        "launch_derived_identity": derived_identity,
        "launch_identity_source": "assignment_top_level_at_bootstrap",
        "launch_recorded_at": "2026-04-21T10:00:00+0800",
        "launch_command": f"claude --agent {bot_name}",
    }
    (runtime_dir / f"runtime-launch-manifest-{bot_name}.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def base_live_runtime(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "cmux_ping_ok": True,
        "selected_workspace_ref": "workspace:1",
        "selected_workspace_matches_assignment": True,
        "workspace_name": "workbot",
        "workspace_ref": "workspace:1",
        "workspace_count": 1,
        "single_workspace_healthy": True,
        "runtime_mode": "pm_only",
        "active_runtime_healthy": True,
        "board_surface_guard": {
            "required": False,
            "healthy": True,
            "surface_count": 0,
            "error": "",
        },
        "five_plus_one_shape_guard": {
            "required": False,
            "healthy": True,
            "present_worker_count": 0,
            "missing_workers": [],
            "error": "",
        },
        "workspaces": [{"ref": "workspace:1", "name": "workbot", "selected": True}],
        "active_runtime": [],
        "board_surfaces": [],
        "cmux_error": None,
    }
    payload.update(overrides)
    return payload


def make_stale_identity_entry(
    *,
    bot_name: str,
    role: str,
    workspace_ref: str,
    pane_ref: str,
    surface_ref: str,
    fresh_assignment_id: str,
    stale_assignment_id: str,
    fresh_tool_profile_id: str,
    stale_tool_profile_id: str,
    fresh_lane_justification: str,
    stale_lane_justification: str,
) -> dict[str, object]:
    stale_tool_profile = {
        "tool_profile_id": stale_tool_profile_id,
        "allowed_tools": ["Read"],
        "forbidden_tools": [],
        "allowed_write_target": "",
        "error_route": "",
    }
    return {
        "logical_target": bot_name,
        "bot_name": bot_name,
        "assignment_id": fresh_assignment_id,
        "lane_identity": bot_name,
        "lane_justification": fresh_lane_justification,
        "worker_role": role,
        "workspace_root": "/Users/busiji/workbot",
        "project_scope": "workbot",
        "project_pack": {
            "project_scope": "workbot",
            "ownership": "legacy-owner",
            "project_kind": "legacy-kind",
        },
        "title": f"Fresh validation dispatch for {bot_name}",
        "goal": "Validate runtime execution boundaries and stop after local writeback.",
        "task_kind": "assignment",
        "assignment_class": "已批准执行方案",
        "assignment_contract": {
            "assignment_class": "已批准执行方案",
            "lane_justification": stale_lane_justification,
            "target_object": "legacy target",
            "scope_boundary": "legacy scope",
            "deliverable": f"/tmp/{bot_name}-legacy-summary.json",
            "verification_goal": "legacy verification",
            "truth_basis_refs": ["/tmp/legacy-truth.md"],
        },
        "target_object": "fresh native validation run",
        "scope_boundary": "validation-only / no repo patch / no historical evidence",
        "deliverable": f"/tmp/{bot_name}-fresh-summary.json",
        "verification_goal": "emit fresh completed/pass control packet and local evidence only",
        "truth_basis_refs": ["/Users/busiji/workbot/AGENTS.md"],
        "tool_profile_id": fresh_tool_profile_id,
        "tool_profile": stale_tool_profile,
        "allowed_tools": ["Read", "Write", "Edit", "Bash", "Glob", "Grep", "LS"],
        "forbidden_tools": [],
        "allowed_write_target": "/Users/busiji/workbot/workspace",
        "error_route": "report blocker in terminal and stop",
        "permission_mode": "default",
        "dispatch_owner": "codex",
        "conflict_status": "resolved",
        "ownership": "",
        "project_kind": "",
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
        "task_text": "Write the assigned summary artifact and stop.",
        "continue_text": "Continue the fresh validation task and stop after local writeback.",
        "status": "ACTIVE",
        "session_class": "formal_cmux_worker",
        "pane_ref": pane_ref,
        "surface_ref": surface_ref,
        "workspace_ref": workspace_ref,
        "runtime_status": "running",
        "allow_intervene": True,
        "runtime_identity": {
            "assignment_id": stale_assignment_id,
            "lane_identity": bot_name,
            "lane_justification": stale_lane_justification,
            "project_pack": {
                "project_scope": "workbot",
                "ownership": "legacy-owner",
                "project_kind": "legacy-kind",
            },
            "assignment_class": "已批准执行方案",
            "tool_profile_id": stale_tool_profile_id,
            "tool_profile": stale_tool_profile,
            "permission_mode": "default",
            "session_class": "formal_cmux_worker",
            "workspace_root": "/Users/busiji/workbot",
            "bot_name": bot_name,
            "logical_target": bot_name,
            "status": "IDLE",
            "audit_round_1_owner": "rea-bot",
        },
        "effective_permission_mode": "default",
        "dispatch_ready": True,
        "dispatch_blockers": [],
    }


def write_stale_identity_runtime(tmp_path: Path) -> tuple[Path, Path]:
    runtime_dir = tmp_path / "workspace" / "artifacts" / "cmux-runtime"
    runtime_dir.mkdir(parents=True)
    assignment_file = runtime_dir / "cmux-assignment.json"
    payload = {
        "runtime": "cmux",
        "ready": True,
        "dispatch_ready": True,
        "workspace_name": "workbot",
        "workspace_ref": "workspace:1",
        "runtime_status": "running",
        "active_assignment_count": 2,
        "updated_at": "2026-04-20T03:50:05+0800",
        "assignments": [
            make_stale_identity_entry(
                bot_name="pm-bot",
                role="pm",
                workspace_ref="workspace:1",
                pane_ref="pane:1",
                surface_ref="surface:1",
                fresh_assignment_id="PM-FRESH-20260420",
                stale_assignment_id="P14-PMBOT-R1-HOMEPAGE-INVENTORY",
                fresh_tool_profile_id="pm-fresh-validation",
                stale_tool_profile_id="pm-active",
                fresh_lane_justification="fresh validation dispatch for pm-bot",
                stale_lane_justification="main-thread formal dispatch from GitHub Project #14 item legacy to pm-bot.",
            ),
            make_stale_identity_entry(
                bot_name="dev-bot",
                role="dev",
                workspace_ref="workspace:1",
                pane_ref="pane:2",
                surface_ref="surface:2",
                fresh_assignment_id="DEV-FRESH-20260420",
                stale_assignment_id="idle-dev-bot",
                fresh_tool_profile_id="dev-fresh-validation",
                stale_tool_profile_id="idle-default",
                fresh_lane_justification="fresh validation dispatch for dev-bot",
                stale_lane_justification="",
            ),
        ],
    }
    assignment_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    for bot_name, stale_assignment_id, stale_lane_justification in (
        ("pm-bot", "P14-PMBOT-R1-HOMEPAGE-INVENTORY", "main-thread formal dispatch from GitHub Project #14 item legacy to pm-bot."),
        ("dev-bot", "idle-dev-bot", ""),
    ):
        runtime_settings = runtime_dir / f"runtime-settings-{bot_name}.json"
        runtime_settings.write_text("{}", encoding="utf-8")
        stale_identity = {
            "assignment_id": stale_assignment_id,
            "lane_identity": bot_name,
            "lane_justification": stale_lane_justification,
            "bot_name": bot_name,
            "logical_target": bot_name,
        }
        manifest = {
            "bot_name": bot_name,
            "assignment_id": stale_assignment_id,
            "lane_identity": bot_name,
            "lane_justification": stale_lane_justification,
            "logical_target": bot_name,
            "workspace_ref": "workspace:1",
            "surface_ref": "surface:1" if bot_name == "pm-bot" else "surface:2",
            "permission_mode": "default",
            "allowed_tools": ["Read"],
            "forbidden_tools": [],
            "runtime_settings_path": str(runtime_settings),
            "external_mcp_tokens": [],
            "resolved_mcp_servers": [],
            "mcp_config": {},
            "derived_identity": stale_identity,
            "identity_source": "assignment_top_level_at_bootstrap",
            "launch_assignment_id": stale_assignment_id,
            "launch_lane_identity": bot_name,
            "launch_lane_justification": stale_lane_justification,
            "launch_logical_target": bot_name,
            "launch_workspace_ref": "workspace:1",
            "launch_surface_ref": "surface:1" if bot_name == "pm-bot" else "surface:2",
            "launch_permission_mode": "default",
            "launch_derived_identity": stale_identity,
            "launch_identity_source": "assignment_top_level_at_bootstrap",
            "launch_recorded_at": "2026-04-20T03:50:05+0800",
            "launch_command": f"CMUX_DERIVED_IDENTITY_JSON='{json.dumps(stale_identity, ensure_ascii=False)}' claude --agent {bot_name}",
        }
        (runtime_dir / f"runtime-launch-manifest-{bot_name}.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    return assignment_file, runtime_dir


def run_print_status(
    module,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    *,
    live_runtime: dict[str, object],
    assignment_file: str = "/tmp/cmux-assignment.json",
    assignment_runtime: dict[str, object] | None = None,
    watcher_runtime: dict[str, object] | None = None,
    hook_guard: dict[str, object] | None = None,
    commander_handoff_guard: dict[str, object] | None = None,
) -> tuple[int, dict[str, object]]:
    if assignment_runtime is None:
        assignment_runtime = {
            "assignment_file": assignment_file,
            "assignment_count": 1,
            "active_assignment_count": 1,
            "ready": True,
            "dispatch_ready": True,
            "error": None,
            "unready_assignments": [],
            "missing_runtime_refs": [],
        }
    if watcher_runtime is None:
        watcher_runtime = {
            "pid_file": "/tmp/watch_cmux_assignments.pid",
            "pid": 12345,
            "pid_file_exists": True,
            "alive": True,
            "command": "python watch_cmux_assignments.py --assignment-file /tmp/cmux-assignment.json",
            "watched_assignment_file": assignment_file,
            "assignment_file_matches_requested": True,
            "error": "",
        }
    if hook_guard is None:
        hook_guard = {
            "hook_state_file": "/tmp/hook-state.json",
            "exists": True,
            "healthy": True,
            "violation_count": 0,
            "adhoc_surface_refs": [],
            "error": "",
        }
    if commander_handoff_guard is None:
        commander_handoff_guard = {
            "required": True,
            "healthy": True,
            "hook_state_file": "/tmp/hook-state.json",
            "consumer_state_file": "/tmp/cmux-consumer-state-latest.json",
            "pending_actions": [],
            "error": "",
        }

    monkeypatch.setattr(module, "load_assignment_runtime_or_error", lambda _: (assignment_runtime, None))
    monkeypatch.setattr(module, "inspect_live_runtime", lambda _: live_runtime)
    monkeypatch.setattr(module, "inspect_watcher_runtime", lambda _: watcher_runtime)
    monkeypatch.setattr(module, "inspect_hook_guard", lambda _: hook_guard)
    monkeypatch.setattr(module, "inspect_commander_handoff_guard", lambda _: commander_handoff_guard)
    rc = module.print_status(SimpleNamespace(assignment_file=assignment_file))
    payload = json.loads(capsys.readouterr().out)
    return rc, payload


def test_runtime_identity_from_assignment_tracks_assignment_id_and_bot_name() -> None:
    module = load_bootstrap_module()

    identity = module.runtime_identity_from_assignment(
        "pm-bot",
        {
            "assignment_id": "PM-FRESH-20260420",
            "lane_identity": "pm-bot",
            "lane_justification": "fresh validation dispatch for pm-bot",
            "project_scope": "fresh-scope",
            "ownership": "fresh-owner",
            "project_kind": "fresh-kind",
            "project_pack": {
                "project_scope": "legacy-scope",
                "ownership": "legacy-owner",
                "project_kind": "legacy-kind",
            },
            "assignment_class": "已批准执行方案",
            "permission_mode": "default",
            "session_class": "formal_cmux_worker",
            "tool_profile_id": "pm-fresh-validation",
            "allowed_tools": ["Read", "Write"],
            "forbidden_tools": [],
            "workspace_root": "/Users/busiji/workbot",
            "logical_target": "pm-bot",
            "status": "ACTIVE",
            "audit_round_1_owner": "rea-bot",
        },
        fallback_permission_mode="plan",
        workspace_name="workbot",
        project_dir=Path("/Users/busiji/workbot"),
    )

    assert identity["assignment_id"] == "PM-FRESH-20260420"
    assert identity["lane_justification"] == "fresh validation dispatch for pm-bot"
    assert identity["bot_name"] == "pm-bot"
    assert identity["logical_target"] == "pm-bot"
    assert identity["project_pack"] == {
        "project_scope": "fresh-scope",
        "ownership": "fresh-owner",
        "project_kind": "fresh-kind",
    }


def test_persist_runtime_identity_writes_fresh_runtime_identity_for_pm_and_dev(tmp_path: Path) -> None:
    module = load_bootstrap_module()
    assignment_file, _runtime_dir = write_stale_identity_runtime(tmp_path)

    runtime_identities = {
        "pm-bot": {
            "assignment_id": "PM-FRESH-20260420",
            "lane_identity": "pm-bot",
            "lane_justification": "fresh validation dispatch for pm-bot",
            "project_pack": {"project_scope": "workbot", "ownership": "", "project_kind": ""},
            "assignment_class": "已批准执行方案",
            "tool_profile_id": "pm-fresh-validation",
            "tool_profile": {
                "tool_profile_id": "pm-fresh-validation",
                "allowed_tools": ["Read", "Write"],
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
        },
        "dev-bot": {
            "assignment_id": "DEV-FRESH-20260420",
            "lane_identity": "dev-bot",
            "lane_justification": "fresh validation dispatch for dev-bot",
            "project_pack": {"project_scope": "workbot", "ownership": "", "project_kind": ""},
            "assignment_class": "已批准执行方案",
            "tool_profile_id": "dev-fresh-validation",
            "tool_profile": {
                "tool_profile_id": "dev-fresh-validation",
                "allowed_tools": ["Read", "Write"],
                "forbidden_tools": [],
                "allowed_write_target": "/Users/busiji/workbot/workspace",
                "error_route": "report blocker in terminal and stop",
            },
            "permission_mode": "default",
            "session_class": "formal_cmux_worker",
            "workspace_root": "/Users/busiji/workbot",
            "bot_name": "dev-bot",
            "logical_target": "dev-bot",
            "status": "ACTIVE",
            "audit_round_1_owner": "rea-bot",
        },
    }

    module.persist_runtime_identity(assignment_file, runtime_identities)

    payload = json.loads(assignment_file.read_text(encoding="utf-8"))
    pm_item, dev_item = payload["assignments"]
    assert pm_item["runtime_identity"]["assignment_id"] == "PM-FRESH-20260420"
    assert pm_item["runtime_identity"]["lane_justification"] == "fresh validation dispatch for pm-bot"
    assert pm_item["runtime_identity"]["tool_profile_id"] == "pm-fresh-validation"
    assert dev_item["runtime_identity"]["assignment_id"] == "DEV-FRESH-20260420"
    assert dev_item["runtime_identity"]["lane_justification"] == "fresh validation dispatch for dev-bot"
    assert dev_item["runtime_identity"]["tool_profile_id"] == "dev-fresh-validation"
    assert pm_item["effective_permission_mode"] == "default"
    assert dev_item["effective_permission_mode"] == "default"


def test_inspect_assignment_runtime_blocks_stale_launch_task_source_manifest(tmp_path: Path) -> None:
    module = load_cmux_runtime_ctl_module()
    assignment_file, _runtime_dir = write_stale_identity_runtime(tmp_path)

    with pytest.raises(ValueError, match="launch task-source gate blocked"):
        module.inspect_assignment_runtime(str(assignment_file))


def test_print_status_reports_blocked_after_stale_launch_task_source(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    module = load_cmux_runtime_ctl_module()
    assignment_file, _runtime_dir = write_stale_identity_runtime(tmp_path)

    monkeypatch.setattr(module, "inspect_live_runtime", lambda _: base_live_runtime(runtime_mode="five_plus_one"))
    monkeypatch.setattr(
        module,
        "inspect_watcher_runtime",
        lambda _: {
            "pid_file": "/tmp/watch_cmux_assignments.pid",
            "manifest_file": "/tmp/watch_cmux_assignments.manifest.json",
            "pid": None,
            "pid_file_exists": False,
            "manifest_exists": False,
            "alive": False,
            "command": "",
            "watched_assignment_file": "",
            "assignment_file_matches_requested": False,
            "manifest_assignment_file": "",
            "manifest_workspace_ref": "",
            "manifest_runtime_mode": "",
            "manifest_matches_requested": False,
            "error": "watcher_pid_file_missing",
        },
    )
    monkeypatch.setattr(
        module,
        "inspect_hook_guard",
        lambda _: {
            "hook_state_file": "/tmp/hook-state.json",
            "exists": True,
            "healthy": True,
            "violation_count": 0,
            "adhoc_surface_refs": [],
            "error": "",
        },
    )
    monkeypatch.setattr(
        module,
        "inspect_commander_handoff_guard",
        lambda _: {
            "required": True,
            "healthy": True,
            "hook_state_file": "/tmp/hook-state.json",
            "consumer_state_file": "/tmp/cmux-consumer-state-latest.json",
            "pending_actions": [],
            "error": "",
        },
    )

    rc = module.print_status(SimpleNamespace(assignment_file=str(assignment_file)))
    payload = json.loads(capsys.readouterr().out)

    assert rc == 1
    assert payload["assignment"]["ready"] is False
    assert "launch task-source gate blocked" in str(payload["assignment"]["error"] or "")
    assert payload["healthy"] is False


def test_inspect_live_runtime_reports_five_plus_one_shape(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    module = load_cmux_runtime_ctl_module()
    assignment_file = tmp_path / "cmux-assignment.json"
    assignment_file.write_text(
        json.dumps(
            {
                "workspace_name": "workbot",
                "workspace_ref": "workspace:100",
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    runtime_dir = assignment_file.parent
    for bot_name, assignment_id, surface_ref in (
        ("pm-bot", "a1", "surface:1"),
        ("dev-bot", "a2", "surface:2"),
        ("qa-bot", "a3", "surface:3"),
        ("doc-bot", "a4", "surface:4"),
        ("rea-bot", "a5", "surface:5"),
    ):
        write_runtime_launch_manifest(
            runtime_dir,
            bot_name=bot_name,
            assignment_id=assignment_id,
            workspace_ref="workspace:100",
            surface_ref=surface_ref,
        )

    monkeypatch.setattr(module, "cmux", lambda *args, **kwargs: "ok")
    monkeypatch.setattr(module, "current_workspace_ref", lambda: "workspace:100")
    monkeypatch.setattr(
        module,
        "list_workspaces",
        lambda: [{"ref": "workspace:100", "name": "workbot", "selected": True}],
    )
    monkeypatch.setattr(
        module,
        "load_assignment_file",
        lambda _: [
            fake_assignment(
                logical_target="pm-bot",
                bot_name="pm-bot",
                assignment_id="a1",
                workspace_ref="workspace:100",
                pane_ref="pane:1",
                surface_ref="surface:1",
            ),
            fake_assignment(
                logical_target="dev-bot",
                bot_name="dev-bot",
                assignment_id="a2",
                workspace_ref="workspace:100",
                pane_ref="pane:2",
                surface_ref="surface:2",
            ),
            fake_assignment(
                logical_target="qa-bot",
                bot_name="qa-bot",
                assignment_id="a3",
                workspace_ref="workspace:100",
                pane_ref="pane:3",
                surface_ref="surface:3",
            ),
            fake_assignment(
                logical_target="doc-bot",
                bot_name="doc-bot",
                assignment_id="a4",
                workspace_ref="workspace:100",
                pane_ref="pane:4",
                surface_ref="surface:4",
            ),
            fake_assignment(
                logical_target="rea-bot",
                bot_name="rea-bot",
                assignment_id="a5",
                workspace_ref="workspace:100",
                pane_ref="pane:5",
                surface_ref="surface:5",
            ),
        ],
    )
    monkeypatch.setattr(
        module,
        "parse_tree",
        lambda _: {
            "surface:1": fake_snapshot(
                workspace_ref="workspace:100",
                pane_ref="pane:1",
                surface_ref="surface:1",
                surface_type="terminal",
                title="pm-bot",
                dead=False,
            ),
            "surface:2": fake_snapshot(
                workspace_ref="workspace:100",
                pane_ref="pane:2",
                surface_ref="surface:2",
                surface_type="terminal",
                title="dev-bot",
                dead=False,
            ),
            "surface:3": fake_snapshot(
                workspace_ref="workspace:100",
                pane_ref="pane:3",
                surface_ref="surface:3",
                surface_type="terminal",
                title="qa-bot",
                dead=False,
            ),
            "surface:4": fake_snapshot(
                workspace_ref="workspace:100",
                pane_ref="pane:4",
                surface_ref="surface:4",
                surface_type="terminal",
                title="doc-bot",
                dead=False,
            ),
            "surface:5": fake_snapshot(
                workspace_ref="workspace:100",
                pane_ref="pane:5",
                surface_ref="surface:5",
                surface_type="terminal",
                title="rea-bot",
                dead=False,
            ),
            "surface:6": fake_snapshot(
                workspace_ref="workspace:100",
                pane_ref="pane:6",
                surface_ref="surface:6",
                surface_type="browser",
                title="cmux-browser",
                dead=True,
            ),
        },
    )

    runtime = module.inspect_live_runtime(str(assignment_file))
    assert runtime["runtime_mode"] == "five_plus_one"
    assert runtime["selected_workspace_matches_assignment"] is True
    assert runtime["active_runtime_healthy"] is True
    assert runtime["board_surface_guard"]["healthy"] is True
    assert runtime["five_plus_one_shape_guard"]["healthy"] is True
    assert runtime["five_plus_one_shape_guard"]["present_worker_count"] == 5
    assert runtime["active_runtime"][0]["launch_provenance_healthy"] is True


def test_inspect_live_runtime_pm_only_rejects_residual_board(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    module = load_cmux_runtime_ctl_module()
    assignment_file = tmp_path / "pm-bot-watch.json"
    assignment_file.write_text(
        json.dumps(
            {
                "workspace_name": "workbot",
                "workspace_ref": "workspace:200",
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    write_runtime_launch_manifest(
        assignment_file.parent,
        bot_name="pm-bot",
        assignment_id="pm1",
        workspace_ref="workspace:200",
        surface_ref="surface:10",
    )

    monkeypatch.setattr(module, "cmux", lambda *args, **kwargs: "ok")
    monkeypatch.setattr(module, "current_workspace_ref", lambda: "workspace:200")
    monkeypatch.setattr(
        module,
        "list_workspaces",
        lambda: [{"ref": "workspace:200", "name": "workbot", "selected": True}],
    )
    monkeypatch.setattr(
        module,
        "load_assignment_file",
        lambda _: [
            fake_assignment(
                logical_target="pm-bot",
                bot_name="pm-bot",
                assignment_id="pm1",
                workspace_ref="workspace:200",
                pane_ref="pane:10",
                surface_ref="surface:10",
            )
        ],
    )
    monkeypatch.setattr(
        module,
        "parse_tree",
        lambda _: {
            "surface:10": fake_snapshot(
                workspace_ref="workspace:200",
                pane_ref="pane:10",
                surface_ref="surface:10",
                surface_type="terminal",
                title="pm-bot",
                dead=False,
            ),
            "surface:11": fake_snapshot(
                workspace_ref="workspace:200",
                pane_ref="pane:11",
                surface_ref="surface:11",
                surface_type="browser",
                title="cmux-browser",
                dead=True,
            ),
        },
    )

    runtime = module.inspect_live_runtime(str(assignment_file))
    assert runtime["runtime_mode"] == "pm_only"
    assert runtime["board_surface_guard"]["healthy"] is False
    assert "pm_only_unexpected_cmux-browser_surface" in runtime["board_surface_guard"]["error"]
    assert runtime["active_runtime"][0]["launch_provenance_healthy"] is True


def test_inspect_live_runtime_flags_launch_provenance_mismatch(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    module = load_cmux_runtime_ctl_module()
    assignment_file = tmp_path / "cmux-assignment.json"
    assignment_file.write_text(
        json.dumps(
            {
                "workspace_name": "workbot",
                "workspace_ref": "workspace:300",
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    write_runtime_launch_manifest(
        assignment_file.parent,
        bot_name="pm-bot",
        assignment_id="idle-pm-bot",
        workspace_ref="workspace:300",
        surface_ref="surface:30",
    )

    monkeypatch.setattr(module, "cmux", lambda *args, **kwargs: "ok")
    monkeypatch.setattr(module, "current_workspace_ref", lambda: "workspace:300")
    monkeypatch.setattr(
        module,
        "list_workspaces",
        lambda: [{"ref": "workspace:300", "name": "workbot", "selected": True}],
    )
    monkeypatch.setattr(
        module,
        "load_assignment_file",
        lambda _: [
            fake_assignment(
                logical_target="pm-bot",
                bot_name="pm-bot",
                assignment_id="pm3",
                workspace_ref="workspace:300",
                pane_ref="pane:30",
                surface_ref="surface:30",
            )
        ],
    )
    monkeypatch.setattr(
        module,
        "parse_tree",
        lambda _: {
            "surface:30": fake_snapshot(
                workspace_ref="workspace:300",
                pane_ref="pane:30",
                surface_ref="surface:30",
                surface_type="terminal",
                title="pm-bot",
                dead=False,
            )
        },
    )

    runtime = module.inspect_live_runtime(str(assignment_file))

    assert runtime["active_runtime_healthy"] is False
    row = runtime["active_runtime"][0]
    assert row["launch_provenance_healthy"] is False
    assert row["launch_provenance_error"] == "runtime_launch_provenance_mismatch"
    assert row["launch_provenance_mismatches"]["assignment_id"]["expected"] == "pm3"
    assert row["launch_provenance_mismatches"]["assignment_id"]["actual"] == "idle-pm-bot"


def test_active_runtime_rows_allow_browser_board_slot() -> None:
    module = load_cmux_runtime_ctl_module()
    rows = [
        {
            "logical_target": "pm-bot",
            "bot_name": "pm-bot",
            "surface_present": True,
            "pane_matches": True,
            "surface_type": "terminal",
            "dead": False,
            "is_board_slot": False,
            "title": "pm-bot",
            "cmd": "claude --agent pm-bot",
        },
        {
            "logical_target": "cmux-browser",
            "bot_name": "empty",
            "surface_present": True,
            "pane_matches": True,
            "surface_type": "browser",
            "dead": True,
            "is_board_slot": True,
            "title": "cmux-browser",
        },
    ]

    assert module.active_runtime_rows_healthy(rows) is True
    assert module.classify_runtime_mode(
        "/tmp/cmux-assignment.json",
        rows,
        [{"surface_ref": "surface:99", "surface_type": "browser", "title": "cmux-browser"}],
    ) == "five_plus_one"


def test_board_surface_guard_rejects_five_plus_one_without_board_surface() -> None:
    module = load_cmux_runtime_ctl_module()
    guard = module.evaluate_board_surface_guard("five_plus_one", [])
    assert guard["required"] is True
    assert guard["healthy"] is False
    assert "expected_exactly_one_cmux-browser_surface" in str(guard["error"])


def test_print_status_reports_pm_only_healthy(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    module = load_cmux_runtime_ctl_module()
    rc, payload = run_print_status(
        module,
        monkeypatch,
        capsys,
        live_runtime=base_live_runtime(
            runtime_mode="pm_only",
            active_runtime=[
                {
                    "logical_target": "pm-bot",
                    "bot_name": "pm-bot",
                    "surface_present": True,
                    "pane_matches": True,
                    "surface_type": "terminal",
                    "dead": False,
                    "is_board_slot": False,
                    "title": "pm-bot",
                }
            ],
        ),
        assignment_file="/tmp/pm-bot-watch.json",
    )
    assert rc == 0
    assert payload["healthy"] is True
    assert payload["watcher_guard"]["healthy"] is True


def test_print_status_fails_when_selected_workspace_mismatch(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    module = load_cmux_runtime_ctl_module()
    rc, payload = run_print_status(
        module,
        monkeypatch,
        capsys,
        live_runtime=base_live_runtime(selected_workspace_matches_assignment=False),
    )
    assert rc == 1
    assert payload["healthy"] is False


def test_print_status_fails_when_single_workspace_guard_fails(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    module = load_cmux_runtime_ctl_module()
    rc, payload = run_print_status(
        module,
        monkeypatch,
        capsys,
        live_runtime=base_live_runtime(single_workspace_healthy=False, workspace_count=2),
    )
    assert rc == 1
    assert payload["healthy"] is False


def test_print_status_fails_when_multi_bot_board_guard_fails(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    module = load_cmux_runtime_ctl_module()
    rc, payload = run_print_status(
        module,
        monkeypatch,
        capsys,
        live_runtime=base_live_runtime(
            runtime_mode="five_plus_one",
            board_surface_guard={
                "required": True,
                "healthy": False,
                "surface_count": 0,
                "error": "expected_exactly_one_cmux-browser_surface",
            },
            five_plus_one_shape_guard={
                "required": True,
                "healthy": True,
                "present_worker_count": 5,
                "missing_workers": [],
                "error": "",
            },
            active_runtime=[
                {
                    "logical_target": "pm-bot",
                    "bot_name": "pm-bot",
                    "surface_present": True,
                    "pane_matches": True,
                    "surface_type": "terminal",
                    "dead": False,
                    "is_board_slot": False,
                    "title": "pm-bot",
                }
            ],
        ),
    )
    assert rc == 1
    assert payload["healthy"] is False


def test_print_status_reports_five_plus_one_healthy_without_watcher(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    module = load_cmux_runtime_ctl_module()
    rc, payload = run_print_status(
        module,
        monkeypatch,
        capsys,
        live_runtime=base_live_runtime(
            runtime_mode="five_plus_one",
            board_surface_guard={
                "required": True,
                "healthy": True,
                "surface_count": 1,
                "error": "",
            },
            five_plus_one_shape_guard={
                "required": True,
                "healthy": True,
                "present_worker_count": 5,
                "missing_workers": [],
                "error": "",
            },
            active_runtime=[
                {
                    "logical_target": "pm-bot",
                    "bot_name": "pm-bot",
                    "surface_present": True,
                    "pane_matches": True,
                    "surface_type": "terminal",
                    "dead": False,
                    "is_board_slot": False,
                    "title": "pm-bot",
                }
            ],
        ),
        assignment_file="/tmp/cmux-assignment.json",
        watcher_runtime={
            "pid_file": "/tmp/watch_cmux_assignments.pid",
            "pid": None,
            "pid_file_exists": False,
            "alive": False,
            "command": "",
            "watched_assignment_file": "",
            "assignment_file_matches_requested": False,
            "error": "watcher_pid_file_missing",
        },
    )
    assert rc == 0
    assert payload["healthy"] is True
    assert payload["watcher_required"] is False
    assert payload["watcher_guard_healthy"] is True


def test_print_status_pm_only_fails_when_watcher_is_dead(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    module = load_cmux_runtime_ctl_module()
    rc, payload = run_print_status(
        module,
        monkeypatch,
        capsys,
        live_runtime=base_live_runtime(runtime_mode="pm_only"),
        assignment_file="/tmp/pm-bot-watch.json",
        watcher_runtime={
            "pid_file": "/tmp/watch_cmux_assignments.pid",
            "pid": None,
            "pid_file_exists": False,
            "alive": False,
            "command": "",
            "watched_assignment_file": "",
            "assignment_file_matches_requested": False,
            "error": "watcher_pid_file_missing",
        },
    )
    assert rc == 1
    assert payload["healthy"] is False
    assert payload["watcher_required"] is True
    assert payload["watcher_guard_healthy"] is False


def test_print_status_five_plus_one_fails_when_watcher_tracks_wrong_assignment(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    module = load_cmux_runtime_ctl_module()
    rc, payload = run_print_status(
        module,
        monkeypatch,
        capsys,
        live_runtime=base_live_runtime(
            runtime_mode="five_plus_one",
            board_surface_guard={
                "required": True,
                "healthy": True,
                "surface_count": 1,
                "error": "",
            },
            five_plus_one_shape_guard={
                "required": True,
                "healthy": True,
                "present_worker_count": 5,
                "missing_workers": [],
                "error": "",
            },
        ),
        assignment_file="/tmp/cmux-assignment.json",
        watcher_runtime={
            "pid_file": "/tmp/watch_cmux_assignments.pid",
            "pid": 99999,
            "pid_file_exists": True,
            "alive": True,
            "command": "python watch_cmux_assignments.py --assignment-file /tmp/pm-bot-watch.json",
            "watched_assignment_file": "/tmp/pm-bot-watch.json",
            "assignment_file_matches_requested": False,
            "error": "watcher_assignment_file_mismatch",
        },
    )
    assert rc == 1
    assert payload["healthy"] is False
    assert payload["watcher_guard"]["healthy"] is False
    assert payload["watcher_guard"]["error"] == "watcher_assignment_file_mismatch"
    assert payload["watcher"]["assignment_file_matches_requested"] is False
    assert payload["watcher"]["watched_assignment_file"] == "/tmp/pm-bot-watch.json"


def test_print_status_fails_when_hook_guard_detects_adhoc_prompt(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    module = load_cmux_runtime_ctl_module()
    rc, payload = run_print_status(
        module,
        monkeypatch,
        capsys,
        live_runtime=base_live_runtime(runtime_mode="pm_only"),
        assignment_file="/tmp/pm-bot-watch.json",
        hook_guard={
            "hook_state_file": "/tmp/hook-state.json",
            "exists": True,
            "healthy": False,
            "violation_count": 1,
            "adhoc_surface_refs": ["surface:8"],
            "error": "adhoc_prompt_violation_detected",
        },
    )
    assert rc == 1
    assert payload["healthy"] is False
    assert payload["hook_guard"]["healthy"] is False
    assert payload["hook_guard"]["adhoc_surface_refs"] == ["surface:8"]


def test_print_status_fails_when_commander_handoff_guard_is_pending(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    module = load_cmux_runtime_ctl_module()
    rc, payload = run_print_status(
        module,
        monkeypatch,
        capsys,
        live_runtime=base_live_runtime(runtime_mode="five_plus_one"),
        commander_handoff_guard={
            "required": True,
            "healthy": False,
            "hook_state_file": "/tmp/hook-state.json",
            "consumer_state_file": "/tmp/cmux-consumer-state-latest.json",
            "pending_actions": [
                {
                    "logical_target": "pm-bot",
                    "assignment_id": "pm-101",
                    "phase": "A6",
                    "reason": "surface_stop_or_notification_requires_commander_review",
                }
            ],
            "error": "commander_handoff_pending",
        },
    )
    assert rc == 1
    assert payload["healthy"] is False
    assert payload["commander_handoff_guard"]["healthy"] is False
    assert payload["commander_handoff_guard"]["pending_actions"][0]["phase"] == "A6"


def test_inspect_watcher_runtime_reads_matching_manifest(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    module = load_cmux_runtime_ctl_module()
    runtime_dir = tmp_path / "workspace" / "artifacts" / "cmux-runtime"
    runtime_dir.mkdir(parents=True)
    assignment_file = runtime_dir / "cmux-assignment.json"
    assignment_file.write_text(json.dumps({"workspace_ref": "workspace:1"}, ensure_ascii=False), encoding="utf-8")
    (runtime_dir / "watch_cmux_assignments.pid").write_text("123\n", encoding="utf-8")
    (runtime_dir / "watch_cmux_assignments.manifest.json").write_text(
        json.dumps(
            {
                "pid": 123,
                "assignment_file": str(assignment_file),
                "workspace_ref": "workspace:1",
                "runtime_mode": "five_plus_one",
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(module.os, "kill", lambda pid, sig: None)
    monkeypatch.setattr(
        module.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(
            returncode=0,
            stdout=f"python watch_cmux_assignments.py --assignment-file {assignment_file}\n",
            stderr="",
        ),
    )

    runtime = module.inspect_watcher_runtime(str(assignment_file))

    assert runtime["alive"] is True
    assert runtime["manifest_exists"] is True
    assert runtime["manifest_matches_requested"] is True
    assert runtime["error"] == ""


def test_inspect_watcher_runtime_flags_manifest_workspace_mismatch(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    module = load_cmux_runtime_ctl_module()
    runtime_dir = tmp_path / "workspace" / "artifacts" / "cmux-runtime"
    runtime_dir.mkdir(parents=True)
    assignment_file = runtime_dir / "cmux-assignment.json"
    assignment_file.write_text(json.dumps({"workspace_ref": "workspace:5"}, ensure_ascii=False), encoding="utf-8")
    (runtime_dir / "watch_cmux_assignments.pid").write_text("123\n", encoding="utf-8")
    (runtime_dir / "watch_cmux_assignments.manifest.json").write_text(
        json.dumps(
            {
                "pid": 123,
                "assignment_file": str(assignment_file),
                "workspace_ref": "workspace:43",
                "runtime_mode": "five_plus_one",
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(module.os, "kill", lambda pid, sig: None)
    monkeypatch.setattr(
        module.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(
            returncode=0,
            stdout=f"python watch_cmux_assignments.py --assignment-file {assignment_file}\n",
            stderr="",
        ),
    )

    runtime = module.inspect_watcher_runtime(str(assignment_file))

    assert runtime["manifest_exists"] is True
    assert runtime["manifest_matches_requested"] is False
    assert runtime["error"] == "watcher_manifest_mismatch"


def test_inspect_watcher_runtime_flags_manifest_without_pid(
    tmp_path: Path,
) -> None:
    module = load_cmux_runtime_ctl_module()
    runtime_dir = tmp_path / "workspace" / "artifacts" / "cmux-runtime"
    runtime_dir.mkdir(parents=True)
    assignment_file = runtime_dir / "cmux-assignment.json"
    assignment_file.write_text(json.dumps({"workspace_ref": "workspace:5"}, ensure_ascii=False), encoding="utf-8")
    (runtime_dir / "watch_cmux_assignments.manifest.json").write_text(
        json.dumps(
            {
                "pid": 123,
                "assignment_file": str(assignment_file),
                "workspace_ref": "workspace:5",
                "runtime_mode": "five_plus_one",
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    runtime = module.inspect_watcher_runtime(str(assignment_file))
    watcher_guard = module.evaluate_watcher_guard("five_plus_one", runtime)

    assert runtime["manifest_exists"] is True
    assert runtime["pid_file_exists"] is False
    assert runtime["error"] == "watcher_manifest_without_pid"
    assert watcher_guard["healthy"] is False
    assert watcher_guard["error"] == "watcher_manifest_without_pid"


def test_active_runtime_row_healthy_rejects_non_formal_worker_session_class() -> None:
    module = load_cmux_runtime_ctl_module()
    row = {
        "surface_present": True,
        "pane_matches": True,
        "is_board_slot": False,
        "surface_type": "terminal",
        "dead": False,
        "session_class": "external_session",
    }
    assert module.active_runtime_row_healthy(row) is False


def test_active_runtime_row_healthy_rejects_non_agent_foreground_command() -> None:
    module = load_cmux_runtime_ctl_module()
    row = {
        "surface_present": True,
        "pane_matches": True,
        "is_board_slot": False,
        "surface_type": "terminal",
        "dead": False,
        "session_class": "formal_cmux_worker",
        "cmd": "sleep 45",
    }
    assert module.active_runtime_row_healthy(row) is False


def test_active_runtime_row_healthy_accepts_agent_in_command_line_when_cmd_is_truncated() -> None:
    module = load_cmux_runtime_ctl_module()
    row = {
        "surface_present": True,
        "pane_matches": True,
        "is_board_slot": False,
        "surface_type": "terminal",
        "dead": False,
        "session_class": "formal_cmux_worker",
        "cmd": "bi",
        "cmdline": "/opt/homebrew/bin/claude --agent pm-bot --permission-mode default",
    }
    assert module.active_runtime_row_healthy(row) is True


def test_inspect_commander_handoff_guard_flags_surface_stop_without_consumer_state(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    module = load_cmux_runtime_ctl_module()
    assignment_file = tmp_path / "cmux-assignment.json"
    assignment_file.write_text(json.dumps({"workspace_ref": "workspace:1"}, ensure_ascii=False), encoding="utf-8")
    (tmp_path / "hook-state.json").write_text(
        json.dumps(
            {
                "surfaces": {
                    "surface:16": {
                        "stop_count": 1,
                        "notification_count": 1,
                        "last_event": "notification",
                    }
                }
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        module,
        "load_assignment_file",
        lambda _: [
            fake_assignment(
                logical_target="pm-bot",
                bot_name="pm-bot",
                assignment_id="pm-101",
                workspace_ref="workspace:1",
                pane_ref="pane:15",
                surface_ref="surface:16",
            )
        ],
    )
    guard = module.inspect_commander_handoff_guard(str(assignment_file))
    assert guard["healthy"] is False
    assert guard["error"] == "commander_handoff_pending"
    assert guard["pending_actions"][0]["phase"] == "A6"
    assert guard["pending_actions"][0]["reason"] == "surface_stop_or_notification_requires_commander_review"


def test_inspect_commander_handoff_guard_clears_stale_stop_after_new_prompt_submit(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    module = load_cmux_runtime_ctl_module()
    assignment_file = tmp_path / "cmux-assignment.json"
    assignment_file.write_text(json.dumps({"workspace_ref": "workspace:1"}, ensure_ascii=False), encoding="utf-8")
    (tmp_path / "hook-state.json").write_text(
        json.dumps(
            {
                "surfaces": {
                    "surface:16": {
                        "prompt_submit_count": 2,
                        "stop_count": 1,
                        "notification_count": 1,
                        "last_event": "prompt-submit",
                        "last_prompt_submit_at": "2026-04-19T09:01:00+0800",
                        "last_stop_at": "2026-04-19T09:00:00+0800",
                        "last_notification_at": "2026-04-19T09:00:05+0800",
                    }
                }
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        module,
        "load_assignment_file",
        lambda _: [
            fake_assignment(
                logical_target="pm-bot",
                bot_name="pm-bot",
                assignment_id="pm-101",
                workspace_ref="workspace:1",
                pane_ref="pane:15",
                surface_ref="surface:16",
            )
        ],
    )
    guard = module.inspect_commander_handoff_guard(str(assignment_file))
    assert guard["healthy"] is True
    assert guard["error"] == ""
    assert guard["pending_actions"] == []


def test_inspect_commander_handoff_guard_uses_last_event_for_legacy_hook_state(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    module = load_cmux_runtime_ctl_module()
    assignment_file = tmp_path / "cmux-assignment.json"
    assignment_file.write_text(json.dumps({"workspace_ref": "workspace:1"}, ensure_ascii=False), encoding="utf-8")
    (tmp_path / "hook-state.json").write_text(
        json.dumps(
            {
                "surfaces": {
                    "surface:16": {
                        "prompt_submit_count": 2,
                        "stop_count": 1,
                        "notification_count": 1,
                        "last_event": "prompt-submit",
                    }
                }
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        module,
        "load_assignment_file",
        lambda _: [
            fake_assignment(
                logical_target="pm-bot",
                bot_name="pm-bot",
                assignment_id="pm-101",
                workspace_ref="workspace:1",
                pane_ref="pane:15",
                surface_ref="surface:16",
            )
        ],
    )
    guard = module.inspect_commander_handoff_guard(str(assignment_file))
    assert guard["healthy"] is True
    assert guard["error"] == ""
    assert guard["pending_actions"] == []


def test_inspect_commander_handoff_guard_flags_completed_control_packet_without_finish_cycle(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    module = load_cmux_runtime_ctl_module()
    assignment_file = tmp_path / "cmux-assignment.json"
    assignment_file.write_text(json.dumps({"workspace_ref": "workspace:1"}, ensure_ascii=False), encoding="utf-8")
    (tmp_path / "cmux-consumer-state-latest.json").write_text(
        json.dumps(
            {
                "assignments": {
                    "pm-bot": {
                        "logical_target": "pm-bot",
                        "assignment_id": "pm-101",
                        "state": "running",
                        "control_packet": {
                            "state": "completed",
                            "result": "pass",
                        },
                    }
                }
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        module,
        "load_assignment_file",
        lambda _: [
            fake_assignment(
                logical_target="pm-bot",
                bot_name="pm-bot",
                assignment_id="pm-101",
                workspace_ref="workspace:1",
                pane_ref="pane:15",
                surface_ref="surface:16",
            )
        ],
    )
    guard = module.inspect_commander_handoff_guard(str(assignment_file))
    assert guard["healthy"] is False
    assert guard["error"] == "commander_handoff_pending"
    assert guard["pending_actions"][0]["phase"] == "A7"
    assert guard["pending_actions"][0]["reason"] == "completed_control_packet_requires_finish_cycle"
