# Workbot cmux P12-core Delivery

Date: 2026-04-17
Scope: `P12-core`

## P12-core Acceptance Map

### 1. dispatch_owner remains codex

- `/Users/busiji/.agents/skills/cmux/scripts/generate_cmux_assignments.py`
  `base_assignment(...)` sets `dispatch_owner = "codex"`.
- `/Users/busiji/.agents/skills/cmux/scripts/watch_cmux_assignments.py`
  `validate_derived_identity_contract(...)` rejects drift from `dispatch_owner = codex`.

### 2. pm-bot is not used as dispatcher or adjudicator

- `/Users/busiji/workbot/AGENTS.md`
  defines `pm-bot` as a bound runtime bot, not external `main-thread`.
- `/Users/busiji/workbot/docs/cmux-subagent-runtime-chain.md`
  states `pm-bot` assignment truth remains external and `dispatch_owner` remains `codex`.
- `/Users/busiji/workbot/memory/kb/projects/workbot.md`
  states `pm-bot` does not own task breakdown, dispatch, closure, or adjudication.

### 3. assignment must exist before pane dispatch

- `/Users/busiji/workbot/docs/cmux-subagent-runtime-chain.md`
  defines the formal unit as `assignment + pane + primary terminal surface`.
- `/Users/busiji/.agents/skills/cmux/scripts/bootstrap_claude_runtime.py`
  generates and validates assignments before launch.

### 4. A7 -> A8 -> A9 closeout order is preserved

- `/Users/busiji/workbot/docs/a1-a9-session-protocol.md`
  explicitly states `A7` must occur before `A8/A9`.
- `/Users/busiji/workbot/docs/a1-a9-session-brief.md`
  repeats the same closeout order as the short-form canonical.
- `/Users/busiji/workbot/memory/kb/decisions/2026-03-25-workbot-project-agents-and-runtime-surfaces.md`
  now freezes the same closeout rule as repository-facing commander truth.

## Omission Fixed in This Delivery

Before this delivery, `AGENTS.md` pointed to:

- `/Users/busiji/workbot/memory/kb/decisions/2026-03-25-workbot-project-agents-and-runtime-surfaces.md`

That file did not exist in the repository, which meant the repository truth contained a broken authoritative anchor. `P12-core` fixes that omission by materializing the missing decision record and indexing it.

## Remaining Omissions Not Fixed in P12-core

- `/Users/busiji/workbot/memory/kb/global/memory-router-design-v2.1.1.md` is still missing from the active tree.
- `/Users/busiji/workbot/memory/kb/lessons/memory-docs-immutable.md` is still missing from the active lessons dir.
- `/Users/busiji/workbot/memory/kb/lessons/pm-bot-crawl4ai-runtime-path.md` is still missing from the active lessons dir.

These are real anchor gaps, but they are not required to close the `P12-core` commander semantics contract itself.

## Repo Artifacts Added or Updated by This Delivery

- `/Users/busiji/workbot/memory/kb/decisions/2026-03-25-workbot-project-agents-and-runtime-surfaces.md`
- `/Users/busiji/workbot/memory/kb/decisions/INDEX.md`
- `/Users/busiji/workbot/memory/kb/projects/workbot.md`
- `/Users/busiji/workbot/docs/project-management/workbot-cmux-p12-core-delivery-2026-04-17.md`
