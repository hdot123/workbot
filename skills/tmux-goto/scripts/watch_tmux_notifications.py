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


def run_tmux(*args: str) -> str:
    proc = subprocess.run(
        ["tmux", *args],
        check=True,
        capture_output=True,
        text=True,
    )
    return proc.stdout


def display_value(pane_id: str, fmt: str) -> str:
    return run_tmux("display-message", "-p", "-t", pane_id, fmt).strip()


def capture_output(pane_id: str, start: int) -> str:
    return run_tmux("capture-pane", "-p", "-S", str(start), "-t", pane_id).rstrip("\n")


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


def event_id_for(event: dict[str, object]) -> str:
    key = "|".join(
        [
            str(event.get("event", "")),
            str(event.get("session", "")),
            str(event.get("window", "")),
            str(event.get("pane_id", "")),
            str(event.get("signature", "")),
            str(event.get("detected_at", "")),
        ]
    )
    return hashlib.sha1(key.encode("utf-8")).hexdigest()[:16]


def build_event(pane_id: str, start: int, max_prompt_lines: int) -> dict[str, object] | None:
    recent_output = capture_output(pane_id, start)
    prompt = tail_block(recent_output, max_prompt_lines)
    if not looks_like_attention(prompt):
        return None
    event = {
        "event": "pane_attention",
        "detected_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "session": display_value(pane_id, "#{session_name}"),
        "window": display_value(pane_id, "#{window_index}"),
        "pane_id": pane_id,
        "pane_title": display_value(pane_id, "#{pane_title}"),
        "cwd": display_value(pane_id, "#{pane_current_path}"),
        "current_command": display_value(pane_id, "#{pane_current_command}"),
        "prompt": prompt,
        "prompt_headline": prompt_headline(prompt),
        "option_lines": option_lines(prompt),
        "recent_output": recent_output,
        "signature": signature_for(prompt or ""),
    }
    event["event_id"] = event_id_for(event)
    return event


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Watch tmux panes and emit attention notifications for tmux-goto."
    )
    parser.add_argument(
        "--pane-id",
        action="append",
        dest="pane_ids",
        required=True,
        help="tmux pane id, for example %%0. Repeat for multiple panes.",
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
        "--once",
        action="store_true",
        help="scan once and exit",
    )
    parser.add_argument(
        "--log-file",
        default="/tmp/tmux-goto-notifications.jsonl",
        help="jsonl file used to record newly detected notifications",
    )
    parser.add_argument(
        "--deliver",
        action="store_true",
        help="deliver each newly detected notification into the current Codex session",
    )
    parser.add_argument(
        "--delivery-script",
        default=str(Path(__file__).with_name("deliver_tmux_goto_notification.py")),
        help="delivery runner path, defaults to the local tmux-goto delivery script",
    )
    parser.add_argument(
        "--session-mode",
        choices=("fixed", "new"),
        default="fixed",
        help="Codex session mode used by the delivery runner, defaults to fixed",
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


def deliver_event(
    event: dict[str, object],
    *,
    delivery_script: str,
    session_mode: str,
    dry_run: bool,
) -> None:
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
        sys.stderr.write(proc.stderr or proc.stdout or "tmux-goto delivery failed\n")
        if not (proc.stderr or proc.stdout):
            sys.stderr.write("\n")
        return
    if proc.stdout.strip():
        sys.stderr.write(proc.stdout)
        if not proc.stdout.endswith("\n"):
            sys.stderr.write("\n")


def main() -> int:
    args = parse_args()
    seen: dict[str, str] = {}
    while True:
        for pane_id in args.pane_ids:
            try:
                event = build_event(pane_id, args.start, args.max_prompt_lines)
            except subprocess.CalledProcessError as exc:
                sys.stderr.write(exc.stderr or exc.stdout or str(exc))
                sys.stderr.write("\n")
                continue
            if not event:
                continue
            signature = str(event["signature"])
            if seen.get(pane_id) == signature:
                continue
            seen[pane_id] = signature
            record_event(args.log_file, event)
            emit(event)
            if args.deliver:
                deliver_event(
                    event,
                    delivery_script=args.delivery_script,
                    session_mode=args.session_mode,
                    dry_run=args.deliver_dry_run,
                )
        if args.once:
            return 0
        time.sleep(args.interval)


if __name__ == "__main__":
    raise SystemExit(main())
