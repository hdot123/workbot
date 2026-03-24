---
title: "Long-Term Memory Index"
created: 2026-03-24 10:13
updated: 2026-03-24 10:13
source: [Manual]
confidence: high
tags: [longterm, memory, governance]
related: [../global/memory-router-design.md, ../projects/workbot.md]
version: v1.0
status: active
last_verified: 2026-03-24
---

# Long-Term Memory Index

## Purpose
- `memory/kb/longterm/` 用于承载跨 run、跨阶段仍然成立的长期稳定记忆
- 它不是普通项目笔记区，也不是日志区

## Admission Rules
- 必须有明确来源
- 必须可验证
- 必须在 30-90 天尺度内仍然有效
- 冲突不能静默覆盖，只能 `superseded` 或 `conflict`
- 不满足条件的内容回退到 `projects/`、`lessons/` 或 `log/`

## Structure
- `user-profile/`：长期稳定的人物画像
- `stable-preferences/`：长期稳定的偏好与工作习惯
- `stable-project-principles/`：稳定项目原则与长期约束
- `cross-project-memory/`：跨项目长期知识
