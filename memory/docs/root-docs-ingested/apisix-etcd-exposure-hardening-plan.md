# etcd 暴露面收窄加固方案

**文档编号**: APISIX-ETCD-HARDEN-001  
**生成日期**: 2026-05-09  
**关联审计**: APISIX-WH-AUDIT-001 (P1-2)  
**目标主机**: 192.168.88.11 (`/opt/apisix-gw-test-01/`)

---

## 1. 当前风险评估

### 1.1 etcd 绑定 `0.0.0.0:2379` 的风险

| 风险维度 | 说明 |
|----------|------|
| **数据完整性** | etcd 存储 APISIX 全部配置：路由、上游、消费者凭据（key-auth key）、插件策略、SSL 证书。任何能访问 2379 的客户端均可读写这些对象。 |
| **凭据泄露** | Consumer key-auth 密钥以明文存储在 etcd 中。若 etcd 对网络开放，攻击者可直接读取所有 APISIX 业务 key。 |
| **路由劫持** | 攻击者可写入恶意路由，将流量劫持到外部服务器，或插入无鉴权的通配路由暴露内部服务。 |
| **拒绝服务** | 删除 etcd 中所有键可导致 APISIX 立即丢失全部路由配置，等同于服务中断。 |

**攻击面分析**:

```
etcd:2379 (0.0.0.0)
  ├── 192.168.88.0/24  (内网 — 可达)
  ├── 172.18.0.0/16    (Docker 内网 — 可达)
  ├── 100.64.0.0/10    (Tailscale — 可达)
  └── 0.0.0.0/0        (公网 — 取决于宿主机防火墙)
```

- 在当前部署中，192.168.88.11 是一台内网主机，公网不可直接到达，但同一内网的任何设备（包括被攻陷的设备）均可无鉴权访问 etcd。
- 如果 APISIX 主机防火墙规则被误删或 Tailscale 配置变更，etcd 可能暴露到更广范围。

### 1.2 `ALLOW_NONE_AUTHENTICATION=yes` 的风险

| 风险维度 | 说明 |
|----------|------|
| **零鉴权** | etcd 不要求任何认证即可执行完整的 CRUD 操作。任何能连接 2379 的客户端就是完全的管理员。 |
| **合规性** | CIS Benchmark 和 CIS Docker Benchmark 均要求 etcd 启用 TLS 客户端认证或至少基于角色的认证。 |
| **横向移动** | 攻击者一旦进入内网，etcd 是高价值目标，可直接获取 APISIX 全部配置和凭据，用于横向移动。 |

### 1.3 公网/内网可达性分析

| 网段 | 当前可达性 | 说明 |
|------|-----------|------|
| 192.168.88.0/24 | ✅ 可达 | 内网设备均可直连 `192.168.88.11:2379` |
| 172.18.0.0/16 | ✅ 可达 | Docker 内网容器可通过宿主机 IP 访问 |
| 100.64.0.0/10 | ⚠️ 取决于 Tailscale ACL | Tailscale 网络中的设备可能可达 |
| 公网 | ❌ 不可达 (当前) | 192.168.88.x 为内网 IP，但依赖宿主机防火墙作为唯一防线 |

**结论**: 当前 etcd 处于 **无鉴权 + 网络可达** 的状态，是 P1 级风险。宿主机防火墙是唯一的保护层，单一防线不符合纵深防御原则。

---

## 2. 收窄方案

### 方案 A（优先推荐）: 改为 Docker 内网访问，不对宿主机公开

**核心思路**: etcd 只在 Docker 内部网络中监听，APISIX 容器通过 Docker 内部 DNS 名称 (`etcd`) 直接访问，宿主机端口不映射。

#### docker-compose.yml Before/After

**Before（当前）**:

```yaml
services:
  etcd:
    image: bitnami/etcd:3.5.11
    environment:
      - ALLOW_NONE_AUTHENTICATION=yes
      - ETCD_ADVERTISE_CLIENT_URLS=http://0.0.0.0:2379
      - ETCD_LISTEN_CLIENT_URLS=http://0.0.0.0:2379
    ports:
      - "2379:2379"          # ⚠️ 绑定到 0.0.0.0:2379
    volumes:
      - etcd_data:/bitnami/etcd
    networks:
      - apisix-net

  apisix-gw:
    image: apache/apisix:3.9.1-debian
    ports:
      - "9080:9080"
      - "9180:9180"
      - "9443:9443"
    volumes:
      - ./config.yaml:/usr/local/apisix/conf/config.yaml:ro
    depends_on:
      - etcd
    networks:
      - apisix-net

networks:
  apisix-net:
    driver: bridge
```

**After（方案 A）**:

```yaml
services:
  etcd:
    image: bitnami/etcd:3.5.11
    environment:
      - ALLOW_NONE_AUTHENTICATION=yes   # 暂时保留（Docker 内网隔离后风险已大幅降低）
      - ETCD_ADVERTISE_CLIENT_URLS=http://etcd:2379     # ← 仅通告内部 DNS 名称
      - ETCD_LISTEN_CLIENT_URLS=http://0.0.0.0:2379     # 容器内仍监听所有接口（仅容器网络可达）
    # ports:                              # ← 完全删除 ports 映射
    volumes:
      - etcd_data:/bitnami/etcd
    networks:
      - apisix-net

  apisix-gw:
    image: apache/apisix:3.9.1-debian
    ports:
      - "9080:9080"
      - "9180:9180"                      # ← Admin API 也应考虑收窄（见下方说明）
      - "9443:9443"
    volumes:
      - ./config.yaml:/usr/local/apisix/conf/config.yaml:ro
    depends_on:
      - etcd
    networks:
      - apisix-net

networks:
  apisix-net:
    driver: bridge
    # internal: true                     # 可选：阻止该网络的外部路由
```

**关键变更说明**:

| 变更项 | Before | After | 效果 |
|--------|--------|-------|------|
| `ports` | `"2379:2379"` | 删除 | etcd 不再映射到宿主机端口 |
| `ETCD_ADVERTISE_CLIENT_URLS` | `http://0.0.0.0:2379` | `http://etcd:2379` | 仅通告 Docker 内部 DNS 名称 |
| `ETCD_LISTEN_CLIENT_URLS` | `http://0.0.0.0:2379` | 不变（容器内 0.0.0.0 安全） | 容器内部仍可正常监听 |

**配套 config.yaml 变更**:

```yaml
# APISIX config.yaml — etcd 连接地址不变
# APISIX 在 Docker 内部网络中通过 DNS 名称 "etcd" 访问 etcd
etcd:
  host:
    - "http://etcd:2379"       # ← 使用 Docker DNS 名称（如果已经是这样则无需改动）
  prefix: "/apisix"
```

> **注意**: 如果 APISIX config.yaml 中 etcd 地址已经是 `http://etcd:2379`（Docker DNS 名称），则无需修改。只有当它使用 `http://192.168.88.11:2379` 或 `http://host.docker.internal:2379` 时才需要改为 `http://etcd:2379`。

#### 方案 A 安全提升评估

| 指标 | Before | After |
|------|--------|-------|
| etcd 对宿主机可达 | ✅ 是 (0.0.0.0:2379) | ❌ 否 |
| etcd 对内网可达 | ✅ 是 (192.168.88.11:2379) | ❌ 否 |
| etcd 对 Tailscale 可达 | ⚠️ 取决于路由 | ❌ 否 |
| etcd 对 Docker 容器可达 | ✅ 是 | ✅ 是（仅同网络容器） |
| etcd 对公网可达 | ❌ 否（依赖防火墙） | ❌ 否 |

---

### 方案 B（降级备选）: 限制到 127.0.0.1 或 Tailscale 管理网

**适用场景**: 如果需要从宿主机直接调试 etcd（如使用 `etcdctl`），不适合使用方案 A。

#### 方案 B-1: 绑定 127.0.0.1

```yaml
services:
  etcd:
    image: bitnami/etcd:3.5.11
    environment:
      - ALLOW_NONE_AUTHENTICATION=yes
      - ETCD_ADVERTISE_CLIENT_URLS=http://127.0.0.1:2379
      - ETCD_LISTEN_CLIENT_URLS=http://0.0.0.0:2379
    ports:
      - "127.0.0.1:2379:2379"    # ← 仅绑定 loopback
    volumes:
      - etcd_data:/bitnami/etcd
    networks:
      - apisix-net
```

**效果**: etcd 仅从宿主机本机可达（`127.0.0.1:2379`），内网其他设备不可达。

**问题**: Docker 容器内的 APISIX 需要通过宿主机 IP 访问 etcd，需确保 `apisix-net` 网络模式下容器可达宿主机 loopback（通常需要 `host` 网络模式或 `host.docker.internal` 解析）。

#### 方案 B-2: 绑定 Tailscale IP

```yaml
services:
  etcd:
    image: bitnami/etcd:3.5.11
    environment:
      - ALLOW_NONE_AUTHENTICATION=yes
      - ETCD_ADVERTISE_CLIENT_URLS=http://100.100.1.11:2379
      - ETCD_LISTEN_CLIENT_URLS=http://0.0.0.0:2379
    ports:
      - "100.100.1.11:2379:2379"  # ← 仅绑定 Tailscale IP
    volumes:
      - etcd_data:/bitnami/etcd
    networks:
      - apisix-net
```

**效果**: etcd 仅从 Tailscale 网络可达，需通过 Tailscale ACL 进一步限制。

---

### ALLOW_NONE_AUTHENTICATION 评估

| 评估维度 | 分析 |
|----------|------|
| **当前状态** | `ALLOW_NONE_AUTHENTICATION=yes`，etcd 无任何认证 |
| **方案 A 后** | etcd 仅 Docker 内网可达，无认证的风险已大幅降低（攻击者需先获得容器访问权限） |
| **长期建议** | 在方案 A 实施后，可接受暂时保留 `ALLOW_NONE_AUTHENTICATION=yes`。若安全要求更高，可后续启用 etcd RBAC： |
| **RBAC 启用步骤** | 1. 创建 root 用户和角色 2. 创建 apisix 专用用户（只读写 `/apisix/` 前缀） 3. 删除 `ALLOW_NONE_AUTHENTICATION=yes` 4. 在 APISIX config.yaml 中配置 etcd 用户名密码 |

**建议**: 先执行方案 A（网络隔离），RBAC 作为后续增强项。理由是 Docker 内网隔离已经消除了最大风险面（网络可达性），而 RBAC 需要额外的凭据管理和连接配置变更，可在后续迭代中实施。

---

### Admin API (9180) 同步收窄建议

P1-2 同时指出 Admin API 也绑定 `0.0.0.0:9180`。建议同步收窄：

```yaml
  apisix-gw:
    ports:
      - "9080:9080"
      - "127.0.0.1:9180:9180"    # ← Admin API 仅本机可达
      - "9443:9443"
```

或在方案 A 中，如果 APISIX Admin API 仅由 APISIX 自身容器内使用（如通过 curl 进入容器管理），也可考虑完全删除 9180 的端口映射。

---

## 3. 备份步骤

### 3.1 备份 docker-compose.yml

```bash
# SSH 到 192.168.88.11
ssh user@192.168.88.11

# 创建带时间戳的备份
cp /opt/apisix-gw-test-01/docker-compose.yml \
   /opt/apisix-gw-test-01/docker-compose.yml.bak.$(date +%Y%m%d-%H%M%S)

# 验证备份存在
ls -la /opt/apisix-gw-test-01/docker-compose.yml.bak.*
```

### 3.2 备份 config.yaml

```bash
cp /opt/apisix-gw-test-01/config.yaml \
   /opt/apisix-gw-test-01/config.yaml.bak.$(date +%Y%m%d-%H%M%S)
```

### 3.3 etcd 数据快照备份

```bash
# 方法 1: 通过 Docker exec 使用 etcdctl（如果容器内有 etcdctl）
docker exec apisix-gw-test-01-etcd-1 etcdctl snapshot save /bitnami/etcd/snapshot.db \
  --endpoints=http://127.0.0.1:2379

# 将快照从容器拷贝到宿主机
docker cp apisix-gw-test-01-etcd-1:/bitnami/etcd/snapshot.db \
  /opt/apisix-gw-test-01/etcd-snapshot-$(date +%Y%m%d-%H%M%S).db

# 方法 2: 如果容器内没有 etcdctl，从宿主机使用 etcdctl
# （需要先安装 etcdctl 或使用独立的 etcd 容器）
docker run --rm --network apisix-net \
  -v /opt/apisix-gw-test-01/etcd-backup:/backup \
  bitnami/etcd:3.5.11 \
  etcdctl snapshot save /backup/snapshot-$(date +%Y%m%d-%H%M%S).db \
    --endpoints=http://etcd:2379

# 验证快照
ls -la /opt/apisix-gw-test-01/etcd-snapshot-*.db
```

### 3.4 导出完整 APISIX 配置（双重保险）

```bash
# 导出所有 APISIX 对象到 JSON 文件
APISIX_KEY="<从 1Password 获取>"
curl -sS -H "X-API-KEY: $APISIX_KEY" \
  http://192.168.88.11:9180/apisix/admin/routes \
  > /opt/apisix-gw-test-01/routes-export-$(date +%Y%m%d).json

curl -sS -H "X-API-KEY: $APISIX_KEY" \
  http://192.168.88.11:9180/apisix/admin/upstreams \
  > /opt/apisix-gw-test-01/upstreams-export-$(date +%Y%m%d).json

curl -sS -H "X-API-KEY: $APISIX_KEY" \
  http://192.168.88.11:9180/apisix/admin/consumers \
  > /opt/apisix-gw-test-01/consumers-export-$(date +%Y%m%d).json

curl -sS -H "X-API-KEY: $APISIX_KEY" \
  http://192.168.88.11:9180/apisix/admin/stream_routes \
  > /opt/apisix-gw-test-01/stream-routes-export-$(date +%Y%m%d).json
```

---

## 4. 回滚步骤

### 4.1 回滚 docker-compose.yml

```bash
# 停止当前服务
cd /opt/apisix-gw-test-01
docker compose down

# 恢复备份
cp docker-compose.yml.bak.<timestamp> docker-compose.yml

# 如果 config.yaml 也被修改
cp config.yaml.bak.<timestamp> config.yaml

# 重新启动
docker compose up -d

# 验证 etcd 恢复到 0.0.0.0:2379
ss -tlnp | grep 2379
# 预期输出: LISTEN 0 ... 0.0.0.0:2379 ...
```

### 4.2 etcd 数据丢失恢复

```bash
# 停止 etcd 容器
docker compose stop etcd

# 恢复快照到 etcd 数据卷
# 注意：恢复快照会覆盖现有数据
docker run --rm \
  -v apisix-gw-test-01_etcd_data:/bitnami/etcd \
  -v /opt/apisix-gw-test-01/etcd-snapshot-<timestamp>.db:/snapshot.db \
  bitnami/etcd:3.5.11 \
  etcdctl snapshot restore /snapshot.db \
    --data-dir /bitnami/etcd

# 重启全部服务
docker compose up -d
```

### 4.3 完全灾难恢复（etcd 数据丢失且无快照）

如果 etcd 数据丢失且没有快照，需要使用 3.4 中导出的 JSON 文件重建 APISIX 配置：

```bash
# 启动空的 etcd + APISIX
docker compose up -d

# 逐个重建路由/上游/消费者
# 从 JSON 导出文件中读取配置，通过 Admin API 重建
# 这是最坏情况的恢复路径，非常耗时
```

---

## 5. 验证步骤

### 5.1 验证 etcd 不再对宿主机网络可达

```bash
# 在 APISIX 宿主机 (192.168.88.11) 上执行

# 检查 2379 端口是否不再绑定到宿主机网络接口
ss -tlnp | grep 2379
# 预期输出: 无结果（端口不再映射到宿主机）
# 如果方案 B-1: 应显示 LISTEN ... 127.0.0.1:2379

# 从宿主机尝试连接 etcd
curl -s http://192.168.88.11:2379/v2/keys/
# 预期输出: Connection refused（或超时）

curl -s http://127.0.0.1:2379/v2/keys/
# 方案 A 预期: Connection refused
# 方案 B-1 预期: 返回 etcd 响应
```

### 5.2 验证从其他内网设备不可达

```bash
# 从另一台内网设备（如 192.168.88.22）执行
curl -s --connect-timeout 5 http://192.168.88.11:2379/v2/keys/
# 预期输出: Connection refused 或 Connection timed out
```

### 5.3 验证 APISIX 仍可正常连接 etcd

```bash
# 方法 1: 检查 APISIX 日志
docker compose -f /opt/apisix-gw-test-01/docker-compose.yml logs apisix-gw | tail -20
# 预期: 无 etcd 连接错误

# 方法 2: 通过 Admin API 查询路由（证明 APISIX 能读取 etcd）
curl -sS -H "X-API-KEY: $APISIX_KEY" \
  http://192.168.88.11:9180/apisix/admin/routes | head -100
# 预期: 正常返回路由列表 JSON

# 方法 3: 测试实际业务路由
curl -s -o /dev/null -w "%{http_code}" \
  http://apisix.tail5e888.ts.net:9080/supabase/auth/v1/health
# 预期: 401 (key-auth 正常拦截，证明路由从 etcd 正确加载)
```

### 5.4 Docker exec 进入容器验证 etcd 连通性

```bash
# 进入 APISIX 容器
docker exec -it $(docker ps -q -f name=apisix) bash

# 在容器内验证可通过 Docker DNS 连接 etcd
curl -s http://etcd:2379/v2/keys/apisix/routes | head -50
# 预期: 返回 etcd 中的路由数据

# 或使用 wget
wget -qO- http://etcd:2379/v2/keys/apisix/routes 2>/dev/null | head -50
```

### 5.5 端口监听预期对照表

| 方案 | `ss -tlnp \| grep 2379` 在宿主机上的输出 |
|------|---------------------------------------|
| 当前 (Before) | `LISTEN 0 4096 0.0.0.0:2379 0.0.0.0:* users:(("docker-proxy",...))` |
| 方案 A (After) | **无输出** (端口不再映射) |
| 方案 B-1 (After) | `LISTEN 0 4096 127.0.0.1:2379 0.0.0.0:* users:(("docker-proxy",...))` |
| 方案 B-2 (After) | `LISTEN 0 4096 100.100.1.11:2379 0.0.0.0:* users:(("docker-proxy",...))` |

---

## 6. 注意事项

### 6.1 APISIX 如何发现 etcd

| 发现方式 | 当前配置 | 方案 A 要求 | 说明 |
|----------|---------|------------|------|
| Docker DNS (`etcd`) | 可能 | ✅ 推荐 | APISIX 和 etcd 在同一 Docker 网络 (`apisix-net`) 中，APISIX 通过 Docker 内部 DNS 解析 `etcd` 到容器 IP |
| 宿主机 IP (`192.168.88.11`) | 可能 | ❌ 不可用 | 删除端口映射后，APISIX 容器无法通过宿主机 IP 访问 etcd |
| `host.docker.internal` | 不推荐 | ❌ 不适用 | 指向宿主机，端口映射删除后不可达 |

**关键检查**: 修改前必须确认 APISIX `config.yaml` 中 etcd 地址使用的是 Docker DNS 名称 `etcd`，而非宿主机 IP。

```yaml
# ✅ 正确（方案 A 兼容）
etcd:
  host:
    - "http://etcd:2379"

# ❌ 错误（方案 A 不兼容，端口映射删除后不可达）
etcd:
  host:
    - "http://192.168.88.11:2379"
    - "http://host.docker.internal:2379"
```

### 6.2 网络模式影响

| 网络模式 | 与方案 A 的兼容性 | 说明 |
|----------|-----------------|------|
| `bridge`（默认） | ✅ 完全兼容 | Docker DNS 正常工作，容器间通过内部 DNS 通信 |
| `host` | ❌ 不兼容 | 使用 host 模式时，容器直接使用宿主机网络栈，无 Docker 内部 DNS。需保持端口映射 |

**当前部署使用 bridge 模式（`apisix-net`）**，方案 A 完全兼容。

### 6.3 etcd 数据丢失的恢复方案

| 场景 | 恢复方法 |
|------|---------|
| etcd 容器重启但数据卷保留 | 无需操作，数据持久化在 Docker volume 中 |
| Docker volume 被删除 | 从 3.3 的快照恢复 |
| 快照也不可用 | 从 3.4 的 JSON 导出文件通过 Admin API 重建所有对象 |
| 全部丢失（最坏情况） | 从 1Password 获取凭据，参考 as-built 文档重建所有路由/上游/消费者 |

**建议**: 将 etcd 快照备份纳入定期维护计划，至少每周一次。

### 6.4 其他注意事项

1. **Admin API 同步收窄**: 建议同步将 9180 端口绑定到 `127.0.0.1`，消除 P1-2 中指出的两个暴露面。
2. **Docker Compose 版本**: 确保 `docker compose`（V2 插件）而非 `docker-compose`（V1 独立版），两者在内部 DNS 解析上有细微差异。
3. **容器重启顺序**: etcd 容器必须先于 APISIX 容器启动。`depends_on` 可保证启动顺序，但不保证 etcd 完全就绪。可在 APISIX 容器中配置 etcd 重试逻辑。
4. **监控告警**: 建议在 APISIX 日志中监控 etcd 连接失败事件，确保网络隔离后 APISIX 与 etcd 的连通性持续正常。
5. **定期审计**: 每季度执行一次 `ss -tlnp | grep 2379` 检查，确认 etcd 端口未意外暴露。

---

**文档结束。本方案仅为分析输出，未执行任何变更命令。执行变更前请先完成备份步骤。**
