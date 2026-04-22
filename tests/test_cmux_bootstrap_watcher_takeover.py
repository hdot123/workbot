from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path

import pytest


CMUX_SCRIPT_DIR = Path.home() / ".agents" / "skills" / "cmux" / "scripts"
BOOTSTRAP_PATH = CMUX_SCRIPT_DIR / "bootstrap_claude_runtime.py"


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


def make_project_venv(module, project_dir: Path):
    venv_root = project_dir / ".venv"
    return module.ProjectVenv(
        root=venv_root,
        bin_dir=venv_root / "bin",
        python=Path(sys.executable),
        activate_script=venv_root / "bin" / "activate",
    )


def make_tree(module, surfaces: list[str], bot_names: list[str]):
    return {
        surface_ref: module.SurfaceInfo(
            pane_ref=f"pane:{index + 1}",
            surface_ref=surface_ref,
            surface_type="browser" if bot_name == module.BOARD_PLACEHOLDER_BOT else "terminal",
            title=module.BOARD_PLACEHOLDER_VISIBLE_TITLE if bot_name == module.BOARD_PLACEHOLDER_BOT else bot_name,
        )
        for index, (surface_ref, bot_name) in enumerate(zip(surfaces, bot_names, strict=True))
    }


def build_task_source_ref(*, assignment_id: str, cycle_id: str, deliverable_path: str, evidence_path: str, status: str) -> dict[str, str]:
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


def test_reconcile_assignment_watcher_for_bootstrap_clears_live_watcher_for_five_plus_one(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    module = load_bootstrap_module()
    runtime_dir = tmp_path / "workspace" / "artifacts" / "cmux-runtime"
    runtime_dir.mkdir(parents=True)
    pid_file = runtime_dir / "watch_cmux_assignments.pid"
    manifest_file = runtime_dir / "watch_cmux_assignments.manifest.json"
    pid_file.write_text("123\n", encoding="utf-8")
    manifest_file.write_text("{}", encoding="utf-8")

    terminated: list[int] = []
    monkeypatch.setattr(
        module,
        "inspect_existing_assignment_watcher",
        lambda _project_dir: {
            "pid_file_exists": True,
            "manifest_exists": True,
            "alive": True,
            "pid": 123,
        },
    )
    monkeypatch.setattr(module, "terminate_pid", lambda pid: terminated.append(pid))

    result = module.reconcile_assignment_watcher_for_bootstrap(
        tmp_path,
        runtime_mode="five_plus_one",
    )

    assert terminated == [123]
    assert not pid_file.exists()
    assert not manifest_file.exists()
    assert result["terminated_existing_watcher"] is True
    assert result["cleared_pid_file"] is True
    assert result["cleared_manifest"] is True


def test_bootstrap_five_plus_one_reconciles_without_starting_watcher(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    module = load_bootstrap_module()
    project_dir = tmp_path
    surfaces = [f"surface:{index + 1}" for index in range(len(module.DEFAULT_BOTS))]
    bot_names = list(module.DEFAULT_BOTS)
    called: dict[str, object] = {}

    monkeypatch.setattr(module, "require_project_venv", lambda _project_dir: make_project_venv(module, project_dir))
    monkeypatch.setattr(module, "enforce_single_gui_window_limit", lambda: None)
    monkeypatch.setattr(module, "enforce_single_workspace_limit", lambda: None)
    monkeypatch.setattr(module, "ensure_fresh_workspace", lambda *args, **kwargs: "workspace:1")
    monkeypatch.setattr(module, "build_standard_topology", lambda *args, **kwargs: (surfaces, {"shape": "3x2"}))
    monkeypatch.setattr(module, "rename_surfaces", lambda *args, **kwargs: None)
    monkeypatch.setattr(module, "materialize_board_surface", lambda *args, **kwargs: surfaces)
    monkeypatch.setattr(module, "verify_standard_runtime_contract", lambda *args, **kwargs: {"ok": True})
    monkeypatch.setattr(module, "reset_hook_state", lambda path: path)
    monkeypatch.setattr(module, "ensure_project_hook_settings", lambda *args, **kwargs: project_dir / ".claude" / "settings.local.json")

    def fake_reconcile(_project_dir, *, runtime_mode):
        called["reconcile_runtime_mode"] = runtime_mode
        return {"runtime_mode": runtime_mode}

    monkeypatch.setattr(module, "reconcile_assignment_watcher_for_bootstrap", fake_reconcile)
    monkeypatch.setattr(
        module,
        "sync_assignment_file",
        lambda _project_dir, _workspace_ref, _bot_names, runtime_python, assignment_file=None: assignment_file
        or module.default_assignment_file_path(project_dir),
    )
    monkeypatch.setattr(module, "validate_dispatch_ready_payload", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        module,
        "assignment_map_by_target",
        lambda _path: {
            bot_name: {"lane_identity": bot_name, "logical_target": bot_name, "bot_name": bot_name}
            for bot_name in module.executable_bot_names(bot_names)
        },
    )
    monkeypatch.setattr(module, "prepare_identity_file", lambda lane_identity, _project_dir: project_dir / f"{lane_identity}.md")
    monkeypatch.setattr(
        module,
        "runtime_identity_from_assignment",
        lambda bot_name, assignment, **kwargs: {
            "lane_identity": bot_name,
            "permission_mode": "default",
            "tool_profile": {"allowed_tools": ["Read"]},
        },
    )
    monkeypatch.setattr(module, "launch_claude_agent", lambda *args, **kwargs: {"ok": True})
    monkeypatch.setattr(module, "wait_for_all_claude_ready", lambda *args, **kwargs: None)
    monkeypatch.setattr(module, "verify_native_agent_session", lambda *args, **kwargs: None)
    monkeypatch.setattr(module, "run_startup_smoke_check", lambda *args, **kwargs: {"ok": True})
    monkeypatch.setattr(module, "persist_runtime_identity", lambda *args, **kwargs: None)
    monkeypatch.setattr(module, "parse_tree", lambda _workspace_ref: make_tree(module, surfaces, bot_names))
    monkeypatch.setattr(
        module,
        "launch_assignment_watcher",
        lambda *args, **kwargs: pytest.fail("five_plus_one bootstrap must not start assignment watcher"),
    )

    args = argparse.Namespace(
        project_dir=str(project_dir),
        workspace_name=None,
        allow_workspace_name_override=False,
        permission_mode="plan",
        recreate=False,
        bot_name=bot_names,
    )
    result = module.bootstrap(args)

    assert called["reconcile_runtime_mode"] == "five_plus_one"
    assert result["assignment_watcher"] is None
    assert result["watcher_reconciliation"]["runtime_mode"] == "five_plus_one"


def test_bootstrap_pm_only_launches_assignment_watcher_with_restart(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    module = load_bootstrap_module()
    project_dir = tmp_path
    surfaces = ["surface:1"]
    bot_names = ["pm-bot"]
    called: dict[str, object] = {}

    monkeypatch.setattr(module, "require_project_venv", lambda _project_dir: make_project_venv(module, project_dir))
    monkeypatch.setattr(module, "enforce_single_gui_window_limit", lambda: None)
    monkeypatch.setattr(module, "enforce_single_workspace_limit", lambda: None)
    monkeypatch.setattr(module, "ensure_fresh_workspace", lambda *args, **kwargs: "workspace:1")
    monkeypatch.setattr(module, "build_standard_topology", lambda *args, **kwargs: (surfaces, {"shape": "1x1"}))
    monkeypatch.setattr(module, "rename_surfaces", lambda *args, **kwargs: None)
    monkeypatch.setattr(module, "materialize_board_surface", lambda *args, **kwargs: surfaces)
    monkeypatch.setattr(module, "verify_standard_runtime_contract", lambda *args, **kwargs: {"ok": True})
    monkeypatch.setattr(module, "reset_hook_state", lambda path: path)
    monkeypatch.setattr(module, "ensure_project_hook_settings", lambda *args, **kwargs: project_dir / ".claude" / "settings.local.json")

    def fake_reconcile(_project_dir, *, runtime_mode):
        called["reconcile_runtime_mode"] = runtime_mode
        return {"runtime_mode": runtime_mode}

    monkeypatch.setattr(module, "reconcile_assignment_watcher_for_bootstrap", fake_reconcile)
    monkeypatch.setattr(
        module,
        "sync_assignment_file",
        lambda _project_dir, _workspace_ref, _bot_names, runtime_python, assignment_file=None: assignment_file
        or module.default_pm_bot_watch_assignment_file_path(project_dir),
    )
    monkeypatch.setattr(module, "validate_dispatch_ready_payload", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        module,
        "assignment_map_by_target",
        lambda _path: {
            "pm-bot": {"lane_identity": "pm-bot", "logical_target": "pm-bot", "bot_name": "pm-bot"}
        },
    )
    monkeypatch.setattr(module, "prepare_identity_file", lambda lane_identity, _project_dir: project_dir / f"{lane_identity}.md")
    monkeypatch.setattr(
        module,
        "runtime_identity_from_assignment",
        lambda bot_name, assignment, **kwargs: {
            "lane_identity": bot_name,
            "permission_mode": "default",
            "tool_profile": {"allowed_tools": ["Read"]},
        },
    )
    monkeypatch.setattr(module, "launch_claude_agent", lambda *args, **kwargs: {"ok": True})
    monkeypatch.setattr(module, "wait_for_all_claude_ready", lambda *args, **kwargs: None)
    monkeypatch.setattr(module, "verify_native_agent_session", lambda *args, **kwargs: None)
    monkeypatch.setattr(module, "run_startup_smoke_check", lambda *args, **kwargs: {"ok": True})
    monkeypatch.setattr(module, "persist_runtime_identity", lambda *args, **kwargs: None)
    monkeypatch.setattr(module, "parse_tree", lambda _workspace_ref: make_tree(module, surfaces, bot_names))

    def fake_launch_assignment_watcher(*args, **kwargs):
        called["watcher_kwargs"] = kwargs
        return {"started": True, "reused": False}

    monkeypatch.setattr(module, "launch_assignment_watcher", fake_launch_assignment_watcher)

    args = argparse.Namespace(
        project_dir=str(project_dir),
        workspace_name=None,
        allow_workspace_name_override=False,
        permission_mode="plan",
        recreate=False,
        bot_name=bot_names,
    )
    result = module.bootstrap(args)

    assert called["reconcile_runtime_mode"] == "pm_only"
    assert called["watcher_kwargs"]["restart_if_running"] is True
    assert called["watcher_kwargs"]["workspace_ref"] == "workspace:1"
    assert called["watcher_kwargs"]["runtime_mode"] == "pm_only"
    assert result["assignment_watcher"] == {"started": True, "reused": False}

def test_launch_claude_agent_uses_current_task_source_in_launch_command(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    module = load_bootstrap_module()
    project_dir = tmp_path
    hook_state_file = project_dir / "hook-state.json"
    hook_state_file.write_text("{}", encoding="utf-8")
    sent_commands: list[str] = []

    monkeypatch.setattr(module, "send_text", lambda _workspace_ref, _surface_ref, text: sent_commands.append(text))

    assignment = {
        "assignment_id": "PM-CURRENT-001",
        "logical_target": "pm-bot",
        "bot_name": "pm-bot",
        "task_source_ref": build_task_source_ref(
            assignment_id="PM-CURRENT-001",
            cycle_id="cycle-001",
            deliverable_path="/Users/busiji/workbot/workspace/memory/tmp/pm-current-001-summary.json",
            evidence_path="/Users/busiji/workbot/workspace/artifacts/cmux-runtime/cmux-assignment.json",
            status="pending",
        ),
    }
    derived_identity = {
        "assignment_id": "PM-CURRENT-001",
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
        "status": "PENDING",
        "audit_round_1_owner": "rea-bot",
    }

    manifest = module.launch_claude_agent(
        "workspace:1",
        "surface:1",
        "pm-bot",
        assignment=assignment,
        lane_identity="pm-bot",
        permission_mode="default",
        project_dir=project_dir,
        project_venv=make_project_venv(module, project_dir),
        hook_state_file=hook_state_file,
        derived_identity=derived_identity,
    )

    assert manifest["assignment_id"] == "PM-CURRENT-001"
    assert manifest["launch_assignment_id"] == "PM-CURRENT-001"
    assert manifest["launch_derived_identity"]["assignment_id"] == "PM-CURRENT-001"
    command_identity = module.extract_json_env_from_launch_command(
        manifest["launch_command"],
        env_name="CMUX_DERIVED_IDENTITY_JSON",
        bot_name="pm-bot",
    )
    assert command_identity["assignment_id"] == "PM-CURRENT-001"
    assert json.dumps(command_identity, ensure_ascii=False, sort_keys=True) == json.dumps(
        manifest["launch_derived_identity"],
        ensure_ascii=False,
        sort_keys=True,
    )
    assert sent_commands and sent_commands[0].strip() == manifest["launch_command"]


def test_launch_claude_agent_blocks_mismatched_task_source_before_send(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    module = load_bootstrap_module()
    project_dir = tmp_path
    hook_state_file = project_dir / "hook-state.json"
    hook_state_file.write_text("{}", encoding="utf-8")
    send_attempted = False

    def track_send(*_args, **_kwargs) -> None:
        nonlocal send_attempted
        send_attempted = True

    monkeypatch.setattr(module, "send_text", track_send)

    assignment = {
        "assignment_id": "PM-CURRENT-002",
        "logical_target": "pm-bot",
        "bot_name": "pm-bot",
        "task_source_ref": build_task_source_ref(
            assignment_id="PM-CURRENT-002",
            cycle_id="cycle-002",
            deliverable_path="/Users/busiji/workbot/workspace/memory/tmp/pm-current-002-summary.json",
            evidence_path="/Users/busiji/workbot/workspace/artifacts/cmux-runtime/cmux-assignment.json",
            status="pending",
        ),
    }
    stale_identity = {
        "assignment_id": "PM-OLD-002",
        "lane_identity": "pm-bot",
        "lane_justification": "stale launch identity",
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
        "status": "PENDING",
        "audit_round_1_owner": "rea-bot",
    }

    with pytest.raises(RuntimeError, match="launch task-source gate blocked"):
        module.launch_claude_agent(
            "workspace:1",
            "surface:1",
            "pm-bot",
            assignment=assignment,
            lane_identity="pm-bot",
            permission_mode="default",
            project_dir=project_dir,
            project_venv=make_project_venv(module, project_dir),
            hook_state_file=hook_state_file,
            derived_identity=stale_identity,
        )

    assert send_attempted is False


def test_list_project_workspaces_detects_browser_only_same_name_residue(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    module = load_bootstrap_module()
    project_dir = tmp_path / "workbot"
    project_dir.mkdir()

    monkeypatch.setattr(
        module,
        "list_workspaces",
        lambda: [{"ref": "workspace:3", "name": "workbot", "selected": True}],
    )
    monkeypatch.setattr(
        module,
        "parse_runtime_tree",
        lambda _workspace_ref: {
            "surface:14": type(
                "BrowserSnapshot",
                (),
                {
                    "surface_type": "browser",
                    "surface_ref": "surface:14",
                    "current_path": "(none)",
                    "title": module.BOARD_PLACEHOLDER_VISIBLE_TITLE,
                },
            )(),
        },
    )

    owned = module.list_project_workspaces(project_dir)

    assert [str(item["ref"]) for item in owned] == ["workspace:3"]


def test_ensure_fresh_workspace_recreate_closes_browser_only_same_name_residue(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    module = load_bootstrap_module()
    project_dir = tmp_path / "workbot"
    project_dir.mkdir()
    commands: list[tuple[str, ...]] = []

    monkeypatch.setattr(
        module,
        "list_workspaces",
        lambda: [{"ref": "workspace:6", "name": "workbot", "selected": True}],
    )
    monkeypatch.setattr(
        module,
        "parse_runtime_tree",
        lambda _workspace_ref: {
            "surface:24": type(
                "BrowserSnapshot",
                (),
                {
                    "surface_type": "browser",
                    "surface_ref": "surface:24",
                    "current_path": "(none)",
                    "title": module.BOARD_PLACEHOLDER_VISIBLE_TITLE,
                },
            )(),
        },
    )
    monkeypatch.setattr(module, "select_workspace_outside_targets", lambda _refs, _cwd: "workspace:99")

    def fake_cmux(*args):
        commands.append(tuple(args))
        if args and args[0] == "new-workspace":
            return "workspace:7"
        return "OK"

    monkeypatch.setattr(module, "cmux", fake_cmux)
    monkeypatch.setattr(module, "parse_workspace_ref", lambda text: text)

    workspace_ref = module.ensure_fresh_workspace("workbot", project_dir, recreate=True)

    assert workspace_ref == "workspace:7"
    assert ("close-workspace", "--workspace", "workspace:6") in commands
    assert ("close-workspace", "--workspace", "workspace:99") in commands


def test_list_project_workspaces_ignores_browser_only_workspace_for_other_project(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    module = load_bootstrap_module()
    project_dir = tmp_path / "workbot"
    project_dir.mkdir()

    monkeypatch.setattr(
        module,
        "list_workspaces",
        lambda: [{"ref": "workspace:9", "name": "not-workbot", "selected": False}],
    )
    monkeypatch.setattr(
        module,
        "parse_runtime_tree",
        lambda _workspace_ref: {
            "surface:22": type(
                "BrowserSnapshot",
                (),
                {
                    "surface_type": "browser",
                    "surface_ref": "surface:22",
                    "current_path": "(none)",
                    "title": module.BOARD_PLACEHOLDER_VISIBLE_TITLE,
                },
            )(),
        },
    )

    owned = module.list_project_workspaces(project_dir)

    assert owned == []
