# MEMORY - Workbot Boot

## Load Order
1. NOW.md
2. ROUTER.md
3. memory/short-index.md
4. memory/log/YYYY-MM-DD.md

## Root Workspace
- 当前唯一总控工作区：`/Users/busiji/workbot/workspace`
- `agents/molt/workspace/` 仅作为 OpenClaw Molt 的来源工作区，不再充当全仓启动入口

## Quick Reference
- `Workspace Home` → `INDEX.md`
- `MRD` → `memory/kb/global/memory-router-design.md`
- `Project Canonical` → `memory/kb/projects/workbot.md`
- `Docs Index` → `memory/docs/INDEX.md`
- `KB Index` → `memory/kb/INDEX.md`
- `Projects Index` → `projects/INDEX.md`

## Hard Rules
- 只有 `NOW.md` 允许覆写
- `memory/log/` 只追加，不覆写
- `memory/kb/` 只允许 read-first-CRUD，禁止静默覆盖
- 项目真相写 `memory/kb/projects/`、`memory/kb/decisions/`、`memory/kb/global/`
- 研究资料写 `memory/docs/`
- 交付产物写 `projects/`
- 冷资料与错误记忆写 `../archive-memory/`
