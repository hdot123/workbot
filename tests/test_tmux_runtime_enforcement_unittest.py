#!/usr/bin/env python3
"""Focused regression tests for tmux-skills runtime token enforcement."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch


os.environ.setdefault("TMUX_SKIP_ENFORCEMENT", "true")

SCRIPTS_DIR = Path("/Users/busiji/workbot/skills/tmux-skills/scripts")
sys.path.insert(0, str(SCRIPTS_DIR))
sys.path.insert(0, str(SCRIPTS_DIR.parent))

import arm_tmux_handoff_watcher  # noqa: E402
import runtime_enforcement  # noqa: E402
import runtime_ledger  # noqa: E402
import start_formal_runtime_chain  # noqa: E402
import watch_tmux_handoff  # noqa: E402


class TmuxRuntimeEnforcementTests(unittest.TestCase):
    def test_enforce_startup_chain_only_accepts_matching_token(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            metadata_path = Path(tmpdir) / "start.lock.json"
            metadata_path.write_text(
                json.dumps({"owner_token": "startup-token-1"}),
                encoding="utf-8",
            )
            with patch.object(runtime_enforcement, "START_CHAIN_LOCK_INFO_PATH", metadata_path):
                with patch.dict(
                    "runtime_enforcement.os.environ",
                    {
                        runtime_enforcement.START_CHAIN_LOCK_TOKEN_ENV: "startup-token-1",
                        "TMUX_SKIP_ENFORCEMENT": "",
                    },
                    clear=False,
                ):
                    with patch("runtime_enforcement._called_from_main_module", return_value=True):
                        runtime_enforcement.enforce_startup_chain_only("init_tmux_env.py")

    def test_enforce_startup_chain_only_rejects_missing_token(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            metadata_path = Path(tmpdir) / "start.lock.json"
            metadata_path.write_text(
                json.dumps({"owner_token": "startup-token-1"}),
                encoding="utf-8",
            )
            with patch.object(runtime_enforcement, "START_CHAIN_LOCK_INFO_PATH", metadata_path):
                with patch.dict(
                    "runtime_enforcement.os.environ",
                    {"TMUX_SKIP_ENFORCEMENT": ""},
                    clear=True,
                ):
                    with patch("runtime_enforcement._called_from_main_module", return_value=True):
                        with self.assertRaises(SystemExit) as exc:
                            runtime_enforcement.enforce_startup_chain_only("init_tmux_env.py")

        self.assertIn("requires startup_chain token", str(exc.exception))

    def test_enforce_runtime_owner_only_accepts_matching_token(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            ledger_path = Path(tmpdir) / "current-runtime.json"
            ledger_path.write_text(
                json.dumps({"runtime_owner_token": "runtime-token-1"}),
                encoding="utf-8",
            )
            with patch.object(runtime_enforcement, "CURRENT_RUNTIME_LEDGER_PATH", ledger_path):
                with patch.dict(
                    "runtime_enforcement.os.environ",
                    {
                        runtime_enforcement.RUNTIME_OWNER_TOKEN_ENV: "runtime-token-1",
                        "TMUX_SKIP_ENFORCEMENT": "",
                    },
                    clear=False,
                ):
                    with patch("runtime_enforcement._called_from_main_module", return_value=True):
                        runtime_enforcement.enforce_runtime_owner_only("watch_tmux_handoff.py")

    def test_enforce_runtime_owner_only_rejects_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            ledger_path = Path(tmpdir) / "current-runtime.json"
            ledger_path.write_text(
                json.dumps({"runtime_owner_token": "runtime-token-1"}),
                encoding="utf-8",
            )
            with patch.object(runtime_enforcement, "CURRENT_RUNTIME_LEDGER_PATH", ledger_path):
                with patch.dict(
                    "runtime_enforcement.os.environ",
                    {
                        runtime_enforcement.RUNTIME_OWNER_TOKEN_ENV: "runtime-token-2",
                        "TMUX_SKIP_ENFORCEMENT": "",
                    },
                    clear=False,
                ):
                    with patch("runtime_enforcement._called_from_main_module", return_value=True):
                        with self.assertRaises(SystemExit) as exc:
                            runtime_enforcement.enforce_runtime_owner_only("watch_tmux_handoff.py")

        self.assertIn("invalid runtime_owner token", str(exc.exception))

    def test_init_current_runtime_ledger_persists_runtime_owner_token(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            ledger_path = Path(tmpdir) / "current-runtime.json"
            with patch.object(runtime_ledger, "CURRENT_RUNTIME_LEDGER_PATH", ledger_path):
                ledger = runtime_ledger.init_current_runtime_ledger(
                    "task-1",
                    pane_count=2,
                    runtime_owner_token="runtime-token-1",
                )
                persisted = json.loads(ledger_path.read_text(encoding="utf-8"))

        self.assertEqual("runtime-token-1", ledger["runtime_owner_token"])
        self.assertEqual("runtime-token-1", persisted["runtime_owner_token"])

    def test_run_runtime_activation_prelaunch_passes_runtime_owner_token_to_ledger(self) -> None:
        steps: dict[str, object] = {}
        with patch.dict("start_formal_runtime_chain.os.environ", {}, clear=True):
            with patch("start_formal_runtime_chain.secrets.token_hex", return_value="runtime-token-1"):
                with patch("start_formal_runtime_chain.set_orchestrator_context"):
                    with patch("start_formal_runtime_chain.bind_tmux_thread_id", return_value={"CODEX_THREAD_ID": "thread-1"}):
                        with patch("start_formal_runtime_chain.run_json_script", return_value={"ok": True}) as mock_run_json:
                            with patch("start_formal_runtime_chain.normalize_pane_surfaces", return_value={"current_target": "formal-session:1.1"}):
                                with patch("start_formal_runtime_chain.write_chain_context"):
                                    start_formal_runtime_chain.run_runtime_activation_prelaunch(
                                        "formal-session",
                                        "task-1",
                                        "thread-1",
                                        2,
                                        [
                                            {"slot": "pane_1", "pane_title": "dev-bot", "target": "formal-session:1.1"},
                                            {"slot": "pane_2", "pane_title": "qa-bot", "target": "formal-session:1.2"},
                                        ],
                                        "fingerprint-1",
                                        ["formal-session:1.1", "formal-session:1.2"],
                                        steps,
                                    )
                                    env_token = start_formal_runtime_chain.os.environ[
                                        start_formal_runtime_chain.RUNTIME_OWNER_TOKEN_ENV
                                    ]

                                    ledger_args = mock_run_json.call_args.args[1]
        self.assertIn("--runtime-owner-token", ledger_args)
        self.assertIn("runtime-token-1", ledger_args)
        self.assertEqual("runtime-token-1", env_token)

    def test_start_watcher_sets_runtime_owner_token_in_child_env(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            stdout_log = Path(tmpdir) / "watcher.log"
            with patch("arm_tmux_handoff_watcher.subprocess.Popen", return_value=Mock(pid=321)) as mock_popen:
                pid = arm_tmux_handoff_watcher.start_watcher(
                    ["python", "watch_tmux_handoff.py"],
                    stdout_log,
                    runtime_owner_token="runtime-token-1",
                )

        self.assertEqual(321, pid)
        self.assertEqual(
            "runtime-token-1",
            mock_popen.call_args.kwargs["env"][runtime_enforcement.RUNTIME_OWNER_TOKEN_ENV],
        )

    def test_spawn_delivery_runner_inherits_runtime_owner_token(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            event_file = Path(tmpdir) / "event.json"
            event_file.write_text(json.dumps({"event": "pane_stopped"}), encoding="utf-8")
            stdout_log = Path(tmpdir) / "delivery.log"
            with patch.dict(
                "watch_tmux_handoff.os.environ",
                {runtime_enforcement.RUNTIME_OWNER_TOKEN_ENV: "runtime-token-1"},
                clear=False,
            ):
                with patch("watch_tmux_handoff.subprocess.Popen", return_value=Mock(pid=654)) as mock_popen:
                    pid = watch_tmux_handoff.spawn_delivery_runner(
                        event_file,
                        delivery_script="/tmp/deliver_tmux_handoff_notification.py",
                        session_mode="fixed",
                        dry_run=False,
                        stdout_log=str(stdout_log),
                    )

        self.assertEqual(654, pid)
        self.assertEqual(
            "runtime-token-1",
            mock_popen.call_args.kwargs["env"][runtime_enforcement.RUNTIME_OWNER_TOKEN_ENV],
        )

    def test_direct_watch_script_is_blocked_before_argparse(self) -> None:
        env = dict(os.environ)
        env.pop("TMUX_SKIP_ENFORCEMENT", None)
        env.pop(runtime_enforcement.RUNTIME_OWNER_TOKEN_ENV, None)

        proc = subprocess.run(
            [
                sys.executable,
                str(SCRIPTS_DIR / "watch_tmux_handoff.py"),
            ],
            capture_output=True,
            text=True,
            env=env,
            check=False,
        )

        self.assertEqual(1, proc.returncode)
        self.assertIn("requires runtime_owner token", proc.stderr)
        self.assertNotIn("at least one --target is required", proc.stderr)


if __name__ == "__main__":
    unittest.main()
