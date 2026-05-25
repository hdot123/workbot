# OPS-LINEAR-008 Real Linear Canary Comment Validation Plan

> 文档编号：OPS-LINEAR-008  
> 版本：V1.0  
> 创建日期：2026-05-04  
> 维护人：bailian-worker

---

## 一、目标

在 **production_canary** 模式下，验证 Linear comment canary action 的完整闭环：

1. **Title/Label guard**：测试 Issue 必须带有 `[canary-ops-008]` 标记，canary workflow 仅对该标记 issue 执行 canary comment action
2. **Trigger Issue update**：真实 Linear Issue update 事件经 webhook ingress → n8n canary workflow → Linear API comment 创建
3. **Exactly one canary comment**：验证测试 Issue 上恰好出现 1 条 canary comment，内容为可识别的验证标记
4. **Duplicate replay idempotency**：对同一 delivery ID 重放，不产生第二条 canary comment

**约束**：canary action 默认关闭，本次验证前才临时开启，验证后立即关闭。

---

## 二、前置条件

| 条件 | 状态 |
|------|------|
| production_canary ingress 模式已运行 | ✅（OPS-LINEAR-007 已验证）|
| 公网入口 `POST /webhook/events` 活跃 | ✅ |
| `production-canary-events` n8n workflow active | ✅ |
| Supabase `webhook_canonical_events` / `webhook_processing_logs` 可查询 | ✅ |
| Linear API Token 可用（`lin_api_<TOKEN>`）| 需执行前确认 |
| JTO team ID 已知 | 需执行前确认 |
| Canary comment action 在 n8n workflow 中已实现但 disabled | 需执行前开启 |

### 2.1 Canary Comment Action 开关

在 n8n `production-canary-events` workflow 中：

- 当前：Webhook onReceived → Code node（minimal），无外部 API 调用
- 本次验证：新增 **Conditional Canary Comment** node，受环境变量/开关控制：
  - `N8N_CANARY_COMMENT_ENABLED=false`（默认）
  - 验证前设为 `true`
- 验证后立即恢复 `false`

---

## 三、测试 Issue 标记约定

| 项目 | 值 |
|------|-----|
| 标记 | **`[canary-ops-008]`** |
| 标题模板 | `[canary-ops-008] canary-validation-YYYYMMDD-HHMM` |
| 描述 | `[canary-ops-008] OPS-LINEAR-008 canary comment validation — create → update → wait for canary comment → replay → archive` |

> **Title guard**：canary workflow 的 Conditional 节点检查 issue title/description 包含 `[canary-ops-008]`，否则跳过 canary comment。

---

## 四、完整验证序列

### Phase 1 — 基础设施确认（T+00:00）

```bash
# 1. Health check
curl -s https://webhook.exa.edu.kg/health
# 预期：{"status":"ok","mode":"production_canary","events":<N>}

# 2. 确认 ingress mode
curl -s https://webhook.exa.edu.kg/health | python3 -c "import sys,json; d=json.load(sys.stdin); assert d['mode']=='production_canary'"

# 3. 确认 n8n canary workflow active
# 通过 n8n API 或 SSH 隧道 UI 确认 production-canary-events 状态 = active

# 4. 开启 canary comment action（验证前）
# 在 n8n workflow 环境变量中设置 N8N_CANARY_COMMENT_ENABLED=true
# 或通过 n8n UI 启用 canary comment node
```

### Phase 2 — 创建测试 Issue（T+00:01）

使用 GraphQL mutation 创建带标记的测试 Issue：

```graphql
mutation CreateCanaryTestIssue {
  issueCreate(
    input: {
      teamId: "<JTO_TEAM_ID>",
      title: "[canary-ops-008] canary-validation-YYYYMMDD-HHMM",
      description: "[canary-ops-008] OPS-LINEAR-008 canary comment validation — create → update → wait for canary comment → replay → archive"
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

**记录返回值**：
- `issue.id`（用于后续操作和验证）
- `issue.identifier`（如 `JTO-NNN`，用于 UI 检查）
- `issue.url`

> **注意**：Issue/create 事件也会到达 webhook，但 canary comment 逻辑设计为仅响应 **Issue/update** 事件（见 Phase 3），因此 create 阶段不预期 canary comment。

### Phase 3 — 触发 Issue Update（T+00:05）

```graphql
mutation UpdateCanaryTestIssue($issueId: String!) {
  issueUpdate(
    id: $issueId,
    input: {
      description: "[canary-ops-008] Updated — triggering canary comment action"
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

**预期事件流**：

```
Linear Issue/update webhook
    ↓
POST /webhook/events (公网入口)
    ↓
webhook-ingress signature verify → normalize → idempotency check
    ↓
store in Supabase (webhook_raw_events + webhook_canonical_events)
    ↓
forward to n8n (production-canary-events webhook URL)
    ↓
n8n workflow: parse canonical event
    ↓
title/label guard check: issue title 包含 [canary-ops-008] → PASS
    ↓
canary comment action: POST Linear GraphQL commentCreate
    ↓
canary comment 出现在测试 Issue 上
```

**Wait time**：更新后等待 **30 秒**（webhook delivery ~2s + ingress processing ~1s + n8n execution ~5s + Linear API comment creation ~3s + buffer）

### Phase 4 — 验证 Canary Comment 存在（T+00:35）

#### 4.1 GraphQL 查询验证

```graphql
query GetIssueComments($issueId: String!) {
  issue(id: $issueId) {
    id
    identifier
    title
    comments {
      nodes {
        id
        body
        createdAt
        user {
          name
        }
      }
    }
  }
}
```

**验证条件**：
- `comments.nodes.length >= 1`
- 至少一条 comment 的 `body` 包含 canary 标记文本（如 `[ops-linear-008-canary]` 或 `[canary-ops-008] verified`）
- 记录该 canary comment 的 `id` 和 `createdAt`

#### 4.2 Supabase 事件验证

```sql
-- 查询最近 5 分钟内的 canonical 事件
SELECT
    ce.event_id,
    ce.canonical_type,
    ce.canonical_action,
    ce.provider_event_type,
    ce.provider_action,
    ce.n8n_forwarded,
    ce.delivery_id,
    ce.created_at
FROM webhook_canonical_events ce
WHERE ce.provider = 'linear'
  AND ce.created_at > NOW() - INTERVAL '5 minutes'
ORDER BY ce.created_at ASC;
```

**预期结果**：至少 2 行

| canonical_type | canonical_action | n8n_forwarded |
|---------------|-----------------|---------------|
| issue | created | 1 |
| issue | updated | 1 |

#### 4.3 n8n Execution 验证

通过 n8n UI 或 API 查看 `production-canary-events` workflow 的最新 execution：

```bash
# 通过 n8n API（需 SSH 隧道）
curl -s http://127.0.0.1:5678/api/v1/executions \
  --data-urlencode "workflowId=<CANARY_WORKFLOW_ID>" \
  --data-urlencode "limit=5" \
  -H "X-N8N-API-KEY: <N8N_API_KEY>"
```

**预期**：
- 最近一次 execution 状态 = `success`
- execution 中包含 canary comment HTTP Request node 成功执行
- execution 日志中可见 `[canary-ops-008]` title guard 通过

### Phase 5 — 幂等重放验证（T+01:00）

使用 Supabase 中记录的真实 delivery ID 对同一事件进行重放：

#### 5.1 构造重放请求

重放使用与 Phase 3 相同的 `Linear-Delivery` header 和原始 payload：

```bash
# 从 Supabase 获取原始 payload 和 delivery ID
SELECT ce.delivery_id, re.raw_body
FROM webhook_canonical_events ce
JOIN webhook_raw_events re ON re.canonical_event_id = ce.event_id
WHERE ce.canonical_type = 'issue'
  AND ce.canonical_action = 'updated'
ORDER BY ce.created_at DESC
LIMIT 1;
```

使用重放的 delivery ID 和原始 payload 发送到公网入口：

```bash
curl -s -X POST https://webhook.exa.edu.kg/webhook/events \
  -H "Content-Type: application/json" \
  -H "Linear-Delivery: <delivery-id-from-phase-3>" \
  -H "X-Linear-Signature: sha256=<signature>" \
  -d '<original-payload-from-phase-3>'
```

> **签名说明**：重放需携带有效的 `X-Linear-Signature`。如果签名是基于原始 payload 和 webhook secret 计算的 HMAC，需要知道 webhook secret。替代方案：通过 ingress 代码路径确认重放也走 idempotency check（delivery ID 已存在 → `duplicate_accepted`）。

#### 5.2 验证重放响应

```json
// 第一次请求（Phase 3 原始事件）
{ "ok": true, "status": "accepted", "event_id": "evt_xxx" }

// 重放请求（Phase 5）
{ "ok": true, "status": "duplicate_accepted", "event_id": "evt_xxx" }
```

#### 5.3 验证无第二条 Canary Comment

```graphql
query GetIssueCommentsAfterReplay($issueId: String!) {
  issue(id: $issueId) {
    comments {
      nodes {
        id
        body
        createdAt
      }
    }
  }
}
```

**验证条件**：
- canary comment 数量 = Phase 4 验证时的数量（没有新增）
- 无新的 canary comment `createdAt` 时间戳在重放之后

#### 5.4 Supabase 重复事件验证

```sql
-- 确认 canonical event 数量未增加
SELECT
    ce.canonical_type,
    ce.canonical_action,
    COUNT(*) as event_count
FROM webhook_canonical_events ce
WHERE ce.provider = 'linear'
  AND ce.created_at > NOW() - INTERVAL '10 minutes'
GROUP BY ce.canonical_type, ce.canonical_action;
```

**预期**：
- `issue/updated` 的 `event_count = 1`（幂等阻止了重复）

### Phase 6 — 关闭 Canary Action（T+01:10）

```bash
# 在 n8n workflow 中关闭 canary comment action
# 设置 N8N_CANARY_COMMENT_ENABLED=false
# 或在 n8n UI 中禁用 canary comment node

# 确认 ingress mode 仍然是 production_canary
curl -s https://webhook.exa.edu.kg/health | python3 -c "import sys,json; d=json.load(sys.stdin); assert d['mode']=='production_canary'"
```

### Phase 7 — 清理归档（T+01:15）

#### 7.1 Archive 测试 Issue

```graphql
mutation ArchiveCanaryTestIssue($issueId: String!) {
  issueArchive(id: $issueId) {
    success
  }
}
```

#### 7.2 归档验证

```graphql
query VerifyIssueArchived($issueId: String!) {
  issue(id: $issueId) {
    id
    identifier
    archivedAt
    state {
      name
    }
  }
}
```

**预期**：`archivedAt` 不为 null

#### 7.3 Supabase 清理事件确认

Archive 会触发 `Issue/archive` → `issue/closed` 事件，产生额外的一行 canonical 记录。这是预期行为，不需要清理 Supabase 数据。

---

## 五、证据收集清单

| 序号 | 证据项 | 收集方式 |
|------|--------|----------|
| E1 | Health check 输出 | `curl` 结果 |
| E2 | ingress mode 确认 | `curl` 结果 |
| E3 | 创建 Issue 的 GraphQL response | mutation 返回值 |
| E4 | Issue update 的 GraphQL response | mutation 返回值 |
| E5 | n8n execution success（含 canary comment node）| n8n API / UI 截图 |
| E6 | Canary comment 存在 | GraphQL `comments.nodes` 查询 |
| E7 | Supabase canonical events（3 条） | SQL 查询结果 |
| E8 | 重放响应 `duplicate_accepted` | `curl` 结果 |
| E9 | 重放后 canary comment 数量不变 | GraphQL 查询结果 |
| E10 | 重放后 Supabase canonical event count 不变 | SQL 查询结果 |
| E11 | canary action 关闭确认 | n8n UI / 环境变量 |
| E12 | Issue archived 确认 | GraphQL 查询结果 |

---

## 六、完整时间线

```
T+00:00  — Phase 1: 基础设施确认 + 开启 canary action
T+00:01  — Phase 2: issueCreate → Issue/create webhook（不触发 canary comment）
T+00:05  — Phase 3: issueUpdate → Issue/update webhook → 触发 canary comment
T+00:35  — Phase 4: 验证 canary comment 存在（30s wait）
T+00:40  — Phase 4: Supabase + n8n execution 验证
T+01:00  — Phase 5: 重放同一 delivery ID
T+01:05  — Phase 5: 验证无第二条 canary comment + Supabase count 不变
T+01:10  — Phase 6: 关闭 canary action
T+01:15  — Phase 7: Archive 测试 Issue
T+01:20  — Phase 7: 归档验证
T+01:25  — 整理证据，撰写验证报告
```

---

## 七、GraphQL Query/Mutation 模板汇总

### A. Issue 操作

#### A1. Create Issue

```graphql
mutation CreateCanaryTestIssue {
  issueCreate(
    input: {
      teamId: "<JTO_TEAM_ID>",
      title: "[canary-ops-008] canary-validation-YYYYMMDD-HHMM",
      description: "[canary-ops-008] OPS-LINEAR-008 canary comment validation — create → update → wait for canary comment → replay → archive"
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

#### A2. Update Issue

```graphql
mutation UpdateCanaryTestIssue($issueId: String!) {
  issueUpdate(
    id: $issueId,
    input: {
      description: "[canary-ops-008] Updated — triggering canary comment action"
    }
  ) {
    success
    issue {
      id
      identifier
      updatedAt
    }
  }
}
```

#### A3. Archive Issue

```graphql
mutation ArchiveCanaryTestIssue($issueId: String!) {
  issueArchive(id: $issueId) {
    success
  }
}
```

### B. Comment 查询

```graphql
query GetIssueComments($issueId: String!) {
  issue(id: $issueId) {
    id
    identifier
    title
    comments {
      nodes {
        id
        body
        createdAt
        user {
          name
        }
      }
    }
  }
}
```

### C. 归档验证

```graphql
query VerifyIssueArchived($issueId: String!) {
  issue(id: $issueId) {
    id
    identifier
    archivedAt
    state {
      name
    }
  }
}
```

### D. Team 查询（用于获取 JTO_TEAM_ID）

```graphql
query GetTeams {
  teams {
    nodes {
      id
      key
      name
    }
  }
}
```

### E. 所有 GraphQL 请求通用格式

```
POST https://api.linear.app/graphql
Authorization: Bearer lin_api_<TOKEN>
Content-Type: application/json
```

---

## 八、Supabase 查询模板汇总

### B1. 最近 canonical 事件

```sql
SELECT
    ce.event_id,
    ce.canonical_type,
    ce.canonical_action,
    ce.provider_event_type,
    ce.provider_action,
    ce.delivery_id,
    ce.n8n_forwarded,
    ce.created_at
FROM webhook_canonical_events ce
WHERE ce.provider = 'linear'
  AND ce.created_at > NOW() - INTERVAL '<WINDOW> minutes'
ORDER BY ce.created_at ASC;
```

### B2. 事件计数验证

```sql
SELECT
    ce.canonical_type,
    ce.canonical_action,
    COUNT(*) as event_count
FROM webhook_canonical_events ce
WHERE ce.provider = 'linear'
  AND ce.created_at > NOW() - INTERVAL '<WINDOW> minutes'
GROUP BY ce.canonical_type, ce.canonical_action
ORDER BY ce.created_at ASC;
```

### B3. 获取重放用原始 payload

```sql
SELECT ce.delivery_id, re.raw_body
FROM webhook_canonical_events ce
JOIN webhook_raw_events re ON re.canonical_event_id = ce.event_id
WHERE ce.canonical_type = 'issue'
  AND ce.canonical_action = 'updated'
ORDER BY ce.created_at DESC
LIMIT 1;
```

### B4. Processing logs 验证

```sql
SELECT
    phase,
    level,
    message,
    event_id,
    created_at
FROM webhook_processing_logs
WHERE provider = 'linear'
  AND created_at > NOW() - INTERVAL '<WINDOW> minutes'
ORDER BY created_at ASC;
```

---

## 九、风险与缓解

| 风险 | 影响 | 缓解 |
|------|------|------|
| Canary comment action 未正确开启 | 无 canary comment 产生 | Phase 1 确认开关状态 |
| Title guard 未生效 | 非测试 issue 也可能收到 canary comment | 验证前检查 n8n workflow 中的 condition 逻辑 |
| Linear API rate limit | commentCreate 失败 | Linear API 限制宽松，单操作不会触发 |
| Webhook delivery 延迟 > 30s | canary comment 验证时可能未到 | 如未找到，延长 wait time 至 60s 重试 |
| 重放请求签名无效 | 重放被 401 拒绝 | 使用 ingress 代码中的 idempotency check 路径确认 |
| Canary comment 已存在但来自其他来源 | 误判 | 验证 comment body 包含 `[ops-linear-008-canary]` 标记 |

---

## 十、验收标准

| 编号 | 标准 | 判定 |
|------|------|------|
| P0-CAN-01 | 测试 Issue title 包含 `[canary-ops-008]` | title guard 确认 |
| P0-CAN-02 | Issue/update 事件到达 ingress 并被正常处理 | Supabase 有 `issue/updated` 记录，`n8n_forwarded=1` |
| P0-CAN-03 | 测试 Issue 上恰好出现 1 条 canary comment | GraphQL query 验证 |
| P0-CAN-04 | Canary comment body 包含可识别标记 | body 包含 `[ops-linear-008-canary]` |
| P0-CAN-05 | 重放同一 delivery ID 返回 `duplicate_accepted` | HTTP response 验证 |
| P0-CAN-06 | 重放后 canary comment 数量不变 | GraphQL query 对比 |
| P0-CAN-07 | 重放后 Supabase canonical event count 不变 | SQL 计数验证 |
| P0-CAN-08 | 验证后 canary action 已关闭 | 配置确认 |
| P0-CAN-09 | 测试 Issue 已 archived | GraphQL 验证 `archivedAt != null` |

---

## 十一、与其他文档的关系

| 本文档 | 关联文档 | 关系说明 |
|--------|----------|----------|
| OPS-LINEAR-008 验证方案 | OPS-LINEAR-007 canary report | 本文档是 007 末尾提到的 "Linear comment canary action" 的验证方案 |
| OPS-LINEAR-008 验证方案 | OPS-LINEAR-005 shadow validation | 复用相同的 GraphQL mutation 模式和 Supabase 查询模式 |
| OPS-LINEAR-008 验证方案 | OPS-LINEAR-006 minimal trigger | 复用事件触发和验证的时间线模式 |
| OPS-LINEAR-008 验证方案 | SEC-ARCH-001 | 遵循签名校验和暴露面收敛原则 |

---

**文档状态**：草稿中  
**审批人**：待定
