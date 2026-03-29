#!/usr/bin/env python3
"""Regression tests for the runtime-only tmux-skills handoff chain."""

from __future__ import annotations

import argparse
import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch


SCRIPTS_DIR = Path("/Users/busiji/workbot/skills/tmux-skills/scripts")
sys.path.insert(0, str(SCRIPTS_DIR))

import build_tmux_handoff_bundle  # noqa: E402
import check_tmux_ready  # noqa: E402
import start_formal_runtime_chain  # noqa: E402
import tmux_runtime_common  # noqa: E402
import verify_pane_identity  # noqa: E402
import watch_tmux_handoff  # noqa: E402
import write_tmux_notifications_sqlite  # noqa: E402


def sample_event(event_type: str, *, deliverable: bool = True) -> dict[str, object]:
    prompt = "Do you want to proceed?\n1. Yes\n2. No"
    return {
        "event": event_type,
        "event_id": "0123456789abcdef",
        "detected_at": "2026-03-28T10:00:00+00:00",
        "target": "formal-session:1.3",
        "session": "formal-session",
        "window": "1",
        "pane_id": "%3",
        "pane_title": "qa-bot",
        "cwd": "/Users/busiji/workbot",
        "current_command": "node",
        "state_class": "sop_approval" if event_type == "pane_attention" else "pane_checkin",
        "state_label": "审批" if event_type == "pane_attention" else "巡检",
        "reachable": True,
        "deliverable": deliverable,
        "prompt": prompt,
        "prompt_headline": "Do you want to proceed?",
        "option_lines": ["1. Yes", "2. No"],
        "recent_output": prompt,
        "signature": "0123456789ab",
        "source": "tmux-skills",
    }


def sample_runtime_snapshot(*, monitor_target: str = "formal-session:1.3") -> dict[str, object]:
    panes = []
    titles = ["dev-bot", "dev-bot", "qa-bot", "qa-bot", "doc-bot", "doc-bot"]
    for index, title in enumerate(titles, start=1):
        panes.append(
            {
                "target": f"formal-session:1.{index}",
                "session_name": "formal-session",
                "pane_id": f"%{index}",
                "pane_title": title,
                "pane_title_normalized": title,
                "claude_entered": True,
                "is_bot_named": True,
            }
        )
    return {
        "session_count": 1,
        "pane_count": 4,
        "sessions": [
            {
                "session_name": "formal-session",
                "attached": 1,
                "is_formal": True,
            }
        ],
        "panes": panes,
        "formal_sessions": ["formal-session"],
        "bootstrap_sessions": [],
        "bootstrap_pane_count": 0,
        "official_formal_pane_count": 4,
        "CODEX_THREAD_ID": "deadbeef",
        "bell_armed": True,
        "bell_processes": [
            {
                "pid": 123,
                "command": (
                    "python3 /Users/busiji/workbot/skills/tmux-skills/scripts/"
                    "watch_tmux_handoff.py "
                    "--target formal-session:1.1 "
                    "--target formal-session:1.2 "
                    "--target formal-session:1.3 "
                    "--target formal-session:1.4 "
                    "--deliver"
                ),
            }
        ],
        "runtime_ledger_present": True,
        "runtime_ledger_path": "/tmp/current-runtime.json",
        "runtime_ledger": {
            "task_id": "test-task",
            "formal_session_name": "formal-session",
            "pane_count": 4,
            "topology_fingerprint": "abc123",
            "slot_bindings": {
                "task_primary": {"role": "dev-bot", "target": "formal-session:1.1"},
                "task_secondary": {"role": "dev-bot", "target": "formal-session:1.2"},
                "monitor": {"role": "qa-bot", "target": monitor_target},
                "doc_primary": {"role": "doc-bot", "target": "formal-session:1.4"},
            },
            "watcher": {
                "armed": True,
                "targets": [f"formal-session:1.{index}" for index in range(1, 5)],
                "pid": 123,
                "transport": "codex",
            },
            "codex_thread_bound": True,
            "worker_ceiling": 3,
            "runtime_status": "INIT_IN_PROGRESS",
        },
        "topology_fingerprint": "abc123",
    }


class TmuxSkillsHandoffTests(unittest.TestCase):
    def test_writer_accepts_runtime_only_event_types(self) -> None:
        for event_type in ("pane_attention", "pane_checkin", "pane_snapshot", "runtime_blocked"):
            with self.subTest(event_type=event_type):
                event = sample_event(event_type, deliverable=event_type != "runtime_blocked")
                if event_type == "runtime_blocked":
                    event["state_class"] = "runtime_blocked"
                    event["state_label"] = "恢复"
                    event["deliverable"] = False
                instructions = write_tmux_notifications_sqlite.normalize_instructions(event)
                self.assertEqual(1, len(instructions))
                self.assertEqual("db_insert", instructions[0]["action"])
                self.assertTrue(instructions[0]["validation"]["valid"])

    def test_watcher_command_binds_to_formal_targets(self) -> None:
        bell_processes = [
            {
                "pid": 123,
                "command": (
                    "python3 /Users/busiji/workbot/skills/tmux-skills/scripts/"
                    "watch_tmux_handoff.py --target formal-session:1.1 --target formal-session:1.3 --deliver"
                ),
            }
        ]
        commands = check_tmux_ready.watcher_commands_for_targets(
            bell_processes,
            ["formal-session:1.1", "formal-session:1.3"],
        )
        self.assertEqual(1, len(commands))
        self.assertIn("--target formal-session:1.3", commands[0])

    @patch("tmux_runtime_common.subprocess.run")
    def test_get_bell_processes_recognizes_target_based_watcher_command(
        self, mock_run: Mock
    ) -> None:
        mock_run.return_value = Mock(
            stdout=(
                "456 python3 /Users/busiji/workbot/skills/tmux-skills/scripts/"
                "watch_tmux_handoff.py --target formal-session:1.3\n"
            ),
            returncode=0,
        )
        processes = tmux_runtime_common.get_bell_processes()
        self.assertEqual(1, len(processes))
        self.assertEqual(456, processes[0]["pid"])
        self.assertIn("watch_tmux_handoff.py", processes[0]["command"])

    def test_ready_check_blocks_when_monitor_target_missing(self) -> None:
        snapshot = sample_runtime_snapshot(monitor_target="")
        args = argparse.Namespace(
            expected_pane_count=4,
            require_formal=True,
            require_bell=True,
            formal_session_name="formal-session",
            task_session_name="",
            monitor_session_name="",
            allow_bootstrap=False,
            allow_extra_formal_sessions=False,
        )
        result = check_tmux_ready.evaluate(snapshot, args)
        self.assertEqual("BLOCKED", result["runtime_status"])
        self.assertTrue(
            any(
                "slot_bindings.monitor.target is missing" in reason
                for reason in result["reasons"]
            )
        )

    def test_shell_pane_with_fake_role_markers_still_fails_identity_verification(self) -> None:
        evaluation = verify_pane_identity.evaluate_role_scene(
            "@qa-bot\n已切换到 qa-bot。",
            "qa-bot",
            pane_current_command="zsh",
            pane_title="qa-bot",
        )
        self.assertFalse(evaluation["verified"])
        self.assertIn("pane is not running Claude yet", evaluation["reasons"][0])

    def test_runtime_only_chain_batch_plan_has_no_launch_agent(self) -> None:
        plan = start_formal_runtime_chain.build_batch_plan(
            [f"formal-session:1.{index}" for index in range(1, 5)],
            ["dev-bot", "dev-bot", "qa-bot", "doc-bot"],
        )
        self.assertEqual(4, len(plan))
        for entry in plan:
            self.assertIn("target", entry)
            self.assertIn("slot", entry)
            self.assertIn("pane_title", entry)
            self.assertNotIn("launch_agent", entry)
            self.assertNotIn("identity_id", entry)

    def test_bundle_message_uses_target_based_frozen_template(self) -> None:
        bundle = build_tmux_handoff_bundle.build_bundle(
            sample_event("pane_attention"),
            table="tmux_notifications_raw",
            session_mode="fixed",
        )
        message = bundle["tmux_skills_handoff"]["notification"]["message"]
        self.assertEqual(
            "qa-bot 呼叫：去 tmux formal-session:1.3 窗口审批 SOP 状态",
            message,
        )

    def test_attention_state_can_reemit_same_signature_after_state_change(self) -> None:
        seen_attention: dict[str, str] = {}
        attention_signature: dict[str, str] = {}
        attention_active: dict[str, bool] = {}
        target = "formal-session:1.3"
        event = {"signature": "abc123def456"}

        first_emit = watch_tmux_handoff.should_emit_attention_event(
            target,
            event,
            "state-attention-1",
            seen_attention=seen_attention,
            attention_signature=attention_signature,
            attention_active=attention_active,
        )
        second_emit = watch_tmux_handoff.should_emit_attention_event(
            target,
            event,
            "state-attention-1",
            seen_attention=seen_attention,
            attention_signature=attention_signature,
            attention_active=attention_active,
        )
        watch_tmux_handoff.reset_attention_tracking_for_state_change(
            target,
            "state-quiet",
            seen_attention=seen_attention,
            attention_signature=attention_signature,
            attention_active=attention_active,
        )
        third_emit = watch_tmux_handoff.should_emit_attention_event(
            target,
            event,
            "state-attention-2",
            seen_attention=seen_attention,
            attention_signature=attention_signature,
            attention_active=attention_active,
        )

        self.assertTrue(first_emit)
        self.assertFalse(second_emit)
        self.assertTrue(third_emit)


if __name__ == "__main__":
    unittest.main()
