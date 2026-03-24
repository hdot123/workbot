#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sqlite3
import sys
from pathlib import Path
from typing import Any, Iterable

from notification_record import build_db_record, validate_db_record

TABLE_NAME_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
IDENTITY_PATTERN = re.compile(r"^[0-9a-f]{16}$")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Write tmux-goto notification records into a local SQLite database."
    )
    parser.add_argument(
        "--db-file",
        default="/Users/busiji/.codex/skills/tmux-goto/data/notifications.sqlite3",
        help="sqlite database file path",
    )
    parser.add_argument(
        "--table",
        default="tmux_notifications_raw",
        help="target sqlite table name",
    )
    parser.add_argument(
        "--input-file",
        help="optional JSON/JSONL input file. If omitted, reads stdin.",
    )
    return parser.parse_args()


def ensure_table_name(name: str) -> str:
    if not TABLE_NAME_PATTERN.match(name):
        raise ValueError(f"invalid table name: {name}")
    return name


def iter_input_chunks(input_file: str | None) -> Iterable[str]:
    if input_file:
        text = Path(input_file).read_text(encoding="utf-8").strip()
        if not text:
            return []
        return [line.strip() for line in text.splitlines() if line.strip()]
    return (line.strip() for line in sys.stdin if line.strip())


def decode_payload(raw: str) -> dict[str, Any]:
    return json.loads(raw)


def normalize_instructions(payload: dict[str, Any]) -> list[dict[str, Any]]:
    if payload.get("action") == "db_insert":
        return [payload]
    if payload.get("channel") == "db_write" and isinstance(payload.get("payload"), dict):
        return [payload["payload"]]
    fanout = payload.get("fanout")
    if isinstance(fanout, list):
        instructions: list[dict[str, Any]] = []
        for item in fanout:
            if isinstance(item, dict) and item.get("channel") == "db_write" and isinstance(item.get("payload"), dict):
                instructions.append(item["payload"])
        return instructions
    if payload.get("event") == "pane_attention":
        record = build_db_record(payload)
        validation = validate_db_record(record)
        return [
            {
                "action": "db_insert",
                "table": "tmux_notifications_raw",
                "record": record,
                "validation": validation,
                "identity": {
                    "identity_id": record["identity_id"],
                    "identity_key": record["identity_id"],
                },
                "write_policy": {"on_invalid_identity": "drop"},
            }
        ]
    return []


def ensure_schema(conn: sqlite3.Connection, table: str) -> None:
    conn.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {table} (
            identity_id TEXT PRIMARY KEY,
            event_id TEXT NOT NULL,
            schema_version TEXT NOT NULL,
            event_type TEXT NOT NULL,
            detected_at TEXT NOT NULL,
            session TEXT,
            window TEXT,
            pane_id TEXT NOT NULL,
            pane_title TEXT NOT NULL,
            cwd TEXT,
            current_command TEXT,
            prompt TEXT NOT NULL,
            prompt_headline TEXT NOT NULL,
            option_lines_json TEXT NOT NULL,
            option_count INTEGER NOT NULL,
            recent_output TEXT NOT NULL,
            signature TEXT NOT NULL,
            classification_status TEXT NOT NULL,
            classification_labels_json TEXT NOT NULL,
            source TEXT NOT NULL,
            validation_valid INTEGER NOT NULL,
            validation_errors_json TEXT NOT NULL,
            validation_warnings_json TEXT NOT NULL,
            inserted_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        f"CREATE INDEX IF NOT EXISTS idx_{table}_detected_at ON {table}(detected_at)"
    )
    conn.execute(
        f"CREATE INDEX IF NOT EXISTS idx_{table}_pane_id ON {table}(pane_id)"
    )
    conn.execute(
        f"CREATE INDEX IF NOT EXISTS idx_{table}_signature ON {table}(signature)"
    )


def identity_is_valid(identity: dict[str, Any], record: dict[str, Any]) -> bool:
    identity_id = str(identity.get("identity_id", ""))
    identity_key = str(identity.get("identity_key", ""))
    record_identity = str(record.get("identity_id", ""))
    if not identity_id or not identity_key or not record_identity:
        return False
    if not IDENTITY_PATTERN.match(identity_id):
        return False
    if not IDENTITY_PATTERN.match(identity_key):
        return False
    return identity_id == identity_key == record_identity


def insert_record(conn: sqlite3.Connection, table: str, instruction: dict[str, Any]) -> str:
    record = instruction.get("record")
    validation = instruction.get("validation") or validate_db_record(record)
    identity = instruction.get("identity") or {}
    if not isinstance(record, dict):
        return "dropped_invalid_record"
    if not isinstance(validation, dict):
        return "dropped_invalid_validation"
    if not identity_is_valid(identity, record):
        return "dropped_invalid_identity"
    if not validation.get("valid", False):
        return "dropped_invalid_record"

    cursor = conn.execute(
        f"""
        INSERT OR IGNORE INTO {table} (
            identity_id,
            event_id,
            schema_version,
            event_type,
            detected_at,
            session,
            window,
            pane_id,
            pane_title,
            cwd,
            current_command,
            prompt,
            prompt_headline,
            option_lines_json,
            option_count,
            recent_output,
            signature,
            classification_status,
            classification_labels_json,
            source,
            validation_valid,
            validation_errors_json,
            validation_warnings_json,
            inserted_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            record["identity_id"],
            record["event_id"],
            record["schema_version"],
            record["event_type"],
            record["detected_at"],
            record.get("session"),
            record.get("window"),
            record["pane_id"],
            record["pane_title"],
            record.get("cwd"),
            record.get("current_command"),
            record["prompt"],
            record["prompt_headline"],
            json.dumps(record.get("option_lines", []), ensure_ascii=False),
            record["option_count"],
            record["recent_output"],
            record["signature"],
            record["classification_status"],
            json.dumps(record.get("classification_labels", []), ensure_ascii=False),
            record["source"],
            1 if validation.get("valid") else 0,
            json.dumps(validation.get("errors", []), ensure_ascii=False),
            json.dumps(validation.get("warnings", []), ensure_ascii=False),
            dt.datetime.now(dt.timezone.utc).isoformat(),
        ),
    )
    return "ignored_duplicate" if cursor.rowcount == 0 else "inserted"


def main() -> int:
    args = parse_args()
    table = ensure_table_name(args.table)
    db_file = Path(args.db_file)
    db_file.parent.mkdir(parents=True, exist_ok=True)

    stats = {
        "processed": 0,
        "inserted": 0,
        "ignored_duplicate": 0,
        "dropped_invalid_identity": 0,
        "dropped_invalid_record": 0,
        "dropped_invalid_validation": 0,
        "unsupported_payload": 0,
    }

    chunks = iter_input_chunks(args.input_file)
    with sqlite3.connect(db_file) as conn:
        ensure_schema(conn, table)
        for raw in chunks:
            try:
                payload = decode_payload(raw)
            except json.JSONDecodeError:
                stats["unsupported_payload"] += 1
                continue
            instructions = normalize_instructions(payload)
            if not instructions:
                stats["unsupported_payload"] += 1
                continue
            for instruction in instructions:
                stats["processed"] += 1
                outcome = insert_record(conn, table, instruction)
                stats[outcome] += 1
                conn.commit()

    summary = {
        "db_file": str(db_file),
        "table": table,
        "stats": stats,
    }
    json.dump(summary, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
