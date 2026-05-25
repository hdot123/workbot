# OPS-LINEAR-006 Dry-Run Acceptance Report Template

> 文档编号：OPS-LINEAR-006  
> 版本：V1.0  
> 创建日期：2026-05-04  
> 维护人：bailian-worker  
> 状态：Template（执行时填写）

---

## 一、执行摘要

### 1.1 验收结论

| 验收项 | 状态 | 证据引用 |
|--------|------|---------|
| R1: 旧 `/webhook/events` 正常 | [ ] 通过 / [ ] 未通过 | DT-01 |
| R2: `/webhooks/linear` 接受有效事件 | [ ] 通过 / [ ] 未通过 | DT-02 |
| R3: Supabase raw/canonical/log 三表正确写入 | [ ] 通过 / [ ] 未通过 | DT-03 |
| R4: n8n dry-run 收到 canonical event（非 raw Linear payload） | [ ] 通过 / [ ] 未通过 | DT-04 |
| R5: 无生产副作用 | [ ] 通过 / [ ] 未通过 | DT-05 |
| R6: 重复 replay 不重复 forward | [ ] 通过 / [ ] 未通过 | DT-06 |
| R7: 敏感字段脱敏 | [ ] 通过 / [ ] 未通过 | DT-07 |
| R8: Unique public endpoint verified | [ ] 通过 / [ ] 未通过 | Section 3.1 |
| R9: Old webhook disabled/deleted | [ ] 通过 / [ ] 未通过 | Section 3.2 |
| R10: Active secret verified | [ ] 通过 / [ ] 未通过 | Section 3.3 |
| R11: Real Linear Issue created/updated/comment created | [ ] 通过 / [ ] 未通过 | Section 4 |
| R12: Raw/canonical/logs written | [ ] 通过 / [ ] 未通过 | Section 5 |
| R13: Dry-run n8n success | [ ] 通过 / [ ] 未通过 | Section 6 |
| R14: Idempotency verified | [ ] 通过 / [ ] 未通过 | Section 7 |
| R15: Redaction verified | [ ] 通过 / [ ] 未通过 | Section 8 |
| R16: No production actions | [ ] 通过 / [ ] 未通过 | Section 9 |

**总体结论**：[ ] 全部通过，建议进入下一阶段  /  [ ] 有条件通过  /  [ ] 不通过，需修复后复测

---

## 二、执行元数据

| 字段 | 值 |
|------|-----|
| 执行日期 | [填写 ISO 8601] |
| 执行人 | [填写] |
| 审核人 | [填写] |
| 执行环境 | [node-22 IP / hostname] |
| Ingress 模式 | `shadow` → `canary_dryrun`（切换后） |
| Git commit SHA | [填写] |
| Branch | `branch-2` (task branch) |

---

## 三、端点与凭证验证

### 3.1 R8: Unique Public Endpoint Verified

| 检查项 | 预期 | 实际 | 状态 |
|--------|------|------|------|
| Health endpoint 可达 | HTTP 200, mode=`shadow`/`canary_dryrun` | [填写] | [ ] |
| Shadow URL unique | `https://webhook.exa.edu.kg/webhooks/linear` 仅由 Linear shadow webhook 使用 | [填写] | [ ] |
| No route collision | `/webhooks/linear` 不与任何现有 route 冲突 | [填写] | [ ] |

**验证命令**：

```bash
curl -sf https://webhook.exa.edu.kg/health | python3 -m json.tool
```

### 3.2 R9: Old Webhook Disabled/Deleted

> **关键约束**：此处的 "old webhook" 指 Linear 侧的 **旧生产 webhook 配置**（非 `/webhook/events` nginx route）。

| 检查项 | 预期 | 实际 | 状态 |
|--------|------|------|------|
| Linear webhook URL 指向新端点 | shadow webhook URL = `https://webhook.exa.edu.kg/webhooks/linear` | [填写] | [ ] |
| 旧 webhook 已 disabled 或 deleted | Linear Settings > Webhooks 中旧条目状态为 Disabled/Deleted | [填写] | [ ] |
| `/webhook/events` nginx route 行为 | [说明是否保留为兼容端点] | [填写] | [ ] |

**验证方式**：
- Linear UI: Settings > Webhooks > 检查条目状态
- 或 Linear GraphQL: `webhooks` query 检查状态

### 3.3 R10: Active Secret Verified

| 检查项 | 预期 | 实际 | 状态 |
|--------|------|------|------|
| `LINEAR_WEBHOOK_SECRET` 在 ingress 环境中存在 | `docker exec webhook-ingress env | grep LINEAR_WEBHOOK_SECRET` 返回非空 | [填写] | [ ] |
| Secret 值与 Linear webhook 配置一致 | 从 1Password 获取的 secret 匹配 Linear webhook 签名密钥 | [填写] | [ ] |
| Secret 未泄漏到日志 | 日志中无明文 secret 值 | [填写] | [ ] |
| Secret 未泄漏到代码/仓库 | `git grep` 无 secret 明文 | [填写] | [ ] |

**验证命令**：

```bash
# 检查环境变量存在
docker exec webhook-ingress-shadow sh -c 'test -n "$LINEAR_WEBHOOK_SECRET" && echo "EXISTS" || echo "MISSING"'

# 验证 Secret 签名（发送测试事件并检查响应）
# 参见 DT-02 测试用例
```

---

## 四、真实 Linear 事件验证（R11）

### 4.1 事件触发记录

| 事件序号 | 操作 | 线性操作 | 预期 canonical | 触发时间 | Supabase event_id | 状态 |
|---------|------|---------|---------------|---------|------------------|------|
| 1 | Issue created | `issueCreate` mutation | `issue` / `created` | [填写] | [填写] | [ ] |
| 2 | Issue updated | `issueUpdate` mutation | `issue` / `updated` | [填写] | [填写] | [ ] |
| 3 | Comment created | `commentCreate` mutation | `comment` / `created` | [填写] | [填写] | [ ] |

### 4.2 临时 Issue 信息

| 字段 | 值 |
|------|-----|
| Issue ID | [填写] |
| Issue identifier | [填写，如 DRY-001] |
| Issue title | `[shadow-ops-006] webhook-test-YYYYMMDD` |
| Issue URL | [填写] |
| Archive 状态 | [ ] 已 archive / [ ] 未 archive |

### 4.3 Linear GraphQL 触发记录

```bash
# Step 1: Create Issue
curl -sS -X POST https://api.linear.app/graphql \
  -H "Authorization: Bearer lin_api_[REDACTED]" \
  -H "Content-Type: application/json" \
  -d '{"query":"mutation { issueCreate(input: { teamId: \"[TEAM_ID]\", title: \"[shadow-ops-006] webhook-test-YYYYMMDD\", description: \"[shadow-ops-006] Minimal real event trigger test\" }) { success issue { id identifier url } } }"}'

# 记录返回的 issue ID 用于后续步骤
```

---

## 五、数据存储验证（R12: Raw/Canonical/Logs Written）

### 5.1 三表计数

```sql
SELECT
    'raw' as table_name, COUNT(*) as count
    FROM webhook_raw_events
    WHERE provider = 'linear' AND created_at > NOW() - INTERVAL '15 minutes'
UNION ALL
SELECT 'canonical', COUNT(*)
    FROM webhook_canonical_events
    WHERE provider = 'linear' AND created_at > NOW() - INTERVAL '15 minutes'
UNION ALL
SELECT 'logs', COUNT(*)
    FROM webhook_processing_logs
    WHERE provider = 'linear' AND created_at > NOW() - INTERVAL '15 minutes';
```

| 表 | 预期最少行数 | 实际行数 | 状态 |
|----|------------|---------|------|
| `webhook_raw_events` | 3（create + update + comment） | [填写] | [ ] |
| `webhook_canonical_events` | 3 | [填写] | [ ] |
| `webhook_processing_logs` | 6+（每个事件至少 store 阶段） | [填写] | [ ] |

### 5.2 Canonical Event 格式验证

```sql
SELECT
    event_id,
    canonical_type,
    canonical_action,
    canonical_version,
    provider_event_type,
    provider_action,
    n8n_forwarded,
    source_resource_id,
    created_at
FROM webhook_canonical_events
WHERE provider = 'linear'
  AND created_at > NOW() - INTERVAL '15 minutes'
ORDER BY created_at ASC;
```

| 检查项 | 预期 | 实际 | 状态 |
|--------|------|------|------|
| `canonical_version` | `v1` | [填写] | [ ] |
| `canonical_type` 覆盖 | `issue`, `comment` | [填写] | [ ] |
| `canonical_action` 覆盖 | `created`, `updated` | [填写] | [ ] |
| `n8n_forwarded` | `0`（dry-run 模式） | [填写] | [ ] |

---

## 六、n8n Dry-Run 验证（R13）

### 6.1 Workflow 状态

| 检查项 | 预期 | 实际 | 状态 |
|--------|------|------|------|
| Dry-run workflow 已导入 | Workflow 存在于 n8n | [填写] | [ ] |
| Dry-run workflow 已激活 | `active = true` | [填写] | [ ] |
| Webhook path 可达 | `https://webhook.exa.edu.kg/webhook/linear-canonical-dryrun` 返回 200 | [填写] | [ ] |

### 6.2 Execution 验证

| 检查项 | 预期 | 实际 | 状态 |
|--------|------|------|------|
| Dry-run workflow executions ≥ 1 | 收到事件后执行 | [填写数量] | [ ] |
| Execution 输入为 canonical event 格式 | 包含 `canonical_type`, `canonical_action`, `source` 等字段 | [填写] | [ ] |
| Execution 输入 NOT raw Linear payload | 无 `Linear-Signature`, `Linear-Delivery` headers | [填写] | [ ] |
| 无外部 API 调用 | Execution log 无 Linear/GitLab/Slack HTTP requests | [填写] | [ ] |

### 6.3 n8n API 验证命令

```bash
# 获取 dry-run workflow executions
curl -s "${N8N_API_URL}/executions?workflowId=<DRYRUN-WORKFLOW-ID>&limit=10" \
  -H "X-N8N-API-KEY: ${N8N_API_KEY}" | python3 -m json.tool
```

---

## 七、幂等性验证（R14）

### 7.1 重放测试记录

| 测试 | Delivery ID | 发送次数 | 第1次 status | 第2次 status | 第3次 status | Canonical count | 状态 |
|------|-------------|---------|-------------|-------------|-------------|----------------|------|
| Dedup test | `dt06-dedup-replay` | 3 | `accepted` | `duplicate_accepted` | `duplicate_accepted` | [填写] | [ ] |

### 7.2 SQL 去重验证

```sql
SELECT
    idempotency_key,
    COUNT(*) as canonical_count,
    MIN(created_at) as first_seen
FROM webhook_canonical_events
WHERE idempotency_key = 'linear:dt06-dedup-replay'
GROUP BY idempotency_key;
-- 预期: canonical_count = 1
```

```sql
SELECT
    COUNT(*) as raw_count
FROM webhook_raw_events
WHERE idempotency_key = 'linear:dt06-dedup-replay';
-- 预期: raw_count = 3（每次请求都记录 raw）
```

---

## 八、脱敏验证（R15）

### 8.1 日志脱敏

| 检查项 | 预期匹配行数 | 实际匹配行数 | 状态 |
|--------|------------|-------------|------|
| 明文 64 位 hex 签名值 | 0 | [填写] | [ ] |
| 明文 `LINEAR_WEBHOOK_SECRET=` | 0 | [填写] | [ ] |
| 明文数据库 URL（含密码） | 0 | [填写] | [ ] |
| `[REDACTED]` 标记 | > 0 | [填写] | [ ] |

### 8.2 数据库 raw_headers 脱敏

```sql
SELECT
    event_id,
    raw_headers->>'x-linear-signature' as sig_value,
    raw_headers->>'X-Linear-Signature' as sig_value_alt,
    CASE
        WHEN raw_headers->>'x-linear-signature' = '[REDACTED]' THEN 'PASS'
        WHEN raw_headers->>'X-Linear-Signature' = '[REDACTED]' THEN 'PASS'
        ELSE 'FAIL'
    END as redaction_status
FROM webhook_raw_events
WHERE provider = 'linear'
  AND created_at > NOW() - INTERVAL '15 minutes';
```

---

## 九、生产隔离验证（R16: No Production Actions）

### 9.1 Production Workflow 隔离

| 检查项 | 预期 | 实际 | 状态 |
|--------|------|------|------|
| 旧 `/webhook/events` 端点可达 | HTTP 200 | [填写] | [ ] |
| 旧 production workflow 无额外 executions | 仅 DT-01 的 1 条测试事件 | [填写数量] | [ ] |
| Production Linear webhook URL 未变 | 仍指向 `/webhook/events`（除非已正式切换） | [填写] | [ ] |

### 9.2 Ingress 模式确认

```bash
curl -sf https://webhook.exa.edu.kg/health | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'mode={d.get(\"mode\",\"UNKNOWN\")}')"
```

| 检查项 | 预期值 | 实际值 | 状态 |
|--------|--------|--------|------|
| Ingress mode | `shadow` 或 `canary_dryrun` | [填写] | [ ] |

### 9.3 Supabase n8n_forwarded 统计

```sql
SELECT
    COUNT(*) as total,
    SUM(CASE WHEN n8n_forwarded = 0 THEN 1 ELSE 0 END) as not_forwarded,
    SUM(CASE WHEN n8n_forwarded = 1 THEN 1 ELSE 0 END) as forwarded
FROM webhook_canonical_events
WHERE provider = 'linear'
  AND created_at > NOW() - INTERVAL '15 minutes';
-- 预期: forwarded = 0
```

---

## 十、执行后检查清单（Post-Fix Queries/Checks）

> 以下是在主修复（main fix）合并后，执行验收前需要逐项确认的查询和检查。

### 10.1 基础设施检查

| # | 检查 | 命令/查询 | 通过条件 |
|---|------|----------|---------|
| 1 | Ingress 服务运行中 | `docker ps --filter name=webhook-ingress` | Status = Up |
| 2 | n8n 容器运行中 | `docker ps --filter name=n8n` | Status = Up |
| 3 | nginx 配置有效 | `docker exec n8n-webhook-gateway nginx -t` | syntax is ok |
| 4 | Health endpoint 可达 | `curl -sf https://webhook.exa.edu.kg/health` | HTTP 200 |
| 5 | Ingress mode 正确 | health endpoint 的 `mode` 字段 | `shadow` 或 `canary_dryrun` |

### 10.2 端点检查

| # | 检查 | 命令 | 通过条件 |
|---|------|------|---------|
| 6 | 旧端点向后兼容 | `curl -s -o /dev/null -w "%{http_code}" -X POST https://webhook.exa.edu.kg/webhook/events -d '{}'` | 200 |
| 7 | Shadow 端点可达 | `curl -s -o /dev/null -w "%{http_code}" -X POST https://webhook.exa.edu.kg/webhooks/linear -d '{}'` | 200（签名失败时 401） |
| 8 | Dry-run webhook 可达 | `curl -s -o /dev/null -w "%{http_code}" -X POST https://webhook.exa.edu.kg/webhook/linear-canonical-dryrun -d '{}'` | 200 |

### 10.3 Linear Webhook 配置检查

| # | 检查 | 查询方式 | 通过条件 |
|---|------|---------|---------|
| 9 | Shadow webhook 处于 Active 状态 | Linear GraphQL: `webhooks` query | `enabled = true` |
| 10 | Shadow webhook URL 正确 | Linear GraphQL: `webhooks` query | URL = `https://webhook.exa.edu.kg/webhooks/linear` |
| 11 | Shadow webhook resourceTypes 包含 Issue+Comment | Linear GraphQL: `webhooks` query | `resourceTypes` 包含 `Issue`, `Comment` |
| 12 | 旧 webhook 已 disabled/deleted | Linear Settings UI 或 GraphQL | 旧条目状态 = Disabled/Deleted 或不存在 |

### 10.4 Secret 验证

| # | 检查 | 命令 | 通过条件 |
|---|------|------|---------|
| 13 | `LINEAR_WEBHOOK_SECRET` 环境变量存在 | `docker exec webhook-ingress sh -c 'test -n "$LINEAR_WEBHOOK_SECRET" && echo OK'` | OK |
| 14 | Secret 签名验证通过 | 发送带正确签名的测试事件 | HTTP 200, status=accepted |

### 10.5 Supabase 检查

| # | 检查 | SQL 查询 | 通过条件 |
|---|------|---------|---------|
| 15 | 三表可访问 | `SELECT COUNT(*) FROM webhook_raw_events` | 无错误 |
| 16 | RLS 策略生效 | 使用 non-service_role 连接测试 | 拒绝写入 |

---

## 十一、Blocked / Needs-Approval Notes

### 11.1 需求冲突分析

#### 冲突 C1: "Do not call Linear API" vs "Trigger real Linear events"

| 维度 | 要求 A | 要求 B | 冲突点 |
|------|--------|--------|--------|
| 要求 | 不要调用 Linear API | 触发真实 Linear 事件（Issue create/update/comment） | 触发真实 Linear 事件必须通过 Linear GraphQL API 创建/更新 Issue |

**分析**：

1. **约束 "do not call Linear API"** 出现在 n8n dry-run 工作流设计中（OPS-LINEAR-006-n8n-dryrun-design.md §8），含义是 **n8n dry-run workflow 不得调用外部 API**（Linear/GitLab/Slack），以保证 dry-run 模式的只读安全性。

2. **约束 "trigger real Linear events"** 是验收要求的一部分，意味着需要通过 Linear GraphQL API 手动创建临时 Issue 来生成真实的 webhook 事件流。

3. **两者不冲突的前提**：
   - "Do not call Linear API" 约束的是 **n8n workflow 内部行为**（dry-run workflow 不得主动调用外部 API）
   - "Trigger real Linear events" 是 **验收前置操作**（由执行人在测试开始前通过 GraphQL 手动触发）
   - 这两个约束作用于不同的系统和阶段

**结论**：需要主代理确认上述解释是否正确，尤其是：
- [ ] "Do not call Linear API" 是否仅指 n8n dry-run workflow？
- [ ] 还是也禁止执行人在验收过程中使用 Linear GraphQL API？

#### 冲突 C2: "Old webhook disabled/deleted" vs "Backward compatibility"

| 维度 | 要求 A | 要求 B | 冲突点 |
|------|--------|--------|--------|
| 要求 | 旧 webhook 已 disabled/deleted | DT-01 验证旧 `/webhook/events` 正常 | 旧端点是否应该保留？ |

**分析**：

1. **R9: Old webhook disabled/deleted** — 指的是 **Linear 侧的旧 webhook 配置**（Linear Settings > Webhooks 中的条目），要求将其 disable 或 delete，因为新的 shadow webhook 已经接管。

2. **DT-01: 旧 `/webhook/events` 向后兼容** — 指的是 **nginx/ingress 侧的 `/webhook/events` route**，验证这个端点仍然可以响应请求（即使 Linear 不再向其发送事件）。

3. **两者不冲突的前提**：
   - R9 约束的是 Linear 端的 webhook 注册条目
   - DT-01 验证的是我们服务端的 route 兼容性（防止 Linear 配置回退时端点不可用）

**结论**：需要主代理确认：
- [ ] R9 的 "old webhook" 仅指 Linear 侧配置，不要求删除 `/webhook/events` nginx route？
- [ ] 是否需要保留 `/webhook/events` 作为回滚路径？

### 11.2 需要审批的决策

| # | 决策项 | 选项 | 推荐 | 待审批 |
|---|--------|------|------|--------|
| D1 | Dry-run 期间 ingress mode | `shadow`（不转发）vs `canary_dryrun`（转发到 dry-run n8n） | `canary_dryrun`（验证完整链路） | [ ] |
| D2 | 旧 `/webhook/events` route 是否保留 | 保留 vs 删除 | 保留（回滚安全） | [ ] |
| D3 | 测试 Issue 是否 archive | Archive vs 删除 | Archive（避免额外事件） | [ ] |
| D4 | 验证窗口期 | 15 分钟 vs 30 分钟 vs 1 小时 | 30 分钟（容错） | [ ] |

### 11.3 前置依赖清单

| 依赖 | 状态 | 备注 |
|------|------|------|
| OPS-LINEAR-005 验收通过 | [ ] 已完成 / [ ] 进行中 | shadow 部署验收是 dry-run 的前置 |
| n8n dry-run workflow 已导入 | [ ] 已完成 / [ ] 进行中 | 参见 OPS-LINEAR-006-n8n-dryrun-design.md |
| Dry-run nginx route 已配置 | [ ] 已完成 / [ ] 进行中 | `/webhook/linear-canonical-dryrun` |
| Linear API Token 可用 | [ ] 已获取 / [ ] 未获取 | 用于触发真实事件 |
| Linear Team ID (JTO) 已知 | [ ] 已获取 / [ ] 未获取 | 用于创建测试 Issue |
| Supabase DB URL 可用 | [ ] 已获取 / [ ] 未获取 | 用于 SQL 验证 |
| 1Password secret 可用 | [ ] 已获取 / [ ] 未获取 | LINEAR_WEBHOOK_SECRET |
| `branch-2` 已创建 | [ ] 已完成 / [ ] 未创建 | 按 Phase Git Convention |

---

## 十二、附录

### 12.1 关联文档

| 文档编号 | 文档名称 | 关系 |
|----------|----------|------|
| OPS-LINEAR-003 | Shadow 验收测试 | 前置基础 |
| OPS-LINEAR-004 | Shadow 部署记录 | 部署上下文 |
| OPS-LINEAR-005 | Shadow 验收报告 | 前置验收 |
| OPS-LINEAR-006-dryrun-acceptance-test-plan | Dry-run 测试用例 | 本文档的测试执行脚本 |
| OPS-LINEAR-006-n8n-dryrun-design | n8n dry-run 工作流设计 | Dry-run 消费端设计 |
| OPS-LINEAR-006-minimal-real-event-trigger-plan | 真实事件触发方案 | R11 的执行步骤 |
| OPS-LINEAR-006-dryrun-rollback-plan | 回滚预案 | 回滚策略 |
| OPS-LINEAR-005-acceptance-report-draft | OPS-LINEAR-005 报告模板 | 模板参考 |

### 12.2 证据文件清单

执行完成后，以下文件应作为证据附件：

| 文件名 | 内容 | 存放位置 |
|--------|------|---------|
| `evidence/health-check.json` | Health endpoint 响应 | `memory/evidence/OPS-LINEAR-006/` |
| `evidence/dt01-backward-compat.txt` | DT-01 curl 输出 | `memory/evidence/OPS-LINEAR-006/` |
| `evidence/dt02-shadow-accepted.json` | DT-02 响应体 | `memory/evidence/OPS-LINEAR-006/` |
| `evidence/supabase-three-tables.txt` | SQL-DT03 三表查询结果 | `memory/evidence/OPS-LINEAR-006/` |
| `evidence/dt04-n8n-canonical.json` | DT-04 n8n execution 输入 | `memory/evidence/OPS-LINEAR-006/` |
| `evidence/linear-issue-info.json` | 创建的临时 Issue 信息 | `memory/evidence/OPS-LINEAR-006/` |
| `evidence/idempotency-sql.txt` | 幂等 SQL 验证结果 | `memory/evidence/OPS-LINEAR-006/` |
| `evidence/redaction-check.txt` | 脱敏验证结果 | `memory/evidence/OPS-LINEAR-006/` |
| `evidence/no-production-actions.txt` | 生产隔离验证结果 | `memory/evidence/OPS-LINEAR-006/` |

---

**文档状态**：Template  
**审批人**：待定  
**下次评审日期**：执行后
