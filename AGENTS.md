# Workbot Agents Guide

## Scope

This file defines the shared agent layout for the entire `workbot` repository.

## Shared Agents Directory

Optional shared helper definitions live in:

`/Users/busiji/workbot/agents/`

This directory is not a shared review-role layer.

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

- Shared review identities must not be added under `/Users/busiji/workbot/agents/`.
- If a shared helper file is kept under `/Users/busiji/workbot/agents/`, it must be non-review and explicitly scoped.
- Globally defined bot bodies belong under `/Users/busiji/.claude/agents/`.
- `/Users/busiji/workbot/.claude/agents/` is the project binding / activation layer for bots enabled in `workbot`; it must not be described as the ontology source for those bots.
- Claude Code project-level bindings that need project-specific narrowing or activation should be defined directly under `/Users/busiji/workbot/.claude/agents/`.
- `/Users/busiji/workbot/.codex/agents/` is an adapter layer only and must not be treated as the source of truth for formal identities.
- Retired `tmux` runtime materials are historical residue only and must not be treated as current runtime or identity truth.
- Keep exactly one source of truth per role. Do not keep duplicate definitions of the same role in both directories.
- Do not use `/Users/busiji/workbot/.claude/agents/` as a symlinked wrapper for `/Users/busiji/workbot/agents/`.

## Project Notes

- The shared review-role library has been removed because it did not match the actual execution model.
- Claude Code should discover `workbot` bindings through `/Users/busiji/workbot/.claude/agents/` at the repository root.
- `pm-bot`、`dev-bot`、`qa-bot`、`doc-bot` and `rea-bot` are globally defined bot bodies that `workbot` currently binds into its formal runtime bot set.
- `workbot/.claude/agents/*.md` files are project binding / activation files for those global bots; they do not make the bot ontology local to `workbot`.
- `pm-bot` is bound into `workbot` as the product-analysis / imitation-product / requirement-organization / website-content-collection / benchmarking / imitation-analysis bot. It is not the external `main-thread`, not the `cmux-browser` board pane, and not a pure runtime-control alias.
- The legacy `pm-bot` collector-variant / crawl4ai wording is historical residue only. Active tool and collection truth must still follow the current runtime/tool policy and implemented bootstrap/tool gates.
- `main-thread` is the external runtime scheduler identity. It stays outside the project `cmux` workspace and does not require a local agent file.
- `cmux` is the only current formal runtime carrier for this repository.
- The current `workbot` `cmux` topology is `5+1`: five runtime panes bound to the global bot bodies `pm-bot`、`dev-bot`、`qa-bot`、`doc-bot`、`rea-bot`, plus one `cmux-browser` board pane.
- The `cmux-browser` board pane is a runtime board surface, not a formal bot identity.
- Runtime `pane` / `surface` titles are lookup aids and visible labels; they are not repository identity truth.
- `/Users/busiji/workbot/.codex/agents/` may wrap active identities for tooling, but it must not introduce standalone formal roles.
