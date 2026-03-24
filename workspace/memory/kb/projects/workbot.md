---
type: [KB:PROJECT]
title: "Workbot"
created: 2026-03-24 10:13
updated: 2026-03-24 10:13
source: [Manual]
confidence: high
tags: [workbot, workspace, obsidian, mrd, control-plane]
related: [AEdu, opencli, platform-capabilities, openclaw-molt]
version: v1.0
status: active
last_verified: 2026-03-24
---

# Workbot

## 定位
- `workbot` 是总控工作台，不是单一业务项目仓。
- 根级 [workspace](/Users/busiji/workbot/workspace) 是新的 MRD + Obsidian 总控工作区。
- 代码层、能力层、记忆治理层、产物层需要分开治理，不再混写。

## 当前一级结构
- 业务项目：`AEdu/`
- 平台项目：`opencli/`、`app/`
- 能力层：`agents/`、`gpt-web-to/`
- 治理层：`workspace/`
- 产物与冷归档：`artifacts/`、`archive-memory/`

## 工作区原则
- `workspace/` 承载总项目的记忆、知识、日志、项目真相。
- `docs/` 保留兼容入口，不再作为主工作区。
- `agents/molt/workspace/` 是 OpenClaw Molt 的来源工作区，不再充当全仓主工作区。

## 相关项目入口
- [AEdu](/Users/busiji/workbot/workspace/memory/kb/projects/AEdu.md)
- [opencli](/Users/busiji/workbot/workspace/memory/kb/projects/opencli.md)
- [platform-capabilities](/Users/busiji/workbot/workspace/memory/kb/projects/platform-capabilities.md)

## 历史来源项目
- [openclaw-molt](/Users/busiji/workbot/workspace/memory/kb/projects/openclaw-molt.md)
