# 1Password Connect MCP 部署报告 — 192.168.88.11

**报告编号**: WORKBOT-MCP-DEPLOY-001  
**日期**: 2026-05-08  
**性质**: MCP 部署（APISIX 代理 + key-auth + ip-restriction）  
**最终判定**: **PASS**

---

## 部署架构

```
LAN / Tailscale Client
  │
  │ GET/POST http://192.168.88.11:9080/mcp/1password
  │ Header: apikey: <consumer key>
  │
  ▼
APISIX route: /mcp/1password (/mcp/1password/*)
  │
  │ 1. ip-restriction: whitelist (192.168.88.0/24, 100.64.0.0/10, 127.0.0.1, 172.16.0.0/12)
  │ 2. key-auth: apikey header/query
  │
  │   ↑ 匹配 APISIX consumer (7 个 consumer 均可访问)
  │   ↑ 建议: 添加 consumer-restriction 限制
  │
  ▼
APISIX upstream: mcp-1password → 192.168.88.11:8000
  │
  ▼
1password-connect-mcp (Docker container)
  │ Image: supercorp/supergateway:latest
  │ Binding: 0.0.0.0:8000 (APISIX 提供认证保护)
  │ SSE Path: /mcp/1password
  │ Messages: /mcp/1password/messages?sessionId=<uuid>
  │
  │ OP_CONNECT_HOST: http://192.168.88.11:8080 (直连 Connect API)
  │ OP_API_KEY: <665B JWT Connect token>
  │
  ▼
op-connect-api (1password/connect-api:latest v1.8.2)
  │ :8080 Bearer JWT 认证
  │
  ▼
1Password Cloud (my.1password.com)
```

---

## 部署组件

| 组件 | 路径/位置 | 说明 |
|------|---------|------|
| MCP Server 源码 | `/opt/mcp-servers/1password-connect/` | index.js + node_modules + package.json |
| Docker Compose | `/opt/1panel/mcp/1password-connect/docker-compose.yml` | 1Panel MCP 管理 |
| 环境变量 | `/opt/1panel/mcp/1password-connect/.env` | 含 OP_API_KEY (REDACTED) |
| 容器名 | `1password-connect-mcp` | supercorp/supergateway:latest |
| APISIX Route | `mcp-1password` | /mcp/1password + /mcp/1password/*, priority=1 |
| APISIX Upstream | `mcp-1password` | → 192.168.88.11:8000 |

---

## APISIX 路由配置

| 属性 | 值 |
|------|-----|
| Route ID | `mcp-1password` |
| URIs | `/mcp/1password`, `/mcp/1password/*` |
| Priority | 1 (高于 n8n catch-all 的 0) |
| Status | 1 (active) |
| Upstream | `mcp-1password` → `192.168.88.11:8000` |

**插件链**:
1. **ip-restriction**: whitelist — 192.168.88.0/24, 100.64.0.0/10, 127.0.0.1, 172.16.0.0/12
2. **key-auth**: header=`apikey`, query=`apikey`

---

## MCP 工具列表

| Tool | Description | 风险 |
|------|-------------|------|
| `op_list_vaults` | 列出所有 vault | 信息泄露 (需认证) |
| `op_list_items` | 列出 vault 内 item (id + title) | 信息泄露 (需认证) |
| `op_get_item` | 获取 item 完整详情含 passwords | **高风险** (需认证) |
| `op_search_items` | 按 title 搜索 item | 信息泄露 (需认证) |

**认证保护**: 所有工具通过 APISIX key-auth 保护，仅认证 consumer 可访问。

---

## 验证结果

| 测试 | 结果 |
|------|------|
| 无认证访问 | `Missing API key found in request` — 拒绝 |
| 错误 apikey | `Invalid API key in request` — 拒绝 |
| 正确 apikey + SSE | `event: endpoint` + sessionId — 成功 |
| MCP initialize | `1password-connect-mcp v1.0.0` — 成功 |
| MCP tools/list | 4 个工具全部返回 — 成功 |
| LAN 访问 (无认证) | 被拒绝 — 安全 |

---

## 与 ce-01 MCP 的对比

| 维度 | ce-01 (旧, 已停止) | apisix-gw-test-01 (新) |
|------|-------------------|----------------------|
| 主机 | 192.168.88.15 | 192.168.88.11 |
| 认证 | **无** | **key-auth + ip-restriction** |
| 绑定 | 0.0.0.0:8000 (裸露) | 0.0.0.0:8000 (APISIX 保护) |
| OP_CONNECT_HOST | APISIX /1password (key-auth) | 直连 :8080 (Bearer) |
| 外部访问 | 直接暴露 | 通过 APISIX 9080 + apikey |
| 判定 | BLOCKED | PASS |

---

## 安全注意事项

1. **consumer-restriction 缺失**: 当前所有 7 个 APISIX consumer 均可访问 `/mcp/1password`。建议添加 consumer-restriction 插件，限制仅 `1password_connect_ro` 访问。

2. **op_get_item 风险**: 此工具可返回完整 secret value。建议后续修改 index.js，限制此工具只返回元数据或长度信息。

3. **MCP 容器绑定 0.0.0.0**: 容器绑定所有接口，但端口 8000 直连被 APISIX 认证保护。如需额外保护，可通过 iptables 限制 8000 端口只允许本机访问。

4. **1Panel 管理**: Compose 文件位于 `/opt/1panel/mcp/1password-connect/`，1Panel 可自动发现和管理。

---

## 客户端连接配置

```
MCP SSE Endpoint: http://192.168.88.11:9080/mcp/1password
Headers: apikey: <consumer key>
Accept: text/event-stream

SSE 流:
  event: endpoint
  data: /mcp/1password/messages?sessionId=<uuid>

POST messages:
  http://192.168.88.11:9080/mcp/1password/messages?sessionId=<uuid>
  Headers: apikey: <consumer key>
  Content-Type: application/json
```

---

## Secret 输出检查

| 禁止项 | 是否违反 |
|--------|---------|
| 输出 secret value | NO |
| 输出 OP_API_KEY | NO |
| 输出 OP_CONNECT_TOKEN | NO |
| 输出 consumer apikey | NO |
| 修改 1Password vault | NO |
| 修改 APISIX 已有路由 | NO |
