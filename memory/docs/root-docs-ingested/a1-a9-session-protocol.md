# A1-A9 Session Protocol
## Purpose
这份文档是当前 `cmux 5+1` 会话生命周期规范（commander 语义层）。
唯一总定义：
- `A1-A9` 是会话级生命周期
- `A6-A9` 是当前会话内的收口与分支判断
- 不是“某个 pane 完成一次就重跑一套”

## Scope
适用：
- `cmux` 项目 workspace（`5+1`）
- `dev-bot`
- `rea-bot`
- `qa-bot`
- `doc-bot`
- `pm-bot`
- watcher / finish-cycle 链路
- commander
不适用：
- 临时探索 pane
- 未进入正式任务流的临时验证命令

## Mandatory Read
每次正式会话开始前，必须先读：
- [A1-A9 Session Brief](/Users/busiji/workbot/docs/a1-a9-session-brief.md)
规则：
- 不读 brief，不进入 `A1`
- brief 读完后，才允许开始 assignment、派发、监控和收口

## Session Model

- `A1-A5`：会话启动与执行
- `A6-A9`：会话收口与分支判断
- 一次正式会话只允许有一条 `A1 -> A9` 主线

## A1 Task Set

必须完成：

- 确定本次会话目标
- 确定各 pane 职责
- 确定哪些任务属于 active assignment
- 确定哪些 pane 只是待命

强约束：

- 每个 pane 只挂 1 条当前任务
- 审计 / 复核 / 一致性 / 真实性类任务，首轮必须先给 `rea-bot`
- 每条任务都必须先落成 assignment 结构：`target / assignment_id / title / goal / task_text / continue_text / status`

禁止：

- 先发进 pane，再补 assignment
- 给空闲 pane 临时编造无真源任务
- 用占位项冒充 active assignment

## A2 Assignment Source of Truth

必须更新：

- [cmux-assignment.json](/Users/busiji/workbot/artifacts/cmux-runtime/cmux-assignment.json)

必须满足：

- 有真实任务时：至少 `1` 条真实 `ACTIVE` assignment
- 没有真实任务时：写成 idle assignment
- 不允许“待分配任务”占位项充当 active assignment

## A3 Dispatch

必须完成：

- 把 active assignment 真正发进对应 pane
- 派发后立刻复查 pane，确认消息已提交

派发成功判定：

- 任务不在输入框
- 不在 queued messages
- pane 已开始消费当前任务

## A4 Monitoring

只有以下条件全部满足，才允许说“会话已启动”：

- watcher 已启动且可读
- `cmux_runtime_ctl.py status` 返回健康状态
- `assignment.ready == true`
- `active_assignment_count >= 1`
- active pane 已收到当前任务

结论：

- 没有 active assignment，不允许启动正式监控
- 没有真实任务时，必须保持 idle，不允许伪装“监控中”

## A5 Supervision

必须持续判断：

- pane 正在推进
- pane 卡审批
- pane 卡 queued messages
- pane 已输出结论但停在结果页

原则：

- pane 停住 = 强执行信号
- 先处理当前卡点，再谈下一步

## A6 Acceptance

先回答 4 个问题：

1. 当前 active assignment 是否全部完成
2. 是否仍有未完成 active pane
3. 是否只是停在 prompt / queued / accept edits
4. 是否已经进入可回写本地真源的状态

分类：

- `A6-1 未完成`：回到 `A5`
- `A6-2 已完成但仅限本地结论`：进入 `A7`
- `A6-3 已完成且具备 CE 生命周期同步条件`：进入 `A7`，然后进入 `A8`
- `A6-4 不存在下一会话真实任务`：进入 `A7`，如有需要进入 `A8`，最终进入 `A9`

## A7 Local Writeback

每次会话内 active assignment 完成后，都必须执行。

必须更新：

- [dev-task-list.md](/Users/busiji/workbot/projects/AEdu/dev-task-list.md)
- [qa-task-list.md](/Users/busiji/workbot/projects/AEdu/qa-task-list.md)
- [doc-task-list.md](/Users/busiji/workbot/projects/AEdu/doc-task-list.md)
- [rea-task-list.md](/Users/busiji/workbot/projects/AEdu/rea-task-list.md)
- [ce-sync-plan.md](/Users/busiji/workbot/projects/AEdu/ce-sync-plan.md)

硬规则：

- `A7` 是每次会话收口都必须做的
- 不允许因为“先看看是否进入下一会话”而跳过 `A7`

## A8 CE Lifecycle Sync

规则：

- 正式 CE 评论由 commander 写
- `cmux` 自动收尾默认只做本地回写
- 自动收尾默认不替 commander 写正式 CE 生命周期评论

必须判断：

- 哪些项同步到 `#31`
- 哪些项继续 `opened`
- 哪些项关闭
- 哪些项只是独立阻塞或未来锚点

CE API 硬门槛：

- 先读目标 issue，再读目标 notes；至少确认读接口可用，才进入写入
- 写入前先按 marker 做一次去重检查，避免重复评论
- 写入后必须再读一次 notes，拿到真实 `note_id`，才允许宣告“CE 已同步”
- `401/403` 先排 token 或权限；`5xx/Bad Gateway` 先判定为 CE 网关异常，不得误报成功
- 遇到 `5xx` 或超时：本地仍执行 `A7`，但 `A8` 只能记为 pending，不得口头或文档写成已完成

## A9 Exit or Next Session Prep

只有两种结果：

- `A9-1 存在下一会话真实任务`：
  - 清掉当前会话 assignment 语义
  - 生成下一会话 assignment
  - 当前会话回到 `A1`
- `A9-2 不存在下一会话真实任务`：
  - 停掉 watcher 常驻链路
  - 把 assignment 清回 idle
  - 不再保持假运行态

## Failure Cases

以下任一情况都算违规：

- 没读 brief 就进入 `A1`
- 先发 pane，再补 assignment
- 派发后没确认消息真的提交
- 没有 active assignment 却宣告监控链路已正式运行
- `A7` 没做就直接进入 `A8/A9`
- 自动收尾替 commander 写正式 CE 生命周期评论
- CE 写入后未拿到真实 `note_id` 却宣告“已同步”
- 不存在下一会话真实任务，却不收回到 idle 运行态

## Summary
必须记住的 4 条：

- `A1-A9` 是会话级生命周期
- `A6-A9` 是会话内收口分支，不是独立新轮次
- 每次正式会话开始前，必须先读 [A1-A9 Session Brief](/Users/busiji/workbot/docs/a1-a9-session-brief.md)
- 每次会话收口都必须先做 `A7`，再决定 `A8/A9`
