# OPS-LINEAR-006 Dry-Run Cutover — Rollback Plan

> **文档编号**: OPS-LINEAR-006  
> **创建日期**: 2026-05-04  
> **状态**: 预案  
> **维护人**: bailian-worker  
> **关联文档**: OPS-LINEAR-004 (shadow deployment), OPS-LINEAR-005 (acceptance & monitoring)

---

## 1. Scope and assumptions

### 1.1 What OPS-LINEAR-006 adds

| Component | Change | Path/Name |
|-----------|--------|-----------|
| **n8n** | New dry-run workflow (consumes canonical events, processes without side effects) | `http://127.0.0.1:5678/webhook/linear-canonical-dryrun` |
| **Gateway nginx** | New route `/webhook/linear-canonical-dryrun` → n8n | `/opt/n8n-linear/nginx/webhook-gateway.conf` |
| **webhook_ingress** | Container mode switch from `shadow` to `canary_dryrun` (stores + forwards to dry-run n8n workflow only, NOT to production `/webhook/events`) | Container `webhook-ingress-shadow` (may be renamed) |

### 1.2 What does NOT change

- **Production `/webhook/events` endpoint** — remains active, serving the original Linear production webhook URL. Linear's existing webhook URL stays pointed here.
- **Supabase database** — schema unchanged; new rows continue to be written as before.
- **Cloudflare Tunnel** — no DNS or tunnel changes.

### 1.3 New ingress mode semantics

`WEBHOOK_INGRESS_MODE=canary_dryrun` means:
- `n8n_sender` is NOT `None` (unlike `shadow`)
- `n8n_sender` routes to the dry-run n8n webhook (`/webhook/linear-canonical-dryrun`) via `routes.yaml`
- **Does NOT** route to any production n8n workflow

---

## 2. Rollback strategy overview

Rollback is designed as a **layered approach**: each step undoes one layer of the change, independent of the others. Order matters because removing the gateway route before stopping the service prevents stray requests to a stopped backend.

**Total estimated rollback time**: ~3-5 minutes

---

## 3. Ordered rollback commands

### Step 1 — Stop canary_dryrun forwarding at the ingress layer

Switch webhook_ingress back to `shadow` mode immediately. This is the fastest way to stop any dry-run traffic.

```bash
ssh root@<node-22-ip>

# Option A: If using docker-compose for webhook-ingress
cd /opt/webhook-ingress
# Edit .env or docker-compose.yml to set WEBHOOK_INGRESS_MODE=shadow
sed -i 's/WEBHOOK_INGRESS_MODE=canary_dryrun/WEBHOOK_INGRESS_MODE=shadow/' .env

# Restart to apply
docker compose restart webhook-ingress-shadow

# Verify mode switched
docker exec webhook-ingress-shadow sh -c 'echo $WEBHOOK_INGRESS_MODE'
# Expected: shadow
```

```bash
# Option B: If using docker run directly
docker stop webhook-ingress-shadow
docker rm webhook-ingress-shadow

docker run -d \
  --name webhook-ingress-shadow \
  --network n8n-linear_default \
  -p 127.0.0.1:5680:8000 \
  -e WEBHOOK_INGRESS_MODE=shadow \
  -e LINEAR_WEBHOOK_SECRET=<from-1password> \
  -e WEBHOOK_DATABASE_URL=<from-1password> \
  -e WEBHOOK_LOG_LEVEL=INFO \
  webhook-ingress:phase1
```

### Step 2 — Remove dry-run route from nginx gateway

Remove or disable the `/webhook/linear-canonical-dryrun` location block from the nginx gateway config.

```bash
ssh root@<node-22-ip>
cd /opt/n8n-linear/nginx

# Create a backup of current config before editing
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
cp webhook-gateway.conf webhook-gateway.conf.bak-${TIMESTAMP}-DRYRUN-ROLLBACK

# Edit webhook-gateway.conf to REMOVE the dry-run location block:
#
# Remove this block (or comment it out):
#   location = /webhook/linear-canonical-dryrun {
#       proxy_pass http://127.0.0.1:5678/webhook/linear-canonical-dryrun;
#       ...
#   }
#
# IMPORTANT: Do NOT touch the existing production /webhook/events block
# IMPORTANT: Do NOT touch the existing shadow /webhooks/linear block (if keeping shadow)

# Verify nginx config syntax
docker exec n8n-webhook-gateway nginx -t

# Reload nginx (graceful, zero-downtime)
docker exec n8n-webhook-gateway nginx -s reload

# Verify reload
sleep 1
docker exec n8n-webhook-gateway nginx -t
```

### Step 3 — Disable or delete the dry-run n8n workflow

```bash
ssh root@<node-22-ip>

# Option A: Deactivate the workflow in n8n (non-destructive, easy to re-enable)
# Via n8n API:
curl -s -X PATCH http://127.0.0.1:5678/api/v1/workflows/<DRYRUN-WORKFLOW-ID> \
  -u "<admin-user>:<admin-password>" \
  -H "Content-Type: application/json" \
  -d '{"active": false}' | python3 -m json.tool

# Option B: Delete the workflow entirely (destructive, save workflow JSON first)
# Export workflow for backup:
curl -s http://127.0.0.1:5678/api/v1/workflows/<DRYRUN-WORKFLOW-ID> \
  -u "<admin-user>:<admin-password>" \
  > /opt/n8n/backups/dryrun-workflow-backup-$(date +%Y%m%d_%H%M%S).json

# Then delete:
curl -s -X DELETE http://127.0.0.1:5678/api/v1/workflows/<DRYRUN-WORKFLOW-ID> \
  -u "<admin-user>:<admin-password>"
```

### Step 4 — Revert webhook_ingress routes.yaml (if modified)

If `routes.yaml` was updated to include dry-run routing entries, revert to the previous version.

```bash
# The routes.yaml should still point to standard canonical endpoints.
# If it was modified with dryrun-specific routes, restore from backup:

cp /opt/webhook-ingress/routes.yaml.bak /opt/webhook-ingress/routes.yaml

# Or verify the current routes.yaml does NOT contain dryrun URLs:
grep -i 'dryrun' /opt/webhook-ingress/routes.yaml
# Expected: no matches

# If the service was restarted in Step 1, the routes.yaml is already reloaded.
```

---

## 4. Verification after rollback

Run these checks in order. Each check must pass before proceeding.

### 4.1 Gateway-level verification

```bash
# The dry-run route should return 404 or 502 (no longer proxied)
curl -sS -o /dev/null -w '%{http_code}\n' \
  -X POST https://webhook.exa.edu.kg/webhook/linear-canonical-dryrun
# Expected: 404 (route removed) or 502 (if upstream is gone)

# The production endpoint MUST still work
curl -sS -o /dev/null -w '%{http_code}\n' \
  -X POST https://webhook.exa.edu.kg/webhook/events
# Expected: 200 (unchanged production)

# Health endpoint must still work
curl -sS https://webhook.exa.edu.kg/healthz
# Expected: {"status": "ok", "mode": "shadow"} or similar
```

### 4.2 Ingress mode verification

```bash
# Confirm shadow mode is active
curl -sS https://webhook.exa.edu.kg/healthz | python3 -m json.tool
# Expected: mode field should be "shadow", NOT "canary_dryrun"

# Verify via container env
docker exec webhook-ingress-shadow sh -c 'echo $WEBHOOK_INGRESS_MODE'
# Expected: shadow
```

### 4.3 Production isolation verification

```bash
# Send a test payload to the production endpoint to confirm it still works
# (Use the same Linear HMAC you used during OPS-LINEAR-004 acceptance)

# Send a test payload to the shadow endpoint to confirm it still stores only
curl -sS -X POST https://webhook.exa.edu.kg/webhooks/linear \
  -H "Content-Type: application/json" \
  -H "Linear-Signature: <test-hmac>" \
  -d '{"test": "rollback-verification"}'

# Check n8n logs — there should be NO new executions from the dry-run workflow
docker logs n8n --since "5 minutes ago" 2>&1 | grep -i "linear-canonical-dryrun"
# Expected: no matches (dry-run workflow not triggered)
```

### 4.4 Nginx config verification

```bash
# Confirm the dry-run location block is gone
docker exec n8n-webhook-gateway cat /etc/nginx/conf.d/webhook-gateway.conf \
  | grep -c "linear-canonical-dryrun"
# Expected: 0

# Confirm production block is intact
docker exec n8n-webhook-gateway cat /etc/nginx/conf.d/webhook-gateway.conf \
  | grep -c "/webhook/events"
# Expected: >= 1
```

### 4.5 Database sanity check

```bash
# Verify Supabase rows are still being written (shadow mode continues)
# Connect to Supabase and check recent entries:
# (Use Supabase dashboard or SQL client)
SELECT COUNT(*) FROM webhook_raw_events 
  WHERE created_at > NOW() - INTERVAL '10 minutes';

# Verify no unexpected data from dry-run workflow processing
# (The dry-run workflow should NOT have written any separate tracking tables)
```

---

## 5. Emergency full rollback (nuclear option)

If the layered rollback is insufficient or something unexpected is broken, execute the full rollback to restore the OPS-LINEAR-004 state:

```bash
ssh root@<node-22-ip>

# 1. Stop the ingress container entirely
docker rm -f webhook-ingress-shadow

# 2. Restore nginx from the OPS-LINEAR-004 backup (the one made before any dry-run changes)
cd /opt/n8n-linear/nginx
# List backups to find the right one
ls -la webhook-gateway.conf.bak-*
# Restore the pre-dry-run backup
cp webhook-gateway.conf.bak-<OPS-LINEAR-004-timestamp> webhook-gateway.conf
docker exec n8n-webhook-gateway nginx -t
docker restart n8n-webhook-gateway

# 3. Deactivate the dry-run n8n workflow
curl -s -X PATCH http://127.0.0.1:5678/api/v1/workflows/<DRYRUN-WORKFLOW-ID> \
  -u "<admin-user>:<admin-password>" \
  -H "Content-Type: application/json" \
  -d '{"active": false}'

# 4. Verify production endpoint
curl -sS -o /dev/null -w '%{http_code}\n' \
  -X POST https://webhook.exa.edu.kg/webhook/events
# Expected: 200
```

---

## 6. Rollback decision criteria

| Trigger condition | Action |
|------------------|--------|
| Dry-run workflow processes events incorrectly | Step 1 only (switch to shadow) |
| Dry-run route causes gateway errors | Steps 1 + 2 |
| Dry-run workflow causes data corruption or side effects | Steps 1 + 2 + 3 |
| Unrecoverable error affecting production | Emergency full rollback (Section 5) |
| Dry-run mode works but you want to pause | Step 1 only (shadow mode is the safe resting state) |

---

## 7. Post-rollback checklist

- [ ] Document the rollback reason and timestamp
- [ ] Verify no dry-run n8n executions after rollback
- [ ] Verify shadow mode still accepts and stores events
- [ ] Verify production `/webhook/events` still serves Linear webhooks
- [ ] Check Supabase for any anomalous data from the dry-run period
- [ ] Notify the team of rollback via the agreed channel
- [ ] File a retrospective if the dry-run cutover failed unexpectedly

---

## 8. Appendix: Key file locations reference

| File/Resource | Location | Purpose |
|--------------|----------|---------|
| Gateway nginx config | `/opt/n8n-linear/nginx/webhook-gateway.conf` | Routes webhook traffic |
| Ingress container | `webhook-ingress-shadow` | Docker container on node-22 |
| Ingress env file | `/opt/webhook-ingress/.env` | Mode, secrets, DB URL |
| Routes config | `/opt/webhook-ingress/routes.yaml` or bundled | Provider → n8n routing |
| n8n API | `http://127.0.0.1:5678/api/v1/` | Workflow management |
| n8n data | `/opt/n8n/data/` | SQLite, workflows, executions |
| Gateway backup dir | `/opt/n8n-linear/nginx/` | Timestamped config backups |
| n8n backups | `/opt/n8n/backups/` | Workflow JSON exports |

---

**文档状态**: 预案  
**下次评审**: OPS-LINEAR-006 执行前
