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
import build_tmux_topology  # noqa: E402
import check_tmux_ready  # noqa: E402
import arm_tmux_handoff_watcher  # noqa: E402
import deliver_tmux_handoff_notification  # noqa: E402
import init_tmux_env  # noqa: E402
import init_tmux_panes  # noqa: E402
import init_runtime_ledger  # noqa: E402
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
        "pane_title": "notes",
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


def runtime_snapshot(
    *,
    sessions: list[dict[str, object]] | None = None,
    panes: list[dict[str, object]] | None = None,
    clients: list[dict[str, object]] | None = None,
    current_client: dict[str, object] | None = None,
    visible_terminal_client: bool | None = None,
    session_names: list[str] | None = None,
    formal_sessions: list[str] | None = None,
    bootstrap_sessions: list[str] | None = None,
    runtime_ledger: dict[str, object] | None = None,
    codex_thread_id: str = "019d3900-80a8-7be1-8e7e-ffa52e0816d3",
    current_visible_formal_client: bool | None = None,
) -> dict[str, object]:
    session_entries = sessions or []
    current = current_client or {"inside_tmux": False, "session_name": "", "client_tty": ""}
    visible_client = (
        visible_terminal_client
        if visible_terminal_client is not None
        else bool(current.get("inside_tmux"))
    )
    client_entries = [
        {
            **client,
            "visible_terminal_client": client.get("visible_terminal_client", visible_client),
        }
        for client in (clients or [])
    ]
    active_formal_clients = [
        client for client in client_entries if client.get("session_name") == "formal-session"
    ]
    current.setdefault("visible_terminal_client", visible_client)
    current.setdefault("visibility_reason", "test_visible_terminal" if visible_client else "test_hidden_terminal")
    current_client_is_formal = bool(
        current.get("inside_tmux")
        and current.get("session_name") == "formal-session"
        and any(client.get("client_tty") == current.get("client_tty") for client in active_formal_clients)
    )
    snapshot: dict[str, object] = {
        "sessions": session_entries,
        "panes": panes or [],
        "session_count": len(session_entries),
        "pane_count": len(panes or []),
        "CODEX_THREAD_ID": codex_thread_id,
        "clients": client_entries,
        "current_client": current,
        "session_names": session_names or [str(session.get("session_name", "")) for session in session_entries],
        "formal_sessions": formal_sessions or [
            str(session.get("session_name", ""))
            for session in session_entries
            if session.get("session_name") == "formal-session"
        ],
        "bootstrap_sessions": bootstrap_sessions or [
            str(session.get("session_name", ""))
            for session in session_entries
            if session.get("session_name") == "tbot"
        ],
        "formal_client_count": len(active_formal_clients),
        "current_client_is_formal": current_client_is_formal,
        "current_visible_formal_client": (
            current_visible_formal_client
            if current_visible_formal_client is not None
            else (
                current_client_is_formal
                and len(active_formal_clients) == 1
                and bool(current.get("visible_terminal_client"))
            )
        ),
    }
    if runtime_ledger is not None:
        snapshot["runtime_ledger"] = runtime_ledger
    return snapshot


def formal_runtime_ledger(
    *,
    pane_count: int = 4,
    targets: list[str] | None = None,
    watcher_armed: bool = True,
    codex_thread_bound: bool = True,
) -> dict[str, object]:
    formal_targets = targets or [f"formal-session:1.{index}" for index in range(1, pane_count + 1)]
    titles = ["dev-bot-1", "dev-bot-2", "doc-bot-1", "doc-bot-2"][:pane_count]
    return {
        "formal_session_name": "formal-session",
        "pane_count": pane_count,
        "topology_fingerprint": "test-topology",
        "slot_bindings": {
            f"pane_{index}": {"pane_title": title, "target": target}
            for index, (title, target) in enumerate(zip(titles, formal_targets), start=1)
        },
        "watcher": {"armed": watcher_armed, "targets": formal_targets},
        "codex_thread_bound": codex_thread_bound,
        "worker_ceiling": 3,
    }


def switched_source_pane_snapshot(
    *,
    source_session: str = "seed-session",
    source_path: str = "/tmp/source-cwd",
    source_attached: int = 0,
    include_formal_pane: bool = True,
    include_source_pane: bool = True,
    bootstrap_sessions: list[str] | None = None,
) -> dict[str, object]:
    panes: list[dict[str, object]] = []
    if include_formal_pane:
        panes.append(
            {
                "session_name": "formal-session",
                "target": "formal-session:1.1",
                "window_index": "1",
                "pane_index": "1",
            }
        )
    if include_source_pane:
        panes.append(
            {
                "session_name": source_session,
                "target": f"{source_session}:1.1",
                "window_index": "1",
                "pane_index": "1",
                "current_path": source_path,
            }
        )
    return runtime_snapshot(
        sessions=[
            {"session_name": "formal-session", "attached": 1},
            {"session_name": source_session, "attached": source_attached},
        ],
        panes=panes,
        clients=[{"session_name": "formal-session", "client_tty": "/dev/ttys048"}],
        current_client={
            "inside_tmux": True,
            "session_name": source_session,
            "client_tty": "/dev/ttys048",
            "visible_terminal_client": False,
        },
        visible_terminal_client=False,
        formal_sessions=["formal-session"],
        bootstrap_sessions=bootstrap_sessions,
    )


def visible_launcher_snapshot() -> dict[str, object]:
    return runtime_snapshot(
        sessions=[],
        panes=[],
        clients=[],
        current_client={
            "inside_tmux": False,
            "session_name": "",
            "client_tty": "/dev/ttys048",
        },
        visible_terminal_client=True,
    )


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

    def test_terminal_provenance_rejects_codex_hidden_pty(self) -> None:
        with patch.dict("tmux_runtime_common.os.environ", {}, clear=True):
            with patch(
                "tmux_runtime_common.process_ancestry_commands",
                return_value=[
                    "/Applications/Codex.app/Contents/Resources/codex app-serve",
                    "/Applications/Codex.app/Contents/MacOS/Codex",
                ],
            ):
                provenance = tmux_runtime_common.resolve_terminal_provenance()
        self.assertFalse(provenance["visible_terminal_client"])
        self.assertEqual("codex_hidden_pty", provenance["visibility_reason"])

    def test_terminal_provenance_ignores_tmux_self_marker(self) -> None:
        with patch.dict("tmux_runtime_common.os.environ", {"TERM_PROGRAM": "tmux"}, clear=False):
            with patch("tmux_runtime_common.read_process_environment_values", return_value={}):
                with patch(
                    "tmux_runtime_common.process_ancestry_commands",
                    return_value=[
                        "/Applications/Codex.app/Contents/Resources/codex app-serve",
                        "/Applications/Codex.app/Contents/MacOS/Codex",
                    ],
                ):
                    provenance = tmux_runtime_common.resolve_terminal_provenance(client_pid=33145)
        self.assertFalse(provenance["visible_terminal_client"])
        self.assertEqual("codex_hidden_pty", provenance["visibility_reason"])

    def test_list_clients_does_not_use_current_env_fallback_for_other_clients(self) -> None:
        with patch.dict("tmux_runtime_common.os.environ", {"TERM_PROGRAM": "Apple_Terminal"}, clear=False):
            with patch(
                "tmux_runtime_common.run",
                return_value="/dev/ttys044\tformal-session\t33145\t180\t52\n",
            ):
                with patch("tmux_runtime_common.read_process_environment_values", return_value={}):
                    with patch("tmux_runtime_common.process_ancestry_commands", return_value=[]):
                        clients = tmux_runtime_common.list_clients("formal-session")
        self.assertEqual(1, len(clients))
        self.assertFalse(clients[0]["visible_terminal_client"])
        self.assertEqual("missing_terminal_marker", clients[0]["visibility_reason"])

    def test_terminal_provenance_accepts_terminal_program_marker(self) -> None:
        with patch.dict("tmux_runtime_common.os.environ", {"TERM_PROGRAM": "Apple_Terminal"}, clear=False):
            with patch("tmux_runtime_common.process_ancestry_commands", return_value=[]):
                provenance = tmux_runtime_common.resolve_terminal_provenance()
        self.assertTrue(provenance["visible_terminal_client"])
        self.assertEqual("terminal_marker_detected", provenance["visibility_reason"])

    def test_terminal_provenance_accepts_client_bundle_marker(self) -> None:
        with patch.dict("tmux_runtime_common.os.environ", {"TERM_PROGRAM": "tmux"}, clear=False):
            with patch(
                "tmux_runtime_common.read_process_environment_values",
                return_value={"__CFBundleIdentifier": "com.apple.Terminal"},
            ):
                with patch("tmux_runtime_common.process_ancestry_commands", return_value=[]):
                    provenance = tmux_runtime_common.resolve_terminal_provenance(client_pid=33145)
        self.assertTrue(provenance["visible_terminal_client"])
        self.assertEqual("Apple_Terminal", provenance["known_terminal_marker"])

    def test_current_tmux_context_uses_client_pid_for_terminal_visibility(self) -> None:
        with patch.dict("tmux_runtime_common.os.environ", {"TMUX": "/tmp/tmux,123,0", "TERM_PROGRAM": "tmux"}, clear=False):
            with patch("tmux_runtime_common.resolve_current_tty", return_value="/dev/ttys058"):
                with patch(
                    "tmux_runtime_common.run",
                    return_value="/dev/ttys044\t33145\tformal-session\t1\t3\t%5\n",
                ):
                    with patch(
                        "tmux_runtime_common.read_process_environment_values",
                        return_value={"TERM_PROGRAM": "Apple_Terminal"},
                    ):
                        with patch("tmux_runtime_common.process_ancestry_commands", return_value=[]):
                            context = tmux_runtime_common.resolve_current_tmux_context()
        self.assertTrue(context["inside_tmux"])
        self.assertEqual(33145, context["client_pid"])
        self.assertTrue(context["visible_terminal_client"])
        self.assertEqual("Apple_Terminal", context["term_program"])

    def test_describe_formal_client_state_marks_visible_formal_runtime(self) -> None:
        snapshot = runtime_snapshot(
            sessions=[{"session_name": "formal-session", "attached": 1}],
            clients=[{"session_name": "formal-session", "client_tty": "/dev/ttys048"}],
            current_client={
                "inside_tmux": True,
                "session_name": "formal-session",
                "client_tty": "/dev/ttys048",
            },
            visible_terminal_client=True,
        )

        state = tmux_runtime_common.describe_formal_client_state(snapshot, "formal-session")

        self.assertTrue(state["formal_attached"])
        self.assertTrue(state["current_visible_formal_client"])
        self.assertFalse(state["startup_transition_ready"])
        self.assertTrue(state["startup_client_ready"])

    def test_describe_formal_client_state_marks_switched_source_pane_transition(self) -> None:
        snapshot = switched_source_pane_snapshot(include_formal_pane=False, include_source_pane=False)

        state = tmux_runtime_common.describe_formal_client_state(snapshot, "formal-session")

        self.assertTrue(state["formal_attached"])
        self.assertFalse(state["current_visible_formal_client"])
        self.assertFalse(state["startup_transition_ready"])
        self.assertFalse(state["startup_client_ready"])
        self.assertEqual("seed-session", state["current_caller_session"])

    def test_build_batch_plan_uses_generic_slots(self) -> None:
        plan = start_formal_runtime_chain.build_batch_plan(
            [f"formal-session:1.{index}" for index in range(1, 5)],
            ["task-1", "task-2", "notes", "monitor"],
        )
        self.assertEqual(4, len(plan))
        self.assertEqual("pane_1", plan[0]["slot"])
        self.assertEqual("pane_4", plan[-1]["slot"])
        self.assertEqual("monitor", plan[-1]["pane_title"])

    def test_split_flag_for_pane_prefers_wide_then_tall(self) -> None:
        self.assertEqual(
            "-h",
            build_tmux_topology.split_flag_for_pane(
                {"target": "formal-session:1.1", "width": 220, "height": 66}
            ),
        )
        self.assertEqual(
            "-v",
            build_tmux_topology.split_flag_for_pane(
                {"target": "formal-session:1.1", "width": 70, "height": 120}
            ),
        )

    def test_select_split_pane_prefers_largest_balanced_candidate(self) -> None:
        selected = build_tmux_topology.select_split_pane(
            [
                {"target": "formal-session:1.2", "width": 100, "height": 30},
                {"target": "formal-session:1.1", "width": 90, "height": 40},
                {"target": "formal-session:1.3", "width": 80, "height": 30},
            ]
        )
        self.assertEqual("formal-session:1.1", selected["target"])

    def test_reconcile_topology_rebalances_after_each_split(self) -> None:
        pane_states = [
            [{"target": "formal-session:1.1", "width": 227, "height": 66}],
            [
                {"target": "formal-session:1.1", "width": 113, "height": 66},
                {"target": "formal-session:1.2", "width": 113, "height": 66},
            ],
            [
                {"target": "formal-session:1.1", "width": 113, "height": 33},
                {"target": "formal-session:1.2", "width": 113, "height": 66},
                {"target": "formal-session:1.3", "width": 113, "height": 32},
            ],
            [
                {"target": "formal-session:1.1", "width": 76, "height": 33},
                {"target": "formal-session:1.2", "width": 76, "height": 33},
                {"target": "formal-session:1.3", "width": 76, "height": 33},
                {"target": "formal-session:1.4", "width": 76, "height": 33},
            ],
            [
                {"target": "formal-session:1.1", "width": 76, "height": 22},
                {"target": "formal-session:1.2", "width": 76, "height": 22},
                {"target": "formal-session:1.3", "width": 76, "height": 22},
                {"target": "formal-session:1.4", "width": 76, "height": 44},
                {"target": "formal-session:1.5", "width": 76, "height": 44},
            ],
        ]
        session_target_states = [
            ["formal-session:1.1"],
            ["formal-session:1.1", "formal-session:1.2"],
            ["formal-session:1.1", "formal-session:1.2", "formal-session:1.3"],
            ["formal-session:1.1", "formal-session:1.2", "formal-session:1.3", "formal-session:1.4"],
            [
                "formal-session:1.1",
                "formal-session:1.2",
                "formal-session:1.3",
                "formal-session:1.4",
                "formal-session:1.5",
            ],
            [
                "formal-session:1.1",
                "formal-session:1.2",
                "formal-session:1.3",
                "formal-session:1.4",
                "formal-session:1.5",
                "formal-session:1.6",
            ],
        ]

        def fake_session_panes(_: str) -> list[dict[str, int | str]]:
            return pane_states.pop(0)

        def fake_session_targets(_: str) -> list[str]:
            return session_target_states.pop(0)

        with patch("build_tmux_topology.session_targets", side_effect=fake_session_targets):
            with patch("build_tmux_topology.session_panes", side_effect=fake_session_panes):
                with patch("build_tmux_topology.run_tmux") as mock_run_tmux:
                    mock_run_tmux.return_value = Mock(returncode=0, stdout="", stderr="")
                    with patch(
                        "build_tmux_topology.inspect_runtime",
                        side_effect=[
                            {
                                "panes": [
                                    {"session_name": "formal-session", "target": f"formal-session:1.{index}"}
                                    for index in range(1, 7)
                                ],
                                "topology_fingerprint": "fingerprint-1",
                            },
                            {
                                "panes": [
                                    {"session_name": "formal-session", "target": f"formal-session:1.{index}"}
                                    for index in range(1, 7)
                                ],
                                "topology_fingerprint": "fingerprint-2",
                            },
                        ],
                    ):
                        result = build_tmux_topology.reconcile_topology("formal-session", 6)

        split_commands = [
            call.args for call in mock_run_tmux.call_args_list if call.args and call.args[0] == "split-window"
        ]
        layout_commands = [
            call.args for call in mock_run_tmux.call_args_list if call.args and call.args[0] == "select-layout"
        ]

        self.assertEqual(
            [
                ("split-window", "-h", "-t", "formal-session:1.1"),
                ("split-window", "-v", "-t", "formal-session:1.1"),
                ("split-window", "-v", "-t", "formal-session:1.1"),
                ("split-window", "-v", "-t", "formal-session:1.2"),
                ("split-window", "-v", "-t", "formal-session:1.2"),
            ],
            split_commands,
        )
        self.assertEqual(6, result["pane_count_after"])
        self.assertGreaterEqual(len(layout_commands), 5)

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
                with patch("start_formal_runtime_chain.unset_tmux_env", return_value="cleared") as mock_unset:
                    result = start_formal_runtime_chain.cleanup_previous_runtime_state()

        self.assertEqual(sorted(removed), sorted(result["removed_files"]))
        self.assertEqual([11, 22], result["stopped_watcher_pids"])
        self.assertEqual("cleared", result["tmux_env"]["CODEX_THREAD_ID"])
        mock_unset.assert_called_once_with("CODEX_THREAD_ID")

    def test_run_json_with_status_preserves_nonzero_json_payload(self) -> None:
        with patch("start_formal_runtime_chain.run") as mock_run:
            mock_run.return_value = Mock(
                stdout=json.dumps({"runtime_status": "BLOCKED", "reasons": ["not visible"]}),
                stderr="",
                returncode=1,
            )
            payload, rc = start_formal_runtime_chain.run_json_with_status(
                ["python3", "fake.py"],
                step="ready_check",
            )
        self.assertEqual(1, rc)
        self.assertEqual("BLOCKED", payload["runtime_status"])
        self.assertEqual(["not visible"], payload["reasons"])

    def test_build_result_reports_ready_check_step(self) -> None:
        result = start_formal_runtime_chain.build_result(
            "ok",
            {"formal_session": "formal-session"},
            ["dev-bot-1"],
        )
        self.assertIn("tmux_preflight", result["chain"])
        self.assertIn("ready_check", result["chain"])

    def test_preflight_kill_all_tmux_sessions_kills_hidden_formal_session(self) -> None:
        snapshot = runtime_snapshot(
            sessions=[{"session_name": "formal-session", "attached": 1, "windows": 1}],
            clients=[{"session_name": "formal-session", "client_tty": "/dev/ttys044"}],
            current_client={"inside_tmux": False, "session_name": "", "client_tty": ""},
            visible_terminal_client=False,
        )
        with patch("start_formal_runtime_chain.inspect_runtime_snapshot", return_value=snapshot):
            with patch("start_formal_runtime_chain.run") as mock_run:
                mock_run.return_value = Mock(returncode=0, stdout="", stderr="")
                result = start_formal_runtime_chain.preflight_kill_all_tmux_sessions()
        self.assertTrue(result["attempted"])
        self.assertTrue(result["cleaned"])
        mock_run.assert_called_once_with(["tmux", "kill-session", "-t", "formal-session"])

    def test_preflight_kill_all_tmux_sessions_kills_bootstrap_session(self) -> None:
        snapshot = runtime_snapshot(
            sessions=[{"session_name": "tbot", "attached": 1, "windows": 1}],
            clients=[{"session_name": "tbot", "client_tty": "/dev/ttys044"}],
            current_client={"inside_tmux": False, "session_name": "", "client_tty": ""},
            visible_terminal_client=False,
        )
        with patch("start_formal_runtime_chain.inspect_runtime_snapshot", return_value=snapshot):
            with patch("start_formal_runtime_chain.run") as mock_run:
                mock_run.return_value = Mock(returncode=0, stdout="", stderr="")
                result = start_formal_runtime_chain.preflight_kill_all_tmux_sessions()
        self.assertTrue(result["attempted"])
        self.assertTrue(result["cleaned"])
        self.assertEqual(["tbot"], result["killed_sessions"])
        mock_run.assert_called_once_with(["tmux", "kill-session", "-t", "tbot"])

    def test_preflight_kill_all_tmux_sessions_kills_current_stale_formal_session(self) -> None:
        snapshot = runtime_snapshot(
            sessions=[{"session_name": "formal-session", "attached": 1, "windows": 1}],
            clients=[{"session_name": "formal-session", "client_tty": "/dev/ttys044"}],
            current_client={
                "inside_tmux": True,
                "session_name": "formal-session",
                "client_tty": "/dev/ttys044",
                "visible_terminal_client": False,
            },
            visible_terminal_client=False,
        )
        with patch("start_formal_runtime_chain.inspect_runtime_snapshot", return_value=snapshot):
            with patch("start_formal_runtime_chain.run") as mock_run:
                mock_run.return_value = Mock(returncode=0, stdout="", stderr="")
                result = start_formal_runtime_chain.preflight_kill_all_tmux_sessions()
        self.assertFalse(result["attempted"])
        self.assertTrue(result["blocked"])
        self.assertEqual(["formal-session"], result["session_names"])
        mock_run.assert_not_called()

    def test_preflight_kill_all_tmux_sessions_kills_current_visible_bootstrap_session(self) -> None:
        snapshot = runtime_snapshot(
            sessions=[{"session_name": "tbot", "attached": 1, "windows": 1}],
            clients=[{"session_name": "tbot", "client_tty": "/dev/ttys044"}],
            current_client={
                "inside_tmux": True,
                "session_name": "tbot",
                "client_tty": "/dev/ttys044",
            },
            visible_terminal_client=True,
        )
        with patch("start_formal_runtime_chain.inspect_runtime_snapshot", return_value=snapshot):
            with patch("start_formal_runtime_chain.run") as mock_run:
                mock_run.return_value = Mock(returncode=0, stdout="", stderr="")
                result = start_formal_runtime_chain.preflight_kill_all_tmux_sessions()
        self.assertFalse(result["attempted"])
        self.assertTrue(result["blocked"])
        self.assertEqual(["tbot"], result["session_names"])
        mock_run.assert_not_called()

    def test_cleanup_hidden_formal_session_on_failure_kills_hidden_codex_client(self) -> None:
        snapshot = runtime_snapshot(
            sessions=[{"session_name": "formal-session", "attached": 1, "windows": 1}],
            clients=[{"session_name": "formal-session", "client_tty": "/dev/ttys044"}],
            current_client={
                "inside_tmux": True,
                "session_name": "formal-session",
                "client_tty": "/dev/ttys044",
                "codex_hosted": True,
                "visible_terminal_client": False,
                "visibility_reason": "codex_hidden_pty",
            },
            visible_terminal_client=False,
        )
        with patch("start_formal_runtime_chain.run_json", return_value=snapshot):
            with patch("start_formal_runtime_chain.run") as mock_run:
                mock_run.return_value = Mock(returncode=0, stdout="", stderr="")
                with patch(
                    "start_formal_runtime_chain.cleanup_previous_runtime_state",
                    return_value={"removed_files": [], "stopped_watcher_pids": [], "tmux_env": {}},
                ):
                    result = start_formal_runtime_chain.cleanup_hidden_formal_session_on_failure(
                        "formal-session",
                        "foreground tmux changes must run from a real visible terminal client",
                    )
        self.assertTrue(result["attempted"])
        self.assertTrue(result["cleaned"])
        mock_run.assert_called_once_with(["tmux", "kill-session", "-t", "formal-session"])

    def test_cleanup_hidden_formal_session_on_failure_kills_residue_error(self) -> None:
        snapshot = runtime_snapshot(
            sessions=[{"session_name": "formal-session", "attached": 1, "windows": 1}],
            clients=[{"session_name": "formal-session", "client_tty": "/dev/ttys044"}],
            current_client={
                "inside_tmux": True,
                "session_name": "formal-session",
                "client_tty": "/dev/ttys044",
                "codex_hosted": False,
                "visible_terminal_client": True,
                "visibility_reason": "terminal_marker_detected",
            },
            visible_terminal_client=True,
        )
        with patch("start_formal_runtime_chain.run_json", return_value=snapshot):
            with patch("start_formal_runtime_chain.run") as mock_run:
                mock_run.return_value = Mock(returncode=0, stdout="", stderr="")
                with patch(
                    "start_formal_runtime_chain.cleanup_previous_runtime_state",
                    return_value={"removed_files": [], "stopped_watcher_pids": [], "tmux_env": {}},
                ):
                    result = start_formal_runtime_chain.cleanup_hidden_formal_session_on_failure(
                        "formal-session",
                        "historical formal-session residue is already attached to the current client",
                    )
        self.assertTrue(result["attempted"])
        self.assertTrue(result["cleaned"])
        self.assertTrue(result["residue_error"])
        mock_run.assert_called_once_with(["tmux", "kill-session", "-t", "formal-session"])

    def test_cleanup_hidden_formal_session_on_failure_skips_visible_client(self) -> None:
        snapshot = runtime_snapshot(
            sessions=[{"session_name": "formal-session", "attached": 1, "windows": 1}],
            clients=[{"session_name": "formal-session", "client_tty": "/dev/ttys044"}],
            current_client={
                "inside_tmux": True,
                "session_name": "formal-session",
                "client_tty": "/dev/ttys044",
                "codex_hosted": False,
                "visible_terminal_client": True,
                "visibility_reason": "terminal_marker_detected",
            },
            visible_terminal_client=True,
        )
        with patch("start_formal_runtime_chain.run_json", return_value=snapshot):
            with patch("start_formal_runtime_chain.run") as mock_run:
                result = start_formal_runtime_chain.cleanup_hidden_formal_session_on_failure(
                    "formal-session"
                )
        self.assertFalse(result["attempted"])
        self.assertEqual("skip", result["reason"])
        mock_run.assert_not_called()

    def test_bundle_message_is_simple_stopped_pane_report(self) -> None:
        bundle = build_tmux_handoff_bundle.build_bundle(
            sample_event("pane_stopped"),
            table="tmux_notifications_raw",
            session_mode="fixed",
        )
        message = bundle["tmux_skills_handoff"]["notification"]["message"]
        self.assertEqual("notes pane 已停止：formal-session:1.3", message)
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
                            "content": [{"type": "text", "text": "notes pane 已停止：formal-session:1.3"}],
                        }
                    ],
                }
            ]
        }
        self.assertTrue(
            tmux_handoff_app_bridge.turn_contains_user_message(
                thread,
                "turn-1",
                "notes pane 已停止：formal-session:1.3",
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
            queue_dir = Path(tmpdir) / "queue"
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
                        "--queue-dir",
                        str(queue_dir),
                    ],
                ):
                    stdout = io.StringIO()
                    with patch("sys.stdout", stdout):
                        rc = deliver_tmux_handoff_notification.main()
            self.assertTrue(event_file.exists())
            queued = json.loads(stdout.getvalue())
            queued_path = Path(queued["event_file"])
            self.assertEqual(queue_dir, queued_path.parent)
            self.assertTrue(queued_path.exists())

        self.assertEqual(0, rc)

    def test_delivery_runner_reuses_event_file_already_in_queue_dir(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            queue_dir = Path(tmpdir) / "queue"
            queue_dir.mkdir(parents=True, exist_ok=True)
            event_file = queue_dir / "event.json"
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
                        "--queue-dir",
                        str(queue_dir),
                    ],
                ):
                    stdout = io.StringIO()
                    with patch("sys.stdout", stdout):
                        rc = deliver_tmux_handoff_notification.main()

        self.assertEqual(0, rc)
        queued = json.loads(stdout.getvalue())
        self.assertEqual(str(event_file), queued["event_file"])

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
        snapshot = runtime_snapshot(
            sessions=[{"session_name": "formal-session", "attached": 0}],
            panes=[
                {
                    "session_name": "formal-session",
                    "target": f"formal-session:1.{i}",
                    "pane_title_normalized": title,
                }
                for i, title in enumerate(["task-1", "task-2", "notes", "monitor"], start=1)
            ],
            runtime_ledger=formal_runtime_ledger(
                targets=[f"formal-session:1.{i}" for i in range(1, 5)]
            ),
        )
        snapshot["bell_processes"] = [
            {
                "command": "python3 watch_tmux_handoff.py --target formal-session:1.1 --target formal-session:1.2 --target formal-session:1.3 --target formal-session:1.4"
            }
        ]
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

    def test_ready_check_blocks_when_formal_client_is_missing(self) -> None:
        snapshot = runtime_snapshot(
            sessions=[{"session_name": "formal-session", "attached": 1}],
            panes=[
                {
                    "session_name": "formal-session",
                    "target": "formal-session:1.1",
                    "pane_title_normalized": "dev-bot-1",
                }
            ],
            runtime_ledger=formal_runtime_ledger(pane_count=1, targets=["formal-session:1.1"]),
        )
        snapshot["bell_processes"] = []
        args = Namespace(
            expected_pane_count=None,
            formal_session_name="formal-session",
            require_formal=False,
            require_watcher=False,
            pretty=False,
        )

        result = check_tmux_ready.evaluate(snapshot, args)

        self.assertEqual("BLOCKED", result["runtime_status"])
        self.assertIn("formal session formal-session has no attached tmux client", result["reasons"])

    def test_ready_check_accepts_visible_formal_client_for_four_panes(self) -> None:
        snapshot = runtime_snapshot(
            sessions=[{"session_name": "formal-session", "attached": 1}],
            panes=[
                {
                    "session_name": "formal-session",
                    "target": "formal-session:1.1",
                    "pane_title_normalized": "dev-bot-1",
                }
            ],
            clients=[{"session_name": "formal-session", "client_tty": "/dev/ttys048"}],
            current_client={
                "inside_tmux": True,
                "session_name": "formal-session",
                "client_tty": "/dev/ttys048",
            },
            runtime_ledger=formal_runtime_ledger(pane_count=1, targets=["formal-session:1.1"]),
        )
        snapshot["bell_processes"] = []
        args = Namespace(
            expected_pane_count=None,
            formal_session_name="formal-session",
            require_formal=False,
            require_watcher=False,
            pretty=False,
        )

        result = check_tmux_ready.evaluate(snapshot, args)

        self.assertEqual("READY", result["runtime_status"])
        self.assertEqual([], result["reasons"])

    def test_ready_check_blocks_hidden_codex_tty_client(self) -> None:
        snapshot = runtime_snapshot(
            sessions=[{"session_name": "formal-session", "attached": 1}],
            panes=[
                {
                    "session_name": "formal-session",
                    "target": "formal-session:1.1",
                    "pane_title_normalized": "dev-bot-1",
                }
            ],
            clients=[{"session_name": "formal-session", "client_tty": "/dev/ttys048"}],
            current_client={
                "inside_tmux": True,
                "session_name": "formal-session",
                "client_tty": "/dev/ttys048",
            },
            visible_terminal_client=False,
            runtime_ledger=formal_runtime_ledger(pane_count=1, targets=["formal-session:1.1"]),
        )
        snapshot["bell_processes"] = []
        args = Namespace(
            expected_pane_count=None,
            formal_session_name="formal-session",
            require_formal=False,
            require_watcher=False,
            pretty=False,
        )

        result = check_tmux_ready.evaluate(snapshot, args)

        self.assertEqual("BLOCKED", result["runtime_status"])
        self.assertIn("current caller is not inside the visible formal session formal-session", result["reasons"])

    def test_ready_check_handles_null_watcher(self) -> None:
        snapshot = runtime_snapshot(
            sessions=[{"session_name": "formal-session", "attached": 1}],
            panes=[
                {
                    "session_name": "formal-session",
                    "target": "formal-session:1.1",
                    "pane_title_normalized": "task-1",
                }
            ],
            clients=[{"session_name": "formal-session", "client_tty": "/dev/ttys048"}],
            current_client={
                "inside_tmux": True,
                "session_name": "formal-session",
                "client_tty": "/dev/ttys048",
            },
            runtime_ledger={
                "pane_count": 1,
                "slot_bindings": {
                    "pane_1": {"pane_title": "task-1", "target": "formal-session:1.1"},
                },
                "watcher": None,
                "codex_thread_bound": True,
            },
        )
        snapshot["bell_processes"] = []
        args = Namespace(
            expected_pane_count=None,
            formal_session_name="formal-session",
            require_formal=False,
            require_watcher=True,
            pretty=False,
        )

        result = check_tmux_ready.evaluate(snapshot, args)

        self.assertEqual("BLOCKED", result["runtime_status"])
        self.assertIn("runtime watcher is not armed", result["reasons"])

    def test_ready_check_blocks_attached_session_without_formal_client(self) -> None:
        snapshot = runtime_snapshot(
            sessions=[{"session_name": "formal-session", "attached": 1}],
            panes=[
                {
                    "session_name": "formal-session",
                    "target": f"formal-session:1.{index}",
                    "pane_title_normalized": title,
                }
                for index, title in enumerate(["dev-bot-1", "dev-bot-2", "doc-bot-1", "doc-bot-2"], start=1)
            ],
            clients=[
                {
                    "client_tty": "/dev/ttys048",
                    "client_session": "bootstrap",
                    "session_name": "bootstrap",
                    "session_attached": 1,
                    "client_width": 80,
                    "client_height": 24,
                }
            ],
            runtime_ledger=formal_runtime_ledger(),
        )
        args = Namespace(
            expected_pane_count=None,
            formal_session_name="formal-session",
            require_formal=True,
            require_watcher=False,
            pretty=False,
        )

        result = check_tmux_ready.evaluate(snapshot, args)

        self.assertEqual("BLOCKED", result["runtime_status"])
        self.assertTrue(
            any(
                any(keyword in reason.lower() for keyword in ("client", "foreground", "tty"))
                for reason in result["reasons"]
            ),
            result["reasons"],
        )

    def test_ready_check_accepts_visible_formal_client(self) -> None:
        snapshot = runtime_snapshot(
            sessions=[{"session_name": "formal-session", "attached": 1}],
            panes=[
                {
                    "session_name": "formal-session",
                    "target": f"formal-session:1.{index}",
                    "pane_title_normalized": title,
                }
                for index, title in enumerate(["dev-bot-1", "dev-bot-2", "doc-bot-1", "doc-bot-2"], start=1)
            ],
            clients=[
                {
                    "client_tty": "/dev/ttys048",
                    "client_session": "formal-session",
                    "session_name": "formal-session",
                    "session_attached": 1,
                    "client_width": 80,
                    "client_height": 24,
                    "active": 1,
                }
            ],
            current_client={
                "inside_tmux": True,
                "session_name": "formal-session",
                "client_tty": "/dev/ttys048",
            },
            runtime_ledger=formal_runtime_ledger(),
        )
        args = Namespace(
            expected_pane_count=None,
            formal_session_name="formal-session",
            require_formal=True,
            require_watcher=True,
            pretty=False,
        )
        snapshot["bell_processes"] = [
            {
                "command": (
                    "python3 watch_tmux_handoff.py --target formal-session:1.1 "
                    "--target formal-session:1.2 --target formal-session:1.3 "
                    "--target formal-session:1.4"
                )
            }
        ]

        result = check_tmux_ready.evaluate(snapshot, args)

        self.assertEqual("READY", result["runtime_status"])
        self.assertTrue(result["watcher_armed"])
        self.assertEqual(
            [
                "formal-session:1.1",
                "formal-session:1.2",
                "formal-session:1.3",
                "formal-session:1.4",
            ],
            result["formal_targets"],
        )

    def test_shell_snapshot_is_not_classified_as_stopped(self) -> None:
        classification = watch_tmux_handoff.classify_snapshot(
            {"session_attached": 1, "pane_dead": 0, "current_command": "zsh"}
        )
        self.assertIsNone(classification)

    def test_arm_watcher_dry_run_accepts_bound_thread_without_local_session_index(self) -> None:
        snapshot = runtime_snapshot(
            sessions=[{"session_name": "formal-session", "attached": 1}],
            panes=[{"session_name": "formal-session", "target": "formal-session:1.1"}],
            clients=[{"session_name": "formal-session", "client_tty": "/dev/ttys048"}],
            current_client={
                "inside_tmux": True,
                "session_name": "formal-session",
                "client_tty": "/dev/ttys048",
            },
        )
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

    def test_arm_watcher_rejects_missing_formal_client(self) -> None:
        snapshot = runtime_snapshot(
            sessions=[{"session_name": "formal-session", "attached": 1}],
            panes=[{"session_name": "formal-session", "target": "formal-session:1.1"}],
        )
        with patch("arm_tmux_handoff_watcher.inspect_runtime", return_value=snapshot):
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
                with self.assertRaises(SystemExit) as exc:
                    arm_tmux_handoff_watcher.main()

        self.assertIn("has no attached tmux client", str(exc.exception))

    def test_init_tmux_env_prepares_formal_session_from_visible_launcher(self) -> None:
        snapshot = runtime_snapshot(
            sessions=[],
            panes=[],
            current_client={"inside_tmux": False, "session_name": "", "client_tty": "/dev/ttys048"},
            visible_terminal_client=True,
        )
        snapshot_after_create = runtime_snapshot(
            sessions=[{"session_name": "formal-session", "attached": 0}],
            panes=[{"session_name": "formal-session", "target": "formal-session:1.1", "window_index": "1", "pane_index": "1"}],
            clients=[],
            current_client={"inside_tmux": False, "session_name": "", "client_tty": "/dev/ttys048"},
            visible_terminal_client=True,
        )
        with patch("init_tmux_env.inspect_runtime", side_effect=[snapshot, snapshot_after_create, snapshot_after_create]):
            with patch("init_tmux_env.run_tmux") as mock_run_tmux:
                mock_run_tmux.return_value = Mock(returncode=0, stdout="", stderr="")
                with patch.object(
                    sys,
                    "argv",
                    [
                        "init_tmux_env.py",
                        "--formal-session",
                        "formal-session",
                        "--create-formal-session",
                    ],
                ):
                    rc = init_tmux_env.main()

        self.assertEqual(0, rc)
        self.assertEqual(("new-session", "-d", "-s", "formal-session", "-c", "/Users/busiji/workbot"), mock_run_tmux.call_args_list[0].args)

    def test_init_tmux_env_rejects_hidden_launcher_client(self) -> None:
        snapshot = runtime_snapshot(
            sessions=[],
            panes=[],
            current_client={
                "inside_tmux": False,
                "session_name": "",
                "client_tty": "",
                "visibility_reason": "codex_hidden_pty",
            },
            visible_terminal_client=False,
        )
        with patch("init_tmux_env.inspect_runtime", return_value=snapshot):
            with patch.object(
                sys,
                "argv",
                [
                    "init_tmux_env.py",
                    "--formal-session",
                    "formal-session",
                    "--create-formal-session",
                ],
            ):
                with self.assertRaises(RuntimeError) as exc:
                    init_tmux_env.main()

        self.assertIn("refusing startup from codex_hidden_pty", str(exc.exception))

    def test_init_tmux_env_rejects_tmux_runtime_residue_before_create(self) -> None:
        snapshot = runtime_snapshot(
            sessions=[{"session_name": "formal-session", "attached": 1}],
            panes=[],
            clients=[{"session_name": "formal-session", "client_tty": "/dev/ttys048"}],
            current_client={
                "inside_tmux": False,
                "session_name": "",
                "client_tty": "/dev/ttys048",
            },
            visible_terminal_client=True,
        )
        with patch("init_tmux_env.inspect_runtime", return_value=snapshot):
            with patch.object(
                sys,
                "argv",
                [
                    "init_tmux_env.py",
                    "--formal-session",
                    "formal-session",
                    "--create-formal-session",
                ],
            ):
                with self.assertRaises(RuntimeError) as exc:
                    init_tmux_env.main()

        self.assertIn("tmux residue must be cleared before formal env setup: formal-session", str(exc.exception))

    def test_init_tmux_env_rejects_inside_tmux_launcher(self) -> None:
        snapshot = runtime_snapshot(
            sessions=[{"session_name": "formal-session", "attached": 1}],
            panes=[],
            clients=[{"session_name": "formal-session", "client_tty": "/dev/ttys048"}],
            current_client={
                "inside_tmux": True,
                "session_name": "formal-session",
                "client_tty": "/dev/ttys048",
            },
            visible_terminal_client=True,
        )
        with patch("init_tmux_env.inspect_runtime", return_value=snapshot):
            with patch.object(
                sys,
                "argv",
                [
                    "init_tmux_env.py",
                    "--formal-session",
                    "formal-session",
                    "--create-formal-session",
                ],
            ):
                with self.assertRaises(RuntimeError) as exc:
                    init_tmux_env.main()

        self.assertIn("must start from a fresh visible terminal", str(exc.exception))

    def test_start_formal_runtime_chain_rejects_source_pane_runtime(self) -> None:
        snapshot = switched_source_pane_snapshot()

        with self.assertRaises(RuntimeError) as exc:
            start_formal_runtime_chain.ensure_attached_formal_session(snapshot, "formal-session")

        self.assertIn("must have exactly one visible tmux client; got 0", str(exc.exception))

    def test_start_formal_runtime_chain_launcher_starts_fresh_formal_session(self) -> None:
        inspect_snapshots = [
            visible_launcher_snapshot(),
            runtime_snapshot(sessions=[], panes=[], clients=[], current_client={"inside_tmux": False}, visible_terminal_client=True),
        ]

        with patch("start_formal_runtime_chain.inspect_runtime_snapshot", side_effect=inspect_snapshots):
            with patch(
                "start_formal_runtime_chain.preflight_kill_all_tmux_sessions",
                return_value={"attempted": True, "cleaned": True, "killed_sessions": ["seed-session"]},
            ):
                with patch(
                    "start_formal_runtime_chain.cleanup_previous_runtime_state",
                    return_value={"removed_files": [], "stopped_watcher_pids": [], "tmux_env": {}},
                ):
                    with patch("start_formal_runtime_chain.subprocess.run") as mock_run:
                        mock_run.return_value = Mock(returncode=0)
                        with patch.object(
                            sys,
                            "argv",
                            [
                                "start_formal_runtime_chain.py",
                                "--codex-thread-id",
                                "test-thread",
                                "--pane-title",
                                "dev-bot-1",
                            ],
                        ):
                            rc = start_formal_runtime_chain.main()

        self.assertEqual(0, rc)
        tmux_command = mock_run.call_args.args[0]
        self.assertEqual(["tmux", "new-session", "-s", "formal-session", "-c", "/Users/busiji/workbot"], tmux_command[:6])
        self.assertIn("--continue-inside-formal", tmux_command[6])
        self.assertIn("--codex-thread-id", tmux_command[6])

    def test_start_formal_runtime_chain_launcher_rejects_hidden_terminal(self) -> None:
        hidden_snapshot = runtime_snapshot(
            sessions=[],
            panes=[],
            clients=[],
            current_client={
                "inside_tmux": False,
                "session_name": "",
                "client_tty": "",
                "visible_terminal_client": False,
                "visibility_reason": "codex_hidden_pty",
            },
            visible_terminal_client=False,
        )
        with patch("start_formal_runtime_chain.inspect_runtime_snapshot", return_value=hidden_snapshot):
            with patch.object(
                sys,
                "argv",
                [
                    "start_formal_runtime_chain.py",
                    "--codex-thread-id",
                    "test-thread",
                    "--pane-title",
                    "dev-bot-1",
                    "--pretty",
                ],
            ):
                with patch("sys.stdout", new_callable=io.StringIO) as stdout:
                    rc = start_formal_runtime_chain.main()

        self.assertEqual(1, rc)
        payload = json.loads(stdout.getvalue())
        self.assertIn("refusing startup from codex_hidden_pty", payload["error"])

    def test_start_formal_runtime_chain_continuation_uses_initialize_only_env(self) -> None:
        env_command: list[str] = []
        formal_snapshot = runtime_snapshot(
            sessions=[{"session_name": "formal-session", "attached": 1}],
            panes=[{"session_name": "formal-session", "target": "formal-session:1.1", "window_index": "1", "pane_index": "1"}],
            clients=[{"session_name": "formal-session", "client_tty": "/dev/ttys048"}],
            current_client={
                "inside_tmux": True,
                "session_name": "formal-session",
                "client_tty": "/dev/ttys048",
            },
            visible_terminal_client=True,
            formal_sessions=["formal-session"],
            bootstrap_sessions=[],
        )
        inspect_after_titles = dict(formal_snapshot)
        inspect_after_titles["topology_fingerprint"] = "test-topology"

        def fake_run_json(command: list[str], *, step: str) -> dict[str, object]:
            nonlocal env_command
            if step == "pre_continuation_guard":
                return formal_snapshot
            if step == "env":
                env_command = command
                return {"phase": "env", "runtime_status": "INIT_IN_PROGRESS"}
            if step == "inspect_after_env":
                return formal_snapshot
            if step == "topology":
                return {"phase": "topology"}
            if step == "inspect_after_topology":
                return formal_snapshot
            if step == "pane-title-application":
                return {"verified": True}
            if step == "inspect_after_titles":
                return inspect_after_titles
            if step == "ledger":
                return {"phase": "ledger"}
            if step == "watcher":
                return {"phase": "watcher"}
            raise AssertionError(f"unexpected step: {step}")

        def fake_run(command: list[str]) -> Mock:
            if command[:3] == ["tmux", "set-environment", "-g"]:
                return Mock(returncode=0, stdout="", stderr="")
            if command[:3] == ["tmux", "show-environment", "-g"]:
                return Mock(returncode=0, stdout="CODEX_THREAD_ID=test-thread\n", stderr="")
            if command[:3] == ["tmux", "set-option", "-t"]:
                return Mock(returncode=0, stdout="", stderr="")
            raise AssertionError(f"unexpected run command: {command}")

        with patch("start_formal_runtime_chain.run_json", side_effect=fake_run_json):
            with patch(
                "start_formal_runtime_chain.run_json_with_status",
                return_value=({"runtime_status": "READY", "reasons": []}, 0),
            ):
                with patch("start_formal_runtime_chain.run", side_effect=fake_run):
                    with patch.object(
                        sys,
                        "argv",
                        [
                            "start_formal_runtime_chain.py",
                            "--codex-thread-id",
                            "test-thread",
                            "--pane-title",
                            "dev-bot-1",
                            "--continue-inside-formal",
                        ],
                    ):
                        with patch("sys.stdout", new_callable=io.StringIO):
                            rc = start_formal_runtime_chain.main()

        self.assertEqual(0, rc)
        self.assertNotIn("--create-formal-session", env_command)
        self.assertNotIn("--kill-detached", env_command)

    def test_start_formal_runtime_chain_continuation_fails_when_extra_session_survives(self) -> None:
        inspect_after_env = runtime_snapshot(
            sessions=[
                {"session_name": "formal-session", "attached": 1},
                {"session_name": "tbot", "attached": 0},
            ],
            panes=[
                {
                    "session_name": "formal-session",
                    "target": "formal-session:1.1",
                    "window_index": "1",
                    "pane_index": "1",
                }
            ],
            clients=[{"session_name": "formal-session", "client_tty": "/dev/ttys048"}],
            current_client={
                "inside_tmux": True,
                "session_name": "formal-session",
                "client_tty": "/dev/ttys048",
            },
            formal_sessions=["formal-session"],
            bootstrap_sessions=["tbot"],
        )

        def fake_run_json(command: list[str], *, step: str) -> dict[str, object]:
            if step == "pre_continuation_guard":
                return inspect_after_env
            if step == "env":
                return {"phase": "env", "runtime_status": "INIT_IN_PROGRESS"}
            if step == "inspect_after_env":
                return inspect_after_env
            raise AssertionError(f"unexpected step: {step}")

        with patch("start_formal_runtime_chain.run_json", side_effect=fake_run_json):
            with patch(
                "start_formal_runtime_chain.cleanup_hidden_formal_session_on_failure",
                return_value={"attempted": False, "reason": "skip"},
            ):
                with patch.object(
                    sys,
                    "argv",
                    [
                        "start_formal_runtime_chain.py",
                        "--codex-thread-id",
                        "test-thread",
                        "--pane-title",
                        "dev-bot-1",
                        "--continue-inside-formal",
                        "--pretty",
                    ],
                ):
                    with patch("sys.stdout", new_callable=io.StringIO) as stdout:
                        rc = start_formal_runtime_chain.main()

        self.assertEqual(1, rc)
        payload = json.loads(stdout.getvalue())
        self.assertIn("unexpected tmux residue remains after startup: tbot", payload["error"])

    def test_init_tmux_env_send_startup_command_quotes_command(self) -> None:
        with patch("init_tmux_env.run_tmux") as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout="", stderr="")
            result = init_tmux_env.send_startup_command("formal-session:1.1", "echo 'hello world'")

        self.assertEqual("startup_command='echo '\"'\"'hello world'\"'\"''", result)
        mock_run.assert_called_once_with(
            "send-keys",
            "-t",
            "formal-session:1.1",
            "C-c",
            "echo 'hello world'",
            "Enter",
        )

    def test_arm_watcher_rejects_attached_session_without_formal_client(self) -> None:
        snapshot = runtime_snapshot(
            sessions=[{"session_name": "formal-session", "attached": 1}],
            panes=[{"session_name": "formal-session", "target": "formal-session:1.1"}],
            clients=[
                {
                    "client_tty": "/dev/ttys048",
                    "client_session": "bootstrap",
                    "session_name": "bootstrap",
                    "session_attached": 1,
                }
            ],
            runtime_ledger=formal_runtime_ledger(pane_count=1, targets=["formal-session:1.1"]),
        )
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
                        with self.assertRaises(SystemExit) as exc:
                            arm_tmux_handoff_watcher.main()

        self.assertNotEqual(0, getattr(exc.exception, "code", 0))

    def test_pane_dead_snapshot_is_classified_as_stopped(self) -> None:
        classification = watch_tmux_handoff.classify_snapshot(
            {"session_attached": 1, "pane_dead": 1, "pane_dead_status": "0"}
        )
        self.assertEqual(("pane_stopped", "pane 已停止 (0)", "pane_stopped"), classification)

    def test_live_snapshot_is_not_classified_as_stopped(self) -> None:
        classification = watch_tmux_handoff.classify_snapshot(
            {"session_attached": 1, "pane_dead": 0, "current_command": "zsh"}
        )
        self.assertIsNone(classification)

    def test_once_scan_does_not_emit_for_live_idle_shell(self) -> None:
        snapshot = {
            "target": "formal-session:1.1",
            "session": "formal-session",
            "window": "1",
            "pane_index": "1",
            "pane_id": "%1",
            "pane_title": "task-1",
            "cwd": "/Users/busiji/workbot",
            "current_command": "zsh",
            "pane_dead": 0,
            "pane_dead_status": "",
            "session_attached": 1,
            "recent_output": "busiji@host workbot %",
            "recent_output_hash": "abc123",
            "reachable": True,
            "state_signature": "sig-1",
        }
        with patch.object(
            sys,
            "argv",
            [
                "watch_tmux_handoff.py",
                "--target",
                "formal-session:1.1",
                "--once",
            ],
        ):
            with patch("watch_tmux_handoff.read_tmux_session_binding", return_value="thread-1"):
                with patch("watch_tmux_handoff.capture_snapshot", return_value=snapshot):
                    with patch("watch_tmux_handoff.record_event") as mock_record:
                        stdout = io.StringIO()
                        with patch("sys.stdout", stdout):
                            rc = watch_tmux_handoff.main()

        self.assertEqual(0, rc)
        self.assertEqual("", stdout.getvalue())
        mock_record.assert_not_called()

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
                cached_snapshot={"pane_title": "notes"},
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
                    "message": "notes pane 已停止：formal-session:1.3",
                }
            }
            client = Mock()
            tmux_handoff_app_bridge.process_queue_item(
                queue_file,
                client=client,
                receipts_log=receipts_log,
                receipts_by_event_id=receipts,
                confirm_timeout=1.0,
                idle_timeout=1.0,
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
            client.wait_for_thread_idle.return_value = True
            tmux_handoff_app_bridge.process_queue_item(
                queue_file,
                client=client,
                receipts_log=receipts_log,
                receipts_by_event_id=receipts,
                confirm_timeout=1.0,
                idle_timeout=1.0,
                max_retries=1,
            )
            lines = receipts_log.read_text(encoding="utf-8").splitlines()
        client.deliver_turn_to_current_window.assert_called_once()
        client.wait_for_thread_idle.assert_called_once()
        self.assertFalse(queue_file.exists())
        self.assertEqual(1, len(lines))
        receipt = json.loads(lines[0])
        self.assertEqual("delivered", receipt["status"])
        self.assertEqual("turn-123", receipt["turn_id"])
        self.assertEqual("client-123", receipt["handled_by_client_id"])
        self.assertEqual("owner_window_response+thread_stream_state_changed+thread_idle", receipt["reason"])

    def test_bridge_keeps_queue_item_while_waiting_for_thread_idle(self) -> None:
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
            client.wait_for_thread_idle.return_value = False
            tmux_handoff_app_bridge.process_queue_item(
                queue_file,
                client=client,
                receipts_log=receipts_log,
                receipts_by_event_id=receipts,
                confirm_timeout=1.0,
                idle_timeout=1.0,
                max_retries=1,
            )
            lines = receipts_log.read_text(encoding="utf-8").splitlines()
            queue_exists = queue_file.exists()

        client.deliver_turn_to_current_window.assert_called_once()
        client.wait_for_thread_idle.assert_called_once()
        self.assertTrue(queue_exists)
        receipt = json.loads(lines[0])
        self.assertEqual("accepted_waiting_idle", receipt["status"])
        self.assertEqual("client-123", receipt["handled_by_client_id"])

    def test_bridge_resumes_waiting_item_without_redelivery(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            queue_file = Path(tmpdir) / "queued.json"
            queue_file.write_text(json.dumps(sample_event("pane_stopped")), encoding="utf-8")
            receipts_log = Path(tmpdir) / "receipts.jsonl"
            receipts: dict[str, dict[str, object]] = {
                "0123456789abcdef": {
                    "status": "accepted_waiting_idle",
                    "thread_id": "019d3900-80a8-7be1-8e7e-ffa52e0816d3",
                    "message": "notes pane 已停止：formal-session:1.3",
                    "turn_id": "turn-123",
                    "handled_by_client_id": "client-123",
                    "reason": "owner_window_response+thread_stream_state_changed",
                }
            }
            client = Mock()
            client.wait_for_thread_idle.return_value = True
            tmux_handoff_app_bridge.process_queue_item(
                queue_file,
                client=client,
                receipts_log=receipts_log,
                receipts_by_event_id=receipts,
                confirm_timeout=1.0,
                idle_timeout=1.0,
                max_retries=1,
            )
            lines = receipts_log.read_text(encoding="utf-8").splitlines()

        client.deliver_turn_to_current_window.assert_not_called()
        client.wait_for_thread_idle.assert_called_once()
        self.assertFalse(queue_file.exists())
        receipt = json.loads(lines[0])
        self.assertEqual("delivered", receipt["status"])
        self.assertEqual("owner_window_response+thread_stream_state_changed+thread_idle", receipt["reason"])

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

    def test_build_tmux_topology_main_rejects_hidden_context(self) -> None:
        hidden_snapshot = runtime_snapshot(
            sessions=[{"session_name": "formal-session", "attached": 1}],
            panes=[{"session_name": "formal-session", "target": "formal-session:1.1"}],
            clients=[{"session_name": "formal-session", "client_tty": "/dev/ttys048"}],
            current_client={
                "inside_tmux": True,
                "session_name": "formal-session",
                "client_tty": "/dev/ttys048",
                "visible_terminal_client": False,
                "visibility_reason": "codex_hidden_pty",
            },
            visible_terminal_client=False,
            current_visible_formal_client=False,
        )
        args = Namespace(session=None, formal_session="formal-session", target_pane_count=2, pretty=False)
        with patch("build_tmux_topology.parse_args", return_value=args):
            with patch("build_tmux_topology.inspect_runtime", return_value=hidden_snapshot):
                with patch("build_tmux_topology.reconcile_topology") as mock_reconcile:
                    with self.assertRaises(SystemExit) as exc:
                        build_tmux_topology.main()
        self.assertIn("current_visible_formal_client=true", str(exc.exception))
        mock_reconcile.assert_not_called()

    def test_init_tmux_panes_main_rejects_hidden_context(self) -> None:
        hidden_snapshot = runtime_snapshot(
            sessions=[{"session_name": "formal-session", "attached": 1}],
            panes=[{"session_name": "formal-session", "target": "formal-session:1.1"}],
            clients=[{"session_name": "formal-session", "client_tty": "/dev/ttys048"}],
            current_client={
                "inside_tmux": True,
                "session_name": "formal-session",
                "client_tty": "/dev/ttys048",
                "visible_terminal_client": False,
                "visibility_reason": "codex_hidden_pty",
            },
            visible_terminal_client=False,
            current_visible_formal_client=False,
        )
        args = Namespace(
            target="formal-session:1.1",
            slot=None,
            window_title=None,
            pane_title="dev-bot",
            batch_file=None,
            pretty=False,
        )
        with patch("init_tmux_panes.parse_args", return_value=args):
            with patch("init_tmux_panes.inspect_runtime", return_value=hidden_snapshot):
                with patch("init_tmux_panes.initialize_entry") as mock_initialize_entry:
                    with patch("sys.stdout", new_callable=io.StringIO) as stdout:
                        rc = init_tmux_panes.main()
        self.assertEqual(1, rc)
        payload = json.loads(stdout.getvalue())
        self.assertIn("current_visible_formal_client=true", payload["error"])
        mock_initialize_entry.assert_not_called()

    def test_init_runtime_ledger_main_rejects_hidden_context(self) -> None:
        hidden_snapshot = runtime_snapshot(
            sessions=[{"session_name": "formal-session", "attached": 1}],
            panes=[{"session_name": "formal-session", "target": "formal-session:1.1"}],
            clients=[{"session_name": "formal-session", "client_tty": "/dev/ttys048"}],
            current_client={
                "inside_tmux": True,
                "session_name": "formal-session",
                "client_tty": "/dev/ttys048",
                "visible_terminal_client": False,
                "visibility_reason": "codex_hidden_pty",
            },
            visible_terminal_client=False,
            current_visible_formal_client=False,
        )
        args = Namespace(
            task_id="tmux-skills-public-run",
            pane_count=2,
            topology_fingerprint="fingerprint",
            formal_session_name="formal-session",
            runtime_status="READY",
            slot_binding=[],
            slot_bindings_json="",
            watcher_armed=False,
            watcher_target=[],
            watcher_pid=None,
            codex_thread_bound=True,
            worker_ceiling=3,
            pretty=False,
        )
        with patch("init_runtime_ledger.parse_args", return_value=args):
            with patch("init_runtime_ledger.inspect_runtime", return_value=hidden_snapshot):
                with patch("init_runtime_ledger.init_current_runtime_ledger") as mock_init_ledger:
                    with self.assertRaises(SystemExit) as exc:
                        init_runtime_ledger.main()
        self.assertIn("current_visible_formal_client=true", str(exc.exception))
        mock_init_ledger.assert_not_called()

    def test_start_formal_runtime_chain_continuation_fails_in_hidden_context(self) -> None:
        """Rule 3: hidden context only allows failure validation, not positive changes.

        When current_visible_formal_client is False, the continuation path must fail fast
        before any topology/init_panes/ledger/watcher steps.
        """
        hidden_snapshot = runtime_snapshot(
            sessions=[{"session_name": "formal-session", "attached": 1}],
            panes=[{"session_name": "formal-session", "target": "formal-session:1.1", "window_index": "1", "pane_index": "1"}],
            clients=[{"session_name": "formal-session", "client_tty": "/dev/ttys048"}],
            current_client={
                "inside_tmux": True,
                "session_name": "formal-session",
                "client_tty": "/dev/ttys048",
                "visible_terminal_client": False,
                "visibility_reason": "codex_hidden_pty",
            },
            visible_terminal_client=False,
            current_visible_formal_client=False,
            formal_sessions=["formal-session"],
            bootstrap_sessions=[],
        )

        def fake_run_json(command: list[str], *, step: str) -> dict[str, object]:
            if step == "pre_continuation_guard":
                return hidden_snapshot
            raise AssertionError(f"unexpected step after guard: {step}")

        with patch("start_formal_runtime_chain.inspect_runtime_snapshot", return_value=hidden_snapshot):
            with patch("start_formal_runtime_chain.run_json", side_effect=fake_run_json):
                with patch.object(
                    sys,
                    "argv",
                    [
                        "start_formal_runtime_chain.py",
                        "--codex-thread-id",
                        "test-thread",
                        "--pane-title",
                        "dev-bot",
                        "--continue-inside-formal",
                        "--pretty",
                    ],
                ):
                    with patch("sys.stdout", new_callable=io.StringIO) as stdout:
                        rc = start_formal_runtime_chain.main()

        self.assertEqual(1, rc)
        payload = json.loads(stdout.getvalue())
        self.assertIn("current_visible_formal_client=true", payload["error"])
        self.assertNotIn("topology", payload.get("steps", {}))
        self.assertNotIn("titles", payload.get("steps", {}))
        self.assertNotIn("ledger", payload.get("steps", {}))
        self.assertNotIn("watcher", payload.get("steps", {}))


if __name__ == "__main__":
    unittest.main()
