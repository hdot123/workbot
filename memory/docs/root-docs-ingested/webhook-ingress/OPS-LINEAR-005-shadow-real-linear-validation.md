# OPS-LINEAR-005 Real Linear Shadow Validation Report

Date: 2026-05-04

## Summary

OPS-LINEAR-005 completed real Linear production-event shadow validation without cutting over the current production webhook and without modifying the existing n8n workflow business logic.

Decision: **Option A** was used. Linear supports multiple webhooks, so a second shadow webhook endpoint was created:

- Production webhook remains: `https://webhook.exa.edu.kg/webhook/events`
- Shadow webhook added: `https://webhook.exa.edu.kg/webhooks/linear`

## Constraints verified

| Constraint | Result |
|---|---|
| Do not modify existing n8n business workflow | PASS |
| Do not switch current Linear production webhook URL | PASS |
| Do not trigger shadow ingress into production n8n business workflow | PASS (`WEBHOOK_INGRESS_MODE=shadow`, `n8n_forwarded=0`) |
| Keep existing `/webhook/events` online | PASS |
| Keep this round as no-cutover | PASS |

## Linear webhook configuration

Existing production webhook:

- ID: `3cafb372-3aa1-4697-9ff4-0b1d6aaa7ce4`
- Label: `linear`
- URL: `https://webhook.exa.edu.kg/webhook/events`
- Enabled: `true`

New shadow webhook:

- ID: `9e1edca6-1d2c-4f42-9a7c-07ddb5654d0d`
- Label: `linear-shadow-ops-005`
- URL: `https://webhook.exa.edu.kg/webhooks/linear`
- Enabled: `true`
- Resource types matched production coverage, including `Issue` and `Comment`.

Important: the shadow webhook has its own Linear signing secret. The node-22 `webhook-ingress-shadow` service was updated to use this shadow webhook secret, not the production webhook secret.

## Real Linear events triggered

A temporary Linear issue was created, updated, commented on, and archived:

- Issue: `JTO-179`
- Issue ID: `8277c03c-e4cc-4e26-a802-5b2fb212e776`
- URL: `https://linear.app/jtoom/issue/JTO-179/shadow-ops-005-real-linear-shadow-validation`
- Comment ID: `5147c617-fe43-42ea-94ff-f8a588c24854`
- Issue was archived after validation.

Required event classes verified:

| Required event | Linear event observed | Canonical event observed | Result |
|---|---|---|---|
| issue created | `Issue` / `create` | `issue` / `created` | PASS |
| issue updated | `Issue` / `update` | `issue` / `updated` | PASS |
| comment created | `Comment` / `create` | `comment` / `created` | PASS |

Additional cleanup events were also observed:

- `Comment` / `remove` -> `comment` / `deleted`
- `Issue` / `remove` -> `issue` / `deleted`

## Supabase verification

Supabase tables used:

- `webhook_raw_events`
- `webhook_canonical_events`
- `webhook_processing_logs`

Observed canonical rows for `JTO-179` / related resources:

| event_id | provider event | canonical event | delivery id | n8n_forwarded |
|---|---|---|---|---|
| `evt_fbf6eaec-6f43-4368-a400-2025cd35029c` | `Issue/create` | `issue/created` | `ae770ca3-8fd1-4564-b40b-e32dc7f831d5` | `0` |
| `evt_db87a730-d6a6-42e3-8e38-85bfcc16ca49` | `Issue/update` | `issue/updated` | `308a7697-2034-4900-8be4-4b047296c598` | `0` |
| `evt_41e90f3c-c43a-4e13-b63e-df7c233c5c49` | `Comment/create` | `comment/created` | `86bcb33e-1454-4a9b-a506-8e8b65b00ef1` | `0` |
| `evt_90645e97-ff0f-406b-9f33-259bc6ae8c08` | `Comment/remove` | `comment/deleted` | `975ce3cf-94da-4b83-94bc-dfe35cf120c2` | `0` |
| `evt_49ec73bd-4b38-42a6-a9ac-4ce05875bfef` | `Issue/remove` | `issue/deleted` | `1a71f647-ba9f-4b2f-95f6-761a63e4c994` | `0` |

Raw rows for these canonical events: `5`.

`n8n_forwarded=0` confirms the shadow ingress did not forward canonical events to production n8n.

## Production n8n verification

During the same real Linear event window, the existing production endpoint continued to receive Linear traffic and returned 200:

```text
POST /webhook/events HTTP/1.1 200 "Linear-Webhook"
POST /webhooks/linear HTTP/1.1 200 "Linear-Webhook"
```

This proves the existing production webhook remained active while the new shadow webhook received a mirror copy from Linear as a separate webhook subscription.

## Idempotency replay verification

Replay was tested using an already accepted real delivery ID:

- Delivery ID: `308a7697-2034-4900-8be4-4b047296c598`
- Response: `200 duplicate_accepted`
- Existing event returned: `evt_db87a730-d6a6-42e3-8e38-85bfcc16ca49`
- Canonical count before replay: `1`
- Canonical count after replay: `1`

Result: PASS. Duplicate delivery did not create another canonical event.

## Log and storage redaction

Findings and fixes:

1. Initial real shadow requests returned 401 because the service used the production Linear webhook secret while the shadow Linear webhook had a separate secret. Fixed by updating node-22 shadow service env to the shadow webhook secret.
2. Audit found `raw_headers` could persist sensitive headers. Fixed by adding shared header redaction and applying it to SQLite/Postgres storage.
3. Existing raw header rows were remediated in Supabase.

Current verification:

- `Linear-Signature` is stored as `[REDACTED]` in `webhook_raw_events.raw_headers`.
- Existing raw header rows with sensitive keys were remediated: `unredacted_sensitive_header_values = 0`.
- Recent shadow logs did not show database URL, DB password, service role, authorization token, or Linear signature plaintext.

## Rollback

Rollback the Linear shadow webhook:

```graphql
mutation WebhookDelete {
  webhookDelete(id: "9e1edca6-1d2c-4f42-9a7c-07ddb5654d0d") {
    success
  }
}
```

Rollback node-22 shadow route/service if needed:

```bash
# Restore nginx backup made during OPS-LINEAR-004
cd /opt/n8n-linear/nginx
cp webhook-gateway.conf.bak-<timestamp> webhook-gateway.conf
docker exec n8n-webhook-gateway nginx -t
docker restart n8n-webhook-gateway

# Stop shadow service
docker rm -f webhook-ingress-shadow
```

The existing production Linear webhook `/webhook/events` does not depend on the shadow webhook and remains available during rollback.

## Next cutover plan

No cutover in this round.

Future cutover steps:

1. Keep both Linear webhooks enabled for a soak period and monitor signature failures, duplicate rate, and Supabase write errors.
2. Build the canonical-event n8n consumer workflow that accepts Canonical Webhook Event v1 only.
3. Validate canonical n8n workflow with shadow events.
4. Switch production Linear webhook only after canonical business workflow is ready.
5. Keep old `/webhook/events` available during rollback window.

## Final verdict

OPS-LINEAR-005 acceptance criteria passed after remediation:

- Old `/webhook/events` still processed real Linear production events.
- New `/webhooks/linear` received real Linear events.
- Supabase raw/canonical/log tables recorded real events.
- New ingress stayed in shadow mode and did not trigger production n8n business workflow.
- At least three true Linear event classes normalized into canonical events.
- Duplicate replay returned `duplicate_accepted` and did not duplicate canonical rows.
- Logs/storage were remediated to avoid sensitive header exposure.
- This round did not cut over production.
