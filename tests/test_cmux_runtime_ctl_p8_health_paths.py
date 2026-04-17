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
