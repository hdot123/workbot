# OPS-LINEAR-010 Acceptance Report

Date: 2026-05-04

## Scope

Extend controlled Linear canary comment scope from OPS-LINEAR-009 label range to one explicit Linear test Project: `Webhook Ingress Canary Project`.

## Implementation

- Public ingress unchanged: `POST https://webhook.exa.edu.kg/webhook/events`.
- Public `/webhooks/linear` remains disabled at gateway level.
- No second Linear webhook was added.
- No GitLab CI, Slack production notification, bulk Linear update, or issue status migration was enabled.
- ActionRegistry / Executor architecture preserved:
  - `WebhookIngress.handle()` still only verifies, normalizes, stores, forwards, then dispatches `action_registry.run(...)`.
  - Project scope logic stays in `LinearCanaryCommentAction`.
  - Linear API side effect stays in `LinearCanaryCommentExecutor`.
- Linear adapter now extracts project fields:
  - `source.project_id`
  - `source.team_id`
  - `payload.project_id`
  - `payload.project_name`
  - `payload.project_url`
- Runtime project whitelist uses root-only env:
  - `LINEAR_CANARY_ALLOWED_PROJECT_IDS=fe99fb4e-a70a-46f9-b94e-a28ef8e5c666`
- Canary action requires:
  - route mode `production_canary`
  - `LINEAR_CANARY_COMMENT_ENABLED=true`
  - Linear canonical event `issue/updated`
  - issue project id is in `LINEAR_CANARY_ALLOWED_PROJECT_IDS`
- Similar title or label outside this project is ignored.
- Comment body prefix remains `[webhook-ingress-canary]`.

## Local Tests

Command:

```bash
/Users/busiji/workbot/.venv/bin/python -m pytest /Users/busiji/workbot/tests/test_webhook_ingress.py /Users/busiji/workbot/tests/test_webhook_ingress_server.py
```

Result: `30 passed`.

## Deployment

- Rebuilt `webhook-ingress:phase1-canary` on node-22.
- Recreated Compose service `webhook-ingress`.
- Runtime remained `production_canary`.
- Added project whitelist to `/opt/n8n-linear/.env.webhook-ingress` with `600 root:root` permissions.

## Validation Evidence

### Endpoint exposure

Local gateway checks on node-22:

- `/webhook/events` GET: `405` (POST-only route exists)
- `/webhooks/linear`: `404`
- `/`: `404`
- `/rest/settings`: `404`
- `/healthz`: `200`

### Test project

- Project name: `Webhook Ingress Canary Project`
- Project id: `fe99fb4e-a70a-46f9-b94e-a28ef8e5c666`
- Project URL: `https://linear.app/jtoom/project/webhook-ingress-canary-project-5158901098bf`

### Synthetic validation

Synthetic in-project issue update:

- First delivery: `200 accepted`, event `evt_120f9fab-359a-4a88-9031-fe19453db034`
- Replay same delivery id: `200 duplicate_accepted`
- Fake issue id caused safe Linear API error but webhook still returned `200 accepted`.
- Duplicate replay did not forward or execute action again.

Synthetic out-of-project issue update:

- Event `evt_d126b713-8037-4de2-bfed-8055fe6874ef`
- Action log: skipped as `not_project_scoped_issue_update`.

### Real Linear validation

Temporary issues:

- In-project issue: `JTO-186`, id `e7086d17-1b7a-4192-b627-0066c7f777f3`
- Out-of-project control issue: `JTO-187`, id `99953ecb-5213-4392-a07a-230081f6b5a5`

Observed events:

- `evt_cf2e1197-ff08-4f7a-914a-e17d90214db1`: JTO-186 Issue create, project present, skipped because action only runs on update.
- `evt_a14c3ee5-09fc-482b-bea9-4eb963ea1fe6`: JTO-186 Issue update, project matched, one canary comment created.
- `evt_c961a971-3325-4fd1-a299-be22e5cd8489`: JTO-187 Issue create, no project, skipped.
- `evt_26e917e5-b5a3-4780-a4bb-944963253595`: JTO-187 Issue update, no project, skipped.
- `evt_d57f101e-c600-4299-ac61-b159e0ab838e`: Comment create from canary comment, skipped because canonical type is `comment`.

Canary comment evidence:

- In-project JTO-186 canary comment count: `1`
- Comment id: `d0f50b5d-312a-4967-b17d-1a48f9ed97e5`
- Body begins: `[webhook-ingress-canary] OPS-LINEAR-010 canonical event evt_a14c3ee5-09fc-482b-bea9-4eb963ea1fe6 accepted for JTO-186.`
- Out-of-project JTO-187 canary comment count: `0`

Supabase evidence:

- All JTO-186/JTO-187/comment canonical rows had `n8n_forwarded=1`.
- JTO-186 update canonical row included:
  - `payload.project_id=fe99fb4e-a70a-46f9-b94e-a28ef8e5c666`
  - `payload.project_name=Webhook Ingress Canary Project`
- JTO-186 update action log included:
  - `route_name=linear.production_canary`
  - `action_name=linear_canary_comment`
  - `target_type=linear_comment_canary`
  - `status=success`
  - `canonical_event_id=evt_a14c3ee5-09fc-482b-bea9-4eb963ea1fe6`
  - `idempotency_key=linear:6eee7403-ae4e-42c0-98de-c0292cb2cb45`
  - `project_id=fe99fb4e-a70a-46f9-b94e-a28ef8e5c666`
- JTO-187 update action log included:
  - `status=skipped`
  - `reason=not_project_scoped_issue_update`
  - `target_type=linear_comment_canary`

n8n executions:

- `production canary events` executions `132-136` were `success` during OPS-LINEAR-010 real validation window.

Cleanup:

- JTO-186 and JTO-187 archived successfully after validation.

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
- Out-of-project issue did not trigger a canary comment.
- Similar title/label outside the project is ignored by project whitelist.

## Rollback to OPS-LINEAR-009 label scope

This rollback removes the Project whitelist while preserving `production_canary`, canary token, DB URL, and label-scope behavior.

```bash
ssh node-22 'set -euo pipefail
cd /opt/n8n-linear
cp .env.webhook-ingress .env.webhook-ingress.bak-ops10-to-ops9-$(date +%Y%m%d-%H%M%S)
python3 - <<"PY"
from pathlib import Path
path = Path(".env.webhook-ingress")
lines = []
for line in path.read_text().splitlines():
    if line.startswith("LINEAR_CANARY_ALLOWED_PROJECT_IDS="):
        continue
    lines.append(line)
if not any(line.startswith("LINEAR_CANARY_COMMENT_ENABLED=") for line in lines):
    lines.append("LINEAR_CANARY_COMMENT_ENABLED=true")
path.write_text("\n".join(lines) + "\n")
PY
chmod 600 .env.webhook-ingress
docker compose up -d --force-recreate webhook-ingress
sleep 5
docker compose ps webhook-ingress
'
```

Emergency dry-run rollback:

```bash
ssh node-22 'set -euo pipefail
cd /opt/n8n-linear
cp .env .env.bak-ops10-dryrun-$(date +%Y%m%d-%H%M%S)
cp .env.webhook-ingress .env.webhook-ingress.bak-ops10-dryrun-$(date +%Y%m%d-%H%M%S)
python3 - <<"PY"
from pathlib import Path
for path in (Path(".env"), Path(".env.webhook-ingress")):
    lines = []
    for line in path.read_text().splitlines():
        if line.startswith("WEBHOOK_INGRESS_MODE="):
            lines.append("WEBHOOK_INGRESS_MODE=canary_dryrun")
        elif line.startswith("N8N_CANONICAL_WEBHOOK_URL="):
            lines.append("N8N_CANONICAL_WEBHOOK_URL=http://n8n:5678/webhook/canonical-dryrun-events/webhook/canonical-events")
        elif line.startswith("LINEAR_CANARY_COMMENT_ENABLED="):
            lines.append("LINEAR_CANARY_COMMENT_ENABLED=false")
        elif line.startswith("LINEAR_CANARY_API_TOKEN=") or line.startswith("LINEAR_CANARY_ALLOWED_PROJECT_IDS="):
            continue
        else:
            lines.append(line)
    path.write_text("\n".join(lines) + "\n")
PY
chmod 600 .env.webhook-ingress
docker compose up -d --force-recreate webhook-ingress
sleep 5
docker compose ps webhook-ingress
'
```
