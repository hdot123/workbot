# M9 ADR: External-Core-Only Governance

Date: 2026-04-16  
Scope: `M9` hardening and decommission phase (`workbot`)

## Context

After `M8`, `external-core` became the default provider. `M9` needs to close migration tail risk by removing transition toggles and enforcing fail-closed behavior when external core cannot load.

## Decision

1. Runtime provider policy is explicit:
- Default provider remains `external-core`.
- `legacy` is only allowed through explicit operator override (`MEMORY_HOOK_CORE_PROVIDER=legacy`).
- Unknown providers are rejected.

2. Transition toggles are retired from active runtime behavior:
- `MEMORY_HOOK_SHADOW_RUN` and related shadow-run output are removed.
- fallback-applied output fields are removed in favor of unified `core_provider_errors`.

3. CI policy is external-core-only:
- workflow: `.github/workflows/memory-hook-external-core-only.yml`
- gate includes regression tests plus fail-closed injection check.

## Operational Guardrails

1. Fail-closed is mandatory when external core load fails.
2. Rollback must be explicit and operator-controlled.
3. Any rollback action must include evidence capture (command, exit code, timestamp).

## Evidence Baseline

- Regression set: `51 passed` on the M9 core suite.
- Fail-closed injection: invalid external module path returns non-zero (`EXIT:1`).
- Cross-validation:
- `rea-bot`: H3/H4 structure and workflow checks passed.
- `qa-bot`: regression + fail-closed injection checks passed.

## Consequences

Benefits:
- Lower silent-degradation risk.
- Clearer provider failure semantics.
- Stronger CI gate aligned with target runtime.

Costs:
- No automatic soft fallback path in default external-core mode.
- Rollback now requires explicit operator action.

## Next Governance Step

Close `M9` only after:
1. Observation window (`H1`) reaches acceptance threshold.
2. Final dual-audit (`H6`) confirms no blocker.
