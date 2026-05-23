# Linear Shadow Webhook 验收测试计划

> 文档编号：OPS-LINEAR-003  
> 版本：V1.0  
> 创建日期：2026-05-04  
> 维护人：bailian-worker  

---

## 一、测试目标

验证部署在 `https://webhook.exa.edu.kg/webhooks/linear` 的 shadow endpoint 满足以下要求：

1. **向后兼容**：旧 `/webhook/events` 路径仍然正常工作（n8n 原有 workflow 不受影响）
2. **正常接受**：新 endpoint 对有效模拟 Linear payload 返回 `accepted`
3. **签名拒绝**：对无效签名返回 `SIGNATURE_INVALID`
4. **去重**：对重复 delivery 返回 `duplicate_accepted`
5. **存储**：Supabase `webhook_raw_events` / `webhook_canonical_events` / `webhook_processing_logs` 正确写入
6. **n8n 隔离**：n8n production workflow 未被调用 / 不受影响

**约束**：以下测试为只读规划，不修改服务器配置。所有 secret 使用占位符。

---

## 二、环境准备

### 2.1 前提条件

| 条件 | 检查方法 | 预期 |
|------|---------|------|
| Shadow server 在 node-22 运行 | `curl -s https://webhook.exa.edu.kg/health` | `{"status":"ok","mode":"shadow"}` |
| Supabase 数据库连接正常 | 连接检查（见 SQL 检查部分） | 表 `webhook_raw_events` / `webhook_canonical_events` / `webhook_processing_logs` 存在 |
| 旧 `/webhook/events` n8n workflow 仍在运行 | 在 n8n UI 检查原有 workflow 状态 | Active / Production |
| Shadow mode = `shadow` | 检查环境变量 `WEBHOOK_INGRESS_MODE=shadow` | 不转发到 n8n |

### 2.2 测试变量（占位符）

```bash
# ===== 以下变量在执行时替换为实际值 =====
SHADOW_BASE="https://webhook.exa.edu.kg"
SHADOW_PATH="/webhooks/linear"
SHADOW_URL="${SHADOW_BASE}${SHADOW_PATH}"
SECRET="<LINEAR_WEBHOOK_SECRET_FROM_1PASSWORD>"
N8N_OLD_WEBHOOK_URL="<旧 webhook/events 的 n8n URL>"
SUPABASE_DB_URL="<supabase-service-role-connection-string>"

# 测试用 delivery ID（每次测试使用不同值）
DELIVERY_VALID="test-delivery-$(date +%s)"
DELIVERY_DUPLICATE="$DELIVERY_VALID"  # 与上一条相同
```

### 2.3 模拟 Linear Payload

```json
{
  "type": "Issue",
  "action": "update",
  "organizationId": "org-test-001",
  "actor": {
    "id": "user-test-001",
    "name": "Test User",
    "email": "test@example.com"
  },
  "data": {
    "id": "issue-test-001",
    "identifier": "TST-001",
    "title": "Shadow Acceptance Test Issue",
    "description": "Auto-generated test issue",
    "url": "https://linear.app/test/issue/TST-001",
    "createdAt": "2026-05-04T00:00:00.000Z",
    "updatedAt": "2026-05-04T00:01:00.000Z",
    "team": {
      "id": "team-test-001",
      "name": "Test Team"
    },
    "state": {
      "id": "state-test-001",
      "name": "Backlog"
    }
  }
}
```

### 2.4 签名计算方法

```bash
# Linear 使用 HMAC-SHA256，签名 header 为 X-Linear-Signature（或 Linear-Signature）
# 签名基于原始请求体（raw body bytes），不是 JSON re-serialize

# Python 计算签名：
import hmac, hashlib, json
payload = <上述 JSON>
body = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
sig = hmac.new(SECRET.encode(), body, hashlib.sha256).hexdigest()

# curl 计算（使用 openssl）：
BODY='{"action":"update","data":{"createdAt":"2026-05-04T00:00:00.000Z","description":"Auto-generated test issue","id":"issue-test-001","identifier":"TST-001","state":{"id":"state-test-001","name":"Backlog"},"team":{"id":"team-test-001","name":"Test Team"},"title":"Shadow Acceptance Test Issue","updatedAt":"2026-05-04T00:01:00.000Z","url":"https://linear.app/test/issue/TST-001"},"organizationId":"org-test-001","type":"Issue"}'
SIG=$(echo -n "$BODY" | openssl dgst -sha256 -hmac "$SECRET" | awk '{print $NF}')
```

> **注意**：Linear 的签名基于**原始 HTTP body**（发送时 exactly 的 bytes）。  
> 如果用 `json.dumps(payload, separators=(",", ":"), sort_keys=True)` 计算，确保 curl 发送的 body 与计算时完全一致（无额外空格/换行）。

---

## 三、测试用例

### TC-01: 健康检查

**目的**：验证 shadow endpoint 服务正常运行  
**命令**：

```bash
curl -s https://webhook.exa.edu.kg/health
```

**预期响应**：

```json
{
  "status": "ok",
  "mode": "shadow"
}
```

**预期 HTTP 状态**：`200`

---

### TC-02: 旧 /webhook/events 向后兼容

**目的**：验证旧 n8n webhook 路径仍正常工作，不受新 shadow endpoint 影响  
**前提**：旧 webhook URL 仍然有效

**命令**：

```bash
curl -s -X POST "<N8N_OLD_WEBHOOK_URL>" \
  -H "Content-Type: application/json" \
  -d '{"test": "backward_compatibility_check", "timestamp": "'$(date -u +%Y-%m-%dT%H:%M:%SZ)'"}' \
  -w "\nHTTP_STATUS:%{http_code}\n"
```

**预期 HTTP 状态**：`200`（n8n Webhook 节点返回）  
**验证**：
- 在 n8n UI 中确认旧 workflow 的 execution 记录中新增了一条
- 确认旧 workflow 未因 shadow endpoint 部署而被禁用/修改

---

### TC-03: 有效签名 → accepted

**目的**：验证正常 Linear payload 被正确接受  
**步骤**：

```bash
# 1. 构造 payload（使用紧凑 JSON，无额外空格）
BODY='{"action":"create","data":{"id":"issue-tc03","identifier":"TST-TC03","title":"TC03 Test Issue","description":"Test for accepted","url":"https://linear.app/test/issue/TST-TC03","createdAt":"2026-05-04T00:00:00.000Z","updatedAt":"2026-05-04T00:00:00.000Z","team":{"id":"team-tc03"},"state":{"name":"Triaged"},"user":{"id":"user-tc03","name":"Tester","email":"test@example.com"}},"organizationId":"org-tc03","type":"Issue"}'

# 2. 计算签名
SIG=$(echo -n "$BODY" | openssl dgst -sha256 -hmac "$SECRET" | awk '{print $NF}')

# 3. 发送请求（带上唯一 delivery ID）
curl -sv -X POST "$SHADOW_URL" \
  -H "Content-Type: application/json" \
  -H "X-Linear-Signature: $SIG" \
  -H "Linear-Delivery: tc03-delivery-001" \
  -d "$BODY" \
  -w "\n\nHTTP_STATUS:%{http_code}\n" 2>/tmp/tc03_debug.log
```

**预期 HTTP 状态**：`200`

**预期响应体**：

```json
{
  "ok": true,
  "status": "accepted",
  "request_id": "req_<uuid>",
  "event_id": "evt_<uuid>",
  "provider": "linear"
}
```

> **注意**：Shadow mode 下 `Response` 不返回 body（server.py 中 `content=None`）。  
> 但 ingress `IngressResult.ack` 内部状态应为 `accepted`，并记录在日志中。  
> 如果需要验证 ACK body，检查 server 日志中的 `webhook result status=200` 行。

**验证**：

```bash
# 检查服务端日志
cat /tmp/tc03_debug.log | grep -i "status=200\|accepted"

# 或检查 systemd/docker 日志（根据实际部署方式）
journalctl -u webhook-ingress --since "2 min ago" --no-pager | grep -i "accepted"
```

---

### TC-04: 无效签名 → SIGNATURE_INVALID

**目的**：验证错误签名被正确拒绝  
**步骤**：

```bash
BODY='{"action":"update","data":{"id":"issue-tc04"},"type":"Issue"}'

curl -sv -X POST "$SHADOW_URL" \
  -H "Content-Type: application/json" \
  -H "X-Linear-Signature: 0000000000000000000000000000000000000000000000000000000000000000" \
  -H "Linear-Delivery: tc04-delivery-001" \
  -d "$BODY" \
  -w "\n\nHTTP_STATUS:%{http_code}\n" 2>/tmp/tc04_debug.log
```

**预期 HTTP 状态**：`401`

**预期响应**：
- 无 body（shadow server `content=None`）
- 日志中应出现 `status=401` 和 `SIGNATURE_INVALID`

**验证**：

```bash
# 检查日志中记录了签名校验失败
journalctl -u webhook-ingress --since "2 min ago" --no-pager | grep -i "SIGNATURE_INVALID\|WARN.*signature"
```

---

### TC-05: 缺少签名 → SIGNATURE_INVALID

**目的**：验证缺少签名 header 被正确拒绝  
**步骤**：

```bash
BODY='{"action":"update","data":{"id":"issue-tc05"},"type":"Issue"}'

curl -sv -X POST "$SHADOW_URL" \
  -H "Content-Type: application/json" \
  -H "Linear-Delivery: tc05-delivery-001" \
  -d "$BODY" \
  -w "\n\nHTTP_STATUS:%{http_code}\n" 2>/tmp/tc05_debug.log
```

**预期 HTTP 状态**：`401`

---

### TC-06: 重复事件 → duplicate_accepted

**目的**：验证幂等去重机制正常工作  
**步骤**：

```bash
# 第一次发送（使用固定 delivery ID）
BODY='{"action":"update","data":{"id":"issue-tc06","identifier":"TST-TC06","title":"TC06 Dedup Test","description":"Dedup test","url":"https://linear.app/test/issue/TST-TC06","createdAt":"2026-05-04T00:00:00.000Z","updatedAt":"2026-05-04T00:01:00.000Z","team":{"id":"team-tc06"},"state":{"name":"Backlog"},"user":{"id":"user-tc06","name":"Tester","email":"test@example.com"}},"organizationId":"org-tc06","type":"Issue"}'
SIG=$(echo -n "$BODY" | openssl dgst -sha256 -hmac "$SECRET" | awk '{print $NF}')

echo "=== First send ==="
curl -s -X POST "$SHADOW_URL" \
  -H "Content-Type: application/json" \
  -H "X-Linear-Signature: $SIG" \
  -H "Linear-Delivery: tc06-delivery-dedup" \
  -d "$BODY" \
  -w "\nHTTP_STATUS:%{http_code}\n"

sleep 1

echo "=== Second send (duplicate) ==="
curl -s -X POST "$SHADOW_URL" \
  -H "Content-Type: application/json" \
  -H "X-Linear-Signature: $SIG" \
  -H "Linear-Delivery: tc06-delivery-dedup" \
  -d "$BODY" \
  -w "\nHTTP_STATUS:%{http_code}\n"
```

**预期**：

| 发送次数 | HTTP 状态 | 内部 ack status |
|---------|----------|-----------------|
| 第一次 | `200` | `accepted` |
| 第二次（相同 delivery ID） | `200` | `duplicate_accepted` |

**验证**：

```bash
# 检查日志中两次发送的不同 status
journalctl -u webhook-ingress --since "3 min ago" --no-pager | grep "tc06-delivery-dedup\|accepted"
```

---

### TC-07: 非 POST 方法 → 405

**目的**：验证非 POST 请求被拒绝  
**步骤**：

```bash
curl -sv -X GET "$SHADOW_URL" -w "\nHTTP_STATUS:%{http_code}\n"
```

**预期 HTTP 状态**：`405`（FastAPI 默认行为）或 `404`

---

### TC-08: 错误 Content-Type → 仍可处理

**目的**：验证即使没有 Content-Type，只要有正确 body 和签名，仍能处理  
**步骤**：

```bash
BODY='{"action":"update","data":{"id":"issue-tc08"},"type":"Issue"}'
SIG=$(echo -n "$BODY" | openssl dgst -sha256 -hmac "$SECRET" | awk '{print $NF}')

curl -sv -X POST "$SHADOW_URL" \
  -H "X-Linear-Signature: $SIG" \
  -H "Linear-Delivery: tc08-delivery-001" \
  -d "$BODY" \
  -w "\nHTTP_STATUS:%{http_code}\n"
```

**预期 HTTP 状态**：`200`（ingress 不强制校验 Content-Type）

---

### TC-09: 大 Payload → 正常处理

**目的**：验证较大 Linear payload（含长描述/多字段）正常处理  
**步骤**：构造一个约 10KB 的 payload，包含长 description 和嵌套字段，计算签名后发送。

**预期 HTTP 状态**：`200`，ack status = `accepted`

---

### TC-10: n8n Production Workflow 未被调用（Shadow Mode 验证）

**目的**：验证 shadow mode 下事件不会转发到 n8n  
**步骤**：

1. 在 n8n UI 中记录当前 time
2. 执行 TC-03（发送有效事件到 shadow endpoint）
3. 检查 n8n 的 canonical-events webhook workflow execution 记录

**验证**：

```bash
# 在 n8n UI 中检查：
# 1. 进入 n8n > Workflows > "Canonical Events" (或对应的 production workflow)
# 2. 查看 Executions 面板
# 3. 确认在 TC-03 发送后，没有新的 execution 记录

# 或通过 n8n API 检查（需要认证）
curl -s "https://<n8n-admin-url>/api/v1/executions?workflowId=<workflow-id>&startDateTime=<TC-03-time-before>" \
  -u "<n8n-username>:<n8n-password>" | python3 -m json.tool
```

**预期**：在 TC-03 执行后，n8n production workflow 没有新增 execution 记录。

---

## 四、Supabase SQL 检查

### 4.1 连接 Supabase

```bash
# 使用 psql 连接（需要 service_role key 或专用服务端角色）
# 连接字符串来自 1Password: supabase-webhook数据库 (id: mgh2gmvw5w3kmjfhrcieoxfb54)
psql "<SUPABASE_DB_URL>"
```

### 4.2 SQL-01: 验证 raw event 写入

```sql
-- 检查最近 5 分钟的 raw events
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
  AND created_at > NOW() - INTERVAL '5 minutes'
ORDER BY created_at DESC
LIMIT 10;
```

**预期**：TC-03 和 TC-06 第一次发送对应的行应存在，`request_path` = `/webhooks/linear`。

### 4.3 SQL-02: 验证 canonical event 写入

```sql
-- 检查最近 5 分钟的 canonical events
SELECT
    event_id,
    provider,
    provider_event_type,
    provider_action,
    canonical_type,
    canonical_action,
    canonical_version,
    idempotency_key,
    source_resource_id,
    n8n_forwarded,
    created_at
FROM webhook_canonical_events
WHERE provider = 'linear'
  AND created_at > NOW() - INTERVAL '5 minutes'
ORDER BY created_at DESC
LIMIT 10;
```

**预期**：
- TC-03 对应的 canonical event 存在，`n8n_forwarded` = `0`（shadow mode）
- `canonical_type` = `issue`，`canonical_action` = `created`
- `idempotency_key` = `linear:tc03-delivery-001`
- TC-06 只有一条 canonical event（去重后不插入第二条）

### 4.4 SQL-03: 验证 processing logs 写入

```sql
-- 检查最近 5 分钟的 processing logs
SELECT
    event_id,
    provider,
    phase,
    level,
    message,
    details,
    created_at
FROM webhook_processing_logs
WHERE provider = 'linear'
  AND created_at > NOW() - INTERVAL '5 minutes'
ORDER BY created_at DESC
LIMIT 20;
```

**预期**：
- TC-03（成功）：`phase=store, level=INFO, message='raw and canonical event stored'`；`phase=route` 不应存在（shadow mode 不转发）
- TC-04（签名失败）：`phase=signature, level=WARN, message` 包含 `invalid Linear-Signature`
- TC-06（去重）：`phase=idempotency, level=INFO, message='duplicate accepted'`

### 4.5 SQL-04: 验证去重 — 相同 idempotency_key 只有一条

```sql
-- 验证 TC-06 去重：相同 idempotency_key 只有一条记录
SELECT
    idempotency_key,
    COUNT(*) as count,
    MIN(event_id) as first_event_id,
    MAX(event_id) as last_event_id
FROM webhook_canonical_events
WHERE idempotency_key = 'linear:tc06-delivery-dedup'
GROUP BY idempotency_key;
```

**预期**：`count = 1`，只有一条记录。

### 4.6 SQL-05: 验证 n8n_forwarded 标志

```sql
-- Shadow mode 下所有 canonical event 的 n8n_forwarded 应为 0
SELECT
    COUNT(*) as total_events,
    SUM(CASE WHEN n8n_forwarded = 0 THEN 1 ELSE 0 END) as not_forwarded,
    SUM(CASE WHEN n8n_forwarded = 1 THEN 1 ELSE 0 END) as forwarded
FROM webhook_canonical_events
WHERE provider = 'linear'
  AND created_at > NOW() - INTERVAL '5 minutes';
```

**预期**：`total_events = not_forwarded`，`forwarded = 0`。

### 4.7 SQL-06: 验证 raw_headers 脱敏

```sql
-- 检查 raw_headers 中是否包含明文 secret
SELECT
    event_id,
    raw_headers::text
FROM webhook_raw_events
WHERE provider = 'linear'
  AND created_at > NOW() - INTERVAL '5 minutes'
ORDER BY created_at DESC
LIMIT 1;
```

**预期**：`raw_headers` 中 `Linear-Signature` 或 `X-Linear-Signature` 的值应被记录，但日志输出中应被脱敏。数据库中的 raw_headers 是完整 header 的 JSONB 存储（用于审计），这不是问题——关键在于**日志输出**中的脱敏。

---

## 五、回滚检查

### 5.1 回滚触发条件

| 条件 | 触发动作 |
|------|---------|
| TC-02 失败（旧 endpoint 不可达） | 立即回滚，检查 n8n 容器状态和 nginx 配置 |
| TC-04 失败（无效签名未被拒绝） | 立即回滚，安全风险 |
| TC-10 失败（n8n 被意外调用） | 确认是否为误判；若确认被调用，立即检查 WEBHOOK_INGRESS_MODE |
| Supabase 表不存在或写入失败 | 检查数据库连接和迁移状态 |

### 5.2 回滚步骤

```bash
# 1. 停止 shadow server（根据实际部署方式）
# Systemd 方式：
sudo systemctl stop webhook-ingress

# Docker 方式：
docker stop webhook-ingress

# 2. 验证旧 /webhook/events 仍然工作
curl -s -X POST "<N8N_OLD_WEBHOOK_URL>" \
  -H "Content-Type: application/json" \
  -d '{"rollback_test": true}' \
  -w "\nHTTP_STATUS:%{http_code}\n"

# 预期：200

# 3. 如果 nginx 配置了 /webhooks/linear 路由，回滚 nginx
# 编辑 /etc/nginx/sites-available/webhook.exa.edu.kg
# 注释掉或删除 /webhooks/linear 的 location block
# 然后重新加载 nginx
sudo nginx -t && sudo systemctl reload nginx

# 4. 验证旧 endpoint 恢复
curl -s -o /dev/null -w "%{http_code}" -X POST "<N8N_OLD_WEBHOOK_URL>"
```

### 5.3 回滚后验证

```bash
echo "=== 回滚验证 ==="
echo "1. Shadow endpoint 不可达:"
curl -s -o /dev/null -w "%{http_code}" "https://webhook.exa.edu.kg/webhooks/linear"
# 预期: 404 或 502

echo "2. 旧 n8n webhook 仍可用:"
curl -s -o /dev/null -w "%{http_code}" -X POST "<N8N_OLD_WEBHOOK_URL>"
# 预期: 200

echo "3. n8n 容器正常运行:"
docker ps --filter name=n8n --format "table {{.Names}}\t{{.Status}}"
# 预期: n8n 状态为 Up

echo "4. nginx 配置正常:"
sudo nginx -t
# 预期: syntax is ok, test is successful
```

---

## 六、完整测试执行脚本

```bash
#!/bin/bash
# Linear Shadow Webhook 验收测试执行脚本
# 使用方法：
#   export LINEAR_WEBHOOK_SECRET="<从1Password获取>"
#   export N8N_OLD_WEBHOOK_URL="<旧 webhook URL>"
#   export SUPABASE_DB_URL="<Supabase 连接字符串>"
#   bash docs/webhook-ingress/OPS-LINEAR-003-execute-tests.sh

set -euo pipefail

SHADOW_BASE="https://webhook.exa.edu.kg"
SHADOW_PATH="/webhooks/linear"
SHADOW_URL="${SHADOW_BASE}${SHADOW_PATH}"
SECRET="${LINEAR_WEBHOOK_SECRET:?Please set LINEAR_WEBHOOK_SECRET}"
N8N_OLD="${N8N_OLD_WEBHOOK_URL:?Please set N8N_OLD_WEBHOOK_URL}"
PASS=0
FAIL=0
TOTAL=0

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log() {
    echo -e "${YELLOW}[$(date -u +%H:%M:%S)]${NC} $*"
}

pass() {
    PASS=$((PASS + 1))
    TOTAL=$((TOTAL + 1))
    echo -e "  ${GREEN}✅ PASS${NC}"
}

fail() {
    FAIL=$((FAIL + 1))
    TOTAL=$((TOTAL + 1))
    echo -e "  ${RED}❌ FAIL${NC}: $*"
}

compute_sig() {
    echo -n "$1" | openssl dgst -sha256 -hmac "$SECRET" | awk '{print $NF}'
}

echo "============================================"
echo "Linear Shadow Webhook 验收测试"
echo "============================================"
echo "Shadow URL: $SHADOW_URL"
echo "时间: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo ""

# --- TC-01: 健康检查 ---
log "TC-01: 健康检查"
HEALTH=$(curl -sf "$SHADOW_BASE/health" 2>/dev/null || echo "")
if echo "$HEALTH" | grep -q '"status".*"ok"'; then
    MODE=$(echo "$HEALTH" | grep -o '"mode"[^,}]*' | head -1)
    log "  响应: $HEALTH"
    if echo "$MODE" | grep -q '"shadow"'; then
        pass
    else
        fail "mode 不是 shadow: $MODE"
    fi
else
    fail "健康检查失败"
fi

# --- TC-02: 旧 /webhook/events 向后兼容 ---
log "TC-02: 旧 /webhook/events 向后兼容"
OLD_CODE=$(curl -s -o /dev/null -w "%{http_code}" \
    -X POST "$N8N_OLD" \
    -H "Content-Type: application/json" \
    -d '{"test":"backward_compat","ts":"'$(date -u +%Y-%m-%dT%H:%M:%SZ)'"}' \
    --max-time 10 2>/dev/null || echo "000")
if [ "$OLD_CODE" = "200" ]; then
    pass
else
    fail "旧 endpoint 返回 $OLD_CODE，期望 200"
fi

# --- TC-03: 有效签名 → accepted ---
log "TC-03: 有效签名 → accepted"
TC03_BODY='{"action":"create","data":{"id":"issue-tc03","identifier":"TST-TC03","title":"TC03 Test Issue","description":"Test for accepted","url":"https://linear.app/test/issue/TST-TC03","createdAt":"2026-05-04T00:00:00.000Z","updatedAt":"2026-05-04T00:00:00.000Z","team":{"id":"team-tc03"},"state":{"name":"Triaged"},"user":{"id":"user-tc03","name":"Tester","email":"test@example.com"}},"organizationId":"org-tc03","type":"Issue"}'
TC03_SIG=$(compute_sig "$TC03_BODY")
TC03_CODE=$(curl -s -o /dev/null -w "%{http_code}" \
    -X POST "$SHADOW_URL" \
    -H "Content-Type: application/json" \
    -H "X-Linear-Signature: $TC03_SIG" \
    -H "Linear-Delivery: tc03-delivery-001" \
    -d "$TC03_BODY" \
    --max-time 10 2>/dev/null || echo "000")
if [ "$TC03_CODE" = "200" ]; then
    pass
else
    fail "返回 $TC03_CODE，期望 200"
fi

# --- TC-04: 无效签名 → SIGNATURE_INVALID ---
log "TC-04: 无效签名 → 401"
TC04_BODY='{"action":"update","data":{"id":"issue-tc04"},"type":"Issue"}'
TC04_CODE=$(curl -s -o /dev/null -w "%{http_code}" \
    -X POST "$SHADOW_URL" \
    -H "Content-Type: application/json" \
    -H "X-Linear-Signature: 0000000000000000000000000000000000000000000000000000000000000000" \
    -H "Linear-Delivery: tc04-delivery-001" \
    -d "$TC04_BODY" \
    --max-time 10 2>/dev/null || echo "000")
if [ "$TC04_CODE" = "401" ]; then
    pass
else
    fail "返回 $TC04_CODE，期望 401"
fi

# --- TC-05: 缺少签名 → 401 ---
log "TC-05: 缺少签名 → 401"
TC05_BODY='{"action":"update","data":{"id":"issue-tc05"},"type":"Issue"}'
TC05_CODE=$(curl -s -o /dev/null -w "%{http_code}" \
    -X POST "$SHADOW_URL" \
    -H "Content-Type: application/json" \
    -H "Linear-Delivery: tc05-delivery-001" \
    -d "$TC05_BODY" \
    --max-time 10 2>/dev/null || echo "000")
if [ "$TC05_CODE" = "401" ]; then
    pass
else
    fail "返回 $TC05_CODE，期望 401"
fi

# --- TC-06: 重复事件 → duplicate_accepted ---
log "TC-06: 重复事件去重"
TC06_BODY='{"action":"update","data":{"id":"issue-tc06","identifier":"TST-TC06","title":"TC06 Dedup Test","description":"Dedup test","url":"https://linear.app/test/issue/TST-TC06","createdAt":"2026-05-04T00:00:00.000Z","updatedAt":"2026-05-04T00:01:00.000Z","team":{"id":"team-tc06"},"state":{"name":"Backlog"},"user":{"id":"user-tc06","name":"Tester","email":"test@example.com"}},"organizationId":"org-tc06","type":"Issue"}'
TC06_SIG=$(compute_sig "$TC06_BODY")

FIRST_CODE=$(curl -s -o /dev/null -w "%{http_code}" \
    -X POST "$SHADOW_URL" \
    -H "Content-Type: application/json" \
    -H "X-Linear-Signature: $TC06_SIG" \
    -H "Linear-Delivery: tc06-delivery-dedup" \
    -d "$TC06_BODY" \
    --max-time 10 2>/dev/null || echo "000")

sleep 1

SECOND_CODE=$(curl -s -o /dev/null -w "%{http_code}" \
    -X POST "$SHADOW_URL" \
    -H "Content-Type: application/json" \
    -H "X-Linear-Signature: $TC06_SIG" \
    -H "Linear-Delivery: tc06-delivery-dedup" \
    -d "$TC06_BODY" \
    --max-time 10 2>/dev/null || echo "000")

if [ "$FIRST_CODE" = "200" ] && [ "$SECOND_CODE" = "200" ]; then
    log "  第一次: $FIRST_CODE, 第二次: $SECOND_CODE"
    log "  注意：请在 Supabase 中验证第一次返回 accepted，第二次返回 duplicate_accepted"
    log "  运行 SQL-04 验证"
    pass
else
    fail "第一次=$FIRST_CODE, 第二次=$SECOND_CODE，期望均为 200"
fi

# --- TC-07: 非 POST 方法 → 405 ---
log "TC-07: GET 方法 → 405"
TC07_CODE=$(curl -s -o /dev/null -w "%{http_code}" \
    -X GET "$SHADOW_URL" \
    --max-time 10 2>/dev/null || echo "000")
if [ "$TC07_CODE" = "405" ] || [ "$TC07_CODE" = "404" ]; then
    pass
else
    fail "返回 $TC07_CODE，期望 405 或 404"
fi

# --- TC-10: n8n 未被调用（手动验证） ---
log "TC-10: n8n Production Workflow 未被调用"
log "  ⚠️  请手动在 n8n UI 中验证："
log "  1. 进入 Workflows > Canonical Events (或生产 workflow)"
log "  2. 查看 Executions 面板"
log "  3. 确认 TC-03 发送后没有新增 execution"
log "  4. 如果通过，标记为 PASS"
echo ""
read -p "  TC-10 是否通过？(y/n): " TC10_ANSWER
if [ "$TC10_ANSWER" = "y" ]; then
    pass
else
    fail "n8n 可能被意外调用"
fi

# --- 汇总 ---
echo ""
echo "============================================"
echo "测试汇总"
echo "============================================"
echo -e "总计: $TOTAL"
echo -e "${GREEN}通过: $PASS${NC}"
echo -e "${RED}失败: $FAIL${NC}"
echo ""

if [ "$FAIL" -gt 0 ]; then
    echo -e "${RED}❌ 测试未通过，请检查失败项${NC}"
    exit 1
else
    echo -e "${GREEN}✅ 所有测试通过${NC}"
    echo ""
    echo "下一步：运行 Supabase SQL 检查（SQL-01 到 SQL-06）"
    echo "命令：psql \"$SUPABASE_DB_URL\" -f docs/webhook-ingress/OPS-LINEAR-003-sql-checks.sql"
fi
```

---

## 七、Supabase SQL 检查脚本

```sql
-- OPS-LINEAR-003-sql-checks.sql
-- 使用方法：psql "<SUPABASE_DB_URL>" -f OPS-LINEAR-003-sql-checks.sql

\echo '============================================'
\echo 'Supabase 验收数据检查'
\echo '============================================'

\echo ''
\echo '--- SQL-01: 最近 raw events ---'
SELECT
    event_id,
    provider,
    idempotency_key,
    raw_body_sha256,
    request_path,
    source_ip,
    received_at
FROM webhook_raw_events
WHERE provider = 'linear'
  AND created_at > NOW() - INTERVAL '10 minutes'
ORDER BY created_at DESC
LIMIT 10;

\echo ''
\echo '--- SQL-02: 最近 canonical events ---'
SELECT
    event_id,
    canonical_type,
    canonical_action,
    idempotency_key,
    n8n_forwarded,
    created_at
FROM webhook_canonical_events
WHERE provider = 'linear'
  AND created_at > NOW() - INTERVAL '10 minutes'
ORDER BY created_at DESC
LIMIT 10;

\echo ''
\echo '--- SQL-03: 最近 processing logs ---'
SELECT
    provider,
    phase,
    level,
    message,
    created_at
FROM webhook_processing_logs
WHERE provider = 'linear'
  AND created_at > NOW() - INTERVAL '10 minutes'
ORDER BY created_at DESC
LIMIT 20;

\echo ''
\echo '--- SQL-04: TC-06 去重验证 ---'
SELECT
    idempotency_key,
    COUNT(*) as count
FROM webhook_canonical_events
WHERE idempotency_key = 'linear:tc06-delivery-dedup'
GROUP BY idempotency_key;

\echo ''
\echo '--- SQL-05: n8n_forwarded 统计 ---'
SELECT
    COUNT(*) as total,
    SUM(CASE WHEN n8n_forwarded = 0 THEN 1 ELSE 0 END) as not_forwarded,
    SUM(CASE WHEN n8n_forwarded = 1 THEN 1 ELSE 0 END) as forwarded
FROM webhook_canonical_events
WHERE provider = 'linear'
  AND created_at > NOW() - INTERVAL '10 minutes';

\echo ''
\echo '--- SQL-06: 签名失败日志计数 ---'
SELECT
    phase,
    level,
    COUNT(*) as count
FROM webhook_processing_logs
WHERE provider = 'linear'
  AND level = 'WARN'
  AND created_at > NOW() - INTERVAL '10 minutes'
GROUP BY phase, level;

\echo ''
\echo '============================================'
\echo '检查完成'
\echo '============================================'
```

---

## 八、验收判定规则

| 等级 | 测试用例 | 通过标准 |
|------|---------|---------|
| **P0** | TC-01（健康检查） | HTTP 200，mode = shadow |
| **P0** | TC-02（向后兼容） | 旧 endpoint HTTP 200 |
| **P0** | TC-03（有效签名 accepted） | HTTP 200，log 中 status=accepted |
| **P0** | TC-04（无效签名拒绝） | HTTP 401，log 中 SIGNATURE_INVALID |
| **P0** | TC-06（去重） | 第一次 accepted，第二次 duplicate_accepted |
| **P0** | SQL-01~03（存储） | raw/canonical/log 表均有对应记录 |
| **P0** | TC-10（n8n 隔离） | n8n 无新增 execution |
| **P0** | SQL-05（n8n_forwarded） | 全部为 0 |
| **P1** | TC-05（缺少签名拒绝） | HTTP 401 |
| **P1** | TC-07（非 POST 拒绝） | HTTP 405 或 404 |
| **P1** | SQL-04（去重验证） | count = 1 |
| **P1** | TC-09（大 Payload） | HTTP 200 |
| **P2** | TC-08（Content-Type 宽容） | HTTP 200 |

**通过条件**：
- 所有 P0 必须通过 → 否则不允许上线
- P1 ≥ 80% 通过 → 剩余项须有修复计划
- P2 不阻塞上线

---

## 九、与其他文档的关系

| 本文档 | 关联文档 | 关系说明 |
|--------|----------|----------|
| OPS-LINEAR-003 验收测试 | OPS-LINEAR-002 验收清单 | 本文档为 shadow endpoint 的具体测试用例，OPS-LINEAR-002 为整体 Linear Webhook 验收 |
| OPS-LINEAR-003 验收测试 | SEC-ARCH-001 Linear Webhook 安全架构 | 本文档 TC-04/TC-05 验证安全架构中的签名校验要求 |
| OPS-LINEAR-003 验收测试 | standard-webhook-ingress-phase1 | 本文档测试覆盖 phase 1 的所有核心功能（签名、去重、存储、n8n 边界） |
| OPS-LINEAR-003 验收测试 | 001_supabase_webhook_events.sql | SQL 检查部分直接使用该迁移文件定义的表结构 |

---

**文档状态**：已发布  
**下次评审日期**：2026-06-04
