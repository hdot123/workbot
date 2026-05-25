# Linear Mutation Dry-run Gate

**文档编号**: P2-GATE-006
**版本**: V1.0
**日期**: 2026-05-08
**关联 Linear Issue**: JTO-202
**P2 Project**: P2 — Long-task dry-run + GitLab CI feedback loop
**状态**: 设计稿（dry-run only, real mutation FORBIDDEN）

---

## 1. 概述

本文档定义 Linear issueUpdate / label mutation 的 dry-run gate。当前禁止真实变更，仅允许 comment。

**核心原则**：dry-run 阶段只读评论，不改状态，不改标签。

---

## 2. 当前禁止事项

| 操作 | 状态 | 说明 |
|------|------|------|
| issueUpdate (状态变更) | ❌ FORBIDDEN | 不允许任何真实状态变更 |
| label mutation | ❌ FORBIDDEN | 不允许任何真实标签变更 |
| issueAddComment | ✅ ALLOWED | 仅允许 dry-run 评论 |
| production issue 变更 | ❌ FORBIDDEN | 仅 canary project 允许 |

---

## 3. IssueUpdate Dry-run Payload

### 3.1 模拟 Payload Schema

```json
{
  "dry_run": true,
  "operation": "issueUpdate",
  "issue_id": "<linear_issue_id>",
  "issue_key": "JTO-XXX",
  "proposed_changes": {
    "state": "In Progress",
    "labels": ["phase:p2", "implementation"],
    "assignee_id": "<user_id>"
  },
  "current_state": {
    "state": "Backlog",
    "labels": ["phase:p2"],
    "assignee_id": null
  },
  "validation": {
    "state_transition_allowed": true,
    "label_mutation_allowed": false,
    "canary_project": true,
    "approval_received": false
  },
  "audit": {
    "timestamp": "2026-05-08T10:30:00Z",
    "reason": "P2-06 dry-run gate validation",
    "dry_run_comment_id": "<comment_id>"
  }
}
```

### 3.2 验证规则

```
INVARIANT: dry_run == true → 不执行真实 mutation
INVARIANT: validation.state_transition_allowed == false → BLOCKED
INVARIANT: validation.label_mutation_allowed == false → BLOCKED
INVARIANT: validation.canary_project == false → BLOCKED
INVARIANT: validation.approval_received == false → BLOCKED
```

---

## 4. Label Mutation Dry-run Payload

### 4.1 模拟 Payload Schema

```json
{
  "dry_run": true,
  "operation": "labelMutation",
  "issue_id": "<linear_issue_id>",
  "issue_key": "JTO-XXX",
  "proposed_labels": {
    "add": ["automation-complete", "ci-passed"],
    "remove": []
  },
  "current_labels": ["phase:p2", "implementation"],
  "validation": {
    "canary_project": true,
    "approval_received": false,
    "label_policy_compliant": true
  },
  "audit": {
    "timestamp": "2026-05-08T10:30:00Z",
    "dry_run_comment_id": "<comment_id>"
  }
}
```

### 4.2 允许添加的标签（未来参考）

| Label | 条件 | 说明 |
|-------|------|------|
| `automation-complete` | CI pipeline success | 自动化完成标记 |
| `ci-passed` | GitLab CI 通过 | CI 验证通过 |
| `ready-for-review` | 实现完成 | 准备评审 |
| `accepted` | AC 通过 | 验收通过 |

### 4.3 禁止移除的标签

| Label | 原因 |
|-------|------|
| `phase:p2` | Phase 标记不可移除 |
| `dry-run` | Dry-run 标记不可移除 |
| `no-real-factory` | 安全标记不可移除 |
| `no-github-push` | 安全标记不可移除 |
| `no-linear-mutation` | 安全标记不可移除 |

---

## 5. State Transition Matrix

### 5.1 允许的状态转换（未来参考）

| 从状态 | 到状态 | 条件 | 说明 |
|--------|--------|------|------|
| Backlog | In Progress | CI success + approval | 开始实施 |
| In Progress | In Review | 实现完成 | 等待评审 |
| In Review | Done | AC 通过 | 完成 |
| Backlog | Done | ❌ 禁止 | 不能跳过实施 |
| Done | Backlog | ❌ 禁止 | 不能回退到 Backlog |

### 5.2 禁止的状态转换

| 从状态 | 到状态 | 原因 |
|--------|--------|------|
| 任何状态 | Done | 必须经过 In Progress → In Review |
| Backlog | In Review | 必须经过 In Progress |
| Done | 任何状态 | Done 是终态，不可回退 |

### 5.3 P2 当前状态

**当前禁止所有真实状态转换。** 仅允许 comment-only 操作。

---

## 6. Label Mutation Policy

### 6.1 允许的条件

| 条件 | 说明 |
|------|------|
| Canary project only | 仅 canary project issue |
| Approval required | 人工或 policy 审批 |
| Audit log required | 所有操作记录审计日志 |
| No production issues | 生产 issue 禁止标签变更 |

### 6.2 标签变更流程（未来参考）

```
Pipeline success → Verify canary → Get approval → Validate label policy
  → Construct label mutation payload → Execute → Audit log → Done
```

### 6.3 P2 当前：Comment-Only Fallback

P2 阶段使用 comment 代替 label mutation：

```
代替 "添加 automation-complete 标签"
→ 评论: "[🔬 DRY-RUN] Would add label: automation-complete"

代替 "移除 in-progress 标签"
→ 评论: "[🔬 DRY-RUN] Would remove label: in-progress"
```

---

## 7. Approval Gate

### 7.1 审批要求

| 属性 | 值 |
|------|-----|
| 审批类型 | Human 或 Policy |
| 审批记录 | Linear comment 或外部系统 |
| 审批有效期 | 单次 mutation 操作 |
| 拒绝处理 | BLOCKED，记录原因 |

### 7.2 审批格式

```
APPROVAL
  type: human | policy
  approver: <user_id>
  timestamp: <ISO-8601>
  issue_key: JTO-XXX
  operation: issueUpdate | labelMutation
  approved: true | false
  reason: <if rejected>
```

---

## 8. Audit Log Required

### 8.1 审计字段

| 字段 | 说明 |
|------|------|
| `operation` | issueUpdate 或 labelMutation |
| `issue_id` | 目标 issue |
| `proposed_changes` | 提议的变更 |
| `validation_result` | 验证结果 |
| `approval_status` | 审批状态 |
| `dry_run` | true |
| `timestamp` | 操作时间 |
| `comment_id` | dry-run 评论 ID |

### 8.2 审计存储

审计日志存储在 `processing_logs` 表，`action_result_json` 字段包含完整 dry-run payload。

---

## 9. Rollback Strategy

### 9.1 如果真实 mutation 出现问题

1. 立即停止所有 mutation 操作
2. 记录 rollback 原因
3. 恢复 issue 到之前状态（手动或 API）
4. 清理已添加的标签
5. 通知相关人员
6. 审计回滚操作
7. 更新 gate 条件

### 9.2 P2 当前：无需回滚

P2 阶段仅 dry-run comment，无真实变更，无需回滚。

---

## 10. Duplicate Suppression

### 10.1 去重机制

| 机制 | 实现 |
|------|------|
| Idempotency key | `SHA256(operation + issue_id + proposed_changes)` |
| Comment check | 检查是否已有相同 dry-run comment |
| Time window | 同一 issue 5 分钟内不重复 dry-run |

---

## 11. 不包含 Secret 声明

本文档不包含任何 API key、token、password、secret、private key 或其他敏感信息。

---

**文档结束**
**P2-06 交付物 — Linear Mutation Dry-run Gate V1.0**
