#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from tmux_notification_record import build_db_record, event_id_for, validate_db_record


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a tmux-runtime handoff bundle from one tmux notification event."
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
        help="Codex session mode for tmux-runtime handoff delivery, defaults to fixed",
    )
    return parser.parse_args()


def load_event(event_file: str | None) -> dict[str, Any]:
    if event_file:
        return json.loads(Path(event_file).read_text(encoding="utf-8"))
    raw = sys.stdin.read().strip()
    if not raw:
        raise ValueError("no event payload provided on stdin")
    return json.loads(raw)


def build_notification_message(event: dict[str, Any]) -> str:
    target = str(event.get("target") or "").strip()
    if not target:
        raise ValueError("target is required for tmux-runtime handoff notification")
    if str(event.get("event") or "").strip() in {"pane_stopped", "pane_unreachable"}:
        return f"去{target}检查 SOP 状态"
    pane_title = str(event.get("pane_title") or "").strip() or "未知 pane"
    state_label = str(event.get("state_label") or "").strip() or "停止"
    reason = str(event.get("reason") or "").strip()
    if reason:
        return f"{pane_title} {state_label}：{target}。原因：{reason}"
    return f"{pane_title} {state_label}：{target}"


def build_bundle(event: dict[str, Any], *, table: str, session_mode: str) -> dict[str, Any]:
    event_id = event.get("event_id") or event_id_for(event)
    codex_thread_id = str(event.get("codex_thread_id") or "").strip()
    record = build_db_record(event)
    validation = validate_db_record(record)
    deliverable = bool(event.get("deliverable"))
    notification = {
        "title": "tmux runtime",
        "message": build_notification_message(event),
        "deliverable": deliverable,
    }
    tmux_runtime_handoff = {
        "skill": "tmux-runtime",
        "event_id": event_id,
        "target": {
            "session_mode": session_mode,
            "thread_id": codex_thread_id,
        },
        "delivery": {
            "transport": "codex_window_ipc",
            "deliverable": deliverable,
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
        "tmux_runtime_handoff": tmux_runtime_handoff,
        "db_write": db_write,
        "fanout": [
            {"channel": "tmux_runtime_handoff", "payload": tmux_runtime_handoff},
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
