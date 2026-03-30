---
name: tmux-runtime-bot
description: "已弃用的 tmux-skills 兼容说明入口，保留文件路径避免旧索引失效"
tools: Read, Bash
model: qwen3.5-plus
permissionMode: default
maxTurns: 4
---

# Deprecated

`tmux-runtime-bot` 不再承担旧的四阶段 runtime / handoff / verify 编排职责。

当前 `tmux-skills` 的正式口径只有两件事：

1. 接收 Codex 提供的 `pane_count` 与 `pane_titles`
2. 在前台 `formal-session` 中生成当前会话期的临时工作 pane，并在 pane 停止时通过 window IPC bridge 回报给 monitor thread 的 `CODEX_THREAD_ID` 对应当前窗口 thread

补充口径：

- `CODEX_THREAD_ID` 表示 Codex app thread id，不是本地 CLI session id
- tmux handoff 不再使用 `codex exec resume`

请直接使用这些脚本：

- `start_formal_runtime_chain.py`
- `check_tmux_ready.py`
- `arm_tmux_handoff_watcher.py`
- `tmux_handoff_app_bridge.py`

不要再调用旧的 handoff 流程。
