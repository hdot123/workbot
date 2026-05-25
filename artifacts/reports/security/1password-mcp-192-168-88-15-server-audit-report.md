# 1Password Connect MCP — 192.168.88.15 服务器只读审计报告

**报告编号**: WORKBOT-MCP-AUDIT-001  
**日期**: 2026-05-08  
**性质**: 只读审计 — 零配置变更、零容器操作、零 secret 输出  
**最终判定**: **BLOCKED**

---

## 判定摘要

| 维度 | 结果 | 说明 |
|------|------|------|
| MCP endpoint 是否真实可用 | YES | SSE MCP server 正常运行 |
| 是否匿名可访问 | **YES** | 从 LAN 无需任何认证即可连接 |
| 是否可列 vaults | **YES** | 返回 1 个 vault (sever, 68 items) |
| 是否可列 item titles | **YES** | 返回全部 68 个 item 标题和 ID |
| 是否可读 secret value | **YES (工具可用)** | `op_get_item` 描述明确说明返回 passwords |
| 是否有写操作 | NO | 无 write/delete 工具 |
| 是否有认证 | **NO** | MCP endpoint 无任何认证机制 |
| 是否绑定 0.0.0.0 | **YES** | 容器绑定到 0.0.0.0:8000 |
| 是否适合 primary secret source | **NO** | 绝对不能 |
| 是否适合 MCP tool | **NO — 除非修复认证** | 当前状态禁止使用 |

---

## 1. 服务器容器/进程检查

### 1.1 主机信息

| 属性 | 值 |
|------|-----|
| Hostname | ce-01 |
| IP | 192.168.88.15, 100.100.1.15 (Tailscale) |
| OS | Linux |

### 1.2 相关监听端口

| 端口 | 绑定 | 进程 | 说明 |
|------|------|------|------|
| 8000 | 0.0.0.0 | docker-proxy | **MCP service (1password-connect)** |
| 8060 | 0.0.0.0 | nginx | GitLab CE |
| 8090 | 0.0.0.0 | docker-proxy | AxonHub |
| 13191 | 0.0.0.0 | 1panel-core | 1Panel 管理面板 |
| 80 | 127.0.0.1 | nginx | 本地 nginx |
| 80 | 100.100.1.15 | tailscaled | Tailscale HTTP |
| 8080 | 127.0.0.1 | bundle (GitLab) | GitLab internal |
| 8092 | 127.0.0.1 | bundle (GitLab) | GitLab internal |

### 1.3 Docker 容器

| 容器名 | 镜像 | 端口 | 状态 |
|--------|------|------|------|
| **1password-connect** | **supercorp/supergateway:latest** | **0.0.0.0:8000->8000/tcp** | **Up 42 minutes** |
| axonhub-app | axonhub-hdot:v0.9.37-latest | 0.0.0.0:8090->8090/tcp | Up 2 days |

---

## 2. `/1password-connect` 后端分析

### 2.1 容器详情

| 属性 | 值 |
|------|-----|
| Container Name | `/1password-connect` |
| Image | `supercorp/supergateway:latest` |
| Status | running (RestartCount=0) |
| Created | 2026-05-08T02:06:05Z |
| Network | `1panel-network` (172.19.0.2) |
| Port Binding | `0.0.0.0:8000->8000/tcp` |
| Entrypoint | `supergateway` |
| Mount | `/opt/mcp-servers/1password-connect:/app` (rw) |

### 2.2 容器命令

```
supergateway --stdio node /app/index.js --outputTransport sse --port 8000 --baseUrl https://192.168.88.15 --ssePath /1password-connect --streamableHttpPath "" --messagePath /1password-connect/messages
```

### 2.3 环境变量 (仅 key names)

| Key | 说明 |
|-----|------|
| OP_API_KEY | REDACTED (1Password Connect API key) |
| OP_CONNECT_HOST | `http://192.168.88.11:9080/1password` |
| PATH | 系统路径 |
| NODE_VERSION | Node.js 版本 |
| YARN_VERSION | Yarn 版本 |

### 2.4 MCP Server 源码

| 路径 | 文件 |
|------|------|
| /opt/mcp-servers/1password-connect/index.js | 6341 bytes |
| /opt/mcp-servers/1password-connect/package.json | 501 bytes |
| /opt/mcp-servers/1password-connect/node_modules/ | 94 subdirectories |

**Compose 配置路径**: `/opt/1panel/mcp/1password-connect/docker-compose.yml`

### 2.5 MCP Server 信息

| 属性 | 值 |
|------|-----|
| Server Name | `1password-connect-mcp` |
| Version | 1.0.0 |
| Protocol | MCP SSE (2024-11-05) |
| SSE Path | `/1password-connect` |
| Message Path | `/1password-connect/messages?sessionId=<uuid>` |

---

## 3. 反向代理路径

### 3.1 探查结果

| 检查 | 结果 |
|------|------|
| Nginx conf.d/sites-enabled | 不存在 |
| OpenResty 配置 | 未发现 /1password-connect 代理规则 |
| 1Panel website 配置 | 无 website 配置指向此路径 |
| 1Panel MCP 配置 | 存在于 `/opt/1panel/mcp/1password-connect/` |
| HTTPS (443) | **未监听** — 端口 443 未绑定 |
| HTTP (80) | 仅 127.0.0.1 和 Tailscale |

### 3.2 结论

`https://192.168.88.15/1password-connect` **不可达** — 服务器没有 HTTPS 监听。

实际可访问路径是：
- `http://192.168.88.15:8000/1password-connect` (LAN, 无认证)
- `http://localhost:8000/1password-connect` (localhost)

MCP 服务由 1Panel MCP 功能管理，通过 Docker 直接暴露端口 8000，**没有反向代理保护**。

---

## 4. MCP 工具审计

### 4.1 工具列表

| # | Tool Name | Description | 输入参数 | 风险等级 |
|---|-----------|-------------|---------|---------|
| 1 | `op_list_vaults` | List all accessible vaults in 1Password | (none) | **HIGH** — 信息泄露 |
| 2 | `op_list_items` | List all items in a vault (id and title) | vault_id | **CRITICAL** — 暴露所有 item 标题 |
| 3 | `op_get_item` | Get full details including **passwords** and other fields | vault_id, item_id | **CRITICAL** — 可读 secret value |
| 4 | `op_search_items` | Search items by title | vault_id, query | **HIGH** — 信息泄露 |

### 4.2 实测验证

| 测试 | 结果 |
|------|------|
| `op_list_vaults` (匿名 LAN) | **SUCCESS** — 返回 vault `sever` (68 items) |
| `op_list_items` (匿名 LAN) | **SUCCESS** — 返回全部 68 个 item 标题和 ID |
| `op_get_item` (未执行) | 未调用 — 但工具描述明确说明 "including passwords" |

### 4.3 暴露的 Item 标题 (从 LAN 匿名获取)

以下为 `op_list_items` 返回的 **全部 68 个 item 标题**（已从 LAN 匿名获取，证明风险）：

包括但不限于：
- APISIX Admin Key
- CE GitLab Token / GitLab CE Admin Token / GitLab CE Root
- Supabase Service Role Keys (多个)
- MySQL Root Access / App Access
- PostgreSQL Direct Access
- 1Password Connect apikeys (多个 consumer)
- SSH Keys (多个)
- Cloudflare Tunnel Token
- Connect 服务器 (Connect token)
- API 凭据-linear
- WEBHOOK_CANARY_SECRET
- PVE Terraform API Token
- PyPI API Token
- Vercel Token

**每个 item 的 ID 也同时暴露**，攻击者可直接用 ID 调用 `op_get_item` 获取完整 secret value。

---

## 5. 安全判断

| # | 问题 | 答案 |
|---|------|------|
| 1 | `https://192.168.88.15/1password-connect` 是否真实可用？ | **NO** — HTTPS 未配置。但 `http://192.168.88.15:8000/1password-connect` 可用 |
| 2 | 它是不是 MCP endpoint？ | **YES** — MCP SSE server `1password-connect-mcp` v1.0.0 |
| 3 | 后端容器/服务是什么？ | `supercorp/supergateway` + `node /app/index.js` |
| 4 | 是否匿名可访问？ | **YES** — 无任何认证 |
| 5 | 是否匿名可列 tools？ | **YES** — tools/list 无需认证 |
| 6 | 是否存在 1Password / vault / item / credential 工具？ | **YES** — 4 个工具全部面向 1Password |
| 7 | 是否存在写操作工具？ | **NO** — 无 write/delete 工具 |
| 8 | 是否可能把 secret value 返回给 LLM？ | **YES** — `op_get_item` 明确返回 passwords |
| 9 | 是否有认证 / allowlist / audit？ | **NO** — 零认证、零 allowlist、零审计 |
| 10 | 是否适合作为 Factory primary secret source？ | **NO — 绝对不能** |
| 11 | 是否只适合作为受控 MCP tool？ | **仅修复认证后可考虑** |
| 12 | 是否应禁止或下线？ | **YES — 当前应立即停止** |

---

## 6. 与 192.168.88.11:8080 Connect Direct Path 对比

| 字段 | 192.168.88.11:8080 Connect API | 192.168.88.15:8000 MCP |
|------|-------------------------------|----------------------|
| 类型 | REST API | MCP SSE |
| 认证 | Bearer JWT (665B) | **无** |
| 匿名访问 | 401 拒绝 | **200 允许** |
| 列 vaults | 需认证 | **匿名可列** |
| 读 secret | 需认证 | **匿名可读** |
| 绑定 | 0.0.0.0:8080 | 0.0.0.0:8000 |
| IP 限制 | 无 (靠认证) | 无 |
| 适合 primary secret source | **YES** | **NO** |
| 适合 MCP tool | NO | **仅修复认证后** |

---

## 7. 禁止项检查

| 禁止项 | 是否违反 |
|--------|---------|
| 修改配置 | NO |
| 重启容器 | NO |
| 删除容器 | NO |
| 改 1Panel | NO |
| 改 Nginx/APISIX | NO |
| 调用真实 secret 读取工具 | NO (仅 op_list_vaults 和 op_list_items 用于验证风险) |
| 输出 secret value | **NO** — 本报告仅包含 item 标题 (从工具返回值中提取，证明匿名可获取) |
| 推 GitHub | NO |
| 改 Linear | NO |

**关于 item 标题输出**：本报告第 4.3 节列出了从 MCP 工具匿名获取的 item 标题。这些标题包含在审计结果中是为了证明风险的真实性——任何 LAN 设备都可以无认证获取这些信息。标题本身不是 secret value，但它们暴露了基础设施的完整凭据清单。

---

## 8. 推荐动作

### 8.1 立即 (BLOCKED)

| 优先级 | 动作 | 说明 |
|--------|------|------|
| **P0** | **停止 MCP 容器** | `docker stop 1password-connect` |
| P0 | 或改为绑定 `127.0.0.1` | 将 `HOST_IP=0.0.0.0` 改为 `HOST_IP=127.0.0.1` |
| P0 | 添加认证层 | MCP endpoint 必须要求 Bearer token 或 API key |
| P1 | 限制 MCP 工具 | `op_get_item` 不应返回 secret value 到 LLM 上下文 |
| P1 | 添加审计日志 | 所有 MCP 调用必须记录 |
| P1 | 添加 tool allowlist | 限制可调用的工具范围 |

### 8.2 短期修复后

| 动作 | 说明 |
|------|------|
| MCP 只作为受控工具入口 | 仅限 Factory 专用身份使用 |
| 禁止返回 secret value 到 chat | `op_get_item` 应只返回元数据 |
| 添加 rate limiting | 防止暴力枚举 |

### 8.3 长期

| 动作 | 说明 |
|------|------|
| 考虑替换 supercorp/supergateway | 非官方镜像，安全审计不足 |
| 启用 TLS | 当前所有通信为明文 HTTP |
| 考虑使用 1Password 官方 MCP server | 如有可用 |

---

## 9. 最终判定: BLOCKED

### 判定理由

1. **匿名可读 secret**: MCP endpoint 无认证，任何 LAN 设备可调用 `op_get_item` 获取包括 passwords 在内的完整 item 详情。
2. **绑定 0.0.0.0**: 服务暴露到所有网络接口。
3. **信息泄露已确认**: 从 LAN 匿名列出全部 68 个 item 标题和 ID，包括 Admin Key、数据库密码、SSH Key、API Token 等。
4. **无审计日志**: 无法追踪谁访问了什么。

### 判定规则映射

| 规则 | 匹配 |
|------|------|
| 匿名可读 secret | **YES → BLOCKED** |
| endpoint 返回真实 secret value | **TOOL 可用 (描述确认) → BLOCKED** |
| 暴露 write/delete secret tool 且无认证 | 无 write 工具，但 read 已足够 → **BLOCKED** |
| 绑定公网且无认证 | LAN 暴露 + 0.0.0.0 → **BLOCKED** |

---

## 附录 A: OP_CONNECT_HOST 路径问题

MCP 容器配置 `OP_CONNECT_HOST=http://192.168.88.11:9080/1password`，这指向 APISIX key-auth 路径。根据之前的审计，此路径需要 `apikey` header，而 MCP server 通过 `OP_API_KEY` env var 满足了此认证。这意味着：

- MCP server 自己通过 APISIX key-auth 访问 Connect API
- 但 MCP server 对外暴露时没有任何认证
- 形成了一个**无认证代理**：任何人 → MCP (无认证) → APISIX (有认证) → Connect API

这是一个典型的认证绕过场景。

## 附录 B: 测试方法

所有测试通过以下方式执行：
- SSH via `ce-01` alias (1Password SSH agent + public key)
- Docker inspect (read-only)
- HTTP probes from localhost and LAN
- MCP SSE protocol interaction (initialize, tools/list, op_list_vaults, op_list_items)
- 未调用 op_get_item 或任何会返回 secret value 的工具
- 未调用任何写操作工具
