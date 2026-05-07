from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from .redaction import redact_mapping

# SQLite is kept as the lightweight local/CI test store.
# Production storage is Supabase/PostgreSQL; see migrations/001_supabase_webhook_events.sql.
SQLITE_DDL = """
CREATE TABLE IF NOT EXISTS webhook_raw_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id TEXT NOT NULL UNIQUE,
    provider TEXT NOT NULL,
    idempotency_key TEXT NOT NULL,
    raw_body BLOB NOT NULL,
    raw_body_sha256 TEXT NOT NULL,
    raw_headers TEXT NOT NULL,
    request_path TEXT NOT NULL,
    source_ip TEXT,
    received_at TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_webhook_raw_events_provider ON webhook_raw_events(provider);
CREATE INDEX IF NOT EXISTS idx_webhook_raw_events_idempotency ON webhook_raw_events(idempotency_key);
CREATE INDEX IF NOT EXISTS idx_webhook_raw_events_sha ON webhook_raw_events(raw_body_sha256);

CREATE TABLE IF NOT EXISTS webhook_canonical_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id TEXT NOT NULL UNIQUE,
    canonical_version TEXT NOT NULL,
    provider TEXT NOT NULL,
    provider_event_type TEXT NOT NULL,
    provider_action TEXT NOT NULL,
    provider_delivery_id TEXT,
    canonical_type TEXT NOT NULL,
    canonical_action TEXT NOT NULL,
    event_timestamp TEXT NOT NULL,
    received_at TEXT NOT NULL,
    source_resource_id TEXT NOT NULL,
    payload TEXT NOT NULL,
    canonical_event TEXT NOT NULL,
    idempotency_key TEXT NOT NULL UNIQUE,
    raw_body_sha256 TEXT NOT NULL,
    n8n_forwarded INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_webhook_canonical_provider_type ON webhook_canonical_events(provider, canonical_type);
CREATE INDEX IF NOT EXISTS idx_webhook_canonical_idempotency ON webhook_canonical_events(idempotency_key);

CREATE TABLE IF NOT EXISTS webhook_processing_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id TEXT,
    provider TEXT NOT NULL,
    phase TEXT NOT NULL,
    level TEXT NOT NULL,
    message TEXT NOT NULL,
    details TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_webhook_processing_logs_event ON webhook_processing_logs(event_id);
CREATE INDEX IF NOT EXISTS idx_webhook_processing_logs_provider ON webhook_processing_logs(provider);
"""


class WebhookEventStore:
    def __init__(self, db_path: str | Path | None = None):
        self.db_path = db_path or ":memory:"
        self.conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.init_schema()

    def init_schema(self) -> None:
        self.conn.executescript(SQLITE_DDL)
        self.conn.commit()

    def find_event_by_idempotency_key(self, idempotency_key: str) -> dict[str, Any] | None:
        row = self.conn.execute(
            "SELECT * FROM webhook_canonical_events WHERE idempotency_key = ?",
            (idempotency_key,),
        ).fetchone()
        return dict(row) if row else None

    def save(self, *, request, canonical_event: dict[str, Any]) -> None:
        headers = redact_mapping(dict(request.headers))
        with self.conn:
            self.conn.execute(
                """
                INSERT INTO webhook_raw_events (
                    event_id, provider, idempotency_key, raw_body, raw_body_sha256,
                    raw_headers, request_path, source_ip, received_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    canonical_event["event_id"],
                    canonical_event["provider"],
                    canonical_event["idempotency_key"],
                    request.raw_body,
                    canonical_event["raw_body_sha256"],
                    json.dumps(headers, ensure_ascii=False, sort_keys=True),
                    request.path,
                    request.source_ip,
                    canonical_event["received_at"],
                ),
            )
            self.conn.execute(
                """
                INSERT INTO webhook_canonical_events (
                    event_id, canonical_version, provider, provider_event_type,
                    provider_action, provider_delivery_id, canonical_type,
                    canonical_action, event_timestamp, received_at, source_resource_id,
                    payload, canonical_event, idempotency_key, raw_body_sha256
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    canonical_event["event_id"],
                    canonical_event["canonical_version"],
                    canonical_event["provider"],
                    canonical_event["provider_event_type"],
                    canonical_event["provider_action"],
                    canonical_event.get("provider_delivery_id"),
                    canonical_event["canonical_type"],
                    canonical_event["canonical_action"],
                    canonical_event["timestamp"],
                    canonical_event["received_at"],
                    canonical_event["source"]["resource_id"],
                    json.dumps(canonical_event["payload"], ensure_ascii=False, sort_keys=True),
                    json.dumps(canonical_event, ensure_ascii=False, sort_keys=True),
                    canonical_event["idempotency_key"],
                    canonical_event["raw_body_sha256"],
                ),
            )

    def log(
        self,
        *,
        provider: str,
        phase: str,
        level: str,
        message: str,
        event_id: str | None = None,
        details: dict[str, Any] | None = None,
        route_name: str | None = None,
        target_type: str | None = None,
        status: str | None = None,
        attempt: int | None = None,
        canonical_event_id: str | None = None,
        action_name: str | None = None,
        idempotency_key: str | None = None,
        project_id: str | None = None,
    ) -> None:
        merged_details = dict(details or {})
        for key, value in {
            "route_name": route_name,
            "target_type": target_type,
            "status": status,
            "attempt": attempt,
            "canonical_event_id": canonical_event_id,
            "action_name": action_name,
            "idempotency_key": idempotency_key,
            "project_id": project_id,
        }.items():
            if value is not None:
                merged_details[key] = value
        with self.conn:
            self.conn.execute(
                "INSERT INTO webhook_processing_logs (event_id, provider, phase, level, message, details) VALUES (?, ?, ?, ?, ?, ?)",
                (event_id, provider, phase, level, message, json.dumps(merged_details, ensure_ascii=False, sort_keys=True)),
            )

    def mark_forwarded(self, event_id: str) -> None:
        with self.conn:
            self.conn.execute(
                "UPDATE webhook_canonical_events SET n8n_forwarded = 1 WHERE event_id = ?",
                (event_id,),
            )

    def count(self, table: str) -> int:
        if table not in {"webhook_raw_events", "webhook_canonical_events", "webhook_processing_logs"}:
            raise ValueError(f"unknown table: {table}")
        return int(self.conn.execute(f"SELECT count(*) FROM {table}").fetchone()[0])
