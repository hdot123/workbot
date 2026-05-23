# P2 Dry-run Tabletop Scenario

**文档编号**: P2-SCENARIO-008
**版本**: V1.0
**日期**: 2026-05-08
**关联 Linear Issue**: JTO-204
**P2 Project**: P2 — Long-task dry-run + GitLab CI feedback loop
**状态**: 设计稿（dry-run only, no real execution）

---

## 1. 概述

本文档设计一次完整的 P2 dry-run tabletop 演练，验证从 Linear issue 到 GitLab CI 结果回写的完整闭环。

**核心原则**：全流程验证，不真实执行。

---

## 2. 完整场景链路

```
1. Linear Issue Ready
     ↓
2. Factory Long-task Dry-run Plan
     ↓
3. Subagent Plan Generated
     ↓
4. GitLab CI Required (simulated)
     ↓
5. Fake Pipeline Result
     ↓
6. Linear Dry-run Comment
     ↓
7. Audit Evidence
     ↓
8. Acceptance
```

---

## 3. 场景输入

### 3.1 触发条件

| 属性 | 值 |
|------|-----|
| Linear Issue | JTO-197 / P2-01 |
| Issue State | Backlog |
| Project | P2 — Long-task dry-run + GitLab CI feedback loop |
| Trigger Type | Manual tabletop simulation |

### 3.2 Input Event Sample

```json
{
  "object_kind": "pipeline",
  "object_attributes": {
    "id": 12345,
    "ref": "main",
    "sha": "abc123def456",
    "status": "success",
    "created_at": "2026-05-08T10:30:00Z"
  },
  "project": {
    "id": 789,
    "path_with_namespace": "busiji/workbot"
  }
}
```

---

## 4. 预期处理流程

### 4.1 Factory Long-task Dry-run Plan

```json
{
  "dispatch_mode": "dry_run",
  "dispatch_type": "factory_long_task",
  "dispatch_id": "disp_p2-tabletop-001",
  "generated_at": "2026-05-08T10:25:00Z",

  "long_task": true,
  "dry_run": true,
  "no_write": true,
  "no_push": true,
  "no_deploy": true,
  "github_push_forbidden": true,
  "required_ci": "gitlab",
  "max_fix_attempts": 3,
  "checkpoint_required": true,
  "runlog_required": true,
  "heartbeat_required": true,
  "acceptance_required": true,

  "linear_issue_id": "JTO-197-id",
  "linear_issue_key": "JTO-197",
  "title": "P2-01 — Define long-task dry-run contract",
  "project_id": "e8365417-e2d8-4834-ace2-98eff6adeeab",
  "repo": "busiji/workbot",
  "target_branch": "branch-2"
}
```

### 4.2 Subagent Plan

```json
{
  "subagent_plan": {
    "phases": [
      {"phase": 1, "name": "read_linear_issue", "estimated_seconds": 30},
      {"phase": 2, "name": "create_deliverable", "estimated_seconds": 300},
      {"phase": 3, "name": "secret_scan", "estimated_seconds": 10},
      {"phase": 4, "name": "create_acceptance_report", "estimated_seconds": 60}
    ],
    "checkpoint_policy": "phase-complete",
    "runlog_policy": "jsonl-append",
    "heartbeat_policy": "60s-interval"
  }
}
```

---

## 5. Fake Pipeline Result

### 5.1 Simulated GitLab Pipeline Event

```json
{
  "object_kind": "pipeline",
  "object_attributes": {
    "id": 99001,
    "ref": "factory/jto-197-long-task-contract",
    "sha": "def789abc012",
    "status": "success",
    "created_at": "2026-05-08T10:35:00Z",
    "updated_at": "2026-05-08T10:38:00Z",
    "duration": 180
  },
  "project": {
    "id": 789,
    "path_with_namespace": "busiji/workbot"
  },
  "user": {
    "name": "Factory Droid",
    "username": "factory-droid"
  }
}
```

### 5.2 Expected Canonical Event

```json
{
  "canonical_version": "1.0",
  "delivery_id": "d-tabletop-001",
  "event_id": "e-tabletop-001-sha256",
  "idempotency_key": "sha256:gitlab+ci.pipeline.result+99001+def789abc012+success",
  "provider": "gitlab",
  "canonical_type": "ci.pipeline.result",
  "timestamp": "2026-05-08T10:38:00Z",
  "payload": {
    "pipeline_id": 99001,
    "commit_sha": "def789abc012",
    "branch": "factory/jto-197-long-task-contract",
    "status": "success",
    "project_id": 789,
    "project_path": "busiji/workbot",
    "duration_seconds": 180
  },
  "metadata": {
    "raw_event_sha256": "sha256:fake-event-body",
    "source_ip": "127.0.0.1",
    "simulation": true
  }
}
```

---

## 6. Expected Dispatch Payload

```json
{
  "dispatch_mode": "dry_run",
  "dispatch_type": "factory_long_task",
  "dispatch_id": "disp_tabletop_001",
  "long_task": true,
  "dry_run": true,
  "no_write": true,
  "no_push": true,
  "no_deploy": true,
  "github_push_forbidden": true,
  "required_ci": "gitlab",
  "max_fix_attempts": 3,
  "checkpoint_required": true,
  "runlog_required": true,
  "heartbeat_required": true,
  "acceptance_required": true,
  "linear_issue_key": "JTO-197",
  "project_id": "e8365417-e2d8-4834-ace2-98eff6adeeab",
  "ci_result": {
    "pipeline_id": 99001,
    "status": "success",
    "commit_sha": "def789abc012"
  }
}
```

---

## 7. Expected Linear Comment

```
[🔬 DRY-RUN] GitLab CI Pipeline Result — Tabletop Scenario

| Field | Value |
|-------|-------|
| pipeline_id | #99001 |
| status | ✅ success |
| commit_sha | `def789abc012` |
| branch | `factory/jto-197-long-task-contract` |
| project | busiji/workbot |
| duration | 3m 0s |
| linear_issue | JTO-197 |
| scenario | tabletop-simulation |

**Audit**: delivery_id=`d-tabletop-001`, event_id=`e-tabletop-001-sha256`

**Gate Check**:
- ✅ CI pipeline success
- ✅ pipeline_id verifiable (simulated)
- ✅ commit_sha matches dispatch payload
- ✅ Canary project scope (P2 project)
- ❌ Human approval (not required for tabletop)
- ✅ max_fix_attempts: 0/3
- ✅ Secret scan: 0 findings
- ✅ GitHub push gate: fail-closed
- ⏭️ Rollback plan: exists (P2-05)
- ⏭️ Acceptance: pending (P2-AC-01)

---
🤖 This is a tabletop simulation. No real execution occurred.
```

---

## 8. Expected Audit Rows

### 8.1 raw_events

| Column | Value |
|--------|-------|
| delivery_id | `d-tabletop-001` |
| provider | `"gitlab"` |
| raw_body | (fake pipeline event JSON) |
| source_ip | `127.0.0.1` |
| simulation | `true` |

### 8.2 canonical_events

| Column | Value |
|--------|-------|
| event_id | `e-tabletop-001-sha256` |
| delivery_id | `d-tabletop-001` |
| canonical_type | `"ci.pipeline.result"` |
| payload | (normalized payload) |
| idempotency_key | `sha256:gitlab+...` |

### 8.3 processing_logs

| Column | Value |
|--------|-------|
| event_id | `e-tabletop-001-sha256` |
| action | `"linear_comment_dry_run"` |
| action_result_json | `{"comment_id": "simulated", "status": "success"}` |
| status | `"success"` |

---

## 9. PASS/BLOCKED Criteria

### 9.1 PASS 条件（全部满足）

| # | 条件 | 验证方式 |
|---|------|---------|
| 1 | Linear issue ready | Issue 存在且在 canary project |
| 2 | Factory dry-run plan generated | Payload 包含所有 required fields |
| 3 | Subagent plan generated | Phases + checkpoint/runlog/heartbeat 策略 |
| 4 | GitLab CI simulated | Fake pipeline event 构造成功 |
| 5 | Fake pipeline result | Pipeline status = success |
| 6 | Linear dry-run comment | Comment 格式正确，包含 [🔬 DRY-RUN] 前缀 |
| 7 | Audit evidence | raw_events + canonical_events + processing_logs 完整 |
| 8 | Secret scan | 0 findings |
| 9 | No real execution | 无 Factory API call, no git push, no state change |
| 10 | Acceptance report | P2-AC-01 PASS |

### 9.2 BLOCKED 条件（任一触发即 BLOCKED）

| # | 条件 | 原因 |
|---|------|------|
| 1 | dry_run != true | 违反 P2-01 契约 |
| 2 | github_push_forbidden == false | Push gate fail-open |
| 3 | Secret 检测 | 任何敏感信息泄露 |
| 4 | Real Factory API call | 违反 dry-run 规则 |
| 5 | Git push | 违反 no-push 规则 |
| 6 | Linear state change | 违反 no-mutation 规则 |
| 7 | Linear label change | 违反 no-mutation 规则 |
| 8 | Missing audit row | 审计不完整 |
| 9 | Missing checkpoint | 阶段完成无 checkpoint |
| 10 | Heartbeat timeout | 子代理静默超时 |

---

## 10. Tabletop 执行步骤

1. **准备阶段**: 确认所有 P2-01 ~ P2-07 文档已完成
2. **触发阶段**: 构造 fake GitLab pipeline event
3. **处理阶段**: 模拟 canonical event 转换
4. **评论阶段**: 生成 Linear dry-run comment (simulated)
5. **审计阶段**: 验证 audit log schema 完整性
6. **验收阶段**: 执行 P2-AC-08 验收
7. **总结阶段**: 输出 tabletop 结果报告

---

## 11. 不包含 Secret 声明

本文档不包含任何 API key、token、password、secret、private key 或其他敏感信息。

所有示例均为模拟数据和 schema 描述。

---

**文档结束**
**P2-08 交付物 — Dry-run Tabletop Scenario V1.0**
