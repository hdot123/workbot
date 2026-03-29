---
type: [KB:DECISION]
title: "Canonical Map - 决策图"
created: 2026-03-04
updated: 2026-03-30
last_verified: 2026-03-30
status: active
tags: []
confidence: high
source: Manual
version: v1.0
related: []
---

# Canonical Map - 决策图

> 用途：记录所有决策的映射关系和依赖

## 元数据
- 创建日期：2026-03-02
- 维护者：Molt King
- 状态：维护中

## 决策索引

| 决策ID | 标题 | 日期 | 状态 | 依赖 |
|--------|------|------|------|------|
| 2026-03-30-tmux-handoff-app-thread-delivery | tmux handoff 投递切换到 Codex app thread | 2026-03-30 | active | 2026-03-25-workbot-project-agents-and-runtime-surfaces |
| 2026-03-25-workbot-project-agents-and-runtime-surfaces | Workbot 项目级 Agents 与正式运行面规范 | 2026-03-25 | active | - |
| 2026-03-25-ce-task-governance | CE 任务治理规范 | 2026-03-25 | active | - |

## 决策分类

### 架构决策
- `2026-03-30-tmux-handoff-app-thread-delivery`
- `2026-03-25-workbot-project-agents-and-runtime-surfaces`

### 流程决策
- `2026-03-25-ce-task-governance`

### 工具决策
- `2026-03-30-tmux-handoff-app-thread-delivery`

## 决策依赖图

```mermaid
graph TD
    "2026-03-25-workbot-project-agents-and-runtime-surfaces" --> "2026-03-30-tmux-handoff-app-thread-delivery"
```

## 待补充
- [ ] 继续补齐 2026-03 之前的历史决策映射
- [ ] 为更多决策补充依赖关系
