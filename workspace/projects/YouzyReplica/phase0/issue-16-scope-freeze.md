# Issue #16 — Phase 0A Scope Freeze: Replica Scope, Non-Goals, and Must-Cover Pages

> **Assignment**: `P10-PHASE0A-ISSUE16-PM`
> **Owner**: pm-bot
> **Parent**: #6 `Phase 0 — Scope Freeze & Acceptance Baseline`
> **Siblings**: #14 (Phase 0B — 1:1 parity contract), #15 (Phase 0C — execution guardrails)
> **Date**: 2026-04-18
> **Scope Boundary**: Phase 0A only. No Phase 1 route capture, implementation, asset localization, or replay design.

---

## 1. Reusable Scope Statement

**Primary deliverable**: `website replica first, data second`

The Youzy 1:1 Replica project delivers a pixel-parity clone of `https://youzy.cn` as its first-class artifact. All queryable data (universities, majors, scores, careers, etc.) is a **derived output** obtained by running queries against the localized replica site and its API replay layer. Data is a by-product, not the primary deliverable.

**Design principles**:

| Principle | Statement |
|-----------|-----------|
| Replica-first | Every page in scope must render with pixel-parity to the original youzy.cn page. |
| Data-second | Query results (university lists, score lines, major details, etc.) are captured as JSON/HAR evidence from the replica, not as independently authored datasets. |
| 1:1 fidelity | "1:1" means rendered DOM parity, localized assets, captured runtime payloads, local replay capability, and screenshot/HAR evidence per accepted page. (Detailed parity contract is defined in issue #14.) |
| gh-only ops | All GitHub project operations use `gh CLI / gh api / GraphQL` only. No browser-based GitHub manipulation. |
| Project #10 surface | GitHub Project #10 is the sole acceptance surface for this delivery stream. |

---

## 2. Must-Cover Page Families (First Delivery Wave)

The following page families are **in-scope** for the first delivery wave. Each family is bounded to avoid scope creep.

### 2.1 Core School Pages — **MANDATORY 1:1**

These are the highest-fidelity targets. Each page in this family must achieve pixel-parity.

| # | Page Family | Description | Example URL Pattern |
|---|-------------|-------------|---------------------|
| M1 | 找大学 — 列表页 | University listing with filters (province, batch, category, year) | `/university/` |
| M2 | 找大学 — 详情页 | Individual university detail (info, historical scores, enrollment plan, majors) | `/university/{id}` |
| M3 | 查专业 — 列表页 | Major listing with filters | `/major/` |
| M4 | 查专业 — 详情页 | Individual major detail (intro, employment, offering schools, scores) | `/major/{id}` |
| M5 | 看职业 — 列表页 | Career/occupation listing | `/career/` |
| M6 | 看职业 — 详情页 | Individual career detail (intro, related schools, salary ranking) | `/career/{id}` |
| M7 | 提前批 | Early-batch university and major listing | `/tqpc/` or equivalent |
| M8 | 分数线 / 批次线 | Provincial historical score lines and batch lines | `/fsx/` or equivalent |

**Mandatory status**: School pages (M1–M8) are **mandatory 1:1 pages**. They are the highest-fidelity targets for this project and form the core acceptance baseline.

### 2.2 Volunteer Filling Flow Pages — **MANDATORY 1:1**

| # | Page Family | Description |
|---|-------------|-------------|
| M9 | 院校优先模式 | University-first volunteer filling flow |
| M10 | 专业优先模式 | Major-first volunteer filling flow |
| M11 | 职业优先模式 | Career-first volunteer filling flow |
| M12 | 一键填报模式 | One-click volunteer filling flow |
| M13 | 测录取概率 | Admission probability calculator (input score → output probability) |
| M14 | 位次查询 | Rank/position query page |
| M15 | 新高考选科 | New gaokao subject selection (smart selection, self-analysis, query) |

### 2.3 Global Navigation & Infrastructure Pages — **MANDATORY 1:1**

| # | Page Family | Description |
|---|-------------|-------------|
| M16 | 首页 (Homepage) | Landing page with province selector, VIP entrance, navigation, footer, APP download QR codes |
| M17 | 全局导航 (Global Nav) | Header navigation tree including all four-level menu items |
| M18 | 全局 Footer | Footer with ICP filing, friend links, APP download, QR codes, legal links |

### 2.4 Auxiliary Pages — **IN-SCOPE, Phase 1**

| # | Page Family | Description | Fidelity |
|---|-------------|-------------|----------|
| A1 | 高考资讯 | Gaokao news listing + detail | 1:1 |
| A2 | 帮助中心 | Help center category nav + Q&A detail | 1:1 |
| A3 | 课堂 / 课程 | Classroom homepage + course list (by subject) + course detail | 1:1 |
| A4 | 试题 | Gaokao past papers + mock exam listing | 1:1 |
| A5 | 用户系统 | Registration, login, password recovery, profile pages | 1:1 (UI only) |
| A6 | 支付 / VIP | Volunteer card / education card purchase pages | 1:1 (UI only, no real payment) |
| A7 | 关于我们 / 法律声明 / 用户协议 / 意见反馈 | About us, legal, terms, feedback | 1:1 |
| A8 | 测评 | Assessment/evaluation pages | 1:1 |
| A9 | 机构 | Institution listing + detail | 1:1 |
| A10 | 社区 | Community homepage | 1:1 |
| A11 | 高招云直播 | Gaokao cloud live streaming listing | 1:1 (UI only) |
| A12 | 代理商加盟 | Agent加盟 page | 1:1 |

---

## 3. Mandatory School Pages — Explicit Call-Out

**School pages are the mandatory 1:1 core of this project.**

The following pages from Section 2.1 (M1–M8) receive the highest fidelity requirement:

1. **找大学 (M1, M2)** — University listing and detail pages
2. **查专业 (M3, M4)** — Major listing and detail pages
3. **看职业 (M5, M6)** — Career listing and detail pages
4. **提前批 (M7)** — Early-batch listing
5. **分数线 / 批次线 (M8)** — Score line and batch line pages

These pages:
- Must achieve pixel-parity (rendered DOM match) with the original youzy.cn.
- Must have per-page screenshot evidence, HAR evidence, and asset manifest.
- Are the primary acceptance targets for the 1:1 parity contract (issue #14).
- Must support filter interactions (province, batch, year, category) with UI-parity.

---

## 4. Phase 0 Non-Goals

The following are **explicitly out of scope for Phase 0**:

| # | Non-Goal | Rationale |
|---|----------|-----------|
| NG-01 | No route capture or HAR recording | This is Phase 1 work. Phase 0 is scope definition only. |
| NG-02 | No asset downloading or localization | This is Phase 2 work. Phase 0 defines what must be covered, not how to capture it. |
| NG-03 | No API mock/reply server implementation | This is Phase 4 work. Phase 0 only defines the boundary. |
| NG-04 | No pixel-diff tooling or automation | Tooling selection is a later phase concern. Phase 0 defines the acceptance target. |
| NG-05 | No backend reverse-engineering | The project does not reverse-engineer recommendation algorithms or probability calculation logic. |
| NG-06 | No real payment integration | VIP/payment pages are UI-only replicas. |
| NG-07 | No mobile/APP/mini-program coverage | This project covers Web only. |
| NG-08 | No live data streaming | Live streaming pages are UI-only replicas with mock data. |
| NG-09 | No third-party SDK integration | Analytics, customer service, SMS, etc. are marked for mock/removal. |
| NG-10 | No implementation of any kind | Phase 0 is purely scoping and baseline definition. |

---

## 5. Phase 1 Non-Goals (Forward Boundary)

To prevent scope creep into later phases, the following are **explicitly excluded from Phase 1** (route capture phase):

| # | Non-Goal | Rationale |
|---|----------|-----------|
| N1-01 | No full-site crawling automation | Route capture is selective, based on the page families defined here. |
| N1-02 | No asset download or re-mapping | Asset work belongs in Phase 2. |
| N1-03 | No replica skeleton搭建 | Skeleton搭建 belongs in Phase 2. |
| N1-04 | No API mock server搭建 | Mock server work belongs in Phase 4. |
| N1-05 | No pixel-diff report generation | Diff reports belong in Phase 3 and Phase 7. |

Phase 1 scope is limited to: **site map enumeration, API traffic recording, static resource inventory, navigation tree documentation, and tech stack analysis** — strictly matching the subtasks in the Phase 1 plan.

---

## 6. Deferred Page Families

The following page families are **deferred beyond the first delivery wave** and will be addressed in subsequent phases or later iterations:

| # | Deferred Family | Deferral Reason | Expected Phase |
|---|----------------|-----------------|----------------|
| D1 | 社区 — 全功能 (Community full features) | Community involves user-generated content, social interactions, and real-time features that require backend integration beyond replica scope. | Post Phase 5 (if needed) |
| D2 | 高招云直播 — 实时流 (Live streaming real-time) | Real-time streaming requires external real-time data sources; replica can only do UI + mock. | Post Phase 5 (if needed) |
| D3 | 测评 — 完整交互 (Assessment full interaction) | Assessment involves interactive scoring logic that goes beyond static replica. | Post Phase 5 (if needed) |
| D4 | 支付 — 真实支付链路 (Real payment flow) | Real payment integration is explicitly out of project scope. Only UI replica. | Never (out of scope) |
| D5 | 后端推荐算法 (Backend recommendation algorithms) | Volunteer recommendation and probability calculation algorithms are not reverse-engineered. | Never (out of scope) |
| D6 | 移动端 / APP / 小程序 (Mobile/APP/mini-program) | This project covers Web only. Mobile strategy is separate. | Separate project |
| D7 | 第三方 SDK 真实集成 (Real third-party SDK integration) | Analytics, customer service, map SDKs are marked for mock/removal, not real integration. | Never (out of scope) |

---

## 7. Page Family Boundary Definitions

To prevent ambiguity, each page family is bounded as follows:

| Family | In-Scope | Out-of-Scope (within family) |
|--------|----------|------------------------------|
| 找大学 | List page + detail page with all filter combinations | Backend data generation, university recommendation algorithm |
| 查专业 | List page + detail page with all filter combinations | Backend major recommendation algorithm |
| 看职业 | List page + detail page | Career assessment logic |
| 志愿填报 | Four filling mode UI pages + probability query UI | Recommendation engine, actual volunteer submission |
| 首页 | Full homepage rendering, nav, footer, QR codes | Dynamic content (real-time news feed, personalized recommendations) |
| 课堂/课程 | Course list + detail page rendering | Video streaming backend, user progress tracking |
| 用户系统 | Login/register/reset/profile UI pages | Real authentication, password management backend |
| 支付/VIP | Payment page UI rendering | Real payment processing, subscription management |

---

## 8. Issue #16 Acceptance Checklist Mapping

| # | Acceptance Item (from issue #16) | Status | Location in This Document |
|---|----------------------------------|--------|---------------------------|
| 1 | Scope statement clearly says `website replica first, data second` | ✅ DONE | Section 1: Reusable Scope Statement |
| 2 | Mandatory page families are listed and bounded | ✅ DONE | Section 2: Must-Cover Page Families (M1–M18, A1–A12) + Section 7: Boundary Definitions |
| 3 | Deferred page families are listed and justified | ✅ DONE | Section 6: Deferred Page Families (D1–D7) |
| 4 | School pages are explicitly called out as highest-fidelity targets | ✅ DONE | Section 3: Mandatory School Pages — Explicit Call-Out |
| 5 | No Phase 1 route-capture or implementation work is mixed into this issue | ✅ DONE | Section 4: Phase 0 Non-Goals + Section 5: Phase 1 Non-Goals |

---

## 9. Phase Boundary Summary

```
Phase 0 (Current)     → Scope freeze, acceptance baseline, parity contract, governance
  ├── Phase 0A (this) → ✅ Freeze replica scope, non-goals, must-cover pages
  ├── Phase 0B (#14)  → Define 1:1 parity contract and school evidence pack
  └── Phase 0C (#15)  → Freeze execution guardrails, GitHub flow, acceptance governance

Phase 1               → Site map, API recording, resource inventory, tech stack analysis
Phase 2               → Asset localization, replica skeleton, external dependency stripping
Phase 3               → School pages 1:1 replica (core), pixel-diff reports
Phase 4               → API mock/replay layer, data by-product persistence
Phase 5               → Auxiliary modules 1:1 replica
Phase 6               → Local replay, integration verification, E2E scripts
Phase 7               → Verification reports, delivery packaging
```

---

## 10. Evidence and References

| Reference | Type | Link |
|-----------|------|------|
| Parent issue #6 | GitHub Issue | https://github.com/hdot123/workbot/issues/6 |
| This issue #16 | GitHub Issue | https://github.com/hdot123/workbot/issues/16 |
| Sibling issue #14 | GitHub Issue | https://github.com/hdot123/workbot/issues/14 |
| Sibling issue #15 | GitHub Issue | https://github.com/hdot123/workbot/issues/15 |
| GitHub Project #10 | Project Board | https://github.com/users/hdot123/projects/10 |
| Youzy.cn replica task draft | Local doc | `/Users/busiji/workbot/docs/project-management/youzy-cn-replica-task-2026-04-18.md` |
| GitHub Project CLI operational standard | Local doc | `/Users/busiji/workbot/docs/project-management/github-project-cli-operational-standard.md` |
| AGENTS.md | Repository truth | `/Users/busiji/workbot/AGENTS.md` |
| Runtime decision record | KB decision | `/Users/busiji/workbot/workspace/memory/kb/decisions/2026-03-25-workbot-project-agents-and-runtime-surfaces.md` |

---

*Document frozen by pm-bot on 2026-04-18. Any scope change requires a new issue linked to Project #10 with explicit rationale.*
