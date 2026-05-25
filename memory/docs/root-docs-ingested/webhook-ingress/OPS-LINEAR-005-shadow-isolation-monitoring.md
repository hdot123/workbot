# Shadow Ingress Isolation Monitoring Checks

> **Goal**: Prove that shadow `/webhooks/linear` does **not** trigger production n8n business workflows.  
> **Date**: 2026-05-04  
> **Status**: Baseline — read-only queries, no modifications required.

---

## Architecture Summary

| Endpoint | Route | Target | n8n Forwarding |
|----------|-------|--------|----------------|
| Production | `POST /webhook/events` | `n8n:5678` (existing webhook) | Yes (direct) |
| Shadow | `POST /webhooks/linear` | `webhook-ingress-shadow:8000` → Supabase | **No** (`WEBHOOK_INGRESS_MODE=shadow`, `n8n_sender=None`) |

In shadow mode, `server.py` line `_make_n8n_sender()` is never called, so `ingress.py` `WebhookIngress.handle()` always returns `forwarded_to_n8n=False`.

---

## Check 1: n8n Container Logs — No Canonical Webhook Hits

**Principle**: If shadow ingress leaked through to n8n, n8n would log HTTP requests to its canonical-event webhook endpoints defined in `routes.yaml`:

- `/webhook/canonical-events` (default)
- `/webhook/linear-issue-created`
- `/webhook/linear-issue-updated`
- `/webhook/linear-comment-events`

**Command** (SSH to node-22):

```bash
# Check n8n container logs for any hits to canonical webhook endpoints
# Replace <n8n-container-name> with actual container name (likely "n8n" or "n8n-linear-n8n-1")
docker logs --since 1h <n8n-container-name> 2>&1 \
  | grep -iE "canonical-events|linear-issue-created|linear-issue-updated|linear-comment"

# If shadow is isolated, this should return ZERO lines.
# Any non-zero count indicates shadow → n8n forwarding is active (bug or misconfiguration).
```

**Interpretation**:
- **Empty result** ✅ → Shadow is properly isolated; no canonical webhook traffic reached n8n.
- **Any matches** ❌ → Shadow is forwarding to n8n. Investigate `WEBHOOK_INGRESS_MODE` env var on the shadow container.

---

## Check 2: n8n Executions Table — No Canonical Event Executions

**Principle**: n8n stores all workflow executions in its SQLite database. If shadow triggered n8n, execution records would appear for workflows listening on the canonical webhook paths.

**Command** (SSH to node-22):

```bash
# Enter the n8n container
docker exec -it <n8n-container-name> sh

# Query n8n SQLite database for executions matching canonical webhook paths
sqlite3 /home/node/.n8n/database.sqlite <<'SQL'
SELECT
  id,
  workflowId,
  startedAt,
  stoppedAt,
  status
FROM execution_entity
WHERE startedAt >= datetime('now', '-24 hours')
  AND (
    workflowId IN (
      SELECT workflowId FROM execution_data
      WHERE data LIKE '%canonical-events%'
         OR data LIKE '%linear-issue-created%'
         OR data LIKE '%linear-issue-updated%'
         OR data LIKE '%linear-comment-events%'
    )
  )
ORDER BY startedAt DESC
LIMIT 50;
SQL
```

**Interpretation**:
- **Empty result** ✅ → No n8n executions were triggered by canonical webhook routes in the last 24h.
- **Results with timestamps matching shadow test activity** ❌ → Shadow ingress is triggering n8n workflows.

**Note**: The existing production webhook `/webhook/events` will still create executions, but they will be for the **original n8n workflow ID** (not the canonical-event workflows). Distinguish by `workflowId`.

---

## Check 3: Shadow Container Logs — Confirm n8n Sender Is None

**Principle**: In shadow mode, the server startup log should confirm `n8n_sender` is disabled.

**Command** (SSH to node-22):

```bash
docker logs webhook-ingress-shadow 2>&1 | grep -iE "mode|sender|n8n|forward"
```

**Expected output** (shadow mode):

```
webhook_ingress starting mode=shadow
webhook_ingress ready
```

**If live mode** (should NOT appear in shadow):

```
forwarded to n8n url=http://127.0.0.1:5678/webhook/...
```

**Interpretation**:
- **Only `mode=shadow` and `ready`** ✅ → Shadow container is correctly configured.
- **Any `forwarded to n8n` lines** ❌ → Shadow is forwarding; check env var `WEBHOOK_INGRESS_MODE`.

---

## Check 4: Shadow Container Env Var Verification

**Principle**: Confirm the runtime environment variable is set to `shadow`.

**Command** (SSH to node-22):

```bash
docker exec webhook-ingress-shadow env | grep WEBHOOK_INGRESS_MODE
```

**Expected output**:

```
WEBHOOK_INGRESS_MODE=shadow
```

**Interpretation**:
- **`shadow`** ✅ → Correct isolation mode.
- **`live` or missing** ❌ → Shadow would forward to n8n; requires immediate fix.

---

## Check 5: End-to-End Fire Test — Send Test Payload to Shadow

**Principle**: Send a known test payload to the shadow endpoint, then verify (a) it was stored in Supabase, and (b) it did NOT appear in n8n executions.

**Commands** (from any machine with network access to `webhook.exa.edu.kg`):

```bash
# Step 5a: Send a known test payload to shadow endpoint
TEST_ID="shadow-isolation-test-$(date +%s)"

curl -sS -X POST https://webhook.exa.edu.kg/webhooks/linear \
  -H "Content-Type: application/json" \
  -H "X-Linear-Signature: $(echo -n '{"test":"'$TEST_ID'"}' | openssl dgst -sha256 -hmac "$LINEAR_WEBHOOK_SECRET" -binary | xxd -p)" \
  -d '{"action":"create","type":"Issue","data":{"id":"'$TEST_ID'","title":"Shadow Isolation Test","description":"Verify shadow does not forward to n8n"}}'

# Expected response: {"ok":true,"status":"accepted","request_id":"req_...","event_id":"evt_..."}

# Step 5b: Wait 5 seconds
sleep 5

# Step 5c: Verify Supabase received the event (shadow stores to Supabase)
# Replace with actual Supabase query
curl -sS "https://rxrcidmnbyvwmhxqdgku.supabase.co/rest/v1/webhook_raw_events?id=eq.$TEST_ID" \
  -H "apikey: <supabase-anon-key>" \
  -H "Authorization: Bearer <supabase-service-role-key>"

# Step 5d: Verify n8n did NOT receive the event (run on node-22)
docker logs --since 1m <n8n-container-name> 2>&1 \
  | grep -c "$TEST_ID"
```

**Interpretation**:
- **Step 5a returns 200 accepted** ✅ → Shadow endpoint received the payload.
- **Step 5c returns 1 row** ✅ → Shadow correctly stored to Supabase.
- **Step 5d returns 0** ✅ → Shadow did **not** forward to n8n. **ISOLATION CONFIRMED.**
- **Step 5d returns >0** ❌ → Shadow forwarded the event to n8n. **ISOLATION BROKEN.**

---

## Check 6: Production Endpoint Still Active — Confirm No Impact

**Principle**: Verify the production `/webhook/events` endpoint still works independently and is not affected by shadow.

**Command** (from any machine):

```bash
# Send a test to the production endpoint
PROD_TEST_ID="prod-test-$(date +%s)"
curl -sS -X POST https://webhook.exa.edu.kg/webhook/events \
  -H "Content-Type: application/json" \
  -H "X-Linear-Signature: <valid-hmac>" \
  -d '{"action":"create","type":"Issue","data":{"id":"'$PROD_TEST_ID'","title":"Prod Endpoint Test"}}'

# Expected: 200 from the existing n8n workflow
# Verify in n8n logs that this execution was for the ORIGINAL workflow, not canonical routes
docker logs --since 1m <n8n-container-name> 2>&1 | grep "$PROD_TEST_ID"
```

**Interpretation**:
- **200 from n8n** ✅ → Production webhook path is unaffected.
- **The execution appears under the original n8n workflow ID** ✅ → Production is routing correctly.

---

## Check 7: Nginx Routing Verification

**Principle**: Confirm nginx is routing the two paths to different backends.

**Command** (SSH to node-22):

```bash
# Check the nginx gateway configuration
cat /opt/n8n-linear/nginx/webhook-gateway.conf \
  | grep -A3 "location.*webhook"
```

**Expected output**:

```nginx
location = /webhook/events {
    proxy_pass http://n8n:5678;          # Production → n8n
    ...
}
location = /webhooks/linear {
    proxy_pass http://webhook-ingress-shadow:8000/webhooks/linear;  # Shadow → shadow service
    ...
}
```

**Interpretation**:
- **Two separate location blocks, two separate upstreams** ✅ → Correct routing isolation.
- **Only one location block or same upstream** ❌ → Routing misconfiguration.

---

## Monitoring Script (Automated Periodic Check)

```bash
#!/bin/bash
# /opt/n8n/shadow-isolation-check.sh
# Run via cron every 15 minutes: */15 * * * * /opt/n8n/shadow-isolation-check.sh

set -euo pipefail

N8N_CONTAINER="n8n"
SHADOW_CONTAINER="webhook-ingress-shadow"
LOG_FILE="/var/log/shadow-isolation.log"
ALERT_EMAIL="alerts@exa.edu.kg"

echo "=== $(date -u +%Y-%m-%dT%H:%M:%SZ) Shadow Isolation Check ===" >> "$LOG_FILE"

# Check 1: Shadow mode env var
MODE=$(docker exec "$SHADOW_CONTAINER" env | grep WEBHOOK_INGRESS_MODE | cut -d= -f2)
if [ "$MODE" != "shadow" ]; then
    echo "CRITICAL: WEBHOOK_INGRESS_MODE=$MODE (expected: shadow)" >> "$LOG_FILE"
    echo "CRITICAL: Shadow container mode=$MODE" | mail -s "Shadow Isolation Alert" "$ALERT_EMAIL"
    exit 1
fi

# Check 2: No canonical webhook hits in last 15 minutes
CANONICAL_HITS=$(docker logs --since 15m "$N8N_CONTAINER" 2>&1 \
  | grep -cE "canonical-events|linear-issue-created|linear-issue-updated|linear-comment" || true)

if [ "$CANONICAL_HITS" -gt 0 ]; then
    echo "WARNING: $CANONICAL_HITS canonical webhook hits in last 15m" >> "$LOG_FILE"
    echo "WARNING: $CANONICAL_HITS canonical webhook hits detected" | mail -s "Shadow Isolation Alert" "$ALERT_EMAIL"
    exit 1
fi

# Check 3: No n8n forwarding logs from shadow
FORWARD_HITS=$(docker logs --since 15m "$SHADOW_CONTAINER" 2>&1 \
  | grep -c "forwarded to n8n" || true)

if [ "$FORWARD_HITS" -gt 0 ]; then
    echo "CRITICAL: $FORWARD_HITS n8n forward events from shadow" >> "$LOG_FILE"
    echo "CRITICAL: Shadow forwarded $FORWARD_HITS events to n8n" | mail -s "Shadow Isolation Alert" "$ALERT_EMAIL"
    exit 1
fi

echo "OK: Shadow isolation verified" >> "$LOG_FILE"
exit 0
```

---

## Key Distinguishing Signals

| Signal | Production (`/webhook/events`) | Shadow (`/webhooks/linear`) |
|--------|-------------------------------|----------------------------|
| **n8n workflow ID** | Original Linear workflow ID | No execution (shadow mode) |
| **n8n endpoint hit** | Original webhook path | None (shadow mode) |
| **Supabase `webhook_raw_events`** | No row (n8n doesn't write here) | Row inserted |
| **Shadow log `forwarded_to_n8n`** | N/A | Always `false` in shadow mode |
| **HTTP response source** | n8n Webhook node response | FastAPI shadow service |
| **Response format** | n8n execution response | `{"ok":true,"status":"accepted","request_id":"...","event_id":"..."}` |

---

## Rollback Trigger Conditions

If any of these conditions are met, restore the nginx backup and remove the shadow container:

1. `WEBHOOK_INGRESS_MODE != shadow` on the shadow container
2. Canonical webhook paths receive traffic in n8n logs when only shadow endpoint was hit
3. n8n execution count spikes correlating with shadow test traffic
4. `forwarded to n8n` appears in shadow container logs

---

## Notes

- All commands above are **read-only** — they query logs, databases, and configurations without modifying anything.
- Replace `<n8n-container-name>` with the actual container name on node-22.
- Replace `<supabase-anon-key>` and `<supabase-service-role-key>` with actual Supabase credentials from the project.
- Replace `<valid-hmac>` with a properly calculated HMAC-SHA256 using the Linear webhook secret.
- The production `/webhook/events` will continue receiving real Linear events — this is expected and must not be disabled.
