---
type: [KB:DECISION]
title: "Workbot Project Agents and Runtime Surfaces"
shortname: WORKBOT-AGENTS-RUNTIME-2026-03-25
status: active
created: 2026-03-25
updated: 2026-04-18
source: local-canonical
confidence: high
tags: [decision, workbot, cmux, agents, runtime, commander]
related: [workbot-project-canonical, workbot-truth-model, workbot-hook-contract]
---

# Workbot Project Agents and Runtime Surfaces

## Decision

`workbot` 的仓库级身份真相与仓库面向运行时定位固定如下：

1. 全局 bot body 只定义在 `/Users/busiji/.claude/agents/` 目录。
2. `workbot` 的项目 binding / activation 层只定义在 `/Users/busiji/workbot/.claude/agents/` 目录。
3. `/Users/busiji/workbot/agents/` 是 retired historical residue，不再属于当前仓库真相。
4. `/Users/busiji/workbot/.codex/agents/` 已删除，不是当前 formal identity chain。
5. `cmux` 是当前唯一正式 runtime carrier。
6. `workbot` 当前正式项目内拓扑是 `5+1`：
   - `pm-bot`
   - `dev-bot`
   - `qa-bot`
   - `doc-bot`
   - `rea-bot`
   - `cmux-browser` board pane
7. `cmux-browser` 是 board surface，不是正式 bot 身份。
8. 外部 `main-thread` 是调度 / 裁定上下文，位于项目 `cmux` workspace 之外，不需要项目本地 agent 文件。

## Commander Core

`workbot` 的 commander 级核心运行规则固定如下：

1. `assignment` 必须先于 pane dispatch 存在，`cmux` 只消费 assignment，不发明任务。
2. active assignment 在启动前必须通过 `dispatch_ready` gate。
3. `dispatch_owner` 固定为 `codex`；`pm-bot` 不是 dispatcher，也不是 adjudicator。
4. `logical_target / bot_name` 负责 lane binding，`lane_identity` 负责 agent locking。
5. 当前 active flow 仍以 `lane_identity == bot_name` 作为 watcher 基线约束。
6. 正式运行单元是 `assignment + pane + primary terminal surface`。
7. 会话级收口顺序固定为 `A7 -> A8 -> A9`；不得跳过 `A7` 直接进入 `A8/A9`。

## Runtime Surface Notes

- title 只承担 runtime lookup aid，不生成身份真相。
- `claude --agent <lane_identity>` 是当前正式的启动时锁身份路径。
- board surface 不能顶替 worker primary terminal surface。
- legacy `tmux` / `doorbell` / `CODEX_THREAD_ID` 语义不构成当前 `cmux` identity truth。

## Why This Record Exists

`AGENTS.md` 已把本决策记录作为 daily execution 的权威锚点。如果该文件缺失，仓库会出现“有权威引用但无权威实体”的真相断链。自 2026-04-17 起，本文件作为该锚点的仓库内实体保留。

## Truth Basis

### Source Refs
- `/Users/busiji/workbot/AGENTS.md`
- `/Users/busiji/workbot/.claude/agents/pm-bot.md`
- `/Users/busiji/workbot/.claude/agents/dev-bot.md`
- `/Users/busiji/workbot/.claude/agents/qa-bot.md`
- `/Users/busiji/workbot/.claude/agents/doc-bot.md`
- `/Users/busiji/workbot/.claude/agents/rea-bot.md`
- `/Users/busiji/workbot/docs/cmux-subagent-runtime-chain.md`
- `/Users/busiji/workbot/docs/cmux-subagent-runtime-truth-table.md`
- `/Users/busiji/workbot/docs/a1-a9-session-protocol.md`
- `/Users/busiji/.agents/skills/cmux/references/workbot/cmux-multi-pane-agent-runtime-requirements.md`
- `/Users/busiji/.agents/skills/cmux/scripts/bootstrap_claude_runtime.py`
- `/Users/busiji/.agents/skills/cmux/scripts/generate_cmux_assignments.py`
- `/Users/busiji/.agents/skills/cmux/scripts/watch_cmux_assignments.py`

### Conflict Status
- `resolved`
