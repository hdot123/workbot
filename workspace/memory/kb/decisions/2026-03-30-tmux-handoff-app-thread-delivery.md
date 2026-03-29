---
type: [KB:DECISION]
title: "tmux handoff 投递切换到 Codex app thread"
created: 2026-03-30
updated: 2026-03-30
last_verified: 2026-03-30
source: Manual
confidence: high
tags: [workbot, tmux-skills, codex, app-server, handoff, thread]
related: [workbot, 2026-03-25-workbot-project-agents-and-runtime-surfaces]
version: v1.0
status: active
---

# tmux handoff 投递切换到 Codex app thread

## 结论

- `tmux-skills` 的 handoff delivery 正式从本地 CLI session 投递切换为 Codex app thread 投递
- `CODEX_THREAD_ID` 在 tmux handoff 链路中的语义固定为 Codex app thread id
- `CODEX_THREAD_ID` 不再允许被当作本地 CLI session id 使用
- handoff 最终投递不再使用 `codex exec resume`
- watcher 继续只负责观察、记录和落队列
- delivery runner 只负责排队编排与确保 bridge 常驻
- 真正的消息投递由常驻 app-server bridge 通过 thread / turn 模型执行

## 原因

- 旧链路虽然使用了 `CODEX_THREAD_ID` 这个名字，但实际仍在调用本地 `codex exec resume`
- 旧 delivery 语义与 Codex App 的 thread / turn 模型不一致，导致“线程名义正确、投递表面成功、实际没有进入目标 app thread”的风险
- watcher 与 delivery 的职责此前耦合过紧，难以定义明确的接收验收标准

## 正式口径

### `CODEX_THREAD_ID`

- `CODEX_THREAD_ID` 必须表示目标 monitor app thread 的真实 thread id
- 不再允许用 `CODEX_THREAD_ID` 去查询本地 `session_index.jsonl`
- 任何把 `CODEX_THREAD_ID` 当作 CLI session id 的脚本、文档或记忆都视为漂移

### delivery 链路

- watcher 发现事件后把事件写入 handoff 队列
- delivery runner 被触发后，只负责确保 bridge 存在，并把事件保留在队列中
- app-thread bridge 常驻消费队列，并通过 `codex app-server` 投递到目标 app thread
- bridge 内部使用真实接口：
  - `thread/resume`
  - `turn/start`
  - `thread/read`

### 成功验收

- 仅“请求已发出”不算成功
- 至少要满足以下条件之一，才视为消息已被目标 app thread 接收：
  - 收到目标 thread 上与该 turn 对应的 `turn/started` 和匹配的 `userMessage` item 回执
  - 或 `thread/read(includeTurns=true)` 能读回该条用户消息

### 失败处理

- app-server 启动失败：保留队列文件，记失败 receipt，等待后续重试
- `thread/resume` 失败：保留队列文件，记失败 receipt
- `turn/start` 失败：保留队列文件，记失败 receipt
- 已经存在 `delivered` / `skipped` receipt 的事件不得重复发送
- 已经存在 `turn_started` receipt 的事件，应优先补确认，不应盲目重发

## 影响范围

- `tmux-skills` 相关脚本、测试和说明文档必须统一采用 app thread 语义
- 记忆层中凡是描述 tmux handoff delivery 的条目，都应以本决策为准

## 后续约束

- 若未来更换 transport，只能替换 bridge 实现，不得回退 watcher 职责边界
- 若 App Server 接口升级，必须先基于真实可用方法重新确认能力，再调整投递实现
- 若需要扩展 ack 规则，应继续以“目标 app thread 已可读回消息”为最低验收线
