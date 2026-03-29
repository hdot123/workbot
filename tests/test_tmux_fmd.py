#!/usr/bin/env python3
"""测试 tmux-skills 内部 legacy FMD 三分类逻辑"""

import sys

try:
    import pytest
except ModuleNotFoundError:  # pragma: no cover - optional dependency for direct script runs
    class _PytestStub:
        def raises(self, *_args, **_kwargs):
            raise RuntimeError("pytest is required for pytest-only assertions")

    pytest = _PytestStub()

sys.path.insert(0, '/Users/busiji/workbot/skills/tmux-skills/scripts')

from legacy_tmux_fmd_compat import (
    PaneState,
    DispatchAction,
    append_event_log,
    build_dispatch_message,
    classify_stop_reason,
    format_output,
    get_dispatch_action,
    resolve_codex_thread_id,
    StopReason,
)


def test_case(name: str, output: str, expected: StopReason):
    """测试单个用例"""
    actual, details = classify_stop_reason(output)
    status = "✓" if actual == expected else "✗"
    print(f"{status} {name}")
    if actual != expected:
        print(f"  期望：{expected.value}")
        print(f"  实际：{actual.value}")
        print(f"  匹配：{details.get('matched_patterns', [])}")
    return actual == expected


def main():
    print("=" * 60)
    print("tmux FMD 三分类逻辑测试")
    print("=" * 60)
    print()

    passed = 0
    total = 0

    # 任务完成测试
    total += 1
    if test_case(
        "任务完成 - 正常成功",
        "All tests passed\nDone\n✓ 3 tests completed",
        StopReason.TASK_COMPLETE
    ):
        passed += 1

    total += 1
    if test_case(
        "任务完成 - success 关键词",
        "Build completed successfully\nSUCCESS",
        StopReason.TASK_COMPLETE
    ):
        passed += 1

    total += 1
    if test_case(
        "任务完成 - finished 关键词",
        "Task finished\nAll done",
        StopReason.TASK_COMPLETE
    ):
        passed += 1

    # SOP 审批测试
    total += 1
    if test_case(
        "SOP 审批 - requires approval",
        "This command requires approval\n1. Yes\n2. No",
        StopReason.SOP_APPROVAL
    ):
        passed += 1

    total += 1
    if test_case(
        "SOP 审批 - do you want to proceed",
        "Do you want to proceed?\n1. Continue\n2. Cancel",
        StopReason.SOP_APPROVAL
    ):
        passed += 1

    total += 1
    if test_case(
        "SOP 审批 - esc to cancel",
        "Press 1 to confirm, 2 to amend, ESC to cancel",
        StopReason.SOP_APPROVAL
    ):
        passed += 1

    # 故障测试
    total += 1
    if test_case(
        "故障 - error",
        "Error: Cannot find module 'foo'\nFailed to start",
        StopReason.FAULT
    ):
        passed += 1

    total += 1
    if test_case(
        "故障 - traceback",
        "Traceback (most recent call last):\n  File 'test.py', line 10",
        StopReason.FAULT
    ):
        passed += 1

    total += 1
    if test_case(
        "故障 - permission denied",
        "Permission denied: cannot access /etc/config",
        StopReason.FAULT
    ):
        passed += 1

    total += 1
    if test_case(
        "故障 - command not found",
        "Command not found: 'node'\nInstall it with npm",
        StopReason.FAULT
    ):
        passed += 1

    # 混合情况测试
    total += 1
    if test_case(
        "混合 - 故障优先于 SOP",
        "Error: something failed\nDo you want to proceed?",
        StopReason.FAULT
    ):
        passed += 1

    total += 1
    if test_case(
        "混合 - 故障优先于完成",
        "Done\nError: but something failed",
        StopReason.FAULT
    ):
        passed += 1

    # 仍在运行测试
    total += 1
    if test_case(
        "仍在运行 - 无关键词",
        "Processing data...\nLoading modules...\nWaiting for input",
        StopReason.STILL_RUNNING
    ):
        passed += 1

    total += 1
    if test_case(
        "仍在运行 - 空输出",
        "",
        StopReason.STILL_RUNNING
    ):
        passed += 1

    total += 1
    if test_case(
        "SOP 审批 - 底部空行与 prompt 不应遮住审批框",
        "This command requires approval\n1. Yes\n2. No\nbusiji@mac workbot %\n\n\n\n",
        StopReason.SOP_APPROVAL
    ):
        passed += 1

    total += 1
    try:
        test_dispatch_action_mapping()
        print("✓ Dispatch 动作映射")
        passed += 1
    except AssertionError as exc:
        print(f"✗ Dispatch 动作映射: {exc}")

    total += 1
    try:
        test_format_output_reflects_target_and_reason()
        print("✓ 输出文案包含目标与审批状态")
        passed += 1
    except AssertionError as exc:
        print(f"✗ 输出文案包含目标与审批状态: {exc}")

    total += 1
    try:
        test_build_dispatch_message_by_action()
        print("✓ Dispatch 文案按动作分流")
        passed += 1
    except AssertionError as exc:
        print(f"✗ Dispatch 文案按动作分流: {exc}")

    print()
    print("=" * 60)
    print(f"测试结果：{passed}/{total} 通过")
    print("=" * 60)

    return 0 if passed == total else 1

def test_resolve_thread_id_env_set(monkeypatch):
    monkeypatch.delenv("CODEX_THREAD_ID", raising=False)
    monkeypatch.setenv("CODEX_THREAD_ID", "deadbeef")
    assert resolve_codex_thread_id() == "deadbeef"

def test_resolve_thread_id_missing(monkeypatch):
    monkeypatch.delenv("CODEX_THREAD_ID", raising=False)
    with pytest.raises(RuntimeError, match="CODEX_THREAD_ID is required"):
        resolve_codex_thread_id()

def test_notify_logging_includes_thread(monkeypatch, tmp_path):
    tmp_file = tmp_path / "events.jsonl"
    monkeypatch.setenv("CODEX_THREAD_ID", "deadbeef")
    monkeypatch.setenv("EVENT_LOG_FILE", str(tmp_file))
    state = PaneState(
        pane_id="%0",
        target="formal-session:2.1",
        session="formal-session",
        window="2",
        pane_index="1",
        pane_title="dev-bot",
        current_command="claude",
        current_path="/Users/busiji/workbot",
        recent_output="This command requires approval",
        pane_dead=0,
        is_stopped=True,
        stop_reason=StopReason.SOP_APPROVAL,
        dispatch_action=DispatchAction.HANDLE_SOP,
        confidence=0.9,
        details={},
    )
    append_event_log(state.target, "deadbeef", state)
    lines = tmp_file.read_text().splitlines()
    assert '"thread_id": "deadbeef"' in lines[-1]

def test_dispatch_action_mapping() -> None:
    mapping = {
        StopReason.TASK_COMPLETE: DispatchAction.ASSIGN_NEXT_TASK,
        StopReason.SOP_APPROVAL: DispatchAction.HANDLE_SOP,
        StopReason.FAULT: DispatchAction.TROUBLESHOOT,
        StopReason.STILL_RUNNING: DispatchAction.CONTINUE_MONITORING,
    }
    for reason, expected in mapping.items():
        assert get_dispatch_action(reason) == expected


def test_format_output_reflects_target_and_reason() -> None:
    state = PaneState(
        pane_id="%0",
        target="formal-session:1.1",
        session="formal-session",
        window="1",
        pane_index="1",
        pane_title="dev-bot",
        current_command="claude",
        current_path="/Users/busiji/workbot",
        recent_output="This command requires approval",
        pane_dead=0,
        is_stopped=True,
        stop_reason=StopReason.SOP_APPROVAL,
        dispatch_action=DispatchAction.HANDLE_SOP,
        confidence=0.9,
        details={"matched_patterns": ["sop"], "active_block": ""},
    )
    formatted = format_output([state])
    assert "dev-bot 呼叫：" in formatted
    assert "formal-session:1.1" in formatted
    assert "审批 SOP 状态" in formatted


def test_build_dispatch_message_by_action() -> None:
    base = dict(
        pane_id="%0",
        target="formal-session:1.1",
        session="formal-session",
        window="1",
        pane_index="1",
        pane_title="dev-bot",
        current_command="claude",
        current_path="/Users/busiji/workbot",
        recent_output="",
        pane_dead=0,
        is_stopped=True,
        confidence=0.9,
        details={},
    )

    sop_state = PaneState(
        **base,
        stop_reason=StopReason.SOP_APPROVAL,
        dispatch_action=DispatchAction.HANDLE_SOP,
    )
    done_state = PaneState(
        **base,
        stop_reason=StopReason.TASK_COMPLETE,
        dispatch_action=DispatchAction.ASSIGN_NEXT_TASK,
    )
    fault_state = PaneState(
        **base,
        stop_reason=StopReason.FAULT,
        dispatch_action=DispatchAction.TROUBLESHOOT,
    )

    assert build_dispatch_message(sop_state) == "dev-bot 呼叫：去 tmux formal-session:1.1 窗口审批 SOP 状态"
    assert build_dispatch_message(done_state) == "dev-bot 呼叫：去 tmux formal-session:1.1 窗口任务完成 SOP 状态"
    assert build_dispatch_message(fault_state) == "dev-bot 呼叫：去 tmux formal-session:1.1 窗口恢复 SOP 状态"


if __name__ == "__main__":
    raise SystemExit(main())
