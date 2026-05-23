# 1Password Connect 双入口只读审计报告

**报告编号**: WORKBOT-DUAL-ENTRY-AUDIT-001  
**日期**: 2026-05-08  
**性质**: 只读审计 — 零配置变更、零容器重启、零 secret 输出  
**最终判定**: **CONDITIONAL PASS**

---

## 判定摘要

| 维度 | 判定 | 说明 |
|------|------|------|
| Connect API 健康性 | PASS | v1.8.2 运行正常，4/4 依赖 ACTIVE |
| APISIX 路由安全 | CONDITIONAL | key-auth + ip-restriction 生效，但所有 7 个 consumer 可访问 /1password 路由 |
| MCP 入口安全 | PASS (不可用) | supergateway 容器已删除，13191 端口返回 1Panel 锁屏页，无 MCP 服务运行 |
| Secret 泄露风险 | PASS | 未发现裸露 secret 读取，Connect API 要求 Bearer 认证 |
| 日志泄露风险 | LOW | APISIX 日志策略未验证，需后续确认 |
| op CLI 兼容性 | CONDITIONAL | op CLI 不支持 apikey header，需直连 :8080 或使用 OP_CONNECT_HOST 直连路径 |

---

## 1. 192.168.88.11 APISIX / 1Password Connect 审计结果

### 1.1 主机可达性

| 端点 | 状态 | 响应 |
|------|------|------|
| `ping 192.168.88.11` | REACHABLE | 0% packet loss, avg 6.3ms |
| `http://192.168.88.11:9080/` | REACHABLE | 200 OK — n8n 前端页面 |
| `http://192.168.88.11:9180/` | UNREACHABLE | 连接超时 (Admin API 未暴露到 LAN) |
| `http://192.168.88.11:8080/health` | REACHABLE | Connect API health JSON |
| `http://192.168.88.11:8081/health` | UNREACHABLE | 连接超时 (sync 仅监听 127.0.0.1) |

### 1.2 Connect API Health

```json
{
  "name": "1Password Connect API",
  "version": "1.8.2",
  "dependencies": [
    {"service": "sqlite", "status": "ACTIVE"},
    {"service": "account_data", "status": "AVAILABLE"},
    {"service": "sync", "status": "ACTIVE"},
    {"service": "1Password", "status": "ACTIVE"}
  ]
}
```

**判定**: PASS — Connect API v1.8.2 健康，所有 4 个依赖 ACTIVE。

### 1.3 APISIX 路由

| 属性 | 值 |
|------|-----|
| Route ID | `op-connect` |
| URIs | `/1password/*` |
| Upstream | `op-connect` → `192.168.88.11:8080` |
| Status | active |

**插件链**:
1. **ip-restriction**: whitelist — 192.168.88.0/24, 100.64.0.0/10, 127.0.0.1, 172.16.0.0/12
2. **key-auth**: header=`apikey`, query=`apikey`
3. **proxy-rewrite**: regex_uri `^/1password/(.*)` → `/$1`, 自动注入 `Authorization: Bearer` header

**认证行为验证**:
- 无 apikey → `{"message":"Missing API key found in request"}`
- 错误 apikey → `{"message":"Invalid API key in request"}`
- 正确 apikey → 正常代理到 Connect API

### 1.4 Consumer 审计

| # | Username | Key Length | 应访问 1password | 实际可访问 |
|---|----------|-----------|-----------------|-----------|
| 1 | `1password_connect_ro` | 48 | YES | YES |
| 2 | `gitlab_runner` | 48 | NO | YES |
| 3 | `n8n_automation` | 48 | NO | YES |
| 4 | `n8n_webhook_consumer` | 24 | NO | YES |
| 5 | `supabase_client_v1` | 64 | NO | YES |
| 6 | `test_source` | 28 | NO | YES |
| 7 | `webhook_ingress` | 48 | NO | YES |

**风险**: 路由无 `consumer-restriction` 插件，所有 7 个 APISIX consumer 均可访问 `/1password/*` 路由。建议添加 consumer-restriction，限制仅 `1password_connect_ro` 访问。

### 1.5 直连 Connect API (:8080)

| 属性 | 值 |
|------|-----|
| 地址 | `http://192.168.88.11:8080` |
| 认证 | `Authorization: Bearer` (665B JWT) |
| 无认证访问 | `401 Invalid bearer token` |
| 镜像 | `1password/connect-api:latest` (正确) |
| sync | `1password/connect-sync:latest` (正确) |
| 监听 | `0.0.0.0:8080` (API), `127.0.0.1:8081` (sync) |

### 1.6 Docker 容器

SSH 无法连接到 192.168.88.11（publickey denied），基于已有 inspect backup:

| 容器 | 镜像 | 状态 |
|------|------|------|
| op-connect-api | `1password/connect-api:latest` | running, 0 restarts |
| op-connect-sync | `1password/connect-sync:latest` | running, 0 restarts |

**镜像检查**: PASS — 两个容器均使用官方 1Password 镜像，未发现 supercorp/supergateway 在此主机上。

### 1.7 op CLI 兼容性分析

| 路径 | op CLI 兼容 | 说明 |
|------|-----------|------|
| `OP_CONNECT_HOST=http://192.168.88.11:8080` | YES | 直连 Connect API，op CLI 原生支持 Bearer 认证 |
| `OP_CONNECT_HOST=http://192.168.88.11:9080/1password` | NO | 需要 apikey header，op CLI 无法携带额外 header |

**结论**: APISIX `/1password` 路由不适合作为 `OP_CONNECT_HOST`。op CLI 应直连 `:8080`。

---

## 2. 192.168.88.15:13191 /ai/mcp 审计结果

### 2.1 Endpoint 可达性

| 端点 | 状态 | 响应 |
|------|------|------|
| `http://192.168.88.15:13191/` | REACHABLE | 1Panel 锁屏页 "Access Temporarily Unavailable" |
| `http://192.168.88.15:13191/ai/mcp` | REACHABLE | 同上，1Panel 锁屏页 |
| `http://192.168.88.15:13191/ai/` | REACHABLE | 同上 |
| `http://192.168.88.15:13191/api/v1/mcp` | REACHABLE | 同上 |
| POST JSON-RPC to `/ai/mcp` | REACHABLE | 同上，无 JSON-RPC 响应 |
| SSE Accept to `/ai/mcp` | REACHABLE | 同上，无 SSE 流 |
| `http://192.168.88.15:8000/` | UNREACHABLE | 连接超时 |
| `http://192.168.88.15:8080/` | UNREACHABLE | 连接超时 |
| `http://192.168.88.15:3000/` | UNREACHABLE | 连接超时 |
| `https://192.168.88.15:13191/` | FAILED | TLS 协议版本不匹配 |

**判定**: 192.168.88.15:13191 当前仅提供 1Panel 管理面板锁屏页，无实际 MCP 服务运行。

### 2.2 MCP Container 状态

基于已有 docker inspect backup:

| 属性 | 值 |
|------|-----|
| Container Name | `1password-connect` (同名冲突!) |
| Image | `supercorp/supergateway:latest` |
| Status | **restarting** (崩溃循环) |
| Port Binding | `0.0.0.0:8000` → container:8000 |
| Network | `1panel-network` |
| Entrypoint | `supergateway` |
| Cmd | `--stdio node /app/index.js --outputTransport sse --port 8000 --baseUrl https://192.168.88.15 --ssePath /1password-connect` |
| OP_CONNECT_HOST | `http://192.168.88.11:9080/1password` |
| OP_API_KEY | REDACTED (present) |

**关键发现**:
1. MCP 容器使用 **错误镜像** `supercorp/supergateway`（应为 1Password Connect 官方镜像）
2. 容器状态为 **restarting**（崩溃循环），端口 8000 不可达
3. 容器名 `1password-connect` 与 192.168.88.11 上的 Connect 容器同名，容易混淆
4. `OP_CONNECT_HOST` 指向 APISIX `/1password` 路由，需 apikey 认证
5. 绑定到 `0.0.0.0:8000`（如恢复运行，将暴露到所有接口）

**注**: 根据 full-flow 报告，此容器已被用户手动删除。当前端口探测确认 8000 不可达。

### 2.3 MCP 工具审计

由于 MCP 服务未运行，无法列出 tools/capabilities。基于配置分析:

| 检查项 | 状态 | 说明 |
|--------|------|------|
| 是否需要认证 | CONDITIONAL | 1Panel 锁屏可能保护 13191，但端口本身对外开放 |
| 是否可匿名访问 | N/A | 服务未运行 |
| 是否暴露 tool list | N/A | 服务未运行 |
| 是否包含 1Password tool | LIKELY YES | supergateway 设计为 MCP 桥接到 1Password Connect |
| 是否允许读取 secret value | LIKELY YES | supergateway 通过 OP_API_KEY 调用 Connect API |
| 是否有审计日志 | UNKNOWN | supergateway 日志能力未知 |
| 是否仅局域网访问 | NO | 绑定到 `0.0.0.0`，但 192.168.88.x 为私网 |

### 2.4 潜在风险（如果 MCP 恢复运行）

| 风险 | 等级 | 说明 |
|------|------|------|
| 匿名 secret 读取 | HIGH | 如果 supergateway 不要求认证，任何局域网设备可读取 |
| Secret 返回给 LLM | HIGH | MCP 工具会将 secret value 返回给调用方（LLM） |
| 0.0.0.0 绑定 | MEDIUM | 理论上所有接口可访问 |
| 无 audit trail | MEDIUM | supergateway 无审计日志 |
| 错误镜像 | LOW | 非 1Password 官方镜像 |

---

## 3. 双入口对比表

| 字段 | A: APISIX (.11:9080) | B: MCP (.15:13191/ai/mcp) |
|------|---------------------|--------------------------|
| **入口** | `http://192.168.88.11:9080/1password/*` | `http://192.168.88.15:13191/ai/mcp` |
| **当前状态** | ACTIVE | INACTIVE (容器已删除) |
| **用途** | API 反向代理 + 认证层 | MCP SSE 桥接（stdio → SSE） |
| **是否认证** | YES | UNKNOWN (服务未运行) |
| **认证方式** | key-auth (apikey header) + IP whitelist | 依赖 1Panel / 无额外认证 |
| **是否可读取 secret** | YES (带认证) | LIKELY YES (如恢复) |
| **是否可写** | NO (Connect API 只读) | LIKELY YES (如实现) |
| **是否可匿名访问** | NO (需要 apikey) | POTENTIALLY YES (如无认证) |
| **是否有审计** | APISIX access log | 无 |
| **适合 Factory secret source** | NO (op CLI 不兼容) | NO |
| **适合 AI/MCP tool** | NO | YES (设计用途) |
| **风险等级** | LOW | HIGH (如恢复无认证) |
| **推荐动作** | 添加 consumer-restriction | 不恢复 / 如需恢复先加认证 |

---

## 4. 标准化建议

### 4.1 Primary Path — Factory Secret Source

```
1Password Connect Server (192.168.88.11:8080)
├── OP_CONNECT_HOST = http://192.168.88.11:8080
├── OP_CONNECT_TOKEN = <REDACTED> (665B JWT)
├── op read op://server/<item>/<field>
├── secret only enters current process env
└── never print value or prefix
```

**理由**:
- 直连 Connect API，op CLI 原生兼容
- Bearer 认证由 Connect API 原生支持
- 不经过 APISIX key-auth 层，无兼容性问题
- IP 限制在 Connect API 层面 (:8080 监听 0.0.0.0 但受 LAN 防护)

### 4.2 APISIX 路由定位

```
APISIX /1password/* (192.168.88.11:9080)
├── 定位: 辅助认证层，用于脚本/自动化工具
├── 不应作为 OP_CONNECT_HOST
├── 适合: curl / httpie / n8n / 自定义脚本
├── 必须修复: 添加 consumer-restriction 插件
└── 建议: 仅允许 1password_connect_ro consumer
```

### 4.3 Fallback Path

```
OP_SERVICE_ACCOUNT_TOKEN
├── 仅用于 non-production dry-run / recovery
├── 必须声明 TEMPORARY_SECRET_PATH 环境变量
├── 禁止用于: Factory dispatch / Linear mutation / GitHub sync / production change
└── 使用后立即清除 env
```

### 4.4 MCP Policy

```
MCP 入口 (192.168.88.15:13191/ai/mcp)
├── 当前状态: INACTIVE (容器已删除)
├── 如需恢复:
│   ├── 1. 替换 supercorp/supergateway 为官方 MCP server
│   ├── 2. 添加认证层 (至少 API key / Bearer token)
│   ├── 3. 绑定到 127.0.0.1 或 Tailscale IP，不绑定 0.0.0.0
│   ├── 4. 禁止将 secret value 返回给 LLM chat context
│   ├── 5. 仅返回 secret 存在性 / 长度 / 格式，不返回 value
│   └── 6. 启用审计日志
├── MCP 可暴露 tool metadata (名称、描述、schema)
├── MCP 不可返回 secret value 到通用 LLM context
├── MCP secret-reading 工具必须要求 explicit allowlist + audit
└── MCP 应优先返回 secret 到 process env / secure handle，而非 chat output
```

### 4.5 APISIX Policy

```
APISIX 保护层 (192.168.88.11:9080/1password/*)
├── 如果客户端可满足认证: 可以保留
├── op CLI 路径不能要求额外 apikey header
├── 如果使用 key-auth: 提供本地 shim 或不作为 OP_CONNECT_HOST
├── 不将 Connect API 暴露到公网
├── 不在日志中记录 Authorization / Bearer / apikey
├── 必须添加 consumer-restriction
└── 建议启用 TLS (当前全 HTTP 明文)
```

---

## 5. 禁止项检查

| 禁止项 | 是否违反 | 证据 |
|--------|---------|------|
| 输出 secret value | NO | 全部输出为 HTTP status / present-missing / redacted |
| 修改 APISIX route | NO | 仅 curl 探测，未调用 Admin API |
| 修改 APISIX upstream | NO | 同上 |
| 修改 1Password Connect 配置 | NO | 无 SSH 权限，无文件修改 |
| 重启容器 | NO | 未执行任何 docker restart / compose up |
| 创建 webhook | NO | 未创建任何 webhook |
| 改 Linear | NO | 未调用 Linear API |
| 推 GitHub | NO | 未执行 git push |
| 触发 Factory | NO | 未调用 Factory API |
| 调用 Factory API | NO | 无 Factory 相关请求 |
| 读取真实 secret value | NO | 仅探测 health endpoint 和认证行为 |

---

## 6. 下一步建议

### 6.1 高优先级

| # | 建议 | 理由 |
|---|------|------|
| 1 | 添加 APISIX consumer-restriction 到 /1password 路由 | 当前所有 7 个 consumer 均可访问 |
| 2 | 确认 MCP 容器不会自动恢复 | 检查 1Panel 是否有 restart policy |
| 3 | Factory 配置 `OP_CONNECT_HOST=http://192.168.88.11:8080` | 直连路径，op CLI 兼容 |

### 6.2 中优先级

| # | 建议 | 理由 |
|---|------|------|
| 4 | 启用 APISIX TLS | 当前 HTTP 明文，apikey 可被嗅探 |
| 5 | 确认 APISIX access log 不记录 Authorization header | 防止日志泄露 |
| 6 | 验证 Connect API :8080 的访问控制 | 当前 0.0.0.0 监听，依赖 IP whitelist |

### 6.3 低优先级

| # | 建议 | 理由 |
|---|------|------|
| 7 | 如需 MCP 入口，重新设计为认证 + 审计模式 | 当前 supergateway 无安全控制 |
| 8 | 修复 Docker healthcheck | distroless 镜像缺 curl/sh |
| 9 | 编写 as-built 文档 | 记录 /1password 路由设计 |

---

## 7. 最终判定: CONDITIONAL PASS

**理由**:
- Connect API primary path (直连 :8080) 安全可用 → PASS
- APISIX key-auth 与 op CLI 存在兼容问题但可通过直连绕过 → CONDITIONAL
- APISIX 路由缺少 consumer-restriction → CONDITIONAL (需后续修复)
- MCP 容器已删除，当前无风险 → PASS
- 如 MCP 恢复无认证运行 → 升级为 BLOCKED
- 无 secret 输出、无配置变更 → PASS

**判定规则映射**:
- 至少一个 Connect primary path 安全可用: YES → 不 BLOCKED
- MCP 不暴露 secret: YES (未运行) → 不 BLOCKED
- APISIX consumer-restriction 缺失: 需后续修复 → CONDITIONAL
- APISIX key-auth 与 op CLI 不兼容: 可通过直连 :8080 绕过 → CONDITIONAL

---

## 附录 A: 探测命令记录

所有命令均为只读 HTTP GET/POST/HEAD 探测:
- `ping 192.168.88.11` / `ping 192.168.88.15`
- `curl -sS -I http://192.168.88.11:{9080,9180,8080,8081}/...`
- `curl -sS http://192.168.88.11:8080/health`
- `curl -sS http://192.168.88.11:8080/v1/vaults`
- `curl -sS http://192.168.88.11:9080/1password/...`
- `curl -sS -I http://192.168.88.15:13191/...`
- `curl -sS http://192.168.88.15:13191/...`
- `curl -sS http://192.168.88.15:{8000,8080,3000,9090}/...`
- `ssh root@192.168.88.11 docker ps` (publickey denied)
- `ssh busiji@192.168.88.11 docker ps` (publickey denied)
- 本地文件读取: artifacts/1password-connect-*.yml, .json, .redacted

## 附录 B: 数据来源

| 数据 | 来源 | 可信度 |
|------|------|--------|
| Connect API health | 实时 HTTP 探测 | HIGH |
| APISIX 认证行为 | 实时 HTTP 探测 | HIGH |
| APISIX 路由配置 | full-flow 报告 + 实时验证 | HIGH |
| MCP 容器状态 | docker inspect backup | MEDIUM (历史快照) |
| Consumer 列表 | full-flow 报告 | HIGH |
| Docker 容器列表 | SSH 失败，无法实时验证 | LOW |
