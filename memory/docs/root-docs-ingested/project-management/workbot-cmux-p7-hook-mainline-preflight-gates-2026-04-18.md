# workbot cmux P7 交付: Hook Mainline And Preflight Gates

日期: 2026-04-18

## 目标

把 `identify -> hook -> hook-state` 主链路补齐为可验证的 fail-close 路径，避免只在 `--no-delegate` 路径里“看起来通过”。

## 本次修改

- 强化 `ClaudeDelegate` preflight:
  - 文件: `/Users/busiji/workbot/tools/memory_hook_impls.py`
  - 行为: 缺失 `CMUX_HOOK_STATE_FILE` 时直接 fail-close（抛出 `RuntimeError`），不再静默回退默认路径。
- 新增 P7 主链路测试:
  - 文件: `/Users/busiji/workbot/tests/test_memory_hook_gateway_p7_mainline.py`
  - 覆盖:
    - `canonicalize_cmux_refs` identify 成功/异常回退
    - `main(no_delegate=False)` 的 `claude` 主链路 smoke（真实 `cmux` 调用路径）
    - `main(no_delegate=False)` 的 `codex` 主链路 smoke
    - `claude` 缺失 `state_file` 的 fail-close
    - `codex` 缺失全部 formal cmux 标记时跳过 delegate
    - `codex` 缺失 `surface` 但仍带 formal cmux 标记时 fail-close
- 扩充 bridge 负向回归:
  - 文件: `/Users/busiji/workbot/tests/test_cmux_hook_bridge.py`
  - 覆盖:
    - 缺失 `workspace`
    - 缺失 `surface`
    - 缺失 `state_file`
  - 断言: 返回非 0（当前 `2`）且 `error=missing_hook_context`
- CI 纳入主链路测试:
  - `/Users/busiji/workbot/.github/workflows/memory-hook-external-core-only.yml`
  - `/Users/busiji/workbot/.github/workflows/memory-core-auto-sync-deploy.yml`
  - 新增 `tests/test_memory_hook_gateway_p7_mainline.py` 与 `tests/test_cmux_hook_bridge.py`

## 结果

- `claude` 与真正的 `cmux` formal runtime 缺少关键 hook 上下文时，gateway/bridge 主链路仍明确 fail-close。
- `codex` 在非 cmux 本地会话里不再因为缺失 `CMUX_SURFACE_ID` 误判为 formal runtime 并退出。
- `delegate-on` 覆盖不再只停留在 no-delegate 路径。
- identify 归一化路径有回归锚点，避免 canonicalize 回归无告警。

## 验证

```bash
pytest /Users/busiji/workbot/tests/test_memory_hook_gateway_p7_mainline.py \
       /Users/busiji/workbot/tests/test_cmux_hook_bridge.py \
       /Users/busiji/workbot/tests/test_cmux_hook_materialization.py \
       /Users/busiji/workbot/tests/test_memory_hook_gateway_m6_batch3_provider_switch.py
python3 -m py_compile /Users/busiji/workbot/tools/memory_hook_impls.py \
                       /Users/busiji/workbot/tests/test_memory_hook_gateway_p7_mainline.py \
                       /Users/busiji/workbot/tests/test_cmux_hook_bridge.py
```
