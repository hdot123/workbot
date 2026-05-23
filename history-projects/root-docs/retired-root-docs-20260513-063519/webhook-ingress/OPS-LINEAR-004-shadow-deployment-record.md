# Webhook Ingress Phase 1 Shadow Deployment Record

Date: 2026-05-04

## Scope

Deploy `webhook_ingress` as a shadow-mode service on node-22 without changing the current Linear production webhook URL and without modifying the production n8n workflow.

## Deployed topology

```text
Cloudflare Tunnel
  -> n8n-webhook-gateway nginx
     -> GET  /healthz          -> n8n:5678/healthz
     -> POST /webhook/events   -> n8n:5678  (existing production entry, unchanged)
     -> POST /webhooks/linear  -> webhook-ingress-shadow:8000/webhooks/linear
```

## Server deployment

Node: `node-22`

New service files:

- `/opt/webhook-ingress/Dockerfile`
- `/opt/webhook-ingress/webhook_ingress_bundle.tgz`
- `/opt/webhook-ingress/.env` (`600 root:root`)

Container:

- Name: `webhook-ingress-shadow`
- Image: `webhook-ingress:phase1`
- Network: `n8n-linear_default`
- Published local port: `127.0.0.1:5680 -> 8000`
- Mode: `WEBHOOK_INGRESS_MODE=shadow`

Environment variables configured from 1Password, values not recorded:

- `WEBHOOK_DATABASE_URL`
- `LINEAR_WEBHOOK_SECRET`
- `WEBHOOK_INGRESS_MODE=shadow`
- `WEBHOOK_LOG_LEVEL=INFO`

## Database

Supabase item:

- 1Password item: `supabase-webhook数据库`
- Item ID: `mgh2gmvw5w3kmjfhrcieoxfb54`
- Project ref: `rxrcidmnbyvwmhxqdgku`

Migration executed twice successfully for idempotency:

- `workspace/tools/webhook_ingress/migrations/001_supabase_webhook_events.sql`

Tables present:

- `webhook_raw_events`
- `webhook_canonical_events`
- `webhook_processing_logs`

## Nginx gateway change

File:

- `/opt/n8n-linear/nginx/webhook-gateway.conf`

Added route:

```nginx
location = /webhooks/linear {
    proxy_pass http://webhook-ingress-shadow:8000/webhooks/linear;
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto https;
}
```

A timestamped backup was created in `/opt/n8n-linear/nginx/` before editing.

## Acceptance results

Public endpoint checks:

| Check | Result |
|---|---|
| `GET https://webhook.exa.edu.kg/healthz` | 200 |
| `GET https://webhook.exa.edu.kg/webhooks/linear` | 405 (FastAPI route reached; POST only) |
| `GET https://webhook.exa.edu.kg/webhook/events` | 404 (existing n8n method behavior) |

Shadow endpoint tests:

| Test | Result |
|---|---|
| Valid simulated Linear payload | 200 `accepted` |
| Repeated delivery id | 200 `duplicate_accepted` |
| Invalid signature | 401 `SIGNATURE_INVALID` |
| Supabase raw rows for public test idempotency key | 1 |
| Supabase canonical rows for public test idempotency key | 1 |

Existing production endpoint check:

- `POST https://webhook.exa.edu.kg/webhook/events` with a valid synthetic Linear HMAC still returned 200 from the existing n8n workflow.
- The extra n8n execution observed during acceptance was caused by this explicit old-entry verification POST, not by shadow endpoint forwarding.

## Shadow isolation

`WEBHOOK_INGRESS_MODE=shadow` means the service stores and ACKs canonical events but does not call production n8n workflows.

Log scan showed Linear signature headers redacted as `[REDACTED]`; no database URL, database password, service role key, authorization token, or webhook secret was printed by the service logs inspected.

## Rollback

1. Remove nginx route by restoring the timestamped backup:

```bash
cd /opt/n8n-linear/nginx
cp webhook-gateway.conf.bak-<timestamp> webhook-gateway.conf
docker exec n8n-webhook-gateway nginx -t
docker restart n8n-webhook-gateway
```

2. Stop/remove shadow service:

```bash
docker rm -f webhook-ingress-shadow
```

3. Optional cleanup:

```bash
rm -rf /opt/webhook-ingress
```

4. Verify old entry remains:

```bash
curl -sS -o /dev/null -w '%{http_code}\n' https://webhook.exa.edu.kg/healthz
curl -sS -o /dev/null -w '%{http_code}\n' https://webhook.exa.edu.kg/webhook/events
```

## Next cutover plan

Do not cut over in this round. For a future cutover:

1. Run shadow mode with real duplicate Linear test traffic for a soak period.
2. Add production monitoring for `SIGNATURE_INVALID`, duplicate rate, and Supabase write errors.
3. Add a canonical-event n8n workflow that consumes only Canonical Webhook Event v1.
4. Switch Linear webhook URL from `/webhook/events` to `/webhooks/linear` only after canonical n8n workflow is ready.
5. Keep `/webhook/events` available during rollback window.
