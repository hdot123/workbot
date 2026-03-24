#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import subprocess
import sys
from typing import Optional

from notification_record import event_id_for

PROMPT_PATTERNS = (
    re.compile(r"do you want to", re.IGNORECASE),
    re.compile(r"\bselect\b", re.IGNORECASE),
    re.compile(r"\bchoose\b", re.IGNORECASE),
    re.compile(r"\bproceed\b", re.IGNORECASE),
    re.compile(r"\by/n\b", re.IGNORECASE),
    re.compile(r"^\s*❯?\s*\d+\.", re.IGNORECASE),
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


def infer_prompt_block(text: str, max_lines: int) -> Optional[str]:
    lines = [line.rstrip() for line in text.splitlines()]
    while lines and not lines[-1].strip():
        lines.pop()
    if not lines:
        return None
    block = lines[-max_lines:]
    while block and not block[0].strip():
        block.pop(0)
    return "\n".join(block) if block else None


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


def build_payload(pane_id: str, start: int, max_prompt_lines: int) -> dict[str, object]:
    recent_output = capture_output(pane_id, start)
    prompt = infer_prompt_block(recent_output, max_prompt_lines)
    return {
        "event": "pane_snapshot",
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
    } | {"event_id": event_id_for({
        "event": "pane_snapshot",
        "detected_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "session": display_value(pane_id, "#{session_name}"),
        "window": display_value(pane_id, "#{window_index}"),
        "pane_id": pane_id,
        "signature": signature_for(prompt or ""),
    })}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a tmux pane notification payload for tmux-goto."
    )
    parser.add_argument("--pane-id", required=True, help="tmux pane id, for example %%0")
    parser.add_argument(
        "--start",
        type=int,
        default=-120,
        help="capture-pane start offset, defaults to -120",
    )
    parser.add_argument(
        "--max-prompt-lines",
        type=int,
        default=8,
        help="maximum lines kept in the prompt summary block",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        payload = build_payload(args.pane_id, args.start, args.max_prompt_lines)
    except subprocess.CalledProcessError as exc:
        sys.stderr.write(exc.stderr or exc.stdout or str(exc))
        return exc.returncode or 1
    json.dump(payload, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
