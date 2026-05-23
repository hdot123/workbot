from __future__ import annotations

import json
from typing import Any

from .redaction import redact_mapping


class PostgresWebhookEventStore:
    """PostgreSQL/Supabase implementation of the webhook event store.

    Requires psycopg2/psycopg2-binary at runtime. Secrets stay in the caller's
    WEBHOOK_DATABASE_URL/SUPABASE_DB_URL environment variable and are never logged.
    """

    def __init__(self, database_url: str):
        try:
            import psycopg2
            import psycopg2.extras
        except Exception as exc:  # pragma: no cover - depends on deployment deps
            raise RuntimeError("psycopg2 is required for PostgresWebhookEventStore") from exc

        self._psycopg2 = psycopg2
        self._extras = psycopg2.extras
        self.conn = psycopg2.connect(database_url)
        self.conn.autocommit = False

    def find_event_by_idempotency_key(self, idempotency_key: str) -> dict[str, Any] | None:
        with self.conn.cursor(cursor_factory=self._extras.RealDictCursor) as cur:
            cur.execute(
                "select * from public.webhook_canonical_events where idempotency_key = %s",
                (idempotency_key,),
            )
            row = cur.fetchone()
        return dict(row) if row else None

    def save(self, *, request, canonical_event: dict[str, Any]) -> None:
        headers = redact_mapping(dict(request.headers))
        source = canonical_event["source"]
        actor = canonical_event.get("actor") or {}
        with self.conn:
            with self.conn.cursor() as cur:
                cur.execute(
                    """
                    insert into public.webhook_raw_events (
                        event_id, provider, idempotency_key, raw_body, raw_body_sha256,
                        raw_headers, request_path, source_ip, received_at
                    ) values (%s, %s, %s, %s, %s, %s::jsonb, %s, %s, %s)
                    """,
                    (
                        canonical_event["event_id"],
                        canonical_event["provider"],
                        canonical_event["idempotency_key"],
                        self._psycopg2.Binary(request.raw_body),
                        canonical_event["raw_body_sha256"],
                        json.dumps(headers, ensure_ascii=False, sort_keys=True),
                        request.path,
                        request.source_ip,
                        canonical_event["received_at"],
                    ),
                )
                cur.execute(
                    """
                    insert into public.webhook_canonical_events (
                        event_id, canonical_version, provider, provider_event_type,
                        provider_action, provider_delivery_id, canonical_type,
                        canonical_action, event_timestamp, received_at,
                        source_provider, source_instance_url, source_workspace_id,
                        source_resource_id, source_resource_url, actor_id,
                        actor_display_name, actor_email, payload, canonical_event,
                        idempotency_key, raw_body_sha256
                    ) values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s::jsonb, %s, %s)
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
                        source["provider"],
                        source.get("instance_url"),
                        source.get("workspace_id"),
                        source["resource_id"],
                        source.get("resource_url"),
                        actor.get("id"),
                        actor.get("display_name"),
                        actor.get("email"),
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
            with self.conn.cursor() as cur:
                cur.execute(
                    """
                    insert into public.webhook_processing_logs (event_id, provider, phase, level, message, details)
                    values (%s, %s, %s, %s, %s, %s::jsonb)
                    """,
                    (event_id, provider, phase, level, message, json.dumps(merged_details, ensure_ascii=False, sort_keys=True)),
                )

    def mark_forwarded(self, event_id: str) -> None:
        with self.conn:
            with self.conn.cursor() as cur:
                cur.execute(
                    """
                    update public.webhook_canonical_events
                    set n8n_forwarded = 1, n8n_forwarded_at = now()
                    where event_id = %s
                    """,
                    (event_id,),
                )

    def count(self, table: str) -> int:
        if table not in {"webhook_raw_events", "webhook_canonical_events", "webhook_processing_logs"}:
            raise ValueError(f"unknown table: {table}")
        with self.conn.cursor() as cur:
            cur.execute(f"select count(*) from public.{table}")
            return int(cur.fetchone()[0])
