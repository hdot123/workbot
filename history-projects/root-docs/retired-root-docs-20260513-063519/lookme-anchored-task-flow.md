# Lookme Anchored Task Flow

> Legacy Notice (P12-rest, 2026-04-18):
> 本文档保留为历史 `lookme/tmux` 锚点流程参考，不再是当前正式 runtime 操作入口。
> 当前正式执行链请以 `/Users/busiji/workbot/docs/cmux-runtime-handbook.md` 与
> `/Users/busiji/workbot/docs/cmux-subagent-runtime-chain.md` 为准。
> 下文中的 `formal-session/4-pane/lookme` 仅作历史样例，禁止作为当前正式执行指令。

## 用法

以后你可以直接发这一句：

```text
按锚点任务执行今天流程
```

或者更完整一点：

```text
按锚点任务执行今天的 AEdu 流程，从任务系统唤醒开始，到 CE 收口和会话结束/下一会话准备结束
```

## 总原则

- Obsidian 导航入口：[[会话运行文档导航]]
- 正式真源先读：
  - [A1-A9 Session Protocol](/Users/busiji/workbot/docs/a1-a9-session-protocol.md)
  - [A1-A9 Session Brief](/Users/busiji/workbot/docs/a1-a9-session-brief.md)
- 每次正式会话开始前，必须先读一遍 Session Brief
- 先任务系统，后 pane
- 先状态真源，后运行面
- 先回写，后决定进入下一会话还是转 idle
- 任一锚点没完成，不得跳到下一个锚点
- 审计密集期默认拓扑：`1 dev + 1 rea + 1 qa + 1 doc`
- 若确需双 `dev`，必须先明确当前会话没有独立 `rea-bot` 常驻需求，且不能绕过“首轮审计先过 `rea-bot`”

## 会话级定义

- `A1-A9` 是会话级生命周期
- `A6-A9` 是当前会话内的收口与分支判断
- 不是“某个 pane 完成一次就重跑一套”

## 锚点

### A0 任务系统唤醒

必须读取：

- [dev-task-list.md](/Users/busiji/workbot/workspace/projects/AEdu/dev-task-list.md)
- [qa-task-list.md](/Users/busiji/workbot/workspace/projects/AEdu/qa-task-list.md)
- [doc-task-list.md](/Users/busiji/workbot/workspace/projects/AEdu/doc-task-list.md)
- [rea-task-list.md](/Users/busiji/workbot/workspace/projects/AEdu/rea-task-list.md)
- [ce-sync-plan.md](/Users/busiji/workbot/workspace/projects/AEdu/ce-sync-plan.md)

必须输出：

- 当前整体项目情况
- CE 已完成多少
- CE 未完成多少
- 哪些项符合要求
- 哪些项需要整改

完成标准：

- 我已经把项目现状说清楚
- 我已经给出今天的主线和残余阻塞

### A1 当前会话任务确定

必须完成：

- 确定今天固定 4 个 pane 各自任务
- 固定执行位：
  - `formal-session:1.1` -> `dev-bot`
  - `formal-session:1.2` -> `rea-bot`
  - `formal-session:1.3` -> `qa-bot`
  - `formal-session:1.4` -> `doc-bot`
- 每个 pane 只挂 1 条当前任务
- 每条任务都要能对应到 task list / CE 口径
- 若当前会话任务含“审计 / 复核 / 一致性 / 真实性”属性，必须先给 `rea-bot` 派首轮任务
- 每条任务都必须先落成可写入 assignment 的结构：`target / assignment_id / title / goal / task_text / continue_text / status`

必须输出：

- `pane -> assignment_id -> title -> goal`

完成标准：

- 4 个 pane 的任务分配已经明确
- 没有“先启动再想任务”的情况
- 没有“先发进 pane、后补 assignment”的情况

### A2 assignment 落盘

必须更新：

- [lookme-assignment.json](/Users/busiji/workbot/workspace/artifacts/tmux-skills/lookme/lookme-assignment.json)

必须保证：

- `target` 是实例真源
- `assignment_id` 是当前任务真源
- `bot_name` 只是角色标签
- 当前会话有执行任务时，assignment 至少有 `1` 条真实 `ACTIVE` 任务，不能是空 `panes`
- 当前会话没有执行任务时，必须显式写成 idle assignment，并停止在 A2，不进入 A3/A4
- 不允许用“待分配任务”占位项冒充当前任务

完成标准：

- assignment 文件和 task list 一致
- assignment 文件足以直接驱动 `lookme`

### A2.5 手动就位 pane

必须完成：

- 你手动把固定 4 个 pane 在 `formal-session` 里就位
- 不动态增减 bot 数量

固定 pane：

- `formal-session:1.1`
- `formal-session:1.2`
- `formal-session:1.3`
- `formal-session:1.4`

完成标准：

- 4 个 pane 已存在且可写入任务
- 这一步完成前，不进入 A3

### A3 pane 派发

必须完成：

- 把 4 条任务发进 `formal-session`
- 派发后立刻复查 pane，确认消息已经真正提交，不是停在输入框或 queued messages

完成标准：

- 4 个 pane 都吃到当前任务文本
- 不存在“任务还躺在输入框里没发出去”的假派发
- 若当前只有部分 pane 有真实任务，则只检查那些 active targets，不强行给空闲 pane 编造任务

### A4 lookme 常驻

必须启动：

- [lookme_supervisor.py](/Users/busiji/workbot/workspace/artifacts/tmux-skills/lookme/lookme_supervisor.py)

必须验活：

- supervisor 进程存在
- watcher 进程存在
- `lookme_ctl.py status` 返回 `0`
- `assignment.ready == true`
- `active_assignment_count >= 1`

完成标准：

- 不是“命令跑过了”
- 而是 supervisor + child watcher 都真的在，且 assignment 真能驱动监控

### A5 运行面盯盘

运行中必须持续做：

- 看 pane 是否推进
- 看 pane 是否审批卡住
- 看 pane 是否 queued messages 卡住
- 看 pane 是否已完成停在结果页

处理原则：

- pane 停住 = 强执行信号
- 先处理，再解释

完成标准：

- 没有停住不管的 pane

### A6 会话内收口判断

必须完成：

- 逐个看 4 个 pane
- 判断当前会话是否真的进入收口状态
- 区分“当前 assignment 完成”和“项目永久没有后续”
- 区分“bot 输出已经形成结论”和“只是停在 prompt / queued / accept edits”

必须输出：

- 哪些 pane 已完成
- 哪些 pane 未完成
- 哪些是独立阻塞

完成标准：

- 不是凭 watcher 猜
- 而是看 pane 现场结论

### A7 状态回写

必须更新：

- [dev-task-list.md](/Users/busiji/workbot/workspace/projects/AEdu/dev-task-list.md)
- [qa-task-list.md](/Users/busiji/workbot/workspace/projects/AEdu/qa-task-list.md)
- [doc-task-list.md](/Users/busiji/workbot/workspace/projects/AEdu/doc-task-list.md)
- [rea-task-list.md](/Users/busiji/workbot/workspace/projects/AEdu/rea-task-list.md)
- [ce-sync-plan.md](/Users/busiji/workbot/workspace/projects/AEdu/ce-sync-plan.md)

必须保证：

- pane 结论和任务系统一致
- 任务系统和 CE 计划一致

完成标准：

- 不允许“pane 已完成但 task list 还没改”

### A8 CE 收口

必须判断：

- 哪些项可以同步到 `#31`
- 哪些项仍然只能保持 `opened`
- 哪些项是独立阻塞，例如 `#56`

完成标准：

- CE 收口口径和本地状态一致

### A9 会话结束或下一会话准备

必须完成：

- 清掉当前会话 assignment 语义
- 若存在下一会话真实任务，生成下一会话 assignment，再次进入 A1
- 若不存在下一会话真实任务，停掉 `lookme`，并把 assignment 清回 idle
- 不允许在“没有下一会话任务”时让 watcher 继续盯空 assignment

完成标准：

- 不允许旧任务 lingering 在 pane 里继续污染后续会话
- 不允许 `lookme` 停在“进程还在、但没有真实任务”的假运行态

## 一句话发布模板

```text
按锚点任务执行今天流程：A0 任务系统唤醒 -> A1 当前会话任务确定 -> A2 assignment 落盘 -> A2.5 手动就位 pane -> A3 pane 派发 -> A4 lookme 常驻 -> A5 运行面盯盘 -> A6 会话内收口判断 -> A7 状态回写 -> A8 CE 收口 -> A9 会话结束或下一会话准备
```

## 最短执行版

```text
按锚点任务执行今天流程，从 A0 开始，做到 A8，完成后再决定是否进入 A9
```

## 收尾回写口令

### 只做本地收尾

```text
按锚点任务执行收尾，从 A6 开始：先验收当前 4 个 pane，再做 A7 状态回写，做到 A8 前停下
```

### 做到 CE 收口

```text
按锚点任务执行收尾，从 A6 开始到 A8 结束
```

### 做到会话结束或下一会话准备

```text
按锚点任务执行收尾，从 A6 开始到 A9 结束
```

## 失败规则

以下任一情况，都视为锚点失败，必须停在当前锚点修复：

- 没做 A0 就直接启动 pane
- assignment 没写好就启动 watcher
- A3 没确认消息已提交就宣布“任务已派发”
- watcher 没验活就说“已经跑起来”
- `status != 0` 或 `assignment.ready != true` 还说“已经跑起来”
- pane 停住但没有处理
- pane 已完成但 task list 没回写
- 本地已完成但 CE 口径没同步
- 没有下一会话真实任务，却没有停掉 `lookme` 并清空 assignment

## 当前推荐口令

你以后直接发这句就够了：

```text
按锚点任务执行今天的 AEdu 流程，从 A0 开始到 A8 结束
```
