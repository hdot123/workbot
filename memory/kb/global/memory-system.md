# 记忆系统规则

本文件是 workbot 项目的全局记忆规范片段。

## Truth Basis

### Source Refs
- `INDEX.md`

### Authority Refs
- `project-map/INDEX.md`

### Evidence Refs
- `tools/memory_hook_gateway.py`

### Conflict Status
- resolved


---

<!-- LEGACY_WORKBOT_SOURCE_BEGIN
Source: memory/kb/global/workbot-memory-system.md
Archived-Source: history-projects/memory/retired-workspace-memory-20260513-043734/memory/kb/global/workbot-memory-system.md
SHA256: 184f2ee2e13078af04014909698976843f6578943d3fb82a754fcc800b2de37f
Migrated: 2026-05-13T04:20:23.739140+00:00
Action: append-marker
Status: RETIRED/ARCHIVED
---

# Workbot Memory System Rules

Status: rule-only, records-cleared
Scope: adapter

> 本文件是 workbot adapter 级别的记忆系统规则，不是模块默认记忆系统。
> 其他 adapter 可以定义自己的记忆系统规则，不受本文件约束。

## Layer Priority
1. Code and runtime facts
2. Locked project documents
3. Rule layer
4. Historical files as evidence only

## Policy
- No historical file may overwrite locked truth.
- Any conflict requires explicit owner confirmation.

## Truth Basis

### Source Refs
- `INDEX.md`

### Authority Refs
- `project-map/legal-core-map.md`

### Evidence Refs
- `tools/memory_hook_gateway.py`

### Conflict Status
- `resolved`


LEGACY_WORKBOT_SOURCE_END -->
