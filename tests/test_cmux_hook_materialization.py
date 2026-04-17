#!/usr/bin/env python3
from __future__ import annotations

import json
import shlex
import sys
import tempfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
CMUX_SCRIPT_DIR = Path.home() / ".agents" / "skills" / "cmux" / "scripts"
if str(CMUX_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(CMUX_SCRIPT_DIR))

import bootstrap_claude_runtime as bootstrap  # type: ignore  # noqa: E402


BRIDGE_SCRIPT = CMUX_SCRIPT_DIR / "cmux_claude_hook_bridge.py"
REQUIRED_EVENTS = {
    "SessionStart": "session-start",
    "UserPromptSubmit": "prompt-submit",
    "Stop": "stop",
    "Notification": "notification",
}


def _bridge_commands_for_event(payload: dict[str, object], event_name: str) -> list[str]:
    hooks = payload.get("hooks")
    assert isinstance(hooks, dict), "settings.local.json must define a hooks object"
    blocks = hooks.get(event_name)
    assert isinstance(blocks, list), f"{event_name} hook blocks must be a list"
    commands: list[str] = []
    for block in blocks:
        if not isinstance(block, dict):
            continue
        block_hooks = block.get("hooks")
        if not isinstance(block_hooks, list):
            continue
        for hook in block_hooks:
            if not isinstance(hook, dict):
                continue
            if hook.get("type") != "command":
                continue
            command = str(hook.get("command") or "").strip()
            if command:
                commands.append(command)
    return commands


def test_ensure_project_hook_settings_installs_required_relays_idempotently() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        project_dir = Path(tmp)
        settings_path = project_dir / ".claude" / "settings.local.json"
        settings_path.parent.mkdir(parents=True)
        settings_path.write_text(
            json.dumps({"permissions": {"allow": ["Read"]}}, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

        hook_python = project_dir / ".venv" / "bin" / "python"
        hook_python.parent.mkdir(parents=True)
        hook_python.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        hook_python.chmod(0o755)

        bootstrap.ensure_project_hook_settings(project_dir, hook_python=hook_python)
        bootstrap.ensure_project_hook_settings(project_dir, hook_python=hook_python)

        payload = json.loads(settings_path.read_text(encoding="utf-8"))
        permissions = payload.get("permissions")
        assert isinstance(permissions, dict), "permissions block must remain present"
        allow = permissions.get("allow")
        assert isinstance(allow, list) and allow == ["Read"], "existing permissions must be preserved"

        for event_name, relay_event in REQUIRED_EVENTS.items():
            expected = shlex.join([str(hook_python), str(BRIDGE_SCRIPT), relay_event])
            commands = _bridge_commands_for_event(payload, event_name)
            assert commands.count(expected) == 1, f"{event_name} must install exactly one cmux bridge relay"


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
