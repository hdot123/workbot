---
name: Standard Task
description: 单个正式任务模板（Issues = 单任务）
title: "[Task] "
labels: []
assignees: []
---

## 1. Task Name

<!-- 例如：round1_package_a_core_behavior_characterization -->

## 2. Goal

- 本任务的唯一目标是什么

## 3. Allowed Scope

- 本任务允许修改的文件 / 模块 / 行为面
- 必须保持单任务、单范围、可 review、可回滚

## 4. Forbidden Scope

- 本任务禁止触碰的文件 / 模块 / 轮次
- 禁止越界到其他 package / 下一个 round / 无关治理项

## 5. Entry Criteria

- 进入本任务前必须满足的前置条件
- 对应 gate / milestone / source comment

## 6. Exit Criteria

- 本任务完成的硬标准
- 什么情况下才算 PASS

## 7. Tests Required

- 必跑测试
- characterization / gate / smoke / parity / regression

## 8. Execution Plan

- `Execution Bot`：
- `Gate Bot`：
- 是否需要 `doc-bot`：
- 是否要求交叉验证：

## 9. Deliverables

- 本任务应交付的内容
- 结果 JSON / 覆盖矩阵 / snapshot / closeout 等

## 10. Blocked Conditions

- 哪些真实 blocker 会导致本任务必须输出 `BLOCKED`

## 11. Source Of Truth

- 来源 issue / 评论 / 文档 / PR
- 当前是否属于正式下发：`Yes / No`

## 12. Notes

- 其他约束
- Scope guard
- 不得伪装为“补测试”或“顺手修复”
