# OPS-LINEAR-011 State Transition Validation Plan

> 文档编号：OPS-LINEAR-011  
> 版本：V1.0  
> 创建日期：2026-05-04  
> 维护人：bailian-worker

---

## 一、目标

验证 **State transition + Project membership** 双维度 guard 的完整闭环。

**核心场景**（4 个验证点）：

| # | 场景 | 预期 |
|---|------|------|
| 1 | 测试 Project 内 issue 移入 **Ready for Dev**（或等效 Ready 状态） | **触发** canary comment |
| 2 | 测试 Project 外 issue 移入 **Ready for Dev** | **不触发** canary comment |
| 3 | 测试 Project 内 issue 移入 **非 Ready** 状态（如 In Progress、Done） | **不触发** canary comment |
| 4 | **Comment** 类型 webhook 事件 | **不触发** canary comment（完全忽略） |

**约束**：READ-ONLY plan。不执行 Linear API 调用。仅提供可执行的 GraphQL 模板和操作序列。

---

## 二、前置条件

| 条件 | 状态 |
|------|------|
| production_canary ingress 模式已运行 | ✅ |
| 公网入口 `POST /webhook/events` 活跃 | ✅ |
| `production-canary-events` n8n workflow active | ✅ |
| Supabase `webhook_canonical_events` / `webhook_processing_logs` 可查询 | ✅ |
| Linear API Token 可用 | 需执行前确认 |
| JTO team ID 已知 | 需执行前确认 |
| Canary comment action 在 ingress 中已实现但 disabled | ✅ |
| Canary project 已创建 | 复用 OPS-LINEAR-010 的 `Webhook Ingress Canary` 或新建 |

### 2.1 双维度 Guard 定义

本次验证结合 **project membership** 和 **state transition** 两个维度：

```
识别为 test issue update（全部条件满足）：
  条件 A：provider == "linear"
  条件 B：canonical_type == "issue" AND canonical_action == "updated"
  条件 C：projectId 在 allowed_project_ids 中（project guard）
  条件 D：state.name 是 Ready 状态之一（state guard）
```

**Ready 状态定义**（需根据 Linear Team 的实际 workflow 确认）：
- 标准 Linear 工作流中，"Ready for Dev" 通常是 triage 后的第一个开发就绪状态
- 常见 Ready 状态名：`"Ready for Dev"`, `"Ready"`, `"Triage"`, `"Backlog"`（需确认）
- 本次验证以 **`"Ready for Dev"`** 作为目标 Ready 状态，但模板可替换

### 2.2 当前代码中的 guard 状态

在 `tools/webhook_ingress/actions.py` 中：

```python
def is_project_scoped_linear_issue_update(canonical_event, *, allowed_project_ids=None):
    # ... 检查 provider/type/action/project
    # ⚠️ 当前实现没有 state guard
    # 只有 project guard 和 label guard 的 fallback
```

**本次验证需要的 guard 扩展**（设计层面，不在本次执行）：

```python
def is_project_scoped_ready_state_update(canonical_event, *, allowed_project_ids=None, ready_state_names=None):
    if not is_project_scoped_linear_issue_update(canonical_event, allowed_project_ids=allowed_project_ids):
        return False
    # State guard：仅当 state 变更为 Ready 状态时才触发
    payload = canonical_event.get("payload") or {}
    state_name = payload.get("state")
    if not state_name:
        return False
    ready_states = ready_state_names or {"Ready for Dev", "Ready"}
    return state_name in ready_states
```

---

## 三、GraphQL 模板汇总

### 通用请求格式

```
POST https://api.linear.app/graphql
Authorization: Bearer lin_api_<TOKEN>
Content-Type: application/json
```

> 所有模板中的 `<TOKEN>` 为 Linear API token 占位符，`<JTO_TEAM_ID>` 为团队 UUID 占位符。

---

### A. Team Workflow 查询（获取 State 信息）

#### A1. 查询 Team 的 Workflow States

在执行验证前，必须先确认 team 的 issue workflow 中有哪些 state，以及它们的名称和顺序：

```graphql
query GetTeamWorkflowStates($teamId: String!) {
  team(id: $teamId) {
    id
    key
    name
    states {
      nodes {
        id
        name
        type          # backlog, unstarted, started, completed, canceled
        position
        color
      }
    }
  }
}
```

**预期输出示例**：

| id (UUID) | name | type | 用途 |
|-----------|------|------|------|
| `uuid-1` | Backlog | backlog | 待处理 |
| `uuid-2` | Ready for Dev | unstarted | **Ready 状态（本次验证目标）** |
| `uuid-3` | In Progress | started | 进行中 |
| `uuid-4` | In Review | started | 审核中 |
| `uuid-5` | Done | completed | 已完成 |
| `uuid-6` | Canceled | canceled | 已取消 |

**记录返回值**：
- `READY_STATE_ID` = `"Ready for Dev"` 或等效状态的 UUID
- `READY_STATE_NAME` = `"Ready for Dev"`（用于后续验证）
- `IN_PROGRESS_STATE_ID` = `"In Progress"` 状态的 UUID（用于对照）
- `DONE_STATE_ID` = `"Done"` 状态的 UUID（用于对照）

#### A2. 查询 Team 的 Projects

```graphql
query GetTeamProjects($teamId: String!) {
  team(id: $teamId) {
    id
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

**筛选**：`name` 包含 `Webhook Ingress Canary` 或 `canary`

#### A3. 创建 Canary Project（如不存在）

```graphql
mutation CreateCanaryProject {
  projectCreate(
    input: {
      teamIds: ["<JTO_TEAM_ID>"],
      name: "Webhook Ingress Canary",
      description: "Dedicated project for webhook ingress state transition validation (OPS-LINEAR-011).",
      state: started
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

**记录**：`project.id` → `<CANARY_PROJECT_ID>`

---

### B. Issue 操作

#### B1. 创建 Canary Project 内的测试 Issue（初始状态 = Backlog）

```graphql
mutation CreateProjectTestIssue($teamId: String!, $projectId: String!, $backlogStateId: String!) {
  issueCreate(
    input: {
      teamId: $teamId,
      title: "ops-linear-011-state-transition-test-YYYYMMDD-HHMM",
      description: "OPS-LINEAR-011: state transition canary validation — this issue IS in the canary project and WILL move to Ready for Dev to trigger canary comment",
      projectId: $projectId,
      stateId: $backlogStateId
    }
  ) {
    success
    issue {
      id
      identifier
      url
      title
      state {
        id
        name
      }
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

#### B2. 创建 Project 外的对照 Issue（初始状态 = Backlog）

```graphql
mutation CreateOutOfProjectControlIssue($teamId: String!, $backlogStateId: String!) {
  issueCreate(
    input: {
      teamId: $teamId,
      title: "ops-linear-011-state-transition-test-YYYYMMDD-HHMM",
      description: "OPS-LINEAR-011: control issue — NOT in the canary project, should NOT trigger canary comment even when state moves to Ready",
      stateId: $backlogStateId
    }
  ) {
    success
    issue {
      id
      identifier
      url
      title
      state {
        id
        name
      }
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
- **注意**：该 issue 的 `project` 应为 `null`

---

### C. State 变更操作

#### C1. Project 内 Issue → 移入 Ready for Dev（触发场景）

```graphql
mutation MoveProjectIssueToReady($issueId: String!, $readyStateId: String!) {
  issueUpdate(
    id: $issueId,
    input: {
      stateId: $readyStateId
    }
  ) {
    success
    issue {
      id
      identifier
      state {
        id
        name
      }
      project {
        id
        name
      }
      updatedAt
    }
  }
}
```

**预期**：触发 canary comment（project ✓ + ready state ✓）

#### C2. Project 外 Issue → 移入 Ready for Dev（对照：不触发）

```graphql
mutation MoveControlIssueToReady($issueId: String!, $readyStateId: String!) {
  issueUpdate(
    id: $issueId,
    input: {
      stateId: $readyStateId
    }
  ) {
    success
    issue {
      id
      identifier
      state {
        id
        name
      }
      project {
        id
        name
      }
      updatedAt
    }
  }
}
```

**预期**：不触发 canary comment（project ✗ → guard 拒绝）

#### C3. Project 内 Issue → 移入 In Progress（对照：不触发）

```graphql
mutation MoveProjectIssueToInProgress($issueId: String!, $inProgressStateId: String!) {
  issueUpdate(
    id: $issueId,
    input: {
      stateId: $inProgressStateId
    }
  ) {
    success
    issue {
      id
      identifier
      state {
        id
        name
      }
      project {
        id
        name
      }
      updatedAt
    }
  }
}
```

**预期**：不触发 canary comment（state ✗ → 非 Ready 状态）

---

### D. Comment 操作

#### D1. 在 Project 内 Issue 上创建 Comment

```graphql
mutation CreateTestComment($issueId: String!, $body: String!) {
  commentCreate(
    input: {
      issueId: $issueId,
      body: $body
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

**用途**：生成 Comment 类型 webhook 事件，验证 ingress 是否正确忽略。

---

### E. 验证查询

#### E1. 查询 Issue 的 Comments

```graphql
query GetIssueComments($issueId: String!) {
  issue(id: $issueId) {
    id
    identifier
    title
    state {
      id
      name
    }
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

#### E2. 查询 Issue 的完整状态历史

```graphql
query GetIssueHistory($issueId: String!) {
  issue(id: $issueId) {
    id
    identifier
    title
    history {
      nodes {
        id
        createdAt
        ... on IssueHistory {
          fromState {
            id
            name
          }
          toState {
            id
            name
          }
          fromProject {
            id
            name
          }
          toProject {
            id
            name
          }
          description
        }
      }
    }
  }
}
```

**用途**：确认 state 变更序列符合预期。

#### E3. 验证 Issue 归档

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

### F. Project 清理

#### F1. 归档测试 Issue

```graphql
mutation ArchiveIssue($issueId: String!) {
  issueArchive(id: $issueId) {
    success
  }
}
```

#### F2. 归档 Canary Project

```graphql
mutation ArchiveCanaryProject($projectId: String!) {
  projectArchive(id: $projectId) {
    success
  }
}
```

#### F3. 验证 Project 归档

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

---

## 四、完整操作序列

### Phase 0 — 确认 Ready State 定义（T+00:00）

```graphql
# 执行 A1 GetTeamWorkflowStates
# 确认 team 的 workflow 中是否存在 "Ready for Dev" 或等效状态
# 记录 READY_STATE_ID、READY_STATE_NAME
# 记录 IN_PROGRESS_STATE_ID（对照用）
# 记录 BACKLOG_STATE_ID 或 UNSTARTED_STATE_ID（初始状态用）
```

**变量记录**：
- `<CANARY_PROJECT_ID>` = canary project UUID
- `READY_STATE_ID` = "Ready for Dev"（或等效）状态的 UUID
- `READY_STATE_NAME` = "Ready for Dev"（或等效）
- `IN_PROGRESS_STATE_ID` = "In Progress" 状态的 UUID
- `DONE_STATE_ID` = "Done" 状态的 UUID
- `BACKLOG_STATE_ID` = "Backlog" 状态的 UUID

### Phase 1 — 基础设施确认（T+00:05）

```bash
# 1. Health check
curl -s https://webhook.exa.edu.kg/health
# 预期：{"status":"ok","mode":"production_canary"}

# 2. 确认 canary comment 已关闭
# 环境变量 LINEAR_CANARY_COMMENT_ENABLED 未设置或为 false

# 3. 确认/创建 canary project
# 执行 A2 查询现有 projects
# 如不存在，执行 A3 创建
# 记录 <CANARY_PROJECT_ID>
```

### Phase 2 — 创建测试 Issue（T+00:10）

| 步骤 | 操作 | 目标 |
|------|------|------|
| 2a | 执行 B1 `CreateProjectTestIssue`（state = Backlog） | Canary project 内的测试 issue |
| 2b | 执行 B2 `CreateOutOfProjectControlIssue`（state = Backlog） | Project 外的对照 issue |

**变量记录**：
- `PROJECT_ISSUE_ID` = Phase 2a 返回的 `issue.id`
- `PROJECT_ISSUE_KEY` = Phase 2a 返回的 `issue.identifier`
- `CONTROL_ISSUE_ID` = Phase 2b 返回的 `issue.id`
- `CONTROL_ISSUE_KEY` = Phase 2b 返回的 `issue.identifier`

> **注意**：Issue/create 事件会到达 webhook ingress，但 canary comment 只响应 `issue/updated` 且 state 为 Ready 的事件，因此 create 阶段不应触发 canary comment。

### Phase 3 — Project 内 Issue → Ready for Dev（触发场景）（T+00:15）

**前置操作**：开启 canary comment action

```bash
# 设置 LINEAR_CANARY_COMMENT_ENABLED=true
# 或修改 ingress 配置启用 canary action
```

**操作**：执行 C1 `MoveProjectIssueToReady($issueId=PROJECT_ISSUE_ID, $readyStateId=READY_STATE_ID)`

**预期事件流**：

```
Linear Issue/update webhook (stateId → READY_STATE_ID)
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
canary check: canary_comment_enabled == true ✓
canary check: _is_linear_test_issue_update()
    → provider == "linear" ✓
    → canonical_type == "issue" ✓
    → canonical_action == "updated" ✓
    → projectId 匹配 <CANARY_PROJECT_ID>？ YES ✓
    → payload.state.name == "Ready for Dev"？ YES ✓（state guard）
    ↓
canary_commenter → commentCreate mutation → canary comment 出现
```

**Wait time**：更新后等待 **30 秒**。

### Phase 4 — 验证 Project 内 Ready Issue 触发 Canary Comment（T+00:45）

**操作 A**：执行 E1 `GetIssueComments($issueId=PROJECT_ISSUE_ID)`

**验证条件**：
- `comments.nodes.length >= 1`
- 至少一条 comment 的 `body` 以 `[webhook-ingress-canary]` 开头
- `issue.state.name == "Ready for Dev"`（确认 issue 处于 Ready 状态）
- `issue.project.id == "<CANARY_PROJECT_ID>"`（确认 issue 在 canary project 中）

**操作 B**：执行 E2 `GetIssueHistory($issueId=PROJECT_ISSUE_ID)`

**验证条件**：
- 历史记录中存在 `fromState.name == "Backlog"` → `toState.name == "Ready for Dev"` 的条目

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

### Phase 5 — Project 外 Issue → Ready for Dev（对照：不触发）（T+00:50）

**操作**：执行 C2 `MoveControlIssueToReady($issueId=CONTROL_ISSUE_ID, $readyStateId=READY_STATE_ID)`

**Wait time**：等待 **30 秒**。

**验证 A**：执行 E1 `GetIssueComments($issueId=CONTROL_ISSUE_ID)`

**验证条件**：
- `comments.nodes` 中 **不存在** body 以 `[webhook-ingress-canary]` 开头的 comment
- `issue.project` 为 `null`（确认不在 canary project 中）
- `issue.state.name == "Ready for Dev"`（确认 state 已变更，但 project guard 拒绝）

**关键验证**：即使该 issue 的 state 也变成了 "Ready for Dev"，但因为不在 canary project 中，不应触发 canary comment。这验证了 **project guard 的必要性**：仅 state guard 是不够的。

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

**预期**：2 行（issue/created + issue/updated），但 processing logs 中 canary_action phase 应为 `skipped` with `reason: not_project_scoped_issue_update`。

### Phase 6 — Project 内 Issue → In Progress（对照：不触发）（T+01:00）

**操作**：执行 C3 `MoveProjectIssueToInProgress($issueId=PROJECT_ISSUE_ID, $inProgressStateId=IN_PROGRESS_STATE_ID)`

> 注意：此时 issue 从 "Ready for Dev" 变为 "In Progress"。这不是 Ready 状态。

**Wait time**：等待 **30 秒**。

**验证**：执行 E1 `GetIssueComments($issueId=PROJECT_ISSUE_ID)`

**验证条件**：
- canary comment 数量与 Phase 4 相同（**没有新增** canary comment）
- `issue.state.name == "In Progress"`（确认 state 已变更）
- `issue.project.id == "<CANARY_PROJECT_ID>"`（确认 issue 仍在 canary project 中）

**关键验证**：即使 issue 在 canary project 中，但 state 变更到了非 Ready 状态，不应触发 canary comment。这验证了 **state guard 的必要性**：仅 project guard 是不够的。

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

**预期**：至少 3 行（issue/created + issue/updated × 2），但 canary_action logs 中只有一次 `success`（Phase 3），Phase 6 的 update 应为 `skipped` with `reason: not_ready_state`。

### Phase 7 — Comment 事件验证（不触发）（T+01:10）

**操作**：执行 D1 `CreateTestComment` 在 Project 内 Issue 上

```graphql
mutation CreateTestComment($issueId: String!, $body: String!) {
  commentCreate(
    input: {
      issueId: $issueId,
      body: "ops-linear-011: testing comment event — should be ignored by ingress"
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

**Wait time**：等待 **30 秒**。

**验证 A**：执行 E1 `GetIssueComments($issueId=PROJECT_ISSUE_ID)`

**验证条件**：
- 只有一条 canary comment（来自 Phase 3），**没有新增**
- 新增的 comment 是用户手动创建的（body = "ops-linear-011: testing comment event..."）
- 没有第二条 canary comment

**验证 B**：Supabase 查询

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

**预期**：有一行 `comment/created` 的记录（comment webhook 事件被 ingress 接收并存储），但 `n8n_forwarded` 的值取决于 ingress 的 comment 处理策略。

**关键验证**：Comment 事件被 ingress 正确处理（存储），但 **canary comment action 完全忽略 comment 类型事件**，不产生任何副作用。

### Phase 8 — 关闭 Canary Action（T+01:20）

```bash
# 设置 LINEAR_CANARY_COMMENT_ENABLED=false
# 确认 ingress mode 仍然是 production_canary
curl -s https://webhook.exa.edu.kg/health
```

### Phase 9 — 清理归档（T+01:25）

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
    id identifier archivedAt project { id name } state { name }
  }
  controlIssue: issue(id: "<CONTROL_ISSUE_ID>") {
    id identifier archivedAt project { id name } state { name }
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
T+00:00  — Phase 0: 查询 Team Workflow States，确认 Ready 状态定义
T+00:05  — Phase 1: 基础设施确认 + project 确认/创建
T+00:10  — Phase 2: 创建 project 内 + project 外 两个测试 issue（Backlog 状态）
T+00:15  — Phase 3: project 内 issue Backlog → Ready for Dev → 触发 canary comment
T+00:45  — Phase 4: 验证 project 内 Ready issue 上有 1 条 canary comment + history
T+00:50  — Phase 5: project 外 issue Backlog → Ready for Dev → 不触发
T+01:00  — Phase 6: project 内 issue Ready for Dev → In Progress → 不触发
T+01:10  — Phase 7: Comment 事件 → 不触发 canary comment
T+01:20  — Phase 8: 关闭 canary action
T+01:25  — Phase 9: Archive 两个测试 issue
T+01:30  — Phase 9: 归档验证 + archive canary project
T+01:35  — 整理证据，撰写验证报告
```

---

## 六、证据收集清单

| 序号 | 证据项 | 收集方式 |
|------|--------|----------|
| E1 | Team workflow states 查询结果 | A1 query 结果 |
| E2 | Health check 输出 | `curl` 结果 |
| E3 | Project 创建确认 | A3 mutation 返回值 |
| E4 | Project 内 issue 创建确认 | B1 mutation 返回值（含 `project.id`, `state.id`）|
| E5 | Project 外 issue 创建确认 | B2 mutation 返回值（`project` 为 null, `state.id`）|
| E6 | Project 内 issue → Ready for Dev 后 canary comment 存在 | E1 query 结果 |
| E7 | Issue history：Backlog → Ready for Dev | E2 query 结果 |
| E8 | Project 外 issue → Ready for Dev 后无 canary comment | E1 query 结果 |
| E9 | Project 内 issue → In Progress 后无新增 canary comment | E1 query 对比 Phase 4 |
| E10 | Comment 事件后无新增 canary comment | E1 query 对比 Phase 6 |
| E11 | Supabase canonical events（含所有 4 个场景） | SQL 查询结果 |
| E12 | Canary action 关闭确认 | 环境变量确认 |
| E13 | 两个 issue 均 archived | E3 query 结果 |
| E14 | Canary project archived | F3 query 结果 |

---

## 七、验收标准

| 编号 | 标准 | 判定 |
|------|------|------|
| P0-ST-01 | Canary project 已创建 | A3 mutation success |
| P0-ST-02 | Project 内 + Ready for Dev → 触发 canary comment | E1 query 找到 `[webhook-ingress-canary]` 开头的 comment |
| P0-ST-03 | 恰好 1 条 canary comment 在 Phase 3 后出现 | comment count = 1 |
| P0-ST-04 | Project 外 + Ready for Dev → 不触发 canary comment | E1 query 无 `[webhook-ingress-canary]` 开头的 comment |
| P0-ST-05 | Project 内 + In Progress → 不触发 canary comment | E1 query 无新增 canary comment |
| P0-ST-06 | Comment 事件 → 不触发 canary comment | E1 query 无新增 canary comment |
| P0-ST-07 | Issue history 记录 state 变更序列 | E2 query 验证 history nodes |
| P0-ST-08 | Supabase 包含所有事件记录 | SQL 查询验证 issue/created + issue/updated × 3 + comment/created |
| P0-ST-09 | Canary action 仅成功执行 1 次（Phase 3） | Processing logs 验证 |
| P0-ST-10 | 两个测试 issue 均 archived | E3 query 验证 `archivedAt != null` |
| P0-ST-11 | Canary project 已归档 | F3 query 验证 `archivedAt != null` |
| P0-ST-12 | Canary action 已关闭 | 环境变量确认 |

---

## 八、与 ingress 代码逻辑的对应关系

| 验证项 | 代码位置 | 测试场景 |
|--------|----------|----------|
| Project guard 识别 | `actions.py:is_project_scoped_linear_issue_update()` | Phase 3 (project ✓) + Phase 5 (project ✗) |
| State guard 识别 | `actions.py` 中需新增 state guard 函数 | Phase 3 (state ✓) + Phase 6 (state ✗) |
| ProjectId 来源 | `adapter.py:normalize()` → `source.project_id` + `payload.project_id` | 已实现（见 adapter.py 第 127-132 行）|
| State name 来源 | `adapter.py:normalize()` → `payload.state` | 已实现（见 adapter.py 第 123 行）|
| Comment 事件忽略 | `actions.py:is_project_scoped_linear_issue_update()` | Phase 7（`canonical_type == "comment"` → guard 返回 False）|
| Idempotency check 在 canary 之前 | `ingress.py:handle()` line ~70-78 | 重放场景（同 OPS-LINEAR-008）|
| Canary commenter protocol | `executors.py:LinearCanaryCommentExecutor` | Phase 3 触发 commentCreate |
| Canary comment body 格式 | `executors.py` | Phase 4 验证 body 以 `[webhook-ingress-canary]` 开头 |

### 8.1 Adapter 中的 State 传递确认

查看 `adapter.py:normalize()` 的 payload 构建：

```python
"payload": {
    "id": data.get("id"),
    "identifier": data.get("identifier"),
    "title": data.get("title") or data.get("name"),
    "description": data.get("description"),
    "state": data.get("state", {}).get("name") if isinstance(data.get("state"), dict) else data.get("state"),
    # ...
}
```

**结论**：`payload.state` 字段已存在于 canonical event 中，格式为 state 名称字符串（如 `"Ready for Dev"`）。**无需修改 adapter**。

### 8.2 Adapter 中的 Project 传递确认

```python
project = data.get("project") if isinstance(data.get("project"), dict) else {}
project_id = data.get("projectId") or project.get("id")
project_name = project.get("name")
# ...
"source": {
    # ...
    "project_id": project_id,
    # ...
},
"payload": {
    # ...
    "project_id": project_id,
    "project_name": project_name,
    # ...
}
```

**结论**：`source.project_id` 和 `payload.project_id` 字段均已存在于 canonical event 中。**无需修改 adapter**。

### 8.3 需要的代码改动（设计层面）

在 `actions.py` 中需要新增一个 **state-aware guard 函数**：

```python
def is_project_scoped_ready_state_update(
    canonical_event: dict[str, Any],
    *,
    allowed_project_ids: set[str] | None = None,
    ready_state_names: set[str] | None = None,
) -> bool:
    """Guard: project + ready state dual-dimension check."""
    # 1. Check project scope first
    if not is_project_scoped_linear_issue_update(canonical_event, allowed_project_ids=allowed_project_ids):
        return False
    # 2. Check state is Ready
    payload = canonical_event.get("payload") or {}
    state_name = payload.get("state")
    if not state_name:
        return False
    ready_states = ready_state_names or {"Ready for Dev", "Ready"}
    return state_name in ready_states
```

然后将 `LinearCanaryCommentAction` 的 guard 从 `is_project_scoped_linear_issue_update` 替换为 `is_project_scoped_ready_state_update`。

> **本次 plan 为 READ-ONLY**，不执行代码修改。执行前必须先实现 state guard。

---

## 九、风险与缓解

### 9.1 Linear Webhook Payload 中 State 格式确认

**问题**：需要确认 Linear Issue/update webhook payload 中 `data.state` 字段的实际格式。

可能的格式：
- `data.state: { id: "uuid", name: "Ready for Dev", type: "unstarted" }`（嵌套对象）→ ✅ adapter 已处理
- `data.stateId: "uuid"`（仅 ID，无 name）→ ❌ adapter 中的 `data.get("state", {}).get("name")` 将返回 None

**验证方法**：在 Phase 3 执行后，检查 Supabase `webhook_raw_events` 中 `raw_body` 的实际结构。

**缓解**：如果 `data.state` 不存在但有 `data.stateId`，需要通过 Linear GraphQL API 查询 state name：

```graphql
query GetStateName($stateId: String!) {
  workflowState(id: $stateId) {
    id
    name
    type
  }
}
```

但这会增加验证复杂度。建议先确认 webhook payload 结构。

### 9.2 State 变更可能不触发 Webhook

**问题**：某些 Linear 配置下，仅 state 变更可能不触发 Issue/update webhook，或 payload 中不包含完整的 state 信息。

**缓解**：
- Linear 标准 webhook 配置中，Issue/update 包含所有字段变更
- State 变更是最常见的 update 类型之一，应该被正常触发
- 如果 webhook 不包含完整 state 信息，需要在 update 时同时修改 description 以确保 payload 完整

### 9.3 Ready State 名称因 Team 而异

**问题**：不同 team 的 workflow 可能有不同的 state 名称（如 `"Todo"` vs `"Ready for Dev"`）。

**缓解**：
- Phase 0 中执行 `GetTeamWorkflowStates` 查询确认实际 state 名称
- state guard 使用可配置的 `ready_state_names` 集合
- 默认包含 `{"Ready for Dev", "Ready"}`，可根据实际情况扩展

### 9.4 State 变更顺序问题

**问题**：Phase 6 中 issue 从 "Ready for Dev" → "In Progress"。如果 team 的 workflow 不允许这种直接跳转（如必须经过 "In Review"），则 mutation 可能失败。

**缓解**：
- Phase 0 确认 team 的 workflow 是否允许直接跳转
- 如不允许，使用 `doneStateId` 或 `canceledStateId` 作为对照状态（这些肯定不是 Ready 状态）

### 9.5 Comment 事件可能被转发到 n8n

**问题**：Comment 类型 webhook 事件会被 ingress 接收并存储，可能被转发到 n8n。

**缓解**：
- n8n canary workflow 中的 code node 应检查 `canonical_type`，仅在 `issue` 类型时执行
- 即使转发到 n8n，canary comment action 的 guard 会拒绝 comment 类型事件（`canonical_type != "issue"`）

### 9.6 Project ID 传递的边界情况

**问题**：如果 issue 在创建时没有指定 project，但后来被添加到 project 中，webhook payload 中 `projectId` 可能不准确。

**缓解**：
- 本次验证中，issue **创建时**就指定 `projectId`
- Phase 3 的 state 变更是在已有 project 的 issue 上进行的
- 不涉及 project membership 变更的场景

### 9.7 Token 安全

所有模板中使用 `lin_api_<TOKEN>` 占位符，执行时通过环境变量注入：

```bash
export LINEAR_API_TOKEN="lin_api_xxxxxxxx"
```

Token 不写入任何持久化文件或文档中。

---

## 十、与 OPS-LINEAR-008/009/010 的正交性分析

### 10.1 Guard 维度对比

| 方案 | 识别维度 | 条件 | 优点 | 缺点 |
|------|----------|------|------|------|
| OPS-LINEAR-008 | Title prefix `[canary-ops-008]` | title 匹配 | 简单直接 | 需要修改标题 |
| OPS-LINEAR-009 | Label `webhook-ingress-canary` | label 匹配 | 不修改标题 | 需要管理 label |
| OPS-LINEAR-010 | Project membership | projectId 匹配 | 最干净隔离 | 粒度较粗 |
| **OPS-LINEAR-011** | **Project + State transition** | **projectId + state 双重匹配** | **最精确：仅在 canary project 中且状态为 Ready 时触发** | **实现最复杂** |

### 10.2 Guard 组合策略

**OPS-LINEAR-011 推荐的 guard 链**：

```
guard 1: provider == "linear"
guard 2: canonical_type == "issue" AND canonical_action == "updated"
guard 3: projectId IN allowed_project_ids          ← project guard
guard 4: payload.state IN ready_state_names        ← state guard
```

只有所有 guard 都通过时才触发 canary comment。

### 10.3 验证独立性

OPS-LINEAR-011 验证 **双维度 guard** 的独立有效性：
- 不依赖 title guard
- 不依赖 label guard
- 唯一识别条件：projectId + state 的组合

---

## 十一、注意事项

### 11.1 代码改动范围

本次验证为 READ-ONLY plan。执行前需要在 `actions.py` 中实现 state guard：

**改动文件**：`tools/webhook_ingress/actions.py`

**改动内容**：
1. 新增 `is_project_scoped_ready_state_update()` 函数
2. `LinearCanaryCommentAction` 使用新的 guard 函数替代 `is_project_scoped_linear_issue_update`
3. 新增 `ready_state_names` 参数到 `LinearCanaryCommentAction.__init__`

### 11.2 Adapter 不需要修改

`adapter.py:normalize()` 已经传递了 `source.project_id` 和 `payload.state` 字段。无需修改。

### 11.3 Project + State 组合的选择建议

| 场景 | 推荐方案 | 理由 |
|------|----------|------|
| 持续 canary 测试（所有 update） | OPS-LINEAR-010（Project only） | 简单，粒度足够 |
| 持续 canary 测试（仅 Ready 状态） | OPS-LINEAR-011（Project + State） | 精确，减少误触发 |
| 一次性精准验证 | OPS-LINEAR-009（Label） | 最小侵入 |

**建议**：如果 canary 验证的目的是确认 **issue 进入开发队列时被正确处理**，则 OPS-LINEAR-011 是最精确的方案。

---

## 十二、与其他文档的关系

| 本文档 | 关联文档 | 关系说明 |
|--------|----------|----------|
| OPS-LINEAR-011 验证方案 | OPS-LINEAR-008 title-based canary | 复用相同 canary comment 验证模式 |
| OPS-LINEAR-011 验证方案 | OPS-LINEAR-009 decoupled design | 复用 actions/executors 架构 |
| OPS-LINEAR-011 验证方案 | OPS-LINEAR-010 project-based canary | 在 project guard 基础上增加 state guard |
| OPS-LINEAR-011 验证方案 | OPS-LINEAR-005 shadow validation | 复用 Linear GraphQL mutation 模式和 Supabase 查询模式 |
| OPS-LINEAR-011 验证方案 | SEC-ARCH-001 | 遵循签名校验和暴露面收敛原则 |

---

**文档状态**：草稿中  
**审批人**：待定
