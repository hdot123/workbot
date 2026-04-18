# Issue #14 — Phase 0B Parity Contract: 1:1 Engineering Baseline and School Evidence Pack

> **Assignment**: `P10-PHASE0B-ISSUE14-PM`
> **Owner**: pm-bot
> **Parent**: #6 `Phase 0 — Scope Freeze & Acceptance Baseline`
> **Sibling**: #16 (Phase 0A — scope freeze), #15 (Phase 0C — governance baseline)
> **Date**: 2026-04-18
> **Scope Boundary**: Define the reusable `1:1` contract and evidence pack only. No route capture, asset download, replay implementation, or pixel-diff execution in this issue.

---

## 1. Contract Statement

In Project #10, `1:1` is an **engineering acceptance contract**, not a loose visual aspiration.

An accepted page is not considered `1:1` unless it satisfies all required parity layers listed below, and unless the acceptance decision is backed by a page-level evidence pack that can be audited later by `qa-bot` and `rea-bot`.

This contract applies first to the mandatory school-page family defined in issue #16:

- 找大学列表页 / 详情页
- 查专业列表页 / 详情页
- 看职业列表页 / 详情页
- 提前批
- 分数线 / 批次线

Later phases may extend this contract to other page families, but no later phase may weaken it.

---

## 2. Minimum Parity Layers

Every accepted `1:1` page must satisfy the following layers.

| Layer | Required | Meaning | Pass Condition |
|---|---|---|---|
| L1 Rendered DOM parity | Yes | The local page renders the same user-visible structure and hierarchy as the captured upstream page. | Major blocks, ordering, labels, lists, and visible controls match the captured source page. |
| L2 Localized asset parity | Yes | CSS, JS, fonts, images, and other page-critical assets are served locally rather than from uncontrolled upstream domains. | No unexplained critical asset gaps; accepted page can load from the localized asset set. |
| L3 Runtime payload parity | Yes | The accepted render is tied to recorded payloads rather than hand-authored data. | Evidence pack references the payloads/HAR entries used to produce the accepted page state. |
| L4 Local replay parity | Yes | The accepted page state is reproducible from local assets plus local replay or frozen page data. | Accepted page can be regenerated locally without depending on a live upstream request. |
| L5 Visual evidence parity | Yes | Visual parity is demonstrated, not asserted. | Screenshot set and diff evidence exist for the accepted viewport set. |
| L6 Manifest parity | Yes | Page, assets, payloads, screenshots, and diff outputs are traceably linked. | A manifest ties the accepted page to all required evidence artifacts. |

If any required layer is missing, the page is not accepted as `1:1`.

---

## 3. Page-Level Acceptance Unit

The smallest acceptance unit is one **captured page state**:

- one upstream source URL
- one localized page route
- one frozen state definition
- one evidence manifest

For example, a university detail page for one school under one province/year/filter state is one acceptance unit.

This matters because list pages, detail pages, and filter-driven variants cannot be accepted by title alone. They must be accepted per captured state.

---

## 4. Mandatory School Evidence Pack

Each accepted school-page state must ship with the following evidence pack.

### 4.1 Required Metadata

| Field | Description |
|---|---|
| `page_family` | One of `university-list`, `university-detail`, `major-list`, `major-detail`, `career-list`, `career-detail`, `early-batch`, `score-line` |
| `page_key` | Stable local identifier for the accepted state |
| `source_url` | Captured upstream URL |
| `local_url` | Local replay URL/path |
| `capture_date` | Date of the upstream capture used as truth basis |
| `viewport_set` | The required viewport set used for validation |
| `payload_refs` | HAR entries / JSON payload references tied to the page |
| `asset_manifest_ref` | Manifest path or identifier for the localized assets |
| `diff_report_ref` | Visual comparison artifact reference |
| `acceptance_status` | `pass`, `conditional-pass`, or `fail` |

### 4.2 Required Artifacts

| Artifact | Required | Notes |
|---|---|---|
| Source screenshot(s) | Yes | Captured from the upstream page at the required viewport set |
| Local screenshot(s) | Yes | Captured from the localized page at the same viewport set |
| HAR or equivalent request log | Yes | Must cover the requests needed for the accepted page state |
| Normalized payload files | Yes | The runtime payloads that feed the accepted local state |
| Asset manifest | Yes | The page-critical CSS/JS/font/image references tied to the accepted state |
| DOM/structure note | Yes | A concise structural note listing major visible blocks and critical controls |
| Visual diff artifact | Yes | Pixel-diff or equivalent review artifact tied to the viewport set |
| Acceptance note | Yes | Short reviewer note recording pass/fail and any bounded exceptions |

### 4.3 Required Viewport Set

The mandatory school-page viewport set is:

1. `1920x1080`
2. `1366x768`
3. `768x1024`

If a page fails one viewport, the page state is not fully accepted.

---

## 5. Evidence Requirements by Page Type

| Page Type | Minimum Accepted States | Extra Evidence Requirement |
|---|---|---|
| University list | At least one baseline filter state and one non-default filter state | Filter bar and result list behavior must be visible in evidence |
| University detail | At least one complete school detail page | Must show profile, tags, contact/overview, score or plan blocks where present |
| Major list | At least one baseline state and one filtered state | Filter and sort affordances must be visible |
| Major detail | At least one complete major detail page | Must show intro, employment direction, offering schools, score-related blocks where present |
| Career list | At least one baseline state | List card structure and filter/navigation blocks must be visible |
| Career detail | At least one complete career detail page | Must show intro, related majors/schools, salary/ranking block where present |
| Early-batch | At least one representative listing state | Batch-specific filters or notices must be visible |
| Score-line | At least one province/year state | Province/year selectors and results table must be visible |

---

## 6. Allowed Differences

Allowed differences are tightly bounded. They are exceptions to acceptance, not a fallback to vague similarity.

The following may be acceptable only if they are explicitly recorded in the page acceptance note:

| Code | Allowed Difference | Boundary |
|---|---|---|
| AD-01 | Third-party analytics, telemetry, or customer-service SDKs removed | Allowed only when removal does not change the visible page structure or core interaction surface |
| AD-02 | Live or time-sensitive content frozen to captured data | Allowed only when the visible state matches a real captured snapshot |
| AD-03 | UI-only handling for login/VIP/payment actions | Allowed only when the rendered UI matches and the missing backend action is explicitly marked |
| AD-04 | Non-user-visible token, request ID, or timestamp changes inside artifacts | Allowed only when these do not affect visible layout or replay correctness |
| AD-05 | Font rendering micro-variation across local environments | Allowed only if the visual diff remains within the defined acceptance threshold and no layout break occurs |

No other difference is implicitly allowed.

---

## 7. Failure Conditions

Any of the following is an automatic acceptance failure:

1. Major visible blocks are missing, reordered incorrectly, or structurally inconsistent.
2. Critical CSS/JS/font/image dependencies are absent and change visible rendering.
3. The local page requires live upstream requests to reach the accepted state.
4. The accepted state cannot be traced to recorded payloads or HAR evidence.
5. The page lacks one or more required viewport screenshots.
6. The page has no manifest tying the evidence together.
7. A claimed `1:1` result relies on hand-authored replacement data rather than recorded inputs.
8. Differences are explained only narratively without linked artifacts.

---

## 8. Reusable Parity Checklist

The following checklist is the reusable acceptance baseline for later phases.

### 8.1 Page Acceptance Checklist

- [ ] The page state is identified by `page_family`, `page_key`, `source_url`, and `local_url`.
- [ ] The source page and local page were captured at `1920x1080`, `1366x768`, and `768x1024`.
- [ ] Rendered structure matches the captured upstream state.
- [ ] Localized assets are complete enough for accepted rendering.
- [ ] HAR or equivalent request evidence exists for the accepted state.
- [ ] Payload references are frozen and linked to the local render.
- [ ] The page can be replayed locally without live upstream dependency.
- [ ] Visual diff evidence exists for the accepted viewport set.
- [ ] Asset manifest and evidence manifest are linked.
- [ ] Any allowed difference is explicitly recorded under `AD-*`.

### 8.2 Phase-Level Gate Checklist

- [ ] Every accepted school page references this issue as the parity baseline.
- [ ] No page is marked `1:1` without a page-level evidence pack.
- [ ] Conditional passes are explicitly bounded and carry follow-up work.
- [ ] Failures are classified by parity layer (`L1` through `L6`), not by vague prose.

---

## 9. Suggested Evidence Pack Layout

One acceptable layout is:

```text
workspace/projects/YouzyReplica/evidence/
  school-pages/
    <page_family>/
      <page_key>/
        manifest.json
        source-1920.png
        source-1366.png
        source-768.png
        local-1920.png
        local-1366.png
        local-768.png
        requests.har
        payloads/
        assets-manifest.json
        diff/
        acceptance.md
```

The exact filenames may change later, but the contract above may not be weakened.

---

## 10. Issue #14 Acceptance Mapping

| # | Acceptance Item (from issue #14) | Status | Location in This Document |
|---|----------------------------------|--------|---------------------------|
| 1 | `1:1` is defined as an engineering contract, not a vague visual claim | ✅ DONE | Sections 1 and 2 |
| 2 | School evidence-pack contents are explicit and complete enough to audit | ✅ DONE | Sections 4 and 9 |
| 3 | Allowed differences are bounded and documented | ✅ DONE | Section 6 |
| 4 | Required evidence types are listed by page | ✅ DONE | Sections 4 and 5 |
| 5 | Later phases can reference this issue as the single parity baseline | ✅ DONE | Sections 1, 8, and 10 |

---

## 11. References

| Reference | Type | Link |
|---|---|---|
| Parent issue #6 | GitHub Issue | https://github.com/hdot123/workbot/issues/6 |
| Issue #14 | GitHub Issue | https://github.com/hdot123/workbot/issues/14 |
| Issue #16 | GitHub Issue | https://github.com/hdot123/workbot/issues/16 |
| GitHub Project #10 | Project Board | https://github.com/users/hdot123/projects/10 |
| Phase 0A scope freeze packet | Local doc | `/Users/busiji/workbot/workspace/projects/YouzyReplica/phase0/issue-16-scope-freeze.md` |
| Youzy replica task draft | Local doc | `/Users/busiji/workbot/docs/project-management/youzy-cn-replica-task-2026-04-18.md` |
| AGENTS.md | Repository truth | `/Users/busiji/workbot/AGENTS.md` |

---

*Document frozen by pm-bot on 2026-04-18. Any relaxation of this contract requires a new Project #10 issue with explicit rationale and reviewer sign-off.*
