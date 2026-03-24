#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

from notification_record import build_db_record, event_id_for, validate_db_record


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a tmux-goto handoff bundle from one tmux notification event."
    )
    parser.add_argument(
        "--event-file",
        help="optional path to a JSON event file. If omitted, reads one JSON object from stdin.",
    )
    parser.add_argument(
        "--table",
        default="tmux_notifications_raw",
        help="target logical table name for the db insert instruction",
    )
    parser.add_argument(
        "--session-mode",
        choices=("fixed", "new"),
        default="fixed",
        help="Codex session mode for tmux-goto delivery, defaults to fixed",
    )
    return parser.parse_args()


def load_event(event_file: str | None) -> dict[str, Any]:
    if event_file:
        return json.loads(Path(event_file).read_text(encoding="utf-8"))
    raw = sys.stdin.read().strip()
    if not raw:
        raise ValueError("no event payload provided on stdin")
    return json.loads(raw)


def _infer_call_identity(event: dict[str, Any]) -> str:
    candidates = [
        str(event.get("pane_title") or ""),
        str(event.get("prompt_headline") or ""),
        str(event.get("prompt") or ""),
        str(event.get("recent_output") or ""),
    ]
    for candidate in candidates:
        match = re.search(r"\b([a-z]+(?:-[a-z]+)*-bot)\b", candidate, re.IGNORECASE)
        if match:
            return match.group(1)
    pane_title = str(event.get("pane_title") or "").strip().lower()
    if pane_title == "qa":
        return "qa-bot"
    if pane_title == "dev":
        return "dev-bot"
    return "unknown"


def _format_call_line(identity: str) -> str:
    normalized = identity.strip().lower()
    if normalized == "dev-bot":
        return "呼叫: 开发 dev-bot"
    if normalized == "qa-bot":
        return "呼叫: 测试 qa-bot"
    return f"呼叫: {identity}"


def build_notification_message(event: dict[str, Any]) -> str:
    """Build minimal 3-line notification message."""
    pane_id = str(event.get("pane_id") or "").strip()
    if not pane_id:
        raise ValueError("pane_id is required for tmux-goto notification")
    call_identity = _infer_call_identity(event)
    return "\n".join([
        "通知",
        _format_call_line(call_identity),
        f"pane_id: {pane_id}",
    ])


def build_bundle(event: dict[str, Any], *, table: str, session_mode: str) -> dict[str, Any]:
    event_id = event.get("event_id") or event_id_for(event)
    record = build_db_record(event)
    validation = validate_db_record(record)
    notification = {
        "title": "通知",
        "message": build_notification_message(event),
    }
    tmux_goto = {
        "skill": "tmux-goto",
        "event_id": event_id,
        "identity_id": event_id,
        "target": {
            "session_mode": session_mode,
        },
        "delivery": {
            "transport": "codex_desktop",
        },
        "notification": notification,
        "payload": event,
    }
    db_write = {
        "action": "db_insert",
        "table": table,
        "record": record,
        "validation": validation,
        "identity": {
            "identity_id": record["identity_id"],
            "identity_key": record["identity_id"],
        },
        "write_policy": {"on_invalid_identity": "drop"},
    }
    return {
        "identity_id": event_id,
        "event_id": event_id,
        "session_mode": session_mode,
        "tmux_goto": tmux_goto,
        "db_write": db_write,
        "fanout": [
            {"channel": "tmux_goto", "payload": tmux_goto},
            {"channel": "db_write", "payload": db_write},
        ],
    }


def main() -> int:
    args = parse_args()
    try:
        event = load_event(args.event_file)
        bundle = build_bundle(event, table=args.table, session_mode=args.session_mode)
    except (ValueError, json.JSONDecodeError) as exc:
        sys.stderr.write(f"{exc}\n")
        return 1
    json.dump(bundle, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
