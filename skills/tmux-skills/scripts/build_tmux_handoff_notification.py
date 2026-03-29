#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import subprocess
import sys


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


def signature_for(payload: str) -> str:
    return hashlib.sha1(payload.encode("utf-8")).hexdigest()[:12]


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


def build_payload(target: str, start: int) -> dict[str, object]:
    recent_output = capture_output(target, start)
    event = {
        "event": "pane_snapshot",
        "state_class": "pane_snapshot",
        "state_label": "快照",
        "deliverable": False,
        "reachable": True,
        "detected_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "target": target,
        "session": display_value(target, "#{session_name}"),
        "window": display_value(target, "#{window_index}"),
        "pane_id": display_value(target, "#{pane_id}"),
        "pane_title": display_value(target, "#{pane_title}"),
        "cwd": display_value(target, "#{pane_current_path}"),
        "current_command": display_value(target, "#{pane_current_command}"),
        "prompt": recent_output,
        "prompt_headline": recent_output.splitlines()[-1] if recent_output.splitlines() else "",
        "option_lines": [],
        "recent_output": recent_output,
        "signature": signature_for(recent_output or target),
        "source": "tmux-skills",
    }
    event["event_id"] = event_id_for(event)
    return event


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a tmux-skills handoff notification payload for one tmux target."
    )
    parser.add_argument("--target", required=True, help="tmux target, for example formal-session:1.1")
    parser.add_argument(
        "--start",
        type=int,
        default=-120,
        help="capture-pane start offset, defaults to -120",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        payload = build_payload(args.target, args.start)
    except subprocess.CalledProcessError as exc:
        sys.stderr.write(exc.stderr or exc.stdout or str(exc))
        return exc.returncode or 1
    json.dump(payload, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
