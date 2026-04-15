---
name: Stage Gate
description: 阶段汇总 / 交叉验证 / 收口模板
title: "[Gate] "
labels: []
assignees: []
---

## 1. Gate Name

<!-- 例如：round1_gate_cross_validation_and_closeout -->

## 2. Scope

- 本 gate 覆盖哪些任务 / packages / PR / milestones

## 3. Inputs Required

- 必须先完成的上游任务
- 必须收齐的 JSON / 证据 / closeout

## 4. Gate Checks

- 范围是否干净
- 是否有越界修改
- 是否有未关闭 blocker
- 是否满足 milestone exit criteria
- 是否允许进入下一轮

## 5. Gate Bots

- `qa-bot`：
- `rea-bot`：
- 其他 bot（如需要）：

## 6. PASS Criteria

- 同时满足哪些条件才可 PASS

## 7. BLOCKED Criteria

- 哪些真实问题会直接导致 BLOCKED

## 8. Deliverables

- 最终 gate JSON
- 交叉验证记录
- remaining blockers / resolution notes

## 9. Next Step Rule

- PASS 后允许进入什么
- BLOCKED 后只允许做什么

## 10. Notes

- 不得跨轮推进
- 不得把未验证结论伪装成通过
