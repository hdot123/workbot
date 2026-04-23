#!/usr/bin/env python3
"""P7 tests: hook mainline preflight gates and identify normalization."""

from __future__ import annotations

import io
import json
import os
import stat
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

repo_root = Path(__file__).resolve().parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from workspace.tools import memory_hook_gateway as gateway
from workspace.tools.memory_hook_impls import ClaudeDelegate


def _write_fake_cmux(bin_dir: Path, *, identify_stdout: str) -> Path:
    script_path = bin_dir / "cmux"
    script_path.write_text(
        """#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

args = sys.argv[1:]
log_path = os.environ.get("CMUX_TEST_LOG")
if log_path:
    with Path(log_path).open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(args, ensure_ascii=False) + "\\n")
if args[:1] == ["identify"]:
    sys.stdout.write(os.environ.get("CMUX_IDENTIFY_STDOUT", ""))
    raise SystemExit(0)
if args[:2] == ["claude-hook", "session-start"]:
    sys.stdout.write("hook-ok\\n")
    raise SystemExit(0)
if args[:1] == ["codex-hook"]:
    sys.stdout.write("hook-ok\\n")
    raise SystemExit(0)
raise SystemExit(1)
""",
        encoding="utf-8",
    )
    script_path.chmod(script_path.stat().st_mode | stat.S_IXUSR)
    return script_path


def _ok_package() -> dict[str, object]:
    return {
        "status": "ok",
        "host": "claude",
        "event": "session-start",
        "project_scope": "workbot",
        "cwd": str(repo_root),
        "missing_paths": [],
        "validation_errors": [],
        "system_context": {},
    }


def test_claude_delegate_requires_hook_state_file_fail_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CMUX_HOOK_STATE_FILE", raising=False)
    delegate = ClaudeDelegate(
        workspace_id="workspace:1",
        surface_id="surface:1",
        state_file=None,
        which_cmd=lambda _: "/fake/cmux",
        runner=lambda *args, **kwargs: None,  # pragma: no cover - should not run
    )
    with pytest.raises(RuntimeError, match="missing required env: CMUX_HOOK_STATE_FILE"):
        delegate.execute("session-start", "{}", {})


def test_canonicalize_cmux_refs_uses_identify_output(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(parents=True)
    _write_fake_cmux(
        bin_dir,
        identify_stdout='{"caller":{"workspace_ref":"workspace:canon","surface_ref":"surface:canon"}}',
    )
    monkeypatch.setenv("PATH", f"{bin_dir}:{os.environ.get('PATH', '')}")
    monkeypatch.setenv(
        "CMUX_IDENTIFY_STDOUT",
        '{"caller":{"workspace_ref":"workspace:canon","surface_ref":"surface:canon"}}',
    )
    workspace_ref, surface_ref = gateway.canonicalize_cmux_refs("workspace:raw", "surface:raw")
    assert workspace_ref == "workspace:canon"
    assert surface_ref == "surface:canon"


def test_canonicalize_cmux_refs_falls_back_when_identify_payload_invalid(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(parents=True)
    _write_fake_cmux(bin_dir, identify_stdout="not-json")
    monkeypatch.setenv("PATH", f"{bin_dir}:{os.environ.get('PATH', '')}")
    monkeypatch.setenv("CMUX_IDENTIFY_STDOUT", "not-json")
    workspace_ref, surface_ref = gateway.canonicalize_cmux_refs("workspace:raw", "surface:raw")
    assert workspace_ref == "workspace:raw"
    assert surface_ref == "surface:raw"


def test_main_delegate_on_claude_runs_real_hook_path(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(parents=True)
    _write_fake_cmux(
        bin_dir,
        identify_stdout='{"caller":{"workspace_ref":"workspace:canon","surface_ref":"surface:canon"}}',
    )
    log_path = tmp_path / "cmux-calls.jsonl"
    state_file = tmp_path / "hook-state.json"
    monkeypatch.setenv("PATH", f"{bin_dir}:{os.environ.get('PATH', '')}")
    monkeypatch.setenv("CMUX_TEST_LOG", str(log_path))
    monkeypatch.setenv(
        "CMUX_IDENTIFY_STDOUT",
        '{"caller":{"workspace_ref":"workspace:canon","surface_ref":"surface:canon"}}',
    )
    monkeypatch.setenv("CMUX_WORKSPACE_ID", "workspace:raw")
    monkeypatch.setenv("CMUX_SURFACE_ID", "surface:raw")
    monkeypatch.setenv("CMUX_HOOK_STATE_FILE", str(state_file))

    monkeypatch.setattr(
        gateway,
        "parse_args",
        lambda: SimpleNamespace(host="claude", event="session-start", no_delegate=False),
    )
    monkeypatch.setattr(gateway, "should_noop_for_external_context", lambda payload: False)
    monkeypatch.setattr(gateway, "build_context_package", lambda host, event, payload: _ok_package())
    monkeypatch.setattr(
        gateway,
        "write_artifacts",
        lambda package: {"snapshot": str(tmp_path / "snapshot.json"), "latest": str(tmp_path / "latest.json")},
    )
    monkeypatch.setattr(gateway.sys, "stdin", io.StringIO(json.dumps({"session_id": "sess-1", "cwd": str(repo_root)})))

    rc = gateway.main()
    assert rc == 0
    payload = json.loads(state_file.read_text(encoding="utf-8"))
    surface = payload["surfaces"]["surface:canon"]
    assert surface["workspace_ref"] == "workspace:canon"
    assert surface["surface_ref"] == "surface:canon"
    assert surface["session_start_count"] == 1
    assert surface["last_session_id"] == "sess-1"

    calls = [
        json.loads(line)
        for line in log_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert any(call[:1] == ["identify"] for call in calls)
    assert any(call[:2] == ["claude-hook", "session-start"] for call in calls)


def test_main_delegate_on_claude_fails_closed_when_state_file_missing(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(parents=True)
    _write_fake_cmux(
        bin_dir,
        identify_stdout='{"caller":{"workspace_ref":"workspace:canon","surface_ref":"surface:canon"}}',
    )
    monkeypatch.setenv("PATH", f"{bin_dir}:{os.environ.get('PATH', '')}")
    monkeypatch.setenv("CMUX_WORKSPACE_ID", "workspace:raw")
    monkeypatch.setenv("CMUX_SURFACE_ID", "surface:raw")
    monkeypatch.delenv("CMUX_HOOK_STATE_FILE", raising=False)

    monkeypatch.setattr(
        gateway,
        "parse_args",
        lambda: SimpleNamespace(host="claude", event="session-start", no_delegate=False),
    )
    monkeypatch.setattr(gateway, "should_noop_for_external_context", lambda payload: False)
    monkeypatch.setattr(gateway, "build_context_package", lambda host, event, payload: _ok_package())
    monkeypatch.setattr(
        gateway,
        "write_artifacts",
        lambda package: {"snapshot": str(tmp_path / "snapshot.json"), "latest": str(tmp_path / "latest.json")},
    )
    monkeypatch.setattr(gateway.sys, "stdin", io.StringIO(json.dumps({"session_id": "sess-2", "cwd": str(repo_root)})))

    rc = gateway.main()
    assert rc == 1


def test_main_delegate_on_codex_runs_real_hook_path(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(parents=True)
    _write_fake_cmux(
        bin_dir,
        identify_stdout='{"caller":{"workspace_ref":"workspace:canon","surface_ref":"surface:canon"}}',
    )
    log_path = tmp_path / "cmux-calls-codex.jsonl"
    monkeypatch.setenv("PATH", f"{bin_dir}:{os.environ.get('PATH', '')}")
    monkeypatch.setenv("CMUX_TEST_LOG", str(log_path))
    monkeypatch.setenv("CMUX_SURFACE_ID", "surface:raw")

    monkeypatch.setattr(
        gateway,
        "parse_args",
        lambda: SimpleNamespace(host="codex", event="prompt-submit", no_delegate=False),
    )
    monkeypatch.setattr(gateway, "should_noop_for_external_context", lambda payload: False)
    monkeypatch.setattr(gateway, "build_context_package", lambda host, event, payload: _ok_package())
    monkeypatch.setattr(
        gateway,
        "write_artifacts",
        lambda package: {"snapshot": str(tmp_path / "snapshot.json"), "latest": str(tmp_path / "latest.json")},
    )
    monkeypatch.setattr(gateway.sys, "stdin", io.StringIO(json.dumps({"session_id": "sess-3", "cwd": str(repo_root)})))

    rc = gateway.main()
    assert rc == 0
    calls = [
        json.loads(line)
        for line in log_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert any(call[:2] == ["codex-hook", "prompt-submit"] for call in calls)


def test_main_delegate_on_codex_skips_delegate_when_surface_missing(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(parents=True)
    _write_fake_cmux(
        bin_dir,
        identify_stdout='{"caller":{"workspace_ref":"workspace:canon","surface_ref":"surface:canon"}}',
    )
    log_path = tmp_path / "cmux-calls-codex-missing-surface.jsonl"
    monkeypatch.setenv("PATH", f"{bin_dir}:{os.environ.get('PATH', '')}")
    monkeypatch.setenv("CMUX_TEST_LOG", str(log_path))
    monkeypatch.delenv("CMUX_SURFACE_ID", raising=False)
    monkeypatch.delenv("CMUX_WORKSPACE_ID", raising=False)
    monkeypatch.delenv("CMUX_HOOK_STATE_FILE", raising=False)
    monkeypatch.delenv("CMUX_PROJECT_DIR", raising=False)

    monkeypatch.setattr(
        gateway,
        "parse_args",
        lambda: SimpleNamespace(host="codex", event="prompt-submit", no_delegate=False),
    )
    monkeypatch.setattr(gateway, "should_noop_for_external_context", lambda payload: False)
    monkeypatch.setattr(gateway, "build_context_package", lambda host, event, payload: _ok_package())
    monkeypatch.setattr(
        gateway,
        "write_artifacts",
        lambda package: {"snapshot": str(tmp_path / "snapshot.json"), "latest": str(tmp_path / "latest.json")},
    )
    monkeypatch.setattr(gateway.sys, "stdin", io.StringIO(json.dumps({"session_id": "sess-4", "cwd": str(repo_root)})))

    rc = gateway.main()
    assert not log_path.exists()
    assert rc == 0


def test_main_delegate_on_codex_fails_closed_when_surface_missing_inside_formal_runtime(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    bin_dir = tmp_path / "bin-formal"
    bin_dir.mkdir(parents=True)
    _write_fake_cmux(
        bin_dir,
        identify_stdout='{"caller":{"workspace_ref":"workspace:canon","surface_ref":"surface:canon"}}',
    )
    monkeypatch.setenv("PATH", f"{bin_dir}:{os.environ.get('PATH', '')}")
    monkeypatch.delenv("CMUX_SURFACE_ID", raising=False)
    monkeypatch.setenv("CMUX_WORKSPACE_ID", "workspace:raw")
    monkeypatch.delenv("CMUX_HOOK_STATE_FILE", raising=False)
    monkeypatch.delenv("CMUX_PROJECT_DIR", raising=False)

    monkeypatch.setattr(
        gateway,
        "parse_args",
        lambda: SimpleNamespace(host="codex", event="prompt-submit", no_delegate=False),
    )
    monkeypatch.setattr(gateway, "should_noop_for_external_context", lambda payload: False)
    monkeypatch.setattr(gateway, "build_context_package", lambda host, event, payload: _ok_package())
    monkeypatch.setattr(
        gateway,
        "write_artifacts",
        lambda package: {"snapshot": str(tmp_path / "snapshot.json"), "latest": str(tmp_path / "latest.json")},
    )
    monkeypatch.setattr(gateway.sys, "stdin", io.StringIO(json.dumps({"session_id": "sess-5", "cwd": str(repo_root)})))

    rc = gateway.main()
    assert rc == 1
