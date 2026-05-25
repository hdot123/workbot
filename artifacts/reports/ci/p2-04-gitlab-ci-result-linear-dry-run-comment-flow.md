# GitLab CI Result → Linear Dry-run Comment Flow

**文档编号**: P2-FLOW-004
**版本**: V1.0
**日期**: 2026-05-08
**关联 Linear Issue**: JTO-200
**P2 Project**: P2 — Long-task dry-run + GitLab CI feedback loop
**状态**: 设计稿（dry-run only, comment-only）

---

## 1. 概述

本文档定义 GitLab CI pipeline 结果如何回写到 Linear issue 的 dry-run comment flow。P2 阶段只允许 comment，不允许 issueUpdate。

**核心原则**：只读评论，不改状态，不改标签。

---

## 2. 完整事件流

```
GitLab Pipeline
  │
  │ webhook POST (X-Gitlab-Token verified)
  ▼
webhook-ingress (:3100)
  │
  │ raw event → raw_events table
  │ delivery_id = uuid4()
  ▼
Canonical Event Transformer
  │
  │ Map GitLab fields → canonical schema
  │ canonical_type = "ci.pipeline.result"
  │ idempotency_key = SHA256(...)
  │ event_id = SHA256(...)
  ▼
Audit Logger
  │
  │ canonical_event → canonical_events table
  │ processing_log → processing_logs table
  ▼
Linear Comment Dispatcher (dry-run mode)
  │
  │ Construct comment body
  │ Linear API: issueAddComment (NOT issueUpdate)
  │ No state change, no label change
  ▼
Linear Issue Comment
  │
  │ [🔬 DRY-RUN] Pipeline #12345: ✅ success
  │ commit_sha: abc123def456
  │ branch: main
  │ ...
  ▼
Audit Evidence
  │
  │ comment_id recorded → action_result_json
  │ audit trail complete
```

---

## 3. Canonical Event Schema

```json
{
  "canonical_version": "1.0",
  "delivery_id": "d-<uuid>",
  "event_id": "e-<sha256>",
  "idempotency_key": "<sha256>",
  "provider": "gitlab",
  "canonical_type": "ci.pipeline.result",
  "timestamp": "2026-05-08T10:30:00Z",
  "payload": {
    "pipeline_id": 12345,
    "commit_sha": "abc123def456",
    "branch": "main",
    "status": "success",
    "project_id": 789,
    "project_path": "busiji/workbot",
    "duration_seconds": 180
  },
  "metadata": {
    "raw_event_sha256": "<sha256>",
    "source_ip": "192.168.88.37"
  }
}
```

---

## 4. Audit Log Schema

### 4.1 raw_events

| Column | Type | 说明 |
|--------|------|------|
| `id` | UUID PK | 主键 |
| `delivery_id` | UUID | 递送唯一标识 |
| `provider` | VARCHAR | "gitlab" |
| `raw_body` | JSONB | 原始 webhook body |
| `raw_body_sha256` | VARCHAR | SHA256 校验 |
| `received_at` | TIMESTAMPTZ | 接收时间 |
| `source_ip` | INET | 来源 IP |

### 4.2 canonical_events

| Column | Type | 说明 |
|--------|------|------|
| `id` | UUID PK | 主键 |
| `event_id` | VARCHAR | 事件唯一标识 |
| `delivery_id` | UUID FK | 关联 raw_event |
| `idempotency_key` | VARCHAR UNIQUE | 去重键 |
| `canonical_type` | VARCHAR | "ci.pipeline.result" |
| `payload` | JSONB | 规范化 payload |
| `created_at` | TIMESTAMPTZ | 创建时间 |

### 4.3 processing_logs

| Column | Type | 说明 |
|--------|------|------|
| `id` | UUID PK | 主键 |
| `event_id` | VARCHAR FK | 关联 canonical_event |
| `action` | VARCHAR | "linear_comment_dry_run" |
| `action_result_json` | JSONB | 操作结果 |
| `status` | VARCHAR | "success" / "failed" |
| `created_at` | TIMESTAMPTZ | 创建时间 |

---

## 5. Linear Comment 策略

### 5.1 只允许的操作

| 操作 | 允许 | API |
|------|------|-----|
| `issueAddComment` | ✅ | Linear GraphQL mutation |
| `issueUpdate` (状态) | ❌ | 禁止 |
| `issueUpdate` (标签) | ❌ | 禁止 |

### 5.2 评论格式要求

所有 dry-run 评论必须以 `[🔬 DRY-RUN]` 前缀标记。

---

## 6. Comment 模板

### 6.1 Success 模板

```
[🔬 DRY-RUN] GitLab CI Pipeline Result

| Field | Value |
|-------|-------|
| pipeline_id | #12345 |
| status | ✅ success |
| commit_sha | `abc123def456` |
| branch | `main` |
| project | busiji/workbot |
| duration | 3m 0s |
| linear_issue | JTO-XXX |

**Audit**: delivery_id=`d-<uuid>`, event_id=`e-<sha256>`

---
🤖 This is a dry-run comment. No state/label changes were made.
```

### 6.2 Failure 模板

```
[🔬 DRY-RUN] GitLab CI Pipeline Result

| Field | Value |
|-------|-------|
| pipeline_id | #12345 |
| status | ❌ failed |
| commit_sha | `abc123def456` |
| branch | `main` |
| project | busiji/workbot |
| failed_stage | test |
| duration | 2m 15s |
| linear_issue | JTO-XXX |

**Audit**: delivery_id=`d-<uuid>`, event_id=`e-<sha256>`

**Next**: max_fix_attempts remaining: 2/3

---
🤖 This is a dry-run comment. No state/label changes were made.
```

### 6.3 Canceled 模板

```
[🔬 DRY-RUN] GitLab CI Pipeline Result

| Field | Value |
|-------|-------|
| pipeline_id | #12345 |
| status | ⏸️ canceled |
| commit_sha | `abc123def456` |
| branch | `main` |
| project | busiji/workbot |
| linear_issue | JTO-XXX |

---
🤖 This is a dry-run comment. Pipeline was canceled.
```

---

## 7. 禁止事项矩阵

| 禁止项 | 状态 | 原因 |
|--------|------|------|
| issueUpdate (状态变更) | ❌ 禁止 | P2 仅 dry-run |
| label mutation | ❌ 禁止 | P2 仅 dry-run |
| GitHub push | ❌ 禁止 | fail-closed |
| Factory dispatch | ❌ 禁止 | dry-run only |
| webhook 创建 | ❌ 禁止 | 不修改基础设施 |
| APISIX route 创建 | ❌ 禁止 | 不修改基础设施 |

---

## 8. Idempotency 保证

| 场景 | 处理 |
|------|------|
| 重复 webhook 递送 | 检查 idempotency_key，跳过已处理事件 |
| 评论重复 | 检查 event_id 是否已有对应评论 |
| 乱序事件 | 按 timestamp 排序，只处理最新状态 |

---

## 9. 不包含 Secret 声明

本文档不包含任何 API key、token、password、secret、private key 或其他敏感信息。

---

**文档结束**
**P2-04 交付物 — GitLab CI → Linear Dry-run Comment Flow V1.0**
