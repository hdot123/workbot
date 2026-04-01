# tmux-skills 设计文档

> 当前文档角色：现行设计文档。
> 本文与 `SKILL.md`、`tmux-skills-duty-boundary.md` 一起构成当前实现的主口径。

## 1. 定位

`tmux-skills` 是一个纯 tmux 技能。

它的职责只有两段：

1. Codex 提供 pane 数量和 pane 标题，`tmux-skills` 在前台 tmux 中生成这些 pane
2. pane 生成完成后，`tmux-skills` 持续监控 pane 状态，并在 pane 停止时向 `CODEX_THREAD_ID` 绑定 thread 的 owner 窗口报告

一句话定义：

**`tmux-skills = foreground tmux pane generator + stopped-pane reporter`**

## 2. 输入模型

`tmux-skills` 不自己决定 pane 拓扑，而是由 Codex 调用时提供参数。

正式输入为：

- `pane_count`
- `pane_titles`

示例：

```json
{
  "pane_count": 4,
  "pane_titles": ["task-1", "task-2", "notes", "monitor"]
}
```

这表示：

- 在前台 `formal-session` 中生成 4 个 pane
- 依次把 pane 标题设置为 `task-1`、`task-2`、`notes`、`monitor`
- 这些标题只是本次 runtime 的临时局部标签，不是项目级身份名

## 3. 运行模型

### 3.1 Formal Session

- 正式 tmux 运行面只承认一个前台 attached 的 `formal-session`
- `tmux-skills` 的目标是维护这个前台 tmux 运行面
- `tmux-skills` 不负责业务线程编排，只负责 pane 生成与 pane 监控
- 每次新的 pane 创建前，必须先清掉上一轮 runtime 遗留

这里依赖 tmux 的 attached 机制：

- detached session 只是 tmux server 里的一个会话对象，还不算正式运行面
- 只有被前台 client 接管后，`session_attached > 0` 才成立
- 只有 attached 后，窗口真实尺寸、pane 布局和交互输入输出才有正式意义

因此 `tmux-skills` 的“创建 session”实际上指的是：

- 先清理旧 watcher、旧 runtime ledger、旧 issues 文件、旧 handoff 数据和旧 watcher 日志
- 清空 delivery queue，并 unset tmux 环境里的 `CODEX_THREAD_ID`
- bridge 当前不在 cleanup 中显式 kill；现状由 PID 文件检查与单实例锁避免重复实例
- 创建并 attach 一个前台 `formal-session`
- 或接管一个已经 attached 的 `formal-session`

### 3.2 Pane 生成

pane 生成阶段只关心 tmux 本身：

- session 是否存在
- pane 数量是否达到调用要求
- pane 标题是否已按调用要求设置
- 是否可以输出稳定的 `target`

对外交付格式固定为：

- `formal-session:window.pane`
- `pane_title`

### 3.3 Pane 监控

pane 监控阶段只关心 pane 是否仍在运行：

- pane 活着
- pane 停止
- target 不可达
- session 不存在

其中最重要的正式动作是：

- pane 停止后向 `CODEX_THREAD_ID` 绑定 thread 的 owner 窗口报告

这里采用固定监控口径：

- tmux 原生命令只提供 pane 原始状态与可抓取屏幕内容
- watcher 不发明新规则，只执行固定规则
- `round` 表示对全部 watcher targets 的一次完整扫描；如果当前有 `6` 个 pane，则一轮就是 `formal-session:1.1` 到 `formal-session:1.6` 全部采完
- `pane_stopped` 固定规则：
  - `pane_dead > 0`
  - 或首次采样建立 baseline 且已经观察到 pane 出现过一次有效输出变化后，同一个 pane 连续 `3` 轮最近 `5` 行输出 hash 不变
- watcher 负责控制“怎么放”：
  - 必须先完成整轮扫描
  - 这一轮里满足 `pane_stopped` 的 pane 可以有多个
  - 但同一时刻最多只允许向下游放 `1` 条消息
  - 如果这一轮有多个 pane 同时满足规则，watcher 只先下放 `1` 条，其余 pane 在后续轮次继续按相同规则重试放行

换句话说：

- watcher 负责“看”和“按固定规则放”
- `deliver_tmux_handoff_notification.py` 负责确保 bridge 常驻
- `tmux_handoff_app_bridge.py` 负责按 queue 顺序处理并投递

## 4. Codex 与 tmux-skills 的边界

### 4.1 Codex 负责

- 决定本次要生成多少 pane
- 决定每个 pane 的标题
- 调用 `tmux-skills`
- 接收 pane 停止后的报告

### 4.2 tmux-skills 负责

- 创建或接管前台 attached 的 `formal-session`
- 在新建 pane 前清理上一轮 runtime 遗留
- 按调用参数生成或收缩 pane
- 设置 pane 标题
- 允许在 pane 内直接启动 `claude`
- 当 pane 标题命中项目 `.claude/agents/<name>.md` 时，启动 `claude --agent <name>`
- 输出 pane target 与标题
- 监控 pane 状态
- pane 停止后向 `CODEX_THREAD_ID` 绑定 thread 的 owner 窗口报告

### 4.3 tmux-skills 不负责

- 为不存在于项目 `.claude/agents/` 的名字启动 `claude --agent`
- agent 定义生成或 prompt 编排
- system prompt 注入
- 外部会话校验
- 业务任务分发

## 5. 报告模型

`tmux-skills` 的报告目标固定为 `CODEX_THREAD_ID` 绑定 thread 的 owner 窗口。

这里不再使用旧简称，以免误解成某个固定名字的线程或 tmux session。

这里真正指的是 tmux 运行面中注入的那个 `CODEX_THREAD_ID` 唯一指向的正式 Codex app thread id，以及该 thread 当前 owner 的 Codex 窗口。

delivery 路径固定为：

- watcher 完成一整轮扫描后，最多只向 handoff 队列下放 `1` 条消息
- `deliver_tmux_handoff_notification.py` 只负责确保 bridge 常驻；如果输入事件尚未落到 queue，会先写入 queue
- `tmux_handoff_app_bridge.py` 按顺序处理 queue 文件，并通过本地 Codex IPC 的 `thread-follower-start-turn` 把消息路由到目标 thread 的 owner 窗口

这里明确排除：

- 把 `CODEX_THREAD_ID` 当成本地 CLI session id
- 用 `codex exec resume` 作为最终投递方式
- 用本地 `session_index.jsonl` 解释 `CODEX_THREAD_ID`

交付目标字段：

- `CODEX_THREAD_ID`

最小报告字段：

- `target`
- `pane_title`
- `state_class`

推荐补充字段：

- `session`
- `window`
- `reachable`

## 6. 成功标准

`tmux-skills` 的完成标准只有两条：

1. 已按 Codex 提供的数量和标题，在前台 tmux 中生成目标 pane
2. 已开始监控这些 pane，并能在 pane 停止时向 `CODEX_THREAD_ID` 绑定 thread 的 owner 窗口报告

只要满足这两条，就算 `ok`。
