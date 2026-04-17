#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import stat
import subprocess
import sys
import tempfile
from pathlib import Path


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


def _run_bridge(event_name: str, state_file: Path, env: dict[str, str]) -> None:
    payload = {
        "session_id": f"{event_name}-session",
        "cwd": str(REPO_ROOT),
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
    assert proc.returncode == 0, proc.stderr or proc.stdout or f"bridge failed for {event_name}"


def test_cmux_hook_bridge_records_all_required_event_counters() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        temp_dir = Path(tmp)
        fake_bin = temp_dir / "bin"
        fake_bin.mkdir(parents=True)
        _write_fake_cmux(fake_bin)
        state_file = temp_dir / "hook-state.json"

        env = os.environ.copy()
        env["PATH"] = f"{fake_bin}:{env.get('PATH', '')}"

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
        assert surface_state["last_event"] == "notification"
        assert surface_state["last_session_id"] == "notification-session"
        assert surface_state["last_cwd"] == str(REPO_ROOT)


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
