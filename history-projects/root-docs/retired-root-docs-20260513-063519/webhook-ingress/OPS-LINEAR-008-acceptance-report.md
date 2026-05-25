# OPS-LINEAR-008 Acceptance Report

Date: 2026-05-04

## Scope

Enable a controlled business-action canary for Linear webhooks: one canary comment on test-scope Linear issues only. Full production automation remains disabled.

## Implementation

- Public ingress unchanged: `POST https://webhook.exa.edu.kg/webhook/events`.
- Public `/webhooks/linear` remains disabled at gateway level.
- No second Linear webhook was added.
- `webhook-ingress` remains Docker Compose managed in `production_canary` mode.
- Linear canary comment action is implemented in ingress side to avoid n8n execution-data token leakage.
- n8n `production-canary-events` remains minimal success-only canonical receiver.
- Canary comment action requires:
  - `WEBHOOK_INGRESS_MODE=production_canary`
  - `LINEAR_CANARY_COMMENT_ENABLED=true`
  - `LINEAR_CANARY_API_TOKEN` present in root-only `/opt/n8n-linear/.env.webhook-ingress`
  - canonical event is Linear `issue/updated`
  - issue title contains `[webhook-ingress-canary]`
- Comment body prefix: `[webhook-ingress-canary]`.
- Duplicate delivery path returns before n8n forward/comment action.

## Validation Evidence

### Endpoint exposure

Local gateway checks on node-22:

- `/webhook/events` GET: `405` (POST-only route exists)
- `/webhooks/linear`: `404`
- `/`: `404`
- `/rest/settings`: `404`
- `/healthz`: `200`

### Synthetic duplicate

Synthetic marked Issue updated delivery:

- First delivery: `200 accepted`, event `evt_8bc87c2f-a3bf-4b85-8c6c-ac2f6dfc44ae`
- Replay same delivery id: `200 duplicate_accepted`
- `processing_logs.canary_forward.details` includes:
  - `route_name=linear.production_canary`
  - `target_type=n8n_canary`
  - `status=success`
  - `attempt=1`
  - `canonical_event_id`

Synthetic issue id was fake, so Linear commentCreate failed safely while the webhook still returned `200 accepted`; this verified error isolation.

### Real Linear canary

Temporary test issue:

- Issue: `JTO-183`
- Issue id: `a541734a-be8d-41d0-9fd0-48295ceb2581`
- Title: `[webhook-ingress-canary] OPS-LINEAR-008 real canary comment validation`

Observed events:

- `evt_0f21efe8-61b1-456f-ae4c-b86ca55ffe4a`: Issue create, `n8n_forwarded=1`, comment action skipped as not update.
- `evt_292aae0b-663e-41d0-ac70-ea9a8577891b`: Issue update, `n8n_forwarded=1`, one canary comment created.
- `evt_c0673ea9-4adf-4b53-96cb-7adaf5716284`: Comment create from canary comment, `n8n_forwarded=1`, comment action skipped as not issue update.

Canary comment:

- Comment id: `449307c7-5105-49ad-8a8e-741dd21fb65c`
- Count on issue with prefix `[webhook-ingress-canary]`: `1`
- Body begins: `[webhook-ingress-canary] OPS-LINEAR-008 canonical event evt_292aae0b-663e-41d0-ac70-ea9a8577891b accepted for JTO-183.`

Supabase summary for JTO-183 validation events:

- canonical total: `3`
- forwarded: `3`
- Issue update `canary_forward`: `target_type=n8n_canary`, `status=success`, `attempt=1`, `canonical_event_id=evt_292aae0b-663e-41d0-ac70-ea9a8577891b`
- Issue update `canary_action`: `target_type=linear_comment_canary`, `status=success`, `attempt=1`, `canonical_event_id=evt_292aae0b-663e-41d0-ac70-ea9a8577891b`

n8n executions:

- `production canary events` executions `112`, `113`, `114` success for the JTO-183 event sequence.

Cleanup:

- `JTO-183` archived successfully after validation.

### Redaction

Ingress log scan hits for secret-like patterns:

- `lin_api_`
- `Authorization:`
- `postgres://` / `postgresql://`
- `Linear-Signature:`
- `WEBHOOK_DATABASE_URL`
- `LINEAR_CANARY_API_TOKEN`

Result: `0` hits.

## Negative Checks

- No GitLab CI enabled.
- No Slack production notification enabled.
- No bulk Linear update executed.
- No issue status migration executed.
- No second Linear webhook added.
- Comment-created webhook did not trigger a second comment.

## Rollback

One-command dry-run rollback on node-22:

```bash
ssh node-22 'set -euo pipefail
cd /opt/n8n-linear
cp .env .env.bak-ops8-rollback-$(date +%Y%m%d-%H%M%S)
cp .env.webhook-ingress .env.webhook-ingress.bak-ops8-rollback-$(date +%Y%m%d-%H%M%S)
python3 - <<"PY"
from pathlib import Path
for path in (Path(".env"), Path(".env.webhook-ingress")):
    lines = path.read_text().splitlines()
    out = []
    seen_mode = seen_url = seen_comment = False
    for line in lines:
        if line.startswith("WEBHOOK_INGRESS_MODE="):
            out.append("WEBHOOK_INGRESS_MODE=canary_dryrun"); seen_mode = True
        elif line.startswith("N8N_CANONICAL_WEBHOOK_URL="):
            out.append("N8N_CANONICAL_WEBHOOK_URL=http://n8n:5678/webhook/canonical-dryrun-events/webhook/canonical-events"); seen_url = True
        elif line.startswith("LINEAR_CANARY_COMMENT_ENABLED="):
            out.append("LINEAR_CANARY_COMMENT_ENABLED=false"); seen_comment = True
        elif line.startswith("LINEAR_CANARY_API_TOKEN="):
            continue
        else:
            out.append(line)
    if path.name == ".env":
        if not seen_mode: out.append("WEBHOOK_INGRESS_MODE=canary_dryrun")
        if not seen_url: out.append("N8N_CANONICAL_WEBHOOK_URL=http://n8n:5678/webhook/canonical-dryrun-events/webhook/canonical-events")
    if path.name == ".env.webhook-ingress" and not seen_comment:
        out.append("LINEAR_CANARY_COMMENT_ENABLED=false")
    path.write_text("\n".join(out) + "\n")
PY
chmod 600 .env.webhook-ingress
docker compose up -d --force-recreate webhook-ingress
sleep 5
docker compose ps webhook-ingress
'
```

Post-rollback verification:

```bash
ssh node-22 'curl -sS http://127.0.0.1:5678/healthz; docker logs --tail=30 webhook-ingress-shadow'
```
