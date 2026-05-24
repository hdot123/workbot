---
type: [KB:PROJECT]
title: "platform-capabilities"
created: 2026-03-24 10:13
updated: 2026-04-11 00:00
source: [Manual]
confidence: high
tags: [platform, capabilities, agents, app, shared-domain]
related: [workbot]
version: v2.0
status: active
last_verified: 2026-04-11
---

# platform-capabilities

## 定位
- 本文件汇总 `workbot` 中不单独占用一级业务项目入口的共享能力域。
- 这些能力域对总项目重要，但它们不是并列业务主项目。

## Included Domains

### app
- `app/` 当前是轻量平台目录，现阶段主要承载 `models/`。
- 物理目录：`/Users/busiji/workbot/app`
- 执行面目录：尚未单独建位；当前默认并入总项目执行面。

### agents
- `agents/` 是仓库级共享角色与能力定义目录。
- 仓库级可复用角色定义的物理真源位于 `/Users/busiji/workbot/agents/`；关于其治理边界的正式 canonical 仍由本项目文件和 global 规则承接。
- 物理目录：`/Users/busiji/workbot/agents`
- 执行面目录：尚未单独建位；当前默认并入总项目执行面。

### skills-gpt-web-to
- `gpt-web-to/` 是能力包与技能目录，不按一级业务项目管理。
- 物理目录：`/Users/busiji/workbot/gpt-web-to`
- 执行面目录：尚未单独建位；当前默认并入总项目执行面。

## 规则
- 能力域可以被项目引用，但不直接定义总记忆系统本体。
- 如果能力域中的某条约束成为跨项目稳定规则，应提升到 `../global/`。

## Truth Basis

### Source Refs
- `/Users/busiji/workbot/AGENTS.md`
- `/Users/busiji/workbot/memory/kb/projects/workbot.md`

### Authority Refs
- `/Users/busiji/workbot/memory/kb/global/workbot-truth-model.md`
- `/Users/busiji/workbot/memory/kb/global/workbot-memory-system.md`

### Evidence Refs
- `/Users/busiji/workbot/app/models/twin_ingest_contract.py`
- `/Users/busiji/workbot/gpt-web-to/SKILL.md`

### Conflict Status
- `resolved`

## 历史说明
- 旧的 `../global/projects/platform-capabilities.md` 自 2026-04-11 起仅保留为兼容跳转与历史痕迹，不再作为 active canonical。
