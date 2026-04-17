# workbot cmux Runtime Handbook

本文是 `workbot` 面向执行者的 `cmux` 统一操作手册。目标是把日常运行和故障处理收敛为一条固定流程，避免再出现多入口、多真相和隐式回退。

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
5. 本文（操作收口）

## 3. 固定流程

### A0. 启动前检查

- 项目必须有 `.venv`，缺失即 fail-fast。
- 前台只允许一个 GUI `cmux` 窗口。
- 只允许一个 `cmux` workspace（项目 workspace）。

### A1. 启动

使用统一入口：

```bash
python3 /Users/busiji/.agents/skills/cmux/scripts/bootstrap_claude_runtime.py \
  --project-dir /Users/busiji/workbot \
  --recreate
```

### A2. Assignment 生成与门禁

- 由 `generate_cmux_assignments.py` 生成并回填 `cmux-assignment.json`。
- active assignment 必须过 `dispatch_ready` gate。
- idle assignment 必须显式包含默认值，禁止空值漂移：
`tool_profile_id=idle-default`、`allowed_tools=["Read"]`、`permission_mode="default"`。

### A3. Hook 链路

- Hook 入口统一走 `cmux_claude_hook_bridge.py`。
- 缺失 `workspace/surface/state_file` 时必须 fail-close（非 0），不得静默成功。
- `.claude/settings.local.json` 必须含四个事件：
`SessionStart`、`UserPromptSubmit`、`Stop`、`Notification`。

### A4. Watcher 链路

- watcher 主循环必须对通知读取异常容错，不得因 socket 抖动退出。
- watcher 必须执行单工作区 guard（workspace 数量大于 1 进入 hold）。
- watcher 继续执行 assignment workspace 与 selected workspace 一致性校验。

### A5. 健康检查

统一命令：

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
  - `5+1` 模式要求且仅允许一个 `cmux-browser` 且 `surface_type=browser`
  - `pm-only` 模式下该 guard 标记为 `required=false`，且检测到残留 board 会返回不健康
- `runtime.five_plus_one_shape_guard.healthy=true`（`5+1` 模式下要求五个 worker 标题齐全）
- watcher 守卫按模式生效：
  - `pm-only`：`watcher.alive=true` 是硬门禁
  - `5+1`：watcher 结果仅记录，不阻断 `healthy`

### A6. 结束与清理

- 清空已处理通知：`cmux clear-notifications`
- 关闭非项目 workspace：`cmux close-workspace --workspace <workspace:n>`
- 清理 stale watcher pid：删除 `workspace/artifacts/cmux-runtime/watch_cmux_assignments.pid`

## 4. 常见故障处理

### 多 workspace 漂移

现象：`workspace_count > 1`，watcher 进入 hold。  
处理：关闭额外 workspace，仅保留项目 workspace。

### Hook 丢上下文

现象：bridge 返回 `missing_hook_context`。  
处理：检查 `CMUX_WORKSPACE_ID`、`CMUX_SURFACE_ID`、`CMUX_HOOK_STATE_FILE` 注入链与 hook 配置。

### watcher 僵尸 pid

现象：`watcher_pid_not_running` 或 `watcher_pid_file_missing`。  
处理：清理 pid 文件后按当前运行策略重启 watcher。

### 通知堆积

现象：`list-notifications` 长期 `Waiting` 未读。  
处理：先确认 watcher 正常，再 `clear-notifications`，再观察是否复发。

## 5. 变更门禁

- 改 `cmux` 运行脚本必须做子代理交叉验证（至少两路独立只读验证）。
- 不允许把 `tmux` 入口重新放回默认路径。
- 不允许引入“空值 assignment + 运行时隐式回退”的新路径。
- 任何运行时策略变更必须同步更新本文与对应 canonical 文档。
