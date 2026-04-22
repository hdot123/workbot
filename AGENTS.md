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
- Daily formal runtime must stay on one active `cmux` project workspace with `5+1` topology (`pm/dev/qa/doc/rea + cmux-browser`).
- Detached/background `tmux` sessions are legacy residue and are not official runtime surfaces for daily execution.
- External `main-thread` remains outside project workspace as scheduler/adjudicator context; it is not a project internal pane.
- Daily task/monitor thread split is a logical stream split, not a requirement to create legacy tmux formal sessions.
- Legacy `tmux-to` / doorbell / `CODEX_THREAD_ID` wording is historical residue only and must not be treated as current `cmux` runtime contract.
- If preflight is incomplete, do not treat temporary bootstrap surfaces as the official daily formal runtime.

## Phase Git Convention

- Local git task isolation must follow `/Users/busiji/workbot/workspace/memory/kb/decisions/2026-04-20-workbot-branch1-branch2-task-isolation.md`.
- `branch-1` is the only local stable branch allowed to accumulate accepted task results. Treat it as the durable local truth branch for this repository and keep it aligned with `origin/main`.
- Before any new task starts, the local git workspace must first be normalized onto `branch-1`.
- Every new task must create a fresh temporary task branch referred to as `branch-2`, created from the current tip of `branch-1`, and the entire task must execute on that `branch-2`.
- `branch-2` is one-task isolation only. Do not reuse the same `branch-2` for a second task, a second attempt, or a cleanup round after rejection.
- `branch-2` is disposable task isolation only. It must not become the long-lived working branch for the repository.
- Development, bug fixing, refactoring, testing, code review, and any other task that may touch repository code must all run on `branch-2`, not directly on `branch-1`.
- `cmux` tasks must still follow the formal runtime protocol: `main-thread` dispatch -> bot execute -> `finish-cycle` local writeback -> `main-thread` acceptance and closure. This formal runtime chain does not replace the requirement that the task's repository code work surface must be the task-local `branch-2`.
- If a task fails, is stopped, is rejected, or leaves an unclear residue state, do not merge it into `branch-1`; discard, delete, or recreate `branch-2` for the next attempt.
- If a task succeeds, passes tests, and passes `main-thread` acceptance, merge `branch-2` back into `branch-1`, then retire or delete `branch-2`.
- Do not leave accepted work only on `branch-2`; the durable local truth must always roll back up into `branch-1`.
- Before merging any `branch-2` back into `branch-1`, the executing agent must verify and be able to report:
  - which repository files were changed
  - whether any repo-external files were touched
  - whether any run artifacts or temporary evidence leaked into repository code paths
  - whether any failed or stopped task residue remains unresolved
- Run artifacts, audit evidence, and temporary validation output must stay under the designated run/evidence directories such as `workspace/memory/tmp/...`; they must not be merged into repository code truth unless the task explicitly requires repository-tracked documentation.
- At the end of every phase task (`M*`, `P*`, `H*`) that is accepted, the executing agent must perform repository git delivery from `branch-1`.
- Required accepted-phase delivery sequence: scoped `git add` on `branch-2` -> commit on `branch-2` -> merge into `branch-1` -> push `branch-1` to `origin/main` -> write commit SHA into the corresponding Projects card evidence.
