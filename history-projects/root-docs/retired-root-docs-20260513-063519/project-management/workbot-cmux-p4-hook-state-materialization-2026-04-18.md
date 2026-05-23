# workbot cmux P4 交付: Hook-state Materialization

日期: 2026-04-18

## 目标

让 `hook-state.json` 在真实 `cmux` runtime 里稳定 materialize 出 active surface 状态，而不是长期停留在空 `surfaces`。

## 发现的真实缺口

- runtime bootstrap 没有确保项目级 hook relay 存在。
- 因此 `cmux_claude_hook_bridge.py` 不会稳定接到 live runtime 事件，`/Users/busiji/workbot/workspace/artifacts/cmux-runtime/hook-state.json` 虽然存在，但会停留在空的 `surfaces` 或只看到部分事件。

## 本次修复

- 修回 runtime bootstrap 的 hook 安装动作:
  - `/Users/busiji/.agents/skills/cmux/scripts/bootstrap_claude_runtime.py`
- 新增 repo-local 回归测试:
  - `/Users/busiji/workbot/tests/test_cmux_hook_materialization.py`
  - `/Users/busiji/workbot/tests/test_cmux_hook_bridge.py`

## 结果

- runtime bootstrap 现在会通过 `ensure_project_hook_settings(...)` 安装四个 relay:
  - `SessionStart -> session-start`
  - `UserPromptSubmit -> prompt-submit`
  - `Stop -> stop`
  - `Notification -> notification`
- live runtime 重新启动后，`hook-state.json` 已经出现非空 `surfaces`，并记录:
  - `workspace_ref`
  - `surface_ref`
  - `session_start_count`
  - `last_session_id`
  - `last_cwd`
- bridge 回归测试证明四类事件都会累计到同一 surface 状态上，而不是只记录 `session-start`。

## live proof

- live state file:
  - `/Users/busiji/workbot/workspace/artifacts/cmux-runtime/hook-state.json`
- 2026-04-18 本地复跑后，`surface:18` 已记录:
  - `session_start_count >= 1`
  - `prompt_submit_count >= 1`
  - `stop_count >= 1`
  - `notification_count >= 1`
  - `last_session_id` 非空

## 验证

```bash
python3 /Users/busiji/workbot/tests/test_cmux_hook_materialization.py
python3 /Users/busiji/workbot/tests/test_cmux_hook_bridge.py
cmux tree
sed -n '1,160p' /Users/busiji/workbot/workspace/artifacts/cmux-runtime/hook-state.json
```
