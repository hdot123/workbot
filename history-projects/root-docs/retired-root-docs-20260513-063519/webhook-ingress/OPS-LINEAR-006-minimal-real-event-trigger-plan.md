# OPS-LINEAR-006 Minimal Real Event Trigger Plan

> 文档编号：OPS-LINEAR-006  
> 版本：V1.0  
> 创建日期：2026-05-04  
> 维护人：bailian-worker  

---

## 一、目标

在 **不修改现有 Linear webhook 配置** 的前提下，通过 shadow webhook `https://webhook.exa.edu.kg/webhooks/linear` 触发并验证三事件最小序列：

1. **Issue created** → `issue` / `created`
2. **Issue updated** → `issue` / `updated`
3. **Comment created** → `comment` / `created`

完成后 archive 临时 Issue，保持团队 backlog 清洁。

---

## 二、前置条件

| 条件 | 状态 |
|------|------|
| Shadow webhook 已存在（Linear webhook ID: `9e1edca6-1d2c-4f42-9a7c-07ddb5654d0d`） | ✅ |
| Shadow webhook URL: `https://webhook.exa.edu.kg/webhooks/linear` | ✅ |
| Shadow webhook resource types 包含 `Issue` + `Comment` | ✅（继承自 OPS-LINEAR-005 配置） |
| Node-22 shadow ingress 运行正常（`WEBHOOK_INGRESS_MODE=shadow`） | 待执行前确认 |
| Supabase 数据库连接正常 | 待执行前确认 |
| JTO team ID 已知 | 需获取 |
| Linear API Token 可用 | 需获取 |

---

## 三、测试 Issue 标记

| 项目 | 值 |
|------|-----|
| 临时 Issue 标记 | **`[shadow-ops-006]`** |
| 标题模板 | `webhook-test-shadow-ops-006-YYYYMMDD` |
| 描述 | `[shadow-ops-006] Minimal real event trigger test — Issue create → update → comment create → archive` |

> **标记约定**：标题和描述中包含 `[shadow-ops-006]` 标记，便于后续在 Supabase 中按文本检索或在 Linear 中按标题过滤。

---

## 四、GraphQL Mutations

### 4.1 通用请求格式

```
POST https://api.linear.app/graphql
Authorization: Bearer lin_api_<TOKEN>
Content-Type: application/json
```

### 4.2 Step 1 — Create Issue

```graphql
mutation CreateTestIssue {
  issueCreate(
    input: {
      teamId: "<JTO_TEAM_ID>",
      title: "[shadow-ops-006] webhook-test-YYYYMMDD",
      description: "[shadow-ops-006] Minimal real event trigger test — Issue create → update → comment create → archive"
    }
  ) {
    success
    issue {
      id
      identifier
      url
      title
    }
  }
}
```

**预期 webhook 事件**：

| 字段 | 值 |
|------|-----|
| `type` | `Issue` |
| `action` | `create` |
| Shadow canonical | `issue` / `created` |
| `n8n_forwarded` | `0` |

### 4.3 Step 2 — Update Issue

```graphql
mutation UpdateTestIssue($issueId: String!) {
  issueUpdate(
    id: $issueId,
    input: {
      description: "[shadow-ops-006] Updated — step 2 of trigger test"
    }
  ) {
    success
    issue {
      id
      identifier
      title
      updatedAt
    }
  }
}
```

```json
{
  "issueId": "<step-1-returned-issue-id>"
}
```

**预期 webhook 事件**：

| 字段 | 值 |
|------|-----|
| `type` | `Issue` |
| `action` | `update` |
| Shadow canonical | `issue` / `updated` |
| `n8n_forwarded` | `0` |

### 4.4 Step 3 — Create Comment

```graphql
mutation CreateTestComment($issueId: String!) {
  commentCreate(
    input: {
      issueId: $issueId,
      body: "[shadow-ops-006] Comment trigger test — step 3"
    }
  ) {
    success
    comment {
      id
      body
      createdAt
    }
  }
}
```

```json
{
  "issueId": "<step-1-returned-issue-id>"
}
```

**预期 webhook 事件**：

| 字段 | 值 |
|------|-----|
| `type` | `Comment` |
| `action` | `create` |
| Shadow canonical | `comment` / `created` |
| `n8n_forwarded` | `0` |

---

## 五、验证

### 5.1 Shadow 端验证（Supabase SQL）

```sql
-- 查询 [shadow-ops-006] 相关事件
SELECT
    ce.event_id,
    ce.canonical_type,
    ce.canonical_action,
    ce.provider_event_type,
    ce.provider_action,
    ce.n8n_forwarded,
    ce.source_resource_id,
    ce.created_at
FROM webhook_canonical_events ce
WHERE ce.provider = 'linear'
  AND ce.created_at > NOW() - INTERVAL '15 minutes'
  AND ce.canonical_type IN ('issue', 'comment')
ORDER BY ce.created_at ASC;
```

**预期结果**：3 行

| canonical_type | canonical_action | n8n_forwarded |
|---------------|-----------------|---------------|
| issue | created | 0 |
| issue | updated | 0 |
| comment | created | 0 |

### 5.2 Health Check

```bash
curl -s https://webhook.exa.edu.kg/health
# 预期：{"status":"ok","mode":"shadow"}
```

---

## 六、清理

### 6.1 Archive Issue（GraphQL）

```graphql
mutation ArchiveTestIssue($issueId: String!) {
  issueArchive(id: $issueId) {
    success
  }
}
```

```json
{
  "issueId": "<step-1-returned-issue-id>"
}
```

> **注意**：Archive 会触发 `Issue/archive` webhook 事件，canonical 映射为 `issue/closed`。产生第 4 条事件，**不属于本次最小验证目标**，但不可避免。

### 6.2 彻底删除（可选，仅当需要时）

```graphql
mutation DeleteTestIssue($issueId: String!) {
  issueDelete(id: $issueId) {
    success
  }
}
```

```json
{
  "issueId": "<step-1-returned-issue-id>"
}
```

> **注意**：`issueDelete` 产生 `Issue/delete` → `issue/deleted` 第 5 条事件。**建议仅 archive，不删除**。

### 6.3 不删除 shadow webhook

Shadow webhook（ID: `9e1edca6-1d2c-4f42-9a7c-07ddb5654d0d`）**保留**，为后续测试轮次复用。

### 6.4 Supabase 数据保留

测试记录**保留用于审计**，通过 `source_resource_id` 或事件中的 `[shadow-ops-006]` 标记可识别。

---

## 七、完整时间线

```
T+00:00  — Health check: curl https://webhook.exa.edu.kg/health
T+00:01  — Step 1: issueCreate → Issue/create webhook
T+00:05  — Step 2: issueUpdate → Issue/update webhook
T+00:10  — Step 3: commentCreate → Comment/create webhook
T+00:15  — Step 4: issueArchive → Issue/archive webhook（额外，不可避）
T+00:20  — Supabase 验证：3 目标 + 1 archive 事件
T+00:25  — 记录结果
```

---

## 八、风险与注意事项

| 风险 | 影响 | 缓解 |
|------|------|------|
| Shadow ingress 未运行 | 404 拒绝 | 执行前确认 health endpoint |
| Linear API Token 过期 | mutation 失败 | 确认 token 有效 |
| Comment 未触发 webhook | Linear webhook 未订阅 Comment | 确认 shadow webhook resourceTypes 包含 Comment |
| 步骤间隔太短导致事件乱序 | Supabase 写入顺序可能不一致 | 步骤间等待 ≥ 3 秒 |

---

## 九、与其他文档的关系

| 本文档 | 关联文档 | 关系说明 |
|--------|----------|----------|
| OPS-LINEAR-006 触发方案 | OPS-LINEAR-005 触发方案 | 本方案复用 OPS-LINEAR-005 的 shadow webhook 基础设施 |
| OPS-LINEAR-006 触发方案 | OPS-LINEAR-005 验证报告 | 参考 JTO-179 的成功经验，使用相同 mutation 模式 |

---

**文档状态**：草稿中  
**审批人**：待定
