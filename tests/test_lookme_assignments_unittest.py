#!/usr/bin/env python3
"""Regression tests for the assignment-driven lookme watcher."""

from __future__ import annotations

import json
import io
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock


ARTIFACTS_DIR = Path("/Users/busiji/workbot/workspace/artifacts/tmux-skills/lookme")
if str(ARTIFACTS_DIR) not in sys.path:
    sys.path.insert(0, str(ARTIFACTS_DIR))

import watch_assignments  # noqa: E402
import generate_lookme_assignments  # noqa: E402
import lookme_supervisor  # noqa: E402
import lookme_finish_cycle  # noqa: E402
import lookme_ctl  # noqa: E402
import watch_pane  # noqa: E402


class LookmeAssignmentsTests(unittest.TestCase):
    def make_args(self, **overrides):
        defaults = {
            "assignment_file": "/tmp/assignments.json",
            "history_start": -20,
            "tail_lines": 20,
            "interval": 0.1,
            "max_idle": 0,
            "blocked_remind_polls": 2,
            "completion_regex": None,
            "task_file": None,
            "task_text": None,
            "auto_approve": False,
            "action_cooldown": 2.0,
            "approval_stuck_polls": 3,
            "sop_followup_delay": 1.0,
            "exit_when_idle": False,
        }
        defaults.update(overrides)
        return type("Args", (), defaults)()

    def test_parse_args_defaults_to_resident_mode(self) -> None:
        original_argv = sys.argv[:]
        try:
            sys.argv = ["lookme.py", "--assignment-file", "/tmp/assignments.json"]
            args = watch_assignments.parse_args()
        finally:
            sys.argv = original_argv

        self.assertFalse(args.exit_when_idle)
        self.assertTrue(args.finish_on_complete)

    def write_assignment_file(self, payload: object) -> str:
        tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(tmpdir.cleanup)
        path = Path(tmpdir.name) / "assignments.json"
        path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        return str(path)

    def test_load_assignment_file_parses_display_and_markers(self) -> None:
        path = self.write_assignment_file(
            {
                "task_id": "task-1",
                "panes": [
                    {
                        "assignment_id": "dev-1",
                        "target": "formal-session:1.1",
                        "bot_name": "dev-bot",
                        "title": "Fix login",
                        "success_markers": ["done", "completed"],
                        "blocked_markers": ["approval"],
                        "allow_intervene": True,
                        "status": "ACTIVE",
                    },
                    {
                        "assignment_id": "qa-1",
                        "target": "formal-session:1.2",
                        "bot_name": "qa-bot",
                        "title": "Regression",
                        "status": "COMPLETED",
                    },
                ],
            }
        )

        assignments = watch_assignments.load_assignment_file(path)

        self.assertEqual(2, len(assignments))
        self.assertEqual("dev-bot / Fix login", assignments[0].display_name)
        self.assertEqual(("done", "completed"), assignments[0].success_markers)
        self.assertEqual(("approval",), assignments[0].blocked_markers)
        self.assertTrue(assignments[0].allow_intervene)
        self.assertEqual("COMPLETED", assignments[1].status)

    def test_load_assignment_file_rejects_duplicate_active_targets(self) -> None:
        path = self.write_assignment_file(
            {
                "panes": [
                    {
                        "assignment_id": "dev-1",
                        "target": "formal-session:1.1",
                        "status": "ACTIVE",
                    },
                    {
                        "assignment_id": "dev-2",
                        "target": "formal-session:1.1",
                        "status": "RUNNING",
                    },
                ]
            }
        )

        with self.assertRaises(ValueError) as exc:
            watch_assignments.load_assignment_file(path)

        self.assertIn("duplicate active target", str(exc.exception))

    def test_placeholder_assignment_is_not_ready_for_startup(self) -> None:
        assignment = watch_assignments.WatchAssignment(
            target="formal-session:1.1",
            assignment_id="pane-1-1",
            bot_name="",
            role="unassigned",
            title="待分配任务 #1.1",
            goal="等待为该 pane 指定真实任务。",
            display_name="待分配任务 #1.1 / formal-session:1.1",
            status="PENDING",
            allow_intervene=False,
            task_text=None,
            continue_text=None,
            completion_regex=None,
            success_markers=(),
            blocked_markers=(),
        )

        self.assertFalse(watch_assignments.assignment_has_task_allocation(assignment))

    def test_validate_active_assignments_ready_rejects_unassigned_entries(self) -> None:
        assignment = watch_assignments.WatchAssignment(
            target="formal-session:1.1",
            assignment_id="pane-1-1",
            bot_name="",
            role="unassigned",
            title="待分配任务 #1.1",
            goal="等待为该 pane 指定真实任务。",
            display_name="待分配任务 #1.1 / formal-session:1.1",
            status="ACTIVE",
            allow_intervene=False,
            task_text=None,
            continue_text=None,
            completion_regex=None,
            success_markers=(),
            blocked_markers=(),
        )

        with self.assertRaises(ValueError) as exc:
            watch_assignments.validate_active_assignments_ready([assignment])

        self.assertIn("lookme requires task allocation before startup", str(exc.exception))

    def test_classify_assignment_state_marks_dead_pane(self) -> None:
        assignment = watch_assignments.WatchAssignment(
            target="formal-session:1.1",
            assignment_id="dev-1",
            bot_name="dev-bot",
            role="dev",
            title="Fix login",
            goal="",
            display_name="dev-bot / Fix login",
            status="ACTIVE",
            allow_intervene=False,
            task_text=None,
            continue_text=None,
            completion_regex=None,
            success_markers=(),
            blocked_markers=(),
        )

        state, blocking = watch_assignments.classify_assignment_state(
            assignment,
            "pane_id=%1 title=✳ Claude Code cmd=node active=1 dead=1 in_mode=0 path=/tmp",
            "still visible",
        )

        self.assertEqual("pane_dead", state)
        self.assertTrue(blocking)

    def test_classify_assignment_state_ignores_accept_edits_footer(self) -> None:
        assignment = watch_assignments.WatchAssignment(
            target="formal-session:1.1",
            assignment_id="dev-1",
            bot_name="dev-bot",
            role="dev",
            title="Fix login",
            goal="",
            display_name="dev-bot / Fix login",
            status="ACTIVE",
            allow_intervene=False,
            task_text=None,
            continue_text=None,
            completion_regex=None,
            success_markers=(),
            blocked_markers=(),
        )

        state, blocking = watch_assignments.classify_assignment_state(
            assignment,
            "pane_id=%1 title=✳ Claude Code cmd=node active=1 dead=0 in_mode=0 path=/tmp",
            "❯",
            raw_body="...\n⏵⏵ accept edits on (shift+tab to cycle)\n",
        )

        self.assertEqual("waiting_input", state)
        self.assertFalse(blocking)

    def test_sanitize_tail_text_hides_bare_input_prompt_line(self) -> None:
        sanitized = watch_pane.sanitize_tail_text(
            "line1\nuseful context\n❯\n",
            5,
        )

        self.assertEqual("line1\nuseful context", sanitized)

    def test_is_assignment_complete_uses_success_markers(self) -> None:
        assignment = watch_assignments.WatchAssignment(
            target="formal-session:1.1",
            assignment_id="dev-1",
            bot_name="dev-bot",
            role="dev",
            title="Fix login",
            goal="",
            display_name="dev-bot / Fix login",
            status="ACTIVE",
            allow_intervene=False,
            task_text=None,
            continue_text=None,
            completion_regex=None,
            success_markers=("validation passed",),
            blocked_markers=(),
        )

        completed = watch_assignments.is_assignment_complete(
            assignment,
            "pane_id=%1 title=✳ Claude Code cmd=node active=1 dead=0 in_mode=0 path=/tmp",
            "validation passed\n❯",
            "waiting_input",
            fallback_completion_regex=None,
        )

        self.assertTrue(completed)

    def test_completion_is_suppressed_before_any_running_observed(self) -> None:
        runtime_state = watch_assignments.TargetRuntimeState(assignment_id="dev-1")
        self.assertFalse(watch_assignments.can_mark_completed(runtime_state))

        runtime_state.observed_running = True
        self.assertTrue(watch_assignments.can_mark_completed(runtime_state))

    def test_render_state_label_maps_approval_to_tmux_sop(self) -> None:
        self.assertEqual(
            "go_tmux_window_approval_sop",
            watch_assignments.render_state_label("approval_prompt"),
        )
        self.assertEqual(
            "go_tmux_window_approval_sop",
            watch_assignments.render_state_label("approval_stuck"),
        )
        self.assertEqual("waiting_input", watch_assignments.render_state_label("waiting_input"))

    def test_print_notify_uses_fixed_parseable_format(self) -> None:
        assignment = watch_assignments.WatchAssignment(
            target="formal-session:1.3",
            assignment_id="qa-1",
            bot_name="qa-bot",
            role="qa",
            title="OCR 主路径 QA 结论",
            goal="",
            display_name="qa-bot / OCR 主路径 QA 结论",
            status="ACTIVE",
            allow_intervene=False,
            task_text=None,
            continue_text=None,
            completion_regex=None,
            success_markers=(),
            blocked_markers=(),
        )

        output = io.StringIO()
        with redirect_stdout(output):
            watch_assignments.print_notify(assignment, "approval_prompt")

        rendered = output.getvalue().strip()
        self.assertIn("[notify]", rendered)
        self.assertIn("state=go_tmux_window_approval_sop", rendered)
        self.assertIn("target=formal-session:1.3", rendered)
        self.assertIn("assignment_id=qa-1", rendered)

    def test_build_initial_prompt_falls_back_to_goal(self) -> None:
        assignment = watch_assignments.WatchAssignment(
            target="formal-session:1.1",
            assignment_id="dev-1",
            bot_name="dev-bot",
            role="dev",
            title="OCR 主路径收口",
            goal="围绕 DEV-004 继续补百度 OCR API 主路径最小验证与测试收口。",
            display_name="dev-bot / OCR 主路径收口",
            status="ACTIVE",
            allow_intervene=True,
        )

        prompt = watch_assignments.build_initial_prompt(assignment)

        self.assertIn("直接开始执行当前 assignment", prompt)
        self.assertIn("dev-bot / OCR 主路径收口", prompt)
        self.assertIn("围绕 DEV-004", prompt)

    def test_build_continue_prompt_mentions_retry_count(self) -> None:
        assignment = watch_assignments.WatchAssignment(
            target="formal-session:1.2",
            assignment_id="dev-2",
            bot_name="dev-bot",
            role="dev-b",
            title="主链测试与回归收口",
            goal="围绕 TWIN、GRAPH、OBS 与非 OCR 主链继续做最小改动和回归收口。",
            display_name="dev-bot / dev-b / 主链回归收口",
            status="ACTIVE",
            allow_intervene=True,
        )
        runtime_state = watch_assignments.TargetRuntimeState(
            assignment_id="dev-2",
            continue_dispatch_count=1,
        )

        prompt = watch_assignments.build_continue_prompt(
            assignment,
            runtime_state,
            "当前尾部\n❯",
        )

        self.assertIn("继续执行当前 assignment", prompt)
        self.assertIn("这是第 2 次继续执行提醒", prompt)
        self.assertIn("当前停住位置参考: ❯", prompt)

    def test_print_followup_notify_uses_repeat_and_action(self) -> None:
        assignment = watch_assignments.WatchAssignment(
            target="formal-session:1.4",
            assignment_id="doc-1",
            bot_name="doc-bot",
            role="doc",
            title="文档同步与 CE 准备",
            goal="",
            display_name="doc-bot / 文档同步与 CE 准备",
            status="ACTIVE",
            allow_intervene=False,
            task_text=None,
            continue_text=None,
            completion_regex=None,
            success_markers=(),
            blocked_markers=(),
        )

        output = io.StringIO()
        with redirect_stdout(output):
            watch_assignments.print_followup_notify(assignment, 2)

        rendered = output.getvalue().strip()
        self.assertIn("state=go_tmux_window_approval_sop_followup", rendered)
        self.assertIn("target=formal-session:1.4", rendered)
        self.assertIn("assignment_id=doc-1", rendered)
        self.assertIn("repeat=2", rendered)
        self.assertIn("action=visit_tmux_pane_for_sop", rendered)

    def test_build_initial_prompt_falls_back_to_goal(self) -> None:
        assignment = watch_assignments.WatchAssignment(
            target="formal-session:1.1",
            assignment_id="dev-1",
            bot_name="dev-bot",
            role="dev",
            title="",
            goal="围绕 DEV-004 继续补百度 OCR API 主路径最小验证与测试收口。",
            display_name="dev-bot / OCR 主路径收口",
            status="ACTIVE",
            allow_intervene=True,
            task_text=None,
            continue_text=None,
            completion_regex=None,
            success_markers=(),
            blocked_markers=(),
        )

        prompt = watch_assignments.build_initial_prompt(assignment)

        self.assertIsNotNone(prompt)
        self.assertIn("assignment: dev-bot / OCR 主路径收口", prompt)
        self.assertIn("目标: 围绕 DEV-004 继续补百度 OCR API 主路径最小验证与测试收口。", prompt)
        self.assertIn("直接开始执行当前 assignment", prompt)

    def test_has_accept_edits_footer_detects_claude_ui_hint(self) -> None:
        self.assertTrue(
            watch_assignments.has_accept_edits_footer(
                "...\n⏵⏵ accept edits on (shift+tab to cycle)\n",
            )
        )
        self.assertFalse(watch_assignments.has_accept_edits_footer("plain output\n❯\n"))

    def test_print_execution_followup_notify_uses_execution_state(self) -> None:
        assignment = watch_assignments.WatchAssignment(
            target="formal-session:1.4",
            assignment_id="doc-1",
            bot_name="doc-bot",
            role="doc",
            title="文档同步与 CE 准备",
            goal="",
            display_name="doc-bot / 文档同步与 CE 准备",
            status="ACTIVE",
            allow_intervene=True,
            task_text=None,
            continue_text=None,
            completion_regex=None,
            success_markers=(),
            blocked_markers=(),
        )

        output = io.StringIO()
        with redirect_stdout(output):
            watch_assignments.print_execution_followup_notify(assignment, 2)

        rendered = output.getvalue().strip()
        self.assertIn("state=go_tmux_window_execute_followup", rendered)
        self.assertIn("target=formal-session:1.4", rendered)
        self.assertIn("assignment_id=doc-1", rendered)
        self.assertIn("repeat=2", rendered)
        self.assertIn("action=visit_tmux_pane_to_continue_execution", rendered)

    def test_print_stuck_followup_notify_uses_manual_check_state(self) -> None:
        assignment = watch_assignments.WatchAssignment(
            target="formal-session:1.2",
            assignment_id="dev-8",
            bot_name="dev-bot",
            role="dev-b",
            title="家长端周报月报解释对象收口",
            goal="",
            display_name="dev-bot / dev-b / 家长端周报月报解释对象收口",
            status="ACTIVE",
            allow_intervene=True,
            task_text=None,
            continue_text=None,
            completion_regex=None,
            success_markers=(),
            blocked_markers=(),
        )

        output = io.StringIO()
        with redirect_stdout(output):
            watch_assignments.print_stuck_followup_notify(assignment, 2, "waiting_input")

        rendered = output.getvalue().strip()
        self.assertIn("state=go_tmux_window_check_stuck_pane", rendered)
        self.assertIn("target=formal-session:1.2", rendered)
        self.assertIn("assignment_id=dev-8", rendered)
        self.assertIn("repeat=2", rendered)
        self.assertIn("pane_state=waiting_input", rendered)
        self.assertIn("action=visit_tmux_pane_for_manual_check", rendered)

    def test_print_notify_appends_structured_event_log(self) -> None:
        assignment = watch_assignments.WatchAssignment(
            target="formal-session:1.2",
            assignment_id="dev-8",
            bot_name="dev-bot",
            role="dev-b",
            title="家长端周报月报解释对象收口",
            goal="",
            display_name="dev-bot / dev-b / 家长端周报月报解释对象收口",
            status="ACTIVE",
            allow_intervene=True,
            task_text=None,
            continue_text=None,
            completion_regex=None,
            success_markers=(),
            blocked_markers=(),
        )
        tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(tmpdir.cleanup)
        log_path = Path(tmpdir.name) / "events.jsonl"

        with mock.patch.object(watch_assignments, "DEFAULT_EVENT_LOG_PATH", log_path):
            output = io.StringIO()
            with redirect_stdout(output):
                watch_assignments.print_notify(assignment, "approval_prompt")

        content = log_path.read_text(encoding="utf-8")
        self.assertIn('"event_type": "notify"', content)
        self.assertIn('"state": "go_tmux_window_approval_sop"', content)
        self.assertIn('"assignment_id": "dev-8"', content)

    def test_is_generic_stuck_candidate_only_flags_prompt_like_states(self) -> None:
        self.assertTrue(watch_assignments.is_generic_stuck_candidate("waiting_input"))
        self.assertTrue(watch_assignments.is_generic_stuck_candidate("idle"))
        self.assertTrue(watch_assignments.is_generic_stuck_candidate("task_blocked"))
        self.assertFalse(watch_assignments.is_generic_stuck_candidate("running"))
        self.assertFalse(watch_assignments.is_generic_stuck_candidate("approval_prompt"))

    def test_main_retries_when_assignment_file_is_temporarily_invalid(self) -> None:
        args = self.make_args()
        with mock.patch.object(watch_assignments, "parse_args", return_value=args), mock.patch.object(
            watch_assignments,
            "read_task_text",
            return_value=None,
        ), mock.patch.object(
            watch_assignments,
            "load_assignment_file",
            side_effect=ValueError("bad json"),
        ), mock.patch.object(
            watch_assignments,
            "print_error",
        ) as print_error, mock.patch(
            "watch_assignments.time.sleep",
            side_effect=KeyboardInterrupt,
        ):
            with self.assertRaises(KeyboardInterrupt):
                watch_assignments.main()

        print_error.assert_called_once()
        self.assertIn("assignment_error", print_error.call_args.args[0])

    def test_main_retries_when_process_assignment_hits_runtime_error(self) -> None:
        args = self.make_args()
        assignment = watch_assignments.WatchAssignment(
            target="formal-session:1.1",
            assignment_id="dev-1",
            bot_name="dev-bot",
            role="dev",
            title="Fix login",
            goal="Do work",
            display_name="dev-bot / Fix login",
            status="ACTIVE",
            allow_intervene=False,
        )
        with mock.patch.object(watch_assignments, "parse_args", return_value=args), mock.patch.object(
            watch_assignments,
            "read_task_text",
            return_value=None,
        ), mock.patch.object(
            watch_assignments,
            "load_assignment_file",
            return_value=[assignment],
        ), mock.patch.object(
            watch_assignments,
            "validate_active_assignments_ready",
            return_value=None,
        ), mock.patch.object(
            watch_assignments,
            "process_assignment",
            side_effect=RuntimeError("tmux command failed"),
        ), mock.patch.object(
            watch_assignments,
            "print_error",
        ) as print_error, mock.patch(
            "watch_assignments.time.sleep",
            side_effect=KeyboardInterrupt,
        ):
            with self.assertRaises(KeyboardInterrupt):
                watch_assignments.main()

        print_error.assert_called_once()
        self.assertIn("process_assignment_error", print_error.call_args.args[0])

    def test_assignment_id_to_task_id_zero_pads(self) -> None:
        self.assertEqual("DEV-015", lookme_finish_cycle.assignment_id_to_task_id("dev-15"))
        self.assertEqual("QA-008", lookme_finish_cycle.assignment_id_to_task_id("qa-8"))
        self.assertEqual("REA-009", lookme_finish_cycle.assignment_id_to_task_id("rea-9"))

    def test_infer_task_id_prefers_evidence_line_over_trailing_task_list(self) -> None:
        assignment = watch_assignments.WatchAssignment(
            target="formal-session:1.3",
            assignment_id="qa-8",
            bot_name="qa-bot",
            role="qa",
            title="班级看板聚合与反馈闭环回归",
            goal="",
            display_name="qa-bot / 班级看板聚合与反馈闭环回归",
            status="ACTIVE",
            allow_intervene=False,
        )
        tail = (
            "QA-007 结论: pass（整体通过率 100%）\n"
            "2 tasks (1 done, 1 open)\n"
            "◻ 执行 QA-006 观察层三端输出 QA 复核\n"
            "✔ 执行 QA-006 观察层三端输出 QA 复核\n"
        )

        inferred = lookme_finish_cycle.infer_task_id(assignment, tail)

        self.assertEqual("QA-007", inferred)

    def test_update_markdown_table_row_updates_status_and_next_step(self) -> None:
        tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(tmpdir.cleanup)
        path = Path(tmpdir.name) / "qa.md"
        path.write_text(
            "| task_id | title | status | owner | write_scope | evidence | blocker | next_step |\n"
            "|---|---|---|---|---|---|---|---|\n"
            "| QA-007 | Demo | `todo` | `qa` | `tests/*` | - | - | old |\n",
            encoding="utf-8",
        )

        updated = lookme_finish_cycle.update_markdown_table_row(
            path,
            "QA-007",
            "qa_done",
            "pass（整体通过率 100%）",
            next_step="转入 CE 同步队列",
        )

        self.assertTrue(updated)
        content = path.read_text(encoding="utf-8")
        self.assertIn("`qa_done`", content)
        self.assertIn("pass（整体通过率 100%）", content)
        self.assertIn("转入 CE 同步队列", content)

    def test_build_gitlab_comment_contains_outcomes(self) -> None:
        body = lookme_finish_cycle.build_gitlab_comment(
            [
                {"task_id": "DEV-015", "status": "dev_done", "summary": "16/16 pytest 通过"},
                {"task_id": "QA-007", "status": "qa_done", "summary": "pass（整体通过率 100%）"},
            ]
        )

        self.assertIn("DEV-015：dev_done", body)
        self.assertIn("QA-007：qa_done", body)
        self.assertIn("commander", body)
        self.assertNotIn("#56", body)

    def test_extract_evidence_line_skips_bare_section_heading(self) -> None:
        tail = "Findings\nEvidence\nBackend\nConclusion\n- 需补同步后复核\n"

        line = lookme_finish_cycle.extract_evidence_line(tail)

        self.assertEqual("- 需补同步后复核", line)

    def test_collect_outcome_maps_rea_assignment_to_done(self) -> None:
        assignment = watch_assignments.WatchAssignment(
            target="formal-session:1.2",
            assignment_id="rea-9",
            bot_name="rea-bot",
            role="rea",
            title="REA-009 阶段四准入审计",
            goal="",
            display_name="rea-bot / REA-009 阶段四准入审计",
            status="ACTIVE",
            allow_intervene=False,
            history_start=-20,
            tail_lines=20,
        )

        with mock.patch.object(
            lookme_finish_cycle,
            "run_tmux_display",
            return_value="pane_id=%4 title=✳ Claude Code cmd=node active=1 dead=0 in_mode=0 path=/tmp",
        ), mock.patch.object(
            lookme_finish_cycle,
            "run_tmux_capture",
            return_value="REA-009 审计结论：#32 继续作为未来阶段锚点保留。",
        ), mock.patch.object(
            lookme_finish_cycle,
            "classify_assignment_state",
            return_value=("waiting_input", False),
        ), mock.patch.object(
            lookme_finish_cycle,
            "is_assignment_complete",
            return_value=True,
        ):
            outcome = lookme_finish_cycle.collect_outcome(assignment)

        self.assertEqual("REA-009", outcome["task_id"])
        self.assertEqual("REA", outcome["prefix"])
        self.assertEqual("done", outcome["status"])

    def test_has_generic_completion_evidence_accepts_delivery_style_tail(self) -> None:
        tail = (
            "DEV-015 交付结论：最小验收支撑已就绪。16/16 pytest 通过\n"
            "下一步：转入 CE 同步\n"
        )

        self.assertTrue(lookme_finish_cycle.has_generic_completion_evidence(tail))

    def test_has_generic_completion_evidence_accepts_closeout_style_tail(self) -> None:
        tail = "阶段三收口结论：QA-006/008/010 已完成，阶段三主线具备 CE 同步条件。"

        self.assertTrue(lookme_finish_cycle.has_generic_completion_evidence(tail))

    def test_run_finish_cycle_reports_success_and_output(self) -> None:
        with mock.patch("watch_assignments.subprocess.run") as run_mock:
            run_mock.return_value = mock.Mock(returncode=0, stdout="ok", stderr="")

            succeeded, message = watch_assignments.run_finish_cycle("/tmp/a.json", "/tmp/finish.py")

        self.assertTrue(succeeded)
        self.assertEqual("ok", message)
        run_mock.assert_called_once()

    def test_build_continue_prompt_mentions_attempt_count(self) -> None:
        assignment = watch_assignments.WatchAssignment(
            target="formal-session:1.4",
            assignment_id="doc-1",
            bot_name="doc-bot",
            role="doc",
            title="文档同步与 CE 准备",
            goal="围绕 DOC-001、DOC-002、DOC-003 与 DOC-008 同步项目文档、验收材料并准备 CE 正式同步。",
            display_name="doc-bot / 文档同步与 CE 准备",
            status="ACTIVE",
            allow_intervene=True,
            task_text=None,
            continue_text=None,
            completion_regex=None,
            success_markers=(),
            blocked_markers=(),
        )
        runtime_state = watch_assignments.TargetRuntimeState(
            assignment_id="doc-1",
            continue_dispatch_count=2,
        )

        prompt = watch_assignments.build_continue_prompt(assignment, runtime_state, "❯")

        self.assertIn("这是第 3 次继续执行提醒", prompt)
        self.assertIn("当前停住位置参考: ❯", prompt)

    def test_visit_tmux_pane_to_continue_execution_selects_target(self) -> None:
        assignment = watch_assignments.WatchAssignment(
            target="formal-session:1.2",
            assignment_id="dev-2",
            bot_name="dev-bot",
            role="dev-b",
            title="主链回归收口",
            goal="",
            display_name="dev-bot / dev-b / 主链回归收口",
            status="ACTIVE",
            allow_intervene=True,
            task_text=None,
            continue_text=None,
            completion_regex=None,
            success_markers=(),
            blocked_markers=(),
        )
        commands: list[list[str]] = []

        original_run_tmux_command = watch_assignments.run_tmux_command
        try:
            watch_assignments.run_tmux_command = commands.append
            watch_assignments.visit_tmux_pane_to_continue_execution(assignment)
        finally:
            watch_assignments.run_tmux_command = original_run_tmux_command

        self.assertEqual(
            [["select-window", "-t", "formal-session:1.2"], ["select-pane", "-t", "formal-session:1.2"]],
            commands,
        )

    def test_tail_signature_is_stable_for_same_tail(self) -> None:
        self.assertEqual(
            watch_assignments.tail_signature("line1\nline2\nline3\nline4\nline5"),
            watch_assignments.tail_signature("line1\nline2\nline3\nline4\nline5"),
        )
        self.assertNotEqual(
            watch_assignments.tail_signature("line1\nline2\nline3\nline4\nline5"),
            watch_assignments.tail_signature("line1\nline2\nlineX\nline4\nline5"),
        )

    def test_merge_assignments_preserves_existing_entries_and_adds_new_panes(self) -> None:
        payload = {
            "task_id": "task-1",
            "panes": [
                {
                    "assignment_id": "dev-1",
                    "target": "formal-session:1.1",
                    "display_name": "dev-bot / OCR 主路径收口",
                    "status": "ACTIVE",
                }
            ],
        }
        panes = [
            {
                "session_name": "formal-session",
                "window_index": "1",
                "pane_index": "1",
                "target": "formal-session:1.1",
                "pane_title": "✳ Claude Code",
                "command": "node",
                "pane_dead": "0",
            },
            {
                "session_name": "formal-session",
                "window_index": "1",
                "pane_index": "2",
                "target": "formal-session:1.2",
                "pane_title": "✳ Claude Code",
                "command": "node",
                "pane_dead": "0",
            },
        ]

        merged = generate_lookme_assignments.merge_assignments(
            panes,
            payload,
            keep_missing=False,
        )

        self.assertEqual(2, len(merged["panes"]))
        self.assertEqual("dev-bot / OCR 主路径收口", merged["panes"][0]["display_name"])
        self.assertEqual("formal-session:1.2", merged["panes"][1]["target"])
        self.assertEqual("PENDING", merged["panes"][1]["status"])

    def test_merge_assignments_marks_missing_targets_removed_when_requested(self) -> None:
        payload = {
            "task_id": "task-1",
            "panes": [
                {
                    "assignment_id": "dev-1",
                    "target": "formal-session:1.1",
                    "status": "ACTIVE",
                },
                {
                    "assignment_id": "doc-1",
                    "target": "formal-session:1.4",
                    "status": "ACTIVE",
                },
            ],
        }
        panes = [
            {
                "session_name": "formal-session",
                "window_index": "1",
                "pane_index": "1",
                "target": "formal-session:1.1",
                "pane_title": "✳ Claude Code",
                "command": "node",
                "pane_dead": "0",
            }
        ]

        merged = generate_lookme_assignments.merge_assignments(
            panes,
            payload,
            keep_missing=True,
        )

        removed = next(item for item in merged["panes"] if item["target"] == "formal-session:1.4")
        self.assertEqual("REMOVED", removed["status"])

    def test_supervisor_build_child_command_passes_assignment_and_approval_flag(self) -> None:
        args = type(
            "Args",
            (),
            {
                "assignment_file": "/tmp/lookme.json",
                "auto_approve": False,
            },
        )()

        command = lookme_supervisor.build_child_command(args)

        self.assertEqual(sys.executable, command[0])
        self.assertEqual(str(ARTIFACTS_DIR / "lookme.py"), command[1])
        self.assertEqual("/tmp/lookme.json", command[3])
        self.assertEqual("--no-auto-approve", command[-1])

    def test_lookme_ctl_build_supervisor_command_includes_runtime_files(self) -> None:
        args = type(
            "Args",
            (),
            {
                "assignment_file": "/tmp/lookme.json",
                "runtime_log": "/tmp/runtime.log",
                "supervisor_log": "/tmp/supervisor.log",
                "lock_file": "/tmp/lookme.lock",
                "pid_file": "/tmp/lookme.pid",
                "child_pid_file": "/tmp/lookme-child.pid",
                "heartbeat_file": "/tmp/lookme-heartbeat.json",
                "restart_delay": 1.0,
                "heartbeat_interval": 5.0,
                "auto_approve": False,
            },
        )()

        command = lookme_ctl.build_supervisor_command(args)

        self.assertEqual(sys.executable, command[0])
        self.assertEqual(str(ARTIFACTS_DIR / "lookme_supervisor.py"), command[1])
        self.assertIn("--heartbeat-file", command)
        self.assertIn("/tmp/lookme-heartbeat.json", command)
        self.assertIn("--child-pid-file", command)
        self.assertIn("/tmp/lookme-child.pid", command)

    def test_lookme_ctl_reads_heartbeat_json(self) -> None:
        tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(tmpdir.cleanup)
        heartbeat_path = Path(tmpdir.name) / "heartbeat.json"
        heartbeat_path.write_text(
            json.dumps({"child_state": "running", "restart_count": 2}, ensure_ascii=False),
            encoding="utf-8",
        )

        payload = lookme_ctl.read_heartbeat(heartbeat_path)

        self.assertEqual("running", payload["child_state"])
        self.assertEqual(2, payload["restart_count"])

    def test_lookme_ctl_inspect_assignment_runtime_rejects_empty_active_set(self) -> None:
        path = self.write_assignment_file({"task_id": "idle", "panes": []})

        runtime = lookme_ctl.inspect_assignment_runtime(path)

        self.assertFalse(runtime["ready"])
        self.assertEqual(0, runtime["active_assignment_count"])
        self.assertIn("at least one active assignment", runtime["error"])

    def test_lookme_ctl_inspect_assignment_runtime_reports_placeholder_assignment(self) -> None:
        path = self.write_assignment_file(
            {
                "task_id": "task-1",
                "panes": [
                    {
                        "assignment_id": "pane-1-2",
                        "target": "formal-session:1.2",
                        "bot_name": "",
                        "role": "unassigned",
                        "title": "待分配任务 #1.2",
                        "goal": "等待为该 pane 指定真实任务。",
                        "display_name": "待分配任务 #1.2 / formal-session:1.2",
                        "status": "PENDING",
                    }
                ],
            }
        )

        runtime = lookme_ctl.inspect_assignment_runtime(path)

        self.assertFalse(runtime["ready"])
        self.assertEqual(1, runtime["active_assignment_count"])
        self.assertEqual("formal-session:1.2", runtime["unready_assignments"][0]["target"])
        self.assertIn("task allocation before startup", runtime["error"])

    def test_lookme_ctl_start_supervisor_blocks_when_assignment_is_not_ready(self) -> None:
        path = self.write_assignment_file({"task_id": "idle", "panes": []})
        args = type(
            "Args",
            (),
            {
                "assignment_file": path,
                "runtime_log": "/tmp/runtime.log",
                "supervisor_log": "/tmp/supervisor.log",
                "lock_file": "/tmp/lookme.lock",
                "pid_file": "/tmp/lookme.pid",
                "child_pid_file": "/tmp/lookme-child.pid",
                "heartbeat_file": "/tmp/lookme-heartbeat.json",
                "restart_delay": 1.0,
                "heartbeat_interval": 5.0,
                "auto_approve": False,
            },
        )()

        stderr = io.StringIO()
        with redirect_stderr(stderr), mock.patch("lookme_ctl.subprocess.Popen") as popen_mock:
            code = lookme_ctl.start_supervisor(args)

        self.assertEqual(1, code)
        self.assertIn("lookme start blocked", stderr.getvalue())
        popen_mock.assert_not_called()

    def test_lookme_ctl_status_reports_assignment_health_and_fails_when_unready(self) -> None:
        path = self.write_assignment_file({"task_id": "idle", "panes": []})
        tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(tmpdir.cleanup)
        pid_path = Path(tmpdir.name) / "lookme.pid"
        child_pid_path = Path(tmpdir.name) / "lookme-child.pid"
        heartbeat_path = Path(tmpdir.name) / "heartbeat.json"

        args = type(
            "Args",
            (),
            {
                "assignment_file": path,
                "pid_file": str(pid_path),
                "child_pid_file": str(child_pid_path),
                "heartbeat_file": str(heartbeat_path),
            },
        )()

        output = io.StringIO()
        with redirect_stdout(output):
            code = lookme_ctl.print_status(args)

        rendered = json.loads(output.getvalue())
        self.assertEqual(1, code)
        self.assertFalse(rendered["assignment"]["ready"])
        self.assertEqual(0, rendered["assignment"]["active_assignment_count"])

    def test_lookme_ctl_status_keeps_unready_assignment_details(self) -> None:
        path = self.write_assignment_file(
            {
                "task_id": "task-1",
                "panes": [
                    {
                        "assignment_id": "pane-1-2",
                        "target": "formal-session:1.2",
                        "bot_name": "",
                        "role": "unassigned",
                        "title": "待分配任务 #1.2",
                        "goal": "等待为该 pane 指定真实任务。",
                        "display_name": "待分配任务 #1.2 / formal-session:1.2",
                        "status": "PENDING",
                    }
                ],
            }
        )
        tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(tmpdir.cleanup)
        pid_path = Path(tmpdir.name) / "lookme.pid"
        child_pid_path = Path(tmpdir.name) / "lookme-child.pid"
        heartbeat_path = Path(tmpdir.name) / "heartbeat.json"

        args = type(
            "Args",
            (),
            {
                "assignment_file": path,
                "pid_file": str(pid_path),
                "child_pid_file": str(child_pid_path),
                "heartbeat_file": str(heartbeat_path),
            },
        )()

        output = io.StringIO()
        with redirect_stdout(output):
            code = lookme_ctl.print_status(args)

        rendered = json.loads(output.getvalue())
        self.assertEqual(1, code)
        self.assertFalse(rendered["assignment"]["ready"])
        self.assertEqual(1, rendered["assignment"]["active_assignment_count"])
        self.assertEqual("formal-session:1.2", rendered["assignment"]["unready_assignments"][0]["target"])


if __name__ == "__main__":
    unittest.main()
