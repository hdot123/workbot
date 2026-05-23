# M9 SOP: External-Core Incident & Rollback

Date: 2026-04-16  
Owner: runtime operator (main-thread / on-duty maintainer)

## Purpose

Provide a deterministic runbook for `external-core` load failures under M9 fail-closed policy.

## Trigger Conditions

Run this SOP when any of the following occurs:

1. `memory_hook_gateway.py` exits non-zero with external-core load error.
2. CI fail-closed step reports external-core load failure.
3. Runtime logs include `manual rollback required`.

## Step 1: Confirm Failure Mode

```bash
cd /Users/busiji/workbot
printf '{}\n' | MEMORY_HOOK_CORE_PROVIDER=external-core MEMORY_HOOK_EXTERNAL_CORE_MODULE=does.not.exist.module \
  python3 workspace/tools/memory_hook_gateway.py --host codex --event session-start --no-delegate
echo "EXIT:$?"
```

Expected incident signal in M9:
- process exits non-zero (`EXIT:1`)
- message indicates external-core load failure and manual rollback requirement

## Step 2: Execute Rollback Drill

```bash
cd /Users/busiji/workbot
MEMORY_HOOK_CORE_PROVIDER=external-core MEMORY_HOOK_EXTERNAL_CORE_PATH=/Users/busiji/memory \
  python3 workspace/tools/memory_hook_provider_rollback.py
```

Acceptance for drill:
- JSON output `status == "passed"`
- `external_probe_ok == true`
- `legacy_probe_ok == true`

## Step 3: Temporary Operational Rollback

Use explicit legacy provider override for temporary mitigation:

```bash
export MEMORY_HOOK_CORE_PROVIDER=legacy
```

After mitigation, run core regression subset:

```bash
cd /Users/busiji/workbot
python3 -m pytest -q \
  tests/test_memory_hook_gateway_m6_batch3_provider_switch.py \
  tests/test_memory_hook_provider_rollback.py \
  tests/test_memory_hook_gateway.py
```

## Step 4: Evidence Capture

Record all of the following in the active task card comment/body:

1. Failure timestamp and command.
2. Exact stderr/stdout failure line.
3. Exit code.
4. Rollback drill JSON result.
5. Mitigation command used.
6. Post-mitigation regression result.

## Step 5: Recovery Back to External-Core

When fix is ready:

1. Remove temporary legacy override.
2. Re-run:
- `memory-hook-external-core-only` workflow or local equivalent test set.
- fail-closed injection command (must still return non-zero on invalid module).
3. Close incident only after dual-audit sign-off.
