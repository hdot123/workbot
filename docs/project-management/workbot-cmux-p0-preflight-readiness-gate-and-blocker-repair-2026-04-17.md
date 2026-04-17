# workbot cmux P0-preflight 交付: Readiness Gate And Blocker Repair

日期: 2026-04-17

## 目标

把 “implemented / delivered / ready” 从口头判断改成可复跑的机器判定，并修掉进入 `Phase 2` 之前会让 `memory_hook_gateway` fail-close 的真实 blocker。

## 本次新增

- Phase readiness checker:
  - `/Users/busiji/workbot/workspace/tools/cmux_phase_readiness.py`
- memory canonical validator:
  - `/Users/busiji/workbot/workspace/tools/validate_memory_system.py`
- readiness tests:
  - `/Users/busiji/workbot/tests/test_cmux_phase_readiness.py`
- readiness receipt:
  - `/Users/busiji/workbot/workspace/artifacts/project-readiness/phase2-preflight-latest.json`

## 本次修复的 blocker

### 1. memory hook canonical 缺失

- 新增 `/Users/busiji/workbot/workspace/memory/docs/INDEX.md`
- 新增 `/Users/busiji/workbot/workspace/memory/docs/记忆系统全景文档.md`
- 新增 `/Users/busiji/workbot/workspace/memory/inbox.md`
- 新增 `/Users/busiji/workbot/workspace/tools/validate_memory_system.py`

### 2. project-map / workspace / global canonical 规则不满足 gateway 校验

- 更新 `/Users/busiji/workbot/workspace/project-map/INDEX.md`
- 更新 `/Users/busiji/workbot/workspace/project-map/legal-core-map.md`
- 更新 `/Users/busiji/workbot/workspace/project-map/ingestion-registry-map.md`
- 更新 `/Users/busiji/workbot/workspace/INDEX.md`
- 更新 `/Users/busiji/workbot/workspace/memory/kb/global/INDEX.md`
- 更新 `/Users/busiji/workbot/workspace/memory/kb/global/workbot-memory-system.md`
- 更新 `/Users/busiji/workbot/workspace/memory/kb/global/workbot-memory-routing.md`
- 更新 `/Users/busiji/workbot/workspace/memory/kb/global/workbot-project-map-governance.md`
- 更新 `/Users/busiji/workbot/workspace/memory/kb/projects/workbot.md`

### 3. delivery doc 坏锚点

- 修复 `/Users/busiji/workbot/docs/project-management/workbot-cmux-p10-core-delivery-2026-04-17.md`

## 结果

- `validate_memory_system.py` 现在返回 `status=ok`
- `cmux_phase_readiness.py` 现在返回:
  - `implemented=true`
  - `delivered=true`
  - `ready=true`
- readiness receipt 已落到:
  - `/Users/busiji/workbot/workspace/artifacts/project-readiness/phase2-preflight-latest.json`

## 验证

```bash
python3 /Users/busiji/workbot/workspace/tools/validate_memory_system.py
python3 /Users/busiji/workbot/workspace/tools/cmux_phase_readiness.py
python3 /Users/busiji/workbot/tests/test_cmux_phase_readiness.py
python3 /Users/busiji/workbot/tests/test_memory_hook_gateway.py
python3 /Users/busiji/workbot/tests/test_memory_hook_gateway_m6_batch3_provider_switch.py
```
