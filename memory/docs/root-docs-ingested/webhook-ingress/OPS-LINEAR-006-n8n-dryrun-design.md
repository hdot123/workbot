# OPS-LINEAR-006: n8n Dry-Run Workflow Design

> **Goal**: Design a safe n8n dry-run workflow that receives canonical events only, produces no external side effects, and leaves the existing production `/webhook/events` workflow completely unchanged.
> 
> **Date**: 2026-05-04  
> **Status**: Design  
> **Parent**: OPS-LINEAR-005 (shadow validation)

---

## 1. Architecture Context

### 1.1 Current Production Topology

```
Linear → POST /webhook/events → n8n:5678/webhook/events  (existing production workflow, UNCHANGED)
       → POST /webhooks/linear → webhook-ingress shadow → Supabase (shadow, no n8n forwarding)
```

### 1.2 Canonical Event Schema

The dry-run workflow accepts **Canonical Webhook Event v1** only:

```json
{
  "canonical_version": "v1",
  "event_id": "evt_xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  "provider": "linear",
  "provider_event_type": "Issue",
  "provider_action": "create",
  "canonical_type": "issue",
  "canonical_action": "created",
  "timestamp": "2026-05-04T10:00:00Z",
  "received_at": "2026-05-04T10:00:01Z",
  "source": {
    "provider": "linear",
    "resource_id": "JTO-179",
    "resource_url": "https://linear.app/exa/issue/JTO-179"
  },
  "payload": { ... },
  "idempotency_key": "linear:xxx",
  "raw_body_sha256": "sha256:xxxx"
}
```

### 1.3 Existing n8n Route Map (from `routes.yaml`)

| Canonical Type | Canonical Action | n8n Webhook URL |
|---|---|---|
| issue | created | `/webhook/linear-issue-created` |
| issue | updated | `/webhook/linear-issue-updated` |
| comment | * | `/webhook/linear-comment-events` |
| default (all others) | * | `/webhook/canonical-events` |

---

## 2. Dry-Run Workflow Design

### 2.1 Design Principles

1. **Read-only**: No writes to Linear, GitLab, Slack, or any external system
2. **No side effects**: No HTTP POST/PUT/DELETE to external APIs
3. **Parallel to production**: Uses its own webhook path; does not modify or disable the existing workflow
4. **Deterministic**: Produces observable output (logs + DB entries) for verification
5. **Safe to activate/deactivate**: Workflow can be toggled on/off without touching anything else

### 2.2 New Webhook Endpoint

| Property | Value |
|---|---|
| **HTTP Method** | POST |
| **Path** | `linear-canonical-dryrun` |
| **Full URL** | `https://webhook.exa.edu.kg/webhook/linear-canonical-dryrun` |
| **Authentication** | None (internal testing only; optional Basic Auth via n8n) |
| **Response Mode** | On Received |
| **Response Code** | 200 |

### 2.3 Workflow Node Structure

```
[Webhook: /webhook/linear-canonical-dryrun]
          │
          ▼
[JSON Schema Validate: Canonical Event v1]
          │
    (valid? → continue, invalid → Stop + log)
          │
          ▼
[Switch: canonical_type + canonical_action]
    ├── issue.created
    ├── issue.updated  
    ├── comment.created
    └── default
          │
          ▼
[Set Node: "Planning Output"]
  - Extract: event_id, canonical_type, canonical_action
  - Extract: source.resource_id
  - Extract: payload.title, payload.description, payload.state
  - Build: dry_run_analysis object
          │
          ▼
[Code Node: Dry-Run Analysis]
  - Log event details to n8n execution log
  - Build read-only analysis:
    * What business action WOULD be taken
    * Which downstream systems WOULD be called (Linear/GitLab/Slack)
    * What data WOULD be written
  - DO NOT call any external API
          │
          ▼
[HTTP Request: Supabase INSERT → webhook_dryrun_events]  ← ONLY safe external write
          │
          ▼
[Respond to Webhook: 200]
  {
    "status": "dry_run_processed",
    "event_id": "...",
    "dry_run_id": "...",
    "analysis": { ... }
  }
```

### 2.4 Exact Workflow JSON Shape

```json
{
  "name": "Linear Canonical Dry-Run",
  "active": false,
  "nodes": [
    {
      "id": "webhook-trigger",
      "name": "Webhook",
      "type": "n8n-nodes-base.webhook",
      "typeVersion": 2,
      "position": [250, 300],
      "webhookId": "linear-canonical-dryrun",
      "parameters": {
        "httpMethod": "POST",
        "path": "linear-canonical-dryrun",
        "responseMode": "responseNode",
        "options": {}
      }
    },
    {
      "id": "validate-schema",
      "name": "Validate Canonical Event v1",
      "type": "n8n-nodes-base.if",
      "typeVersion": 2,
      "position": [500, 300],
      "parameters": {
        "conditions": {
          "options": {
            "caseSensitive": true,
            "leftValue": "",
            "typeValidation": "strict"
          },
          "conditions": [
            {
              "id": "cond-1",
              "leftValue": "={{ $json.canonical_version }}",
              "rightValue": "v1",
              "operator": { "type": "string", "operation": "equals" }
            }
          ],
          "combinator": "AND"
        }
      }
    },
    {
      "id": "switch-type",
      "name": "Route by canonical_type",
      "type": "n8n-nodes-base.switch",
      "typeVersion": 3,
      "position": [750, 300],
      "parameters": {
        "rules": {
          "values": [
            {
              "conditions": {
                "options": { "caseSensitive": true, "leftValue": "", "typeValidation": "strict" },
                "conditions": [
                  { "id": "r1", "leftValue": "={{ $json.canonical_type }}", "rightValue": "issue", "operator": { "type": "string", "operation": "equals" } },
                  { "id": "r2", "leftValue": "={{ $json.canonical_action }}", "rightValue": "created", "operator": { "type": "string", "operation": "equals" } }
                ],
                "combinator": "AND"
              },
              "renameOutput": true,
              "outputKey": "issue.created"
            },
            {
              "conditions": {
                "conditions": [
                  { "leftValue": "={{ $json.canonical_type }}", "rightValue": "issue", "operator": { "type": "string", "operation": "equals" } },
                  { "leftValue": "={{ $json.canonical_action }}", "rightValue": "updated", "operator": { "type": "string", "operation": "equals" } }
                ],
                "combinator": "AND"
              },
              "renameOutput": true,
              "outputKey": "issue.updated"
            },
            {
              "conditions": {
                "conditions": [
                  { "leftValue": "={{ $json.canonical_type }}", "rightValue": "comment", "operator": { "type": "string", "operation": "equals" } }
                ],
                "combinator": "AND"
              },
              "renameOutput": true,
              "outputKey": "comment.*"
            }
          ]
        },
        "options": {}
      }
    },
    {
      "id": "analysis-code",
      "name": "Dry-Run Analysis",
      "type": "n8n-nodes-base.code",
      "typeVersion": 2,
      "position": [1000, 300],
      "parameters": {
        "mode": "runOnceForAllItems",
        "jsCode": "// Dry-run analysis: NO external API calls\nconst items = $input.all();\nconst analysis = items.map(item => {\n  const e = item.json;\n  return {\n    json: {\n      event_id: e.event_id,\n      canonical_version: e.canonical_version,\n      canonical_type: e.canonical_type,\n      canonical_action: e.canonical_action,\n      provider: e.provider,\n      resource_id: e.source?.resource_id,\n      received_at: e.received_at,\n      dry_run_id: `dry_${crypto.randomUUID()}`,\n      analysis: {\n        would_trigger: `${e.canonical_type}.${e.canonical_action} handler`,\n        would_call_external_systems: [],\n        would_write: ['webhook_dryrun_events'],\n        notes: 'Dry-run mode: no external side effects'\n      },\n      payload_summary: {\n        title: e.payload?.title,\n        state: e.payload?.state,\n        description_preview: (e.payload?.description || '').substring(0, 100)\n      }\n    }\n  };\n});\nreturn analysis;"
      }
    },
    {
      "id": "supabase-insert",
      "name": "Insert into webhook_dryrun_events",
      "type": "n8n-nodes-base.postgres",
      "typeVersion": 2.4,
      "position": [1250, 300],
      "parameters": {
        "operation": "insert",
        "schema": "public",
        "table": "webhook_dryrun_events",
        "columns": "event_id,dry_run_id,canonical_type,canonical_action,resource_id,received_at,analysis",
        "options": {}
      },
      "credentials": {
        "postgres": { "id": "supabase-readonly", "name": "Supabase (read-write for dry-run table)" }
      }
    },
    {
      "id": "respond-webhook",
      "name": "Respond to Webhook",
      "type": "n8n-nodes-base.respondToWebhook",
      "typeVersion": 1.1,
      "position": [1500, 300],
      "parameters": {
        "respondWith": "json",
        "responseBody": "={{ $json }}",
        "options": {
          "responseCode": 200
        }
      }
    }
  ],
  "connections": {
    "Webhook": { "main": [[{ "node": "Validate Canonical Event v1", "type": "main", "index": 0 }]] },
    "Validate Canonical Event v1": { "main": [[{ "node": "Route by canonical_type", "type": "main", "index": 0 }]] },
    "Route by canonical_type": { "main": [[{ "node": "Dry-Run Analysis", "type": "main", "index": 0 }]] },
    "Dry-Run Analysis": { "main": [[{ "node": "Insert into webhook_dryrun_events", "type": "main", "index": 0 }]] },
    "Insert into webhook_dryrun_events": { "main": [[{ "node": "Respond to Webhook", "type": "main", "index": 0 }]] }
  },
  "settings": {
    "executionOrder": "v1",
    "saveManualExecutions": true,
    "callerPolicy": "workflowsFromSameOwner"
  }
}
```

---

## 3. Database Schema for Dry-Run Results

### 3.1 `webhook_dryrun_events` Table

Add to Supabase alongside existing `webhook_canonical_events`:

```sql
create table if not exists public.webhook_dryrun_events (
    id uuid default gen_random_uuid() primary key,
    dry_run_id text not null unique,
    event_id text not null,
    canonical_type text not null,
    canonical_action text not null,
    resource_id text,
    received_at timestamptz not null,
    analysis jsonb not null default '{}',
    created_at timestamptz not null default now(),
    
    -- FK to canonical events (optional, for correlation)
    canonical_event_id uuid references public.webhook_canonical_events(id)
);

create index idx_dryrun_event_id on public.webhook_dryrun_events(event_id);
create index idx_dryrun_resource_id on public.webhook_dryrun_events(resource_id);
create index idx_dryrun_created_at on public.webhook_dryrun_events(created_at desc);

-- RLS
alter table public.webhook_dryrun_events enable row level security;

create policy "Allow authenticated insert" on public.webhook_dryrun_events
    for insert to authenticated with check (true);

create policy "Allow authenticated select" on public.webhook_dryrun_events
    for select to authenticated using (true);
```

---

## 4. Activation Steps

### 4.1 Step 1: Import Workflow into n8n

```bash
# Option A: n8n CLI import (if available)
ssh root@<node-22-ip>
docker exec n8n n8n import:workflow \
    --input=/opt/n8n/workflows/linear-canonical-dryrun.json

# Option B: n8n REST API
curl -X POST https://webhook.exa.edu.kg/api/v1/workflows \
    -u "<n8n-admin-user>:<n8n-admin-password>" \
    -H "Content-Type: application/json" \
    -d @linear-canonical-dryrun.json

# Option C: n8n Web UI (manual)
# 1. Login to https://webhook.exa.edu.kg
# 2. Click "Add Workflow" → "Import from File"
# 3. Upload linear-canonical-dryrun.json
# 4. Review nodes and connections
# 5. Save (DO NOT activate yet)
```

### 4.2 Step 2: Add Database Table

```bash
# Connect to Supabase via psql or Supabase dashboard
# Execute the webhook_dryrun_events DDL from Section 3
```

### 4.3 Step 3: Verify Workflow (Inactive)

```bash
# Check workflow is imported but NOT active
curl -s "https://webhook.exa.edu.kg/api/v1/workflows" \
    -u "<n8n-admin-user>:<n8n-admin-password>" \
    | python3 -c "
import sys, json
workflows = json.load(sys.stdin)['data']
dryrun = [w for w in workflows if 'dryrun' in w.get('name', '').lower()]
for w in dryrun:
    print(f\"Name: {w['name']}, Active: {w['active']}, ID: {w['id']}\")"

# Expected output: Active: False
```

### 4.4 Step 4: Send Test Events

```bash
# Test 1: issue.created
curl -sS -X POST https://webhook.exa.edu.kg/webhook/linear-canonical-dryrun \
    -H "Content-Type: application/json" \
    -d '{
        "canonical_version": "v1",
        "event_id": "evt_00000000-0000-0000-0000-000000000001",
        "provider": "linear",
        "provider_event_type": "Issue",
        "provider_action": "create",
        "canonical_type": "issue",
        "canonical_action": "created",
        "timestamp": "2026-05-04T10:00:00Z",
        "received_at": "2026-05-04T10:00:01Z",
        "source": {
            "provider": "linear",
            "resource_id": "DRY-001",
            "resource_url": "https://linear.app/exa/issue/DRY-001"
        },
        "payload": {
            "title": "Dry-run test issue",
            "description": "This is a dry-run test event",
            "state": "backlog"
        },
        "idempotency_key": "linear:dryrun-001",
        "raw_body_sha256": "sha256:0000000000000000000000000000000000000000000000000000000000000000"
    }'

# Expected response:
# {
#   "status": "dry_run_processed",
#   "event_id": "evt_00000000-0000-0000-0000-000000000001",
#   "dry_run_id": "dry_xxxxxxxx-...",
#   "analysis": {
#     "would_trigger": "issue.created handler",
#     "would_call_external_systems": [],
#     "would_write": ["webhook_dryrun_events"],
#     "notes": "Dry-run mode: no external side effects"
#   }
# }
```

### 4.5 Step 5: Activate Workflow

```bash
# Activate via API
DRYRUN_WORKFLOW_ID="<workflow-id-from-step-3>"
curl -X PATCH "https://webhook.exa.edu.kg/api/v1/workflows/$DRYRUN_WORKFLOW_ID" \
    -u "<n8n-admin-user>:<n8n-admin-password>" \
    -H "Content-Type: application/json" \
    -d '{"active": true}'

# Or via n8n UI: Toggle Active = On
```

---

## 5. Verification Checks

### 5.1 SQL Checks

```sql
-- 1. Verify dry-run events were stored
SELECT dry_run_id, event_id, canonical_type, canonical_action, resource_id, created_at
FROM webhook_dryrun_events
ORDER BY created_at DESC
LIMIT 10;

-- 2. Count events by type
SELECT canonical_type, canonical_action, COUNT(*) as count
FROM webhook_dryrun_events
GROUP BY canonical_type, canonical_action
ORDER BY count DESC;

-- 3. Verify NO calls to Linear/GitLab/Slack
--    This dry-run workflow has ZERO HTTP Request nodes to external systems.
--    Confirm by checking the workflow JSON:
--    grep -c "http://api.linear.app\|https://gitlab.com\|https://slack.com" \
--      linear-canonical-dryrun.json
--    Expected: 0

-- 4. Correlate dry-run with canonical events (if FK is populated)
SELECT d.dry_run_id, c.event_id, c.canonical_type, c.canonical_action
FROM webhook_dryrun_events d
LEFT JOIN webhook_canonical_events c ON d.canonical_event_id = c.id
ORDER BY d.created_at DESC
LIMIT 10;
```

### 5.2 Log Checks

```bash
# 1. n8n execution logs for dry-run workflow
ssh root@<node-22-ip>
DRYRUN_WORKFLOW_ID="<workflow-id>"
docker exec n8n sqlite3 /home/node/.n8n/database.sqlite "
SELECT id, workflowId, startedAt, stoppedAt, status
FROM execution_entity
WHERE workflowId = '$DRYRUN_WORKFLOW_ID'
ORDER BY startedAt DESC
LIMIT 10;
"

# 2. Verify no external HTTP calls in execution data
docker exec n8n sqlite3 /home/node/.n8n/database.sqlite "
SELECT id, data
FROM execution_data
WHERE workflowId = '$DRYRUN_WORKFLOW_ID'
AND data LIKE '%linear.app%';
"
# Expected: Empty result (no Linear API calls)

# 3. Check n8n container logs
docker logs --since 10m n8n 2>&1 | grep -i "dryrun\|linear-canonical"
# Should show webhook trigger and execution logs only, no API calls
```

### 5.3 Safety Checks

```bash
# 1. Production workflow still active
curl -s "https://webhook.exa.edu.kg/api/v1/workflows" \
    -u "<n8n-admin-user>:<n8n-admin-password>" \
    | python3 -c "
import sys, json
workflows = json.load(sys.stdin)['data']
prod = [w for w in workflows if 'events' in w.get('name', '').lower() or 'linear' in w.get('name', '').lower()]
for w in prod:
    print(f\"Name: {w['name']}, Active: {w['active']}\")"

# 2. Production endpoint still works
curl -s -X POST https://webhook.exa.edu.kg/webhook/events \
    -H "Content-Type: application/json" \
    -d '{"test": "health_check"}' -o /dev/null -w "%{http_code}\n"
# Expected: 200 (or whatever the existing production behavior is)

# 3. Shadow endpoint still works
curl -s https://webhook.exa.edu.kg/health
# Expected: {"status": "ok", "mode": "shadow"}
```

---

## 6. Rollback Plan

### 6.1 Immediate Rollback (Deactivate Only)

```bash
# Deactivate the dry-run workflow
curl -X PATCH "https://webhook.exa.edu.kg/api/v1/workflows/$DRYRUN_WORKFLOW_ID" \
    -u "<n8n-admin-user>:<n8n-admin-password>" \
    -H "Content-Type: application/json" \
    -d '{"active": false}'
```

**Impact**: Zero. No production workflows affected. Dry-run events stop being processed.

### 6.2 Full Rollback (Delete Workflow)

```bash
# Delete the workflow entirely
curl -X DELETE "https://webhook.exa.edu.kg/api/v1/workflows/$DRYRUN_WORKFLOW_ID" \
    -u "<n8n-admin-user>:<n8n-admin-password>"
```

### 6.3 Cleanup Database

```sql
-- Option 1: Archive dry-run data
ALTER TABLE webhook_dryrun_events RENAME TO webhook_dryrun_events_archived;

-- Option 2: Delete dry-run data
DELETE FROM webhook_dryrun_events WHERE created_at < now() - interval '30 days';

-- Option 3: Drop table entirely
DROP TABLE IF EXISTS webhook_dryrun_events;
```

### 6.4 Rollback Verification

```bash
# Confirm dry-run webhook returns 404 (workflow deactivated/deleted)
curl -s -X POST https://webhook.exa.edu.kg/webhook/linear-canonical-dryrun \
    -H "Content-Type: application/json" \
    -d '{"test": true}' -o /dev/null -w "%{http_code}\n"
# Expected: 404 (if deleted) or 200 with no processing (if deactivated)

# Confirm production is unaffected
curl -s -X POST https://webhook.exa.edu.kg/webhook/events \
    -H "Content-Type: application/json" \
    -d '{"test": true}' -o /dev/null -w "%{http_code}\n"
# Expected: 200 (unchanged)
```

---

## 7. CLI Import Plan

### 7.1 Workflow File Location

```
/opt/n8n/workflows/linear-canonical-dryrun.json
```

### 7.2 Import Script

```bash
#!/bin/bash
# /opt/n8n/scripts/import-dryrun-workflow.sh
set -euo pipefail

N8N_URL="https://webhook.exa.edu.kg"
N8N_USER="${N8N_ADMIN_USER:-admin}"
N8N_PASS="${N8N_ADMIN_PASSWORD:-}"
WORKFLOW_FILE="/opt/n8n/workflows/linear-canonical-dryrun.json"

if [ ! -f "$WORKFLOW_FILE" ]; then
    echo "ERROR: Workflow file not found: $WORKFLOW_FILE"
    exit 1
fi

echo "Importing dry-run workflow..."
RESPONSE=$(curl -s -X POST "$N8N_URL/api/v1/workflows" \
    -u "$N8N_USER:$N8N_PASS" \
    -H "Content-Type: application/json" \
    -d @"$WORKFLOW_FILE")

WORKFLOW_ID=$(echo "$RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['id'])")
echo "Imported workflow ID: $WORKFLOW_ID"

# Verify inactive
ACTIVE=$(echo "$RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['active'])")
if [ "$ACTIVE" = "True" ] || [ "$ACTIVE" = "true" ]; then
    echo "WARNING: Workflow is active! Deactivating..."
    curl -s -X PATCH "$N8N_URL/api/v1/workflows/$WORKFLOW_ID" \
        -u "$N8N_USER:$N8N_PASS" \
        -H "Content-Type: application/json" \
        -d '{"active": false}' > /dev/null
    echo "Deactivated."
fi

echo "Dry-run workflow imported and deactivated. Ready for testing."
```

### 7.3 Verification Script

```bash
#!/bin/bash
# /opt/n8n/scripts/verify-dryrun-workflow.sh
set -euo pipefail

N8N_URL="https://webhook.exa.edu.kg"
N8N_USER="${N8N_ADMIN_USER:-admin}"
N8N_PASS="${N8N_ADMIN_PASSWORD:-}"

echo "=== Dry-Run Workflow Verification ==="
echo ""

# 1. Check workflow exists
echo "1. Checking workflow exists..."
WORKFLOWS=$(curl -s "$N8N_URL/api/v1/workflows" -u "$N8N_USER:$N8N_PASS")
DRYRUN=$(echo "$WORKFLOWS" | python3 -c "
import sys, json
data = json.load(sys.stdin)['data']
dryrun = [w for w in data if 'dryrun' in w.get('name', '').lower()]
if dryrun:
    w = dryrun[0]
    print(f\"ID: {w['id']}\")
    print(f\"Active: {w['active']}\")
    print(f\"CreatedAt: {w['createdAt']}\")
else:
    print('NOT FOUND')
    sys.exit(1)
")
echo "$DRYRUN"
echo ""

# 2. Send test event
echo "2. Sending test event..."
RESPONSE=$(curl -s -X POST "$N8N_URL/webhook/linear-canonical-dryrun" \
    -H "Content-Type: application/json" \
    -d '{
        "canonical_version": "v1",
        "event_id": "evt_00000000-0000-0000-0000-000000000099",
        "provider": "linear",
        "provider_event_type": "Issue",
        "provider_action": "create",
        "canonical_type": "issue",
        "canonical_action": "created",
        "timestamp": "2026-05-04T10:00:00Z",
        "received_at": "2026-05-04T10:00:01Z",
        "source": {"provider": "linear", "resource_id": "DRY-099"},
        "payload": {"title": "Verify test"},
        "idempotency_key": "linear:dryrun-verify-099",
        "raw_body_sha256": "sha256:0000000000000000000000000000000000000000000000000000000000000099"
    }')
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$N8N_URL/webhook/linear-canonical-dryrun" \
    -H "Content-Type: application/json" \
    -d '{"canonical_version":"v1","event_id":"evt_00000000-0000-0000-0000-000000000098","provider":"linear","provider_event_type":"Issue","provider_action":"create","canonical_type":"issue","canonical_action":"created","timestamp":"2026-05-04T10:00:00Z","received_at":"2026-05-04T10:00:01Z","source":{"provider":"linear","resource_id":"DRY-098"},"payload":{"title":"Verify test 2"},"idempotency_key":"linear:dryrun-verify-098","raw_body_sha256":"sha256:0000000000000000000000000000000000000000000000000000000000000098"}')
echo "HTTP Status: $HTTP_CODE"
echo "Response: $RESPONSE"
echo ""

# 3. Check Supabase
echo "3. Checking Supabase webhook_dryrun_events table..."
echo "   Run: SELECT COUNT(*) FROM webhook_dryrun_events;"
echo ""

echo "=== Verification Complete ==="
```

---

## 8. Safety Guarantees Summary

| Constraint | Guarantee | How |
|---|---|---|
| No Linear API calls | ✅ | Workflow contains zero HTTP Request nodes to `api.linear.app` |
| No GitLab API calls | ✅ | Workflow contains zero HTTP Request nodes to GitLab |
| No Slack API calls | ✅ | Workflow contains zero HTTP Request nodes to Slack |
| Production unchanged | ✅ | Separate webhook path; separate workflow; no shared state |
| Read-only planning | ✅ | Only reads canonical event, writes to `webhook_dryrun_events` table |
| Safe to activate | ✅ | Workflow starts deactivated; manual activation required |
| Safe to deactivate | ✅ | Single API call or UI toggle; no side effects |
| Deterministic output | ✅ | Always writes to `webhook_dryrun_events` with `dry_run_id` |

---

## 9. Next Steps (for OPS-LINEAR-007+)

1. **Populate dry-run events** from shadow Supabase data to simulate production load
2. **Add analysis logic** in the Code node to model what production workflows would do
3. **Compare dry-run results** against expected production behavior
4. **Promote to production** only after dry-run validation passes all criteria
