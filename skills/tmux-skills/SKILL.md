---
name: tmux-skills
description: |
  Workbot 的 tmux pane 生成与监控技能。
  Codex 提供 pane 数量和 pane 标题，tmux-skills 负责在前台 tmux 中生成这些 pane，并在 pane 停止时通过 Codex 本地 window IPC 向专用 monitor thread 的 `CODEX_THREAD_ID` 对应当前窗口 thread 报告。
---

# tmux-skills

## 目的

这个 skill 只做两件事：

1. 接收 Codex 提供的 `pane_count` 与 `pane_titles`
2. 在前台 tmux 中生成这些 pane，并在 pane 停止时向 monitor thread 的 `CODEX_THREAD_ID` 对应当前窗口 thread 报告

## 冻结口径

- `tmux-skills` 是纯 tmux 技能，不负责 Claude、agent、scene 或 prompt
- pane 数量与 pane 标题由 Codex 调用时显式传入
- `tmux-skills` 不自己决定 pane 数量，也不自己决定 pane 标题
- pane 标题只是当前 attached runtime 的临时标签，不承载项目级身份定义
- 正式 tmux 运行面只承认一个前台 attached 的 `formal-session`
- detached tmux session 不算正式运行面，必须先被前台 client 接管，`session_attached > 0` 才成立
- 对外主展示格式固定为 `target = formal-session:window.pane`
- pane 停止后的报告目标固定为 monitor thread 注入的 `CODEX_THREAD_ID`
- `CODEX_THREAD_ID` 是 tmux 门铃投递目标的唯一 thread 真源，必须指向当天唯一的监控 app thread
- `CODEX_THREAD_ID` 的语义是 Codex app thread id，不是本地 CLI session id
- tmux handoff 的 delivery 通过常驻 window IPC bridge 投递到当前 Codex 窗口，不再使用 `codex exec resume`
- 每次新的 pane 创建前，必须先清理上一轮遗留的 watcher、runtime ledger、issues 文件和 watcher 日志

## Attached 机制

`tmux-skills` 依赖 tmux 的一个基础机制：

- 只有 session 被前台 client attach 以后，attached 状态才成立
- 只有 attached 以后，窗口真实尺寸和 pane 布局才有正式意义
- 只有 attached 的 `formal-session` 才能被当作官方运行面

所以：

- 单纯 `tmux new-session -d` 创建出来的 detached session 还不算正式 runtime
- `tmux-skills` 必须创建或接管一个前台 attached 的 `formal-session`
- 文档里出现的 “formal-session 已经起来了” 默认指的是 “已经被前台接管”

## 负责什么

- 创建或接管前台 attached 的 `formal-session`
- 在新建 pane 前清理上一轮 runtime 遗留
- 按 Codex 提供的数量生成 pane
- 按 Codex 提供的标题设置 pane 标题
- 输出 pane 的 `target` 与标题
- 持续监控 pane 状态
- 当 pane 停止、失联或不可达时，向 `CODEX_THREAD_ID` 绑定的 monitor 当前窗口 thread 报告

## 不负责什么

- `claude --agent`
- 角色切换
- system prompt 注入
- 身份 payload 注入
- 外部会话校验
- 业务任务下发

## 调用合同

Codex 调用 `tmux-skills` 时必须显式提供：

- `pane_count`
- `pane_titles`

常见示例：

- `pane_count = 4`
- `pane_titles = ["task-1", "task-2", "notes", "monitor"]`

这表示：

- 生成 4 个 pane
- 第 1、2 个 pane 标题设为 `task-1`、`task-2`
- 第 3 个 pane 标题设为 `notes`
- 第 4 个 pane 标题设为 `monitor`

## 报告合同

pane 监控阶段只保留一个对外动作：

- pane 停止后向 `CODEX_THREAD_ID` 绑定的 monitor 当前窗口 thread 报告
  - 这里的目标线程只认 `CODEX_THREAD_ID`，不认发起本次调用的对话，也不认 tmux session 名称
  - delivery runner 只负责排队并确保 bridge 常驻，真正投递由 window IPC bridge 完成

报告目标使用：

- `CODEX_THREAD_ID`

报告内容至少应包含：

- `target`
- `pane_title`
- `state_class`

## 正式入口

优先使用这些脚本：

- 主链入口：`/Users/busiji/workbot/skills/tmux-skills/scripts/start_formal_runtime_chain.py`
- 布局入口：`/Users/busiji/workbot/skills/tmux-skills/scripts/build_tmux_topology.py`
- 运行面审计：`/Users/busiji/workbot/skills/tmux-skills/scripts/check_tmux_ready.py`
- watcher 挂载：`/Users/busiji/workbot/skills/tmux-skills/scripts/arm_tmux_handoff_watcher.py`
- window IPC bridge：`/Users/busiji/workbot/skills/tmux-skills/scripts/tmux_handoff_app_bridge.py`

常见调用方式：

```bash
python3 /Users/busiji/workbot/skills/tmux-skills/scripts/start_formal_runtime_chain.py \
  --codex-thread-id "$CODEX_THREAD_ID" \
  --formal-session formal-session \
  --pane-title task-1 \
  --pane-title task-2 \
  --pane-title notes \
  --pane-title monitor \
  --pretty
```

主链执行时会先做一轮预清理：

- 停掉旧的 tmux-skills watcher
- 清掉旧的 `current-runtime.json`
- 清掉旧的 `last-runtime-issues.json`
- 清掉旧的 `handoff-notifications.jsonl`
- 清掉旧的 `handoff-notifications.sqlite3`
- 清掉旧的 `watch-tmux-handoff.stdout.log`

布局规则：

- `4` 个 pane：`2x2`
- `6` 个 pane：`3x2`
- 其他数量：尽量按 `tiled` 网格布局

## Delivery 口径

- watcher 负责“看”，发现事件后落 handoff 队列
- delivery runner 负责“送”的编排，只确保 bridge 在跑并把事件留在队列中
- bridge 常驻消费队列，并通过 Codex 本地 window IPC 的 `thread-follower-start-turn` 把消息路由到目标 thread 的 owner 窗口
- 投递成功至少要求 owner 窗口返回 `handledByClientId`，并拿到该次 turn 的成功响应；如果同连接还观察到 `thread-stream-state-changed` 广播，会一并记入 receipt

## 一句话职责

**根据 Codex 提供的数量和标题，在前台 tmux 中生成 pane，并在 pane 停止后通过 window IPC bridge 向 `CODEX_THREAD_ID` 对应的 monitor 当前窗口 thread 报告。**
