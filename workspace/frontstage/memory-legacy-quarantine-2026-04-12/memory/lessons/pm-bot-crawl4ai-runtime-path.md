---
type: [KB:LESSON]
title: "Lesson: pm-bot 的 Crawl4AI 调用必须在启动链内收敛"
created: 2026-04-07
updated: 2026-04-18
last_verified: 2026-04-18
status: superseded
tags: [cmux, pm-bot, crawl4ai, mcp]
confidence: high
source: Manual
version: v1.0
related: [mcp-config, runbook]
---

# Lesson: pm-bot 的 Crawl4AI 调用必须在启动链内收敛

## Quarantine Status

本文件位于 `workspace/frontstage/memory-legacy-quarantine-2026-04-12/`，仅保留历史实现记录，不构成当前 active lesson。

- 当前状态：`superseded`（quarantine historical residue only）
- active replacement lesson：
  `/Users/busiji/workbot/workspace/memory/kb/lessons/pm-bot-global-binding-and-legacy-fence.md`
- 若与当前仓库 truth 冲突，以 `AGENTS.md`、`cmux` canonical 和 active lesson 为准。

## 问题现象
- `cmux` 交互态 `pm-bot` 会先尝试 `Bash(mcp__crawl4ai__md ...)`
- 有时还会转去读本地 `.claude` 文件，自证 crawl4ai 是否“已加载”
- 即使 `claude mcp get crawl4ai` 和 `/mcp` 都显示 `connected`，交互态仍可能先走 fallback

## 根因
- 交互启动链给了模型过宽的 shell 面和自检空间
- 仅改身份 md 不足以约束交互态 tool 路由
- 必须在 `cmux` bootstrap 里收敛 `pm-bot` 的启动参数，而不是靠全局 wrapper 修补

## 干净方案
- 只对 `pm-bot` 注入：
  - `--bare`
  - `--strict-mcp-config`
  - 单独的 `crawl4ai` MCP 配置
  - `--append-system-prompt`，明确原生 MCP 可用
  - `--disallowed-tools 'Bash(*)'`
- `pm-bot` 身份文件只声明 `crawl4ai` 能力，不再声明 Bash
- 不再依赖 `~/bin/claude` 这类全局 wrapper
- 只要 `claude mcp get crawl4ai` 和 `/mcp` 都是 `connected`，网页事实任务就直接走原生 `mcp__crawl4ai__*`

## 验证结果
- 新 runtime 中，`pm-bot` 已经直接出现原生调用 `crawl4ai - md (MCP)(url: "https://example.com")`
- 最终返回 `页面标题：Example Domain`
- 证明问题已经从“先走 Bash fallback”收敛到“直接走原生 MCP”

## 以后排查顺序
1. 看 `pm-bot` 启动命令是否带 `--bare`、`--strict-mcp-config` 和 crawl4ai 专属 MCP
2. 看 `claude mcp get crawl4ai`
3. 看 `/mcp` 是否 `connected`
4. 只有在 `tool not found` 或 `/mcp` 明确 `failed/absent` 时，才判断 crawl4ai 不可用
