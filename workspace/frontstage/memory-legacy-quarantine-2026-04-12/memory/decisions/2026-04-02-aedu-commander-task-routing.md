---
type: [KB:DECISION]
title: "AEdu Commander 任务路由与 Bot 分派规则"
created: 2026-04-02
updated: 2026-04-02
last_verified: 2026-04-02
source: Manual
confidence: high
tags: [aedu, commander, routing, bot, workflow]
related: [2026-04-02-aedu-local-repo-first-and-handoff-order, 2026-04-02-aedu-ce-lifecycle-rule, 2026-03-25-ce-task-governance, workbot]
version: v1.0
status: active
---

# AEdu Commander 任务路由与 Bot 分派规则

## 结论

- 当用户给出 AEdu 任务时，指挥官必须先查本地 `task-list`，再查 GitLab CE API，最后才做 bot 分派
- 本地执行真源优先级固定为：`代码/测试现场 > 本地 task-list > CE`
- `pm-bot`、`dev-bot`、`qa-bot`、`doc-bot`、`rea-bot` 的分派必须服从当前任务所在生命周期阶段，不允许跳阶段乱派
- 凡进入“审计 / 复核 / 真实性核对 / 一致性核对”链路的任务，第一轮必须先分派 `rea-bot`
- 指挥官负责维护 task-list 与 CE 正式状态，bot 只负责执行与回报

## Intake 顺序

### 1. 读取本地执行现场

- 先看当前工作树、代码、测试、文档和未提交改动
- 再看：
  - `/Users/busiji/workbot/workspace/projects/AEdu/pm-task-list.md`
  - `/Users/busiji/workbot/workspace/projects/AEdu/dev-task-list.md`
  - `/Users/busiji/workbot/workspace/projects/AEdu/qa-task-list.md`
  - `/Users/busiji/workbot/workspace/projects/AEdu/doc-task-list.md`
  - `/Users/busiji/workbot/workspace/projects/AEdu/rea-task-list.md`

### 2. 读取 CE 正式状态

- 只用 GitLab CE API
- 不用 Web UI，不用浏览器自动化
- CE 只回答“正式任务现在怎么记录”，不替代本地真实现场

### 3. 判定任务所处阶段

- `pm`：需求澄清、范围收敛、验收口径、任务拆解
- `dev`：实现、修复、最小验证
- `qa`：测试、验收、阻断判断
- `doc`：文档同步、验收材料同步、CE 同步准备
- `rea`：真实性、稳定性、一致性审计
- `ce`：正式状态同步与关单动作

### 4. 再做 bot 分派

- 指挥官按阶段和 `write_scope` 分派
- 不是看到任务就立刻起 bot
- 若任务带有审计、复核、真实性判断或一致性判断属性，先派 `rea-bot` 完成首轮审计，再决定是否转 `pm / dev / qa / doc`

## 真源优先级

### 1. 代码与测试现场

- 当前本地代码、测试输出、日志、未提交改动，是最高优先级真源

### 2. 本地 task-list

- 本地 task-list 是当前执行态和 owner 分配真源
- 若 task-list 与代码现场冲突，先以代码现场为准，再回写 task-list

### 3. CE

- CE 是正式状态真源
- 若 CE 与本地 task-list 冲突，不直接按 CE 派 bot；先按本地现场执行，再把 CE 补同步

## 分派规则

### 首轮审计优先规则

- 触发条件：
  - 用户明确要求“审计 / 复核 / review / audit / examine”
  - 需要先判断“是否允许继续 / 是否真实完成 / 是否口径一致”
  - 指挥官无法直接确定该任务应落到 `dev / qa / doc` 哪一阶段
- 处理动作：
  - 第一轮固定分派 `rea-bot`
  - 由 `rea-bot` 先给出 findings、evidence 和结论
  - 指挥官再根据首轮审计结论决定后续是否转 `dev / qa / doc / ce`
- 禁止事项：
  - 不允许 `qa-bot` 代替 `rea-bot` 做首轮真实性审计
  - 不允许 `doc-bot` 代替 `rea-bot` 做首轮一致性审计
  - 不允许指挥官在没有 `rea-bot` 首轮结论时直接宣布“可收口”

### Dev

- 进入条件：任务需要改代码、补测试、修复实现
- 指派对象：`dev-bot`
- 双开发位时：
  - `dev-a` 负责输入链、OCR、契约、事件组装
  - `dev-b` 负责 TWIN、GRAPH、OBS、非 OCR 主链测试
- 同一时间不得给两个 `dev-bot` 分配重叠 `write_scope`

### QA

- 进入条件：对应任务已 `dev_done`，需要形成测试或验收结论
- 指派对象：`qa-bot`
- `qa-bot` 默认只读；只有明确授权时才做最小修复

### Doc

- 进入条件：代码与 QA 证据已形成，但文档、验收文件、状态口径未同步
- 指派对象：`doc-bot`
- `doc-bot` 只改点名文档与验收材料，不越权改代码

### REA

- 进入条件：
  - 首轮审计 / 复核 / review / audit 请求
  - 代码、测试、task-list、文档、CE 之间有冲突
  - 或 CE 同步前需要最终真实性复核
- 指派对象：`rea-bot`
- `rea-bot` 默认只读，负责给“允许继续 / 需补同步后复核 / 不允许收口”结论

### CE

- 进入条件：本地至少已完成 `dev -> qa -> doc` 所需阶段
- 指派对象：指挥官自己
- CE 更新动作不下放给 bot

## 用户任务到 Bot 的标准表述

当用户只说一句任务时，指挥官必须把任务补成下面这些字段再分发：

- `目标`
- `阶段`
- `owner`
- `write_scope`
- `禁止事项`
- `最小验证`
- `交付格式`
- `与 CE / task-list 的关系`

## 固定派发模板

```markdown
任务阶段：`dev | qa | doc | rea | ce`

任务目标：
1. ...
2. ...

当前状态依据：
- 本地 task-list：...
- CE：...
- 代码/测试现场：...

owner：
- `dev-a | dev-b | qa | doc | rea | commander`

write_scope：
- ...

禁止事项：
- ...

最小验证：
- ...

交付格式：
- Diff 摘要 / 测试结果 / 剩余风险
- 或 Findings / Coverage Gaps / Acceptance / Conclusion
```

## AEdu 当前特别口径

- OCR 正式方案固定为 `百度 OCR API only`
- 不再以 local / ollama / glm-ocr 作为正式主路径
- 若相关代码仍保留 local provider，只能视为历史兼容或非正式 fallback，不得作为正式签收依据

## 一句话规则

- 用户给任务后，先查本地 task-list 与 CE；凡属审计/复核类任务，第一轮先派 `rea-bot`，再按阶段和 `write_scope` 做后续分派；CE 由指挥官自己维护，bot 不直接接 CE 正式收口。
