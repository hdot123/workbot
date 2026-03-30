# Workbot Agents Guide

## Scope

This file defines the shared agent layout for the entire `workbot` repository.

## Shared Agents Directory

Reusable shared role definitions live in:

`/Users/busiji/workbot/agents/`

This directory remains the shared role library for the repository.

## Project Claude Agents Directory

Claude Code project-level subagents for this repository live in:

`/Users/busiji/workbot/.claude/agents/`

This directory is the direct project discovery source used by Claude Code.

## Current Shared Roles

- `architecture-judge-bot.md`
- `business-judge-bot.md`
- `engineering-judge-bot.md`
- `operations-judge-bot.md`
- `product-judge-bot.md`
- `qa-judge-bot.md`

## Current Project Claude Roles

- `.claude/agents/dev-bot.md`
- `.claude/agents/qa-bot.md`
- `.claude/agents/doc-bot.md`

## Usage Convention

- Repository-wide reusable shared roles should be added under `/Users/busiji/workbot/agents/`.
- Claude Code project-level execution identities that need project-local locking should be defined directly under `/Users/busiji/workbot/.claude/agents/`.
- tmux pane topology and pane-monitoring rules belong only to the `tmux-skills` domain (`/Users/busiji/workbot/skills/tmux-skills/`) and are not project-level Claude identities.
- Do not define, mirror, or migrate tmux temporary work partitions into `/Users/busiji/workbot/.claude/agents/`.
- Keep exactly one source of truth per role. Do not keep duplicate definitions of the same role in both directories.
- Do not use `/Users/busiji/workbot/.claude/agents/` as a symlinked wrapper for `/Users/busiji/workbot/agents/`.

## Project Notes

- The shared review-role library remains under `/Users/busiji/workbot/agents/`.
- Claude Code should discover project-local agents through `/Users/busiji/workbot/.claude/agents/` at the repository root.
- `dev-bot`、`qa-bot` and `doc-bot` are project-local Claude identities and should be maintained directly in `/Users/busiji/workbot/.claude/agents/`.
- tmux panes, pane titles and pane slots are disposable runtime surfaces inside the current attached session; they are not project-level identities and must not be documented as long-lived role objects.
- tmux pane-generation and pane-monitoring rules are owned only by `tmux-skills`; `.claude/agents/` must not be used as their source of truth.

## Daily Runtime Convention

- Daily execution must follow the decision record at `/Users/busiji/workbot/workspace/memory/kb/decisions/2026-03-25-workbot-project-agents-and-runtime-surfaces.md`.
- Daily task/monitor thread separation may start only after the preflight checklist is complete.
- tmux must run in the foreground. Detached or background tmux sessions are not official runtime surfaces.
- Each day may maintain one task thread and one monitor thread when task flow and monitoring flow need separate fact streams.
- The official tmux runtime for the day must be exactly one attached formal session, normally named `formal-session`.
- `task` / `monitor` and other temporary work panes must exist inside that one formal session, not as separate formal sessions.
- `tmux-to` normal task flow must go only to the daily task thread.
- `tmux-to` monitor and exception flow must go only to the daily monitor thread.
- The tmux doorbell pipeline must use the `CODEX_THREAD_ID` injected by the active monitor work pane or temporary slot as its only delivery target. Any other candidate variable or fallback thread constant is deprecated; the doorbell should fail fast when `CODEX_THREAD_ID` is unset.
- If preflight is incomplete, do not treat temporary tmux sessions or bootstrap surfaces as the official daily formal runtime.
