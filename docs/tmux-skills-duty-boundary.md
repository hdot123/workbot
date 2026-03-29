# tmux-skills 冻结职责分层

## 目的

本文件是 `tmux-skills` 的冻结职责边界真源，单独说明：

- `tmux-skills` 负责什么
- 人类负责什么
- Codex 负责什么
- pane 生成模式是什么
- 什么情况下才触发 Codex 介入

本文件只讨论 runtime / watcher / bell / verify 边界，不讨论业务任务细节。

## `tmux-skills` 负责

`tmux-skills` 只保留 runtime / watcher / bell / verify 职责，不承担角色注入和业务调度。

保留职责：

- 创建或接管唯一 attached 的 `formal-session`
- 构造目标 pane 拓扑
- 生成 pane 基础运行面
- 修改 pane 标题为白名单角色名
- 输出 pane 基础定位信息
- 维护 runtime ledger 的运行面事实
- 观察 pane 是否进入“可到达但停止推进”的状态
- 向 Codex 发送固定记忆触发门铃
- 对正式运行面做 ready-check / verify

不再承担：

- 在 skill 内启动 `claude`
- 在 skill 内切换角色
- 在 skill 内注入 system prompt
- 在 skill 内下发业务任务
- 在 skill 内替指挥官做业务决策

## pane 生成模式

当指挥官通过指令要求生成 pane 时，`tmux-skills` 只负责“建车位和贴标签”，不负责“把身份内容塞进去”。

例如：

- `2` 个 `dev-bot`
- `1` 个 `qa-bot`
- `1` 个 `doc-bot`

则 `tmux-skills` 只负责生成 `4` 个 pane，并把标题改成对应角色名。后续哪个 pane 要注入什么身份内容，由人类自行决定。

正式交付给指挥官的 pane 格式固定为：

```text
formal-session:1.1 dev-bot
formal-session:1.2 dev-bot
formal-session:1.3 qa-bot
formal-session:1.4 doc-bot
```

这里固定使用：

- `session:window.pane`
- `pane_title`

不把 `%0` 这类 `pane_id` 作为对外主展示格式。

## 触发 Codex 干预的唯一门槛

门铃只在一种情况下触发 Codex 干预：

- pane 仍然活着
- tmux target 仍可到达
- pane 已经停止推进
- Codex 可以进入该 pane 继续处理

这类状态才属于“窗口 SOP 干预”。

如果 pane 已死、session 不存在或 target 不可达，则不进入窗口 SOP，而进入 runtime 恢复分支。

## 人类负责

以下动作全部归人类前置准备，不属于 `tmux-skills`：

- `claude` 进入
- 白名单角色进入
- system prompt 注入
- 决定哪个 pane 注入哪份身份内容
- 现场准备到“既有白名单 pane 现场”状态

## Codex 负责

Codex 只在收到固定门铃之后介入，不提前代替 runtime 做准备。

Codex 负责：

- 接收门铃
- 命中固定记忆
- 进入目标 `formal-session:window.pane`
- 在 pane 内执行窗口 SOP 动作
- 动作后立即复查
- 再回外层汇报
- 投递业务任务内容
- 处理收到门铃后的业务逻辑
