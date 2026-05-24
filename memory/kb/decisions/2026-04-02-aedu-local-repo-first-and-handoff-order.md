---
type: [KB:DECISION]
title: "AEdu 本地仓库真源与任务交接顺序"
created: 2026-04-02
updated: 2026-04-02
last_verified: 2026-04-02
source: Manual
confidence: high
tags: [aedu, local-repo, workflow, handoff, github]
related: [2026-04-02-aedu-ce-lifecycle-rule, 2026-03-25-ce-task-governance, workbot]
version: v1.0
status: active
---

# AEdu 本地仓库真源与任务交接顺序

## 结论

- 当前 GitHub 上的版本视为正常基线
- 之后每次 AEdu 任务都必须基于当前机器上的最新本地仓库执行
- 默认交接顺序固定为：`rea-bot(首轮审计) -> dev -> qa -> doc -> codex submit/push`
- 第一轮审计必须先由 `rea-bot` 完成；后续若需要最终收口复核，可再次进入 `rea-bot`
- `codex submit/push` 仍是独立最终动作，不并入审计职责

## 仓库真源规则

- 运行任务时，以当前工作机上的本地仓库为直接执行真源
- GitHub 用于提供正常基线与历史参考，不替代任务执行时的本地现场
- 若 GitHub 与本地仓库状态不一致，应先以本地实际工作树为准判断当前任务现场，再决定是否需要同步
- 任何任务开始前，默认从“最新本地仓库”读取代码、测试、文档和未提交状态

## 默认交接顺序

### 1. REA Bot（首轮审计）

- 只要任务先需要判断真实性、稳定性、一致性或是否允许继续，第一轮必须先进入 `rea-bot`
- `rea-bot` 负责：
  - 核对“说完成”和“实际完成”是否一致
  - 核对代码、测试、文档、CE 状态是否一致
  - 给出“允许继续 / 需补同步后复核 / 不允许收口”入口结论
- `rea-bot` 不替代 `qa` 的测试职责
- `rea-bot` 的首轮结论出来前，不允许直接进入正式收口判断

### 2. Dev

- `dev` 负责实现、修复、最小验证
- `dev` 的完成状态是 `dev_done`
- `dev` 完成后只能交付给 `qa`，不能直接宣布任务完成

### 3. QA

- `qa` 负责测试、验收、阻断判断
- `qa` 的完成状态是 `qa_done`
- `qa` 完成后交付给 `doc`

### 4. Doc

- `doc` 负责同步状态文档、验收材料和 CE 准备信息
- `doc` 的完成状态是 `doc_synced`
- `doc` 完成后才允许进入正式收口准备

### 5. Codex Submit/Push

- `codex` 在 `doc` 之后执行最终提交与 push
- `codex` 只在以下条件满足后才允许执行：
  - `rea-bot` 已完成首轮审计
  - `dev` 已完成
  - `qa` 已完成且无未消除阻断
  - `doc` 已完成同步
- `codex submit/push` 是交付动作，不替代 QA、Doc 或审计

## 与 CE 的关系

- CE 仍只承接正式任务状态
- CE 上的同一张 issue 继续贯穿 `dev -> qa -> doc -> ce -> done`
- `rea-bot` 的首轮结论是后续执行入口证据；若有收口前复核，再作为补充证据，但不单独占用新的 CE 主流程状态
- `codex submit/push` 不改变 CE 生命周期规则；提交与 push 不等于 CE 可提前关单

## 今日落地口径

- AEdu 当前三张 task list 已按 `dev / qa / doc` 分层
- `rea-bot` 固定作为首轮审计入口；后续如需再审，可在 `doc` 之后补一次收口复核
- 若后续流程需要调整顺序，必须先形成新决策，再覆盖本规则
