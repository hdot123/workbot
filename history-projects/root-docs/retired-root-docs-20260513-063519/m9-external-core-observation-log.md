# M9 Observation Log (H1)

Observation window: 7-14 days  
Start date: 2026-04-16  
Status: in-progress

## Acceptance Criteria

1. No unplanned runtime fallback behavior.
2. No unresolved external-core load incident.
3. Manual rollback operations (if any) have complete evidence and closure.
4. Fail-closed behavior remains stable (`EXIT:1` on invalid external module injection).

## Daily Metrics

| Date | Runtime errors (external-core load) | Manual rollback count | Fail-closed injection check | Notes |
|---|---:|---:|---|---|
| 2026-04-16 | 0 observed in current verification run | 0 | pass (`EXIT:1`) | Observation started; H3/H4/H5 completed |
| 2026-04-16 | 0 observed in latest precheck run | 0 | pass (`EXIT:1`) | 11:03 CST precheck: `51 passed`; cmux `rea-bot` and `qa-bot` cross-check both pass |

## Evidence Commands

```bash
cd /Users/busiji/workbot
python3 -m pytest -q \
  tests/test_memory_hook_gateway_m6_batch3_provider_switch.py \
  tests/test_memory_hook_impls_policy_conflict.py \
  tests/test_memory_hook_provider_rollback.py \
  tests/test_memory_hook_gateway.py \
  tests/test_f8_rollback.py
```

```bash
cd /Users/busiji/workbot
printf '{}\n' | MEMORY_HOOK_CORE_PROVIDER=external-core MEMORY_HOOK_EXTERNAL_CORE_MODULE=does.not.exist.module \
  python3 workspace/tools/memory_hook_gateway.py --host codex --event session-start --no-delegate
echo "EXIT:$?"
```
