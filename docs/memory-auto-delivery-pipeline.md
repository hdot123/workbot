# Memory Auto Delivery Pipeline

This repository now supports end-to-end automation for memory external-core upgrades.

## Flow

1. `memory` repo push to `main` runs tests and auto-creates next `v0.1.x` release tag.
2. `memory` repo dispatches `memory_release_published` event to `workbot`.
3. `workbot` auto-sync workflow updates `EXTERNAL_CORE_RELEASE_REF`.
4. `workbot` runs regression + fail-closed gates.
5. `workbot` auto-commits and pushes the upgrade to `main`.
6. Optional deploy command runs.
7. If deploy fails, `workbot` auto-rolls back and opens an issue.

## Workflows

- `memory`: `.github/workflows/release-and-dispatch.yml`
- `workbot`: `.github/workflows/memory-core-auto-sync-deploy.yml`

## Required secrets/variables

### In `hdot123/memory`

- `WORKBOT_REPO_DISPATCH_TOKEN`
  - PAT with permission to call repository dispatch on `hdot123/workbot`.
  - If empty, release still completes but cross-repo dispatch is skipped.

### In `hdot123/workbot`

- `MEMORY_AUTO_DEPLOY_COMMAND` (Repository Variable, optional)
  - Shell command used for deployment after successful auto-upgrade.
  - Leave empty to disable deployment stage (sync + validation still run).

## Safety gates

- Regression suite:
  - `tests/test_memory_hook_gateway_m6_batch3_provider_switch.py`
  - `tests/test_memory_hook_impls_policy_conflict.py`
  - `tests/test_memory_hook_provider_rollback.py`
  - `tests/test_memory_hook_gateway.py`
  - `tests/test_f8_rollback.py`
- Fail-closed injection must return non-zero for invalid external module.

## Rollback behavior

When deploy stage fails after upgrade commit:

1. Restore previous `EXTERNAL_CORE_RELEASE_REF`.
2. Commit rollback to `main`.
3. Open issue documenting rollback event.
