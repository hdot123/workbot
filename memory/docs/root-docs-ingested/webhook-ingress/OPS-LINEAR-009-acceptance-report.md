# OPS-LINEAR-009 Acceptance Report

Date: 2026-05-04

## Scope

Extend the controlled Linear canary comment action from title-scoped tests to the explicit Linear test label `webhook-ingress-canary`, while keeping full production automation disabled.

## Implementation

- Public ingress unchanged: `POST https://webhook.exa.edu.kg/webhook/events`.
- Public `/webhooks/linear` remains disabled at gateway level.
- No second Linear webhook was added.
- No GitLab CI, Slack production notification, bulk Linear update, or issue status migration was enabled.
- Business action was decoupled from ingress core handler:
  - `tools/webhook_ingress/actions.py`: `ActionRegistry`, `LinearCanaryCommentAction`, label guard.
  - `tools/webhook_ingress/executors.py`: `LinearCanaryCommentExecutor` for the Linear `commentCreate` side effect.
  - `WebhookIngress.handle()` now only stores, forwards, and dispatches `action_registry.run(...)`.
- Linear adapter now extracts `payload.labels` and `payload.label_ids` from Linear issue webhook payloads.
- Canary action requires:
  - route mode `production_canary`
  - `LINEAR_CANARY_COMMENT_ENABLED=true`
  - Linear canonical event `issue/updated`
  - canonical payload includes label name `webhook-ingress-canary`
- Title marker alone is no longer sufficient.
- Comment body prefix remains `[webhook-ingress-canary]`.

## Local Tests

Command:

```bash
/Users/busiji/workbot/.venv/bin/python -m pytest /Users/busiji/workbot/tests/test_webhook_ingress.py /Users/busiji/workbot/tests/test_webhook_ingress_server.py
```

Result: `27 passed`.

## Deployment

- Rebuilt `webhook-ingress:phase1-canary` on node-22.
- Recreated Compose service `webhook-ingress`.
- Runtime remained `production_canary`.
- Root-only env file `/opt/n8n-linear/.env.webhook-ingress` preserved DB URL and canary token; Compose config redacted secrets.

## Validation Evidence

### Endpoint exposure

Local gateway checks on node-22:

- `/webhook/events` GET: `405` (POST-only route exists)
- `/webhooks/linear`: `404`
- `/`: `404`
- `/rest/settings`: `404`
- `/healthz`: `200`

### Synthetic validation

Synthetic labeled issue update, no title marker:

- First delivery: `200 accepted`, event `evt_f6e9c279-72f1-475a-b03c-3e69e630c901`
- Replay same delivery id: `200 duplicate_accepted`
- Labeled synthetic action attempted and failed safely because issue id was fake; webhook still returned `200 accepted`.
- Duplicate replay did not forward or execute action again.

Synthetic unlabeled issue update:

- Event `evt_1857507f-08a1-4a9a-8a62-69ea4deebd37`
- Action log: `status=skipped`, `reason=not_labelled_issue_update`

Synthetic logs included required fields:

- `route_name`
- `action_name`
- `target_type`
- `status`
- `canonical_event_id`
- `idempotency_key`

### Real Linear validation

Test label:

- Label: `webhook-ingress-canary`
- Label id: `ef64fb65-fc4b-4e50-ae97-a03a0a2244f3`

Temporary issues:

- Labeled issue: `JTO-184`, id `acf57566-6c1e-4ba4-8383-3db5caf2494c`
- Unlabeled control: `JTO-185`, id `9ac3819b-f36c-4a0b-8726-f7482f922b24`

Observed events:

- `evt_1ae7895f-73ee-4bf6-8c3a-051549093532`: JTO-184 Issue create, label present, skipped because action only runs on update.
- `evt_55156beb-971d-453a-ac70-f6488b355239`: JTO-184 Issue update, label present, one canary comment created.
- `evt_00cc3130-47dd-468c-b649-6959836e50e3`: JTO-185 Issue create, no label, skipped.
- `evt_a679220d-9121-4954-ba27-004a60a86e90`: JTO-185 Issue update, no label, skipped.
- `evt_71205b77-c6ab-455d-ad5b-7dbaa3bc21de`: Comment create from the canary comment, skipped because canonical type is `comment`.

Canary comment evidence:

- Labeled JTO-184 canary comment count: `1`
- Comment id: `94fc5f37-de9b-4849-8f96-8636c9188a9c`
- Body begins: `[webhook-ingress-canary] OPS-LINEAR-009 canonical event evt_55156beb-971d-453a-ac70-f6488b355239 accepted for JTO-184.`
- Unlabeled JTO-185 canary comment count: `0`

Supabase evidence:

- All JTO-184/JTO-185/comment canonical rows had `n8n_forwarded=1`.
- JTO-184 update action log:
  - `route_name=linear.production_canary`
  - `action_name=linear_canary_comment`
  - `target_type=linear_comment_canary`
  - `status=success`
  - `canonical_event_id=evt_55156beb-971d-453a-ac70-f6488b355239`
  - `idempotency_key=linear:b3527168-fb6a-425f-a5d1-78b3c3218f7e`
- JTO-185 update action log:
  - `status=skipped`
  - `reason=not_labelled_issue_update`
  - `target_type=linear_comment_canary`

n8n executions:

- `production canary events` executions `119-125` all `success` during OPS-LINEAR-009 validation window.

Cleanup:

- JTO-184 and JTO-185 archived successfully after validation.

### Redaction

Ingress log scan hits for:

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
- Unlabeled issue did not trigger a canary comment.

## Rollback

One-command dry-run rollback on node-22:

```bash
ssh node-22 'set -euo pipefail
cd /opt/n8n-linear
cp .env .env.bak-ops9-rollback-$(date +%Y%m%d-%H%M%S)
cp .env.webhook-ingress .env.webhook-ingress.bak-ops9-rollback-$(date +%Y%m%d-%H%M%S)
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
