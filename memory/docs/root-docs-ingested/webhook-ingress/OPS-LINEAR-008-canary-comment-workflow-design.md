# OPS-LINEAR-008: n8n Canary Comment Workflow Design

> **Goal**: Design a read-only n8n workflow that creates exactly one Linear comment with prefix `[webhook-ingress-canary]` only for test-scope issues, with full dedup and loop prevention.
>
> **Date**: 2026-05-04
> **Status**: Design (READ-ONLY)
> **Parent**: OPS-LINEAR-007 (production canary)

---

## 1. Architecture Context

### 1.1 Current Canary Topology

```
Linear webhook → POST /webhook/events (public)
              → ingress verifier (signature + idempotency)
              → Supabase (raw + canonical + logs)
              → n8n:5678/webhook/production-canary-events/webhook/canonical-production-canary
              → [Webhook onReceived only - no external calls]
```

### 1.2 Canonical Event Shape (v1)

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
    "resource_id": "JTO-182",
    "resource_url": "https://linear.app/jtoom/issue/JTO-182/..."
  },
  "payload": {
    "id": "c6d2463a-23f7-4212-a8fd-003ade83cf8a",
    "identifier": "JTO-182",
    "title": "ops-linear-007-production-canary-validation-1777885094",
    "description": "...",
    "state": "backlog",
    "url": "https://linear.app/jtoom/issue/JTO-182/..."
  },
  "idempotency_key": "linear:<delivery-id>",
  "raw_body_sha256": "sha256:xxxx"
}
```

### 1.3 Existing Test Issue Pattern

All test issues created during OPS-LINEAR phases follow this pattern:

| Issue | Title Pattern | Phase |
|-------|--------------|-------|
| JTO-177 | test | OPS-LINEAR-003 |
| JTO-179 | shadow-ops-005-real-linear-shadow-validation | OPS-LINEAR-005 |
| JTO-181 | ops-linear-006-final-dry-run-validation | OPS-LINEAR-006 |
| JTO-182 | ops-linear-007-production-canary-validation | OPS-LINEAR-007 |

---

## 2. Test-Scope Identification Strategy

### 2.1 Multi-Layer Guard (Defense in Depth)

The workflow uses THREE independent checks to identify test-scope issues:

```
Layer 1: Title Pattern Match (primary)
Layer 2: Linear Label Check (secondary, requires API call)
Layer 3: Supabase Canary Table Lookup (tertiary, for dedup)
```

**Layer 1: Title Pattern** (no API call needed - uses canonical event data)

Test issue titles match any of these regex patterns:
- `^ops-linear-\d+` - official OPS-LINEAR test issues
- `shadow-ops-\d+` - shadow test issues  
- `^test` - generic test issues
- `canary-validation` - explicit canary validation

**Layer 2: Linear Label** (API call required)

Test issues must have a `webhook-test` or `ops-linear-test` label applied.

**Layer 3: Supabase Canary Tracking** (API call required)

A dedicated table tracks which issues have already received canary comments to prevent duplicates.

### 2.2 Recommended: Label-Based Identification

**Safest approach**: Create a Linear label `webhook-test` and apply it to all test issues.

```graphql
mutation CreateLabel {
  issueLabelCreate(input: {
    teamId: "<team-id>",
    name: "webhook-test",
    color: "#f59e0b",
    description: "Issues created for webhook ingress testing"
  }) {
    success
    issueLabel { id name }
  }
}
```

Then apply to existing test issues:
```graphql
mutation UpdateIssue {
  issueUpdate(id: "JTO-182-id", input: {
    labelIds: ["<webhook-test-label-id>"]
  }) { success }
}
```

**Alternative**: If labels cannot be added immediately, use title pattern matching as the primary guard.

---

## 3. n8n Workflow Node Structure

### 3.1 Complete Node Flow

```
[1. Webhook: /webhook/canary-comment-events/webhook/canary-comment]
          │
          ▼ (onReceived)
[2. Code: Extract Event Data]
          │ Extract: event_id, canonical_type, canonical_action, 
          │          source.resource_id, payload.title, payload.id
          ▼
[3. IF: Is Issue Event?]
          │ canonical_type == "issue" AND canonical_action == "created"
          ├─ NO → [4. Stop: Not an issue creation]
          │
          ▼ YES
[5. IF: Test-Scope Title Match?]
          │ payload.title matches test pattern regex
          ├─ NO → [6. Stop: Not a test issue]
          │
          ▼ YES
[7. Supabase: Check Already Commented?]
          │ SELECT 1 FROM webhook_canary_comments 
          │ WHERE issue_identifier = $resource_id AND status = 'posted'
          ├─ FOUND → [8. Stop: Already commented (dedup)]
          │
          ▼ NOT FOUND
[9. Code: Build Comment Body]
          │ Build: "[webhook-ingress-canary] Event $event_id received 
          │         and validated for $resource_id at $received_at. 
          │         Type: $canonical_type/$canonical_action"
          ▼
[10. HTTP Request: Linear API - POST Comment]
          │ POST https://api.linear.app/graphql
          │ mutation { commentCreate(input: { 
          │   issueId: "$payload.id", 
          │   body: "$comment_body" 
          │ }) { success comment { id } } }
          ▼
[11. IF: Comment Success?]
          ├─ NO → [12. Log Error + Stop]
          │
          ▼ YES
[13. Supabase: Record Comment Posted]
          │ INSERT INTO webhook_canary_comments 
          │ (event_id, issue_identifier, comment_id, status, posted_at)
          ▼
[14. Respond to Webhook: 200]
          │ {"status": "canary_comment_posted", 
          │  "event_id": "...", 
          │  "issue": "JTO-NNN",
          │  "comment_id": "..."}
```

### 3.2 Critical Guard Points

| # | Guard | Purpose | Location |
|---|-------|---------|----------|
| G1 | Issue type check | Only comment on issues, not comments/projects | Node 3 |
| G2 | Created action check | Only comment on new issues, not updates | Node 3 |
| G3 | Title pattern match | Only comment on test-scope issues | Node 5 |
| G4 | Supabase dedup lookup | Never comment twice on same issue | Node 7 |
| G5 | Comment success check | Only record if Linear API succeeds | Node 11 |
| G6 | Supabase record insert | Persistent dedup across workflow restarts | Node 13 |

---

## 4. Exact Workflow JSON Sketch

```json
{
  "name": "canary-comment-events",
  "active": false,
  "nodes": [
    {
      "id": "webhook-trigger",
      "name": "Webhook",
      "type": "n8n-nodes-base.webhook",
      "typeVersion": 2,
      "position": [250, 300],
      "webhookId": "canary-comment-trigger",
      "parameters": {
        "httpMethod": "POST",
        "path": "canary-comment-events",
        "responseMode": "responseNode",
        "options": {}
      }
    },
    {
      "id": "extract-data",
      "name": "Extract Event Data",
      "type": "n8n-nodes-base.code",
      "typeVersion": 2,
      "position": [500, 300],
      "parameters": {
        "mode": "runOnceForAllItems",
        "jsCode": "return $input.all().map(item => {\n  const e = item.json;\n  return {\n    json: {\n      event_id: e.event_id,\n      canonical_type: e.canonical_type,\n      canonical_action: e.canonical_action,\n      resource_id: e.source?.resource_id,\n      issue_id: e.payload?.id,\n      issue_title: e.payload?.title,\n      received_at: e.received_at,\n      idempotency_key: e.idempotency_key\n    }\n  };\n});"
      }
    },
    {
      "id": "is-issue-created",
      "name": "Is Issue Created?",
      "type": "n8n-nodes-base.if",
      "typeVersion": 2,
      "position": [750, 300],
      "parameters": {
        "conditions": {
          "options": { "caseSensitive": true, "leftValue": "", "typeValidation": "strict" },
          "conditions": [
            {
              "id": "c1",
              "leftValue": "={{ $json.canonical_type }}",
              "rightValue": "issue",
              "operator": { "type": "string", "operation": "equals" }
            },
            {
              "id": "c2", 
              "leftValue": "={{ $json.canonical_action }}",
              "rightValue": "created",
              "operator": { "type": "string", "operation": "equals" }
            }
          ],
          "combinator": "AND"
        }
      }
    },
    {
      "id": "is-test-scope",
      "name": "Test-Scope Title Match?",
      "type": "n8n-nodes-base.if",
      "typeVersion": 2,
      "position": [1000, 300],
      "parameters": {
        "conditions": {
          "options": { "caseSensitive": false, "leftValue": "", "typeValidation": "strict" },
          "conditions": [
            {
              "id": "t1",
              "leftValue": "={{ $json.issue_title }}",
              "rightValue": "ops-linear-|shadow-ops-|^test|canary-validation",
              "operator": { "type": "regex", "operation": "regexMatch" }
            }
          ],
          "combinator": "AND"
        }
      }
    },
    {
      "id": "check-dedup",
      "name": "Check Already Commented?",
      "type": "n8n-nodes-base.postgres",
      "typeVersion": 2.4,
      "position": [1250, 300],
      "parameters": {
        "operation": "executeQuery",
        "query": "SELECT 1 FROM webhook_canary_comments WHERE issue_identifier = $1 AND status = 'posted' LIMIT 1",
        "options": {
          "queryParams": "={{ $json.resource_id }}"
        }
      },
      "credentials": {
        "postgres": { "id": "supabase-readonly", "name": "Supabase (canary)" }
      }
    },
    {
      "id": "has-commented-check",
      "name": "Has Already Commented?",
      "type": "n8n-nodes-base.if",
      "typeVersion": 2,
      "position": [1500, 300],
      "parameters": {
        "conditions": {
          "options": { "caseSensitive": true, "leftValue": "", "typeValidation": "strict" },
          "conditions": [
            {
              "id": "d1",
              "leftValue": "={{ $json?.count ?? $input.all().length }}",
              "rightValue": "0",
              "operator": { "type": "number", "operation": "larger" }
            }
          ],
          "combinator": "AND"
        }
      }
    },
    {
      "id": "build-comment",
      "name": "Build Comment Body",
      "type": "n8n-nodes-base.code",
      "typeVersion": 2,
      "position": [1750, 150],
      "parameters": {
        "mode": "runOnceForAllItems",
        "jsCode": "return $input.all().map(item => {\n  const e = item.json;\n  const body = `[webhook-ingress-canary] Event ${e.event_id} received and validated for ${e.resource_id} at ${e.received_at}. Type: ${e.canonical_type}/${e.canonical_action}`;\n  return { json: { ...e, comment_body: body } };\n});"
      }
    },
    {
      "id": "linear-comment-api",
      "name": "Post Linear Comment",
      "type": "n8n-nodes-base.httpRequest",
      "typeVersion": 4.2,
      "position": [2000, 150],
      "parameters": {
        "method": "POST",
        "url": "https://api.linear.app/graphql",
        "authentication": "genericCredentialType",
        "genericAuthType": "httpHeaderAuth",
        "sendBody": true,
        "bodyParameters": {
          "parameters": [
            {
              "name": "query",
              "value": "=mutation { commentCreate(input: { issueId: \"{{ $json.issue_id }}\", body: \"{{ $json.comment_body }}\" }) { success comment { id body } } }"
            }
          ]
        },
        "options": {}
      },
      "credentials": {
        "httpHeaderAuth": { "id": "linear-api-token", "name": "Linear API (canary-comment)" }
      }
    },
    {
      "id": "comment-success-check",
      "name": "Comment Posted OK?",
      "type": "n8n-nodes-base.if",
      "typeVersion": 2,
      "position": [2250, 150],
      "parameters": {
        "conditions": {
          "options": { "caseSensitive": true, "leftValue": "", "typeValidation": "strict" },
          "conditions": [
            {
              "id": "s1",
              "leftValue": "={{ $json.data?.commentCreate?.success }}",
              "rightValue": "true",
              "operator": { "type": "boolean", "operation": "equal" }
            }
          ],
          "combinator": "AND"
        }
      }
    },
    {
      "id": "record-comment",
      "name": "Record Comment Posted",
      "type": "n8n-nodes-base.postgres",
      "typeVersion": 2.4,
      "position": [2500, 150],
      "parameters": {
        "operation": "insert",
        "schema": "public",
        "table": "webhook_canary_comments",
        "columns": "event_id,issue_identifier,comment_id,status,posted_at",
        "options": {}
      },
      "credentials": {
        "postgres": { "id": "supabase-readonly", "name": "Supabase (canary)" }
      }
    },
    {
      "id": "respond-webhook",
      "name": "Respond to Webhook",
      "type": "n8n-nodes-base.respondToWebhook",
      "typeVersion": 1.1,
      "position": [2750, 150],
      "parameters": {
        "respondWith": "json",
        "responseBody": "={{ { status: 'canary_comment_posted', event_id: $json.event_id, issue: $json.resource_id, comment_id: $json.data?.commentCreate?.comment?.id } }}",
        "options": { "responseCode": 200 }
      }
    },
    {
      "id": "respond-notest",
      "name": "Respond (Not Test)",
      "type": "n8n-nodes-base.respondToWebhook",
      "typeVersion": 1.1,
      "position": [1250, 550],
      "parameters": {
        "respondWith": "json",
        "responseBody": "={{ { status: 'skipped', reason: 'not_test_scope', event_id: $json.event_id } }}",
        "options": { "responseCode": 200 }
      }
    },
    {
      "id": "respond-dedup",
      "name": "Respond (Already Commented)",
      "type": "n8n-nodes-base.respondToWebhook",
      "typeVersion": 1.1,
      "position": [1750, 550],
      "parameters": {
        "respondWith": "json",
        "responseBody": "={{ { status: 'skipped', reason: 'already_commented', event_id: $json.event_id, issue: $json.resource_id } }}",
        "options": { "responseCode": 200 }
      }
    }
  ],
  "connections": {
    "Webhook": {
      "main": [[{ "node": "Extract Event Data", "type": "main", "index": 0 }]]
    },
    "Extract Event Data": {
      "main": [[{ "node": "Is Issue Created?", "type": "main", "index": 0 }]]
    },
    "Is Issue Created?": {
      "main": [
        [{ "node": "Test-Scope Title Match?", "type": "main", "index": 0 }],
        [{ "node": "Respond (Not Test)", "type": "main", "index": 0 }]
      ]
    },
    "Test-Scope Title Match?": {
      "main": [
        [{ "node": "Check Already Commented?", "type": "main", "index": 0 }],
        [{ "node": "Respond (Not Test)", "type": "main", "index": 0 }]
      ]
    },
    "Check Already Commented?": {
      "main": [[{ "node": "Has Already Commented?", "type": "main", "index": 0 }]]
    },
    "Has Already Commented?": {
      "main": [
        [{ "node": "Respond (Already Commented)", "type": "main", "index": 0 }],
        [{ "node": "Build Comment Body", "type": "main", "index": 0 }]
      ]
    },
    "Build Comment Body": {
      "main": [[{ "node": "Post Linear Comment", "type": "main", "index": 0 }]]
    },
    "Post Linear Comment": {
      "main": [[{ "node": "Comment Posted OK?", "type": "main", "index": 0 }]]
    },
    "Comment Posted OK?": {
      "main": [
        [{ "node": "Record Comment Posted", "type": "main", "index": 0 }],
        [{ "node": "Respond to Webhook", "type": "main", "index": 0 }]
      ]
    },
    "Record Comment Posted": {
      "main": [[{ "node": "Respond to Webhook", "type": "main", "index": 0 }]]
    }
  },
  "settings": {
    "executionOrder": "v1",
    "saveManualExecutions": true,
    "callerPolicy": "workflowsFromSameOwner",
    "errorWorkflow": "<error-handling-workflow-id>"
  }
}
```

---

## 5. Database Schema: `webhook_canary_comments`

```sql
-- Track which issues have received canary comments (dedup table)
create table if not exists public.webhook_canary_comments (
    id uuid default gen_random_uuid() primary key,
    event_id text not null unique,          -- canonical event that triggered the comment
    issue_identifier text not null,          -- e.g. "JTO-182"
    issue_linear_id text,                    -- Linear issue UUID
    comment_id text unique,                  -- Linear comment UUID
    comment_body text,                       -- Full comment text for audit
    status text not null default 'posted',   -- 'posted', 'failed', 'skipped'
    posted_at timestamptz not null default now(),
    failure_reason text,                     -- If status = 'failed'
    
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

-- Indexes for dedup lookup performance
create index idx_canary_comments_issue on public.webhook_canary_comments(issue_identifier);
create index idx_canary_comments_status on public.webhook_canary_comments(status);
create index idx_canary_comments_event on public.webhook_canary_comments(event_id);

-- RLS
alter table public.webhook_canary_comments enable row level security;

create policy "Allow n8n service role insert" on public.webhook_canary_comments
    for insert to service_role with check (true);

create policy "Allow n8n service role select" on public.webhook_canary_comments
    for select to service_role using (true);

create policy "Allow authenticated select" on public.webhook_canary_comments
    for select to authenticated using (true);
```

---

## 6. Comment Loop Prevention

### 6.1 The Risk

Linear comment events also trigger webhooks. If the workflow comments on an issue, Linear sends a `Comment/create` webhook, which could trigger the workflow again, creating an infinite loop.

### 6.2 Prevention Layers

```
Layer 1: Event Type Filter (Node 3)
  └─ Only processes canonical_type = "issue" AND canonical_action = "created"
  └─ Comment events are canonical_type = "comment" → REJECTED at Node 3

Layer 2: Idempotency at Ingress (existing)
  └─ ingress.py already deduplicates by idempotency_key
  └─ Same Linear delivery ID → duplicate_accepted → no forwarding to n8n

Layer 3: Supabase Dedup Table (Node 7)
  └─ Even if a comment event somehow passes Layer 1, Node 7 checks 
     webhook_canary_comments for the issue
  └─ If already commented → skip

Layer 4: Comment Content Guard (defensive)
  └─ If a comment event somehow passes all layers, the comment body 
     starts with "[webhook-ingress-canary]"
  └─ Add check: if payload.comment.body starts with "[webhook-ingress-canary]", skip
```

### 6.3 Loop Prevention Code (Add to Node 3 or New Node)

```javascript
// Add as first guard after Extract Event Data
// "Is Canary Comment?" guard
const title = $json.issue_title || '';
const body = $json.payload?.body || $json.payload?.description || '';

// Skip if this is our own canary comment
if (body.startsWith('[webhook-ingress-canary]')) {
  return {
    json: {
      ...$json,
      skip_reason: 'canary_comment_loop_prevention',
      should_skip: true
    }
  };
}

// Continue normal processing
return { json: { ...$json, should_skip: false } };
```

---

## 7. Guard Summary Matrix

| Guard | Check Point | What It Prevents | Failure Mode |
|-------|------------|------------------|--------------|
| G1 | Node 3: IF node | Comments on non-issue events | Stops early, 200 response |
| G2 | Node 3: IF node | Comments on issue updates (not creates) | Stops early, 200 response |
| G3 | Node 5: IF node | Comments on production issues | Stops early, 200 response |
| G4 | Node 7: Supabase query | Duplicate comments on same issue | Stops early, 200 response |
| G5 | Node 11: IF node | Recording failed comments | No Supabase insert |
| G6 | Node 13: Supabase insert | Future duplicate comments | Persistent dedup |
| G7 | Ingress idempotency | Replay attacks | duplicate_accepted |
| G8 | Comment content check | Own comment triggering loop | Skip processing |

---

## 8. Activation Steps

### 8.1 Pre-Activation Checklist

- [ ] Create `webhook_canary_comments` table in Supabase
- [ ] Create `webhook-test` label in Linear (optional but recommended)
- [ ] Apply `webhook-test` label to existing test issues (JTO-177, JTO-179, JTO-181, JTO-182)
- [ ] Add Linear API credential to n8n (Header Auth: `Authorization: Bearer lin_api_xxx`)
- [ ] Import workflow JSON into n8n (DO NOT activate yet)
- [ ] Verify workflow is inactive
- [ ] Test with synthetic canonical event for JTO-182

### 8.2 Test Plan

```bash
# Test 1: Test issue creation (should comment)
curl -X POST https://webhook.exa.edu.kg/webhook/events \
  -H "Content-Type: application/json" \
  -H "Linear-Signature: sha256=<calculated>" \
  -H "Linear-Delivery: <uuid>" \
  -d '{
    "type": "Issue",
    "action": "create",
    "data": {
      "id": "test-issue-uuid",
      "identifier": "JTO-TEST-001",
      "title": "ops-linear-008-canary-comment-test",
      "state": { "name": "backlog" }
    }
  }'

# Test 2: Production issue creation (should NOT comment)
# Same payload but title = "Real production bug"
# Expected: skipped, reason: not_test_scope

# Test 3: Replay same event (should NOT comment again)
# Same Linear-Delivery header
# Expected: duplicate_accepted at ingress level

# Test 4: Comment event (should NOT trigger comment)
curl -X POST https://webhook.exa.edu.kg/webhook/events \
  -H "Content-Type: application/json" \
  -H "Linear-Signature: sha256=<calculated>" \
  -H "Linear-Delivery: <uuid>" \
  -d '{
    "type": "Comment",
    "action": "create",
    "data": {
      "id": "comment-uuid",
      "body": "test comment",
      "issue": { "id": "test-issue-uuid", "identifier": "JTO-TEST-001" }
    }
  }'
# Expected: stopped at Node 3 (canonical_type = "comment")

# Test 5: Canary comment content loop (should NOT trigger comment)
# Same as Test 4 but body = "[webhook-ingress-canary] Event evt_xxx..."
# Expected: stopped at G8 (own comment detection)
```

### 8.3 Verification Queries

```sql
-- 1. Check canary comments posted
SELECT event_id, issue_identifier, comment_id, status, posted_at
FROM webhook_canary_comments
ORDER BY posted_at DESC
LIMIT 10;

-- 2. Check for duplicate comments (should be 0)
SELECT issue_identifier, COUNT(*) as comment_count
FROM webhook_canary_comments
WHERE status = 'posted'
GROUP BY issue_identifier
HAVING COUNT(*) > 1;

-- 3. Check for failed comments
SELECT event_id, issue_identifier, failure_reason, posted_at
FROM webhook_canary_comments
WHERE status = 'failed'
ORDER BY posted_at DESC;

-- 4. Cross-reference with canonical events
SELECT ce.event_id, ce.canonical_type, ce.canonical_action, 
       cc.comment_id, cc.status
FROM webhook_canonical_events ce
LEFT JOIN webhook_canary_comments cc ON ce.event_id = cc.event_id
WHERE ce.source->>'resource_id' LIKE 'JTO-%'
ORDER BY ce.created_at DESC
LIMIT 10;
```

---

## 9. Rollback Plan

### 9.1 Immediate Rollback

```bash
# Deactivate the workflow in n8n
ssh root@<node-22-ip>
curl -X PATCH "https://webhook.exa.edu.kg/api/v1/workflows/<canary-comment-workflow-id>" \
  -u "<n8n-admin>:<n8n-password>" \
  -H "Content-Type: application/json" \
  -d '{"active": false}'
```

**Impact**: Zero external side effects. Comments stop being created.

### 9.2 Clean Up Test Comments

```graphql
# Archive or delete canary comments from Linear
# Get comment IDs from webhook_canary_comments table
mutation DeleteComment {
  commentDelete(id: "<comment-id>") { success }
}
```

### 9.3 Full Cleanup

```sql
-- Drop canary comments table (after verification)
DROP TABLE IF EXISTS public.webhook_canary_comments;

-- Delete workflow from n8n
curl -X DELETE "https://webhook.exa.edu.kg/api/v1/workflows/<canary-comment-workflow-id>" \
  -u "<n8n-admin>:<n8n-password>"
```

---

## 10. Safety Guarantees Summary

| Constraint | Guarantee | How |
|------------|-----------|-----|
| Only test-scope issues | ✅ | Title regex match + optional label check |
| Exactly one comment per issue | ✅ | Supabase dedup table + unique constraint |
| No comment loops | ✅ | Event type filter (issue only) + content guard |
| No production impact | ✅ | Guards reject non-test titles immediately |
| No GitLab CI / Slack / bulk updates | ✅ | Workflow has NO nodes for these systems |
| No status changes | ✅ | Workflow only calls `commentCreate` mutation |
| Read-only design | ✅ | This document is read-only; no changes made |
| Idempotent | ✅ | Ingress idempotency + Supabase dedup + Linear unique constraint |
| Rollback safe | ✅ | Single deactivate call; no persistent side effects |

---

## 11. n8n Environment Variables Required

| Variable | Purpose | Example |
|----------|---------|---------|
| `LINEAR_API_TOKEN` | Linear API authentication | `lin_api_xxxxxxxx` |
| `SUPABASE_DB_URL` | Supabase connection for dedup table | `postgresql://...` |
| `CANARY_COMMENT_PREFIX` | Comment prefix (default: `[webhook-ingress-canary]`) | `[webhook-ingress-canary]` |

Add to n8n workflow environment or n8n credentials:

```json
{
  "credentials": {
    "linear-api": {
      "type": "httpHeaderAuth",
      "name": "Linear API (canary-comment)",
      "properties": {
        "name": "Authorization",
        "value": "Bearer lin_api_xxxxxxxx"
      }
    },
    "supabase-canary": {
      "type": "postgres",
      "name": "Supabase (canary)",
      "properties": {
        "host": "db.<project>.supabase.co",
        "port": 5432,
        "database": "postgres",
        "user": "postgres",
        "password": "<password>",
        "ssl": true
      }
    }
  }
}
```

---

## 12. Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Comment on wrong issue | Low | High | Triple guard (title + label + dedup) |
| Infinite comment loop | Very Low | Medium | Event type filter + content guard |
| API token exposure | Low | High | n8n credential storage, not in workflow JSON |
| Duplicate comments | Low | Low | Supabase unique constraint + idempotency |
| Rate limiting from Linear | Low | Low | Only one comment per test issue |
| Workflow activation error | Medium | Low | Start inactive, test manually first |

---

## 13. Implementation Sequence

```
Phase 1: Database Setup (1 hour)
  └─ Create webhook_canary_comments table
  └─ Test insert/select from Supabase

Phase 2: Workflow Import (30 minutes)
  └─ Import workflow JSON into n8n
  └─ Configure credentials (Linear API, Supabase)
  └─ Verify workflow is inactive

Phase 3: Dry-Run Testing (1 hour)
  └─ Send synthetic test issue event
  └─ Verify all guards work correctly
  └─ Check Supabase dedup table

Phase 4: Activation (15 minutes)
  └─ Create test issue with proper title
  └─ Activate workflow
  └─ Verify comment is created
  └─ Verify dedup works (replay same event)

Phase 5: Monitoring (ongoing)
  └─ Monitor webhook_canary_comments table
  └─ Check n8n execution logs
  └─ Verify no comments on production issues
```

---

**Document Status**: Design Complete  
**Next Step**: Create OPS-LINEAR-008 implementation task with this design as reference  
**Reviewer**: TBD
