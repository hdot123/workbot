---
type: [KB:PROJECT]
title: "Workbot"
created: 2026-03-24 10:13
updated: 2026-04-11 00:00
source: [Manual]
confidence: high
tags: [workbot, workspace, control-plane, memory-system, cmux]
related: [AEdu, platform-capabilities, workbot-memory-system]
version: v2.0
status: active
last_verified: 2026-04-11
---

# Workbot

## 定位
- `workbot` 是当前仓库级控制面与项目容器，不是单一业务项目目录。
- 它承载统一的总记忆系统、项目执行面、共享能力层和运行产物层。
- 总记忆系统的本体规则写在 `../global/workbot-memory-system.md` 与 `../global/workbot-memory-routing.md`，本文件只定义 `workbot` 这个项目容器本身的稳定事实。

## 与总记忆系统的关系
- `workbot` 只有一套总记忆系统。
- `workbot` 既是仓库名，也是承载这套总记忆系统的顶层项目容器。
- 项目域如 `AEdu`、能力域如 `platform-capabilities`，都属于这套总系统中的派生对象。

## 当前一级结构
- 业务项目域：`AEdu/`
- 平台与能力域：`app/`、`agents/`、`gpt-web-to/`
- 记忆与治理工作区：`workspace/`
- 运行产物与导出结果：`workspace/artifacts/`

## 控制面事实
- 根级 `workspace/` 是唯一正式总控工作区。
- `workspace/memory/kb/**` 是长期真相层；`workspace/memory/docs/**` 是资料层；`workspace/projects/**` 与 `workspace/artifacts/**` 是执行面与产物层。
- `cmux` 是当前日常运行面，但运行面不等于角色定义，也不等于记忆系统本体。

## Truth Basis

### Source Refs
- `/Users/busiji/workbot/workspace/INDEX.md`
- `/Users/busiji/workbot/workspace/memory/docs/记忆系统全景文档.md`

### Authority Refs
- `/Users/busiji/workbot/workspace/memory/kb/global/workbot-truth-model.md`
- `/Users/busiji/workbot/workspace/memory/kb/global/workbot-memory-system.md`

### Evidence Refs
- `/Users/busiji/workbot/workspace/tools/memory_hook_gateway.py`
- `/Users/busiji/workbot/workspace/tools/validate_memory_system.py`

### Conflict Status
- `resolved`

## 相关项目域
- [AEdu](/Users/busiji/workbot/workspace/memory/kb/projects/AEdu.md)
- [platform-capabilities](/Users/busiji/workbot/workspace/memory/kb/projects/platform-capabilities.md)

## 历史说明
- 旧的 `../global/projects/workbot.md` 自 2026-04-11 起仅保留为兼容跳转与历史痕迹，不再作为 active canonical。
