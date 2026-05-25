# 1Password Connect 全流程调查报告

**报告编号**: WORKBOT-1PCONNECT-001  
**日期**: 2026-05-08  
**执行**: 10 子代理并行调查  
**结论**: 全流程已查明，Connect API 健康可用

---

## 1. 完整架构图

```
1Password Cloud (my.1password.com)
      │
      │ 加密同步 (WebSocket/轮询)
      ▼
┌──────────────────────────────────────────────────────────┐
│ apisix-gw-test-01 (192.168.88.11 / 100.100.1.11)        │
│                                                          │
│  ┌─────────────────────────────────────┐                │
│  │ op-connect-sync (:8081, 127.0.0.1)  │                │
│  │ 1password/connect-sync:latest       │                │
│  │ 同步 vault/keys 从 1P Cloud         │                │
│  │ ✅ 每小时同步，无错误                │                │
│  └──────────────┬──────────────────────┘                │
│                 │ localhost:8081                        │
│  ┌──────────────▼──────────────────────┐                │
│  │ op-connect-api (:8080, 0.0.0.0)     │                │
│  │ 1password/connect-api:latest v1.8.2 │                │
│  │ REST API: /v1/vaults, /v1/items ... │                │
│  │ ✅ 健康：sqlite ACTIVE, sync ACTIVE │                │
│  │ ✅ 0 restarts, uptime 3 days        │                │
│  │ ⚠️ Docker healthcheck: false positive│                │
│  └──────────────┬──────────────────────┘                │
│                 │ HTTP                                  │
│  ┌──────────────▼──────────────────────┐                │
│  │ APISIX/3.9.1 (:9080)                │                │
│  │ route: /1password/*                 │                │
│  │  ├── key-auth (apikey header)       │                │
│  │  ├── ip-restriction (whitelist)     │                │
│  │  ├── proxy-rewrite:                 │                │
│  │  │    strip /1password prefix       │                │
│  │  │    inject Authorization: Bearer  │                │
│  │  └── upstream → :8080 (connect-api)│                │
│  └─────────────────────────────────────┘                │
│                                                          │
│  ┌─────────────────────────────────────┐                │
│  │ n8n (:5678) + etcd (:2379)         │                │
│  └─────────────────────────────────────┘                │
└──────────────────────────────────────────────────────────┘
        │
        │ APISIX key-auth + Bearer token
        ▼
┌──────────────────────────────────────────────────────────┐
│ 客户端 (LAN / Tailscale)                                  │
│  • `op` CLI (OP_CONNECT_HOST + OP_CONNECT_TOKEN)         │
│  • 脚本/自动化 (apikey header → APISIX)                   │
│  • AI Agent MCP (已移除: ce-01 supergateway)              │
└──────────────────────────────────────────────────────────┘
```

## 2. 完整请求链路

```
Client
  │
  │ GET http://192.168.88.11:9080/1password/v1/vaults
  │ Header: apikey: <APISIX consumer key>
  │
  ▼
APISIX /1password/* route (id: op-connect)
  │
  │ 1. ip-restriction: 检查源 IP 在白名单内
  │    ✅ 192.168.88.0/24, 100.64.0.0/10, 127.0.0.1, 172.16.0.0/12
  │
  │ 2. key-auth: 验证 apikey header
  │    ✅ consumer: 1password_connect_ro (48 char hex key)
  │    ⚠️ 所有 7 个 consumer 都可访问此路由（无 consumer-restriction 插件）
  │
  │ 3. proxy-rewrite:
  │    regex_uri: ^/1password/(.*) → /$1  (strip prefix)
  │    headers.set.Authorization: Bearer <665 char JWT token>
  │
  │ 4. upstream: op-connect → 192.168.88.11:8080
  │
  ▼
op-connect-api (:8080)
  │
  │ 接收: GET /v1/vaults
  │       Header: Authorization: Bearer <JWT>
  │
  │ 查询本地 SQLite + connect-sync 缓存
  │
  ▼
op-connect-sync (:8081, localhost)
  │
  │ 本地 gRPC 通信，返回缓存数据
  │ 每小时从 1P Cloud 同步一次
  │
  ▼
响应: HTTP 200 [{"id":"ozqqpvh5yvvxvyu64npq62a3ti","name":"sever","items":76,...}]
```

## 3. 健康检查结果

| 组件 | 状态 | 详情 |
|------|------|------|
| **op-connect-api** | ✅ **HEALTHY** | 4/4 dependencies ACTIVE, 响应 <10ms |
| **op-connect-sync** | ✅ **HEALTHY** | 每小时同步完成，版本匹配 ✅ |
| **APISIX route** | ✅ **ACTIVE** | key-auth + ip-restriction + proxy-rewrite 全生效 |
| **SQLite DB** | ✅ **OK** | WAL 1.3MB，正常活跃 |
| **credentials.json** | ✅ **OK** | 1093 bytes, 权限 0600 |
| **Docker healthcheck** | ⚠️ FALSE POSITIVE | distroless 镜像缺 curl/sh，不影响服务 |
| **容器重启次数** | 0 | 稳定运行 3 天 |
| **内存占用** | ~20MB | API 9.3MB + Sync 10.7MB |

## 4. APISIX 路由完整配置

| 属性 | 值 |
|------|-----|
| Route ID | `op-connect` |
| Route Name | `1password-connect` |
| URIs | `/1password/*` |
| Status | 1 (active) |
| Upstream | `op-connect` → `192.168.88.11:8080` |
| **Plugins** | |
| → ip-restriction | whitelist: 192.168.88.0/24, 100.64.0.0/10, 127.0.0.1, 172.16.0.0/12 |
| → key-auth | header=`apikey`, query=`apikey` |
| → proxy-rewrite | regex_uri: `^/1password/(.*)` → `/$1`, inject Bearer token |

## 5. Consumer 审计（7 个）

| # | Username | Key Length | 可访问 1password | 描述 |
|---|----------|-----------|-----------------|------|
| 1 | `1password_connect_ro` | 48 | ✅ | 1Password Connect 只读 |
| 2 | `gitlab_runner` | 48 | ✅ ⚠️ | ce-01 GitLab Runner |
| 3 | `n8n_automation` | 48 | ✅ ⚠️ | n8n 自动化 |
| 4 | `n8n_webhook_consumer` | 24 | ✅ ⚠️ | n8n webhook |
| 5 | `supabase_client_v1` | 64 | ✅ ⚠️ | Supabase 客户端 |
| 6 | `test_source` | 28 | ✅ ⚠️ | 测试源 |
| 7 | `webhook_ingress` | 48 | ✅ ⚠️ | webhook-ingress on node-22 |

**⚠️ 安全发现**: 路由无 `consumer-restriction` 插件，**所有 7 个 consumer 均可访问** 1Password Connect。建议添加 consumer-restriction 限制仅 `1password_connect_ro` 访问。

## 6. 凭据清单

| 凭据 | 用途 | 存储位置 | 注入方式 |
|------|------|---------|---------|
| `1password-credentials.json` (1093B) | connect-sync 部署凭据 | `/opt/1password-connect/` 挂载 ro | 容器启动读取 |
| `OP_SESSION` (~1.6KB JWT) | Connect Server 云认证 | compose .env | Docker env var |
| APISIX Bearer Token (665B JWT) | proxy-rewrite 注入 | APISIX route config | 自动注入 header |
| APISIX apikey `1password_connect_ro` (48B) | 客户端认证 | APISIX consumer | 客户端 `apikey` header |
| APISIX Admin Key (64B) | Admin API 管理 | config.yaml | X-API-Key header |

## 7. 访问路径表

| 来源 | URL | 可用 | 认证 |
|------|-----|------|------|
| LAN (192.168.88.x) | `http://192.168.88.11:9080/1password/v1/vaults` | ✅ | `apikey` header |
| LAN (192.168.88.x) | `http://192.168.88.11:8080/v1/vaults` | ✅ | `Authorization: Bearer` |
| Tailscale (100.64.x.x) | `http://apisix.tail5e888.ts.net:9080/1password/v1/vaults` | ✅ | `apikey` header |
| 外部 | 任何 | ❌ | 被 IP restriction + 私有 IP 阻挡 |

## 8. ce-01 supergateway 状态

| 项目 | 状态 |
|------|------|
| 容器 | 已删除（用户手动移除） |
| 功能 | MCP SSE 桥接（stdio → SSE） |
| 之前崩溃原因 | `/app/index.js` 未挂载 |
| 修复 | 已添加 volume mount，但用户选择移除 |
| Connect API | 不受影响，仍通过 APISIX 正常工作 |

## 9. 单点故障分析

| SPOF | 影响范围 | 恢复 |
|------|---------|------|
| apisix-gw-test-01 主机 | 全部服务中断 | 主机级恢复 |
| op-connect-api | API 读取失败 → APISIX 502 | 重启容器 |
| op-connect-sync | 数据过期，仍可提供缓存 | 重启容器，全量同步 |
| etcd | APISIX 路由全部失效 | 重启 etcd + APISIX |
| 1P Cloud 连接 | 同步暂停，本地缓存继续 | 网络恢复后自动同步 |

## 10. 安全建议

| 优先级 | 建议 |
|--------|------|
| 🔴 高 | 添加 APISIX `consumer-restriction` 插件，限制 1password-connect 路由仅 `1password_connect_ro` 访问 |
| 🟡 中 | 启用 TLS（当前全部明文 HTTP，apikey/Bearer token 在 LAN 上可被嗅探） |
| 🟡 中 | 缩紧 ce-01 UFW 规则：13191(1Panel)、3100 端口限制到特定 IP |
| 🟢 低 | 修复 Docker healthcheck（distroless 镜像缺 curl/sh，改用 HTTP 探测） |
| 🟢 低 | `/1password/*` 路由建议记录到 as-built 文档 |

## 11. 最终判定

**✅ 全流程已查明，Connect API 健康可用**

- Connect API v1.8.2 正常运行，所有依赖 ACTIVE
- APISIX 路由完整，key-auth + ip-restriction + proxy-rewrite 全生效
- 同步正常，每小时从 1P Cloud 同步，vault sever 含 76 个 item
- 通过 APISIX 可正常列出 vault、读取 item 元数据
- 无 secret 泄露（报告中所有凭据值已脱敏）
