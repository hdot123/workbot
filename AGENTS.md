# Workbot Agents Guide

## Scope

This file defines the shared agent layout for the entire `workbot` repository.

## Retired Shared Agents Directory

`/Users/busiji/workbot/agents/` is retired historical residue and is no longer retained as part of the current repository truth.

The current repository truth does not preserve a project-local shared agents directory.

## Global Claude Agents Directory

Globally defined bot bodies live in:

`/Users/busiji/.claude/agents/`

This directory is the global ontology layer for reusable bot role bodies.

## Project Claude Agents Directory

Claude Code project-level subagents for this repository live in:

`/Users/busiji/workbot/.claude/agents/`

This directory is the direct project discovery source used by Claude Code for `workbot`, and acts as the project binding / activation layer for globally defined bots.

## Current Shared Review Roles

- None. The shared review layer has been retired.

## Current Project Claude Bindings

- `.claude/agents/pm-bot.md`
- `.claude/agents/dev-bot.md`
- `.claude/agents/qa-bot.md`
- `.claude/agents/doc-bot.md`
- `.claude/agents/rea-bot.md`

## Repository Truth Role

- This file is the repository-level identity truth source for `workbot`.
- This file is also the repository-facing runtime positioning document for `workbot`.
- It defines which globally defined bots are formally bound into this repository and how repository-level runtime surfaces are positioned.
- It does not replace the workbot-specific `cmux` runtime canonical for detailed runtime semantics.

## Conflict Rule

- For repository identity truth and repository-facing runtime positioning, this file wins.
- For workbot-specific `cmux` runtime semantics, use `/Users/busiji/.agents/skills/cmux/references/workbot/cmux-multi-pane-agent-runtime-requirements.md`.
- `/Users/busiji/.agents/skills/cmux/SKILL.md` is a global operational reference only; it must defer whenever `workbot` truth is narrower than the global default.
- No document may claim a runtime capability that the current bootstrap path does not implement.

## Usage Convention

- No current repository truth may rely on `/Users/busiji/workbot/agents/`; that directory is retired residue and not part of the active repository layout.
- Globally defined bot bodies belong under `/Users/busiji/.claude/agents/`.
- `/Users/busiji/workbot/.claude/agents/` is the only project binding / activation layer for bots enabled in `workbot`; it must not be described as the ontology source for those bots.
- Claude Code project-level bindings that need project-specific narrowing or activation should be defined directly under `/Users/busiji/workbot/.claude/agents/`.
- `/Users/busiji/workbot/.codex/agents/` has been removed and must not be reintroduced as a parallel adapter-layer identity source.
- Retired `tmux` runtime materials are historical residue only and must not be treated as current runtime or identity truth.
- Keep exactly one source of truth per role. Do not keep duplicate definitions of the same role across repository paths.
- Do not use `/Users/busiji/workbot/.claude/agents/` as a wrapper or mirror for any retired project-local agents directory.

## Project Notes

- The shared review-role library has been removed because it did not match the actual execution model.
- Claude Code should discover `workbot` bindings through `/Users/busiji/workbot/.claude/agents/` at the repository root.
- `/Users/busiji/workbot/.claude/agents/` is the sole project-local binding layer retained by the repository.
- `/Users/busiji/workbot/agents/` is no longer retained as a current repository directory; any old references to it are historical residue only.
- `/Users/busiji/workbot/.codex/agents/` has been deleted and is not part of the active repository identity chain.
- `pm-bot`、`dev-bot`、`qa-bot`、`doc-bot` and `rea-bot` are globally defined bot bodies that `workbot` currently binds into its formal runtime bot set.
- `workbot/.claude/agents/*.md` files are project binding / activation files for those global bots; they do not make the bot ontology local to `workbot`.
- `pm-bot` is bound into `workbot` as the product-analysis / imitation-product / requirement-organization / website-content-collection / benchmarking / imitation-analysis bot. It is not the external `main-thread`, not the `cmux-browser` board pane, and not a pure runtime-control alias.
- The legacy `pm-bot` collector-variant / crawl4ai wording is historical residue only. Active tool and collection truth must still follow the current runtime/tool policy and implemented bootstrap/tool gates.
- `main-thread` is the external runtime scheduler identity. It stays outside the project `cmux` workspace and does not require a local agent file.
- `cmux` is the only current formal runtime carrier for this repository.
- The current `workbot` `cmux` topology is `5+1`: five runtime panes bound to the global bot bodies `pm-bot`、`dev-bot`、`qa-bot`、`doc-bot`、`rea-bot`, plus one `cmux-browser` board pane.
- The `cmux-browser` board pane is a runtime board surface, not a formal bot identity.
- Runtime `pane` / `surface` titles are lookup aids and visible labels; they are not repository identity truth.

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

## Phase Git Convention

- At the end of every phase task (`M*`, `P*`, `H*`), the executing agent must perform repository git delivery automatically.
- Required delivery sequence: scoped `git add` -> commit with phase identifier in message -> push to `origin/main` -> write commit SHA into the corresponding Projects card evidence.
- Do not leave completed phase work only in local working tree.
- This repository forbids Codex-created local feature branches; phase delivery must remain on the official branch flow.
