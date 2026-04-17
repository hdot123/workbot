---
type: [KB:DECISION]
title: "CMUX MCP Cross-Bot Stability and Memory Guard"
shortname: CMUX-MCP-GUARD-2026-04-16
status: active
created: 2026-04-16
updated: 2026-04-16
source: local-verified
confidence: high
tags: [decision, cmux, mcp, crawl4ai, bootstrap, guardrail, cross-verify]
related: [workbot-project-canonical, workbot-truth-model, workbot-hook-contract]
---

# CMUX MCP Cross-Bot Stability and Memory Guard

## Decision

`workbot` 的 cmux 运行时必须采用以下固定策略，防止“配置存在但工具不可调用”再次出现：

1. MCP 配置合并必须包含 `~/.claude.json` 的项目作用域块：
   `projects[/Users/busiji/workbot].mcpServers`。
2. 只要允许外部 MCP 工具，启动必须注入 `--mcp-config` 且启用 `--strict-mcp-config`。
3. `idle-default` 不允许退化为全 bot 通用 `Read`；必须按 bot 下发默认工具映射。
4. agent `tools` 声明统一保留双前缀：
   `mcp__claude_code__*` + `mcp__claude-code__*`。
5. `pm-bot` 启动 smoke 允许一次冷启动重试（针对首轮 `tool_not_found` 抖动）。
6. 主线程验收必须走 cmux 代理交叉验证（R1-R4），不能仅看静态配置文件。

## Root Cause (This Incident)

1. 旧 bootstrap 只读顶层 `mcpServers`，遗漏项目作用域 `mcpServers`。
   结果：`pm-bot` 有 `crawl4ai` 声明但运行时未注入。
2. `idle-default` 回退逻辑过于粗暴，导致其他 bot 近似只读。
3. Claude MCP 前缀存在命名差异，声明不统一时会出现可调用性漂移。
4. smoke 解析对带前缀输出（如 `⏺ ...`）不稳，且未对冷启动抖动做重试。

## Prevention Gate (Mandatory)

每次涉及 cmux/MCP 变更后，主线程必须完成同一工作区的四回合验证：

1. `R1`：`dev/qa/doc/rea` 各自回报可调用工具清单。
2. `R2`：`dev` + `qa` 独立执行 `mcp__claude_code__Read`。
3. `R3`：`pm` 执行 `mcp__crawl4ai__md` 并返回成功状态（`status=200` 或等价）。
4. `R4`：`rea` 对 manifest/settings 做一致性核对（建议 deterministic 比对）。

若任一回合失败，不得宣称“修复完成”。

## Automation Gate (Required Command)

为避免人工读屏误判，交叉验证改为脚本化门禁，命令固定如下：

```bash
python3 /Users/busiji/workbot/workspace/tools/cmux_cross_verify.py \
  --workspace workspace:47 \
  --project-dir /Users/busiji/workbot \
  --timeout-seconds 25 \
  --retries 2
```

执行规范：

1. 以退出码作为门禁结论（`0=passed`，非零=failed）。
2. 只认 `/Users/busiji/workbot/workspace/artifacts/cmux-runtime/cross-verify-latest.json` 的最终结果。
3. 若失败，先修复再重跑，不允许跳过或口头判定通过。

本次补丁同时修复了脚本解析层的两类误判来源：

1. `cmux read-screen` 折行导致 marker JSON 跨行，旧逻辑按单行解析会误报 `timeout`。
2. marker 文本过长导致输出再次折行，已改为短 marker 协议。

## Memory Routing

- 本条决策属于 active canonical，必须保留在 `workspace/memory/kb/decisions/`。
- 后续若再出现同类故障，先引用本决策，再做新一轮差异定位；不要重走无门禁排查。

## Truth Basis

### Source Refs
- `/Users/busiji/.agents/skills/cmux/scripts/bootstrap_claude_runtime.py`
- `/Users/busiji/.agents/skills/cmux/scripts/generate_cmux_assignments.py`
- `/Users/busiji/workbot/.claude/agents/pm-bot.md`
- `/Users/busiji/workbot/.claude/agents/dev-bot.md`
- `/Users/busiji/workbot/.claude/agents/qa-bot.md`
- `/Users/busiji/workbot/.claude/agents/doc-bot.md`
- `/Users/busiji/workbot/.claude/agents/rea-bot.md`

### Evidence Refs
- `/Users/busiji/workbot/docs/project-management/main-thread-cmux-mcp-fix-plan-2026-04-16.md`
- `/Users/busiji/workbot/workspace/artifacts/cmux-runtime/cross-verify-report-2026-04-16.json`
- `/Users/busiji/workbot/workspace/artifacts/cmux-runtime/pm-bot-smoke-report.json`

### Conflict Status
- `resolved`
