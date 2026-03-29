---
type: [KB:PROJECT]
title: "Workbot"
created: 2026-03-24 10:13
updated: 2026-03-30 02:35
source: [Manual]
confidence: high
tags: [workbot, workspace, obsidian, mrd, control-plane]
related: [AEdu, platform-capabilities]
version: v1.0
status: active
last_verified: 2026-03-30
---

# Workbot

## 定位
- `workbot` 是总控工作台，不是单一业务项目仓。
- 根级 [workspace](/Users/busiji/workbot/workspace) 是新的 MRD + Obsidian 总控工作区。
- 代码层、能力层、记忆治理层、产物层需要分开治理，不再混写。

## 当前一级结构
- 业务项目：`AEdu/`
- 平台项目：`app/`
- 能力层：`agents/`、`gpt-web-to/`
- 治理层：`workspace/`
- 产物与冷归档：`artifacts/`、`archive-memory/`

## 工作区原则
- `workspace/` 承载总项目的记忆、知识、日志、项目真相。
- `docs/` 保留兼容入口，不再作为主工作区。
- 历史项目材料统一从主入口剥离，集中暂存到 `history-projects/`。

## 当前控制面口径
- `tmux-skills` 负责前台 `formal-session` 的 pane 生成与 stopped-pane handoff。
- tmux handoff 的目标真源是 monitor 对应的 `CODEX_THREAD_ID`，且该值必须是 Codex app thread id。
- stopped-pane delivery 当前通过常驻 app-server bridge 投递到目标 app thread，不再通过 `codex exec resume` 投递到本地 CLI session。

## 相关项目入口
- [AEdu](/Users/busiji/workbot/workspace/memory/kb/projects/AEdu.md)
- [platform-capabilities](/Users/busiji/workbot/workspace/memory/kb/projects/platform-capabilities.md)

## 已删除项目
- `opencli/` 已于 2026-03-29 从工作区物理删除。
- 相关记忆仅保留在历史/研究资料中，不再视为当前项目入口。

## 历史来源项目
- 历史项目材料统一暂存于 [history-projects](/Users/busiji/workbot/workspace/history-projects/INDEX.md)
