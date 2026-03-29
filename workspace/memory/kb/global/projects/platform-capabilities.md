---
type: [KB:PROJECT]
title: "platform-capabilities"
created: 2026-03-24 10:13
updated: 2026-03-24 10:13
source: [Manual]
confidence: high
tags: [platform, capabilities, agents, skills, app]
related: [workbot, opencli, openclaw-molt]
version: v1.0
status: active
last_verified: 2026-03-24
---

# platform-capabilities

## 定位
- 本文件汇总 `workbot` 中不需要单独占用一级项目入口的辅助能力层。
- 这些能力对总项目重要，但不是独立业务主项目。

## Included Domains

### app
- `app/` 当前是轻量平台目录，现阶段主要承载 `models/`。
- 物理目录：`/Users/busiji/workbot/app`
- 总控项目区：`/Users/busiji/workbot/workspace/projects/app`

### agents
- `agents/` 是全仓共享代理与角色定义目录。
- 仓库级可复用角色的 canonical 位置是 `workbot/agents/`，不是各项目自带的 wrapper。
- 物理目录：`/Users/busiji/workbot/agents`
- 总控项目区：`/Users/busiji/workbot/workspace/projects/agents`

### skills-gpt-web-to
- `gpt-web-to/` 是 skill 能力包，不按一级业务项目管理。
- 它通过 `SKILL.md` 暴露能力，并依赖 opencli 的网页执行链路。
- 物理目录：`/Users/busiji/workbot/gpt-web-to`
- 总控项目区：`/Users/busiji/workbot/workspace/projects/skills`
