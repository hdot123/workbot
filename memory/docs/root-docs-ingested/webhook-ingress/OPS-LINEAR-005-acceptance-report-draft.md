# Linear Webhook Shadow Deployment Acceptance Report

> 文档编号：OPS-LINEAR-005  
> 版本：V1.0  
> 创建日期：2026-05-04  
> 维护人：[待填写]

---

## 一、执行摘要

### 1.1 验收结论

| 验收项 | 状态 | 备注 |
|--------|------|------|
| Shadow 部署 | [ ] 通过 / [ ] 未通过 | |
| 向后兼容 | [ ] 通过 / [ ] 未通过 | |
| n8n 隔离 | [ ] 通过 / [ ] 未通过 | |
| 数据存储 | [ ] 通过 / [ ] 未通过 | |
| 安全性 | [ ] 通过 / [ ] 未通过 | |

**总体结论**：[ ] 建议转入生产  /  [ ] 需要修复后复测  /  [ ] 建议回滚

---

## 二、方案决策：Option A/B/C

### 2.1 方案对比

| 维度 | Option A：直接替换 | Option B：影子模式 | Option C：双写模式 |
|------|-------------------|-------------------|-------------------|
| 实施复杂度 | 低 | 中 | 高 |
| 风险等级 | 高 | 低 | 中 |
| 验证能力 | 无 | 完整 | 部分 |
| 回滚难度 | 高 | 低 | 中 |
| 推荐度 | ❌ 不推荐 | ✅ 推荐 | ⚠️ 备选 |

### 2.2 本次部署选择

**选定方案**：Option B（影子模式 Shadow Mode）

**决策理由**：[待填写，如：1) 零风险验证新端点 2) 完整测试数据流 3) 保持生产稳定性]

### 2.3 未来切换计划

**暂不切产（No Cutover）**

- 当前阶段：纯影子验证
- 预计切产时间：[待填写]
- 切产前提条件：[待填写，如：1) 7天稳定运行 2) 1000+事件处理无异常 3) 告警系统就绪]

---

## 三、Shadow Webhook 配置

### 3.1 部署拓扑

```text
Cloudflare Tunnel
  -> n8n-webhook-gateway nginx
     -> GET  /healthz          -> n8n:5678/healthz
     -> POST /webhook/events   -> n8n:5678  (现有生产入口，未变更)
     -> POST /webhooks/linear  -> webhook-ingress-shadow:8000/webhooks/linear  (新增影子入口)
```

### 3.2 服务端配置

| 配置项 | 值 | 备注 |
|--------|-----|------|
| 部署节点 | `node-22` | |
| 容器名称 | `webhook-ingress-shadow` | |
| 镜像版本 | `webhook-ingress:phase1` | |
| 监听端口 | `127.0.0.1:5680 -> 8000` | 仅本地暴露 |
| 运行模式 | `WEBHOOK_INGRESS_MODE=shadow` | 关键配置 |
| 日志级别 | `WEBHOOK_LOG_LEVEL=INFO` | |

### 3.3 环境变量来源

| 变量名 | 来源 | 备注 |
|--------|------|------|
| `WEBHOOK_DATABASE_URL` | 1Password: `supabase-webhook数据库` | Item ID: `mgh2gmvw5w3kmjfhrcieoxfb54` |
| `LINEAR_WEBHOOK_SECRET` | 1Password: `linear-webhook-secret` | 实际值未记录 |
| `WEBHOOK_INGRESS_MODE` | 硬编码 `shadow` | 切产前改为 `production` |
| `WEBHOOK_LOG_LEVEL` | 硬编码 `INFO` | |

---

## 四、真实事件样本（脱敏处理）

### 4.1 样本来源

| 样本编号 | 来源 | 事件类型 | 采集时间 |
|----------|------|----------|----------|
| SAMPLE-001 | 模拟 Linear Payload | Issue.create | [待填写] |
| SAMPLE-002 | 模拟 Linear Payload | Issue.update | [待填写] |
| SAMPLE-003 | [待填写] | [待填写] | [待填写] |

### 4.2 脱敏规则

| 敏感字段 | 脱敏方式 | 示例 |
|----------|----------|------|
| `organizationId` | 替换为假名 | `org-real-xxx` → `org-test-001` |
| `actor.email` | 替换为测试邮箱 | `real@company.com` → `test@example.com` |
| `actor.id` | 替换为假名 | `user-real-xxx` → `user-test-001` |
| `data.id` | 替换为假名 | `issue-real-xxx` → `issue-test-001` |
| `Linear-Signature` | 日志中标记为 `[REDACTED]` | |

### 4.3 脱敏后样本示例

**原始事件类型**：Issue.create

**脱敏后 Payload**（SAMPLE-001）：

```json
{
  "type": "Issue",
  "action": "create",
  "organizationId": "[REDACTED-ORG]",
  "actor": {
    "id": "[REDACTED-USER]",
    "name": "[REDACTED-NAME]",
    "email": "[REDACTED]"
  },
  "data": {
    "id": "[REDACTED-ISSUE]",
    "identifier": "TEST-001",
    "title": "[示例标题 - 测试事件]",
    "description": "[REDACTED-CONTENT]",
    "url": "https://linear.app/[REDACTED]/issue/TEST-001",
    "createdAt": "2026-05-04T00:00:00.000Z",
    "updatedAt": "2026-05-04T00:00:00.000Z",
    "team": {
      "id": "[REDACTED-TEAM]",
      "name": "[REDACTED]"
    },
    "state": {
      "id": "[REDACTED-STATE]",
      "name": "Backlog"
    }
  }
}
```

---

## 五、Supabase 验证

### 5.1 数据库连接信息

| 项目 | 值 |
|------|-----|
| 服务 | Supabase PostgreSQL |
| Project Ref | `rxrcidmnbyvwmhxqdgku` |
| Project URL | `https://rxrcidmnbyvwmhxqdgku.supabase.co` |
| 凭据来源 | 1Password: `supabase-webhook数据库` |
| Item ID | `mgh2gmvw5w3kmjfhrcieoxfb54` |

### 5.2 表结构验证

迁移文件：`tools/webhook_ingress/migrations/001_supabase_webhook_events.sql`

| 表名 | 存在性 | 备注 |
|------|--------|------|
| `webhook_raw_events` | [ ] 已创建 / [ ] 不存在 | |
| `webhook_canonical_events` | [ ] 已创建 / [ ] 不存在 | |
| `webhook_processing_logs` | [ ] 已创建 / [ ] 不存在 | |

### 5.3 迁移执行记录

| 执行次数 | 执行时间 | 执行结果 | 执行人 |
|----------|----------|----------|--------|
| 第1次 | [待填写] | [ ] 成功 / [ ] 失败 | [待填写] |
| 第2次 | [待填写] | [ ] 成功 / [ ] 失败 | [待填写] |

**幂等性验证**：[待填写，如：迁移脚本支持幂等重复执行，多次执行结果一致]

### 5.4 数据写入验证

#### Raw Events 检查

```sql
SELECT
    event_id,
    provider,
    idempotency_key,
    raw_body_sha256,
    request_path,
    source_ip,
    received_at,
    created_at
FROM webhook_raw_events
WHERE provider = 'linear'
  AND created_at > NOW() - INTERVAL '1 hour'
ORDER BY created_at DESC
LIMIT 10;
```

**检查结果**：[待填写查询结果摘要]

#### Canonical Events 检查

```sql
SELECT
    event_id,
    provider_event_type,
    provider_action,
    canonical_type,
    canonical_action,
    idempotency_key,
    n8n_forwarded,
    created_at
FROM webhook_canonical_events
WHERE provider = 'linear'
  AND created_at > NOW() - INTERVAL '1 hour'
ORDER BY created_at DESC
LIMIT 10;
```

**检查结果**：[待填写查询结果摘要]

**关键指标**：

| 指标 | 预期值 | 实际值 | 状态 |
|------|--------|--------|------|
| 总事件数 | > 0 | [待填写] | [ ] 正常 / [ ] 异常 |
| n8n_forwarded = 1 | 0（shadow 模式） | [待填写] | [ ] 正常 / [ ] 异常 |
| n8n_forwarded = 0 | = 总事件数 | [待填写] | [ ] 正常 / [ ] 异常 |

#### Processing Logs 检查

```sql
SELECT
    event_id,
    phase,
    level,
    message,
    created_at
FROM webhook_processing_logs
WHERE provider = 'linear'
  AND created_at > NOW() - INTERVAL '1 hour'
ORDER BY created_at DESC
LIMIT 20;
```

**检查结果**：[待填写查询结果摘要]

---

## 六、幂等性重放验证

### 6.1 测试目标

验证重复事件不会导致重复入库或重复触发。

### 6.2 重放测试记录

| 测试编号 | 事件ID | 首次发送 | 重放次数 | 结果 |
|----------|--------|----------|----------|------|
| REPLAY-001 | [待填写] | [时间戳] | 2 | [ ] duplicate_accepted / [ ] 异常 |
| REPLAY-002 | [待填写] | [时间戳] | 5 | [ ] duplicate_accepted / [ ] 异常 |
| REPLAY-003 | [待填写] | [时间戳] | 10 | [ ] duplicate_accepted / [ ] 异常 |

### 6.3 SQL 去重验证

```sql
SELECT
    idempotency_key,
    COUNT(*) as count,
    MIN(event_id) as first_event_id,
    MAX(event_id) as last_event_id
FROM webhook_canonical_events
WHERE idempotency_key IN ('[待填写测试用的 key1]', '[key2]')
GROUP BY idempotency_key;
```

**预期**：每个 `idempotency_key` 的 `count = 1`

**实际结果**：[待填写]

### 6.4 幂等性机制说明

| 幂等键来源 | 优先级 | 示例 |
|------------|--------|------|
| `provider + delivery_id` | 优先 | `linear:tc06-delivery-dedup` |
| `provider + raw_body_sha256` | 备选 | `linear:sha256:abc123...` |

---

## 七、旧端点状态验证

### 7.1 现有生产端点

| 端点 | 状态 | 验证结果 |
|------|------|----------|
| `GET https://webhook.exa.edu.kg/healthz` | [ ] 200 OK / [ ] 异常 | [待填写] |
| `POST https://webhook.exa.edu.kg/webhook/events` | [ ] 200 OK / [ ] 异常 | [待填写] |

### 7.2 向后兼容性验证

**测试方法**：向旧 `/webhook/events` 端点发送测试事件

```bash
curl -s -X POST "https://webhook.exa.edu.kg/webhook/events" \
  -H "Content-Type: application/json" \
  -H "X-Linear-Signature: [有效签名]" \
  -d '{"test": "backward_compatibility_check", "timestamp": "[ISO8601]"}' \
  -w "\nHTTP_STATUS:%{http_code}\n"
```

**预期结果**：
- HTTP 状态码：200
- n8n Webhook Node 正常触发
- 原有 workflow 执行成功

**实际结果**：[待填写]

### 7.3 n8n Workflow 状态检查

| Workflow 名称 | 状态 | 执行记录 | 备注 |
|---------------|------|----------|------|
| [原有 workflow 名] | [ ] Active / [ ] Inactive | [待填写] | |

**结论**：旧端点 [ ] 完全正常 / [ ] 存在异常

---

## 八、n8n 隔离验证

### 8.1 隔离机制

`WEBHOOK_INGRESS_MODE=shadow` 模式下，服务行为：

| 行为 | Shadow 模式 | Production 模式 |
|------|-------------|-----------------|
| 接收并验证请求 | ✅ 是 | ✅ 是 |
| 存储到 Supabase | ✅ 是 | ✅ 是 |
| 返回 ACK | ✅ 是 | ✅ 是 |
| 转发到 n8n | ❌ 否 | ✅ 是 |

### 8.2 隔离验证方法

**测试窗口**：在 shadow 端点接收真实事件期间

**验证步骤**：
1. 记录测试开始时间
2. 向 `/webhooks/linear` 发送测试事件
3. 检查 n8n workflow 执行记录
4. 确认无新增 execution

### 8.3 隔离验证结果

| 测试事件数 | n8n 新增执行数 | 结论 |
|------------|----------------|------|
| [待填写] | [预期: 0] | [ ] 隔离成功 / [ ] 隔离失败 |

### 8.4 边界确认

| 检查项 | 预期 | 实际 | 状态 |
|--------|------|------|------|
| Shadow 事件不触发 n8n | 0 次 | [待填写] | |
| 旧端点事件正常触发 n8n | > 0 次 | [待填写] | |
| 无异常 n8n 调用日志 | 无 | [待填写] | |

---

## 九、日志脱敏验证

### 9.1 脱敏规则检查

| 敏感类型 | 脱敏方式 | 验证结果 |
|----------|----------|----------|
| Webhook Secret | 日志中替换为 `[REDACTED]` | [ ] 已脱敏 / [ ] 未脱敏 |
| 数据库 URL | 不打印完整连接串 | [ ] 已脱敏 / [ ] 未脱敏 |
| Service Role Key | 完全不出现在日志 | [ ] 已脱敏 / [ ] 未脱敏 |
| Authorization Token | 日志中替换为 `[REDACTED]` | [ ] 已脱敏 / [ ] 未脱敏 |
| Linear Signature | 日志中替换为 `[REDACTED]` | [ ] 已脱敏 / [ ] 未脱敏 |

### 9.2 日志采样检查

**检查命令**：

```bash
# Docker 日志
docker logs webhook-ingress-shadow --since "1 hour ago" 2>&1 | grep -E "(signature|secret|token|password|key)" -i

# 或 systemd 日志
journalctl -u webhook-ingress --since "1 hour ago" --no-pager | grep -E "(signature|secret|token|password|key)" -i
```

**检查结果**：[待填写，如：未发现明文 secret，所有敏感字段均已脱敏]

### 9.3 数据库中的敏感数据

**注意**：`webhook_raw_events.raw_headers` 字段以 JSONB 形式完整存储 headers，用于审计追溯。这是**预期行为**，不是安全问题。

数据库访问控制：
- 仅 service_role 可写
- 应用连接使用专用凭据
- 凭据存储于 1Password

---

## 十、回滚方案

### 10.1 回滚触发条件

| 条件 | 触发动作 |
|------|----------|
| 旧 endpoint 不可达 | 立即回滚 |
| 无效签名未被拒绝 | 立即回滚（安全风险） |
| n8n 被意外调用 | 立即检查并回滚 |
| Supabase 写入失败 | 检查数据库连接，必要时回滚 |
| 其他严重异常 | 根据具体情况判断 |

### 10.2 回滚步骤

#### 步骤 1：恢复 nginx 配置

```bash
cd /opt/n8n-linear/nginx

# 恢复备份（根据实际时间戳）
cp webhook-gateway.conf.bak-<timestamp> webhook-gateway.conf

# 验证配置
docker exec n8n-webhook-gateway nginx -t

# 重载 nginx
docker restart n8n-webhook-gateway
```

#### 步骤 2：停止 Shadow 服务

```bash
# Docker 方式
docker rm -f webhook-ingress-shadow

# Systemd 方式（如适用）
sudo systemctl stop webhook-ingress
sudo systemctl disable webhook-ingress
```

#### 步骤 3：清理（可选）

```bash
rm -rf /opt/webhook-ingress
```

#### 步骤 4：验证回滚

```bash
# 验证旧端点仍可用
curl -s -o /dev/null -w '%{http_code}\n' \
  -X POST "https://webhook.exa.edu.kg/webhook/events" \
  -H "Content-Type: application/json" \
  -d '{"rollback_verification": true}'
# 预期: 200

# 验证 Shadow 端点已不可用
curl -s -o /dev/null -w '%{http_code}\n' \
  -X POST "https://webhook.exa.edu.kg/webhooks/linear"
# 预期: 404 或 502
```

### 10.3 回滚验证清单

| 检查项 | 预期结果 | 验证方式 |
|--------|----------|----------|
| 旧 `/webhook/events` 可达 | HTTP 200 | curl 测试 |
| 旧 n8n workflow 可触发 | 新增 execution | n8n UI 检查 |
| Shadow 端点不可达 | 404/502 | curl 测试 |
| n8n 容器运行正常 | Up | `docker ps` |
| nginx 配置有效 | syntax ok | `nginx -t` |

---

## 十一、不切产声明

### 11.1 当前阶段结论

**本次部署为纯影子验证阶段，不进行生产切换。**

### 11.2 不切产理由

| 理由 | 说明 |
|------|------|
| 1. 需要观察期 | 建议运行 [待填写，如：7天] 观察稳定性 |
| 2. 数据积累不足 | 当前处理事件数：[待填写]，建议达到 [待填写，如：1000+] 后再评估 |
| 3. 告警系统待完善 | 生产监控和告警尚未就绪 |
| 4. n8n canonical workflow 未就绪 | 消费 canonical events 的 workflow 尚未部署 |
| 5. 其他 | [待填写] |

### 11.3 切产前置条件

| 条件 | 状态 | 预计完成时间 |
|------|------|--------------|
| Shadow 模式稳定运行 [待填写] 天 | [ ] 已满足 / [ ] 进行中 | |
| 处理 [待填写] 个真实事件无异常 | [ ] 已满足 / [ ] 进行中 | |
| 告警系统部署完成 | [ ] 已满足 / [ ] 进行中 | |
| Canonical Events Workflow 就绪 | [ ] 已满足 / [ ] 进行中 | |
| 回滚方案演练通过 | [ ] 已满足 / [ ] 进行中 | |

### 11.4 切产计划

**预计切产时间**：[待填写]

**切产步骤预览**：

1. 部署 canonical events n8n workflow
2. 将 `WEBHOOK_INGRESS_MODE` 改为 `production`
3. 在 Linear Settings 中修改 Webhook URL 从 `/webhook/events` 到 `/webhooks/linear`
4. 保持旧 `/webhook/events` 可用 [待填写，如：24小时] 作为回滚窗口
5. 监控切换后的事件流

---

## 十二、问题与风险

### 12.1 发现的问题

| 编号 | 问题描述 | 严重程度 | 状态 | 跟踪人 |
|------|----------|----------|------|--------|
| ISSUE-001 | [待填写] | [ ] 高 / [ ] 中 / [ ] 低 | [ ] 已解决 / [ ] 待修复 | |

### 12.2 风险清单

| 编号 | 风险描述 | 概率 | 影响 | 缓解措施 |
|------|----------|------|------|----------|
| RISK-001 | Shadow 模式配置意外改为 production | 低 | 高 | 配置审计 + 告警 |
| RISK-002 | Supabase 连接中断 | 中 | 中 | 重试机制 + 队列 |
| RISK-003 | 签名验证算法变更 | 低 | 高 | 监控失败率 + 告警 |

---

## 十三、附录

### 13.1 参考文档

| 文档编号 | 文档名称 | 关系说明 |
|----------|----------|----------|
| OPS-LINEAR-002 | Linear Webhook 验收清单 | 整体验收标准 |
| OPS-LINEAR-003 | Shadow Webhook 验收测试 | 详细测试用例 |
| OPS-LINEAR-004 | Shadow 部署记录 | 部署过程记录 |
| OPS-LINEAR-005 | 本报告 | 验收报告 |
| standard-webhook-ingress-phase1 | Phase 1 规范 | 技术规范 |

### 13.2 执行团队

| 角色 | 姓名 | 职责 |
|------|------|------|
| 执行人 | [待填写] | 部署和测试执行 |
| 审核人 | [待填写] | 报告审核 |
| 批准人 | [待填写] | 切产批准 |

### 13.3 执行时间

| 阶段 | 开始时间 | 结束时间 | 耗时 |
|------|----------|----------|------|
| 部署 | [待填写] | [待填写] | |
| 测试 | [待填写] | [待填写] | |
| 验证 | [待填写] | [待填写] | |
| 报告编写 | [待填写] | [待填写] | |

---

**文档状态**：草稿中  
**审批人**：[待填写]  
**下次评审日期**：[待填写]
