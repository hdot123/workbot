---
type: [KB:DECISION]
title: "tmux handoff 投递切换到 Codex owner window"
created: 2026-03-30
updated: 2026-03-30
last_verified: 2026-03-30
source: Manual
confidence: high
tags: [workbot, tmux-skills, codex, window-ipc, handoff, thread]
related: [workbot, 2026-03-25-workbot-project-agents-and-runtime-surfaces]
version: v1.0
status: active
---

# tmux handoff 投递切换到 Codex owner window

## 结论

- `tmux-skills` 的 handoff delivery 正式从本地 CLI session 投递切换为 Codex owner window 投递
- `CODEX_THREAD_ID` 在 tmux handoff 链路中的语义固定为 Codex app thread id
- `CODEX_THREAD_ID` 不再允许被当作本地 CLI session id 使用
- handoff 最终投递不再使用 `codex exec resume`
- watcher 继续只负责观察、记录和落队列
- delivery runner 只负责排队编排与确保 bridge 常驻
- 真正的消息投递由常驻 window IPC bridge 通过 owner window 的 `thread-follower-start-turn` 执行

## 原因

- 旧链路虽然使用了 `CODEX_THREAD_ID` 这个名字，但实际仍在调用本地 `codex exec resume`
- 旧 delivery 语义与 Codex App 当前窗口显示链路不一致，导致“线程名义正确、投递表面成功、当前窗口仍不可见”的风险
- watcher 与 delivery 的职责此前耦合过紧，难以定义明确的接收验收标准

## 正式口径

### `CODEX_THREAD_ID`

- `CODEX_THREAD_ID` 必须表示目标 monitor app thread 的真实 thread id
- 不再允许用 `CODEX_THREAD_ID` 去查询本地 `session_index.jsonl`
- 任何把 `CODEX_THREAD_ID` 当作 CLI session id 的脚本、文档或记忆都视为漂移

### delivery 链路

- watcher 发现事件后把事件写入 handoff 队列
- delivery runner 被触发后，只负责确保 bridge 存在，并把事件保留在队列中
- window IPC bridge 常驻消费队列，并通过本地 Codex IPC 把消息路由到目标 thread 的 owner 窗口
- bridge 内部使用真实接口：
  - `initialize`
  - `thread-follower-start-turn`

### 成功验收

- 仅“请求已发出”不算成功
- 至少要满足以下条件，才视为消息已被当前窗口接收：
  - 收到 owner window 返回的 `handledByClientId`
  - 并拿到该次 `thread-follower-start-turn` 的成功响应
  - 如同连接观察到 `thread-stream-state-changed`，应记录到 receipt 作为补充可见性证据

### 失败处理

- window IPC socket 不存在或连接失败：保留队列文件，记失败 receipt，等待后续重试
- `thread-follower-start-turn` 失败：保留队列文件，记失败 receipt
- 已经存在 `delivered` / `skipped` receipt 的事件不得重复发送

## 影响范围

- `tmux-skills` 相关脚本、测试和说明文档必须统一采用 owner window / window IPC 语义
- 记忆层中凡是描述 tmux handoff delivery 的条目，都应以本决策为准

## 后续约束

- 若未来更换 transport，只能替换 bridge 实现，不得回退 watcher 职责边界
- 若本地窗口 IPC 协议升级，必须先基于真实可用方法重新确认能力，再调整投递实现
- 若需要扩展 ack 规则，应继续以“owner window 已返回成功响应”为最低验收线
