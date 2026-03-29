#!/usr/bin/env python3
"""Legacy pure-Python compatibility surface for tmux-fmd tests and callers."""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path

STOP_QUEUE_FILE = "/tmp/tmux-fmd-queue.json"
EVENT_LOG_FILE = "/Users/busiji/workbot/workspace/artifacts/tmux-fmd/events.jsonl"


class StopReason(Enum):
    TASK_COMPLETE = "task_complete"
    SOP_APPROVAL = "sop_approval"
    FAULT = "fault"
    STILL_RUNNING = "still_running"


class DispatchAction(Enum):
    ASSIGN_NEXT_TASK = "assign_next_task"
    HANDLE_SOP = "handle_sop"
    TROUBLESHOOT = "troubleshoot"
    CONTINUE_MONITORING = "continue_monitoring"


SOP_PATTERNS = [
    re.compile(r"this command requires approval", re.IGNORECASE),
    re.compile(r"do you want to proceed\?", re.IGNORECASE),
    re.compile(r"do you want to", re.IGNORECASE),
    re.compile(r"proceed\?", re.IGNORECASE),
    re.compile(r"confirm.*action", re.IGNORECASE),
    re.compile(r"esc to cancel", re.IGNORECASE),
    re.compile(r"tab to amend", re.IGNORECASE),
    re.compile(r"ctrl\+e to explain", re.IGNORECASE),
    re.compile(r"select an option", re.IGNORECASE),
    re.compile(r"choose.*\?", re.IGNORECASE),
    re.compile(r"approve\?", re.IGNORECASE),
    re.compile(r"y/n", re.IGNORECASE),
]

FAULT_PATTERNS = [
    re.compile(r"\berror\b", re.IGNORECASE),
    re.compile(r"\bfailed\b", re.IGNORECASE),
    re.compile(r"\bexception\b", re.IGNORECASE),
    re.compile(r"\btraceback\b", re.IGNORECASE),
    re.compile(r"\bpermission denied\b", re.IGNORECASE),
    re.compile(r"\bcommand not found\b", re.IGNORECASE),
    re.compile(r"\bfatal\b", re.IGNORECASE),
    re.compile(r"\bcrash\b", re.IGNORECASE),
    re.compile(r"\bpanic\b", re.IGNORECASE),
]

COMPLETE_PATTERNS = [
    re.compile(r"\bcompleted\b", re.IGNORECASE),
    re.compile(r"\bdone\b", re.IGNORECASE),
    re.compile(r"\bfinished\b", re.IGNORECASE),
    re.compile(r"\bsuccess\b", re.IGNORECASE),
    re.compile(r"\bpassed\b", re.IGNORECASE),
    re.compile(r"^\s*✓", re.MULTILINE),
    re.compile(r"^\s*✔", re.MULTILINE),
    re.compile(r"^\s*✅", re.MULTILINE),
    re.compile(r"all tests passed", re.IGNORECASE),
    re.compile(r"no change detected", re.IGNORECASE),
    re.compile(r"task completed", re.IGNORECASE),
]


@dataclass
class PaneState:
    pane_id: str
    target: str
    session: str
    window: str
    pane_index: str
    pane_title: str
    current_command: str
    current_path: str
    recent_output: str
    pane_dead: int = 0
    is_stopped: bool = False
    stop_reason: StopReason = StopReason.STILL_RUNNING
    dispatch_action: DispatchAction = DispatchAction.CONTINUE_MONITORING
    confidence: float = 0.0
    details: dict = field(default_factory=dict)


def extract_active_block(output: str, lines: int = 20) -> str:
    all_lines = output.splitlines()
    while all_lines and not all_lines[-1].strip():
        all_lines.pop()
    recent_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines
    return "\n".join(recent_lines)


def classify_stop_reason(output: str) -> tuple[StopReason, dict]:
    active_block = extract_active_block(output, lines=20)
    details = {
        "matched_patterns": [],
        "confidence_factors": [],
        "active_block": active_block,
    }

    for pattern in SOP_PATTERNS:
        match = pattern.search(active_block)
        if match:
            details["matched_patterns"].append(f"sop:{match.group()}")
            details["confidence_factors"].append(("sop_pattern", 0.9))

    fault_count = 0
    for pattern in FAULT_PATTERNS:
        match = pattern.search(active_block)
        if match:
            fault_count += 1
            details["matched_patterns"].append(f"fault:{match.group()}")

    complete_count = 0
    for pattern in COMPLETE_PATTERNS:
        match = pattern.search(active_block)
        if match:
            complete_count += 1
            details["matched_patterns"].append(f"complete:{match.group()}")

    if fault_count > 0:
        details["confidence_factors"].append(("fault_detected", 0.8 + min(fault_count * 0.05, 0.2)))
        return StopReason.FAULT, details

    if details["matched_patterns"]:
        has_sop = any(pattern.startswith("sop:") for pattern in details["matched_patterns"])
        if has_sop:
            details["confidence_factors"].append(("sop_confirmed", 0.85))
            return StopReason.SOP_APPROVAL, details
        has_complete = any(pattern.startswith("complete:") for pattern in details["matched_patterns"])
        if has_complete:
            details["confidence_factors"].append(
                ("complete_confirmed", 0.8 + min(complete_count * 0.05, 0.2))
            )
            return StopReason.TASK_COMPLETE, details

    return StopReason.STILL_RUNNING, details


def compute_confidence(reason: StopReason, details: dict) -> float:
    if not details.get("confidence_factors"):
        return 0.5
    confidence = 0.0
    for _, value in details.get("confidence_factors", []):
        confidence = max(confidence, value)
    return round(confidence, 2)


def get_dispatch_action(reason: StopReason) -> DispatchAction:
    mapping = {
        StopReason.TASK_COMPLETE: DispatchAction.ASSIGN_NEXT_TASK,
        StopReason.SOP_APPROVAL: DispatchAction.HANDLE_SOP,
        StopReason.FAULT: DispatchAction.TROUBLESHOOT,
        StopReason.STILL_RUNNING: DispatchAction.CONTINUE_MONITORING,
    }
    return mapping[reason]


def build_dispatch_message(state: PaneState) -> str:
    pane_title = state.pane_title or "未知 pane"
    if state.dispatch_action == DispatchAction.HANDLE_SOP:
        return f"{pane_title} 呼叫：去 tmux {state.target} 窗口审批 SOP 状态"
    if state.dispatch_action == DispatchAction.ASSIGN_NEXT_TASK:
        return f"{pane_title} 呼叫：去 tmux {state.target} 窗口任务完成 SOP 状态"
    if state.dispatch_action == DispatchAction.TROUBLESHOOT:
        return f"{pane_title} 呼叫：去 tmux {state.target} 窗口恢复 SOP 状态"
    return f"{pane_title} 呼叫：去 tmux {state.target} 窗口巡检 SOP 状态"


def resolve_codex_thread_id() -> str:
    thread_id = os.environ.get("CODEX_THREAD_ID", "").strip()
    if not thread_id:
        raise RuntimeError("CODEX_THREAD_ID is required")
    return thread_id


def append_event_log(target: str, thread_id: str, state: PaneState) -> None:
    path = Path(EVENT_LOG_FILE)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(
            json.dumps(
                {
                    "timestamp": datetime.now().isoformat(),
                    "target": target,
                    "thread_id": thread_id,
                    "stop_reason": state.stop_reason.value,
                    "dispatch_action": state.dispatch_action.value,
                    "message": build_dispatch_message(state),
                },
                ensure_ascii=False,
            )
            + "\n"
        )


def format_output(states: list[PaneState], output_format: str = "text") -> str:
    if output_format == "json":
        result = []
        for state in states:
            result.append(
                {
                    "pane_id": state.pane_id,
                    "target": state.target,
                    "stop_reason": state.stop_reason.value,
                    "dispatch_action": state.dispatch_action.value,
                    "message": build_dispatch_message(state),
                }
            )
        return json.dumps(result, ensure_ascii=False, indent=2)

    if not states:
        return "TMUX_FMD_OK"
    return "\n".join(build_dispatch_message(state) for state in states)
