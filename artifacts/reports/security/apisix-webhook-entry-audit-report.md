# APISIX Webhook 入口控制只读审计报告

**审计编号**: APISIX-WH-AUDIT-001  
**审计日期**: 2026-05-08  
**审计类型**: 只读审计（零修改）  
**审计范围**: APISIX 路由、Webhook Ingress、Linear Canary、Factory Dispatch、Supabase 事件账本、GitLab CI 闭环、入口暴露面  
**审计人**: main-thread  
**脱敏声明**: 本报告所有 secret/token/key 均已脱敏，无明文泄露  

---

## 1. 总结结论：FAIL

### 判定依据

| # | PASS 条件 | 状态 | 说明 |
|---|-----------|------|------|
| 1 | 所有 webhook 入口统一经过 APISIX | **FAIL** | Linear webhook 仍走 Cloudflare Tunnel → nginx，未经过 APISIX |
| 2 | 不存在外部可访问的裸 n8n webhook | **CONDITIONAL** | n8n 仅绑定 Tailscale IP，公网不达；但 APISIX 内存在 `/*` 通配路由直达 n8n |
| 3 | 不存在高风险宽路由直达 n8n | **FAIL** | `n8n-route-v1` 匹配 `/*` 且无鉴权，仅靠 host vars 过滤 |
| 4 | 所有 webhook 路由有鉴权/限流/签名校验 | **FAIL** | `route-webhook-events-v1` 无鉴权，仅限流 100/min |
| 5 | Webhook Ingress 有 raw/canonical/log 三层记录 | **PASS** | 三表结构完整，DDL + 代码验证通过 |
| 6 | 幂等去重有效 | **PASS** | idempotency_key UNIQUE 约束 + delivery_id 去重 |
| 7 | Linear canary 不会误触发生产 issue | **PASS** | project whitelist + type/action gate + dedupe |
| 8 | Factory dispatch 仍受 dry-run/canary/label/project/status gating 控制 | **CONDITIONAL** | 代码层面 PASS，但 runtime env 未实时验证 |
| 9 | GitHub direct push 仍为 0 | **CONDITIONAL** | 策略层面 PASS，无硬性技术阻断 |
| 10 | secret 明文泄露数量 = 0 | **PASS** | headers 脱敏三层覆盖，raw body 原文入 bytea（功能需要） |

**FAIL 根因**：APISIX 中存在两条未受控路由直接指向 n8n，且 webhook 入口未统一经过 APISIX。

---

## 2. 当前架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                        外部 Provider                            │
│          Linear / Factory / (GitHub 未接入) / (GitLab 未接入)    │
└──────────┬──────────────────────────────┬───────────────────────┘
           │                              │
           ▼                              ▼
┌──────────────────────┐    ┌────────────────────────────────────┐
│   Cloudflare CDN     │    │   APISIX (192.168.88.11)           │
│   webhook.exa.edu.kg │    │   :9080 HTTP / :3306 TCP / :5432  │
└──────────┬───────────┘    │                                    │
           │                │   ⚠️ n8n-route-v1  /* → n8n:5678  │
           ▼                │      (NO AUTH, host vars only)     │
┌──────────────────────┐    │                                    │
│  cloudflared (node-22)│    │   ⚠️ route-webhook-events-v1       │
│  43.167.177.86       │    │      /webhook/events → n8n:5678   │
└──────────┬───────────┘    │      (NO AUTH, rate-limit only)    │
           │                │                                    │
           ▼                │   ✅ n8n-webhook-apix-route         │
┌──────────────────────┐    │      /webhook/events → 5678        │
│  nginx:8080          │    │      (key-auth + rate-limit)       │
│  /healthz → n8n      │    │                                    │
│  /webhook/events →   │    │   ✅ webhook-ingest-route          │
│    webhook-ingress    │    │      /wh/*/events → .37:3100      │
│    :8000              │    │      (key-auth)                   │
└──────────┬───────────┘    │                                    │
           │                │   ✅ supabase-route-http-v2        │
           ▼                │      /supabase/* → .16:8000        │
┌──────────────────────┐    │      (key-auth)                   │
│  webhook-ingress     │    └────────────────────────────────────┘
│  (FastAPI :8000)     │
│  Linear HMAC 校验    │           │
│  Factory HMAC 校验   │           ▼
│  幂等去重            │    ┌────────────────────┐
│  raw→canonical→log   │    │   n8n (:5678)      │
│  Action 执行         │    │   仅 Tailscale 可达 │
└──────┬───────────────┘    └────────────────────┘
       │
       ▼
┌──────────────────────┐
│  Supabase PostgreSQL  │
│  rxrcidmnbyvwmhxqdgku │
│  webhook_raw_events   │
│  webhook_canonical_*  │
│  webhook_processing_* │
└──────────────────────┘
```

### 关键路径说明

| 入口路径 | 是否经过 APISIX | 是否经过 Webhook Ingress | 鉴权状态 |
|----------|----------------|------------------------|----------|
| Linear → webhook.exa.edu.kg → nginx → webhook-ingress | 否 | 是 | HMAC 签名校验 |
| 内网 → APISIX:9080/webhook/events (v1) | 是 | 否，直达 n8n | **无鉴权** |
| 内网 → APISIX:9080/webhook/events (apix) | 是 | 否，直达 n8n | key-auth |
| 内网 → APISIX:9080/* (n8n-route-v1) | 是 | 否，直达 n8n | **无鉴权** |
| 内网 → APISIX:9080/wh/*/events | 是 | 否，到 .37:3100 | key-auth |

---

## 3. 路由清单表

### 3.1 APISIX 路由 (11 条)

| # | Route ID | URI | Methods | Upstream | Priority | Status | Auth | 风险 |
|---|----------|-----|---------|----------|----------|--------|------|------|
| 1 | **n8n-route-v1** | `/*` | ALL | n8n:5678 | 0 | **启用** | **无鉴权** (仅 host vars) | **P0** |
| 2 | **route-webhook-events-v1** | `/webhook/events` | ALL | n8n:5678 | 10 | **启用** | **无鉴权** (仅限流 100/min) | **P0** |
| 3 | n8n-webhook-apix-route | `/webhook/events` | POST | 192.168.88.11:5678 | 0 | 启用 | key-auth + 限流 | P2 |
| 4 | webhook-ingest-route | `/wh/*/events` | POST | 192.168.88.37:3100 | 0 | 启用 | key-auth | 安全 |
| 5 | supabase-route-http-v2 | `/supabase/*` | ALL | 192.168.88.16:8000 | 10 | 启用 | key-auth | 安全 |
| 6 | supabase-route-http-v1 | `/supabase/*` | ALL | 192.168.88.16:8000 | 0 | 启用 | 无 (被 v2 覆盖) | P2 |
| 7 | mcp-1password | `/mcp/1password/*` | ALL | 1password-connect-mcp:8000 | 1 | 启用 | ip-restriction + key-auth | 安全 |
| 8 | op-connect | `/1password/*` | ALL | 192.168.88.11:8080 | 0 | 启用 | ip-restriction + key-auth | 安全 |
| 9 | route-webhook-healthz-v1 | `/healthz` | GET/HEAD | n8n:5678 | 10 | 启用 | 无 (健康检查) | 安全 |
| 10 | route-linear-events-v1 | `/linear/events` | POST | n8n:5678 | 10 | **禁用** | 无 (未激活) | P2 |
| 11 | route-gitlab-events-v1 | `/gitlab/events` | POST | n8n:5678 | 10 | **禁用** | 无 (未激活) | P2 |

### 3.2 APISIX Upstream (6 个)

| Upstream ID | 目标 | 说明 |
|-------------|------|------|
| supabase-gateway-http-v1 | 192.168.88.16:8000 | Supabase gateway |
| upstream-webhook-ingress-v1 | **n8n:5678** | ⚠️ 名称含 webhook-ingress 但实际指向 n8n |
| upstream-n8n-health-v1 | n8n:5678 | n8n 健康检查 |
| mcp-1password | 1password-connect-mcp:8000 | 1Password MCP |
| op-connect | 192.168.88.11:8080 | 1Password Connect API |
| test-upstream-id | 127.0.0.1:80 | 测试用 |

**关键问题**: `upstream-webhook-ingress-v1` 的描述是 "webhook ingress upstream (currently points to n8n; switch to webhook-ingress-shadow when deployed)"，说明尚未切换到真正的 webhook-ingress。

### 3.3 APISIX Consumer (7 个)

| Username | 用途 | Auth 方式 |
|----------|------|-----------|
| supabase_client_v1 | Supabase 客户端 | key-auth |
| webhook_ingress | Webhook Ingress (node-22) | key-auth |
| n8n_automation | n8n 自动化 | key-auth |
| n8n_webhook_consumer | n8n webhook 消费者 | key-auth |
| gitlab_runner | GitLab Runner | key-auth |
| 1password_connect_ro | 1Password 只读 | key-auth |
| test_source | 测试 | key-auth |

### 3.4 Stream Routes (2 条)

| ID | 端口 | 目标 | Auth |
|----|------|------|------|
| mysql-stream-3306-v1 | 3306 | 192.168.88.17:3306 | ip-restriction (白名单) |
| postgres-stream-5432-v1 | 5432 | 192.168.88.16:5432 | ip-restriction (白名单) |

---

## 4. 风险清单

### P0 — 必须立即修复

| # | 风险 | 影响 | 证据 |
|---|------|------|------|
| P0-1 | **n8n-route-v1 (`/*`) 无鉴权直达 n8n** | 内网/Tailscale 网络中任何可达 apisix.tail5e888.ts.net:9080 的客户端，均可无鉴权访问 n8n 全部端点 | route: `uri: /*`, `plugins: {}`, upstream: `n8n:5678`, host vars 限制为 4 个 hostname |
| P0-2 | **route-webhook-events-v1 无鉴权直达 n8n** | 所有可通过 APISIX :9080 的客户端可无鉴权 POST/GET/PUT/DELETE 到 n8n webhook 端点 | route: `uri: /webhook/events`, methods: ALL, plugins: 仅 limit-count 100/min + request-id |
| P0-3 | **upstream-webhook-ingress-v1 实际指向 n8n 而非 webhook-ingress** | 所有使用该 upstream 的路由（route-webhook-events-v1, route-linear-events-v1, route-gitlab-events-v1）实际都是绕过 webhook-ingress 直达 n8n | upstream desc: "currently points to n8n; switch to webhook-ingress-shadow when deployed" |

### P1 — 需要尽快修复

| # | 风险 | 影响 | 证据 |
|---|------|------|------|
| P1-1 | **Linear webhook 不经过 APISIX，走独立 Cloudflare + nginx 路径** | 两套入口并存，无法统一治理、审计、限流 | Linear webhook → webhook.exa.edu.kg → cloudflared → nginx:8080 → webhook-ingress:8000 |
| P1-2 | **APISIX Admin API (9180) 和 etcd (2379) 绑定 0.0.0.0** | 依赖宿主机防火墙做唯一防线；误操作可导致 admin 暴露 | Admin API listen: `0.0.0.0:9180` |
| P1-3 | **FactoryDispatchDryRunAction 无 try/except** | action 异常可能影响 ingress 主流程 ACK | actions.py: `result = self.executor.execute(canonical_event)` 无异常捕获 |
| P1-4 | **ActionRegistry 无 action-level exception isolation** | 任何未捕获的 action 异常会中断后续 action 和请求处理 | ActionRegistry.run: 顺序遍历 action.run() 无 try/except |
| P1-5 | **route-webhook-events-v1 和 n8n-webhook-apix-route URI 冲突** | 两条路由匹配相同 `/webhook/events` 路径，优先级差异（10 vs 0）决定实际匹配，但语义不清 | v1: priority 10 无鉴权; apix: priority 0 有 key-auth → **v1 优先生效** |

### P2 — 需要关注

| # | 风险 | 影响 | 证据 |
|---|------|------|------|
| P2-1 | **supabase-route-http-v1 仍存在且无鉴权** | 被 v2 (priority 10) 覆盖，但如果 v2 被删除则会回退到无鉴权状态 | priority 0, 无 key-auth |
| P2-2 | **GitLab CI → webhook 闭环未实现** | 无 GitLab provider adapter，无 CI failure → Linear issue 映射 | routes.yaml: github/gitlab enabled: false; 无 GitLabAdapter |
| P2-3 | **raw body 原文入 bytea 未做 body-level secret redaction** | 若 webhook body 包含 secret，会原文保留 | postgres_storage.py: `psycopg2.Binary(request.raw_body)` |
| P2-4 | **Factory lifecycle 状态仅存内存** | 多进程/重启后状态丢失 | lifecycle.py: `_runs = {}` 进程内 dict |
| P2-5 | **WEBHOOK_INGRESS_MODE 无枚举校验** | 未知 mode 字符串会被当作 live-like 行为 | server.py: `os.environ.get("WEBHOOK_INGRESS_MODE", "shadow")` |
| P2-6 | **route-linear-events-v1 / route-gitlab-events-v1 虽禁用但无鉴权配置** | 若激活则直接暴露 n8n，且不经过 webhook-ingress | status: 0, plugins: {} |

---

## 5. 证据链

### 5.1 APISIX Route/Upstream/Plugin 证据

**来源**: APISIX Admin API 只读转储 (apisix-gw-test-01:9180)

**关键发现**:

```json
// P0-1: n8n-route-v1 — 通配路由无鉴权直达 n8n
{
  "id": "n8n-route-v1",
  "status": 1,           // 启用
  "priority": 0,
  "uri": "/*",           // 匹配所有路径
  "vars": [["host", "in", ["192.168.88.11", "100.100.1.11",
             "apisix.tail5e888.ts.net", "mac.tail5e888.ts.net"]]],
  "upstream": {"nodes": {"n8n:5678": 1}},
  "plugins": {}          // 无任何鉴权/限流插件
}
```

```json
// P0-2: route-webhook-events-v1 — 无鉴权直达 n8n
{
  "id": "route-webhook-events-v1",
  "status": 1,           // 启用
  "priority": 10,        // 高优先级，覆盖 n8n-webhook-apix-route (priority 0)
  "uris": ["/webhook/events"],
  "methods": ["GET","HEAD","POST","PUT","PATCH","DELETE","OPTIONS"],
  "upstream_id": "upstream-webhook-ingress-v1",  // 实际指向 n8n:5678
  "plugins": {
    "limit-count": {"count": 100, "time_window": 60},  // 仅限流
    "request-id": {}                                     // 仅追踪
    // 无 key-auth / ip-restriction
  }
}
```

```json
// P0-3: upstream 描述明确说还未切换
{
  "id": "upstream-webhook-ingress-v1",
  "desc": "webhook ingress upstream (currently points to n8n; switch to webhook-ingress-shadow when deployed)",
  "nodes": {"n8n:5678": 1}  // 指向 n8n 而非 webhook-ingress
}
```

### 5.2 Webhook Ingress 代码证据

**来源**: `/Users/busiji/workbot/workspace/tools/webhook_ingress/`

| 审计项 | 判定 | 证据 |
|--------|------|------|
| Canonical Schema | **PASS** | `schemas/canonical-webhook-event-v1.json` 存在，required 字段完整，`schema.py` 校验器覆盖 required/enum/pattern |
| Raw/Canonical/Log 三表 | **PASS** | `storage.py` SQLite DDL + `postgres_storage.py` + `migrations/001_supabase_webhook_events.sql` 三表结构完整 |
| 幂等去重 | **PASS** | `ingress.py` idempotency_key + DB UNIQUE 约束 + duplicate_accepted 不触发 action |
| Headers 脱敏 | **PASS** | `redaction.py` 7 种敏感模式 + 三层脱敏（存储/日志/过滤器） |
| Body 脱敏 | **CONDITIONAL** | raw body 原文 bytea 存储（功能需要），无 body-level secret redaction |
| Linear Adapter | **PASS** | HMAC-SHA256, type_map 18 种, action_map 6 种 |
| Factory Adapter | **PASS** | HMAC-SHA256, lifecycle 5 种状态 |
| 测试覆盖 | **CONDITIONAL** | 45 个 test case (34+11)，未实际运行（只读限制） |
| 运行模式 | **PASS** | 4 种 mode (shadow/canary_dryrun/production_canary/live) 行为隔离正确 |

### 5.3 Supabase 表/字段证据

**来源**: `migrations/001_supabase_webhook_events.sql` + `postgres_storage.py`

| 表 | 字段数 | RLS | 关键字段 |
|----|--------|-----|----------|
| webhook_raw_events | 11 | 已启用 | event_id, idempotency_key, raw_body(bytea), raw_headers(jsonb, 脱敏), raw_body_sha256, source_ip |
| webhook_canonical_events | 24 | 已启用 | event_id, canonical_version, provider, canonical_type/action, source, actor, payload(jsonb), idempotency_key(UNIQUE), n8n_forwarded |
| webhook_processing_logs | 8 | 已启用 | event_id, phase, level, message, details(jsonb 含 action_result_json) |

**Supabase 实时数据抽样**: UNKNOWN (MCP 未授权)

### 5.4 Linear Canary 证据

**来源**: `actions.py` + OPS-LINEAR-008/009/010 文档

| 审计项 | 判定 | 证据 |
|--------|------|------|
| Project Whitelist | **PASS** | `LINEAR_CANARY_ALLOWED_PROJECT_IDS` 限制为 "Webhook Ingress Canary Project" (OPS-LINEAR-010) |
| Label Fallback | **CONDITIONAL** | 未配置白名单时回退到 label `webhook-ingress-canary`，安全性依赖运行时配置 |
| Comment Loop 防护 | **PASS** | type/action filter 只处理 `issue/updated`，不处理 `comment/created` |
| Dedupe | **PASS** | duplicate_accepted 不触发 canary comment |
| 非 Canary 误触发 | **PASS** | JTO-187 out-of-project control: comment count = 0 |
| Canary 证据 | **PASS** | OPS-008/009 真实 Linear GraphQL commentCreate 记录，comment ID 可追溯 |

### 5.5 Factory Dispatch 证据

**来源**: `executors.py` + `dispatch_payload.py` + OPS-LINEAR-011

| 审计项 | 判定 | 证据 |
|--------|------|------|
| Dry-run 状态 | **PASS** | `FactoryDispatchDryRunExecutor` 只构建 payload，无 HTTP client/Factory API 调用 |
| Payload 安全标志 | **PASS** | `dry_run: true, no_write: true, no_push: true, github_push_forbidden: true` |
| Target Branch | **PASS** | 默认 `branch-2`，AGENTS.md 规则禁止直推 main |
| Project/State Gating | **PASS** | allowed_project_ids + ready_state_names ("Ready for Factory") + previous_state 不是 ready |
| Runtime Env | **UNKNOWN** | node-22 当前 env 未实时验证；OPS-011 文档显示 `FACTORY_DISPATCH_DRYRUN_ENABLED=false` |
| 失败回写 Linear | **FAIL** | 无 Factory dry-run 失败回写 Linear comment 机制 |
| 失败不阻塞 | **FAIL** | ActionRegistry 无异常隔离，FactoryDispatchDryRunAction 无 try/except |

### 5.6 GitLab CI 回传证据

**来源**: `.gitlab-ci.yml` + `routes.yaml` + `adapter.py`

| 审计项 | 判定 | 证据 |
|--------|------|------|
| CI failure webhook 入口 | **UNKNOWN** | `.gitlab-ci.yml` 无 webhook 配置；未发现 GitLab webhook 指向入口 |
| GitLab provider adapter | **UNKNOWN** | 不存在；routes.yaml 无 gitlab provider，无 GitLabAdapter 实现 |
| CI failure → Linear issue | **FAIL** | 无 CI_JOB_URL → Linear issue 映射逻辑 |
| 回写 Linear | **CONDITIONAL** | LinearCanaryCommentExecutor 可创建 comment，但无 CI status 专用 action |
| Factory 修复判断 | **UNKNOWN** | FactoryLifecycleStateMachine 存在，但未被 CI failure 触发 |
| GitHub direct push = 0 | **CONDITIONAL** | 策略禁止 + payload 安全标志 + AGENTS.md 规则，但无硬性技术阻断 |

### 5.7 入口暴露面证据

**来源**: HTTP 探测 + SSH 只读检查

| 入口 | 可达性 | 鉴权 | 结论 |
|------|--------|------|------|
| webhook.exa.edu.kg (Cloudflare) | 可达 | webhook-ingress HMAC | 受控 |
| APISIX:9080/supabase/* | 可达 | key-auth | 受控 |
| APISIX:9080/webhook/events (v1) | 可达 (内网) | **无** | **未受控** |
| APISIX:9080/* (n8n-route-v1) | 可达 (内网) | **无** | **未受控** |
| APISIX:9080/wh/*/events | 可达 (内网) | key-auth | 受控 |
| node-22:5678 (n8n 直连) | 不可达 (公网) | N/A | 安全 (仅 Tailscale) |
| node-22:8000 (webhook-ingress 直连) | 可达 (公网) | 无 | 风险但未暴露到域名 |
| APISIX:9180 (Admin API) | 不可达 (外部) | admin key | 依赖防火墙 |

---

## 6. UNKNOWN 事项

以下事项无法在本次只读审计中确认，标记为 UNKNOWN：

| # | 事项 | 原因 |
|---|------|------|
| U-1 | node-22 当前 WEBHOOK_INGRESS_MODE 实际运行值 | 未 SSH 到 node-22 执行 env 检查 |
| U-2 | node-22 当前 FACTORY_DISPATCH_DRYRUN_ENABLED 实际值 | 同上 |
| U-3 | node-22 当前 LINEAR_CANARY_ALLOWED_PROJECT_IDS 实际值 | 同上 |
| U-4 | Supabase webhook 数据库真实数据抽样 | Supabase MCP 未授权 |
| U-5 | 最近一次 pytest 运行结果 | 只读限制，未执行测试 |
| U-6 | GitLab 项目是否配置了 webhook 指向 APISIX 或 webhook.exa.edu.kg | 需 GitLab admin 访问 |
| U-7 | APISIX 宿主机防火墙规则 (iptables/nftables) 实际状态 | 需 SSH 到 192.168.88.11 检查 |
| U-8 | Factory lifecycle 状态在多进程/重启场景下的一致性 | 需运行时测试 |
| U-9 | 192.168.88.37:3100 (/wh/*/events 的目标) 服务状态 | 需进一步探测 |

---

## 7. 最终验收判断

### 判定：FAIL

**FAIL 根因 (3 项 P0)**:

1. **n8n-route-v1 (`/*`) 无鉴权直达 n8n** — 通配路由在 APISIX 上处于启用状态，仅靠 host vars 过滤。任何通过 `apisix.tail5e888.ts.net:9080` 或 `192.168.88.11:9080` 的请求均可无鉴权访问 n8n 全部端点。

2. **route-webhook-events-v1 (`/webhook/events`) 无鉴权直达 n8n** — 高优先级 (10) 的公开路由，无 key-auth、无 ip-restriction，仅有限流。且与另一条有鉴权的同名路由 (`n8n-webhook-apix-route`) 冲突时，无鉴权版本优先匹配。

3. **upstream-webhook-ingress-v1 实际指向 n8n 而非 webhook-ingress** — 所有使用该 upstream 的路由都绕过了 webhook-ingress 层的 HMAC 签名校验、幂等去重、事件标准化和审计日志。

**降级为 CONDITIONAL PASS 的条件**:
1. 删除或禁用 `n8n-route-v1`
2. 为 `route-webhook-events-v1` 添加 key-auth 或 ip-restriction
3. 将 `upstream-webhook-ingress-v1` 切换到 webhook-ingress 实际地址
4. 将 Linear webhook 入口统一到 APISIX

**审计完成。所有审计动作均为只读，未修改任何配置。**
