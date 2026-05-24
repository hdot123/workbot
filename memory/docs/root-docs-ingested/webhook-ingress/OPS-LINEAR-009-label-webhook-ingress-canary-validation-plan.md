# OPS-LINEAR-009 Label-Based Canary Validation Plan

> 文档编号：OPS-LINEAR-009  
> 版本：V1.0  
> 创建日期：2026-05-04  
> 维护人：bailian-worker

---

## 一、目标

验证 **label `webhook-ingress-canary`** 作为 canary test-issue 识别 guard 的完整闭环。

**核心场景**：
1. 带 label `webhook-ingress-canary` 的 issue 执行 update → ingress 命中 canary comment → 恰好 1 条 canary comment
2. 不带 label 的 issue 执行 update → 不产生 canary comment
3. 对同一 delivery ID 重放 → 不产生第二条 canary comment（幂等）
4. Archive 测试 issue 清理

**约束**：READ-ONLY plan。不执行 Linear API 调用。仅提供可执行的 GraphQL 模板和操作序列。

---

## 二、前置条件

| 条件 | 状态 |
|------|------|
| production_canary ingress 模式已运行 | ✅（OPS-LINEAR-007）|
| 公网入口 `POST /webhook/events` 活跃 | ✅ |
| `production-canary-events` n8n workflow active | ✅ |
| Supabase `webhook_canonical_events` / `webhook_processing_logs` 可查询 | ✅ |
| Linear API Token 可用 | 需执行前确认 |
| JTO team ID 已知 | 需执行前确认 |
| Canary comment action 在 ingress 中已实现但 disabled | ✅（`LINEAR_CANARY_COMMENT_ENABLED`）|
| Label `webhook-ingress-canary` 已创建 | 本次验证需先创建 |

### 2.1 Canary 识别机制

当前 ingress `_is_linear_test_issue_update()` 采用 OR 逻辑：

```
识别为 test issue update（任一条件满足即可）：
  条件 A：title 包含 "[webhook-ingress-canary]"
  条件 B：identifier 在 canary_allowed_identifiers 列表中
  条件 C：labels 中包含 "webhook-ingress-canary"（字符串匹配）
```

本次验证聚焦 **条件 C（label guard）**：

- 验证 label 作为唯一识别手段（不带 title prefix 的 issue + 带 label → 应触发）
- 验证无 label 的 issue → 不触发

---

## 三、GraphQL 模板汇总

### 通用请求格式

```
POST https://api.linear.app/graphql
Authorization: lin_api_<TOKEN>
Content-Type: application/json
```

> 所有 mutation 中的 `<TOKEN>` 为 Linear API token 占位符，`<JTO_TEAM_ID>` 为团队 UUID 占位符。

---

### A. Label 操作

#### A1. 查询现有 Labels

确认 `webhook-ingress-canary` label 是否已存在：

```graphql
query GetTeamLabels($teamId: String!) {
  team(id: $teamId) {
    id
    key
    labels {
      nodes {
        id
        name
        color
        description
      }
    }
  }
}
```

#### A2. 创建 Label（如不存在）

```graphql
mutation CreateCanaryLabel {
  issueLabelCreate(
    input: {
      teamId: "<JTO_TEAM_ID>",
      name: "webhook-ingress-canary",
      color: "#f59e0b",
      description: "Issue is in scope for webhook ingress canary comment validation (OPS-LINEAR-009)"
    }
  ) {
    success
    issueLabel {
      id
      name
      color
    }
  }
}
```

#### A3. 给 Issue 附加 Label

```graphql
mutation AttachCanaryLabel($issueId: String!, $labelId: String!) {
  issueUpdate(
    id: $issueId,
    input: {
      labelIds: ["$labelId"]
    }
  ) {
    success
    issue {
      id
      identifier
      labels {
        nodes {
          id
          name
        }
      }
    }
  }
}
```

> **注意**：`labelIds` 是覆盖式设置，如需保留已有 labels 需一并传入。

---

### B. Issue 操作

#### B1. 创建带 Label 的测试 Issue

```graphql
mutation CreateLabeledCanaryIssue {
  issueCreate(
    input: {
      teamId: "<JTO_TEAM_ID>",
      title: "ops-linear-009-labeled-canary-test-YYYYMMDD",
      description: "OPS-LINEAR-009: label-based canary validation — this issue has the webhook-ingress-canary label but NO title prefix"
      labelIds: ["<CANARY_LABEL_ID>"]
    }
  ) {
    success
    issue {
      id
      identifier
      url
      title
      labels {
        nodes {
          id
          name
        }
      }
    }
  }
}
```

#### B2. 创建不带 Label 的对照 Issue

```graphql
mutation CreateUnlabeledControlIssue {
  issueCreate(
    input: {
      teamId: "<JTO_TEAM_ID>",
      title: "ops-linear-009-unlabeled-control-YYYYMMDD",
      description: "OPS-LINEAR-009: control issue — NO webhook-ingress-canary label, should NOT trigger canary comment"
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

#### B3. Issue Update — 触发 canary comment

```graphql
mutation UpdateLabeledIssue($issueId: String!) {
  issueUpdate(
    id: $issueId,
    input: {
      description: "ops-linear-009-labeled-canary-test-YYYYMMDD — update to trigger canary comment via label guard"
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

#### B4. Issue Update — 对照（不触发 canary comment）

```graphql
mutation UpdateUnlabeledIssue($issueId: String!) {
  issueUpdate(
    id: $issueId,
    input: {
      description: "ops-linear-009-unlabeled-control — update, should NOT trigger canary comment"
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

#### B5. Archive Issue

```graphql
mutation ArchiveIssue($issueId: String!) {
  issueArchive(id: $issueId) {
    success
  }
}
```

---

### C. Comment 查询

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

---

### D. Issue 状态验证

```graphql
query VerifyIssueArchived($issueId: String!) {
  issue(id: $issueId) {
    id
    identifier
    archivedAt
    state {
      name
    }
    labels {
      nodes {
        id
        name
      }
    }
  }
}
```

---

### E. Label 删除（清理）

```graphql
mutation DeleteCanaryLabel($labelId: String!) {
  issueLabelDelete(id: $labelId) {
    success
  }
}
```

---

## 四、完整操作序列

### Phase 1 — 基础设施确认（T+00:00）

```bash
# 1. Health check
curl -s https://webhook.exa.edu.kg/health
# 预期：{"status":"ok","mode":"production_canary"}

# 2. 确认 Linear API token 有效（用 teams query 验证）
# POST https://api.linear.app/graphql
# Authorization: lin_api_<TOKEN>
# {"query": "query { teams { nodes { id key name } } }"}
# 预期：返回包含 JTO team 的结果

# 3. 确认 canary comment 已关闭
# 检查环境变量 LINEAR_CANARY_COMMENT_ENABLED 未设置或为 false

# 4. 确认 label webhook-ingress-canary 存在
# 执行 A1 查询，如不存在则执行 A2 创建
```

### Phase 2 — 创建测试 Issue（T+00:02）

| 步骤 | 操作 | 目标 |
|------|------|------|
| 2a | 执行 B1 `CreateLabeledCanaryIssue` | 带 label 的测试 issue |
| 2b | 执行 B2 `CreateUnlabeledControlIssue` | 不带 label 的对照 issue |
| 记录 | 两个 issue 的 `id` 和 `identifier` | 后续操作使用 |

**变量记录**：
- `LABELED_ISSUE_ID` = Phase 2a 返回的 `issue.id`
- `LABELED_ISSUE_KEY` = Phase 2a 返回的 `issue.identifier`（如 JTO-NNN）
- `UNLABELED_ISSUE_ID` = Phase 2b 返回的 `issue.id`
- `UNLABELED_ISSUE_KEY` = Phase 2b 返回的 `issue.identifier`（如 JTO-NNN）
- `CANARY_LABEL_ID` = Phase 1 中 label 的 `id`

### Phase 3 — 触发 Labeled Issue Update（T+00:05）

**操作**：执行 B3 `UpdateLabeledIssue`

**预期事件流**：

```
Linear Issue/update webhook
    ↓
POST /webhook/events (公网入口)
    ↓
signature verify → normalize → idempotency check
    ↓
store in Supabase (webhook_raw_events + webhook_canonical_events)
    ↓
forward to n8n (production-canary-events webhook URL)
    ↓
canary check: route_mode == production_canary ✓
canary check: canary_comment_enabled == true ✓（本次验证前开启）
canary check: _is_linear_test_issue_update()
    → canonical_type == "issue" ✓
    → canonical_action == "updated" ✓
    → title 包含 "[webhook-ingress-canary]"？ NO（标题无前缀）
    → labels 包含 "webhook-ingress-canary"？ YES → PASS
    ↓
canary_commenter → commentCreate mutation → canary comment 出现
```

**Wait time**：更新后等待 **30 秒**。

### Phase 4 — 验证 Labeled Issue Canary Comment（T+00:35）

**操作**：执行 C `GetIssueComments($issueId=LABELED_ISSUE_ID)`

**验证条件**：
- `comments.nodes.length >= 1`
- 至少一条 comment 的 `body` 以 `[webhook-ingress-canary]` 开头
- 记录该 canary comment 的 `id`

**Supabase 验证**：

```sql
SELECT
    ce.event_id,
    ce.canonical_type,
    ce.canonical_action,
    ce.n8n_forwarded,
    ce.created_at
FROM webhook_canonical_events ce
WHERE ce.provider = 'linear'
  AND ce.created_at > NOW() - INTERVAL '5 minutes'
ORDER BY ce.created_at ASC;
```

**预期**：至少 2 行（issue/created + issue/updated，均 `n8n_forwarded=1`）

### Phase 5 — 验证 Unlabeled Issue 不触发（T+00:40）

**操作 A**：执行 B4 `UpdateUnlabeledIssue`

**Wait time**：等待 **30 秒**。

**操作 B**：执行 C `GetIssueComments($issueId=UNLABELED_ISSUE_ID)`

**验证条件**：
- `comments.nodes` 中 **不存在** body 以 `[webhook-ingress-canary]` 开头的 comment
- （可能有其他用户 comment，但无 canary comment）

**Supabase 验证**：

```sql
SELECT
    ce.event_id,
    ce.canonical_type,
    ce.canonical_action,
    ce.n8n_forwarded,
    ce.created_at
FROM webhook_canonical_events ce
WHERE ce.provider = 'linear'
  AND ce.created_at > NOW() - INTERVAL '5 minutes'
  AND ce.source_resource_id = '<UNLABELED_ISSUE_KEY>'
ORDER BY ce.created_at ASC;
```

**预期**：2 行（issue/created + issue/updated），但 processing logs 中 canary_action phase 应为 `skipped` with `reason: not_test_issue_update`。

### Phase 6 — 幂等重放验证（T+01:00）

**操作 A**：从 Supabase 获取 Phase 3 的原始 delivery ID 和 payload

```sql
SELECT ce.delivery_id, re.raw_body
FROM webhook_canonical_events ce
JOIN webhook_raw_events re ON re.canonical_event_id = ce.event_id
WHERE ce.canonical_type = 'issue'
  AND ce.canonical_action = 'updated'
  AND ce.source_resource_id = '<LABELED_ISSUE_KEY>'
ORDER BY ce.created_at DESC
LIMIT 1;
```

**操作 B**：用相同 delivery ID 重放请求

```bash
curl -s -X POST https://webhook.exa.edu.kg/webhook/events \
  -H "Content-Type: application/json" \
  -H "Linear-Delivery: <delivery-id-from-phase-3>" \
  -H "X-Linear-Signature: sha256=<signature>" \
  -d '<original-payload-from-phase-3>'
```

**验证**：
- 响应 `status = "duplicate_accepted"`
- 不触发 canary comment（因为 ingress idempotency check 在 canary 之前）

**操作 C**：执行 C `GetIssueComments($issueId=LABELED_ISSUE_ID)` 验证 comment 数量不变

**Supabase 验证**：

```sql
SELECT
    ce.canonical_type,
    ce.canonical_action,
    COUNT(*) as event_count
FROM webhook_canonical_events ce
WHERE ce.provider = 'linear'
  AND ce.created_at > NOW() - INTERVAL '10 minutes'
  AND ce.source_resource_id = '<LABELED_ISSUE_KEY>'
GROUP BY ce.canonical_type, ce.canonical_action;
```

**预期**：`issue/updated` 的 `event_count = 1`（幂等阻止重复）

### Phase 7 — 关闭 Canary Action（T+01:10）

```bash
# 设置 LINEAR_CANARY_COMMENT_ENABLED=false 或取消环境变量
# 确认 ingress mode 仍然是 production_canary
curl -s https://webhook.exa.edu.kg/health
```

### Phase 8 — 清理归档（T+01:15）

**操作 A**：Archive 两个测试 Issue

```graphql
mutation ArchiveBothIssues {
  archiveLabeled: issueArchive(id: "<LABELED_ISSUE_ID>") { success }
  archiveUnlabeled: issueArchive(id: "<UNLABELED_ISSUE_ID>") { success }
}
```

**操作 B**：验证归档

```graphql
query VerifyBothArchived {
  labeled: issue(id: "<LABELED_ISSUE_ID>") {
    id identifier archivedAt
  }
  unlabeled: issue(id: "<UNLABELED_ISSUE_ID>") {
    id identifier archivedAt
  }
}
```

**预期**：两个 issue 的 `archivedAt` 均不为 null。

**操作 C**：可选 — 删除 label（如果不再需要）

```graphql
mutation DeleteCanaryLabel {
  issueLabelDelete(id: "<CANARY_LABEL_ID>") { success }
}
```

---

## 五、完整时间线

```
T+00:00  — Phase 1: 基础设施确认 + label 确认/创建
T+00:02  — Phase 2: 创建 labeled + unlabeled 两个测试 issue
T+00:05  — Phase 3: labeled issue update → 触发 canary comment
T+00:35  — Phase 4: 验证 labeled issue 上有 1 条 canary comment
T+00:40  — Phase 5: unlabeled issue update → 不触发 canary comment
T+01:10  — Phase 5: 验证 unlabeled issue 上无 canary comment
T+01:20  — Phase 6: 重放 labeled issue 的 delivery ID
T+01:25  — Phase 6: 验证 comment 数量不变 + Supabase count 不变
T+01:30  — Phase 7: 关闭 canary action
T+01:35  — Phase 8: Archive 两个测试 issue
T+01:40  — Phase 8: 归档验证 + 可选 label 删除
T+01:45  — 整理证据，撰写验证报告
```

---

## 六、证据收集清单

| 序号 | 证据项 | 收集方式 |
|------|--------|----------|
| E1 | Health check 输出 | `curl` 结果 |
| E2 | Label 创建确认 | A2 mutation 返回值 |
| E3 | Labeled issue 创建确认 | B1 mutation 返回值 |
| E4 | Unlabeled issue 创建确认 | B2 mutation 返回值 |
| E5 | Labeled issue update 后 canary comment 存在 | C query 结果 |
| E6 | Unlabeled issue update 后无 canary comment | C query 结果 |
| E7 | 重放响应 `duplicate_accepted` | `curl` 结果 |
| E8 | 重放后 canary comment 数量不变 | C query 结果 |
| E9 | Supabase canonical events（含 labeled + unlabeled） | SQL 查询结果 |
| E10 | Supabase 幂等计数验证 | SQL 计数结果 |
| E11 | Canary action 关闭确认 | 配置确认 |
| E12 | 两个 issue 均 archived | D query 结果 |

---

## 七、验收标准

| 编号 | 标准 | 判定 |
|------|------|------|
| P0-LBL-01 | Label `webhook-ingress-canary` 已创建 | A2 mutation success |
| P0-LBL-02 | Labeled issue update 触发 canary comment | C query 找到 `[webhook-ingress-canary]` 开头的 comment |
| P0-LBL-03 | 恰好 1 条 canary comment 在 labeled issue 上 | comment count = 1 |
| P0-LBL-04 | Unlabeled issue update 不触发 canary comment | C query 无 `[webhook-ingress-canary]` 开头的 comment |
| P0-LBL-05 | 重放返回 `duplicate_accepted` | HTTP response |
| P0-LBL-06 | 重放后 canary comment 数量不变 | C query 对比 |
| P0-LBL-07 | 重放后 Supabase canonical event count 不变 | SQL 计数 |
| P0-LBL-08 | 两个测试 issue 均 archived | D query 验证 `archivedAt != null` |
| P0-LBL-09 | Canary action 已关闭 | 环境变量确认 |

---

## 八、与 ingress 代码逻辑的对应关系

| 验证项 | 代码位置 | 测试场景 |
|--------|----------|----------|
| Label 识别 | `ingress.py:_is_linear_test_issue_update()` line ~155 | Phase 3 + Phase 4 |
| Title 不匹配 → fallback to labels | `ingress.py` line ~149-155 | Phase 3（标题无前缀，依赖 label） |
| 无 label → skipped | `ingress.py` line ~155 返回 False | Phase 5（无 label + 无 title prefix） |
| Idempotency check 在 canary 之前 | `ingress.py:handle()` line ~70-78 | Phase 6（重放返回 duplicate_accepted） |
| Canary commenter protocol | `server.py:_make_linear_canary_commenter()` | Phase 3 触发 commentCreate |
| Canary comment body 格式 | `server.py:_linear_comment_body()` | Phase 4 验证 body 以 `[webhook-ingress-canary]` 开头 |

---

## 九、风险与缓解

| 风险 | 影响 | 缓解 |
|------|------|------|
| **[BLOCKER] adapter 不传递 labels** | label check 永远返回 False | 必须先修复 adapter.py，在 canonical payload 中添加 labels |
| Label 名称匹配大小写 | labels 比较用 `.lower()` 可匹配 | ingress 已做 `str(label).lower() == "webhook-ingress-canary"` |
| Label payload 结构未知 | Linear webhook payload 中 labels 可能是 `[{"name":"..."}]` 或 `["name"]` | 需要在实际 webhook payload 中确认 labels 字段格式 |
| Unlabeled issue 也触发 canary | 说明 title 匹配逻辑有误 | 检查 title 中是否意外包含 `[webhook-ingress-canary]` |
| Canary comment 延迟 > 30s | 验证时 comment 未到 | 延长 wait 到 60s |
| 重放签名无效 | ingress 401 拒绝 | 使用 ingress idempotency path（delivery ID 已存在）确认 |

---

## 十、注意事项

### 10.1 [BLOCKER] Adapter 不传递 labels 到 canonical payload

**问题**：`adapter.py:normalize()` 构建 canonical payload 时，仅包含 `id`、`identifier`、`title`、`description`、`state`、`url`、`metadata`，**未包含 `labels` 字段**。

```python
# adapter.py canonical payload 构建
"payload": {
    "id": data.get("id"),
    "identifier": data.get("identifier"),
    "title": data.get("title") or data.get("name"),
    "description": data.get("description"),
    "state": ...,
    "url": data.get("url"),
    "metadata": {...},
    # ❌ labels 字段缺失
}
```

但 `ingress.py:_is_linear_test_issue_update()` 从 canonical payload 中读取 labels：

```python
labels = payload.get("labels") if isinstance(payload.get("labels"), list) else []
return any(str(label).lower() == "webhook-ingress-canary" for label in labels)
```

**结果**：无论 Linear webhook payload 中是否包含 labels，canonical payload 中 `labels` 永远为 `None` → 转为空列表 `[]` → label check **永远返回 False**。

**修复方案**：修改 `adapter.py:normalize()` 在 payload 中添加 labels 字段：

```python
# adapter.py normalize() 方法中，payload dict 添加：
"labels": [
    lbl.get("name") if isinstance(lbl, dict) else str(lbl)
    for lbl in (data.get("labels") or [])
],
```

或在 `ingress.py` 中改用其他方式（如 title prefix 或 metadata 中的标识符列表）作为 test issue 识别手段。

**本次 plan 为 READ-ONLY**，不执行代码修改。执行前必须先解决此 blocker。

### 10.2 Label Payload 格式不确定性

**问题**：当前 ingress 代码中的 label 检查：

```python
labels = payload.get("labels") if isinstance(payload.get("labels"), list) else []
return any(str(label).lower() == "webhook-ingress-canary" for label in labels)
```

该代码期望 `labels` 是一个列表，且每个元素转字符串后等于 `"webhook-ingress-canary"`。即使 10.1 blocker 修复后，Linear webhook payload 中 `data.labels` 字段的实际格式可能是：

- `["webhook-ingress-canary"]`（字符串列表）→ ✅ 当前代码匹配
- `[{"id": "...", "name": "webhook-ingress-canary"}]`（对象列表）→ 需要提取 `.name` 字段

**验证前必须确认**：检查 OPS-LINEAR-005 或 OPS-LINEAR-007 中实际 webhook payload 的 `data.labels` 字段格式。如果格式是对象列表，adapter 修复时需提取 `.name` 值。

### 10.3 Label 附加方式

在 GraphQL 中通过 `labelIds` 附加 label 后，Linear webhook 发出的 Issue/update 事件 payload 中是否包含更新后的 labels 信息取决于 Linear 的 webhook payload 结构。如果 labels 信息不在 issue update payload 中，则需要：

- 方案 A：修改 ingress 代码，通过 Linear API 查询 issue 的当前 labels
- 方案 B：确认 Linear issue update webhook payload 确实包含 labels 字段

### 10.4 Token 安全

所有模板中使用 `lin_api_<TOKEN>` 占位符，执行时通过环境变量注入：

```bash
export LINEAR_API_TOKEN="lin_api_xxxxxxxx"
```

Token 不写入任何持久化文件或文档中。

---

## 十一、与其他文档的关系

| 本文档 | 关联文档 | 关系说明 |
|--------|----------|----------|
| OPS-LINEAR-009 验证方案 | OPS-LINEAR-008 canary validation | 复用相同 canary comment 验证模式，但识别机制从 title 改为 label |
| OPS-LINEAR-009 验证方案 | OPS-LINEAR-005 shadow validation | 复用 Linear GraphQL mutation 模式和 Supabase 查询模式 |
| OPS-LINEAR-009 验证方案 | OPS-LINEAR-006 minimal trigger | 复用事件触发和验证时间线模式 |
| OPS-LINEAR-009 验证方案 | SEC-ARCH-001 | 遵循签名校验和暴露面收敛原则 |

---

**文档状态**：草稿中  
**审批人**：待定
