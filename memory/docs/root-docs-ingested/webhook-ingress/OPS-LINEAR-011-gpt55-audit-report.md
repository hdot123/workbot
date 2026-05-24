# OPS-LINEAR-011 GPT-5.5 Evidence Pack Audit Report

Date: 2026-05-04

## Verdict

CONDITIONAL PASS

This audit remains **CONDITIONAL PASS** rather than full PASS because the user explicitly required the audit conclusion to remain conditional, and because two absence categories (Factory/GitLab/Slack remote-side proof) are supported by local/runtime evidence but not by independent remote vendor audit APIs. No code or production configuration was changed during this audit; only read-only config/log/API/SQL checks were used.

## Scope and Guardrails

- Scope: Re-audit OPS-LINEAR-011 evidence pack for JTO-191 Factory Dispatch dry-run.
- Prohibited: code changes, config changes, Linear/GitLab/Factory/Slack triggers.
- Performed: read-only SQL, read-only Linear GraphQL, read-only container logs/config inspection, read-only local git checks.
- Redaction: no token, DB URL, password, Authorization header, or Linear-Signature is included below.

## P0 Issues

### P0-1: `request_path=/webhooks/linear` vs public `/webhook/events`

Status: CLOSED WITH CONFIG + LOG EVIDENCE.

#### Finding

The public gateway route is `/webhook/events`. The nginx gateway internally proxies that route to the ingress app's internal path `/webhooks/linear`. Therefore the Supabase `request_path=/webhooks/linear` is the internal upstream path seen by the ingress app, not evidence of a public `/webhooks/linear` endpoint.

#### Config evidence

Source: node-22 `/opt/n8n-linear/nginx/webhook-gateway.conf` read-only.

```nginx
server {
    listen 8080;
    server_name _;

    location = /healthz {
        proxy_pass http://n8n:5678/healthz;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto https;
    }

    location = /webhook/events {
        proxy_pass http://webhook-ingress-shadow:8000/webhooks/linear;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto https;
    }

    location / {
        return 404;
    }
}
```

Container topology evidence:

```text
n8n-webhook-gateway nginx:1.27-alpine 80/tcp, 127.0.0.1:5678->8080/tcp
webhook-ingress-shadow webhook-ingress:phase1-canary 8000/tcp
cloudflared-webhook cloudflare/cloudflared:latest
```

#### Log evidence

Gateway access logs during the OPS-011 window show external requests hitting `/webhook/events` with the Linear webhook user agent:

```text
172.19.0.1 - - [04/May/2026:11:19:33 +0000] "POST /webhook/events HTTP/1.1" 200 161 "-" "Linear-Webhook" "34.134.222.122"
172.19.0.1 - - [04/May/2026:11:19:41 +0000] "POST /webhook/events HTTP/1.1" 200 161 "-" "Linear-Webhook" "34.134.222.122"
172.19.0.1 - - [04/May/2026:11:20:42 +0000] "POST /webhook/events HTTP/1.1" 200 171 "-" "Linear-Webhook" "34.134.222.122"
```

Prior endpoint checks also show public/internal separation:

```text
GET /webhook/events -> 405
GET /webhooks/linear -> 404
```

#### Conclusion

`/webhook/events` was the public gateway path. `/webhooks/linear` was the internal proxied path used by nginx to reach the ingress app, which explains the Supabase `request_path` field.

### P0-2: Three-table join for same event id

Status: CLOSED.

#### SQL evidence

Read-only SQL:

```sql
select r.event_id,
       r.provider as raw_provider,
       r.request_path,
       r.received_at as raw_received_at,
       r.raw_body_sha256,
       c.provider_action,
       c.canonical_type,
       c.canonical_action,
       c.source_resource_id,
       c.payload->>'identifier' as identifier,
       c.payload->>'state' as state,
       c.payload->>'project_id' as project_id,
       c.n8n_forwarded,
       l.id as log_id,
       l.phase,
       l.message,
       l.details->>'action_name' as action_name,
       l.details->>'target_type' as target_type,
       l.details->>'status' as status,
       l.details ? 'action_result_json' as has_action_result_json
from webhook_raw_events r
join webhook_canonical_events c on c.event_id = r.event_id
join webhook_processing_logs l on l.details->>'canonical_event_id' = r.event_id
where r.event_id = 'evt_3a286207-e1a2-4df2-81f7-762199499804'
order by l.id;
```

Output:

```json
[
  {
    "event_id": "evt_3a286207-e1a2-4df2-81f7-762199499804",
    "raw_provider": "linear",
    "request_path": "/webhooks/linear",
    "raw_received_at": "2026-05-04 11:19:31.042226+00:00",
    "raw_body_sha256": "sha256:57ca29b148112b15a48f99816a9775b24e4424209f6d8c4e059b03c041df8efa",
    "provider_action": "update",
    "canonical_type": "issue",
    "canonical_action": "updated",
    "source_resource_id": "31a38216-a4d2-4601-8d6b-15d47cd7ad11",
    "identifier": "JTO-191",
    "state": "Ready for Factory",
    "project_id": "fe99fb4e-a70a-46f9-b94e-a28ef8e5c666",
    "n8n_forwarded": 1,
    "log_id": 307,
    "phase": "store",
    "message": "raw and canonical event stored",
    "action_name": "save_event",
    "status": "stored",
    "has_action_result_json": false
  },
  {
    "event_id": "evt_3a286207-e1a2-4df2-81f7-762199499804",
    "raw_provider": "linear",
    "request_path": "/webhooks/linear",
    "raw_received_at": "2026-05-04 11:19:31.042226+00:00",
    "raw_body_sha256": "sha256:57ca29b148112b15a48f99816a9775b24e4424209f6d8c4e059b03c041df8efa",
    "provider_action": "update",
    "canonical_type": "issue",
    "canonical_action": "updated",
    "source_resource_id": "31a38216-a4d2-4601-8d6b-15d47cd7ad11",
    "identifier": "JTO-191",
    "state": "Ready for Factory",
    "project_id": "fe99fb4e-a70a-46f9-b94e-a28ef8e5c666",
    "n8n_forwarded": 1,
    "log_id": 308,
    "phase": "canary_forward",
    "message": "canonical event forwarded successfully",
    "action_name": "forward_to_n8n",
    "target_type": "n8n_canary",
    "status": "success",
    "has_action_result_json": false
  },
  {
    "event_id": "evt_3a286207-e1a2-4df2-81f7-762199499804",
    "raw_provider": "linear",
    "request_path": "/webhooks/linear",
    "raw_received_at": "2026-05-04 11:19:31.042226+00:00",
    "raw_body_sha256": "sha256:57ca29b148112b15a48f99816a9775b24e4424209f6d8c4e059b03c041df8efa",
    "provider_action": "update",
    "canonical_type": "issue",
    "canonical_action": "updated",
    "source_resource_id": "31a38216-a4d2-4601-8d6b-15d47cd7ad11",
    "identifier": "JTO-191",
    "state": "Ready for Factory",
    "project_id": "fe99fb4e-a70a-46f9-b94e-a28ef8e5c666",
    "n8n_forwarded": 1,
    "log_id": 309,
    "phase": "canary_action",
    "message": "factory dispatch dry-run payload generated",
    "action_name": "factory_dispatch_dryrun",
    "target_type": "factory_dispatch_dryrun",
    "status": "success",
    "has_action_result_json": true
  }
]
```

#### Conclusion

The same `event_id` links all required facts: raw Linear webhook, canonical JTO-191 `issue.updated` with `Ready for Factory`, and `factory_dispatch_dryrun` processing log with `action_result_json`.

### P0-3: Linear activity/history transition evidence

Status: PARTIALLY CLOSED / RESIDUAL GAP.

#### Direct Linear history query evidence

Read-only Linear query by issue id returned current issue metadata and history nodes:

```json
{
  "issue": {
    "id": "31a38216-a4d2-4601-8d6b-15d47cd7ad11",
    "identifier": "JTO-191",
    "title": "OPS-LINEAR-011 Ready dispatch dry-run final 1777893569",
    "url": "https://linear.app/jtoom/issue/JTO-191/ops-linear-011-ready-dispatch-dry-run-final-1777893569",
    "project_id": "fe99fb4e-a70a-46f9-b94e-a28ef8e5c666",
    "project_name": "Webhook Ingress Canary Project",
    "current_state": {
      "id": "87d293e5-1a6e-436d-8979-41fb0e34826a",
      "name": "Ready for Factory",
      "type": "started"
    },
    "updatedAt": "2026-05-04T11:19:30.002Z",
    "archivedAt": "2026-05-04T11:19:38.266Z"
  },
  "history_nodes": [
    {
      "id": "105222fe-7292-47e9-835b-1dbe08090942",
      "createdAt": "2026-05-04T11:19:38.255Z",
      "fromState": null,
      "toState": null,
      "actor_name": "Ahern li"
    }
  ]
}
```

#### Supplemental canonical lifecycle evidence

Supabase canonical events for issue id `31a38216-a4d2-4601-8d6b-15d47cd7ad11` show:

```json
[
  {
    "event_id": "evt_3a286207-e1a2-4df2-81f7-762199499804",
    "provider_action": "update",
    "canonical_action": "updated",
    "state": "Ready for Factory",
    "received_at": "2026-05-04 11:19:31.042226+00:00"
  },
  {
    "event_id": "evt_d4fb2a6d-9322-43ad-981b-e405c87218a8",
    "provider_action": "create",
    "canonical_action": "created",
    "state": "In Review",
    "received_at": "2026-05-04 11:19:33.260871+00:00"
  },
  {
    "event_id": "evt_b31b4fcf-bfb9-489d-a9b7-2b6550b6e440",
    "provider_action": "remove",
    "canonical_action": "deleted",
    "state": "Ready for Factory",
    "received_at": "2026-05-04 11:19:39.189695+00:00"
  }
]
```

#### Audit interpretation

- Direct Linear issue metadata proves current/archive-time state was `Ready for Factory`, with `updatedAt=2026-05-04T11:19:30.002Z`.
- Supabase canonical webhook proves Linear emitted an `Issue update` webhook for JTO-191 with `state=Ready for Factory` at `2026-05-04 11:19:31.042226+00:00`.
- The GraphQL `history(first:50)` query did **not** expose a state transition from `In Review` to `Ready for Factory`; it returned only an archive-related node with null state fields. Therefore the requested direct `fromState -> toState` evidence is not fully available from this query.

#### Conclusion

This P0 is only partially closed. There is strong event-level proof that JTO-191 was created in `In Review` by the validation script and then updated to `Ready for Factory`, and Linear's current issue metadata confirms Ready state. However, Linear activity/history did not expose the exact `fromState=In Review` to `toState=Ready for Factory` transition. This is the primary reason the verdict remains CONDITIONAL PASS.

### P0-4: External side-effect reverse evidence

Status: CLOSED WITH LOCAL/RUNTIME EVIDENCE; REMOTE VENDOR AUDIT NOT PERFORMED.

#### Source-code evidence

File paths:

- `/Users/busiji/workbot/tools/webhook_ingress/executors.py`
- `/Users/busiji/workbot/tools/webhook_ingress/actions.py`

Dry-run executor evidence:

```python
class FactoryDispatchDryRunExecutor:
    def __init__(self, *, payload_builder: FactoryDispatchPayloadBuilder):
        self.payload_builder = payload_builder

    def execute(self, canonical_event: dict[str, Any]) -> FactoryDispatchDryRunResult:
        return FactoryDispatchDryRunResult(action_result_json=self.payload_builder.build(canonical_event))
```

Action only logs `action_result_json`:

```python
result = self.executor.execute(canonical_event)
_log_action(
    store,
    provider=provider,
    event_id=event_id,
    idempotency_key=idempotency_key,
    action_name=self.name,
    status="success",
    message="factory dispatch dry-run payload generated",
    details={"action_result_json": result.action_result_json},
    project_id=project_id,
    target_type="factory_dispatch_dryrun",
)
```

Conclusion from code: no Factory HTTP call, no GitLab HTTP call, no Slack call, no bailian task creation, no Linear mutation exists in the Factory dry-run executor path.

#### n8n workflow absence evidence

Read-only `workflow_entity` inspection of `production-canary-events` nodes produced:

```json
{
  "contains_slack": false,
  "contains_gitlab": false,
  "contains_factory": false,
  "contains_bailian": false,
  "contains_linear_update_mutation": false
}
```

#### Processing log absence evidence

Read-only aggregate over `webhook_processing_logs` in the validation window `2026-05-04 11:15:00+00` to `2026-05-04 11:25:00+00`:

```json
{
  "slack_mentions": 0,
  "gitlab_mentions": 1,
  "factory_call_mentions": 0,
  "migration_mentions": 0
}
```

The single GitLab mention is not an API call; it is the dry-run policy boolean inside `action_result_json`:

```json
[
  {
    "id": 309,
    "event_id": "evt_3a286207-e1a2-4df2-81f7-762199499804",
    "action_name": "factory_dispatch_dryrun",
    "status": "success",
    "gitlab_required": "true"
  }
]
```

#### Local git evidence for push/merge absence

Read-only local git log/reflog check in the validation window for OPS-LINEAR-011/GitLab/pipeline/Factory/Slack returned no entries:

```text
<no output>
```

#### Conclusion

Local/runtime evidence supports no real Factory dispatch/run/subagent task, no Slack send path, no GitLab execution path, and no Linear status migration path in OPS-011 dry-run. This is strong local evidence, but not a remote vendor-side audit log; keep as CONDITIONAL PASS.

### P0-5: Duplicate/idempotency evidence

Status: CLOSED.

#### Real JTO-191 event counts

Read-only aggregate for real event `evt_3a286207-e1a2-4df2-81f7-762199499804`:

```json
{
  "event_counts": {
    "event_id": "evt_3a286207-e1a2-4df2-81f7-762199499804",
    "idempotency_key": "linear:6f7afa9a-de11-466c-ba2d-464e353de37c",
    "raw_count": 1,
    "canonical_count": 1,
    "dispatch_success_count": 1,
    "action_result_json_count": 1
  },
  "idempotency_log_counts": [
    {
      "idempotency_key": "linear:6f7afa9a-de11-466c-ba2d-464e353de37c",
      "action_name": "factory_dispatch_dryrun",
      "status": "success",
      "count": 1
    },
    {
      "idempotency_key": "linear:6f7afa9a-de11-466c-ba2d-464e353de37c",
      "action_name": "forward_to_n8n",
      "status": "success",
      "count": 1
    },
    {
      "idempotency_key": "linear:6f7afa9a-de11-466c-ba2d-464e353de37c",
      "action_name": "save_event",
      "status": "stored",
      "count": 1
    }
  ]
}
```

#### Synthetic replay evidence

Read-only aggregate for synthetic duplicate replay event `evt_1bf1f665-7f51-4511-9ae3-ff658540daf7`:

```json
{
  "event_id": "evt_1bf1f665-7f51-4511-9ae3-ff658540daf7",
  "idempotency_key": "linear:ops11-synth-ready-b-befd6aa8-2b06-4667-ac6c-8bfd81d9f01c",
  "raw_count": 1,
  "canonical_count": 1,
  "dispatch_success_count": 1,
  "duplicate_log_count": 1
}
```

#### Conclusion

The real JTO-191 event generated exactly one `factory_dispatch_dryrun` success and one `action_result_json`. Synthetic replay evidence demonstrates the duplicate path: same idempotency key produced one duplicate log and did not create a second successful dispatch payload.

## P1 Issues

### P1-1: Evidence pack raw-body marker check can be confusing

The evidence pack says the raw row exists but `raw_mentions_jto191=false` and `raw_mentions_ready=false`. This is not a blocker because Linear raw payload may not contain the key/state as plain text and the canonical row provides normalized linkage. However, the evidence pack should explicitly say the raw proof is by event id/hash/byte length plus canonical join, not by string search.

### P1-2: Remote-side absence evidence remains weaker than local/runtime evidence

No read-only Factory/GitLab/Slack vendor audit endpoints were queried in this audit. Local source/runtime/n8n/log evidence is strong enough for CONDITIONAL PASS, but not enough for a stronger full PASS if the acceptance standard requires independent remote audit logs.

### P1-3: Linear history API did not expose state transition details

The direct history query did not return `fromState`/`toState` for the Ready transition. If a future full PASS is required, use Linear's activity UI screenshot or an alternative Linear audit/history API query that exposes state-change records for archived issues.

## Required Follow-ups Before Full PASS

1. Obtain direct Linear activity/history evidence showing `fromState=In Review` and `toState=Ready for Factory`, or document why Linear history for this archived issue no longer exposes that state transition.
2. If the organization requires stronger external absence proof, collect read-only remote audit outputs from Factory/GitLab/Slack showing no dispatch/run/pipeline/message in `2026-05-04 11:15:00+00` to `11:25:00+00`.
3. Clarify in the evidence pack that `/webhooks/linear` is the internal upstream path set by nginx `proxy_pass`, while `/webhook/events` is the public route.

## Final Audit Conclusion

CONDITIONAL PASS.

The core OPS-LINEAR-011 evidence chain is now substantially stronger: routing is explained by nginx config and gateway logs; raw/canonical/processing logs are joined by one event id; dispatch payload generation is proven; duplicate replay is proven; n8n success is already evidenced in the evidence pack; and local/runtime evidence shows no real Factory/GitLab/Slack/bailian/status-migration side effects. The remaining condition is direct Linear activity/history transition proof, which the read-only GraphQL query did not expose beyond current Ready state plus canonical update webhook evidence.
