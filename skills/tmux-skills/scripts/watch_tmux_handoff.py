#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from runtime_ledger import CURRENT_RUNTIME_LEDGER_PATH


PROMPT_PATTERNS = (
    re.compile(r"do you want to", re.IGNORECASE),
    re.compile(r"\bselect\b", re.IGNORECASE),
    re.compile(r"\bchoose\b", re.IGNORECASE),
    re.compile(r"\bproceed\b", re.IGNORECASE),
    re.compile(r"\by/n\b", re.IGNORECASE),
    re.compile(r"^\s*❯?\s*1\.", re.IGNORECASE),
    re.compile(r"^\s*1\.\s+\S+"),
)

OPTION_PATTERN = re.compile(r"^\s*❯?\s*\d+\.\s+")
SEPARATOR_PATTERN = re.compile(r"^[╌─-]{8,}$")
DEFAULT_PROACTIVE_INTERVAL = 30.0


def run_tmux(*args: str) -> str:
    proc = subprocess.run(
        ["tmux", *args],
        check=True,
        capture_output=True,
        text=True,
    )
    return proc.stdout


def display_value(target: str, fmt: str) -> str:
    return run_tmux("display-message", "-p", "-t", target, fmt).strip()


def capture_output(target: str, start: int) -> str:
    return run_tmux("capture-pane", "-p", "-S", str(start), "-t", target).rstrip("\n")


def resolve_target_from_pane_id(pane_id: str) -> str:
    return display_value(pane_id, "#{session_name}:#{window_index}.#{pane_index}")


def tail_block(text: str, max_lines: int) -> str | None:
    lines = [line.rstrip() for line in text.splitlines()]
    while lines and not lines[-1].strip():
        lines.pop()
    if not lines:
        return None
    block = lines[-max_lines:]
    while block and not block[0].strip():
        block.pop(0)
    return "\n".join(block) if block else None


def looks_like_attention(prompt: str | None) -> bool:
    if not prompt:
        return False
    lines = prompt.splitlines()
    numbered = sum(1 for line in lines if re.match(r"^\s*❯?\s*\d+\.", line))
    if numbered >= 2:
        return True
    return any(pattern.search(prompt) for pattern in PROMPT_PATTERNS)


def prompt_headline(prompt: str | None) -> str | None:
    if not prompt:
        return None
    lines = [line.strip() for line in prompt.splitlines() if line.strip()]
    for line in lines:
        lowered = line.lower()
        if "?" in line or any(pattern.search(line) for pattern in PROMPT_PATTERNS):
            if OPTION_PATTERN.match(line):
                continue
            if lowered.startswith("esc to cancel"):
                continue
            return line
    for line in lines:
        stripped = line.strip()
        if OPTION_PATTERN.match(stripped):
            continue
        if SEPARATOR_PATTERN.match(stripped):
            continue
        if stripped.startswith(("+++", "---", "@@", "⏺", "❯")):
            continue
        if stripped.lower().startswith("esc to cancel"):
            continue
        return stripped
    return None


def option_lines(prompt: str | None) -> list[str]:
    if not prompt:
        return []
    return [line.strip() for line in prompt.splitlines() if OPTION_PATTERN.match(line.strip())]


def signature_for(prompt: str) -> str:
    return hashlib.sha1(prompt.encode("utf-8")).hexdigest()[:12]


def state_signature_for(*parts: str) -> str:
    return hashlib.sha1("|".join(parts).encode("utf-8")).hexdigest()[:12]


def event_id_for(event: dict[str, object]) -> str:
    key = "|".join(
        [
            str(event.get("event", "")),
            str(event.get("target", "")),
            str(event.get("signature", "")),
            str(event.get("detected_at", "")),
        ]
    )
    return hashlib.sha1(key.encode("utf-8")).hexdigest()[:16]


def capture_snapshot(target: str, start: int, max_prompt_lines: int) -> dict[str, object]:
    recent_output = capture_output(target, start)
    prompt = tail_block(recent_output, max_prompt_lines)
    pane_title = display_value(target, "#{pane_title}")
    cwd = display_value(target, "#{pane_current_path}")
    current_command = display_value(target, "#{pane_current_command}")
    session_attached = display_value(target, "#{session_attached}")
    session_name = display_value(target, "#{session_name}")
    window_index = display_value(target, "#{window_index}")
    pane_index = display_value(target, "#{pane_index}")
    pane_id = display_value(target, "#{pane_id}")
    return {
        "target": target,
        "session": session_name,
        "window": window_index,
        "pane_index": pane_index,
        "pane_id": pane_id,
        "pane_title": pane_title,
        "cwd": cwd,
        "current_command": current_command,
        "session_attached": int(session_attached or 0),
        "prompt": prompt,
        "prompt_headline": prompt_headline(prompt),
        "option_lines": option_lines(prompt),
        "recent_output": recent_output,
        "reachable": True,
        "state_signature": state_signature_for(
            target,
            pane_title,
            cwd,
            current_command,
            tail_block(recent_output, max_prompt_lines) or "",
        ),
    }


def build_attention_event(snapshot: dict[str, object]) -> dict[str, object] | None:
    prompt = snapshot.get("prompt")
    if not looks_like_attention(prompt if isinstance(prompt, str) else None):
        return None
    event = {
        "event": "pane_attention",
        "state_class": "sop_approval",
        "state_label": "审批",
        "deliverable": True,
        "detected_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        **snapshot,
        "signature": signature_for(str(prompt or "")),
        "source": "tmux-skills",
    }
    event["event_id"] = event_id_for(event)
    return event


def build_proactive_event(
    snapshot: dict[str, object],
    *,
    proactive_interval: float,
) -> dict[str, object]:
    prompt = f"主动巡检：pane 状态已连续 {int(proactive_interval)} 秒未变化，请查看现场。"
    event = {
        "event": "pane_checkin",
        "state_class": "pane_checkin",
        "state_label": "巡检",
        "deliverable": True,
        "detected_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        **snapshot,
        "prompt": prompt,
        "prompt_headline": prompt,
        "option_lines": [],
        "signature": signature_for(f"{snapshot['state_signature']}|pane_checkin"),
        "source": "tmux-skills",
    }
    event["event_id"] = event_id_for(event)
    return event


def build_runtime_blocked_event(
    target: str,
    *,
    reason: str,
    cached_snapshot: dict[str, object] | None = None,
) -> dict[str, object]:
    cached_snapshot = cached_snapshot or {}
    session_name = str(cached_snapshot.get("session", "")).strip()
    window = str(cached_snapshot.get("window", "")).strip()
    pane_title = str(cached_snapshot.get("pane_title", "")).strip()
    event = {
        "event": "runtime_blocked",
        "state_class": "runtime_blocked",
        "state_label": "恢复",
        "deliverable": False,
        "detected_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "target": target,
        "session": session_name or target.partition(":")[0],
        "window": window or target.partition(":")[2].partition(".")[0],
        "pane_title": pane_title,
        "current_command": str(cached_snapshot.get("current_command", "")).strip(),
        "reachable": False,
        "prompt": reason,
        "prompt_headline": reason,
        "option_lines": [],
        "recent_output": str(cached_snapshot.get("recent_output", "")).strip(),
        "signature": signature_for(f"{target}|{reason}"),
        "source": "tmux-skills",
    }
    event["event_id"] = event_id_for(event)
    return event


def reset_attention_tracking_for_state_change(
    pane_id: str,
    state_signature: str,
    *,
    seen_attention: dict[str, str],
    attention_signature: dict[str, str],
    attention_active: dict[str, bool],
) -> None:
    cached_signature = attention_signature.get(pane_id)
    if cached_signature and cached_signature != state_signature:
        attention_signature.pop(pane_id, None)
        seen_attention.pop(pane_id, None)
        attention_active[pane_id] = False


def should_emit_attention_event(
    pane_id: str,
    event: dict[str, object],
    state_signature: str,
    *,
    seen_attention: dict[str, str],
    attention_signature: dict[str, str],
    attention_active: dict[str, bool],
) -> bool:
    signature = str(event["signature"])
    if attention_active.get(pane_id) and seen_attention.get(pane_id) == signature:
        return False
    seen_attention[pane_id] = signature
    attention_signature[pane_id] = state_signature
    attention_active[pane_id] = True
    return True


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Watch tmux panes and emit tmux-skills handoff notifications."
    )
    parser.add_argument(
        "--target",
        action="append",
        dest="targets",
        default=[],
        help="tmux target, for example formal-session:1.1. Repeat for multiple panes.",
    )
    parser.add_argument(
        "--pane-id",
        action="append",
        dest="pane_ids",
        default=[],
        help="Deprecated compatibility input. Converted to target immediately.",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=0.8,
        help="polling interval in seconds, defaults to 0.8",
    )
    parser.add_argument(
        "--start",
        type=int,
        default=-120,
        help="capture-pane start offset, defaults to -120",
    )
    parser.add_argument(
        "--max-prompt-lines",
        type=int,
        default=10,
        help="maximum lines kept in the prompt summary block",
    )
    parser.add_argument(
        "--proactive-interval",
        type=float,
        default=DEFAULT_PROACTIVE_INTERVAL,
        help="seconds before an unchanged pane triggers a proactive check-in, defaults to 30",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="scan once and exit",
    )
    parser.add_argument(
        "--log-file",
        default="/Users/busiji/workbot/workspace/artifacts/tmux-skills/handoff-notifications.jsonl",
        help="jsonl file used to record newly detected notifications",
    )
    parser.add_argument(
        "--deliver",
        action="store_true",
        help="deliver each newly detected notification into the current Codex session",
    )
    parser.add_argument(
        "--delivery-script",
        default=str(Path(__file__).with_name("deliver_tmux_handoff_notification.py")),
        help="delivery runner path, defaults to the local tmux-skills handoff delivery script",
    )
    parser.add_argument(
        "--session-mode",
        choices=("fixed", "new"),
        default="fixed",
        help="Codex session mode used by the handoff delivery runner, defaults to fixed",
    )
    parser.add_argument(
        "--deliver-dry-run",
        action="store_true",
        help="run the delivery runner in dry-run mode",
    )
    return parser.parse_args()


def emit(event: dict[str, object]) -> None:
    json.dump(event, sys.stdout, ensure_ascii=False)
    sys.stdout.write("\n")
    sys.stdout.flush()


def record_event(log_file: str, event: dict[str, object]) -> None:
    path = Path(log_file)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        json.dump(event, fh, ensure_ascii=False)
        fh.write("\n")


def clear_runtime_ledger() -> None:
    try:
        CURRENT_RUNTIME_LEDGER_PATH.unlink()
    except FileNotFoundError:
        return


def deliver_event(
    event: dict[str, object],
    *,
    delivery_script: str,
    session_mode: str,
    dry_run: bool,
) -> None:
    if not bool(event.get("deliverable")):
        return
    cmd = [
        sys.executable,
        delivery_script,
        "--session-mode",
        session_mode,
    ]
    if dry_run:
        cmd.append("--dry-run")
    proc = subprocess.run(
        cmd,
        input=json.dumps(event, ensure_ascii=False),
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        sys.stderr.write(proc.stderr or proc.stdout or "tmux-skills handoff delivery failed\n")
        if not (proc.stderr or proc.stdout):
            sys.stderr.write("\n")
        return
    if proc.stdout.strip():
        sys.stderr.write(proc.stdout)
        if not proc.stdout.endswith("\n"):
            sys.stderr.write("\n")


def normalize_targets(args: argparse.Namespace) -> list[str]:
    targets = [str(target).strip() for target in args.targets if str(target).strip()]
    for pane_id in args.pane_ids:
        pane_id = str(pane_id).strip()
        if not pane_id:
            continue
        targets.append(resolve_target_from_pane_id(pane_id))
    targets = [target for target in targets if target]
    return sorted(dict.fromkeys(targets))


def main() -> int:
    args = parse_args()
    watched_targets = normalize_targets(args)
    if not watched_targets:
        raise SystemExit("at least one --target is required")

    seen_attention: dict[str, str] = {}
    attention_signature: dict[str, str] = {}
    attention_active: dict[str, bool] = {}
    last_state: dict[str, str] = {}
    last_state_change: dict[str, float] = {}
    last_proactive_emit: dict[str, float] = {}
    last_runtime_blocked: dict[str, str] = {}
    cached_snapshots: dict[str, dict[str, object]] = {}

    while True:
        unavailable_targets = 0
        detached_targets = 0
        for target in watched_targets:
            try:
                snapshot = capture_snapshot(target, args.start, args.max_prompt_lines)
                cached_snapshots[target] = snapshot
                last_runtime_blocked.pop(target, None)
            except (subprocess.CalledProcessError, RuntimeError) as exc:
                unavailable_targets += 1
                reason = "target 不可达，进入 runtime 恢复分支"
                signature = f"runtime_blocked:{reason}"
                if last_runtime_blocked.get(target) != signature:
                    blocked_event = build_runtime_blocked_event(
                        target,
                        reason=reason,
                        cached_snapshot=cached_snapshots.get(target),
                    )
                    record_event(args.log_file, blocked_event)
                    emit(blocked_event)
                    last_runtime_blocked[target] = signature
                continue

            if int(snapshot.get("session_attached", 0)) <= 0:
                detached_targets += 1
                reason = "formal session 已脱离前台，进入 runtime 恢复分支"
                signature = f"runtime_blocked:{reason}"
                if last_runtime_blocked.get(target) != signature:
                    blocked_event = build_runtime_blocked_event(
                        target,
                        reason=reason,
                        cached_snapshot=snapshot,
                    )
                    record_event(args.log_file, blocked_event)
                    emit(blocked_event)
                    last_runtime_blocked[target] = signature
                continue

            now = time.monotonic()
            state_signature = str(snapshot["state_signature"])
            reset_attention_tracking_for_state_change(
                target,
                state_signature,
                seen_attention=seen_attention,
                attention_signature=attention_signature,
                attention_active=attention_active,
            )
            if last_state.get(target) != state_signature:
                last_state[target] = state_signature
                last_state_change[target] = now
                last_proactive_emit[target] = 0.0
            event = build_attention_event(snapshot)
            if event:
                if not should_emit_attention_event(
                    target,
                    event,
                    state_signature,
                    seen_attention=seen_attention,
                    attention_signature=attention_signature,
                    attention_active=attention_active,
                ):
                    continue
                last_proactive_emit[target] = now
                record_event(args.log_file, event)
                emit(event)
                if args.deliver:
                    deliver_event(
                        event,
                        delivery_script=args.delivery_script,
                        session_mode=args.session_mode,
                        dry_run=args.deliver_dry_run,
                    )
                continue
            if attention_active.get(target):
                attention_active[target] = False
                seen_attention.pop(target, None)
            proactive_interval = max(0.0, float(args.proactive_interval))
            if proactive_interval <= 0:
                continue
            state_age = now - last_state_change.get(target, now)
            since_last_emit = now - last_proactive_emit.get(target, 0.0)
            if state_age < proactive_interval or since_last_emit < proactive_interval:
                continue
            proactive_event = build_proactive_event(
                snapshot,
                proactive_interval=proactive_interval,
            )
            last_proactive_emit[target] = now
            record_event(args.log_file, proactive_event)
            emit(proactive_event)
            if args.deliver:
                deliver_event(
                    proactive_event,
                    delivery_script=args.delivery_script,
                    session_mode=args.session_mode,
                    dry_run=args.deliver_dry_run,
                )
        if detached_targets >= len(watched_targets):
            clear_runtime_ledger()
            sys.stderr.write("formal session is detached; watcher exiting\n")
            return 0
        if unavailable_targets >= len(watched_targets):
            clear_runtime_ledger()
            sys.stderr.write("all watched targets are unavailable; watcher exiting\n")
            return 0
        if args.once:
            return 0
        time.sleep(args.interval)


if __name__ == "__main__":
    raise SystemExit(main())
