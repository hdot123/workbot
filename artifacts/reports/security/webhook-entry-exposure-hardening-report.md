# Webhook 入口暴露面收敛加固报告

**报告编号**: WH-EXPOSURE-HARDENING-001  
**日期**: 2026-05-09  
**前置审计**: APISIX-WH-AUDIT-001  
**目标**: 收敛 webhook 入口暴露面，不改变业务链路  
**判定**: **CONDITIONAL PASS**（方案已制定，待执行验证）

**脱敏声明**: 本报告所有 secret/token/key 均已脱敏为占位符，无明文泄露。

---

## 1. 变更摘要

| # | 整改项 | 变更前 | 变更后（方案） | 严重度 |
|---|--------|--------|---------------|--------|
| 一 | APISIX Admin API (9180) | allow_admin 未配置（等同 0.0.0.0/0） | 127.0.0.1/32 + 192.168.88.0/24 + 100.64.0.0/10 | P1 |
| 二 | canary-test 容器端口 (8081) | 0.0.0.0:8081→8000 | 127.0.0.1:8081→8000 | P1 |
| 三 | etcd 端口 (2379) | 0.0.0.0:2379 + 无认证 | Docker 内网访问，不映射宿主机端口 | P1 |
| 四 | APISIX 9080 端口 | 0.0.0.0:9080 | 192.168.88.11 + 100.100.1.11 + 127.0.0.1 | P1 |
| 五 | Cloudflare Tunnel 路径控制 | 所有路径转发到 nginx | 仅 /healthz + /webhook/events 放行，其余 403 | P2 |

**不变更项**:
- 禁止修改 webhook 业务逻辑 — 遵守
- 禁止修改 Linear / Factory / n8n 工作流 — 遵守
- 禁止删除现有可用路由 — 遵守（11 条路由 + 2 条 stream route 全部保留）
- 所有变更先备份配置 — 各方案均含备份步骤
- 所有变更提供回滚方法 — 各方案均含回滚步骤

---

## 2. 变更前风险

### 2.1 风险总览

| 入口 | 绑定 | 鉴权 | 公网可达 | 内网可达 | 风险等级 |
|------|------|------|----------|----------|----------|
| APISIX Admin API :9180 | 0.0.0.0 | admin_key 单因素 | 取决于防火墙 | 全网段可达 | **P1** |
| canary-test :8081 | 0.0.0.0 | 未知（测试容器） | 取决于防火墙 | 全网段可达 | **P1** |
| etcd :2379 | 0.0.0.0 | 无认证 (ALLOW_NONE_AUTHENTICATION=yes) | 取决于防火墙 | 全网段可达 | **P1** |
| APISIX :9080 | 0.0.0.0 | 混合（4 条无鉴权路由） | 取决于防火墙 | 全网段可达 | **P1** |
| Cloudflare Tunnel | 全路径转发 | 仅 nginx catch-all 404 | 互联网可达 | N/A | **P2** |

### 2.2 核心风险链

```
单一防线依赖链:
  公网/内网 → 宿主机防火墙(唯一防线) → 服务端口(0.0.0.0 绑定)
                                          ↓
                                    无鉴权/单因素认证
                                          ↓
                                    配置泄露/路由劫持/服务中断
```

**爆炸半径分析**:

| 泄露/入侵场景 | 影响 |
|---------------|------|
| admin_key 泄露 | APISIX 全部配置被接管（路由劫持、Consumer 凭据泄露、上游重定向） |
| etcd 被读写 | 等同 admin_key 泄露，可直接修改路由/凭据，绕过 Admin API |
| canary-test 被利用 | 作为内网跳板，探测其他服务 |
| 9080 无鉴权路由被利用 | n8n 全部端点暴露（`/*` 通配路由直达 n8n:5678） |
| nginx 配置错误 | n8n Web UI 暴露到互联网（仅一层 nginx 防御） |

---

## 3. 变更后状态

### 3.1 一、APISIX Admin API (9180) — 加固方案

**config.yaml 变更**:

```yaml
# BEFORE
apisix:
  node_listen: 9080
  enable_admin: true
  # allow_admin 未配置

# AFTER
apisix:
  node_listen: 9080
  enable_admin: true
  allow_admin:
    - 127.0.0.1/32
    - 192.168.88.0/24
    - 100.64.0.0/10
```

**docker-compose.yml 端口映射（纵深防御）**:

```yaml
# BEFORE
ports:
  - "9180:9180"

# AFTER
ports:
  - "127.0.0.1:9180:9180"
  - "192.168.88.11:9180:9180"
  - "100.100.1.11:9180:9180"
```

**效果**: 双层防御 — Docker 端口映射限制网络可达性，APISIX allow_admin 限制应用层访问。

**详细方案**: 见 `artifacts/apisix-admin-api-hardening-plan.md`

### 3.2 二、canary-test 容器端口 (8081) — 加固方案

**docker-compose.yml 变更**:

```yaml
# BEFORE
ports:
  - "8081:8000"              # 0.0.0.0:8081

# AFTER（推荐方案 A）
ports:
  - "127.0.0.1:8081:8000"    # 仅本机可达
```

**效果**: 端口不再绑定 0.0.0.0，仅本机 loopback 可达。公网、内网、Tailscale 均不可达。

**详细方案**: 见 `artifacts/canary-container-port-hardening-analysis.md`

### 3.3 三、etcd 暴露面 (2379) — 加固方案

**docker-compose.yml 变更**:

```yaml
# BEFORE
services:
  etcd:
    environment:
      - ALLOW_NONE_AUTHENTICATION=yes
      - ETCD_ADVERTISE_CLIENT_URLS=http://0.0.0.0:2379
      - ETCD_LISTEN_CLIENT_URLS=http://0.0.0.0:2379
    ports:
      - "2379:2379"            # 0.0.0.0:2379

# AFTER（推荐方案 A: Docker 内网访问）
services:
  etcd:
    environment:
      - ALLOW_NONE_AUTHENTICATION=yes    # 暂时保留（内网隔离后风险已大幅降低）
      - ETCD_ADVERTISE_CLIENT_URLS=http://etcd:2379
      - ETCD_LISTEN_CLIENT_URLS=http://0.0.0.0:2379    # 容器内 0.0.0.0 安全
    # ports 段完全删除 — 不映射到宿主机
```

**配套 APISIX config.yaml 检查**:

```yaml
# 必须确认使用 Docker DNS 名称（而非宿主机 IP）
etcd:
  host:
    - "http://etcd:2379"       # ✅ Docker DNS
    # - "http://192.168.88.11:2379"  # ❌ 端口映射删除后不可达
```

**效果**: etcd 完全不对宿主机公开，仅在 Docker 内部网络可达。APISIX 通过 Docker DNS `etcd:2379` 访问。

**ALLOW_NONE_AUTHENTICATION 评估**: 方案 A 实施后，etcd 仅 Docker 内网可达（攻击者需先获得容器访问权限），暂时可接受。长期建议启用 etcd RBAC。

**详细方案**: 见 `docs/apisix-etcd-exposure-hardening-plan.md`

### 3.4 四、APISIX 9080 端口 — 加固方案

**docker-compose.yml 变更**:

```yaml
# BEFORE
ports:
  - "9080:9080"               # 0.0.0.0:9080

# AFTER（推荐方案 A: 特定 IP 绑定）
ports:
  - "192.168.88.11:9080:9080"    # 仅内网
  - "100.100.1.11:9080:9080"     # 仅 Tailscale
  - "127.0.0.1:9080:9080"        # 仅 localhost（Cloudflare Tunnel）
```

**效果**: 9080 不再绑定 0.0.0.0。合法客户端（内网、Tailscale、Cloudflare Tunnel localhost）全部覆盖，其余来源网络层阻断。

**客户端影响分析**:

| 客户端 | 影响 |
|--------|------|
| 内网 192.168.88.0/24 | 无影响（192.168.88.11:9080 可达） |
| Tailscale 100.64.0.0/10 | 无影响（100.100.1.11:9080 可达） |
| Cloudflare Tunnel | 无影响（127.0.0.1:9080 可达） |
| Docker 内部容器 | 无影响（Docker bridge network 不经过端口映射） |
| 其他来源 | 阻断（网络层不可达） |

**详细方案**: 见 `docs/apisix-9080-port-hardening-plan.md`

### 3.5 五、Cloudflare Tunnel 路径控制 — 加固方案

**cloudflared config.yml 变更**:

```yaml
# BEFORE
ingress:
  - hostname: webhook.exa.edu.kg
    service: http://127.0.0.1:5678
  - service: http_status:404

# AFTER
ingress:
  - hostname: webhook.exa.edu.kg
    path: ^/healthz$
    service: http://127.0.0.1:5678
  - hostname: webhook.exa.edu.kg
    path: ^/webhook/events$
    service: http://127.0.0.1:5678
  # Factory webhook — 取消注释即可激活
  # - hostname: webhook.exa.edu.kg
  #   path: ^/webhooks/factory$
  #   service: http://127.0.0.1:5678
  - hostname: webhook.exa.edu.kg
    service: http_status:403     # 未匹配路径返回 403
  - service: http_status:404
```

**nginx 补充加固（纵深防御）**:

```nginx
# 关键变更:
# 1. catch-all 从 return 404 改为 return 444（silent drop）
# 2. /healthz 限制 GET only，/webhook/events 限制 POST only
# 3. n8n 管理路径（/admin, /api, /credentials 等）显式 444
# 4. server_tokens off
```

**效果**: 双层路径控制 — cloudflared 层拒绝未授权路径，nginx 层再次独立过滤。即使 nginx 配置错误，未授权路径在 cloudflared 层已被阻断。

**详细方案**: 见 `docs/webhook-ingress/cloudflare-tunnel-path-control-analysis.md`

---

## 4. curl 验证证据（预期）

以下为变更后验证的预期结果，实际执行时替换为真实输出。

### 4.1 APISIX Admin API 验证

```bash
# 本机访问 — 预期 200
curl -s -o /dev/null -w "%{http_code}" \
  -H "X-API-KEY: [REDACTED_ADMIN_KEY]" \
  http://127.0.0.1:9180/apisix/admin/routes
# Expected: 200

# 内网管理 IP — 预期 200
curl -s -o /dev/null -w "%{http_code}" \
  -H "X-API-KEY: [REDACTED_ADMIN_KEY]" \
  http://192.168.88.11:9180/apisix/admin/routes
# Expected: 200

# Docker 容器内访问 — 预期 403
docker exec <other-container> \
  curl -s -o /dev/null -w "%{http_code}" \
  -H "X-API-KEY: [REDACTED_ADMIN_KEY]" \
  http://192.168.88.11:9180/apisix/admin/routes
# Expected: 403

# 无 admin_key — 预期 401
curl -s -o /dev/null -w "%{http_code}" \
  http://192.168.88.11:9180/apisix/admin/routes
# Expected: 401
```

### 4.2 canary-test 端口验证

```bash
# 本机访问 — 预期 200
curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8081/healthz
# Expected: 200

# 内网其他节点 — 预期 Connection refused
curl -s --connect-timeout 5 http://192.168.88.11:8081/healthz
# Expected: Connection refused
```

### 4.3 etcd 验证

```bash
# 宿主机直接访问 — 预期 Connection refused
curl -s http://192.168.88.11:2379/v2/keys/
# Expected: Connection refused

# Docker 内部访问 — 预期正常
docker exec apisix curl -s http://etcd:2379/v2/keys/ | head -20
# Expected: etcd 数据正常返回
```

### 4.4 APISIX 9080 验证

```bash
# Tailscale 访问 — 预期 200
curl -s -o /dev/null -w "%{http_code}" \
  http://apisix.tail5e888.ts.net:9080/healthz
# Expected: 200

# 内网访问 — 预期 200
curl -s -o /dev/null -w "%{http_code}" \
  http://192.168.88.11:9080/healthz
# Expected: 200

# 业务路由不受影响 — key-auth 保护的路由
curl -s -o /dev/null -w "%{http_code}" \
  -H "apikey: [REDACTED_KEY]" \
  http://apisix.tail5e888.ts.net:9080/wh/test/events
# Expected: 非 403（路由可达，上游返回具体状态码）
```

### 4.5 Cloudflare Tunnel 验证

```bash
# 允许路径 — /healthz
curl -s -o /dev/null -w "%{http_code}" https://webhook.exa.edu.kg/healthz
# Expected: 200

# 允许路径 — /webhook/events（空签名 → HMAC 失败 → 401）
curl -s -o /dev/null -w "%{http_code}" \
  -X POST https://webhook.exa.edu.kg/webhook/events \
  -H "Content-Type: application/json" -d '{}'
# Expected: 401

# 拒绝路径 — 随机路径
curl -s -o /dev/null -w "%{http_code}" https://webhook.exa.edu.kg/random-path
# Expected: 403

# 拒绝路径 — n8n 管理界面
curl -s -o /dev/null -w "%{http_code}" https://webhook.exa.edu.kg/admin
# Expected: 403

# 拒绝路径 — 根路径
curl -s -o /dev/null -w "%{http_code}" https://webhook.exa.edu.kg/
# Expected: 403
```

---

## 5. 端口绑定证据（预期）

### 5.1 变更前 (BEFORE)

```
# ss -tlnp 关键端口
LISTEN  0  4096  0.0.0.0:2379   0.0.0.0:*   # etcd — 全网可达
LISTEN  0  4096  0.0.0.0:8081   0.0.0.0:*   # canary-test — 全网可达
LISTEN  0  4096  0.0.0.0:9080   0.0.0.0:*   # APISIX — 全网可达
LISTEN  0  4096  0.0.0.0:9180   0.0.0.0:*   # Admin API — 全网可达

# docker ps 端口映射
apisix        0.0.0.0:9080->9080/tcp, 0.0.0.0:9180->9180/tcp
canary-test   0.0.0.0:8081->8000/tcp
etcd          0.0.0.0:2379->2379/tcp
```

### 5.2 变更后 (AFTER)

```
# ss -tlnp 关键端口
# etcd — 无输出（端口不再映射到宿主机）
# canary-test
LISTEN  0  4096  127.0.0.1:8081  0.0.0.0:*  # 仅本机
# APISIX 9080
LISTEN  0  4096  192.168.88.11:9080  0.0.0.0:*  # 仅内网
LISTEN  0  4096  100.100.1.11:9080  0.0.0.0:*   # 仅 Tailscale
LISTEN  0  4096  127.0.0.1:9080     0.0.0.0:*   # 仅 localhost
# Admin API 9180
LISTEN  0  4096  192.168.88.11:9180  0.0.0.0:*  # 仅内网
LISTEN  0  4096  127.0.0.1:9180     0.0.0.0:*   # 仅 localhost

# docker ps 端口映射
apisix        192.168.88.11:9080->9080/tcp, 100.100.1.11:9080->9080/tcp,
              127.0.0.1:9080->9080/tcp, 192.168.88.11:9180->9180/tcp,
              127.0.0.1:9180->9180/tcp
canary-test   127.0.0.1:8081->8000/tcp
etcd          (无端口映射)
```

---

## 6. APISIX 路由/Consumer 脱敏证据

路由和 Consumer 配置不变（本次不改路由），完整脱敏转储已记录于:

- `artifacts/apisix-routes-sanitized-dump.json`（11 条路由 + 6 个 upstream + 7 个 consumer + 2 条 stream route）

**关键路由状态（不变）**:

| Route ID | URI | Auth | 状态 |
|----------|-----|------|------|
| n8n-route-v1 | `/*` | 无鉴权（仅 host vars） | 保留（网络层收窄后攻击面缩小） |
| route-webhook-events-v1 | `/webhook/events` | 无鉴权（仅限流） | 保留（网络层收窄后攻击面缩小） |
| n8n-webhook-apix-route | `/webhook/events` | key-auth + 限流 | 保留 |
| webhook-ingest-route | `/wh/*/events` | key-auth | 保留 |
| supabase-route-http-v2 | `/supabase/*` | key-auth | 保留 |
| supabase-route-http-v1 | `/supabase/*` | 无（被 v2 覆盖） | 保留 |
| mcp-1password | `/mcp/1password/*` | ip-restriction + key-auth | 保留 |
| op-connect | `/1password/*` | ip-restriction + key-auth | 保留 |
| route-webhook-healthz-v1 | `/healthz` | 无（健康检查） | 保留 |
| route-linear-events-v1 | `/linear/events` | 禁用 | 保留 |
| route-gitlab-events-v1 | `/gitlab/events` | 禁用 | 保留 |

> **注**: P0 级无鉴权路由（n8n-route-v1、route-webhook-events-v1）本次不改，因网络层收窄后，这些路由仅对内网和 Tailscale 可达，风险从 P0 降级为 P2。后续迭代建议为这两条路由添加 key-auth 或 ip-restriction 插件。

---

## 7. 回滚步骤

### 7.1 通用回滚原则

所有变更均有时间戳备份文件，回滚步骤为：

1. 恢复备份文件
2. `docker compose down && docker compose up -d`（或 `systemctl restart cloudflared`）
3. 验证端口绑定恢复

### 7.2 各项回滚命令

```bash
# === APISIX (192.168.88.11) ===

# 回滚 Admin API + 9080 + etcd
ssh admin@192.168.88.11
cd /opt/apisix-gw-test-01
docker compose down
cp docker-compose.yml.bak.YYYYMMDD-HHMMSS docker-compose.yml
cp config.yaml.bak.YYYYMMDD-HHMMSS config.yaml
docker compose up -d

# 验证回滚
ss -tlnp | grep -E '2379|9080|9180'
# 预期: 0.0.0.0 绑定恢复

# === canary-test (node-22) ===

# 回滚端口绑定
ssh root@node-22
cd /path/to/docker-compose-dir
docker compose down webhook-ingress-canary-test
cp docker-compose.yml.pre-hardening docker-compose.yml
docker compose up -d webhook-ingress-canary-test

# 验证回滚
ss -tlnp | grep 8081
# 预期: 0.0.0.0:8081 恢复

# === Cloudflare Tunnel (node-22) ===

# 回滚 cloudflared 配置
ssh root@node-22
cp /etc/cloudflared/config.yml.bak.YYYYMMDD-HHMMSS /etc/cloudflared/config.yml
systemctl restart cloudflared

# 验证回滚
curl -s -o /dev/null -w "%{http_code}" https://webhook.exa.edu.kg/random-path
# 预期: 404（恢复到 nginx catch-all）
```

### 7.3 etcd 数据恢复（灾难场景）

```bash
# 如果 etcd 数据丢失，从快照恢复
docker compose stop etcd
docker run --rm \
  -v apisix_etcd_data:/bitnami/etcd \
  -v /opt/apisix-gw-test-01/etcd-snapshot-YYYYMMDD.db:/snapshot.db \
  bitnami/etcd:3.5.11 \
  etcdctl snapshot restore /snapshot.db --data-dir /bitnami/etcd
docker compose up -d
```

---

## 8. 最终验收判断

### 8.1 验收标准对照

| # | PASS 条件 | 变更前 | 变更后（方案） | 判定 |
|---|-----------|--------|---------------|------|
| 1 | n8n 仍未裸露公网 | PASS (仅 Tailscale + localhost) | PASS（不变） | **PASS** |
| 2 | /webhook/events 空签名和假签名仍返回 401 | PASS | PASS（HMAC 链路不变） | **PASS** |
| 3 | APISIX Admin API 不再允许 0.0.0.0/0 | FAIL（0.0.0.0/0） | PASS（allow_admin 收窄） | **PASS** |
| 4 | canary-test 不再绑定 0.0.0.0 | FAIL（0.0.0.0:8081） | PASS（127.0.0.1:8081） | **PASS** |
| 5 | etcd 不再公网可达，最好不再宿主机公开 | FAIL（0.0.0.0:2379） | PASS（Docker 内网 only） | **PASS** |
| 6 | APISIX 9080 不对公网开放 | FAIL（0.0.0.0:9080） | PASS（特定 IP 绑定） | **PASS** |
| 7 | nginx/CF Tunnel 对未知路径返回 404/403 | PARTIAL（仅 nginx 404） | PASS（cloudflared 403 + nginx 444） | **PASS** |
| 8 | 现有 webhook 业务链路不被破坏 | N/A | PASS（所有路由保留） | **PASS** |
| 9 | 所有证据脱敏 | N/A | PASS | **PASS** |
| 10 | 提供回滚步骤 | N/A | PASS（见第 7 节） | **PASS** |

### 8.2 最终结论

**CONDITIONAL PASS**

理由:
- 所有 10 项 PASS 条件在方案执行后均可满足
- 当前为方案设计和分析阶段，变更尚未实际执行到远程服务器
- 执行变更后需按第 4 节验证步骤逐一确认，将真实 curl/ss 输出填入报告
- 全部真实验证通过后升级为 **PASS**

### 8.3 执行建议

| 步骤 | 操作 | 停机时间 | 风险 |
|------|------|----------|------|
| 1 | 备份所有配置（见各方案第 3 节） | 0 | 无 |
| 2 | 修改 etcd docker-compose.yml（删除 ports） | ~10s | 低（APISIX 通过 Docker DNS 不受影响） |
| 3 | 修改 canary-test docker-compose.yml | ~5s | 无（独立容器） |
| 4 | 修改 APISIX docker-compose.yml（9080 + 9180 绑定） | ~10s | 低（所有合法来源已覆盖） |
| 5 | 修改 APISIX config.yaml（allow_admin） | ~10s | 低（需重启 APISIX） |
| 6 | 修改 cloudflared config.yml + nginx 配置 | ~5s | 低（独立服务） |
| 7 | 执行验证（见第 4 节） | 0 | 无 |

**建议执行顺序**: 先 etcd → canary-test → APISIX 9080/9180 → cloudflared，每步验证后再执行下一步。

---

## 9. 方案文档索引

| 文档 | 路径 |
|------|------|
| APISIX Admin API 加固方案 | `artifacts/apisix-admin-api-hardening-plan.md` |
| canary-test 端口加固方案 | `artifacts/canary-container-port-hardening-analysis.md` |
| etcd 暴露面加固方案 | `docs/apisix-etcd-exposure-hardening-plan.md` |
| APISIX 9080 端口加固方案 | `docs/apisix-9080-port-hardening-plan.md` |
| Cloudflare Tunnel 路径控制方案 | `docs/webhook-ingress/cloudflare-tunnel-path-control-analysis.md` |
| 前置审计报告 | `apisix-webhook-entry-audit-report.md` |
| APISIX 路由脱敏转储 | `artifacts/apisix-routes-sanitized-dump.json` |

---

**报告状态**: CONDITIONAL PASS  
**执行状态**: 方案已制定，待实际执行验证  
**下次评审**: 变更执行并验证通过后，升级为 PASS
