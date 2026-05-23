# APISIX Admin API Hardening — 收窄方案与验证步骤

**文档编号**: APISIX-ADMIN-HARDENING-001  
**日期**: 2026-05-09  
**类型**: 安全加固分析与操作方案  
**脱敏声明**: 所有 secret/token/key 均使用占位符替代，无明文泄露  
**目标主机**: 192.168.88.11 (apisix-gw-test-01)  

---

## 1. 当前风险评估

### 1.1 Admin API 绑定 `0.0.0.0:9180` 的风险

| 风险维度 | 详情 |
|----------|------|
| **监听范围** | `0.0.0.0:9180` 表示 APISIX Admin API 在所有网络接口上监听，包括回环、内网、Tailscale、Docker 桥接网络 |
| **攻击面** | 任何可达 192.168.88.11:9180 的网络客户端都可以向 Admin API 发送请求 |
| **单点防线** | 当前唯一的防护是 `admin_key`（通过 `X-API-KEY` header 传递）。没有 IP 层面的 `allow_admin` 白名单作为第二道防线 |
| **配置文件层面** | 当前 `config.yaml` 中 `allow_admin` 未配置或配置为 `0.0.0.0/0`（等价于无限制） |
| **默认行为** | APISIX 默认在 `allow_admin` 未设置时允许所有 IP 访问 Admin API，仅依赖 `admin_key` 做认证 |

### 1.2 谁当前可以访问

| 网络范围 | 可达性 | 说明 |
|----------|--------|------|
| `127.0.0.1` (本机回环) | ✅ 可达 | APISIX 容器内/宿主机本机 |
| `192.168.88.0/24` (局域网) | ✅ 可达 | 同一 LAN 内所有设备 |
| `100.64.0.0/10` (Tailscale) | ✅ 可达 | 所有 Tailscale 网络成员 |
| `172.16.0.0/12` (Docker 内网) | ✅ 可达 | 同一 Docker 网络内的容器 |
| `0.0.0.0/0` (理论所有 IP) | ✅ 可达 | 如果端口被路由/端口转发暴露到外部，则公网可达 |

**实际威胁场景**：
- 局域网内任何被入侵的设备都可以尝试暴力破解 `admin_key`
- 如果 Tailscale 网络中有不受控设备，也可以访问
- Docker 网络中任何容器（包括被攻陷的容器）都可以调用 Admin API

### 1.3 `admin_key` 泄露的爆炸半径

如果 `admin_key` 泄露，攻击者可以在当前配置下（无 IP 白名单）从任何可达网络执行以下操作：

| 攻击能力 | 影响 | 严重度 |
|----------|------|--------|
| **读取所有路由配置** | 获取上游地址、路径映射、插件配置，包括 Supabase Anon Key（嵌入在 proxy-rewrite 中） | **CRITICAL** |
| **创建/修改路由** | 将流量劫持到攻击者控制的上游，实现中间人攻击 | **CRITICAL** |
| **删除路由** | 造成服务拒绝（DoS），所有业务入口（Supabase/MySQL/PostgreSQL/webhook）不可用 | **CRITICAL** |
| **读取所有 Consumer** | 获取所有 `key-auth` 密钥，进而模拟合法客户端访问受保护服务 | **CRITICAL** |
| **创建新 Consumer** | 持久化后门，绕过现有鉴权 | **HIGH** |
| **修改 Upstream** | 将业务流量重定向到恶意服务 | **CRITICAL** |
| **读取 stream_route** | 了解 MySQL/PostgreSQL 转发目标和 IP 白名单 | **HIGH** |
| **修改 SSL/TLS 配置** | 如果启用了 HTTPS，可以替换证书实现中间人 | **HIGH** |

**综合爆炸半径**：Admin API 拥有对 APISIX 全部配置对象的完整 CRUD 权限。`admin_key` 泄露等价于整个 API 网关被接管。

---

## 2. 收窄方案

### 2.1 目标 `allow_admin` 配置

将 Admin API 的 IP 白名单从 `0.0.0.0/0`（或未配置）收窄到以下三个网段：

| CIDR | 用途 | 说明 |
|------|------|------|
| `127.0.0.1/32` | 本机回环 | APISIX 容器自身、宿主机本机管理 |
| `192.168.88.0/24` | 局域网管理 | 内网管理操作来源 |
| `100.64.0.0/10` | Tailscale 管理网段 | 远程管理通过 Tailscale VPN |

**不包含**：
- `172.16.0.0/12`（Docker 内网）：Docker 容器不应直接调用 Admin API
- `0.0.0.0/0`（全网）：不应对所有 IP 开放

### 2.2 `config.yaml` 修改片段（before/after 对比）

#### BEFORE（当前配置 — 不安全）

```yaml
apisix:
  node_listen: 9080
  enable_admin: true
  # allow_admin 未配置或配置为以下（等价于无限制）：
  # allow_admin:
  #   - 0.0.0.0/0
```

#### AFTER（收窄后配置 — 加固）

```yaml
apisix:
  node_listen: 9080
  enable_admin: true
  allow_admin:
    - 127.0.0.1/32
    - 192.168.88.0/24
    - 100.64.0.0/10
```

### 2.3 完整 `config.yaml` 中 `allow_admin` 配置示例

```yaml
# ============================================================
# APISIX config.yaml — Admin API 加固配置片段
# ============================================================

apisix:
  # --- 节点监听 ---
  node_listen:
    - 9080
  enable_admin: true

  # --- Admin API IP 白名单（加固后）---
  # 仅允许以下网段访问 9180 端口的 Admin API：
  #   127.0.0.1/32     → 本机回环（容器自身 + 宿主机 localhost）
  #   192.168.88.0/24  → 内网管理网段
  #   100.64.0.0/10    → Tailscale 管理网段
  # 不包含 Docker 桥接网络（172.16.0.0/12），容器不应直连 Admin API
  allow_admin:
    - 127.0.0.1/32
    - 192.168.88.0/24
    - 100.64.0.0/10

  # --- Admin API 监听端口 ---
  # 注意：端口绑定由 Docker 端口映射控制（见下方 Docker 建议）
  # 如果 APISIX 在 Docker 中运行，建议将端口映射从 0.0.0.0:9180
  # 收窄到 127.0.0.1:9180 或特定管理 IP
```

### 2.4 Docker Compose 端口映射加固（附加建议）

如果 APISIX 通过 Docker Compose 部署，建议同时收窄端口映射：

#### BEFORE

```yaml
services:
  apisix:
    ports:
      - "9180:9180"    # 绑定 0.0.0.0:9180
```

#### AFTER

```yaml
services:
  apisix:
    ports:
      - "127.0.0.1:9180:9180"           # 仅本机
      - "192.168.88.11:9180:9180"       # 内网管理 IP
      - "100.100.1.11:9180:9180"        # Tailscale IP
```

> **注意**：如果 Docker 端口映射收窄后，从 Docker 内部（其他容器）访问 Admin API 将不可达。这符合预期——只有宿主机层和指定管理 IP 可以到达。

---

## 3. 备份步骤

### 3.1 备份 APISIX config.yaml

```bash
# 在 APISIX 主机 (192.168.88.11) 上执行

# 如果 config.yaml 在 Docker volume 中：
docker cp apisix:/usr/local/apisix/conf/config.yaml \
  ./config.yaml.backup.$(date +%Y%m%d-%H%M%S)

# 如果 config.yaml 在宿主机挂载目录中：
cp /path/to/apisix/conf/config.yaml \
   /path/to/apisix/conf/config.yaml.backup.$(date +%Y%m%d-%H%M%S)

# 如果使用 Docker Compose，也备份 docker-compose.yml：
cp docker-compose.yml docker-compose.yml.backup.$(date +%Y%m%d-%H%M%S)
```

### 3.2 导出当前全量 APISIX 配置快照

```bash
# 导出所有路由
curl -sS -H "X-API-KEY: [REDACTED_ADMIN_KEY]" \
  http://192.168.88.11:9180/apisix/admin/routes \
  | jq '.' > apisix-routes-backup.$(date +%Y%m%d-%H%M%S).json

# 导出所有 upstream
curl -sS -H "X-API-KEY: [REDACTED_ADMIN_KEY]" \
  http://192.168.88.11:9180/apisix/admin/upstreams \
  | jq '.' > apisix-upstreams-backup.$(date +%Y%m%d-%H%M%S).json

# 导出所有 consumer
curl -sS -H "X-API-KEY: [REDACTED_ADMIN_KEY]" \
  http://192.168.88.11:9180/apisix/admin/consumers \
  | jq '.' > apisix-consumers-backup.$(date +%Y%m%d-%H%M%S).json

# 导出所有 stream_route
curl -sS -H "X-API-KEY: [REDACTED_ADMIN_KEY]" \
  http://192.168.88.11:9180/apisix/admin/stream_routes \
  | jq '.' > apisix-stream-routes-backup.$(date +%Y%m%d-%H%M%S).json

# 导出所有 ssl（如有）
curl -sS -H "X-API-KEY: [REDACTED_ADMIN_KEY]" \
  http://192.168.88.11:9180/apisix/admin/ssl \
  | jq '.' > apisix-ssl-backup.$(date +%Y%m%d-%H%M%S).json
```

---

## 4. 回滚步骤

### 4.1 恢复原 config.yaml

```bash
# 在 APISIX 主机 (192.168.88.11) 上执行

# 恢复 config.yaml（使用之前备份的文件）
cp /path/to/apisix/conf/config.yaml.backup.YYYYMMDD-HHMMSS \
   /path/to/apisix/conf/config.yaml

# 如果 config.yaml 在 Docker volume 中：
docker cp config.yaml.backup.YYYYMMDD-HHMMSS \
  apisix:/usr/local/apisix/conf/config.yaml
```

### 4.2 恢复 Docker Compose 端口映射（如果修改了）

```bash
# 恢复 docker-compose.yml
cp docker-compose.yml.backup.YYYYMMDD-HHMMSS docker-compose.yml
```

### 4.3 重启 APISIX 使回滚生效

```bash
# Docker Compose 方式
docker compose restart apisix

# 或完整重建（如果修改了 docker-compose.yml）
docker compose down apisix && docker compose up -d apisix
```

### 4.4 验证回滚成功

```bash
# 确认 Admin API 恢复为无 IP 限制（回滚到原始状态）
# 应该可以从任意可达 IP 访问
curl -sS -H "X-API-KEY: [REDACTED_ADMIN_KEY]" \
  http://192.168.88.11:9180/apisix/admin/routes \
  | jq '.node.nodes | length'
```

---

## 5. 验证步骤

### 5.1 本机可访问 Admin API

```bash
# 在 APISIX 主机 (192.168.88.11) 上执行
# 来源 IP: 127.0.0.1 → 应该被 allow_admin 允许

curl -sS -o /dev/null -w "%{http_code}" \
  -H "X-API-KEY: [REDACTED_ADMIN_KEY]" \
  http://127.0.0.1:9180/apisix/admin/routes

# 期望: 200
```

### 5.2 内网管理 IP 可访问 Admin API

```bash
# 从内网管理机 (192.168.88.x) 执行
# 来源 IP: 192.168.88.x → 应该被 192.168.88.0/24 允许

curl -sS -o /dev/null -w "%{http_code}" \
  -H "X-API-KEY: [REDACTED_ADMIN_KEY]" \
  http://192.168.88.11:9180/apisix/admin/routes

# 期望: 200
```

### 5.3 Tailscale IP 可访问 Admin API

```bash
# 从 Tailscale 网络中的管理机执行
# 来源 IP: 100.x.x.x → 应该被 100.64.0.0/10 允许

curl -sS -o /dev/null -w "%{http_code}" \
  -H "X-API-KEY: [REDACTED_ADMIN_KEY]" \
  http://100.100.1.11:9180/apisix/admin/routes

# 期望: 200
```

### 5.4 非授权 IP 不可访问

```bash
# 从 Docker 内网容器中执行（如果可能）
# 来源 IP: 172.18.x.x → 不在 allow_admin 中，应该被拒绝

# 方法 1：从另一个 Docker 容器内访问
docker exec -it <other-container> \
  curl -sS -o /dev/null -w "%{http_code}" \
  -H "X-API-KEY: [REDACTED_ADMIN_KEY]" \
  http://192.168.88.11:9180/apisix/admin/routes

# 期望: 403 (Forbidden)
# APISIX 会返回 {"error_msg":"Your IP address is not allowed"}

# 方法 2：从不受信任的内网 IP 访问（如果有多网卡）
# 如果 APISIX 宿主机有其他网段 IP，尝试从该网段访问
# 期望: 403
```

### 5.5 无 admin_key 不可访问（确认认证仍然有效）

```bash
# 不带 admin_key 的请求应被拒绝
curl -sS -o /dev/null -w "%{http_code}" \
  http://192.168.88.11:9180/apisix/admin/routes

# 期望: 401 (Unauthorized)
```

### 5.6 错误 admin_key 不可访问

```bash
# 带错误 admin_key 的请求应被拒绝
curl -sS -o /dev/null -w "%{http_code}" \
  -H "X-API-KEY: wrong-key-value" \
  http://192.168.88.11:9180/apisix/admin/routes

# 期望: 401 (Unauthorized)
```

### 5.7 admin_key 仍然有效（从授权 IP 发起）

```bash
# 从授权 IP (192.168.88.x) 使用正确 admin_key
curl -sS -H "X-API-KEY: [REDACTED_ADMIN_KEY]" \
  http://192.168.88.11:9180/apisix/admin/routes \
  | jq '.node.nodes | keys'

# 期望: 返回所有路由 ID 列表
```

### 5.8 业务路由未受影响

```bash
# 确认 Supabase 业务入口仍然正常
curl -sS -o /dev/null -w "%{http_code}" \
  http://apisix.tail5e888.ts.net:9080/supabase/auth/v1/health \
  -H "apikey: [REDACTED_CLIENT_KEY]"

# 期望: 200

# 确认无 key 的请求仍然被拒绝
curl -sS -o /dev/null -w "%{http_code}" \
  http://apisix.tail5e888.ts.net:9080/supabase/auth/v1/health

# 期望: 401
```

### 5.9 验证矩阵总结

| # | 来源 IP | 目标 | 带 Key | 期望状态码 | 验证点 |
|---|---------|------|--------|-----------|--------|
| 1 | `127.0.0.1` | `127.0.0.1:9180` | ✅ 正确 key | 200 | 本机允许 |
| 2 | `192.168.88.x` | `192.168.88.11:9180` | ✅ 正确 key | 200 | 内网允许 |
| 3 | `100.x.x.x` | `100.100.1.11:9180` | ✅ 正确 key | 200 | Tailscale 允许 |
| 4 | `172.18.x.x` | `192.168.88.11:9180` | ✅ 正确 key | 403 | Docker 容器拒绝 |
| 5 | `192.168.88.x` | `192.168.88.11:9180` | ❌ 无 key | 401 | 认证仍有效 |
| 6 | `192.168.88.x` | `192.168.88.11:9180` | ❌ 错误 key | 401 | 认证仍有效 |
| 7 | `192.168.88.x` | `:9080/supabase/...` | ✅ 业务 key | 200 | 业务不受影响 |

---

## 6. 注意事项

### 6.1 是否需要重启 APISIX

**是的，需要重启。**

- `config.yaml` 中的 `allow_admin` 是启动时加载的配置项
- 修改后必须重启 APISIX 进程才能生效
- 热加载（`apisix reload`）可能生效，但官方建议对 `config.yaml` 的修改通过重启确保

### 6.2 Docker Compose 场景下的操作方式

```bash
# 步骤 1: 修改 config.yaml（挂载卷方式）
vim /path/to/apisix/conf/config.yaml
# 添加 allow_admin 配置

# 步骤 2: 重启 APISIX 容器
docker compose restart apisix

# 步骤 3: 检查容器状态
docker compose ps apisix

# 步骤 4: 检查 APISIX 日志确认启动正常
docker compose logs --tail=50 apisix

# 步骤 5: 执行验证步骤（见第 5 节）
```

### 6.3 Docker 端口映射与 APISIX `allow_admin` 的关系

| 防线 | 作用层 | 说明 |
|------|--------|------|
| Docker 端口映射 | 宿主机网络层 | 控制哪些宿主机 IP 接收到的流量会转发到容器 |
| APISIX `allow_admin` | 应用层 | APISIX 在处理请求时检查客户端 IP 是否在白名单中 |

**推荐**：两层都配置，实现纵深防御：
1. Docker 端口映射收窄到管理 IP → 减少网络可达性
2. APISIX `allow_admin` 收窄到管理网段 → 应用层二次校验

### 6.4 etcd 访问安全（关联风险）

- 当前 etcd (2379) 也绑定在 `0.0.0.0`
- `allow_admin` 不影响 etcd 的访问控制
- etcd 的加固应作为独立的后续任务处理
- 建议后续将 etcd 也收窄到内网管理 IP + Tailscale

### 6.5 已知影响范围

| 操作/服务 | 是否受影响 | 说明 |
|-----------|-----------|------|
| Admin API 管理（路由/Consumer/Upstream CRUD） | ✅ 受影响 | 仅授权 IP 可访问 |
| 业务流量 (`:9080`) | ❌ 不受影响 | `allow_admin` 仅影响 Admin API (`:9180`) |
| Stream 代理 (`:3306`, `:5432`) | ❌ 不受影响 | Stream 路由使用 `ip-restriction` 插件独立控制 |
| etcd 通信 | ❌ 不受影响 | APISIX 内部与 etcd 的通信不经过 Admin API |
| APISIX Dashboard（如果部署了） | ⚠️ 需确认 | Dashboard 通过 Admin API 操作，其来源 IP 需在白名单中 |

### 6.6 操作时间窗口建议

- 建议在低峰期执行（如业务量最低时段）
- 预计影响时间：重启 APISIX 约 5-10 秒
- 在重启期间，所有经过 APISIX 的业务流量会短暂中断
- 准备好回滚方案，如果验证失败可在 1 分钟内恢复

---

## 附录 A: 当前 APISIX 配置快照参考

以下信息来自 `apisix-routes-sanitized-dump.json`：

```json
{
  "metadata": {
    "source": "apisix-gw-test-01 (192.168.88.11)",
    "admin_listen": "0.0.0.0:9180",
    "node_listen": [80, 9080],
    "stream_proxy_tcp": [3306, 5432]
  }
}
```

## 附录 B: 相关风险条目参考

以下风险条目来自 `apisix-webhook-entry-audit-report.md`：

| 编号 | 风险 | 说明 |
|------|------|------|
| P1-2 | APISIX Admin API (9180) 和 etcd (2379) 绑定 0.0.0.0 | 依赖宿主机防火墙做唯一防线；误操作可导致 admin 暴露 |

本文档即为 P1-2 的详细加固方案。
