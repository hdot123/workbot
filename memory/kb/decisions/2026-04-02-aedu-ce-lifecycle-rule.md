---
type: [KB:DECISION]
title: "AEdu CE 正式任务全生命周期续写规则"
created: 2026-04-02
updated: 2026-04-02
last_verified: 2026-04-02
source: Manual
confidence: high
tags: [aedu, gitlab, ce, lifecycle, state-flow]
related: [2026-03-25-ce-task-governance, workbot]
version: v1.0
status: active
---

# AEdu CE 正式任务全生命周期续写规则

## 结论

- AEdu 的一张 GitLab CE 正式任务单必须贯穿 `dev -> qa -> doc -> ce -> done` 全生命周期
- `dev_done` 不是关单条件，`qa_done` 也不是关单条件
- 只有当任务真正到达 `done`，对应 CE issue 才允许关闭
- QA、Doc、Commander 后续进度必须继续写回同一张 CE issue，不允许因为开发完成而关闭原 issue，再开替代单续写

## 适用范围

- 适用于 `aedu/workbot` 项目当前主线任务与阶段任务
- 适用于 CE 中的阶段单、主线单、模块单和关键实现单
- 不适用于 bot 内部分工记录；bot 分工仍只出现在 task list、评论或日报

## 背景

- 2026-04-01 / 2026-04-02 的 AEdu 审计表明：本地开发进度、QA 证据、文档同步和 CE 状态之间存在时间差
- 若按“开发完成即关闭 CE issue”执行，后续 QA 与 Doc 将失去在同一正式任务上续写状态的落点
- 这会造成：
  - 正式任务生命周期被切断
  - 后续状态只能写在评论外部或另起单，形成双口径
  - CE 无法继续承担“当前做到哪一步、卡在哪里、下一步是什么”的正式裁决职责

## 正式规则

### 1. 生命周期规则

- 一张正式任务只允许一个 CE issue 承接全生命周期
- `dev` 只负责把任务推进到 `dev_done`
- `qa` 在同一 issue 上继续补 `qa_done` 或 `blocked`
- `doc` 在同一 issue 上继续补 `doc_synced`
- `commander` 在同一 issue 上执行最终 `ce_synced` / `done`

### 2. 关闭规则

- `dev_done` 后 CE issue 必须保持 `opened`
- `qa_done` 后 CE issue 必须保持 `opened`
- `doc_synced` 后 CE issue 仍保持 `opened`，直到 commander 完成 CE 正式收口
- 只有满足以下条件时才允许关闭：
  - 对应实现文件已存在
  - 至少有一条最小验证证据
  - QA 已形成正式结论且没有未消除阻断
  - 文档与验收材料已同步到当前事实
  - 同一 CE issue 上已经补齐 `dev_done -> qa_done -> doc_synced -> ce_synced` 记录

### 3. 状态映射规则

- 本地 `todo` / `in_progress`：CE 保持 `opened`，必要时补进展评论
- 本地 `blocked`：CE 保持 `opened`，补阻塞评论与解除条件
- 本地 `dev_done`：CE 保持 `opened`，评论“开发完成，待 QA”
- 本地 `qa_done`：CE 保持 `opened`，评论“QA 完成，待文档同步”
- 本地 `doc_synced`：CE 保持 `opened`，评论或更新描述，准备正式收口
- 本地 `ce_synced`：CE 已完成本轮同步动作
- 本地 `done`：对应 CE issue 才允许关闭

## 与既有规则的关系

- 本规则是 [2026-03-25-ce-task-governance.md](/Users/busiji/workbot/memory/kb/decisions/2026-03-25-ce-task-governance.md) 的补充细化，不替代其“CE 不给 bot 直接挂任务”的原则
- 既有治理规则回答“谁是正式任务主体”，本规则回答“正式任务如何跨 dev / qa / doc 续写直到收口”

## 今天的执行留痕

- 已在 `aedu/workbot` 的 `#28`、`#30`、`#33`、`#37-69` 上写入 `[Audit sync 2026-04-02]` 状态纠偏评论
- 本次只做正式状态纠偏，不做关单动作
- 本地执行文件：
  - `projects/AEdu/dev-task-list.md`
  - `projects/AEdu/qa-task-list.md`
  - `projects/AEdu/doc-task-list.md`
  - `projects/AEdu/ce-sync-plan.md`
