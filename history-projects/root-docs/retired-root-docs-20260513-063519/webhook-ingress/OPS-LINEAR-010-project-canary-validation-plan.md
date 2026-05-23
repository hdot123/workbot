# OPS-LINEAR-010 Project-Based Canary Validation Plan

> 文档编号：OPS-LINEAR-010  
> 版本：V1.0  
> 创建日期：2026-05-04  
> 维护人：bailian-worker

---

## 一、目标

验证 **Project membership** 作为 canary test-issue 识别 guard 的完整闭环。

**核心场景**：
1. 在 **Webhook Ingress Canary Project** 中创建 issue → 执行 update → 恰好 1 条 canary comment
2. 在 **其他项目**（或无 project 的 team-level issue）中创建相同标题/标签的 issue → 执行 update → **不产生** canary comment
3. 对同一 delivery ID 重放 → 不产生第二条 canary comment（幂等）
4. Archive 测试 issue + 清理 canary project

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
| Canary project 已创建 | 本次验证需先创建/选定 |

### 2.1 Canary 识别机制（Project Guard）

本次验证聚焦 **project membership** 作为唯一识别手段：

```
识别为 test issue update（条件）：
  条件 A：canonical payload 中包含 projectId
  条件 B：projectId == "<CANARY_PROJECT_ID>"
```

- 验证 project 内的 issue → 应触发 canary comment
- 验证 project 外的 issue → 不应触发 canary comment（即使标题/标签与 008/009 的测试 issue 相同）
- 这是最粗粒度的隔离方式：整个 project 是 canary scope，project 外一律忽略

### 2.2 与 OPS-LINEAR-008/009 的对比

| 方案 | 识别维度 | 粒度 | 优点 | 缺点 |
|------|----------|------|------|------|
| OPS-LINEAR-008 | Title prefix `[canary-ops-008]` | 单个 issue | 精确控制 | 需要修改标题 |
| OPS-LINEAR-009 | Label `webhook-ingress-canary` | 单个 issue | 不修改标题 | adapter 需传递 labels |
| **OPS-LINEAR-010** | **Project membership** | **整个 project** | **最干净隔离，无需 title/label 修饰** | **需要专用 project，粒度较粗** |

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

### A. Project 操作

#### A1. 查询现有 Projects

确认 `Webhook Ingress Canary` project 是否已存在：

```graphql
query GetTeamProjects($teamId: String!) {
  team(id: $teamId) {
    id
    key
    projects {
      nodes {
        id
        name
        description
        state
        createdAt
      }
    }
  }
}
```

**筛选条件**：`name` 包含 `Webhook Ingress Canary` 或 `canary`

#### A2. 创建 Canary Project（如不存在）

```graphql
mutation CreateCanaryProject {
  projectCreate(
    input: {
      teamIds: ["<JTO_TEAM_ID>"],
      name: "Webhook Ingress Canary",
      description: "Dedicated project for webhook ingress canary comment validation (OPS-LINEAR-010). All issues in this project are in scope for canary testing.",
      state: started,
      leadId: null
    }
  ) {
    success
    project {
      id
      name
      url
      state
    }
  }
}
```

**记录返回值**：
- `project.id` → `<CANARY_PROJECT_ID>`（用于后续 issue 创建）
- `project.url`（用于 UI 验证）

#### A3. 查询 Project 详细信息

确认 project 创建成功且处于活跃状态：

```graphql
query GetCanaryProject($projectId: String!) {
  project(id: $projectId) {
    id
    name
    description
    state
    teamIds
    createdAt
    issues {
      nodes {
        id
        identifier
        title
        state { name }
      }
    }
  }
}
```

---

### B. Issue 操作

#### B1. 创建在 Canary Project 中的测试 Issue

```graphql
mutation CreateProjectScopedCanaryIssue {
  issueCreate(
    input: {
      teamId: "<JTO_TEAM_ID>",
      title: "ops-linear-010-project-canary-test-YYYYMMDD-HHMM",
      description: "OPS-LINEAR-010: project-based canary validation — this issue IS in the Webhook Ingress Canary project and SHOULD trigger canary comment on update",
      projectId: "<CANARY_PROJECT_ID>"
    }
  ) {
    success
    issue {
      id
      identifier
      url
      title
      project {
        id
        name
      }
    }
  }
}
```

**记录返回值**：
- `issue.id` → `PROJECT_ISSUE_ID`
- `issue.identifier` → 如 `JTO-NNN`

#### B2. 创建在 Project 外的对照 Issue

```graphql
mutation CreateOutOfProjectControlIssue {
  issueCreate(
    input: {
      teamId: "<JTO_TEAM_ID>",
      title: "ops-linear-010-project-canary-test-YYYYMMDD-HHMM",
      description: "OPS-LINEAR-010: control issue — NOT in the Webhook Ingress Canary project, should NOT trigger canary comment even with same title"
    }
  ) {
    success
    issue {
      id
      identifier
      url
      title
      project {
        id
        name
      }
    }
  }
}
```

**记录返回值**：
- `issue.id` → `CONTROL_ISSUE_ID`
- `issue.identifier` → 如 `JTO-NNN`
- **注意**：该 issue 的 `project` 应为 `null`（不属于任何 project）

#### B3. Issue Update — 触发 canary comment（project 内 issue）

```graphql
mutation UpdateProjectScopedIssue($issueId: String!) {
  issueUpdate(
    id: $issueId,
    input: {
      description: "ops-linear-010-project-scoped-canary-test-YYYYMMDD — update to trigger canary comment via project guard"
    }
  ) {
    success
    issue {
      id
      identifier
      updatedAt
      project {
        id
        name
      }
    }
  }
}
```

#### B4. Issue Update — 对照（project 外 issue，不触发 canary comment）

```graphql
mutation UpdateOutOfProjectIssue($issueId: String!) {
  issueUpdate(
    id: $issueId,
    input: {
      description: "ops-linear-010-out-of-project-control — update, should NOT trigger canary comment"
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
    project {
      id
      name
    }
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
    project {
      id
      name
    }
    state {
      name
    }
  }
}
```

---

### E. Project 清理

#### E1. 归档 Canary Project

```graphql
mutation ArchiveCanaryProject($projectId: String!) {
  projectArchive(id: $projectId) {
    success
  }
}
```

#### E2. 验证 Project 归档

```graphql
query VerifyProjectArchived($projectId: String!) {
  project(id: $projectId) {
    id
    name
    archivedAt
    state
  }
}
```

**预期**：`archivedAt` 不为 null，`state` 为 `archived` 或 equivalent。

---

## 四、完整操作序列

### Phase 1 — 基础设施确认（T+00:00）

```bash
# 1. Health check
curl -s https://webhook.exa.edu.kg/health
# 预期：{"status":"ok","mode":"production_canary"}

# 2. 确认 Linear API token 有效
# POST https://api.linear.app/graphql
# {"query": "query { teams { nodes { id key name } } }"}
# 预期：返回包含 JTO team 的结果

# 3. 确认 canary comment 已关闭
# 检查环境变量 LINEAR_CANARY_COMMENT_ENABLED 未设置或为 false

# 4. 确认/创建 canary project
# 执行 A1 查询现有 projects
# 如不存在 `Webhook Ingress Canary`，执行 A2 创建
# 记录 <CANARY_PROJECT_ID>
```

### Phase 2 — 创建测试 Issue（T+00:02）

| 步骤 | 操作 | 目标 |
|------|------|------|
| 2a | 执行 B1 `CreateProjectScopedCanaryIssue` | 在 canary project 中的测试 issue |
| 2b | 执行 B2 `CreateOutOfProjectControlIssue` | 不在 canary project 中的对照 issue |
| 记录 | 两个 issue 的 `id`、`identifier`、`project` | 后续操作使用 |

**变量记录**：
- `PROJECT_ISSUE_ID` = Phase 2a 返回的 `issue.id`
- `PROJECT_ISSUE_KEY` = Phase 2a 返回的 `issue.identifier`（如 JTO-NNN）
- `CONTROL_ISSUE_ID` = Phase 2b 返回的 `issue.id`
- `CONTROL_ISSUE_KEY` = Phase 2b 返回的 `issue.identifier`（如 JTO-NNN）
- `<CANARY_PROJECT_ID>` = Phase 1 中 project 的 `id`

### Phase 3 — 触发 Project 内 Issue Update（T+00:05）

**操作**：执行 B3 `UpdateProjectScopedIssue($issueId=PROJECT_ISSUE_ID)`

**预期事件流**：

```
Linear Issue/update webhook (issue in Webhook Ingress Canary project)
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
    → projectId 匹配 <CANARY_PROJECT_ID>？ YES → PASS
    ↓
canary_commenter → commentCreate mutation → canary comment 出现
```

**Wait time**：更新后等待 **30 秒**。

### Phase 4 — 验证 Project 内 Issue Canary Comment（T+00:35）

**操作**：执行 C `GetIssueComments($issueId=PROJECT_ISSUE_ID)`

**验证条件**：
- `comments.nodes.length >= 1`
- 至少一条 comment 的 `body` 以 `[webhook-ingress-canary]` 开头
- `issue.project.id == "<CANARY_PROJECT_ID>"` 确认 issue 在 canary project 中
- 记录该 canary comment 的 `id` 和 `createdAt`

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
  AND ce.source_resource_id = '<PROJECT_ISSUE_KEY>'
ORDER BY ce.created_at ASC;
```

**预期**：至少 2 行（issue/created + issue/updated，均 `n8n_forwarded=1`）

### Phase 5 — 验证 Project 外 Issue 不触发（T+00:40）

**操作 A**：执行 B4 `UpdateOutOfProjectIssue($issueId=CONTROL_ISSUE_ID)`

**Wait time**：等待 **30 秒**。

**操作 B**：执行 C `GetIssueComments($issueId=CONTROL_ISSUE_ID)`

**验证条件**：
- `comments.nodes` 中 **不存在** body 以 `[webhook-ingress-canary]` 开头的 comment
- `issue.project` 为 `null`（确认不在任何 project 中）
- （可能有其他用户 comment，但无 canary comment）

**关键验证**：即使该 issue 的 title 与 project 内测试 issue 相同（Phase 2 中使用了相同标题模板），但因为不在 canary project 中，不应触发 canary comment。这证明了 project guard 的隔离效果优于 title/label guard。

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
  AND ce.source_resource_id = '<CONTROL_ISSUE_KEY>'
ORDER BY ce.created_at ASC;
```

**预期**：2 行（issue/created + issue/updated），但 processing logs 中 canary_action phase 应为 `skipped` with `reason: not_test_issue_update` 或 `reason: project_not_in_canary_scope`。

### Phase 6 — 额外验证：Project 内 + 带 canary label 的 issue（T+00:50）

**目的**：验证 project guard 与 label guard 的兼容性。如果 ingress 使用 OR 逻辑（任一条件满足即可），则：
- project 内 + 带 label → 触发 canary comment（project guard 已满足）
- project 外 + 带 label → 触发 canary comment（label guard 满足）

**如果 ingress 使用 AND 逻辑**（所有条件都需满足），则：
- project 内 + 带 label → 触发 canary comment
- project 外 + 带 label → **不**触发

**操作**：可选。取决于实际 ingress 中 `_is_linear_test_issue_update()` 的逻辑定义。

> 本次 plan 假设 project guard 是**独立且充分**的条件，不依赖 label 或 title。

### Phase 7 — 幂等重放验证（T+01:00）

**操作 A**：从 Supabase 获取 Phase 3 的原始 delivery ID 和 payload

```sql
SELECT ce.delivery_id, re.raw_body
FROM webhook_canonical_events ce
JOIN webhook_raw_events re ON re.canonical_event_id = ce.event_id
WHERE ce.canonical_type = 'issue'
  AND ce.canonical_action = 'updated'
  AND ce.source_resource_id = '<PROJECT_ISSUE_KEY>'
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

**操作 C**：执行 C `GetIssueComments($issueId=PROJECT_ISSUE_ID)` 验证 comment 数量不变

**Supabase 验证**：

```sql
SELECT
    ce.canonical_type,
    ce.canonical_action,
    COUNT(*) as event_count
FROM webhook_canonical_events ce
WHERE ce.provider = 'linear'
  AND ce.created_at > NOW() - INTERVAL '10 minutes'
  AND ce.source_resource_id = '<PROJECT_ISSUE_KEY>'
GROUP BY ce.canonical_type, ce.canonical_action;
```

**预期**：`issue/updated` 的 `event_count = 1`（幂等阻止重复）

### Phase 8 — 关闭 Canary Action（T+01:10）

```bash
# 设置 LINEAR_CANARY_COMMENT_ENABLED=false 或取消环境变量
# 确认 ingress mode 仍然是 production_canary
curl -s https://webhook.exa.edu.kg/health
```

### Phase 9 — 清理归档（T+01:15）

#### 9.1 Archive 两个测试 Issue

```graphql
mutation ArchiveBothIssues {
  archiveProjectIssue: issueArchive(id: "<PROJECT_ISSUE_ID>") { success }
  archiveControlIssue: issueArchive(id: "<CONTROL_ISSUE_ID>") { success }
}
```

#### 9.2 验证归档

```graphql
query VerifyBothArchived {
  projectIssue: issue(id: "<PROJECT_ISSUE_ID>") {
    id identifier archivedAt project { id name }
  }
  controlIssue: issue(id: "<CONTROL_ISSUE_ID>") {
    id identifier archivedAt project { id name }
  }
}
```

**预期**：两个 issue 的 `archivedAt` 均不为 null。

#### 9.3 归档 Canary Project

```graphql
mutation ArchiveCanaryProject($projectId: String!) {
  projectArchive(id: $projectId) { success }
}
```

#### 9.4 验证 Project 归档

```graphql
query VerifyProjectArchived($projectId: String!) {
  project(id: $projectId) {
    id
    name
    archivedAt
    state
  }
}
```

**预期**：`archivedAt != null`，`state` 表示已归档。

---

## 五、完整时间线

```
T+00:00  — Phase 1: 基础设施确认 + project 确认/创建
T+00:02  — Phase 2: 创建 project 内 + project 外 两个测试 issue
T+00:05  — Phase 3: project 内 issue update → 触发 canary comment
T+00:35  — Phase 4: 验证 project 内 issue 上有 1 条 canary comment
T+00:40  — Phase 5: project 外 issue update → 不触发 canary comment
T+01:10  — Phase 5: 验证 project 外 issue 上无 canary comment
T+01:20  — Phase 7: 重放 project 内 issue 的 delivery ID
T+01:25  — Phase 7: 验证 comment 数量不变 + Supabase count 不变
T+01:30  — Phase 8: 关闭 canary action
T+01:35  — Phase 9: Archive 两个测试 issue
T+01:40  — Phase 9: 归档验证 + archive canary project
T+01:45  — 整理证据，撰写验证报告
```

---

## 六、证据收集清单

| 序号 | 证据项 | 收集方式 |
|------|--------|----------|
| E1 | Health check 输出 | `curl` 结果 |
| E2 | Project 创建确认 | A2 mutation 返回值 |
| E3 | Project 内 issue 创建确认 | B1 mutation 返回值（含 `project.id`）|
| E4 | Project 外 issue 创建确认 | B2 mutation 返回值（`project` 为 null）|
| E5 | Project 内 issue update 后 canary comment 存在 | C query 结果 |
| E6 | Project 外 issue update 后无 canary comment | C query 结果 |
| E7 | 重放响应 `duplicate_accepted` | `curl` 结果 |
| E8 | 重放后 canary comment 数量不变 | C query 结果 |
| E9 | Supabase canonical events（含 project 内 + project 外） | SQL 查询结果 |
| E10 | Supabase 幂等计数验证 | SQL 计数结果 |
| E11 | Canary action 关闭确认 | 环境变量确认 |
| E12 | 两个 issue 均 archived | D query 结果 |
| E13 | Canary project archived | E2 query 结果 |

---

## 七、验收标准

| 编号 | 标准 | 判定 |
|------|------|------|
| P0-PRJ-01 | Canary project `Webhook Ingress Canary` 已创建 | A2 mutation success |
| P0-PRJ-02 | Project 内 issue update 触发 canary comment | C query 找到 `[webhook-ingress-canary]` 开头的 comment |
| P0-PRJ-03 | 恰好 1 条 canary comment 在 project 内 issue 上 | comment count = 1 |
| P0-PRJ-04 | Project 外 issue update 不触发 canary comment | C query 无 `[webhook-ingress-canary]` 开头的 comment |
| P0-PRJ-05 | Project 外 issue 即使标题相同也不触发 | B2 title == B1 title 但无 canary comment |
| P0-PRJ-06 | 重放返回 `duplicate_accepted` | HTTP response |
| P0-PRJ-07 | 重放后 canary comment 数量不变 | C query 对比 |
| P0-PRJ-08 | 重放后 Supabase canonical event count 不变 | SQL 计数 |
| P0-PRJ-09 | 两个测试 issue 均 archived | D query 验证 `archivedAt != null` |
| P0-PRJ-10 | Canary project 已归档 | E2 query 验证 `archivedAt != null` |
| P0-PRJ-11 | Canary action 已关闭 | 环境变量确认 |

---

## 八、与 ingress 代码逻辑的对应关系

| 验证项 | 代码位置 | 测试场景 |
|--------|----------|----------|
| Project guard 识别 | `ingress.py:_is_linear_test_issue_update()` 或 actions guard | Phase 3 + Phase 4 |
| projectId 来源 | `adapter.py:normalize()` canonical payload 中需包含 `project_id` | 见 9.1 BLOCKER |
| Project 不匹配 → skipped | guard 返回 False | Phase 5（同一 team 但不在 canary project）|
| Idempotency check 在 canary 之前 | `ingress.py:handle()` line ~70-78 | Phase 7（重放返回 duplicate_accepted）|
| Canary commenter protocol | `executors.py:LinearCanaryCommentExecutor` | Phase 3 触发 commentCreate |
| Canary comment body 格式 | `executors.py:linear_canary_comment_body()` | Phase 4 验证 body 以 `[webhook-ingress-canary]` 开头 |

---

## 九、风险与缓解

### 9.1 [BLOCKER] Adapter 不传递 projectId 到 canonical payload

**问题**：当前 `adapter.py:normalize()` 构建 canonical payload 时，**未包含 `projectId` 或 `project` 字段**：

```python
"payload": {
    "id": data.get("id"),
    "identifier": data.get("identifier"),
    "title": data.get("title") or data.get("name"),
    "description": data.get("description"),
    "state": ...,
    "url": data.get("url"),
    "labels": labels,
    "label_ids": label_ids,
    "metadata": {
        "linear_id": data.get("id"),
        "linear_identifier": data.get("identifier"),
        "raw_type": event_type,
        "raw_action": action,
    },
    # ❌ projectId / project 字段缺失
}
```

**影响**：ingress 代码无法从 canonical event 中读取 `projectId` → project guard **无法实现**。

**修复方案**：修改 `adapter.py:normalize()` 在 payload 中添加 project 信息：

```python
# adapter.py normalize() 方法中，payload dict 添加：
"project_id": data.get("projectId") or data.get("project", {}).get("id") if isinstance(data.get("project"), dict) else None,
"project_name": data.get("project", {}).get("name") if isinstance(data.get("project"), dict) else None,
```

或在 metadata 中传递：

```python
"metadata": {
    "linear_id": data.get("id"),
    "linear_identifier": data.get("identifier"),
    "linear_project_id": data.get("projectId") or data.get("project", {}).get("id") if isinstance(data.get("project"), dict) else None,
    "raw_type": event_type,
    "raw_action": action,
},
```

**本次 plan 为 READ-ONLY**，不执行代码修改。执行前必须先解决此 blocker。

### 9.2 [BLOCKER] Linear Issue Webhook Payload 中 projectId 格式确认

**问题**：需要确认 Linear Issue webhook payload 中 project 信息的实际格式。可能的格式：

- `data.projectId: "uuid"`（直接字段）→ ✅ 最简单
- `data.project: { id: "uuid", name: "...", ... }`（嵌套对象）→ 需要提取 `.id`
- 两个字段都不存在 → 需要通过 Linear API 查询 issue 的 project membership

**验证前必须确认**：检查实际 webhook payload 中 `data.projectId` 或 `data.project` 字段是否存在及格式。

**参考**：Linear GraphQL `issue` query 返回 `project { id name }`，但 webhook payload 结构可能不同。

### 9.3 Project 变更事件不被 webhook 触发

**问题**：如果 issue 被**移入** canary project（而非创建时就在 project 中），Linear webhook 发出的事件类型可能是 `Issue/update`，但 payload 中的 `projectId` 是否为更新后的值取决于 Linear 的 webhook payload 结构。

**缓解**：
- 本次验证中，issue **创建时**就指定 `projectId`，确保初始状态就在 canary project 中
- update 事件 payload 应包含当前的 `projectId`（而非变更前的值）

### 9.4 Project 粒度可能过粗

**问题**：Project guard 将所有在该 project 中的 issue 都视为 canary scope。如果 project 中已有生产 issue，它们也会被 canary comment action 处理。

**缓解**：
- Canary project 应该是专用的，不含生产 issue
- 创建 `Webhook Ingress Canary` 时确保 project 为空
- 验证完成后归档整个 project

### 9.5 Token 安全

所有模板中使用 `lin_api_<TOKEN>` 占位符，执行时通过环境变量注入：

```bash
export LINEAR_API_TOKEN="lin_api_xxxxxxxx"
```

Token 不写入任何持久化文件或文档中。

---

## 十、与 OPS-LINEAR-008/009 的正交性分析

### 10.1 Guard 组合策略

如果 ingress 同时支持多种 guard（title/label/project），需要明确组合策略：

| 策略 | 行为 | 适用场景 |
|------|------|----------|
| OR（任一满足即可） | title match → 触发；label match → 触发；project match → 触发 | 最大兼容性 |
| AND（全部满足） | title match + label match + project match → 触发 | 最严格隔离 |
| 互斥（仅一种生效） | 按配置选择 title/label/project 之一 | 最清晰的语义 |

**推荐**：project guard 应该是**独立且充分**的条件。即：只要 issue 在 canary project 中，就触发 canary comment，无需额外 title 或 label 修饰。

### 10.2 本次验证的独立性

OPS-LINEAR-010 验证 project guard 的独立有效性：
- 不依赖 title guard（issue title 为普通格式，无前缀）
- 不依赖 label guard（issue 不带 `webhook-ingress-canary` label）
- 唯一识别条件：`projectId == "<CANARY_PROJECT_ID>"`

---

## 十一、注意事项

### 11.1 与 adapter labels 问题的关系

OPS-LINEAR-009 中发现的 adapter 不传递 labels 的 blocker（10.1）与 OPS-LINEAR-010 的 adapter projectId blocker（9.1）是**同类问题**：canonical payload 缺少用于 test issue 识别的字段。

**统一修复方案**：在 `adapter.py:normalize()` 中同时添加 `labels`、`label_ids`、`project_id`、`project_name` 等字段。

### 11.2 Project vs Label 选择建议

| 维度 | Project Guard | Label Guard |
|------|--------------|-------------|
| 隔离粒度 | 整个 project | 单个 issue |
| 实现复杂度 | 中等（需确认 projectId 来源） | 中等（需确认 labels 来源） |
| 运维成本 | 需要管理专用 project | 需要管理 label |
| 误触发风险 | 低（project 外 issue 不可能触发） | 低（需手动附加 label） |
| 适合场景 | 持续 canary 测试（project 常驻） | 一次性验证 |

**建议**：
- 如果需要**持续**的 canary 验证能力 → 选择 Project Guard（OPS-LINEAR-010）
- 如果需要**一次性**的精准验证 → 选择 Label Guard（OPS-LINEAR-009）
- 两者可以同时保留，使用 OR 逻辑

---

## 十二、与其他文档的关系

| 本文档 | 关联文档 | 关系说明 |
|--------|----------|----------|
| OPS-LINEAR-010 验证方案 | OPS-LINEAR-008 title-based canary | 复用相同 canary comment 验证模式，识别机制从 title 改为 project |
| OPS-LINEAR-010 验证方案 | OPS-LINEAR-009 label-based canary | 复用相同验证模式，识别机制从 label 改为 project |
| OPS-LINEAR-010 验证方案 | OPS-LINEAR-005 shadow validation | 复用 Linear GraphQL mutation 模式和 Supabase 查询模式 |
| OPS-LINEAR-010 验证方案 | OPS-LINEAR-009 decoupled design | 复用 actions/executors 架构 |
| OPS-LINEAR-010 验证方案 | SEC-ARCH-001 | 遵循签名校验和暴露面收敛原则 |

---

**文档状态**：草稿中  
**审批人**：待定
