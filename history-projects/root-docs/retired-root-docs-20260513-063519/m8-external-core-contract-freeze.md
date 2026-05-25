# M8 External-Core Contract Freeze

Date: 2026-04-16
Owner: dev-bot
Scope: `workbot` consumer contract for memory external-core cutover.

## 1) Frozen Public Contracts

The following contracts are frozen for M8 cutover and must remain backward-compatible through M9:

1. `workspace/tools/memory_hook_interfaces.py`
2. `workspace/tools/memory_hook_core.py::build_context_package_core(...)`
3. `workspace/tools/memory_hook_gateway.py::build_context_package(...)`
4. `workspace/tools/memory_hook_provider_rollback.py::run_rollback_drill()`

## 2) Runtime Provider Contract

Default provider policy for M8 (updated by M9 fail-closed policy):

1. `DEFAULT_CORE_PROVIDER = external-core`
2. `EXTERNAL_CORE_DEFAULT_MODULE = memory_hook_core`
3. `EXTERNAL_CORE_RELEASE_REF = hdot123/memory@v0.1.0`

Runtime fields emitted by gateway (frozen keys):

1. `system_context.core_provider`
2. `system_context.core_provider_requested`
3. `system_context.core_provider_module`
4. `system_context.core_provider_release_ref`
5. `system_context.core_provider_errors` (when provider resolve fails)
6. `system_context.core_provider_manual_rollback_required` (when external-core load fails)

## 3) Compatibility Matrix

| Consumer (`workbot`) | External core source | Expected result |
| --- | --- | --- |
| `M8` | `memory_hook_core` (installed package) | `external-core` loaded directly |
| `M9` | external module unavailable | fail-closed (`status=degraded`), manual rollback required |

## 4) Rollback Contract

`workspace/tools/memory_hook_provider_rollback.py` pass criteria are frozen as:

1. `external_probe_ok == true`
2. `legacy_probe_ok == true`
3. `status == passed`

## 5) Non-Goals in M8

1. Remove `legacy` implementation.
2. Enforce external-only policy in production.
3. Remove compatibility fallback modules. (done in M9 H3)

Those are M9 scope.
