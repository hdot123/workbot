# OPS-LINEAR-008 Rollback Plan

> **文档编号**: OPS-LINEAR-008  
> **创建日期**: 2026-05-04  
> **状态**: 预案  
> **维护人**: bailian-worker  
> **关联文档**: OPS-LINEAR-007 (production canary report), OPS-LINEAR-006 (dry-run rollback)

---

## 1. Scope

OPS-LINEAR-008 adds a **Linear comment canary action** to the existing `production-canary-events` n8n workflow. This rollback plan covers:

1. **One-command rollback** to `canary_dryrun` mode if the comment canary action fails or causes unintended side effects.
2. **Disabling the canary workflow / comment action** in n8n.
3. **Preserving** `WEBHOOK_DATABASE_URL` and all existing data.
4. **Optional**: deactivate the `production-canary-events` workflow entirely.

### Assumptions

- node-22 (`root@node-22`) hosts the n8n + webhook-ingress stack at `/opt/n8n-linear`.
- `docker compose` manages `webhook-ingress` and `n8n` services.
- `WEBHOOK_DATABASE_URL` lives in `/opt/n8n-linear/.env.webhook-ingress` (mode 600, root:root).
- `production-canary-events` n8n workflow is the only active canary workflow.
- `canonical-dryrun-events` dry-run workflow remains available for rollback target.

---

## 2. One-command rollback to dry-run

Execute on your local machine (SSH into node-22 internally):

```bash
ssh root@node-22 'set -euo pipefail
cd /opt/n8n-linear

# --- Step 0: backup current .env ---
TS=$(date +%Y%m%d-%H%M%S)
cp .env ".env.bak-rollback-ops-linear-008-${TS}"

# --- Step 1: switch .env to canary_dryrun ---
python3 -c "
from pathlib import Path
p = Path('.env')
lines = p.read_text().splitlines()
updates = {
    'WEBHOOK_INGRESS_MODE': 'canary_dryrun',
    'N8N_CANONICAL_WEBHOOK_URL': 'http://n8n:5678/webhook/canonical-dryrun-events/webhook/canonical-events',
}
out = []
seen = set()
for line in lines:
    key = line.split('=', 1)[0] if '=' in line else ''
    if key in updates:
        out.append(f'{key}={updates[key]}')
        seen.add(key)
    else:
        out.append(line)
for k, v in updates.items():
    if k not in seen:
        out.append(f'{k}={v}')
p.write_text('\n'.join(out) + '\n')
print('env_updated')
"

# --- Step 2: recreate webhook-ingress container ---
docker compose up -d --force-recreate webhook-ingress

# --- Step 3: verify mode ---
sleep 5
docker exec webhook-ingress-shadow python3 -c "
from workspace.tools.webhook_ingress.server import ServerConfig
c = ServerConfig.from_env()
assert c.ingress_mode == 'canary_dryrun', f'expected canary_dryrun, got {c.ingress_mode}'
assert c.database_url, 'WEBHOOK_DATABASE_URL is missing'
print(f'rollback_ok mode={c.ingress_mode} db_url_present=True')
"

echo "=== ROLLBACK COMPLETE ==="
echo "Ingress mode: canary_dryrun"
echo "n8n target: canonical-dryrun-events (dry-run workflow)"
echo "production-canary-events n8n workflow: still active but NOT receiving traffic"
'
```

### What this does

| Step | Effect |
|------|--------|
| Backup `.env` | Timestamped copy for audit |
| Update `WEBHOOK_INGRESS_MODE` | `production_canary` → `canary_dryrun` |
| Update `N8N_CANONICAL_WEBHOOK_URL` | Points to dry-run n8n webhook URL |
| `docker compose up -d --force-recreate` | Rebuilds webhook-ingress with new env |
| Verification assert | Confirms mode is `canary_dryrun` and DB URL present |

### What is preserved

- `WEBHOOK_DATABASE_URL` in `.env.webhook-ingress` — untouched.
- All Supabase data — untouched.
- `production-canary-events` n8n workflow — still active but receives no traffic because ingress routes to dry-run URL.
- `canonical-dryrun-events` n8n workflow — receives all traffic post-rollback.

---

## 3. Disable the canary workflow in n8n (optional)

If you want to deactivate the `production-canary-events` workflow entirely after rollback:

```bash
ssh root@node-22 '
# Deactivate production-canary-events via n8n API
# First, find the workflow ID
WORKFLOW_ID=$(docker exec n8n sqlite3 /home/node/.n8n/database.sqlite \
  "SELECT id FROM workflow_entity WHERE name = '\''production-canary-events'\'' LIMIT 1;")

if [ -z "$WORKFLOW_ID" ]; then
  echo "ERROR: production-canary-events workflow not found"
  exit 1
fi

echo "Deactivating workflow: $WORKFLOW_ID"

docker exec n8n n8n update:workflow \
  --id="$WORKFLOW_ID" \
  --active=false 2>/dev/null || \
curl -s -X PATCH "http://127.0.0.1:5678/api/v1/workflows/$WORKFLOW_ID" \
  -H "Content-Type: application/json" \
  -d "{\"active\": false}"

echo "production-canary-events deactivated"
'
```

> **Note**: The n8n API may require auth credentials. If using Basic Auth, add `-u "<user>:<password>"` to the curl command.

### Alternative: Edit the n8n workflow to remove the comment action

If the comment canary action was added as a specific node (e.g., HTTP Request or Code node), you can edit the workflow JSON to remove it:

```bash
ssh root@node-22 '
# Export the workflow for inspection
WORKFLOW_ID=$(docker exec n8n sqlite3 /home/node/.n8n/database.sqlite \
  "SELECT id FROM workflow_entity WHERE name = '\''production-canary-events'\'' LIMIT 1;")

curl -s "http://127.0.0.1:5678/api/v1/workflows/$WORKFLOW_ID" \
  > /opt/n8n/backups/production-canary-events-pre-ops008-$(date +%Y%m%d-%H%M%S).json

echo "Workflow exported to /opt/n8n/backups/"
echo "Manually edit to remove comment canary node, then re-import."
'
```

---

## 4. Post-rollback verification

Run these checks after rollback:

```bash
# 1. Confirm ingress mode
ssh root@node-22 'docker exec webhook-ingress-shadow python3 -c \
  "from workspace.tools.webhook_ingress.server import ServerConfig; \
   c=ServerConfig.from_env(); print(f\"mode={c.ingress_mode}\")"'
# Expected: mode=canary_dryrun

# 2. Confirm dry-run n8n workflow is receiving events
ssh root@node-22 'docker exec n8n sqlite3 /home/node/.n8n/database.sqlite \
  "SELECT id, startedAt, status FROM execution_entity \
   WHERE workflowId = (SELECT id FROM workflow_entity WHERE name = '\''canonical-dryrun-events'\'' LIMIT 1) \
   ORDER BY startedAt DESC LIMIT 5;"'

# 3. Confirm production-canary-events is NOT receiving new events
ssh root@node-22 'docker exec n8n sqlite3 /home/node/.n8n/database.sqlite \
  "SELECT id, startedAt, status FROM execution_entity \
   WHERE workflowId = (SELECT id FROM workflow_entity WHERE name = '\''production-canary-events'\'' LIMIT 1) \
   AND startedAt > datetime('\''now'\'', '\''-10 minutes'\'');"'
# Expected: no rows

# 4. Confirm Supabase DB URL is still present
ssh root@node-22 'grep -c WEBHOOK_DATABASE_URL /opt/n8n-linear/.env.webhook-ingress'
# Expected: 1

# 5. Health endpoint
curl -sS https://webhook.exa.edu.kg/health | python3 -m json.tool
# Expected: mode=canary_dryrun (or shadow if using /webhooks/linear endpoint)
```

---

## 5. Decision matrix

| Scenario | Action | Severity |
|----------|--------|----------|
| Comment canary produces incorrect output | Section 2 (one-command rollback) | Medium |
| Comment canary makes unintended external API calls | Section 2 + Section 3 (deactivate workflow) | High |
| Comment canary corrupts Supabase data | Section 2 + Section 3 + investigate data | Critical |
| Comment canary causes n8n errors/crashes | Section 2 + Section 3 | High |
| False alarm; want to re-test later | Section 2 is reversible; re-run cutover script | Low |

---

## 6. Emergency nuclear rollback

If the standard rollback fails:

```bash
ssh root@node-22 'set -euo pipefail
cd /opt/n8n-linear

# Restore .env from the OPS-LINEAR-007 rollback backup (which set canary_dryrun)
cp .env .env.bak-emergency-ops008-$(date +%Y%m%d-%H%M%S)

# Manually set the known-good values
python3 -c "
from pathlib import Path
p = Path('.env')
content = p.read_text()
import re
content = re.sub(r'WEBHOOK_INGRESS_MODE=.*', 'WEBHOOK_INGRESS_MODE=canary_dryrun', content)
content = re.sub(r'N8N_CANONICAL_WEBHOOK_URL=.*', 'N8N_CANONICAL_WEBHOOK_URL=http://n8n:5678/webhook/canonical-dryrun-events/webhook/canonical-events', content)
p.write_text(content)
"

docker compose up -d --force-recreate webhook-ingress
sleep 5

# Deactivate production-canary-events if running
docker exec n8n sqlite3 /home/node/.n8n/database.sqlite \
  "UPDATE workflow_entity SET active = 0 WHERE name = '\''production-canary-events'\'';"

echo "EMERGENCY ROLLBACK COMPLETE"
'
```

---

## 7. Post-rollback checklist

- [ ] Run Section 4 verification checks; all pass.
- [ ] Document the rollback reason, timestamp, and evidence.
- [ ] Check Supabase for any anomalous data written during the canary comment action.
- [ ] Verify `production-canary-events` workflow has no new executions after rollback.
- [ ] Verify `canonical-dryrun-events` workflow is receiving events.
- [ ] Notify the team via agreed channel.
- [ ] File a retrospective if the canary comment action failed unexpectedly.

---

## 8. Key file reference

| Resource | Location | Purpose |
|----------|----------|---------|
| Deployment directory | `/opt/n8n-linear/` | docker-compose.yml, .env files |
| Ingress env | `/opt/n8n-linear/.env` | `WEBHOOK_INGRESS_MODE`, `N8N_CANONICAL_WEBHOOK_URL` |
| DB URL (root-only) | `/opt/n8n-linear/.env.webhook-ingress` | `WEBHOOK_DATABASE_URL` (never printed) |
| n8n SQLite DB | `/opt/n8n/data/database.sqlite` | Workflow + execution data |
| n8n backups | `/opt/n8n/backups/` | Workflow JSON exports |
| webhook-ingress container | `webhook-ingress-shadow` | Docker container |
| n8n container | `n8n` | Docker container |

---

**文档状态**: 预案  
**下次评审**: OPS-LINEAR-008 执行前
