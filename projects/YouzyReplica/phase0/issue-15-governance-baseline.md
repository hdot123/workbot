# Issue #15 — Phase 0C Governance Baseline: Execution Guardrails, GitHub Flow, and Acceptance Governance

> **Assignment**: `P10-PHASE0C-ISSUE15-PM`
> **Owner**: pm-bot
> **Parent**: #6 `Phase 0 — Scope Freeze & Acceptance Baseline`
> **Siblings**: #16 (scope freeze), #14 (parity contract)
> **Date**: 2026-04-18
> **Scope Boundary**: Define governance and operating rules only. No page capture, implementation, or replay work in this issue.

---

## 1. Governance Statement

Project #10 is governed by four non-negotiable rules:

1. **GitHub operations are CLI/API only**.
   Allowed paths are `gh`, `gh api`, and GitHub GraphQL.
2. **GitHub Project #10 is the sole acceptance surface**.
   Phase status, execution ownership, and gating must be visible there.
3. **Formal execution uses the `cmux` 5+1 runtime**.
   The five bot panes are `pm-bot`, `dev-bot`, `qa-bot`, `doc-bot`, `rea-bot`, plus one `cmux-browser` board surface.
4. **Codex must not create local feature branches in this repository**.
   Delivery stays on the official branch flow defined in `AGENTS.md`.

These rules apply to all later phases unless a newer Project #10 governance issue explicitly replaces them.

---

## 2. Prohibited Operations

The following are explicitly prohibited for this project stream:

| Code | Prohibited Operation | Why It Is Prohibited |
|---|---|---|
| PO-01 | GitHub browser UI clicks for project creation, field edits, status moves, or acceptance updates | Browser operations are not scriptable or auditable in this workflow |
| PO-02 | Creating a parallel local feature branch for Codex work | Repository policy forbids Codex-created local branches |
| PO-03 | Treating a chat transcript or issue comment thread as the main acceptance surface | Acceptance truth must live in Project #10 plus linked issues/evidence |
| PO-04 | Marking a phase `Done` without evidence | Phase closure must be evidence-backed |
| PO-05 | Running outside the formal `cmux` daily runtime and still claiming official execution | Runtime truth for this repo is `cmux` 5+1 |
| PO-06 | Inventing or changing bot role ownership ad hoc during a phase | Execution and gate ownership must remain explicit and visible |

---

## 3. Runtime and Role Contract

The repository truth from `AGENTS.md` and the 2026-03-25 decision record applies directly here.

### 3.1 Runtime Carrier

- Formal project-internal execution surface: `cmux`
- Formal topology: `5+1`
- Worker panes: `pm-bot`, `dev-bot`, `qa-bot`, `doc-bot`, `rea-bot`
- Board surface: `cmux-browser`
- External scheduler/adjudicator context: `main-thread`

`main-thread` is outside the project workspace and is not a project-local bot pane.

### 3.2 Phase Ownership Matrix

| Phase | Execution Bot | Gate Bot | Governance Meaning |
|---|---|---|---|
| Phase 0 | `pm-bot` | `qa+rea` | Scope, parity contract, and governance are authored by `pm-bot` and reviewed by both gate bots |
| Phase 1 | `pm-bot` | `qa+rea` | Blueprint and capture design remain pm-led but must be cross-checked |
| Phase 2 | `dev-bot` | `qa+rea` | Asset localization and skeleton work are implementation-led |
| Phase 3 | `dev-bot` | `qa+rea` | Core school-page replica is implementation-led with strict gate review |
| Phase 4 | `dev-bot` | `qa+rea` | Replay/data work remains implementation-led and gate-reviewed |
| Phase 5 | `dev-bot` | `qa+rea` | Auxiliary-module replica remains implementation-led |
| Phase 6 | `qa-bot` | `qa+rea` | Integrated validation is QA-led with analytical gate support |
| Phase 7 | `doc-bot` | `qa+rea` | Delivery pack and runbook are doc-led, still gate-reviewed |

No phase may omit an execution owner or gate owner.

---

## 4. Required Status Flow

Project #10 uses the following lifecycle:

1. `Todo`
2. `In Progress`
3. `In Review`
4. `Gate`
5. `Done`

### 4.1 Transition Rules

| Transition | Minimum Requirement |
|---|---|
| `Todo -> In Progress` | Phase issue exists, owner is set, scope guard is written, and work has been formally dispatched |
| `In Progress -> In Review` | The execution bot has produced the stated deliverables and linked the evidence packet |
| `In Review -> Gate` | Review comments are resolved or explicitly deferred with rationale |
| `Gate -> Done` | `qa-bot` and `rea-bot` have accepted the evidence baseline and no blocking gap remains |

Status changes are operational decisions, not cosmetic updates.

---

## 5. Minimum Evidence Before Review or Gate

Before any phase can move to `In Review` or `Gate`, it must provide a minimum evidence set.

### 5.1 Evidence Packet Requirements

| Evidence Item | Required | Notes |
|---|---|---|
| Scope statement or implementation target | Yes | Must match the issue body and project fields |
| Local artifact path(s) | Yes | Docs, manifests, test outputs, captures, or code references |
| Verification command(s) | Yes | Commands actually run, or an explicit note explaining why verification could not be run |
| Result summary | Yes | Pass/fail plus the meaningful outcome |
| Open differences or risks | Yes | Anything unresolved must be recorded explicitly |
| Commit SHA | Yes at phase close | Required when phase work is delivered to `main` |

### 5.2 Governance Rule

No card may enter `Gate` with only prose and no linked artifact path.

---

## 6. Child Issue Creation Rules

Any future child issue created under Project #10 must follow these rules.

### 6.1 Title Rules

- Prefix with the phase, for example `Phase 3A`, `Phase 4B`, or equivalent bounded naming.
- Use an imperative, bounded title.
- Do not use vague titles such as `continue`, `cleanup`, or `misc`.

### 6.2 Body Template

Each issue body must include:

```md
## Goal
<one bounded result>

## Subtasks
- [ ] ...

## Acceptance Checklist
- [ ] ...
```

### 6.3 Metadata Rules

Each child issue must be:

- added to GitHub Project #10
- attached to the correct milestone
- labeled with `replica-1to1`, `youzy-replica`, and the correct phase label
- assigned an `Execution Bot`
- assigned a `Gate Bot`
- given a `Priority`
- given a `Track`
- given `Formal Dispatch = Yes` when it becomes official work
- given a `Scope Guard` that prevents spillover

### 6.4 Evidence Rule

Each child issue must define what evidence will be required before review.

---

## 7. Git Delivery Contract

`AGENTS.md` defines a repository-level phase delivery rule, and this issue freezes it as Project #10 governance.

At the end of every phase task (`M*`, `P*`, `H*` or equivalent bounded phase unit), the executing agent must:

1. stage only the scoped files for that phase
2. create a commit whose message includes the phase identifier
3. push to `origin/main`
4. write the resulting commit SHA into the corresponding Project evidence or linked issue note

Additional guardrails:

- No Codex-created local feature branches
- No unscoped mass staging
- No claiming phase closure while work remains only in the local tree

---

## 8. Project #10 as the Sole Acceptance Surface

For this delivery stream, Project #10 is the formal place where the following must remain visible:

- current status
- execution owner
- gate owner
- milestone
- priority
- source
- scope guard
- start date / target date
- linked issue or issue set
- evidence state sufficient to decide review or gate

Supporting artifacts may live in the repository, but acceptance truth must still be reflected back to Project #10 and its linked issues.

---

## 9. Review and Gate Responsibilities

### 9.1 Execution Bot

The execution bot is responsible for:

- producing the phase deliverable
- linking the local artifacts
- running or explicitly accounting for verification
- declaring unresolved risks before requesting review

### 9.2 Gate Bots

`qa-bot` and `rea-bot` together are responsible for:

- checking that the deliverable matches the issue scope
- checking that evidence is sufficient
- checking that no acceptance claim hides a known gap
- deciding whether the phase may advance to `Done`

No execution bot may self-certify a gated phase as complete without gate review.

---

## 10. Issue #15 Acceptance Mapping

| # | Acceptance Item (from issue #15) | Status | Location in This Document |
|---|----------------------------------|--------|---------------------------|
| 1 | GitHub browser operations are explicitly prohibited | ✅ DONE | Sections 1 and 2 |
| 2 | Phase execution and gate bots are explicitly defined | ✅ DONE | Sections 3 and 9 |
| 3 | Evidence expectations are stated before implementation begins | ✅ DONE | Section 5 |
| 4 | Child issue creation rules are documented | ✅ DONE | Section 6 |
| 5 | The issue can be referenced as the governance baseline for later phases | ✅ DONE | Sections 1, 4, 7, 8, and 10 |

---

## 11. References

| Reference | Type | Link |
|---|---|---|
| Parent issue #6 | GitHub Issue | https://github.com/hdot123/workbot/issues/6 |
| Issue #15 | GitHub Issue | https://github.com/hdot123/workbot/issues/15 |
| Issue #16 | GitHub Issue | https://github.com/hdot123/workbot/issues/16 |
| Issue #14 | GitHub Issue | https://github.com/hdot123/workbot/issues/14 |
| GitHub Project #10 | Project Board | https://github.com/users/hdot123/projects/10 |
| AGENTS.md | Repository truth | `/Users/busiji/workbot/AGENTS.md` |
| Runtime decision record | KB decision | `/Users/busiji/workbot/workspace/memory/kb/decisions/2026-03-25-workbot-project-agents-and-runtime-surfaces.md` |
| GitHub CLI operational standard | Local doc | `/Users/busiji/workbot/docs/project-management/github-project-cli-operational-standard.md` |
| GitHub standard bootstrap | Local doc | `/Users/busiji/workbot/docs/project-management/github-standard-project-bootstrap.md` |

---

*Document frozen by pm-bot on 2026-04-18. Any governance change for Project #10 must be introduced as a new linked issue rather than silently mutating the operating rules.*
