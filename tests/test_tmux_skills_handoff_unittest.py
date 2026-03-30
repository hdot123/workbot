#!/usr/bin/env python3
"""Regression tests for the pane-generation and stopped-pane reporting contract."""

from __future__ import annotations

import json
import io
import sys
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path
from unittest.mock import Mock, patch


SCRIPTS_DIR = Path("/Users/busiji/workbot/skills/tmux-skills/scripts")
sys.path.insert(0, str(SCRIPTS_DIR))

import build_tmux_handoff_bundle  # noqa: E402
import check_tmux_ready  # noqa: E402
import deliver_tmux_handoff_notification  # noqa: E402
import start_formal_runtime_chain  # noqa: E402
import tmux_handoff_app_bridge  # noqa: E402
import tmux_runtime_common  # noqa: E402
import watch_tmux_handoff  # noqa: E402
import write_tmux_notifications_sqlite  # noqa: E402


def sample_event(event_type: str, *, deliverable: bool = True) -> dict[str, object]:
    return {
        "event": event_type,
        "event_id": "0123456789abcdef",
        "detected_at": "2026-03-29T10:00:00+00:00",
        "target": "formal-session:1.3",
        "session": "formal-session",
        "window": "1",
        "pane_id": "%3",
        "pane_title": "qa-bot",
        "cwd": "/Users/busiji/workbot",
        "current_command": "zsh",
        "state_class": event_type,
        "state_label": "pane 已停止" if event_type == "pane_stopped" else "pane 不可达",
        "reachable": event_type != "pane_unreachable",
        "deliverable": deliverable,
        "recent_output": "",
        "signature": "0123456789ab",
        "codex_thread_id": "019d3900-80a8-7be1-8e7e-ffa52e0816d3",
        "source": "tmux-skills",
    }


class TmuxSkillsHandoffTests(unittest.TestCase):
    def test_writer_accepts_stopped_and_unreachable_events(self) -> None:
        for event_type in ("pane_stopped", "pane_unreachable", "session_detached"):
            with self.subTest(event_type=event_type):
                event = sample_event(event_type)
                instructions = write_tmux_notifications_sqlite.normalize_instructions(event)
                self.assertEqual(1, len(instructions))
                self.assertEqual("db_insert", instructions[0]["action"])
                self.assertTrue(instructions[0]["validation"]["valid"])

    def test_get_bell_processes_recognizes_watcher_command(self) -> None:
        with patch("tmux_runtime_common.subprocess.run") as mock_run:
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

    def test_build_batch_plan_uses_generic_slots(self) -> None:
        plan = start_formal_runtime_chain.build_batch_plan(
            [f"formal-session:1.{index}" for index in range(1, 5)],
            ["dev-bot", "dev-bot", "qa-bot", "doc-bot"],
        )
        self.assertEqual(4, len(plan))
        self.assertEqual("pane_1", plan[0]["slot"])
        self.assertEqual("pane_4", plan[-1]["slot"])
        self.assertEqual("doc-bot", plan[-1]["pane_title"])

    def test_list_existing_watcher_processes_parses_ps_output(self) -> None:
        with patch("start_formal_runtime_chain.run") as mock_run:
            mock_run.return_value = Mock(
                stdout=(
                    "123 /opt/python watch_tmux_handoff.py --target formal-session:1.1\n"
                    "456 /bin/zsh\n"
                ),
                returncode=0,
            )
            processes = start_formal_runtime_chain.list_existing_watcher_processes()
        self.assertEqual([{"pid": 123, "command": "/opt/python watch_tmux_handoff.py --target formal-session:1.1"}], processes)

    def test_cleanup_previous_runtime_state_clears_known_artifacts(self) -> None:
        removed = {
            str(start_formal_runtime_chain.CURRENT_RUNTIME_LEDGER_PATH),
            str(start_formal_runtime_chain.HANDOFF_LOG_PATH),
            str(start_formal_runtime_chain.HANDOFF_SQLITE_PATH),
        }

        def fake_unlink(path: Path) -> bool:
            return str(path) in removed

        with patch("start_formal_runtime_chain.safe_unlink", side_effect=fake_unlink):
            with patch("start_formal_runtime_chain.stop_existing_watchers", return_value=[11, 22]):
                with patch("start_formal_runtime_chain.unset_tmux_env", return_value="cleared"):
                    result = start_formal_runtime_chain.cleanup_previous_runtime_state()

        self.assertEqual(sorted(removed), sorted(result["removed_files"]))
        self.assertEqual([11, 22], result["stopped_watcher_pids"])
        self.assertEqual("cleared", result["tmux_env"]["CODEX_THREAD_ID"])

    def test_bundle_message_is_simple_stopped_pane_report(self) -> None:
        bundle = build_tmux_handoff_bundle.build_bundle(
            sample_event("pane_stopped"),
            table="tmux_notifications_raw",
            session_mode="fixed",
        )
        message = bundle["tmux_skills_handoff"]["notification"]["message"]
        self.assertEqual("qa-bot pane 已停止：formal-session:1.3", message)
        self.assertEqual(
            "019d3900-80a8-7be1-8e7e-ffa52e0816d3",
            bundle["tmux_skills_handoff"]["target"]["thread_id"],
        )
        self.assertEqual(
            "codex_window_ipc",
            bundle["tmux_skills_handoff"]["delivery"]["transport"],
        )

    def test_bridge_command_targets_app_thread_bridge(self) -> None:
        command = deliver_tmux_handoff_notification.build_bridge_command(
            bridge_script="/tmp/tmux_handoff_app_bridge.py",
            queue_dir="/tmp/delivery-queue",
            receipts_log="/tmp/receipts.jsonl",
            pid_file="/tmp/bridge.pid",
        )
        self.assertEqual(
            [
                sys.executable,
                "/tmp/tmux_handoff_app_bridge.py",
                "--queue-dir",
                "/tmp/delivery-queue",
                "--receipts-log",
                "/tmp/receipts.jsonl",
                "--pid-file",
                "/tmp/bridge.pid",
            ],
            command,
        )

    def test_target_thread_id_does_not_fallback_to_process_env(self) -> None:
        with patch.dict("os.environ", {"CODEX_THREAD_ID": "env-thread"}, clear=False):
            thread_id = deliver_tmux_handoff_notification.target_thread_id(
                {"tmux_skills_handoff": {"target": {}, "payload": {}}}
            )
        self.assertEqual("", thread_id)

    def test_turn_contains_matching_user_message(self) -> None:
        thread = {
            "turns": [
                {
                    "id": "turn-1",
                    "items": [
                        {
                            "type": "userMessage",
                            "content": [{"type": "text", "text": "qa-bot pane 已停止：formal-session:1.3"}],
                        }
                    ],
                }
            ]
        }
        self.assertTrue(
            tmux_handoff_app_bridge.turn_contains_user_message(
                thread,
                "turn-1",
                "qa-bot pane 已停止：formal-session:1.3",
            )
        )

    def test_default_ipc_socket_path_uses_uid_tmpdir(self) -> None:
        with patch.dict("os.environ", {}, clear=True):
            with patch("tmux_handoff_app_bridge.tempfile.gettempdir", return_value="/tmp/codex-tests"):
                with patch("tmux_handoff_app_bridge.os.getuid", return_value=501):
                    path = tmux_handoff_app_bridge.default_ipc_socket_path()
        self.assertEqual(Path("/tmp/codex-tests/codex-ipc/ipc-501.sock"), path)

    def test_encode_ipc_message_uses_length_prefixed_json(self) -> None:
        payload = {"type": "request", "method": "initialize", "params": {"clientType": "tmux-tests"}}
        frame = tmux_handoff_app_bridge.encode_ipc_message(payload)
        body_size = int.from_bytes(frame[:4], byteorder="little", signed=False)
        self.assertEqual(len(frame) - 4, body_size)
        self.assertEqual(payload, json.loads(frame[4:].decode("utf-8")))

    def test_watcher_handoff_queues_event_and_spawns_delivery_runner(self) -> None:
        event = sample_event("pane_stopped")
        with tempfile.TemporaryDirectory() as tmpdir:
            queue_dir = Path(tmpdir) / "queue"
            stdout_log = Path(tmpdir) / "delivery.log"
            with patch("watch_tmux_handoff.subprocess.Popen") as mock_popen:
                mock_popen.return_value = Mock(pid=43210)
                pid = watch_tmux_handoff.handoff_event(
                    event,
                    delivery_script="/tmp/deliver_tmux_handoff_notification.py",
                    session_mode="fixed",
                    dry_run=False,
                    queue_dir=str(queue_dir),
                    stdout_log=str(stdout_log),
                )

            queued_files = list(queue_dir.glob("*.json"))
            self.assertEqual(1, len(queued_files))
            self.assertEqual(event["event_id"], json.loads(queued_files[0].read_text(encoding="utf-8"))["event_id"])
            self.assertEqual(43210, pid)
            command = mock_popen.call_args.args[0]
            self.assertEqual(
                [
                    sys.executable,
                    "/tmp/deliver_tmux_handoff_notification.py",
                    "--session-mode",
                    "fixed",
                    "--event-file",
                    str(queued_files[0]),
                ],
                command,
            )

    def test_delivery_runner_keeps_event_file_for_bridge_processing(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            event_file = Path(tmpdir) / "event.json"
            event_file.write_text(json.dumps(sample_event("pane_stopped")), encoding="utf-8")
            with patch(
                "deliver_tmux_handoff_notification.ensure_bridge_running",
                return_value=(54321, True),
            ):
                with patch.object(
                    sys,
                    "argv",
                    [
                        "deliver_tmux_handoff_notification.py",
                        "--event-file",
                        str(event_file),
                    ],
                ):
                    rc = deliver_tmux_handoff_notification.main()
            self.assertTrue(event_file.exists())

        self.assertEqual(0, rc)

    def test_delivery_runner_dry_run_reports_window_ipc_transport(self) -> None:
        stdout = io.StringIO()
        with patch.object(
            sys,
            "argv",
            [
                "deliver_tmux_handoff_notification.py",
                "--dry-run",
            ],
        ):
            with patch("sys.stdout", stdout):
                payload = sample_event("pane_stopped")
                with patch("deliver_tmux_handoff_notification.load_json", return_value=payload):
                    rc = deliver_tmux_handoff_notification.main()
        self.assertEqual(0, rc)
        self.assertEqual("codex_window_ipc", json.loads(stdout.getvalue())["transport"])

    def test_delivery_runner_acknowledges_non_deliverable_event_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            event_file = Path(tmpdir) / "event.json"
            event_file.write_text(json.dumps(sample_event("pane_stopped", deliverable=False)), encoding="utf-8")
            with patch.object(
                sys,
                "argv",
                [
                    "deliver_tmux_handoff_notification.py",
                    "--event-file",
                    str(event_file),
                ],
            ):
                rc = deliver_tmux_handoff_notification.main()

        self.assertEqual(0, rc)
        self.assertFalse(event_file.exists())

    def test_tmux_env_requires_real_tmux_binding(self) -> None:
        with patch.dict("os.environ", {"CODEX_THREAD_ID": "env-thread"}, clear=False):
            with patch("tmux_runtime_common.run", side_effect=RuntimeError("tmux not available")):
                thread_id = tmux_runtime_common.get_tmux_env("CODEX_THREAD_ID")
        self.assertEqual("", thread_id)

    def test_ready_check_blocks_unattached_formal_session(self) -> None:
        snapshot = {
            "runtime_ledger": {
                "pane_count": 4,
                "slot_bindings": {
                    "pane_1": {"role": "dev-bot", "target": "formal-session:1.1"},
                    "pane_2": {"role": "dev-bot", "target": "formal-session:1.2"},
                    "pane_3": {"role": "qa-bot", "target": "formal-session:1.3"},
                    "pane_4": {"role": "doc-bot", "target": "formal-session:1.4"},
                },
                "watcher": {"armed": True, "targets": [f"formal-session:1.{i}" for i in range(1, 5)]},
                "codex_thread_bound": True,
            },
            "bell_processes": [
                {
                    "command": "python3 watch_tmux_handoff.py --target formal-session:1.1 --target formal-session:1.2 --target formal-session:1.3 --target formal-session:1.4"
                }
            ],
            "panes": [
                {
                    "session_name": "formal-session",
                    "target": f"formal-session:1.{i}",
                    "pane_title_normalized": title,
                }
                for i, title in enumerate(["dev-bot", "dev-bot", "qa-bot", "doc-bot"], start=1)
            ],
            "sessions": [{"session_name": "formal-session", "attached": 0}],
            "CODEX_THREAD_ID": "019d3900-80a8-7be1-8e7e-ffa52e0816d3",
            "session_count": 1,
            "pane_count": 4,
        }
        args = Namespace(
            expected_pane_count=None,
            formal_session_name="formal-session",
            require_formal=False,
            require_watcher=False,
            pretty=False,
        )
        result = check_tmux_ready.evaluate(snapshot, args)
        self.assertEqual("BLOCKED", result["runtime_status"])
        self.assertIn("formal session formal-session is not attached", result["reasons"])

    def test_shell_snapshot_is_not_classified_as_stopped(self) -> None:
        classification = watch_tmux_handoff.classify_snapshot(
            {"session_attached": 1, "pane_dead": 0, "current_command": "zsh"}
        )
        self.assertIsNone(classification)

    def test_arm_watcher_dry_run_accepts_bound_thread_without_local_session_index(self) -> None:
        snapshot = {
            "sessions": [{"session_name": "formal-session", "attached": 1}],
            "panes": [{"session_name": "formal-session", "target": "formal-session:1.1"}],
        }
        with patch("arm_tmux_handoff_watcher.inspect_runtime", return_value=snapshot):
            with patch("arm_tmux_handoff_watcher.enforce_destroy_unattached", return_value="destroy_unattached=on"):
                with patch("arm_tmux_handoff_watcher.ensure_tmux_thread_binding", return_value="thread-123"):
                    with patch.object(
                        sys,
                        "argv",
                        [
                            "arm_tmux_handoff_watcher.py",
                            "--target",
                            "formal-session:1.1",
                            "--dry-run",
                        ],
                    ):
                        import arm_tmux_handoff_watcher

                        rc = arm_tmux_handoff_watcher.main()
        self.assertEqual(0, rc)

    def test_pane_dead_snapshot_is_classified_as_stopped(self) -> None:
        classification = watch_tmux_handoff.classify_snapshot(
            {"session_attached": 1, "pane_dead": 1, "pane_dead_status": "0"}
        )
        self.assertEqual(("pane_stopped", "pane 已停止 (0)", "pane_stopped"), classification)

    def test_hash_state_requires_observed_activity_before_stop_eligibility(self) -> None:
        last_output_hash: dict[str, str] = {}
        unchanged_output_count: dict[str, int] = {}
        observed_activity: dict[str, bool] = {}
        snapshot = {"recent_output_hash": "abc123"}
        counts = [
            watch_tmux_handoff.advance_output_hash_state(
                "formal-session:1.1",
                snapshot,
                last_output_hash=last_output_hash,
                unchanged_output_count=unchanged_output_count,
                observed_activity=observed_activity,
            )
            for _ in range(4)
        ]
        self.assertEqual([0, 1, 2, 3], counts)
        self.assertFalse(observed_activity["formal-session:1.1"])

    def test_hash_state_marks_activity_after_output_change(self) -> None:
        last_output_hash: dict[str, str] = {}
        unchanged_output_count: dict[str, int] = {}
        observed_activity: dict[str, bool] = {}
        target = "formal-session:1.1"

        first_count = watch_tmux_handoff.advance_output_hash_state(
            target,
            {"recent_output_hash": "abc123"},
            last_output_hash=last_output_hash,
            unchanged_output_count=unchanged_output_count,
            observed_activity=observed_activity,
        )
        second_count = watch_tmux_handoff.advance_output_hash_state(
            target,
            {"recent_output_hash": "def456"},
            last_output_hash=last_output_hash,
            unchanged_output_count=unchanged_output_count,
            observed_activity=observed_activity,
        )
        follow_up_counts = [
            watch_tmux_handoff.advance_output_hash_state(
                target,
                {"recent_output_hash": "def456"},
                last_output_hash=last_output_hash,
                unchanged_output_count=unchanged_output_count,
                observed_activity=observed_activity,
            )
            for _ in range(3)
        ]

        self.assertEqual(0, first_count)
        self.assertEqual(0, second_count)
        self.assertTrue(observed_activity[target])
        self.assertEqual([1, 2, 3], follow_up_counts)

    def test_reset_output_hash_state_clears_cached_values(self) -> None:
        last_output_hash = {"formal-session:1.1": "abc123"}
        unchanged_output_count = {"formal-session:1.1": 2}
        observed_activity = {"formal-session:1.1": True}
        watch_tmux_handoff.reset_output_hash_state(
            "formal-session:1.1",
            last_output_hash=last_output_hash,
            unchanged_output_count=unchanged_output_count,
            observed_activity=observed_activity,
        )
        self.assertEqual({}, last_output_hash)
        self.assertEqual({}, unchanged_output_count)
        self.assertEqual({}, observed_activity)

    def test_detached_snapshot_is_classified_as_session_detached(self) -> None:
        classification = watch_tmux_handoff.classify_snapshot(
            {"session_attached": 0, "pane_dead": 0, "current_command": "python3"}
        )
        self.assertEqual(
            ("session_detached", "会话已脱离前台", "session_detached"),
            classification,
        )

    def test_unreachable_event_uses_cached_session_binding(self) -> None:
        with patch("watch_tmux_handoff.read_tmux_env", return_value=""):
            event = watch_tmux_handoff.build_unreachable_event(
                "formal-session:1.3",
                reason="pane 不可达",
                codex_thread_id="019d3900-80a8-7be1-8e7e-ffa52e0816d3",
                cached_snapshot={"pane_title": "qa-bot"},
            )
        self.assertEqual("019d3900-80a8-7be1-8e7e-ffa52e0816d3", event["codex_thread_id"])

    def test_bridge_acknowledges_already_delivered_queue_item_without_resend(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            queue_file = Path(tmpdir) / "queued.json"
            queue_file.write_text(json.dumps(sample_event("pane_stopped")), encoding="utf-8")
            receipts_log = Path(tmpdir) / "receipts.jsonl"
            receipts = {
                "0123456789abcdef": {
                    "status": "delivered",
                    "thread_id": "019d3900-80a8-7be1-8e7e-ffa52e0816d3",
                    "message": "qa-bot pane 已停止：formal-session:1.3",
                }
            }
            client = Mock()
            tmux_handoff_app_bridge.process_queue_item(
                queue_file,
                client=client,
                receipts_log=receipts_log,
                receipts_by_event_id=receipts,
                confirm_timeout=1.0,
                max_retries=1,
            )
        client.deliver_turn_to_current_window.assert_not_called()
        self.assertFalse(queue_file.exists())

    def test_bridge_delivers_via_window_ipc_and_acknowledges_queue_item(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            queue_file = Path(tmpdir) / "queued.json"
            queue_file.write_text(json.dumps(sample_event("pane_stopped")), encoding="utf-8")
            receipts_log = Path(tmpdir) / "receipts.jsonl"
            receipts: dict[str, dict[str, object]] = {}
            client = Mock()
            client.deliver_turn_to_current_window.return_value = tmux_handoff_app_bridge.WindowIpcDeliveryResult(
                handled_by_client_id="client-123",
                turn_id="turn-123",
                visibility_broadcast_observed=True,
            )
            tmux_handoff_app_bridge.process_queue_item(
                queue_file,
                client=client,
                receipts_log=receipts_log,
                receipts_by_event_id=receipts,
                confirm_timeout=1.0,
                max_retries=1,
            )
            lines = receipts_log.read_text(encoding="utf-8").splitlines()
        client.deliver_turn_to_current_window.assert_called_once()
        self.assertFalse(queue_file.exists())
        self.assertEqual(1, len(lines))
        receipt = json.loads(lines[0])
        self.assertEqual("delivered", receipt["status"])
        self.assertEqual("turn-123", receipt["turn_id"])
        self.assertEqual("client-123", receipt["handled_by_client_id"])
        self.assertEqual("owner_window_response+thread_stream_state_changed", receipt["reason"])

    def test_send_request_does_not_starve_matching_response_behind_broadcast(self) -> None:
        client = tmux_handoff_app_bridge.CodexWindowIpcClient(request_timeout=1.0)
        client.socket = Mock()
        client.client_id = "client-abc"
        messages = [
            {"type": "broadcast", "method": "client-status-changed"},
            {"type": "response", "requestId": "fixed-request", "resultType": "success", "method": "thread-follower-start-turn", "handledByClientId": "window-1", "result": {}},
        ]

        def fake_next_message(_timeout: float) -> dict[str, object] | None:
            return messages.pop(0) if messages else None

        with patch("tmux_handoff_app_bridge.uuid4", return_value="fixed-request"):
            with patch.object(client, "_write_message"):
                with patch.object(client, "_next_message", side_effect=fake_next_message):
                    response = client._send_request_raw(
                        "thread-follower-start-turn",
                        {"conversationId": "thread-1", "turnStartParams": {"input": [], "attachments": []}},
                    )

        self.assertEqual("success", response["resultType"])
        self.assertEqual(1, len(client._backlog))
        self.assertEqual("client-status-changed", client._backlog[0]["method"])


if __name__ == "__main__":
    unittest.main()
