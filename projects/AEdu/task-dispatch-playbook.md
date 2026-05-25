# AEdu Task Dispatch Playbook

## Purpose
- 这页只给指挥官使用
- 作用是把“用户说一句任务”转换成可直接派给 bot 的标准派单

正式会话开始前必须先读：

- [A1-A9 Session Brief](/Users/busiji/workbot/docs/a1-a9-session-brief.md)

## 固定顺序

1. 看本地代码和测试现场
2. 看四张本地单
3. 看 CE API 正式状态
4. 判定阶段
5. 判定是否先走 `rea-bot` 首轮审计
6. 选 bot
7. 写清 `write_scope`
8. 先写 assignment 真源
9. 再发任务
10. 派发后立刻复查 pane，确认消息已真正提交

## 四张本地单

- `dev-task-list.md`
- `qa-task-list.md`
- `doc-task-list.md`
- `rea-task-list.md`

## 阶段与 bot 对应

- `dev` -> `dev-bot`
- `qa` -> `qa-bot`
- `doc` -> `doc-bot`
- `rea` -> `rea-bot`
- `ce` -> 指挥官自己处理

## 首轮审计优先

- 只要任务带有“审计 / 复核 / review / audit / examine / 一致性 / 真实性”属性，第一轮必须先派 `rea-bot`
- `rea-bot` 先给 findings、evidence 和 conclusion
- 指挥官再根据 `rea-bot` 结论决定是否转 `dev / qa / doc / ce`

## 推荐运行面

- 审计密集期默认使用 `4 pane`：`dev-bot / rea-bot / qa-bot / doc-bot`
- 只有当当前会话确无独立审计位需求，且 `rea-bot` 不会成为首轮瓶颈时，才允许临时切回 `2 dev + 1 qa + 1 doc`
- 运行面怎么排，不改变“首轮审计必须先过 `rea-bot`”这条规则
- `lookme` 只有在 assignment 已落盘、且至少有 1 条真实 active assignment 时才允许启动

## 双 Dev 分配

- `dev-a`：输入链 / OCR / 契约 / 事件组装
- `dev-b`：TWIN / GRAPH / OBS / 非 OCR 主链测试
- 同一时间两个 `dev-bot` 不允许写同一文件组

## 任务派发表述模板

```markdown
任务阶段：`dev | qa | doc | rea`

目标：
1. ...
2. ...

当前状态依据：
- 本地 task-list：...
- CE：...
- 代码/测试现场：...

owner：
- ...

write_scope：
- ...

禁止事项：
- ...

最小验证：
- ...

交付格式：
- ...
```

## AEdu 当前固定口径

- OCR 正式方案：`百度 OCR API only`
- `accept edits` 只有在“修改确认提醒”语义下才走 SOP
- CE 状态只用 API 查询和更新
- `done` 前不允许因为 `dev_done` 或 `qa_done` 直接关 CE issue
