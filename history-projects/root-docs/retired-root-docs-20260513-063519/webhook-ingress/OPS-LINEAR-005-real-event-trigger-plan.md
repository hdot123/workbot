# Linear Real Event Trigger Sequence — Minimal Plan

> 文档编号：OPS-LINEAR-005  
> 版本：V1.0  
> 创建日期：2026-05-04  
> 维护人：bailian-worker  

---

## 一、目标

在 **不修改生产 Linear webhook 配置** 的前提下，通过 Linear UI/API 创建真实 Issue → 更新 Issue → 添加 Comment → Archive Issue，验证：

1. 生产 webhook `https://webhook.exa.edu.kg/webhook/events` 收到事件 → 触发 n8n 原有 workflow
2. Shadow webhook `https://webhook.exa.edu.kg/webhooks/linear` 收到事件 → 存入 Supabase（shadow mode，不转发 n8n）
3. 事件序列完整覆盖 `Issue/create` → `Issue/update` → `Comment/create` → `Issue/archive`

---

## 二、当前生产拓扑（只读确认）

| 组件 | 端点 | 模式 |
|------|------|------|
| n8n 生产 webhook | `POST /webhook/events` | 活跃，处理所有 Linear 事件 |
| Shadow webhook | `POST /webhooks/linear` | shadow mode，存储但不转发 n8n |
| Cloudflare Tunnel | → n8n-webhook-gateway nginx | 公网入口 `webhook.exa.edu.kg` |
| Supabase | webhook DB（ref: `rxrcidmnbyvwmhxqdgku`） | 三表：raw / canonical / logs |

**关键约束**：
- Linear webhook 已在 Linear Settings → Webhooks 中注册，指向生产 URL
- Shadow endpoint 由 nginx 新增 `/webhooks/linear` location 路由
- 两个端点**共享同一个 Linear webhook secret**（来自 1Password `supabase-webhook数据库`）

---

## 三、测试 Issue 方案

### 3.1 测试 Issue 命名

| 项目 | 值 |
|------|-----|
| 团队 | JTO（JTOOM workspace） |
| 新 Issue 编号 | **临时创建，记下 identifier**（如 `JTO-NNN`） |
| 标题 | `webhook-test-YYYYMMDD-HHMM`（确保唯一可检索） |
| 描述 | `Real event trigger test for OPS-LINEAR-005` |

### 3.2 前置 Issue 清理

- 原测试 Issue `JTO-177` 已 archived，**不复用**
- 新 Issue 创建后完成全序列 → 立即 archived → 不污染团队 backlog

---

## 四、Linear GraphQL 操作方案

以下所有操作使用 Linear API `https://api.linear.app/graphql`，需 Bearer Token（从 1Password 获取 `lin_api_*`）。

> **方案 A（推荐）：通过 Linear UI 手动操作**  
> 最简单、最真实。直接在浏览器中操作 Linear 即可触发 webhook 事件。无需写 GraphQL。

> **方案 B：通过 GraphQL mutation API 操作**  
> 适合自动化脚本，但需注意 Linear 的 mutation 参数可能随版本变化。

### 4.1 方案 A — Linear UI 手动操作（推荐）

**Step 1 — Create Issue**
1. 打开 Linear → 选择 JTO 团队
2. 点击 `C` 创建新 Issue
3. 标题：`webhook-test-20260504`
4. 描述：`Real event trigger test for OPS-LINEAR-005`
5. 点击 `Create`

**Step 2 — Update Issue**
1. 打开刚创建的 Issue
2. 修改标题为：`webhook-test-20260504-updated`
3. 或修改描述
4. 点击保存

**Step 3 — Add Comment**
1. 在 Issue 底部 Comment 区域
2. 输入：`webhook trigger test comment — OPS-LINEAR-005`
3. 点击发送

**Step 4 — Archive Issue**
1. 在 Issue 中点击 `⋯` → `Archive`
2. 确认归档

### 4.2 方案 B — GraphQL Mutation（备选）

所有 mutation 通过同一个端点发送：

```
POST https://api.linear.app/graphql
Authorization: Bearer lin_api_<TOKEN>
Content-Type: application/json
```

#### Step 1 — Create Issue

```graphql
mutation CreateTestIssue {
  issueCreate(
    input: {
      teamId: "<JTO_TEAM_ID>",
      title: "webhook-test-20260504",
      description: "Real event trigger test for OPS-LINEAR-005"
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
| 生产端 | n8n 收到，原有 workflow 执行 |
| Shadow 端 | 存入 Supabase，`canonical_type=issue`, `canonical_action=created` |

#### Step 2 — Update Issue

```graphql
mutation UpdateTestIssue($issueId: String!) {
  issueUpdate(
    id: $issueId,
    input: {
      title: "webhook-test-20260504-updated",
      description: "Real event trigger test for OPS-LINEAR-005 — updated"
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
| 生产端 | n8n 收到，原有 workflow 执行 |
| Shadow 端 | 存入 Supabase，`canonical_type=issue`, `canonical_action=updated` |

#### Step 3 — Create Comment

```graphql
mutation CreateTestComment($issueId: String!) {
  commentCreate(
    input: {
      issueId: $issueId,
      body: "webhook trigger test comment — OPS-LINEAR-005"
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
| 生产端 | n8n 收到，原有 workflow 执行 |
| Shadow 端 | 存入 Supabase，`canonical_type=comment`, `canonical_action=created` |

> **注意**：Linear adapter 中 `type_map` 包含 `"Comment": "comment"`，`action_map` 包含 `"create": "created"`，所以 Comment/create 能被正确映射。

#### Step 4 — Archive Issue

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

**预期 webhook 事件**：

| 字段 | 值 |
|------|-----|
| `type` | `Issue` |
| `action` | `archive` |
| 生产端 | n8n 收到，原有 workflow 执行 |
| Shadow 端 | 存入 Supabase，`canonical_type=issue`, `canonical_action=closed` |

> **注意**：Linear adapter 中 `action_map` 包含 `"archive": "closed"`。

---

## 五、Webhook Payload 结构预期

Linear webhook 发送到 `https://webhook.exa.edu.kg/webhook/events`（生产）和 `https://webhook.exa.edu.kg/webhooks/linear`（shadow）的 payload 格式如下：

### Issue Create

```json
{
  "action": "create",
  "type": "Issue",
  "organizationId": "<org-id>",
  "actorId": "<actor-id>",
  "userAgent": "Linear",
  "webhookTimestamp": 1714809600000,
  "data": {
    "id": "<issue-uuid>",
    "identifier": "JTO-NNN",
    "title": "webhook-test-20260504",
    "description": "Real event trigger test for OPS-LINEAR-005",
    "url": "https://linear.app/jtoom/issue/JTO-NNN",
    "createdAt": "2026-05-04T00:00:00.000Z",
    "updatedAt": "2026-05-04T00:00:00.000Z",
    "teamId": "<team-uuid>",
    "team": {
      "id": "<team-uuid>",
      "name": "JTO",
      "key": "JTO"
    },
    "state": {
      "id": "<state-uuid>",
      "name": "Backlog"
    },
    "creator": {
      "id": "<user-uuid>",
      "name": "<user-name>",
      "email": "<user-email>"
    }
  }
}
```

### Issue Update

```json
{
  "action": "update",
  "type": "Issue",
  "organizationId": "<org-id>",
  "actorId": "<actor-id>",
  "userAgent": "Linear",
  "webhookTimestamp": 1714809660000,
  "data": {
    "id": "<issue-uuid>",
    "identifier": "JTO-NNN",
    "title": "webhook-test-20260504-updated",
    "description": "Real event trigger test for OPS-LINEAR-005 — updated",
    "url": "https://linear.app/jtoom/issue/JTO-NNN",
    "createdAt": "2026-05-04T00:00:00.000Z",
    "updatedAt": "2026-05-04T00:01:00.000Z",
    "teamId": "<team-uuid>",
    "state": {
      "id": "<state-uuid>",
      "name": "Backlog"
    }
  },
  "updatedFrom": {
    "title": "webhook-test-20260504"
  }
}
```

### Comment Create

```json
{
  "action": "create",
  "type": "Comment",
  "organizationId": "<org-id>",
  "actorId": "<actor-id>",
  "userAgent": "Linear",
  "webhookTimestamp": 1714809720000,
  "data": {
    "id": "<comment-uuid>",
    "body": "webhook trigger test comment — OPS-LINEAR-005",
    "url": "https://linear.app/jtoom/issue/JTO-NNN#comment-<comment-id>",
    "createdAt": "2026-05-04T00:02:00.000Z",
    "issue": {
      "id": "<issue-uuid>",
      "identifier": "JTO-NNN",
      "title": "webhook-test-20260504-updated",
      "url": "https://linear.app/jtoom/issue/JTO-NNN"
    },
    "user": {
      "id": "<user-uuid>",
      "name": "<user-name>",
      "email": "<user-email>"
    }
  }
}
```

### Issue Archive

```json
{
  "action": "archive",
  "type": "Issue",
  "organizationId": "<org-id>",
  "actorId": "<actor-id>",
  "userAgent": "Linear",
  "webhookTimestamp": 1714809780000,
  "data": {
    "id": "<issue-uuid>",
    "identifier": "JTO-NNN",
    "title": "webhook-test-20260504-updated",
    "url": "https://linear.app/jtoom/issue/JTO-NNN",
    "createdAt": "2026-05-04T00:00:00.000Z",
    "updatedAt": "2026-05-04T00:03:00.000Z",
    "teamId": "<team-uuid>",
    "archivedAt": "2026-05-04T00:03:00.000Z",
    "state": {
      "id": "<state-uuid>",
      "name": "Done"
    }
  }
}
```

---

## 六、请求 Headers 预期

Linear 发送的 webhook 请求包含以下 headers：

```
Content-Type: application/json
X-Linear-Signature: sha256=<hmac-sha256-hex>
User-Agent: Linear
X-Linear-Webhook-Id: <webhook-uuid>
```

> **签名计算**：`HMAC-SHA256(secret, raw_request_body)`，结果以 `sha256=` 前缀。
> **Adapter 兼容**：代码中 `verify()` 方法处理了 `sha256=` 前缀剥离，直接使用裸 hex 比对。

---

## 七、验证步骤

### 7.1 生产端验证（n8n）

```bash
# 1. 登录 n8n Web UI（通过 SSH 隧道）
ssh -L 5678:127.0.0.1:5678 root@node-22
# 浏览器打开 http://127.0.0.1:5678

# 2. 进入生产 workflow（接收 /webhook/events 的 workflow）
# 3. 查看 Executions 面板
# 4. 确认在执行序列后新增了 4 条 execution 记录：
#    - Issue/create
#    - Issue/update
#    - Comment/create
#    - Issue/archive
```

### 7.2 Shadow 端验证（Supabase SQL）

```bash
# 连接 Supabase（1Password: supabase-webhook数据库, id: mgh2gmvw5w3kmjfhrcieoxfb54）
psql "<SUPABASE_DB_URL>"
```

```sql
-- 验证最近 15 分钟的 shadow 事件
SELECT
    ce.event_id,
    ce.canonical_type,
    ce.canonical_action,
    ce.provider_event_type,
    ce.provider_action,
    ce.idempotency_key,
    ce.source_resource_id,
    ce.n8n_forwarded,
    ce.created_at
FROM webhook_canonical_events ce
WHERE ce.provider = 'linear'
  AND ce.created_at > NOW() - INTERVAL '15 minutes'
ORDER BY ce.created_at ASC;
```

**预期结果**：4 行记录，顺序为：

| canonical_type | canonical_action | n8n_forwarded |
|---------------|-----------------|---------------|
| issue | created | 0 |
| issue | updated | 0 |
| comment | created | 0 |
| issue | closed | 0 |

```sql
-- 验证 processing logs 完整性
SELECT
    phase,
    level,
    message,
    event_id,
    created_at
FROM webhook_processing_logs
WHERE provider = 'linear'
  AND created_at > NOW() - INTERVAL '15 minutes'
ORDER BY created_at ASC;
```

**预期**：每个事件至少包含 `signature → normalize → idempotency → store` 四阶段的日志。

### 7.3 端到端延迟验证

在每个步骤执行后，记录时间戳：

```bash
# 执行 Linear 操作时记录时间
date -u +%Y-%m-%dT%H:%M:%S.%3NZ

# 然后查询 Supabase
SELECT created_at FROM webhook_canonical_events
WHERE provider = 'linear'
ORDER BY created_at DESC LIMIT 1;
```

计算差值，验证 < 5 秒（P0-LIN-04 要求）。

---

## 八、清理步骤

### 8.1 Linear 侧清理

新 Issue 已在 Step 4 中 archived，**无需额外操作**。

如果需要彻底删除（而非 archive）：

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

> **注意**：`issueDelete` 会产生额外的 `Issue/delete` webhook 事件，adapter 中 `action_map` 包含 `"delete": "deleted"`。如果执行删除，会产生第 5 条事件。建议仅 archive 即可。

### 8.2 测试数据保留

Supabase 中的测试记录**保留用于审计**，不做清理。通过 `idempotency_key` 或 `source_resource_id` 可识别测试事件。

### 8.3 n8n 侧清理

n8n 中的 execution 记录按现有 retention policy 自动清理（30 天），**无需手动清理**。

---

## 九、注意事项和风险

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| 执行期间 Linear webhook 异常 | 两个端点都收不到事件 | 操作前先 `curl -s https://webhook.exa.edu.kg/health` 确认服务正常 |
| 网络延迟导致事件乱序 | n8n execution 顺序可能不一致 | 步骤间等待 ≥ 5 秒 |
| Shadow mode 配置错误 | 可能转发到 n8n | 确认 `WEBHOOK_INGRESS_MODE=shadow` |
| 签名密钥不一致 | 401 拒绝 | 确认 shadow endpoint 使用与 Linear webhook 相同的 secret |
| Issue 创建失败 | 无 webhook 事件 | 检查 Linear API Token 权限和 team ID |
| Comment 创建不触发 webhook | Linear webhook 未订阅 Comment 类型 | 检查 Linear webhook 配置中的 `resourceTypes` |

### 关键检查项

在执行前确认：

1. ✅ Linear webhook 配置包含 `resourceTypes: ["Issue", "Comment"]`
2. ✅ Shadow server 运行正常：`curl -s https://webhook.exa.edu.kg/health` 返回 `{"status":"ok","mode":"shadow"}`
3. ✅ 生产 n8n workflow 处于 Active 状态
4. ✅ Supabase 数据库连接正常

---

## 十、完整执行时间线

```
T+00:00  — 检查基础设施（health check, n8n status, Supabase）
T+00:01  — Step 1: Create Issue（触发 Issue/create webhook）
T+00:05  — Step 2: Update Issue（触发 Issue/update webhook）
T+00:10  — Step 3: Add Comment（触发 Comment/create webhook）
T+00:15  — Step 4: Archive Issue（触发 Issue/archive webhook）
T+00:20  — 验证生产端（n8n Executions）
T+00:25  — 验证 Shadow 端（Supabase SQL）
T+00:30  — 完成，记录测试结果
```

---

## 十一、与其他文档的关系

| 本文档 | 关联文档 | 关系说明 |
|--------|----------|----------|
| OPS-LINEAR-005 触发方案 | OPS-LINEAR-002 验收清单 | 本文档是 P0-LIN-01~04 的具体执行方案 |
| OPS-LINEAR-005 触发方案 | OPS-LINEAR-003 验收测试 | OPS-LINEAR-003 使用模拟 payload，本文档使用真实 Linear 事件 |
| OPS-LINEAR-005 触发方案 | OPS-LINEAR-004 部署记录 | 依赖已部署的 shadow endpoint |
| OPS-LINEAR-005 触发方案 | SEC-ARCH-001 安全架构 | 遵循签名校验和暴露面收敛原则 |

---

**文档状态**：草稿中  
**审批人**：待定  
**下次评审日期**：待定
