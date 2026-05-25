# Standardized Webhook Ingress Phase 1

## Scope

Phase 1 adds a parallel webhook ingress protocol layer for Linear only. It does not change or destroy the existing node-22 n8n workflow. The goal is to move provider-specific protocol concerns out of n8n so n8n receives canonical events only.

## Public ingress model

Provider requests enter provider-specific protocol endpoints:

- `POST /webhooks/linear`
- future: `/webhooks/github`, `/webhooks/slack`, `/webhooks/posthog`, `/webhooks/pagerduty`, `/webhooks/uptime-kuma`

The ingress layer verifies, normalizes, stores, deduplicates, ACKs, and then forwards canonical events to n8n business workflows. n8n is a business orchestrator only.

## Canonical Webhook Event v1

The canonical event schema is tracked at:

- `workspace/tools/webhook_ingress/schemas/canonical-webhook-event-v1.json`

Required shape:

```json
{
  "canonical_version": "v1",
  "event_id": "evt_<uuid>",
  "provider": "linear",
  "provider_event_type": "Issue",
  "provider_action": "update",
  "provider_delivery_id": "<provider delivery id if available>",
  "canonical_type": "issue",
  "canonical_action": "updated",
  "timestamp": "2026-05-04T00:00:00Z",
  "received_at": "2026-05-04T00:00:01Z",
  "source": {
    "provider": "linear",
    "instance_url": "https://linear.app",
    "workspace_id": "<workspace/team id>",
    "resource_id": "<provider resource id>",
    "resource_url": "<provider URL>"
  },
  "actor": {
    "id": "<actor id>",
    "display_name": "<actor name>",
    "email": "<actor email>"
  },
  "payload": {},
  "idempotency_key": "linear:<delivery-id-or-sha>",
  "raw_body_sha256": "sha256:<hex>"
}
```

## Linear Provider Adapter

Phase 1 implements `provider = linear`.

Rules:

1. Preserve raw body as bytes before JSON parsing.
2. Verify `Linear-Signature`/`X-Linear-Signature` with HMAC-SHA256 over raw body.
3. Do not verify against parsed JSON or re-serialized JSON.
4. Extract `type`, `action`, `data.id`, `data.identifier`, `data.url`, actor fields, and delivery id if present.
5. Convert provider event type/action into canonical type/action.

Linear resource coverage includes Issues, Comments, Customers, Documents, Initiative updates, Issue Labels, Project updates, Releases, Customer requests, Cycles, Emoji reactions, Initiatives, Issue attachments, Project Labels, Projects, Users, and Issue SLA.

## ACK response

Success:

```json
{
  "ok": true,
  "status": "accepted",
  "request_id": "req_<uuid>",
  "event_id": "evt_<uuid>",
  "provider": "linear"
}
```

Duplicate:

```json
{
  "ok": true,
  "status": "duplicate_accepted",
  "request_id": "req_<uuid>",
  "event_id": "evt_<existing>",
  "provider": "linear"
}
```

Invalid signature:

```json
{
  "ok": false,
  "status": "SIGNATURE_INVALID",
  "request_id": "req_<uuid>",
  "event_id": null,
  "provider": "linear",
  "error": "SIGNATURE_INVALID"
}
```

## Idempotency

Idempotency key:

1. Prefer `provider + delivery_id` when the provider supplies a delivery id.
2. Otherwise fallback to `provider + raw_body_sha256`.

Duplicate requests return `duplicate_accepted` and do not trigger n8n again.

## Storage tables

The ingress layer owns three tables in the dedicated Supabase webhook database:

- `webhook_raw_events`: immutable raw body, headers, request metadata, sha256.
- `webhook_canonical_events`: canonical event JSON and routing/idempotency metadata.
- `webhook_processing_logs`: signature, normalize, idempotency, store, and route logs.

Production database source:

- 1Password item: `supabase-webhook数据库`
- Item ID: `mgh2gmvw5w3kmjfhrcieoxfb54`
- Vault: `sever`
- Supabase project ref: `rxrcidmnbyvwmhxqdgku`
- Project URL: `https://rxrcidmnbyvwmhxqdgku.supabase.co`

PostgreSQL/Supabase DDL is tracked at:

- `workspace/tools/webhook_ingress/migrations/001_supabase_webhook_events.sql`

The Python `WebhookEventStore` SQLite implementation in `workspace/tools/webhook_ingress/storage.py` is retained only as a lightweight local/CI test store. Runtime ingress deployment should use the Supabase/PostgreSQL schema and server-side credentials from 1Password; do not use `anon public` for writes.

## n8n boundary

n8n must receive canonical events only. It must not:

- verify provider signatures;
- store raw provider payloads;
- perform idempotency;
- grow giant provider-specific IF branches over raw payloads.

Business workflows may route on `provider`, `canonical_type`, and `canonical_action` only.

## routes.yaml

Routing config is tracked at:

- `workspace/tools/webhook_ingress/routes.yaml`

The file maps canonical events to n8n workflow endpoints. Phase 1 enables Linear and keeps future provider entries disabled.

## Future provider onboarding

To add GitHub, Slack, PostHog, PagerDuty, or Uptime Kuma:

1. Add a provider adapter implementing signature/token verification over the provider's required signing base string.
2. Normalize provider payload into Canonical Webhook Event v1.
3. Add provider to `routes.yaml` and enable it.
4. Add provider secrets via environment variables only.
5. Add signature, idempotency, normalization, routing, and storage tests.

Provider auth expectations:

- GitHub: `X-Hub-Signature-256`, HMAC-SHA256, delivery id `X-GitHub-Delivery`.
- Slack: `X-Slack-Signature`, HMAC-SHA256 over `v0:{timestamp}:{raw_body}`.
- PostHog: bearer/shared token depending on configured webhook.
- PagerDuty: provider signature or event id depending on integration version.
- Uptime Kuma: pre-shared token header or query token.

## Tests and CI

Tests cover signature, idempotency, normalize, routing, fixed ACK response, raw event storage, and n8n receiving canonical events only.

CI workflow:

- `.github/workflows/webhook-ingress-validation.yml`
