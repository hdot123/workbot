# tmux-skills 冻结职责边界

## 目的

本文件只定义一件事：

- `tmux-skills` 到底负责什么

这里采用当前冻结口径：

**`tmux-skills` 是一个前台 tmux pane 生成与停止监控上报技能。**

## `tmux-skills` 负责

- 接收 Codex 提供的 `pane_count`
- 接收 Codex 提供的 `pane_titles`
- 创建或接管前台 attached 的 `formal-session`
- 按数量生成或收缩 pane
- 把 pane 标题设置为调用要求的标题
- 输出 pane 的 `target` 和标题
- 监控 pane 状态
- pane 停止时向 `CODEX_THREAD_ID` 绑定的 Codex app thread 报告

补充一条基础规则：

- detached tmux session 不算正式运行面
- 必须先被前台 client 接管，`session_attached > 0`，才算正式 `formal-session`

## `tmux-skills` 不负责

- 决定 pane 数量
- 决定 pane 标题
- `claude --agent`
- agent 身份切换
- system prompt 注入
- Claude scene 校验
- 业务任务分发

## Codex 负责

- 决定这次要生成多少 pane
- 决定每个 pane 的标题
- 调用 `tmux-skills`
- 接收 pane 停止后的报告

## pane 生成模式

pane 生成是参数化的，不是写死在技能里。

例如，当 Codex 提供：

- `pane_count = 4`
- `pane_titles = ["dev-bot", "dev-bot", "qa-bot", "doc-bot"]`

则 `tmux-skills` 只负责：

- 在前台 tmux 中生成 4 个 pane
- 把 4 个 pane 标题依次改为 `dev-bot`、`dev-bot`、`qa-bot`、`doc-bot`

正式交付格式固定为：

```text
formal-session:1.1 dev-bot
formal-session:1.2 dev-bot
formal-session:1.3 qa-bot
formal-session:1.4 doc-bot
```

这里固定使用：

- `session:window.pane`
- `pane_title`

## 触发报告的条件

`tmux-skills` 的监控阶段只保留一个正式触发条件：

- pane 停止了

触发后就向 `CODEX_THREAD_ID` 绑定的 Codex app thread 报告。

报告目标使用：

- `CODEX_THREAD_ID`
- `CODEX_THREAD_ID` 在这里表示 Codex app thread id，不是本地 CLI session id
- delivery 固定经由常驻 app-server bridge，不使用 `codex exec resume`，也不查本地 `session_index.jsonl`

## 一句话结论

`tmux-skills` 的职责不是“管理 Claude pane”，而是“按 Codex 的参数生成前台 tmux pane，并在 pane 停止时报告给 `CODEX_THREAD_ID` 绑定的 Codex app thread”。
