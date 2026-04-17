# Workbot cmux P10-core Delivery

Date: 2026-04-17  
Scope: `P10-core`

## Current Board State

GitHub Project `workbot cmux Phase 0-4 Execution Plan` currently shows both Phase 0 cards as `Todo`:

- `[Phase 0] P10-core Dispatch gate contract`
- `[Phase 0] P12-core Commander semantics core`

Evidence source:

- `gh project item-list 8 --owner hdot123 --format json`

## P10-core Acceptance Map

### 1. assignment-before-dispatch is enforced

- `/Users/busiji/.agents/skills/cmux/scripts/bootstrap_claude_runtime.py`
  `bootstrap()` calls `sync_assignment_file(...)` before launching agent surfaces.
- `/Users/busiji/.agents/skills/cmux/scripts/bootstrap_claude_runtime.py`
  `validate_dispatch_ready_payload(...)` is called before `launch_claude_agent(...)`.

### 2. dispatch_ready, dispatch_blockers, strict_identity_status are explicit pre-start gates

- `/Users/busiji/.agents/skills/cmux/scripts/generate_cmux_assignments.py`
  emits:
  - `dispatch_blockers`
  - `dispatch_ready`
  - `strict_identity_blockers`
  - `strict_identity_status`
- `/Users/busiji/workbot/workspace/artifacts/cmux-runtime/cmux-assignment.json`
  already contains concrete runtime samples for those fields.

### 3. bootstrap must not bypass dispatch gates

- `/Users/busiji/.agents/skills/cmux/scripts/bootstrap_claude_runtime.py`
  `validate_dispatch_ready_payload(...)` raises on active assignments with failed pre-launch dispatch gates.

### 4. runtime health checks align with dispatch gating

- `/Users/busiji/.agents/skills/cmux/scripts/watch_cmux_assignments.py`
  `validate_active_assignments_ready(...)` rejects active assignments that lack task allocation or runtime refs.
- `/Users/busiji/.agents/skills/cmux/scripts/watch_cmux_assignments.py`
  `validate_derived_identity_contract(...)` enforces assignment/mode/dispatch owner consistency before normal monitoring proceeds.

## Repo Artifact Added by This Delivery

- `/Users/busiji/workbot/docs/project-management/workbot-cmux-p10-core-delivery-2026-04-17.md`
