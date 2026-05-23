# OPS-LINEAR-011 Acceptance Report

Date: 2026-05-04

## Scope

Factory main-thread Dispatch dry-run for Linear issues in `Webhook Ingress Canary Project` when state is `Ready for Factory`.

No Factory API call, no real Factory long task, no real bailian subagent creation, no GitLab/Slack/status migration/bulk update was implemented or executed.

## Implementation

- Added `FactoryDispatchPayloadBuilder`.
- Added `FactoryDispatchDryRunExecutor` with pure payload construction only.
- Added `FactoryDispatchDryRunAction` through `ActionRegistry`.
- Added Linear state/project extraction in canonical payload.
- Added processing log payload under `details.action_result_json`.
- Added env controls:
  - `FACTORY_DISPATCH_DRYRUN_ENABLED`
  - `FACTORY_DISPATCH_ALLOWED_PROJECT_IDS`
  - `FACTORY_DISPATCH_READY_STATE_NAMES`
  - `FACTORY_DISPATCH_REPO`
  - `FACTORY_DISPATCH_TARGET_BRANCH`

## Validation Evidence

### Local Tests

`/Users/busiji/workbot/.venv/bin/python -m pytest /Users/busiji/workbot/tests/test_webhook_ingress.py /Users/busiji/workbot/tests/test_webhook_ingress_server.py`

Result: `34 passed`.

### Endpoint Contract

Local gateway checks on node-22:

- `/webhook/events` -> `405` for GET; POST remains the canonical webhook route.
- `/webhooks/linear` -> `404`.
- `/` -> `404`.
- `/rest/settings` -> `404`.
- `/healthz` -> `200`.

### Synthetic Webhooks

Fresh synthetic event ids:

- In-project Ready: `evt_1bf1f665-7f51-4511-9ae3-ff658540daf7`.
- Out-of-project Ready: `evt_f8debc22-ed04-41c4-90ca-335a51193ce0`.
- In-project non-Ready: `evt_0dfa2997-6a48-4c17-815c-1960511ab23a`.
- Comment created: `evt_43a6887a-90d9-4751-862b-d22bbfa85a2f`.

Results:

- In-project Ready generated exactly one `factory_dispatch_dryrun` success log with `details.action_result_json`.
- Duplicate delivery returned `duplicate_accepted` and did not generate a second payload.
- Out-of-project Ready skipped; no payload.
- In-project non-Ready skipped; no payload.
- Comment created skipped; no payload.
- Required log fields present: `route_name`, `action_name`, `target_type=factory_dispatch_dryrun`, `status`, `canonical_event_id`, `idempotency_key`, `project_id`.

Payload evidence for in-project Ready included:

- `dispatch_mode=dry_run`
- `dispatch_type=factory_main_thread`
- `repo=busiji/workbot`
- `target_branch=branch-2`
- `max_bailian_agents=10`
- `min_bailian_agents=1`
- `required_review_agents=1`
- `gitlab_required=true`
- `ci_required=true`
- main-thread/subagent/acceptance/CI/loop-guard policy blocks.

### Real Linear Validation

Temporary validation setup:

- Project id: `fe99fb4e-a70a-46f9-b94e-a28ef8e5c666`.
- Team id: `62318e54-d65f-42bd-8d31-7a1f0e146cae`.
- `Ready for Factory` state did not exist, so a test workflow state was created: `87d293e5-1a6e-436d-8979-41fb0e34826a`.

Real issues:

- JTO-188/JTO-189/JTO-190: initial real controls used before adapting to Linear's omission of `updatedFrom.state`; archived.
- JTO-191: final in-project Ready validation issue; archived.

Final accepted real event:

- JTO-191 Ready update event: `evt_3a286207-e1a2-4df2-81f7-762199499804`.
- Supabase canonical row: `issue updated`, `state=Ready for Factory`, `project_id=fe99fb4e-a70a-46f9-b94e-a28ef8e5c666`, `n8n_forwarded=1`.
- Processing log: `factory dispatch dry-run payload generated`, `status=success`, `action_name=factory_dispatch_dryrun`, `target_type=factory_dispatch_dryrun`, payload present.

Real negative controls:

- Out-of-project Ready control JTO-189 skipped; no payload.
- In-project non-Ready control JTO-190 skipped; no payload.
- Comment-created validation comment on JTO-188 skipped; no payload.
- Created/deleted/archive events skipped; no payload.

### n8n

Recent `production-canary-events` executions after OPS-011 validation were success:

- 161 success
- 160 success
- 159 success
- 158 success
- 157 success
- 156 success

### Redaction

Ingress log sensitive-pattern scan hits: `0`.

Patterns checked included Linear tokens, Authorization headers, postgres URLs, Linear signatures, Factory/GitLab token strings, and explicit secret env names.

## Runtime Rollback

Runtime was returned to OPS-010 Project comment canary state after validation:

- `FACTORY_DISPATCH_DRYRUN_ENABLED=false`
- `LINEAR_CANARY_COMMENT_ENABLED=true`
- `LINEAR_CANARY_ALLOWED_PROJECT_IDS=fe99fb4e-a70a-46f9-b94e-a28ef8e5c666`

Rollback command shape:

```bash
cd /opt/n8n-linear
# set FACTORY_DISPATCH_DRYRUN_ENABLED=false
# set LINEAR_CANARY_COMMENT_ENABLED=true
docker compose up -d --force-recreate webhook-ingress
```

## Acceptance

Accepted.

OPS-LINEAR-011 demonstrated Factory main-thread Dispatch dry-run payload generation for project-scoped Ready issues with durable Supabase evidence, no duplicate payloads, n8n success, no secret leakage, and no real Factory/GitLab/Slack/subagent side effects.
