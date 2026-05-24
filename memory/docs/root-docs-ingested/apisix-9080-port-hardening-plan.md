# APISIX 9080 端口暴露面收窄方案

**文档编号**: APISIX-HARDEN-9080-001  
**生成日期**: 2026-05-09  
**生成代理**: worker subagent (security hardening analysis)  
**状态**: 分析方案，待执行  

---

## 1. 当前风险评估

### 1.1 APISIX 9080 绑定 0.0.0.0 的风险

APISIX 当前 `node_listen: [80, 9080]`，Docker 容器以 `0.0.0.0:9080` 形式映射到宿主机。这意味着：

| 风险维度 | 说明 |
|----------|------|
| **内网全开放** | 192.168.88.0/24 网段内任何设备均可直接访问 `192.168.88.11:9080` |
| **Tailscale 全开放** | Tailscale 网络内任何设备均可访问 `100.100.1.11:9080` 和 `apisix.tail5e888.ts.net:9080` |
| **潜在公网暴露** | 若宿主机有公网 IP 或路由规则不当，9080 将直接暴露到公网；即使当前无公网 IP，未来网络变更可能引入风险 |
| **零网络层防御** | 无 iptables/nftables 规则限制 9080 的访问源；完全依赖 APISIX 插件层做鉴权 |

### 1.2 内网/Tailscale 可达性与公网可达性

| 来源 | 可达性 | 说明 |
|------|--------|------|
| **192.168.88.0/24 内网** | ✅ 可达 | 交换机/路由器广播域内所有设备 |
| **100.64.0.0/10 Tailscale** | ✅ 可达 | Tailscale Mesh 内所有已认证节点 |
| **公网** | ⚠️ 未确认 | 宿主机 192.168.88.11 无直接公网 IP，但网关路由规则未验证；Cloudflare Tunnel 的 `cloudflared` 进程绑定 `localhost` 可间接触达 |
| **Docker 内部网络** | ✅ 可达 | 同一 Docker network 内容器可通过 `apisix:9080` 互访 |

### 1.3 现有无鉴权路由的暴露风险

9080 端口上当前存在 **4 条无鉴权路由**，其中 2 条为 P0 级风险：

| 路由 ID | URI | 风险等级 | 说明 |
|---------|-----|----------|------|
| **n8n-route-v1** | `/*` | **P0-CRITICAL** | 通配路由无鉴权直达 n8n:5678；任何可达客户端均可访问 n8n 全部端点 |
| **route-webhook-events-v1** | `/webhook/events` | **P0-HIGH** | 无鉴权，接受 ALL HTTP 方法，仅限流 100/min；且优先级 10 高于同路径的鉴权路由 |
| **route-webhook-healthz-v1** | `/healthz` | **LOW** | 健康检查，仅 GET/HEAD，限流 200/min；设计上可接受 |
| **supabase-route-http-v1** | `/supabase/*` | **MEDIUM** | 无鉴权但被 v2（priority 10）覆盖；若 v2 被删除则回退到无鉴权 |

**核心问题**：9080 绑定 `0.0.0.0` 意味着以上所有无鉴权路由对内网和 Tailscale 全网开放。即使为路由添加鉴权，网络层仍无纵深防御。

---

## 2. 收窄方案

### 2.1 APISIX 9080 是否需要绑定 0.0.0.0？

**不需要。** 当前 9080 的合法客户端来源明确：

| 客户端 | 来源 IP/网段 | 访问方式 |
|--------|-------------|----------|
| 内网设备 | 192.168.88.0/24 | `192.168.88.11:9080` |
| Tailscale 节点 | 100.64.0.0/10 | `100.100.1.11:9080` 或 `apisix.tail5e888.ts.net:9080` |
| Cloudflare Tunnel (cloudflared) | 127.0.0.1 | `localhost:9080` |
| Docker 内部容器 | Docker bridge | `apisix:9080` (容器名) |

以上客户端可通过 **Tailscale IP + 内网 IP + localhost** 全部覆盖，无需 `0.0.0.0`。

### 2.2 方案 A: 改为 Tailscale IP + 内网 IP + localhost bind（推荐 ✅）

**原理**：修改 `docker-compose.yml` 的 `ports` 映射，将 `0.0.0.0:9080` 改为绑定到特定 IP 地址。

#### docker-compose.yml before/after 对比

**BEFORE（当前）**:

```yaml
services:
  apisix:
    image: apache/apisix:3.8.0-debian
    ports:
      - "80:80"
      - "9080:9080"        # ← 绑定 0.0.0.0:9080，全网可达
      - "9180:9180"        # ← Admin API，同样绑定 0.0.0.0（风险）
      - "9443:9443"
      - "3306:3306"        # ← MySQL stream
      - "5432:5432"        # ← PostgreSQL stream
    # ...
```

**AFTER（方案 A）**:

```yaml
services:
  apisix:
    image: apache/apisix:3.8.0-debian
    ports:
      - "80:80"
      - "192.168.88.11:9080:9080"    # ← 仅内网可达
      - "100.100.1.11:9080:9080"     # ← 仅 Tailscale 可达
      - "127.0.0.1:9080:9080"        # ← 仅 localhost（Cloudflare Tunnel）
      - "192.168.88.11:9180:9180"    # ← Admin API 仅内网
      - "127.0.0.1:9180:9180"        # ← Admin API localhost
      - "9443:9443"
      - "192.168.88.11:3306:3306"    # ← MySQL stream 仅内网
      - "100.100.1.11:3306:3306"     # ← MySQL stream Tailscale
      - "192.168.88.11:5432:5432"    # ← PostgreSQL stream 仅内网
      - "100.100.1.11:5432:5432"     # ← PostgreSQL stream Tailscale
    # ...
```

> **注意**: 同一容器端口可以映射到宿主机的多个 IP，Docker 支持这种写法。

**优势**:
- 网络层直接阻断未授权来源
- 不依赖宿主机防火墙（防火墙是附加层）
- Docker 内部容器间通信不受影响（走 Docker bridge network）
- 配置简单、可审计

**劣势**:
- IP 变更时需要修改 docker-compose.yml 并重启容器
- Tailscale IP 变更（极罕见）需要同步更新

### 2.3 方案 B: 保持 0.0.0.0 但依赖宿主机防火墙

**原理**：保持 Docker 绑定 `0.0.0.0:9080`，通过 iptables/nftables 规则限制来源 IP。

```bash
# 示例 iptables 规则
iptables -A INPUT -p tcp --dport 9080 -s 192.168.88.0/24 -j ACCEPT
iptables -A INPUT -p tcp --dport 9080 -s 100.64.0.0/10 -j ACCEPT
iptables -A INPUT -p tcp --dport 9080 -s 127.0.0.1 -j ACCEPT
iptables -A INPUT -p tcp --dport 9080 -j DROP
```

**优势**:
- 无需修改 docker-compose.yml
- 运行时动态调整规则

**劣势**:
- 防火墙规则是"软防御"，重启丢失（需持久化）
- Docker 的 iptables 操作可能覆盖自定义规则
- 依赖运维记忆，不可审计
- 单点防御，无纵深

### 2.4 方案 C: 使用 Docker network 内部 + nginx/SOCKS 反代

**原理**：将 APISIX 的 `ports` 改为仅暴露到 Docker 内部网络，前置 nginx 或 SOCKS5 反代做访问控制。

```yaml
services:
  apisix:
    ports:
      - "80:80"
      # 9080 不映射到宿主机
    networks:
      - internal

  nginx-proxy:
    image: nginx:alpine
    ports:
      - "192.168.88.11:9080:9080"
      - "100.100.1.11:9080:9080"
    networks:
      - internal
```

**优势**:
- APISIX 完全不暴露到宿主机网络
- 可以在 nginx 层做更精细的访问控制

**劣势**:
- 增加一层网络跳转，增加延迟和故障点
- 配置复杂度显著增加
- 需要维护额外的 nginx 配置
- 对 stream routes (3306/5432) 支持困难

### 2.5 推荐方案及理由

**推荐方案 A**，理由：

1. **最小变更**：仅修改 docker-compose.yml 的 ports 映射
2. **最大安全性**：网络层直接阻断，不依赖上层防御
3. **不影响功能**：所有合法客户端来源均被覆盖
4. **可审计**：变更在 Git 管理的配置文件中
5. **可回滚**：恢复 `0.0.0.0` 即可
6. **不删除任何现有路由**：所有 11 条路由和 2 条 stream routes 保持不变

---

## 3. 对路由的影响分析

### 3.1 改变绑定 IP 后受影响的客户端

#### 3.1.1 内网 192.168.88.0/24 客户端

| 影响 | 说明 |
|------|------|
| ✅ **无影响** | `192.168.88.11:9080` 绑定保留，内网客户端访问路径不变 |
| ✅ Stream routes | `192.168.88.11:3306` 和 `192.168.88.11:5432` 绑定保留 |

受影响路由（访问路径不变，功能正常）：
- `/supabase/*` → key-auth 保护 → 192.168.88.16:8000
- `/webhook/events` → n8n:5678（无鉴权路由仍可到达）
- `/wh/*/events` → key-auth 保护 → 192.168.88.37:3100
- `/mcp/1password/*` → ip-restriction + key-auth
- `/1password/*` → ip-restriction + key-auth
- `/healthz` → n8n 健康检查
- `/*` → n8n 通配路由

#### 3.1.2 Tailscale 100.64.0.0/10 客户端

| 影响 | 说明 |
|------|------|
| ✅ **无影响** | `100.100.1.11:9080` 绑定保留，Tailscale 客户端访问路径不变 |
| ✅ 域名访问 | `apisix.tail5e888.ts.net:9080` 解析到 Tailscale IP，正常工作 |

受影响路由：同上，全部正常。

#### 3.1.3 Cloudflare Tunnel (localhost) 客户端

| 影响 | 说明 |
|------|------|
| ✅ **无影响** | `127.0.0.1:9080` 绑定保留，cloudflared 进程间接待达 |
| ⚠️ 注意 | 需确认 cloudflared 配置中使用的上游地址是 `http://localhost:9080` 或 `http://127.0.0.1:9080` |

**验证点**: 检查 cloudflared 配置文件（通常在 `~/.cloudflared/config.yml` 或 `/etc/cloudflared/config.yml`），确认 `url` 字段指向 `http://localhost:9080`。

#### 3.1.4 Docker 内部容器间通信

| 影响 | 说明 |
|------|------|
| ✅ **无影响** | Docker ports 绑定只影响宿主机到容器的端口映射 |
| ✅ 容器间 | 同一 Docker network 内容器仍通过容器名（如 `apisix:9080`）直接通信，不经过宿主机端口映射 |

**关键**：APISIX 路由中引用的 `n8n:5678`、`1password-connect-mcp:8000` 等 Docker 内部服务名不受任何影响。

### 3.2 被阻断的访问来源

| 来源 | 变更前 | 变更后 |
|------|--------|--------|
| 公网（若有） | ⚠️ 可能可达 | ❌ 不可达 |
| 其他 Docker network | ⚠️ 可能可达 | ❌ 不可达 |
| 同网段未授权设备 | ⚠️ 可达（需 APISIX 鉴权） | ❌ 不可达（网络层阻断） |
| 非 192.168.88.0/24 非 Tailscale 非 localhost | ⚠️ 可达 | ❌ 不可达 |

---

## 4. 备份步骤

```bash
# 1. SSH 到 APISIX 宿主机 (192.168.88.11)
ssh admin@192.168.88.11

# 2. 备份当前 docker-compose.yml
sudo cp /opt/apisix-gw-test-01/docker-compose.yml \
        /opt/apisix-gw-test-01/docker-compose.yml.bak.$(date +%Y%m%d-%H%M%S)

# 3. 备份当前 APISIX 配置
sudo cp /opt/apisix-gw-test-01/config.yaml \
        /opt/apisix-gw-test-01/config.yaml.bak.$(date +%Y%m%d-%H%M%S)

# 4. 导出当前 APISIX 路由快照（用于回滚对比）
curl -s http://127.0.0.1:9180/apisix/admin/routes \
  -H 'X-API-KEY: [REDACTED_ADMIN_KEY]' | jq . > \
  /tmp/apisix-routes-backup-$(date +%Y%m%d-%H%M%S).json

# 5. 导出 upstream 快照
curl -s http://127.0.0.1:9180/apisix/admin/upstreams \
  -H 'X-API-KEY: [REDACTED_ADMIN_KEY]' | jq . > \
  /tmp/apisix-upstreams-backup-$(date +%Y%m%d-%H%M%S).json

# 6. 导出 stream_routes 快照
curl -s http://127.0.0.1:9180/apisix/admin/stream_routes \
  -H 'X-API-KEY: [REDACTED_ADMIN_KEY]' | jq . > \
  /tmp/apisix-stream-routes-backup-$(date +%Y%m%d-%H%M%S).json

# 7. 记录当前容器状态
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" > \
  /tmp/apisix-containers-backup-$(date +%Y%m%d-%H%M%S).txt
```

---

## 5. 回滚步骤

```bash
# 1. SSH 到 APISIX 宿主机
ssh admin@192.168.88.11

# 2. 查找备份文件
ls -la /opt/apisix-gw-test-01/docker-compose.yml.bak.*

# 3. 停止当前容器
cd /opt/apisix-gw-test-01
sudo docker compose down

# 4. 恢复备份
sudo cp docker-compose.yml.bak.YYYYMMDD-HHMMSS docker-compose.yml

# 5. 重新启动
sudo docker compose up -d

# 6. 验证容器状态
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# 7. 验证端口绑定
ss -tlnp | grep -E '9080|9180|3306|5432'

# 8. 功能验证（参见第 6 节）
```

---

## 6. 验证步骤

### 6.1 端口绑定验证

```bash
# 在 APISIX 宿主机上执行，确认端口绑定到正确 IP
ss -tlnp | grep 9080
# 预期输出应包含:
# LISTEN  0  4096  192.168.88.11:9080  ...
# LISTEN  0  4096  100.100.1.11:9080  ...
# LISTEN  0  4096  127.0.0.1:9080     ...
# 不应出现 0.0.0.0:9080
```

### 6.2 Tailscale 可访问

```bash
# 从 Tailscale 客户端执行
curl -s -o /dev/null -w "%{http_code}" http://apisix.tail5e888.ts.net:9080/healthz
# 预期: 200

curl -s http://apisix.tail5e888.ts.net:9080/healthz
# 预期: n8n 健康检查响应

# Supabase 路由 (需 key-auth)
curl -s -o /dev/null -w "%{http_code}" \
  -H "apikey: <VALID_KEY>" \
  http://apisix.tail5e888.ts.net:9080/supabase/rest/v1/
# 预期: 200
```

### 6.3 内网可访问

```bash
# 从内网设备 (192.168.88.0/24) 执行
curl -s -o /dev/null -w "%{http_code}" http://192.168.88.11:9080/healthz
# 预期: 200

# Stream routes
mysql -h 192.168.88.11 -P 3306 -u <user> -p<pass> -e "SELECT 1"
# 预期: 成功连接

psql -h 192.168.88.11 -p 5432 -U <user> -c "SELECT 1"
# 预期: 成功连接
```

### 6.4 公网不可访问

```bash
# 从外部网络（非内网、非 Tailscale）执行
# 如果有外部 VPS，从 VPS 执行:
curl -s -o /dev/null -w "%{http_code}" --connect-timeout 5 \
  http://192.168.88.11:9080/healthz
# 预期: 连接超时 (connection refused 或 timeout)

curl -s -o /dev/null -w "%{http_code}" --connect-timeout 5 \
  http://100.100.1.11:9080/healthz
# 预期: 连接超时 (100.x.x.x 不路由到公网)

# 也可通过 nmap 扫描确认
nmap -p 9080 192.168.88.11
# 预期: filtered 或 closed（从外部扫描）
```

### 6.5 /webhooks/factory 路由不受影响

```bash
# webhook-ingest-route (/wh/*/events) - key-auth 保护
curl -s -o /dev/null -w "%{http_code}" \
  -X POST \
  -H "apikey: <VALID_WEBHOOK_INGRESS_KEY>" \
  -H "Content-Type: application/json" \
  -d '{"test": true}' \
  http://apisix.tail5e888.ts.net:9080/wh/factory/events
# 预期: 非 403/401（路由可达，上游返回具体状态码）

# 无 apikey 时应被拒绝
curl -s -o /dev/null -w "%{http_code}" \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{"test": true}' \
  http://apisix.tail5e888.ts.net:9080/wh/factory/events
# 预期: 401
```

### 6.6 Docker 内部通信不受影响

```bash
# 在 APISIX 宿主机上执行
docker exec apisix curl -s -o /dev/null -w "%{http_code}" http://n8n:5678/healthz
# 预期: 200（容器间通信正常）

# 验证 APISIX 路由引用的 n8n upstream 仍可用
docker exec apisix curl -s http://n8n:5678/healthz
# 预期: n8n 健康检查响应
```

### 6.7 Cloudflare Tunnel 验证

```bash
# 在 APISIX 宿主机上确认 cloudflared 可达 localhost:9080
curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:9080/healthz
# 预期: 200

# 从外部通过 Cloudflare 域名验证（如 webhook.exa.edu.kg）
curl -s -o /dev/null -w "%{http_code}" https://webhook.exa.edu.kg/healthz
# 预期: 200（Cloudflare → cloudflared → localhost:9080 → APISIX → n8n）
```

---

## 附录 A: 完整方案 A docker-compose.yml diff

```diff
--- a/docker-compose.yml (BEFORE)
+++ b/docker-compose.yml (AFTER - 方案 A)
@@
 services:
   apisix:
     image: apache/apisix:3.8.0-debian
     ports:
       - "80:80"
-      - "9080:9080"
+      - "192.168.88.11:9080:9080"
+      - "100.100.1.11:9080:9080"
+      - "127.0.0.1:9080:9080"
-      - "9180:9180"
+      - "192.168.88.11:9180:9180"
+      - "127.0.0.1:9180:9180"
       - "9443:9443"
-      - "3306:3306"
+      - "192.168.88.11:3306:3306"
+      - "100.100.1.11:3306:3306"
-      - "5432:5432"
+      - "192.168.88.11:5432:5432"
+      - "100.100.1.11:5432:5432"
```

## 附录 B: 注意事项

1. **Tailscale IP 稳定性**: `100.100.1.11` 是 Tailscale 分配的 IP。Tailscale IP 在节点不删除的情况下保持稳定。若 Tailscale 节点被重建，需更新 docker-compose.yml。
2. **80 端口和 9443 端口**: 当前未做绑定收窄。若 80 端口承载的业务也需收窄，可同样改为 IP 绑定。建议后续单独评估。
3. **Admin API (9180)**: 同样建议收窄。Admin API 控制 APISIX 全部路由配置，暴露到 `0.0.0.0` 风险极高。
4. **路由不做变更**: 本方案仅收窄网络绑定，不修改、不删除任何 APISIX 路由。11 条路由和 2 条 stream routes 保持原状。
5. **并行加固建议**: 收窄绑定后，仍建议对 `n8n-route-v1` 和 `route-webhook-events-v1` 添加鉴权插件，作为纵深防御。
