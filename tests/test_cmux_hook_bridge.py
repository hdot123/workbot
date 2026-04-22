#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import stat
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent
BRIDGE_SCRIPT = Path.home() / ".agents" / "skills" / "cmux" / "scripts" / "cmux_claude_hook_bridge.py"


def _write_fake_cmux(bin_dir: Path) -> Path:
    script_path = bin_dir / "cmux"
    script_path.write_text(
        """#!/usr/bin/env python3
from __future__ import annotations

import json
import sys

args = sys.argv[1:]
if args[:1] == ["identify"]:
    print(json.dumps({"caller": {"workspace_ref": "workspace:canon", "surface_ref": "surface:canon"}}))
    raise SystemExit(0)
if args[:2] == ["claude-hook", "session-start"]:
    raise SystemExit(0)
if args[:2] == ["claude-hook", "prompt-submit"]:
    raise SystemExit(0)
if args[:2] == ["claude-hook", "stop"]:
    raise SystemExit(0)
if args[:2] == ["claude-hook", "notification"]:
    raise SystemExit(0)
raise SystemExit(1)
""",
        encoding="utf-8",
    )
    script_path.chmod(script_path.stat().st_mode | stat.S_IXUSR)
    return script_path


def _run_bridge(
    event_name: str,
    state_file: Path,
    env: dict[str, str],
    *,
    expected_returncode: int = 0,
) -> subprocess.CompletedProcess[str]:
    payload = {
        "session_id": f"{event_name}-session",
        "cwd": env.get("CMUX_PROJECT_DIR", str(REPO_ROOT)),
    }
    proc = subprocess.run(
        [
            sys.executable,
            str(BRIDGE_SCRIPT),
            event_name,
            "--workspace",
            "workspace:raw",
            "--surface",
            "surface:raw",
            "--state-file",
            str(state_file),
        ],
        input=json.dumps(payload, ensure_ascii=False),
        text=True,
        capture_output=True,
        check=False,
        env=env,
    )
    assert proc.returncode == expected_returncode, (
        proc.stderr or proc.stdout or f"bridge failed for {event_name}; rc={proc.returncode}"
    )
    return proc


def _write_assignment_file(
    assignment_file: Path,
    *,
    workspace_ref: str,
    surface_ref: str,
    status: str = "ACTIVE",
    session_class: str = "formal_cmux_worker",
) -> None:
    assignment_file.write_text(
        json.dumps(
            {
                "assignments": [
                    {
                        "logical_target": "pm-bot",
                        "bot_name": "pm-bot",
                        "assignment_id": "pm#1",
                        "workspace_ref": workspace_ref,
                        "pane_ref": "pane:canon",
                        "surface_ref": surface_ref,
                        "title": "pm-bot",
                        "goal": "test",
                        "task_kind": "assignment",
                        "audit_round_1_owner": "rea-bot",
                        "audit_round_1_status": "pending",
                        "audit_round_2_owner": "codex",
                        "audit_round_2_status": "pending",
                        "status": status,
                        "session_class": session_class,
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def _write_runtime_launch_manifest(
    runtime_dir: Path,
    *,
    bot_name: str = "pm-bot",
    assignment_id: str = "pm#1",
    workspace_ref: str,
    surface_ref: str,
    lane_identity: str | None = None,
    logical_target: str | None = None,
) -> None:
    lane_identity = lane_identity or bot_name
    logical_target = logical_target or bot_name
    derived_identity = {
        "assignment_id": assignment_id,
        "lane_identity": lane_identity,
        "logical_target": logical_target,
        "bot_name": bot_name,
    }
    manifest = {
        "bot_name": bot_name,
        "assignment_id": assignment_id,
        "lane_identity": lane_identity,
        "lane_justification": "test launch",
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
        "launch_lane_identity": lane_identity,
        "launch_lane_justification": "test launch",
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


def _require_bridge_script() -> None:
    if not BRIDGE_SCRIPT.exists():
        pytest.skip(f"missing bridge script: {BRIDGE_SCRIPT}")


def test_cmux_hook_bridge_records_all_required_event_counters() -> None:
    _require_bridge_script()
    with tempfile.TemporaryDirectory() as tmp:
        temp_dir = Path(tmp)
        fake_bin = temp_dir / "bin"
        fake_bin.mkdir(parents=True)
        _write_fake_cmux(fake_bin)
        state_file = temp_dir / "hook-state.json"
        _write_assignment_file(
            temp_dir / "cmux-assignment.json",
            workspace_ref="workspace:canon",
            surface_ref="surface:canon",
        )
        _write_runtime_launch_manifest(
            temp_dir,
            workspace_ref="workspace:canon",
            surface_ref="surface:canon",
        )

        env = os.environ.copy()
        env["PATH"] = f"{fake_bin}:{env.get('PATH', '')}"
        env["CMUX_PROJECT_DIR"] = str(temp_dir)

        _run_bridge("session-start", state_file, env)
        _run_bridge("prompt-submit", state_file, env)
        _run_bridge("stop", state_file, env)
        _run_bridge("notification", state_file, env)

        payload = json.loads(state_file.read_text(encoding="utf-8"))
        surface_state = payload["surfaces"]["surface:canon"]
        assert surface_state["workspace_ref"] == "workspace:canon"
        assert surface_state["surface_ref"] == "surface:canon"
        assert surface_state["session_start_count"] == 1
        assert surface_state["prompt_submit_count"] == 1
        assert surface_state["stop_count"] == 1
        assert surface_state["notification_count"] == 1
        assert surface_state["guard_violation_count"] == 0
        assert surface_state["adhoc_prompt_count"] == 0
        assert surface_state["last_event"] == "notification"
        assert surface_state["last_session_id"] == "notification-session"
        assert surface_state["last_cwd"] == str(temp_dir)


def test_cmux_hook_bridge_records_guard_violation_for_prompt_without_active_assignment() -> None:
    _require_bridge_script()
    with tempfile.TemporaryDirectory() as tmp:
        temp_dir = Path(tmp)
        fake_bin = temp_dir / "bin"
        fake_bin.mkdir(parents=True)
        _write_fake_cmux(fake_bin)
        state_file = temp_dir / "hook-state.json"

        env = os.environ.copy()
        env["PATH"] = f"{fake_bin}:{env.get('PATH', '')}"
        env["CMUX_PROJECT_DIR"] = str(temp_dir)

        proc = _run_bridge("prompt-submit", state_file, env, expected_returncode=3)
        error_payload = json.loads(proc.stderr.strip())
        assert error_payload["error"] == "prompt_without_active_assignment"

        payload = json.loads(state_file.read_text(encoding="utf-8"))
        surface_state = payload["surfaces"]["surface:canon"]
        assert surface_state["prompt_submit_count"] == 1
        assert surface_state["guard_violation_count"] == 1
        assert surface_state["adhoc_prompt_count"] == 1
        assert surface_state["last_guard_violation"] == "prompt_without_active_assignment"


def test_cmux_hook_bridge_records_guard_violation_for_non_formal_session_class() -> None:
    _require_bridge_script()
    with tempfile.TemporaryDirectory() as tmp:
        temp_dir = Path(tmp)
        fake_bin = temp_dir / "bin"
        fake_bin.mkdir(parents=True)
        _write_fake_cmux(fake_bin)
        state_file = temp_dir / "hook-state.json"
        _write_assignment_file(
            temp_dir / "cmux-assignment.json",
            workspace_ref="workspace:canon",
            surface_ref="surface:canon",
            session_class="external_session",
        )

        env = os.environ.copy()
        env["PATH"] = f"{fake_bin}:{env.get('PATH', '')}"
        env["CMUX_PROJECT_DIR"] = str(temp_dir)

        proc = _run_bridge("prompt-submit", state_file, env, expected_returncode=4)
        error_payload = json.loads(proc.stderr.strip())
        assert error_payload["error"] == "prompt_submit_non_formal_session_class"

        payload = json.loads(state_file.read_text(encoding="utf-8"))
        surface_state = payload["surfaces"]["surface:canon"]
        assert surface_state["prompt_submit_count"] == 1
        assert surface_state["guard_violation_count"] == 1
        assert surface_state["adhoc_prompt_count"] == 0
        assert surface_state["last_guard_violation"] == "prompt_submit_non_formal_session_class"


def test_cmux_hook_bridge_records_guard_violation_for_launch_provenance_mismatch() -> None:
    _require_bridge_script()
    with tempfile.TemporaryDirectory() as tmp:
        temp_dir = Path(tmp)
        fake_bin = temp_dir / "bin"
        fake_bin.mkdir(parents=True)
        _write_fake_cmux(fake_bin)
        state_file = temp_dir / "hook-state.json"
        _write_assignment_file(
            temp_dir / "cmux-assignment.json",
            workspace_ref="workspace:canon",
            surface_ref="surface:canon",
        )
        _write_runtime_launch_manifest(
            temp_dir,
            assignment_id="idle-pm-bot",
            workspace_ref="workspace:canon",
            surface_ref="surface:canon",
        )

        env = os.environ.copy()
        env["PATH"] = f"{fake_bin}:{env.get('PATH', '')}"
        env["CMUX_PROJECT_DIR"] = str(temp_dir)

        proc = _run_bridge("prompt-submit", state_file, env, expected_returncode=5)
        error_payload = json.loads(proc.stderr.strip())
        assert error_payload["error"] == "prompt_submit_launch_provenance_mismatch"
        assert error_payload["manifest_exists"] is True
        assert error_payload["mismatches"]["assignment_id"]["expected"] == "pm#1"
        assert error_payload["mismatches"]["assignment_id"]["actual"] == "idle-pm-bot"

        payload = json.loads(state_file.read_text(encoding="utf-8"))
        surface_state = payload["surfaces"]["surface:canon"]
        assert surface_state["prompt_submit_count"] == 1
        assert surface_state["guard_violation_count"] == 1
        assert surface_state["adhoc_prompt_count"] == 1
        assert surface_state["last_guard_violation"] == "prompt_submit_launch_provenance_mismatch"


def test_cmux_hook_bridge_fails_closed_when_required_context_missing() -> None:
    _require_bridge_script()
    with tempfile.TemporaryDirectory() as tmp:
        temp_dir = Path(tmp)
        fake_bin = temp_dir / "bin"
        fake_bin.mkdir(parents=True)
        _write_fake_cmux(fake_bin)

        base_env = os.environ.copy()
        base_env["PATH"] = f"{fake_bin}:{base_env.get('PATH', '')}"
        base_env.pop("CMUX_WORKSPACE_ID", None)
        base_env.pop("CMUX_SURFACE_ID", None)
        base_env.pop("CMUX_HOOK_STATE_FILE", None)
        base_env.pop("CMUX_PROJECT_DIR", None)

        scenarios = [
            (
                "workspace",
                [
                    sys.executable,
                    str(BRIDGE_SCRIPT),
                    "session-start",
                    "--surface",
                    "surface:raw",
                    "--state-file",
                    str(temp_dir / "hook-state-a.json"),
                ],
            ),
            (
                "surface",
                [
                    sys.executable,
                    str(BRIDGE_SCRIPT),
                    "session-start",
                    "--workspace",
                    "workspace:raw",
                    "--state-file",
                    str(temp_dir / "hook-state-b.json"),
                ],
            ),
            (
                "state_file",
                [
                    sys.executable,
                    str(BRIDGE_SCRIPT),
                    "session-start",
                    "--workspace",
                    "workspace:raw",
                    "--surface",
                    "surface:raw",
                ],
            ),
        ]

        for expected_missing, command in scenarios:
            proc = subprocess.run(
                command,
                input="{}",
                text=True,
                capture_output=True,
                check=False,
                env=base_env,
            )
            assert proc.returncode == 2
            payload = json.loads(proc.stderr.strip())
            assert payload["error"] == "missing_hook_context"
            assert expected_missing in payload["missing"]


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    passed = 0
    failed = 0
    for fn in tests:
        try:
            fn()
            passed += 1
            print(f"  PASS  {fn.__name__}")
        except Exception as exc:  # noqa: BLE001
            failed += 1
            print(f"  FAIL  {fn.__name__}: {exc}")
    print(f"\n{passed} passed, {failed} failed out of {passed + failed}")
    sys.exit(1 if failed else 0)
