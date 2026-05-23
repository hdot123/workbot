# workbot cmux Runtime Handbook

本文是 `workbot` 面向执行者的 `cmux` 统一操作手册。目标是把 commander 语义层 `A1-A9` 与当前 `cmux 5+1` 实现链对齐，避免再出现多入口、多真相和历史术语漂移。

## 1. 运行边界

- `cmux` 是当前唯一正式 runtime carrier。
- `tmux` 已退役，仅保留历史材料，不允许作为执行入口。
- 项目内部正式拓扑是 `5+1`：`pm-bot`、`dev-bot`、`qa-bot`、`doc-bot`、`rea-bot` 五个 bot pane，加 `cmux-browser` board pane。
- 外部 `main-thread` 在项目工作区外，负责调度与裁定，不属于项目内部 `5+1`。

## 2. 真相源顺序

冲突时按下面顺序判定：

1. `/Users/busiji/workbot/AGENTS.md`（仓库身份与边界）
2. `/Users/busiji/.agents/skills/cmux/references/workbot/cmux-multi-pane-agent-runtime-requirements.md`
3. `/Users/busiji/.agents/skills/cmux/scripts/*.py`（实现真相）
4. `/Users/busiji/workbot/docs/cmux-subagent-runtime-chain.md`
5. 本文（执行手册）

## 3. A1-A9 执行映射（cmux 实现）

### A1 启动拓扑

统一入口：

```bash
python3 /Users/busiji/.agents/skills/cmux/scripts/bootstrap_claude_runtime.py \
  --project-dir /Users/busiji/workbot \
  --recreate
```

执行基线：

- 项目必须有 `.venv`，缺失即 fail-fast。
- 前台只允许一个 GUI `cmux` 窗口。
- 只允许一个项目 workspace。

### A2 assignment 落盘与 dispatch gate

- assignment 由 `generate_cmux_assignments.py` 生成/同步到：
  - `/Users/busiji/workbot/workspace/artifacts/cmux-runtime/cmux-assignment.json`
- active assignment 必须满足 `dispatch_ready=true` 才允许启动。
- idle assignment 必须显式落默认值，禁止空值漂移：
  - `tool_profile_id=idle-default`
  - `allowed_tools` 使用 bot 级 idle baseline
  - `permission_mode="default"`

### A3 启动与派发

- active lane 通过 `claude --agent <lane_identity>` 启动。
- active flow 仍要求 `lane_identity == bot_name`。
- 启动完成后会产出运行清单：
  - `workspace/artifacts/cmux-runtime/runtime-launch-manifest-<bot>.json`

### A4 Hook 合同

- Hook 入口统一走 `cmux_claude_hook_bridge.py`。
- `.claude/settings.local.json` 必须配置四个事件：
  - `SessionStart`
  - `UserPromptSubmit`
  - `Stop`
  - `Notification`
- 缺 `workspace/surface/state_file` 时必须 fail-close（返回码 `2`，`missing_hook_context`），不得静默成功。
- Hook 状态统一写入 runtime state 文件（默认在 `workspace/artifacts/cmux-runtime/`）。

### A5 运行中监控与健康检查

- watcher 主循环必须容忍通知读取抖动，不得因为 socket 短暂异常退出。
- watcher 必须执行单 workspace guard 与 selected-workspace 一致性校验。
- watcher 持续输出 consumer sidecar：
  - `workspace/artifacts/cmux-runtime/cmux-consumer-state-latest.json`

统一健康检查：

```bash
python3 /Users/busiji/.agents/skills/cmux/scripts/cmux_runtime_ctl.py status \
  --assignment-file /Users/busiji/workbot/workspace/artifacts/cmux-runtime/cmux-assignment.json
```

`healthy` 需要同时满足：

- `cmux_ping_ok=true`
- assignment `ready=true` 且 `dispatch_ready=true`
- `runtime.single_workspace_healthy=true`
- `runtime.selected_workspace_matches_assignment=true`
- `runtime.active_runtime_healthy=true`
- `runtime.board_surface_guard.healthy=true`
  - `5+1` 模式下必须且仅允许一个 `cmux-browser` 且 `surface_type=browser`
  - `pm-only` 模式下 board guard 为 `required=false`
- `runtime.five_plus_one_shape_guard.healthy=true`（`5+1` 模式要求五个 worker 标题齐全）
- watcher 守卫按模式生效：
  - `pm-only`：`watcher.alive=true` 是硬门禁
  - `5+1`：watcher 状态记录但不阻断 `healthy`

### A6 收口判定

- 完成判定优先依赖 control packet（`state=completed` 且 `result=pass`）。
- 非取证模式下，缺 control packet 不允许判定为完成。
- `--forensic-read-pane` 只用于显式取证兜底，不是 normal path。

### A7 本地治理回写

- 默认 watcher 在所有 active assignment 完成后触发 finish-cycle（`finish_on_complete=true`）。
- `cmux_finish_cycle.py` 回写：
  - `*-task-list.md`
  - `ce-sync-plan.md`
  - `cmux-finish-receipts.jsonl`
- normal path 回写依据是结构化来源优先：
  - `control_packet`
  - `consumer-state`
- pane transcript/evidence line 仅保留在 `forensic` 兜底路径。

### A8 CE 生命周期同步

- 正式 CE 生命周期评论由 commander 复核并执行。
- 自动收尾默认只做本地回写，不替代 commander 的正式生命周期评论职责。

### A9 下一轮或 idle 出口

- 有下一轮真实任务：准备下一轮 assignment，返回 `A1`。
- 无下一轮真实任务：active assignment 清回 `IDLE`，运行态回到 idle，禁止假运行。
- finish receipt 用于同一 `cycle_id` 幂等去重，避免重复收口。

## 4. 漂移口径澄清

- `A1-A9` 语义仍有效，但 `cmux` 当前 assignment 真源不是历史 `lookme-assignment.json`，而是 `workspace/artifacts/cmux-runtime/cmux-assignment.json`。
- `cmux-browser` 是 board pane，不是正式 bot 身份，也不是 `main-thread` 别名。
- `empty` 仅是内部 placeholder token，不是 `workbot` 对外身份真相。
- 正式写回 normal path 不再以 pane transcript 作为主证据来源。

## 5. 变更门禁

- 改 `cmux` 运行链路脚本前，必须先对齐本文与 `cmux-subagent-runtime-chain.md`。
- 不允许把 `tmux` 入口重新放回默认路径。
- 不允许引入“空值 assignment + 运行时隐式回退”的新路径。
- 任何阶段交付文档必须保留“子代理执行 + 双路交叉验证”门禁文本，并在验证完成后补 PASS/FAIL 证据。
