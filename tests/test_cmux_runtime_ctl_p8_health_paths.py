from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

CMUX_SCRIPT_DIR = Path.home() / ".agents" / "skills" / "cmux" / "scripts"
CMUX_RUNTIME_CTL_PATH = CMUX_SCRIPT_DIR / "cmux_runtime_ctl.py"


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


def run_print_status(
    module,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    *,
    live_runtime: dict[str, object],
    assignment_file: str = "/tmp/cmux-assignment.json",
    assignment_runtime: dict[str, object] | None = None,
    watcher_runtime: dict[str, object] | None = None,
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
            "error": "",
        }

    monkeypatch.setattr(module, "load_assignment_runtime_or_error", lambda _: (assignment_runtime, None))
    monkeypatch.setattr(module, "inspect_live_runtime", lambda _: live_runtime)
    monkeypatch.setattr(module, "inspect_watcher_runtime", lambda _: watcher_runtime)
    rc = module.print_status(SimpleNamespace(assignment_file=assignment_file))
    payload = json.loads(capsys.readouterr().out)
    return rc, payload


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
            "error": "watcher_pid_file_missing",
        },
    )
    assert rc == 1
    assert payload["healthy"] is False
    assert payload["watcher_required"] is True
    assert payload["watcher_guard_healthy"] is False
