#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from contextlib import suppress
from pathlib import Path
from typing import Any

from build_tmux_goto_bundle import build_bundle


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Deliver a tmux-goto notification into the current Codex session."
    )
    parser.add_argument(
        "--event-file",
        help="optional path to a JSON event file. If omitted, reads one JSON object from stdin.",
    )
    parser.add_argument(
        "--bundle-file",
        help="optional path to a prebuilt tmux-goto bundle. If omitted, accepts an event or bundle on stdin.",
    )
    parser.add_argument(
        "--session-mode",
        choices=("fixed", "new"),
        default="fixed",
        help="Codex session mode. fixed sends to the current session; new opens a fresh session first.",
    )
    parser.add_argument(
        "--opencli-bin",
        default="opencli",
        help="opencli executable path, defaults to opencli",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="print the delivery plan instead of executing it",
    )
    return parser.parse_args()


def load_json(path: str | None) -> dict[str, Any]:
    if path:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    raw = sys.stdin.read().strip()
    if not raw:
        raise ValueError("no input payload provided")
    return json.loads(raw)


def ensure_bundle(payload: dict[str, Any], *, session_mode: str) -> dict[str, Any]:
    if "tmux_goto" in payload:
        return payload
    return build_bundle(payload, table="tmux_notifications_raw", session_mode=session_mode)


def run_command(cmd: list[str], *, dry_run: bool, timeout: float | None = None) -> None:
    if dry_run:
        return
    subprocess.run(
        cmd,
        check=True,
        text=True,
        timeout=timeout,
        capture_output=True,
    )


def run_text_command(cmd: list[str], *, input_text: str | None = None) -> str:
    proc = subprocess.run(
        cmd,
        input=input_text,
        capture_output=True,
        text=True,
        check=True,
    )
    return proc.stdout


def activate_codex_app() -> None:
    run_text_command(
        [
            "osascript",
            "-e",
            'tell application "Codex" to activate',
            "-e",
            "delay 0.6",
        ]
    )


def send_new_session_shortcut() -> None:
    run_text_command(
        [
            "osascript",
            "-e",
            'tell application "System Events"',
            "-e",
            'tell process "Codex" to set frontmost to true',
            "-e",
            "delay 0.2",
            "-e",
            'keystroke "n" using command down',
            "-e",
            "end tell",
        ]
    )
    run_text_command(["osascript", "-e", "delay 0.5"])


def paste_and_submit(message: str) -> None:
    previous_clipboard = ""
    with suppress(subprocess.CalledProcessError):
        previous_clipboard = run_text_command(["pbpaste"])
    run_text_command(["pbcopy"], input_text=message)
    try:
        run_text_command(
            [
                "osascript",
                "-e",
                'tell application "System Events"',
                "-e",
                'tell process "Codex" to set frontmost to true',
                "-e",
                "delay 0.25",
                "-e",
                'keystroke "v" using command down',
                "-e",
                "delay 0.35",
                "-e",
                "key code 36",
                "-e",
                "end tell",
            ]
        )
    finally:
        run_text_command(["pbcopy"], input_text=previous_clipboard)


def fallback_deliver(message: str, *, session_mode: str) -> None:
    activate_codex_app()
    if session_mode == "new":
        send_new_session_shortcut()
    paste_and_submit(message)


def main() -> int:
    args = parse_args()
    try:
        payload = load_json(args.bundle_file or args.event_file)
        bundle = ensure_bundle(payload, session_mode=args.session_mode)
        tmux_goto = bundle["tmux_goto"]
        session_mode = str(tmux_goto.get("target", {}).get("session_mode", args.session_mode))
        message = str(tmux_goto.get("notification", {}).get("message", "")).strip()
        if not message:
            raise ValueError("tmux_goto.notification.message is empty")
    except (ValueError, KeyError, json.JSONDecodeError) as exc:
        sys.stderr.write(f"{exc}\n")
        return 1

    commands: list[list[str]] = []
    if session_mode == "new":
        commands.append([args.opencli_bin, "codex", "new"])
    commands.append([args.opencli_bin, "codex", "send", message])

    if args.dry_run:
        json.dump(
            {
                "status": "dry_run",
                "transport": "opencli_or_applescript",
                "session_mode": session_mode,
                "commands": commands,
                "message": message,
            },
            sys.stdout,
            ensure_ascii=False,
            indent=2,
        )
        sys.stdout.write("\n")
        return 0

    try:
        for index, cmd in enumerate(commands):
            timeout = 4.0 if cmd[:3] == [args.opencli_bin, "codex", "send"] else 5.0
            run_command(cmd, dry_run=False, timeout=timeout)
    except subprocess.TimeoutExpired:
        try:
            fallback_deliver(message, session_mode=session_mode)
        except subprocess.CalledProcessError as fallback_exc:
            sys.stderr.write(fallback_exc.stderr or fallback_exc.stdout or str(fallback_exc))
            sys.stderr.write("\n")
            return fallback_exc.returncode or 1
        json.dump(
            {
                "status": "delivered",
                "transport": "applescript",
                "session_mode": session_mode,
                "message": message,
                "fallback_reason": "opencli_timeout",
            },
            sys.stdout,
            ensure_ascii=False,
            indent=2,
        )
        sys.stdout.write("\n")
        return 0
    except subprocess.CalledProcessError as exc:
        stderr = exc.stderr or ""
        stdout = exc.stdout or ""
        if "Browser Extension is not connected" in stderr or "Browser Extension is not connected" in stdout:
            try:
                fallback_deliver(message, session_mode=session_mode)
            except subprocess.CalledProcessError as fallback_exc:
                sys.stderr.write(fallback_exc.stderr or fallback_exc.stdout or str(fallback_exc))
                sys.stderr.write("\n")
                return fallback_exc.returncode or 1
            json.dump(
                {
                    "status": "delivered",
                    "transport": "applescript",
                    "session_mode": session_mode,
                    "message": message,
                },
                sys.stdout,
                ensure_ascii=False,
                indent=2,
            )
            sys.stdout.write("\n")
            return 0
        sys.stderr.write(stderr or stdout or str(exc))
        sys.stderr.write("\n")
        return exc.returncode or 1

    json.dump(
        {
            "status": "delivered",
            "transport": "opencli",
            "session_mode": session_mode,
            "message": message,
        },
        sys.stdout,
        ensure_ascii=False,
        indent=2,
    )
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
