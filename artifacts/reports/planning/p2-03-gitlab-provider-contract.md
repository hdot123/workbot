# GitLab Provider Contract

**文档编号**: P2-CONTRACT-003
**版本**: V1.0
**日期**: 2026-05-08
**关联 Linear Issue**: JTO-199
**P2 Project**: P2 — Long-task dry-run + GitLab CI feedback loop
**状态**: 设计稿（dry-run only, disabled-by-default）

---

## 1. 概述

本文档定义 GitLab 作为 CI pipeline result provider 的契约。该 provider 在 P2 阶段仅做设计，disabled-by-default，不启用。

**核心原则**：GitLab provider 仅接收 pipeline/job 结果事件，映射为 canonical event 格式，用于 dry-run 验证闭环。

---

## 2. Provider 标识

| 属性 | 值 |
|------|-----|
| `provider` | `"gitlab"` |
| `provider_version` | `"1.0"` |
| `enabled` | `false` (disabled-by-default) |
| `event_types` | `["pipeline", "job", "push", "merge_request"]` |

---

## 3. 支持的 Event 类型

### 3.1 Event 映射表

| GitLab Event Type | 触发条件 | canonical_type | 说明 |
|-------------------|---------|----------------|------|
| `pipeline` | Pipeline 状态变更 | `ci.pipeline.result` | 整体 pipeline 完成/失败/取消 |
| `job` | Job 状态变更 | `ci.job.result` | 单个 job 完成/失败 |
| `push` | Git push 到仓库 | `vcs.push` | 代码推送事件 |
| `merge_request` | MR 创建/更新/合并 | `vcs.merge_request` | MR 生命周期事件 |

### 3.2 canonical_type 完整映射

```
GitLab pipeline event
  ├── object_kind == "pipeline"
  │     → canonical_type = "ci.pipeline.result"
  │
  ├── object_kind == "job"
  │     → canonical_type = "ci.job.result"
  │
  ├── object_kind == "push"
  │     → canonical_type = "vcs.push"
  │
  └── object_kind == "merge_request"
        → canonical_type = "vcs.merge_request"
```

---

## 4. 事件字段映射

### 4.1 Pipeline 事件

| GitLab 字段 | 映射字段 | 类型 | 示例 |
|------------|---------|------|------|
| `object_attributes.id` | `pipeline_id` | int | `12345` |
| `object_attributes.sha` | `commit_sha` | string | `"abc123def456"` |
| `object_attributes.ref` | `branch` | string | `"main"` |
| `object_attributes.status` | `status` | string | `"success" \| "failed" \| "canceled"` |
| `project.id` | `project_id` | int | `789` |
| `project.path_with_namespace` | `project_path` | string | `"busiji/workbot"` |
| `object_attributes.created_at` | `timestamp` | ISO-8601 | `"2026-05-08T10:30:00Z"` |

### 4.2 Job 事件

| GitLab 字段 | 映射字段 | 类型 |
|------------|---------|------|
| `build_id` | `job_id` | int |
| `build_name` | `job_name` | string |
| `build_status` | `status` | string |
| `commit.sha` | `commit_sha` | string |
| `commit.ref` | `branch` | string |
| `pipeline_id` | `pipeline_id` | int |
| `project.id` | `project_id` | int |

### 4.3 Push 事件

| GitLab 字段 | 映射字段 | 类型 |
|------------|---------|------|
| `after` | `commit_sha` | string |
| `ref` | `branch` | string (strip `refs/heads/`) |
| `project.id` | `project_id` | int |
| `user_name` | `author` | string |

### 4.4 Merge Request 事件

| GitLab 字段 | 映射字段 | 类型 |
|------------|---------|------|
| `object_attributes.iid` | `mr_iid` | int |
| `object_attributes.state` | `mr_state` | string |
| `object_attributes.action` | `mr_action` | string |
| `object_attributes.target_branch` | `target_branch` | string |
| `object_attributes.source_branch` | `source_branch` | string |
| `project.id` | `project_id` | int |

---

## 5. 元数据字段

### 5.1 delivery_id / event_id

| 字段 | 生成方式 | 说明 |
|------|---------|------|
| `delivery_id` | `uuid4()` at webhook ingress time | 每次 webhook 递送唯一标识 |
| `event_id` | SHA256 of (provider + pipeline_id + timestamp) | 事件全局唯一标识，用于去重 |

### 5.2 Idempotency Key

```
idempotency_key = SHA256(provider + event_type + pipeline_id + commit_sha + status)
```

用途：
- 防止同一事件重复处理
- 审计日志关联
- retry 安全保证

### 5.3 Signature / Token Verification

| 方法 | 实现 |
|------|------|
| GitLab Secret Token | webhook payload header `X-Gitlab-Token` 与配置 token 比对 |
| 签名验证 | `X-Gitlab-Token` == configured secret (HMAC 可选) |
| 失败处理 | 401 Unauthorized，事件丢弃，记录 audit log |

**P2 阶段仅定义，不配置真实 token。**

---

## 6. Canonical Event 完整 Schema

```json
{
  "canonical_version": "1.0",
  "delivery_id": "<uuid>",
  "event_id": "<sha256>",
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
    "ref": "refs/heads/main",
    "duration_seconds": 180,
    "source": "push"
  },

  "metadata": {
    "raw_event_sha256": "<sha256>",
    "content_length": 1024,
    "source_ip": "192.168.88.37",
    "gitlab_webhook_version": "1.0"
  },

  "verification": {
    "token_verified": true,
    "token_method": "X-Gitlab-Token"
  }
}
```

---

## 7. Disabled-by-Default Policy

### 7.1 当前状态

| 项目 | 状态 |
|------|------|
| Provider enabled | ❌ false |
| Webhook 创建 | ❌ 禁止 |
| APISIX route | ❌ 禁止 |
| GitLab API 写操作 | ❌ 禁止 |
| 真实事件处理 | ❌ 禁止 |

### 7.2 启用前置条件（未来参考）

Provider 启用需满足：

1. ✅ P2-04 (Linear dry-run comment flow) 已通过验收
2. ✅ P2-05 (Factory real-dispatch gate) 已通过验收
3. ✅ P2-07 (Persistent audit upgrade) 已通过验收
4. ✅ GitLab webhook token 已配置且存储安全
5. ✅ APISIX route 已创建并限制 IP
6. ✅ 审计日志表已迁移
7. ✅ 人工审批通过

### 7.3 Dry-run 模式

P2 阶段使用 fake/simulated GitLab events 验证闭环：

```
模拟 GitLab pipeline event
  → 手动构造 canonical event
  → 验证 mapping 逻辑
  → 验证 idempotency key
  → 验证 audit log schema
  → 验证 Linear dry-run comment
```

---

## 8. Validation Checklist

| # | 检查项 | P2 状态 |
|---|--------|---------|
| 1 | provider=gitlab 明确定义 | ✅ |
| 2 | 4 种 event type 映射 | ✅ |
| 3 | canonical_type 映射表 | ✅ |
| 4 | pipeline_id/commit_sha/branch/status 字段 | ✅ |
| 5 | delivery_id / event_id 生成 | ✅ |
| 6 | idempotency key 算法 | ✅ |
| 7 | token verification 方案 | ✅ |
| 8 | disabled-by-default 政策 | ✅ |
| 9 | 无 webhook 创建 | ✅ |
| 10 | 无 APISIX route 创建 | ✅ |
| 11 | 无 GitLab API 写操作 | ✅ |
| 12 | 无 token/secret 输出 | ✅ |

---

## 9. 不包含 Secret 声明

本文档不包含任何 API key、token、password、secret、private key 或其他敏感信息。

所有示例均为结构定义和 schema 描述。token verification 仅描述算法，不包含真实值。

---

**文档结束**
**P2-03 交付物 — GitLab Provider Contract V1.0**
