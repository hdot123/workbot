# OPS-LINEAR-011 Evidence Pack

Date: 2026-05-04

Scope: read-only evidence collection for JTO-191 Factory Dispatch dry-run. No production configuration or data was intentionally modified during this evidence collection. All command outputs below are redacted: no token, DB URL, password, Authorization header, or Linear-Signature is included.

## 1. Linear JTO-191 entered Ready for Factory

Evidence source: read-only Linear GraphQL query by immutable issue id `31a38216-a4d2-4601-8d6b-15d47cd7ad11`.

```json
{
  "identifier": "JTO-191",
  "title": "OPS-LINEAR-011 Ready dispatch dry-run final 1777893569",
  "state_name": "Ready for Factory",
  "state_type": "started",
  "state_id": "87d293e5-1a6e-436d-8979-41fb0e34826a",
  "project_id": "fe99fb4e-a70a-46f9-b94e-a28ef8e5c666",
  "project_name": "Webhook Ingress Canary Project",
  "team_key": "JTO",
  "archived_at": "2026-05-04T11:19:38.266Z",
  "updated_at": "2026-05-04T11:19:30.002Z",
  "created_at": "2026-05-04T11:19:29.597Z",
  "url": "https://linear.app/jtoom/issue/JTO-191/ops-linear-011-ready-dispatch-dry-run-final-1777893569"
}
```

Conclusion: JTO-191's Linear state evidence shows `state_name=Ready for Factory` before it was archived as cleanup.

## 2. Supabase `webhook_raw_events` stored the Linear raw webhook event

Evidence source: read-only SQL against `webhook_raw_events` for event `evt_3a286207-e1a2-4df2-81f7-762199499804`.

```sql
select event_id, provider, idempotency_key, raw_body_sha256, request_path, source_ip, received_at,
       octet_length(raw_body) as raw_bytes
from webhook_raw_events
where event_id='evt_3a286207-e1a2-4df2-81f7-762199499804';
```

```json
{
  "event_id": "evt_3a286207-e1a2-4df2-81f7-762199499804",
  "provider": "linear",
  "idempotency_key": "linear:6f7afa9a-de11-466c-ba2d-464e353de37c",
  "raw_body_sha256": "sha256:57ca29b148112b15a48f99816a9775b24e4424209f6d8c4e059b03c041df8efa",
  "request_path": "/webhooks/linear",
  "source_ip": "172.19.0.3",
  "received_at": "2026-05-04 11:19:31.042226+00:00",
  "raw_bytes": 2354
}
```

Additional raw-body marker check was intentionally boolean-only to avoid dumping full provider payload:

```json
{
  "event_id": "evt_3a286207-e1a2-4df2-81f7-762199499804",
  "raw_mentions_issue_id": false,
  "raw_mentions_ready": false,
  "raw_mentions_identifier": false
}
```

Conclusion: the raw Linear webhook event is durably present by event id, provider, idempotency key, request path, body hash, body byte length, and receive timestamp. The raw provider body did not include the issue key/state as plain text, so canonical linkage below is the normalized proof for JTO-191.

## 3. Supabase `webhook_canonical_events` stored canonical JTO-191 events

Evidence source: read-only SQL against `webhook_canonical_events` by JTO-191 source resource id / identifier.

```sql
select event_id, canonical_version, provider, provider_event_type, provider_action,
       canonical_type, canonical_action, source_resource_id, source_resource_url,
       payload->>'identifier' as identifier, payload->>'state' as state,
       payload->>'project_id' as project_id, payload->>'project_name' as project_name,
       n8n_forwarded, received_at
from webhook_canonical_events
where event_id='evt_3a286207-e1a2-4df2-81f7-762199499804'
   or source_resource_id='31a38216-a4d2-4601-8d6b-15d47cd7ad11'
   or payload->>'identifier'='JTO-191'
order by id;
```

Canonical Ready update row:

```json
{
  "event_id": "evt_3a286207-e1a2-4df2-81f7-762199499804",
  "canonical_version": "v1",
  "provider": "linear",
  "provider_event_type": "Issue",
  "provider_action": "update",
  "canonical_type": "issue",
  "canonical_action": "updated",
  "source_resource_id": "31a38216-a4d2-4601-8d6b-15d47cd7ad11",
  "source_resource_url": "https://linear.app/jtoom/issue/JTO-191/ops-linear-011-ready-dispatch-dry-run-final-1777893569",
  "identifier": "JTO-191",
  "state": "Ready for Factory",
  "project_id": "fe99fb4e-a70a-46f9-b94e-a28ef8e5c666",
  "project_name": "Webhook Ingress Canary Project",
  "n8n_forwarded": 1,
  "received_at": "2026-05-04 11:19:31.042226+00:00"
}
```

Related lifecycle rows also existed and were not dispatch-triggering:

```json
[
  {
    "event_id": "evt_d4fb2a6d-9322-43ad-981b-e405c87218a8",
    "provider_action": "create",
    "canonical_action": "created",
    "identifier": "JTO-191",
    "state": "In Review",
    "n8n_forwarded": 1
  },
  {
    "event_id": "evt_b31b4fcf-bfb9-489d-a9b7-2b6550b6e440",
    "provider_action": "remove",
    "canonical_action": "deleted",
    "identifier": "JTO-191",
    "state": "Ready for Factory",
    "n8n_forwarded": 1
  }
]
```

Conclusion: JTO-191 was normalized to canonical v1 events, including the decisive `issue updated` event in the canary project with `state=Ready for Factory`.

## 4. Supabase `webhook_processing_logs` generated Factory Dispatch dry-run payload

Evidence source: read-only SQL against `webhook_processing_logs` for canonical event `evt_3a286207-e1a2-4df2-81f7-762199499804`.

```sql
select id, event_id, provider, phase, level, message, created_at,
       details->>'route_name' as route_name,
       details->>'action_name' as action_name,
       details->>'target_type' as target_type,
       details->>'status' as status,
       details->>'canonical_event_id' as canonical_event_id,
       details->>'idempotency_key' as idempotency_key,
       details->>'project_id' as project_id,
       details ? 'action_result_json' as has_action_result_json
from webhook_processing_logs
where details->>'canonical_event_id'='evt_3a286207-e1a2-4df2-81f7-762199499804'
order by id;
```

```json
[
  {
    "id": 307,
    "event_id": "evt_3a286207-e1a2-4df2-81f7-762199499804",
    "provider": "linear",
    "phase": "store",
    "level": "INFO",
    "message": "raw and canonical event stored",
    "created_at": "2026-05-04 11:19:31.739560+00:00",
    "action_name": "save_event",
    "status": "stored",
    "canonical_event_id": "evt_3a286207-e1a2-4df2-81f7-762199499804",
    "idempotency_key": "linear:6f7afa9a-de11-466c-ba2d-464e353de37c",
    "has_action_result_json": false
  },
  {
    "id": 308,
    "event_id": "evt_3a286207-e1a2-4df2-81f7-762199499804",
    "provider": "linear",
    "phase": "canary_forward",
    "level": "INFO",
    "message": "canonical event forwarded successfully",
    "created_at": "2026-05-04 11:19:32.546219+00:00",
    "route_name": "linear.production_canary",
    "action_name": "forward_to_n8n",
    "target_type": "n8n_canary",
    "status": "success",
    "canonical_event_id": "evt_3a286207-e1a2-4df2-81f7-762199499804",
    "idempotency_key": "linear:6f7afa9a-de11-466c-ba2d-464e353de37c",
    "has_action_result_json": false
  },
  {
    "id": 309,
    "event_id": "evt_3a286207-e1a2-4df2-81f7-762199499804",
    "provider": "linear",
    "phase": "canary_action",
    "level": "INFO",
    "message": "factory dispatch dry-run payload generated",
    "created_at": "2026-05-04 11:19:32.930035+00:00",
    "route_name": "linear.production_canary",
    "action_name": "factory_dispatch_dryrun",
    "target_type": "factory_dispatch_dryrun",
    "status": "success",
    "canonical_event_id": "evt_3a286207-e1a2-4df2-81f7-762199499804",
    "idempotency_key": "linear:6f7afa9a-de11-466c-ba2d-464e353de37c",
    "project_id": "fe99fb4e-a70a-46f9-b94e-a28ef8e5c666",
    "has_action_result_json": true
  }
]
```

Conclusion: processing logs show storage, n8n canary forwarding, and Factory Dispatch dry-run payload generation for JTO-191's Ready update.

## 5. Exported `action_result_json` field check

Evidence source: read-only SQL extracting `details->'action_result_json'` from log id 309 / event `evt_3a286207-e1a2-4df2-81f7-762199499804`.

```json
{
  "dispatch_mode": "dry_run",
  "dispatch_type": "factory_main_thread",
  "dispatch_id": "disp_8304dc82-8aac-4c9a-9831-30e1cd52a47e",
  "linear_issue_key": "JTO-191",
  "linear_issue_id": "31a38216-a4d2-4601-8d6b-15d47cd7ad11",
  "project_id": "fe99fb4e-a70a-46f9-b94e-a28ef8e5c666",
  "repo": "busiji/workbot",
  "target_branch": "branch-2",
  "min_bailian_agents": 1,
  "max_bailian_agents": 10,
  "required_review_agents": 1,
  "ci_required": true,
  "gitlab_required": true,
  "has_main_thread_policy": true,
  "has_subagent_policy": true,
  "has_acceptance_policy": true,
  "has_ci_policy": true,
  "has_loop_guard_policy": true,
  "main_thread_policy": {
    "responsibilities": ["understand_goal", "decompose_tasks", "dispatch_subagents", "supervise", "summarize", "final_acceptance"],
    "must_not_implement_code": true,
    "must_summarize_after_subagents": true
  },
  "subagent_policy": {
    "recommended_split": ["development", "tests", "security", "documentation", "acceptance_audit"],
    "max_bailian_agents": 10,
    "min_bailian_agents": 1,
    "required_review_agents": 1,
    "implementation_by_bailian_only": true
  },
  "acceptance_policy": {
    "gitlab_ci_must_pass": true,
    "review_subagent_must_report": "PASS_or_FAIL",
    "linear_acceptance_criteria_required": true
  },
  "ci_policy": {
    "gitlab_ci_is_machine_gate": true,
    "do_not_mark_done_when_ci_fails": true,
    "generate_fix_dispatch_on_ci_failure": true
  },
  "loop_guard_policy": {
    "max_auto_fix_attempts_per_issue": 3,
    "comment_created_does_not_dispatch": true,
    "duplicate_webhook_not_redispatched": true,
    "same_failure_hash_not_redispatched": true
  }
}
```

Required field conclusion:

- `dispatch_mode=dry_run`: present.
- `dispatch_type=factory_main_thread`: present.
- `min_bailian_agents=1`: present.
- `max_bailian_agents=10`: present.
- `required_review_agents=1`: present.
- `main_thread_policy`: present.
- `subagent_policy`: present.
- `acceptance_policy`: present.
- `ci_policy`: present.
- `loop_guard_policy`: present.

## 6. n8n `production-canary-events` executions 156-161 success

Evidence source: read-only SQL against `n8n-linear-postgres` `execution_entity`.

```sql
select e.id,e.status,e."startedAt",e."stoppedAt",e."workflowId"
from execution_entity e
where e."workflowId"=$$production-canary-events$$
  and e.id between 156 and 161
order by e.id;
```

```text
156|success|2026-05-04 19:17:12.69+08|2026-05-04 19:17:12.699+08|production-canary-events
157|success|2026-05-04 19:17:14.932+08|2026-05-04 19:17:14.942+08|production-canary-events
158|success|2026-05-04 19:17:17.176+08|2026-05-04 19:17:17.182+08|production-canary-events
159|success|2026-05-04 19:19:32.093+08|2026-05-04 19:19:32.103+08|production-canary-events
160|success|2026-05-04 19:19:34.298+08|2026-05-04 19:19:34.304+08|production-canary-events
161|success|2026-05-04 19:19:40.225+08|2026-05-04 19:19:40.231+08|production-canary-events
```

Conclusion: all requested n8n executions 156-161 finished with `success`.

## 7. Evidence of no Factory/GitLab/Slack real side effects, no real bailian task, no Linear status migration

### 7.1 Runtime/source evidence: dry-run executor has no network call

File path evidence:

- `/Users/busiji/workbot/workspace/tools/webhook_ingress/executors.py`
- `/Users/busiji/workbot/workspace/tools/webhook_ingress/actions.py`

Relevant code evidence:

```python
class FactoryDispatchDryRunExecutor:
    def __init__(self, *, payload_builder: FactoryDispatchPayloadBuilder):
        self.payload_builder = payload_builder

    def execute(self, canonical_event: dict[str, Any]) -> FactoryDispatchDryRunResult:
        return FactoryDispatchDryRunResult(action_result_json=self.payload_builder.build(canonical_event))
```

```python
result = self.executor.execute(canonical_event)
_log_action(
    ...,
    action_name=self.name,
    status="success",
    message="factory dispatch dry-run payload generated",
    details={"action_result_json": result.action_result_json},
    target_type="factory_dispatch_dryrun",
)
```

Conclusion: the Factory action executor builds a payload and returns it; it does not contain HTTP client code, Factory API calls, GitLab API calls, Slack calls, bailian creation calls, or Linear mutation calls.

### 7.2 Processing-log aggregate absence evidence

Evidence source: read-only aggregate SQL over processing logs since the OPS-011 validation window.

```json
{
  "slack_mentions": 0,
  "gitlab_mentions": 3,
  "factory_call_mentions": 0,
  "migration_mentions": 0
}
```

The three GitLab mentions were classified by read-only row inspection as dry-run policy booleans only:

```json
[
  {"id": 233, "action_result_json.gitlab_required": "true"},
  {"id": 250, "action_result_json.gitlab_required": "true"},
  {"id": 309, "action_result_json.gitlab_required": "true"}
]
```

Conclusion: logs show no Slack mention, no Factory API/call marker, and no status/state migration marker. GitLab only appears as `gitlab_required=true` inside dry-run payload policy, not as an API call result.

### 7.3 Runtime config after validation

Evidence source: redacted runtime config summary from `.env.webhook-ingress`; values only, no secrets.

```json
{
  "FACTORY_DISPATCH_DRYRUN_ENABLED": "false",
  "LINEAR_CANARY_COMMENT_ENABLED": "true",
  "FACTORY_DISPATCH_ALLOWED_PROJECT_IDS": "fe99fb4e-a70a-46f9-b94e-a28ef8e5c666",
  "FACTORY_DISPATCH_REPO": "busiji/workbot",
  "FACTORY_DISPATCH_TARGET_BRANCH": "branch-2"
}
```

Conclusion: validation runtime was rolled back to OPS-010 comment canary after OPS-011, with Factory dry-run disabled.

## 8. Secret redaction evidence

Evidence source: read-only `docker logs webhook-ingress-shadow` sensitive-pattern scan; the command counted matches and did not print any matching log lines.

Patterns checked:

```text
lin_api_|Authorization:|postgres(ql)?://|Linear-Signature:|WEBHOOK_DATABASE_URL|LINEAR_CANARY_API_TOKEN|FACTORY.*TOKEN|GITLAB.*TOKEN|SLACK.*TOKEN|password
```

Output:

```text
0
```

Conclusion: evidence collection output and ingress logs did not expose token, DB URL, password, Authorization, or Linear-Signature patterns.

## 9. Evidence collection files

Temporary local collector script path:

- `/Users/busiji/workbot/workspace/memory/tmp/ops11_evidence_collect.py`

Acceptance report reference:

- `/Users/busiji/workbot/docs/webhook-ingress/OPS-LINEAR-011-acceptance-report.md`

Final evidence pack path:

- `/Users/busiji/workbot/docs/webhook-ingress/OPS-LINEAR-011-evidence-pack.md`

## 10. Overall conclusion

OPS-LINEAR-011 evidence pack is complete:

- Linear shows JTO-191 reached `Ready for Factory`.
- Supabase raw event exists for the decisive webhook event id.
- Supabase canonical event exists and identifies JTO-191 as `issue updated` in the canary project with `state=Ready for Factory`.
- Supabase processing log id 309 generated `factory_dispatch_dryrun` with `action_result_json`.
- The exported action result contains all required dispatch and policy fields.
- n8n executions 156-161 are all `success`.
- Evidence supports no real Factory/GitLab/Slack/bailian/Linear-status-migration side effects beyond dry-run payload generation.
- No secret material is included in this evidence pack.
