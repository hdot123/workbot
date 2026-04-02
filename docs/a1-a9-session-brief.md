# A1-A9 Session Brief

## Mandatory Rule

每次正式会话开始前，必须先读完这一页，再进入 `A1`。

## One-Line Model

- `A1-A9` 是**会话级生命周期**
- `A6-A9` 是当前会话内的收口与分支判断
- 不是“某个 pane 完成一次就重跑一套”

## Must Remember

1. 先 assignment，后派发
2. 派发后必须确认消息已真正提交
3. 有真实 active assignment，才允许启动 `lookme`
4. 每次会话收口都必须先做本地回写
5. 正式 CE 评论由 commander 写
6. CE 同步必须“先读、再写、再回读验真”，没拿到 `note_id` 不算成功
7. 没有下一会话真实任务，就停 `lookme` 并清空 assignment

## A1-A9 Short Form

- `A1`：确定当前会话任务集
- `A2`：把当前会话 assignment 落盘
- `A3`：把 active assignment 发进 pane，并确认已提交
- `A4`：启动并验活 `lookme`
- `A5`：持续盯盘与解卡
- `A6`：对当前会话状态做收口分类判断
- `A7`：回写本地 task-list / `ce-sync-plan`
- `A8`：由 commander 执行 CE 生命周期同步
- `A9`：有下一会话则准备后续；无后续会话则停监控并转 idle

## Four Hard Stops

- 没读这页，不进 `A1`
- assignment 没写好，不进 `A3/A4`
- `A7` 没做，不进 `A8/A9`
- `A8` 写后没验真，不算 CE 已同步
- 没有下一会话真实任务，不允许让 `lookme` 继续跑
