# Canary Container Port Hardening Analysis

**分析编号**: CANARY-PORT-HARDENING-001  
**分析日期**: 2026-05-09  
**分析类型**: 端口暴露面收窄方案（只读分析，不执行）  
**目标容器**: webhook-ingress-canary-test  
**宿主机**: node-22 (43.167.177.86 公网 / 192.168.88.11 内网 / 100.100.1.22 Tailscale)  

---

## 1. 当前风险评估

### 1.1 假设当前绑定: `0.0.0.0:8081→8000`

如果 canary-test 容器的 `docker-compose.yml` ports 段配置为 `"8081:8000"` 或 `"0.0.0.0:8081:8000"`，则端口绑定行为如下：

| 绑定地址 | 含义 | 实际效果 |
|----------|------|----------|
| `0.0.0.0:8081` | 监听所有网卡的 8081 端口 | 公网 + 内网 + Tailscale 全部可达 |

### 1.2 公网可达性分析

| 访问路径 | 是否可达 | 风险等级 | 说明 |
|----------|----------|----------|------|
| `http://43.167.177.86:8081` | **可能可达** | **P0** | 除非宿主机防火墙 (iptables/nftables/ufw) 明确 DROP 了 8081 入站，否则公网可直接访问 |
| `http://192.168.88.11:8081` | 可达 | P1 | 内网所有节点可达 |
| `http://100.100.1.22:8081` | 可达 | P2 | Tailscale 网络内可达 |
| `http://127.0.0.1:8081` | 可达 | 安全 | 仅本机 |

### 1.3 风险矩阵

| 风险 | 等级 | 说明 |
|------|------|------|
| **公网暴露测试端点** | P0 | canary-test 是测试/验证容器，其鉴权模型可能与生产不同（或无鉴权），公网可达 = 攻击面扩大 |
| **信息泄露** | P1 | 测试容器可能暴露调试信息、内部 API 结构、健康检查细节 |
| **未授权操作** | P1 | canary test 端点可能允许触发测试 webhook、写入测试数据到 Supabase，影响数据完整性 |
| **SSRF 跳板** | P2 | 如果 canary-test 可达内网其他服务，攻击者可将其作为内网跳板 |
| **违反最小暴露原则** | P1 | 测试容器不应有公网可见性，违反 defense-in-depth |

### 1.4 防火墙依赖风险

当前如果 `0.0.0.0:8081` 绑定，**唯一防线是宿主机防火墙**。根据 APISIX 审计报告 U-7，宿主机防火墙规则实际状态为 UNKNOWN：

- 若防火墙未配置 8081 DROP → **公网直接可达**
- 若防火墙规则被误操作清空 → **公网直接可达**
- 即使防火墙当前生效，也不应依赖单一防线

---

## 2. 收窄方案

### 方案 A: 改为 `127.0.0.1:8081→8000`（仅本机访问）

**docker-compose.yml ports 段变更**:

```yaml
# BEFORE (当前，假设)
ports:
  - "8081:8000"          # 等价于 0.0.0.0:8081:8000

# AFTER (方案 A)
ports:
  - "127.0.0.1:8081:8000"   # 仅本机 lo 接口可达
```

| 维度 | 评估 |
|------|------|
| 公网可达性 | ❌ 不可达 |
| 内网可达性 | ❌ 不可达 |
| Tailscale 可达性 | ❌ 不可达 |
| 本机可达性 | ✅ 可达 |
| 适用场景 | canary-test 仅需本机 curl 验证；或由同一宿主机上的 nginx/APISIX 反代 |
| 优点 | 最小暴露面；零网络配置依赖 |
| 缺点 | 无法从其他节点远程验证；Tailscale 管理员无法远程访问 |

### 方案 B: 改为 Docker 内网访问（仅 Docker network 内部可达）

**docker-compose.yml 变更**:

```yaml
# BEFORE
ports:
  - "8081:8000"

# AFTER (方案 B)
# 方式 1: 完全移除 ports 段（容器仅在 Docker network 内通过容器名访问）
ports: []

# 方式 2: 使用 expose 代替 ports（仅声明容器端口，不映射到宿主机）
expose:
  - "8000"
```

| 维度 | 评估 |
|------|------|
| 公网可达性 | ❌ 不可达 |
| 内网可达性 | ❌ 不可达 |
| Tailscale 可达性 | ❌ 不可达 |
| Docker network 内可达性 | ✅ 可达（通过容器名 `webhook-ingress-canary-test:8000`） |
| 适用场景 | canary-test 仅被同一 Docker network 中的其他容器（如 APISIX、n8n）访问 |
| 优点 | 最强隔离；宿主机层面完全不可达 |
| 缺点 | 本机 curl 无法直接验证；需要 `docker exec` 或通过另一个容器访问 |

### 方案 C: 绑定到 Tailscale IP（仅 Tailscale 网络可达）

**docker-compose.yml ports 段变更**:

```yaml
# BEFORE
ports:
  - "8081:8000"

# AFTER (方案 C)
ports:
  - "100.100.1.22:8081:8000"   # 仅 Tailscale IP 绑定
```

> 注意: Tailscale IP 需在宿主机上确认。node-22 的 Tailscale IP 根据文档为 `100.100.1.22`，但需 `tailscale ip -4` 实时确认。

| 维度 | 评估 |
|------|------|
| 公网可达性 | ❌ 不可达（Tailscale 流量走 userspace/wg 隧道，不经过公网网卡） |
| 内网可达性 | ❌ 不可达（192.168.88.x 无法到达 100.64.0.0/10 除非路由了 Tailscale） |
| Tailscale 可达性 | ✅ 可达（仅 Tailscale 网络内授权节点） |
| 本机可达性 | ✅ 可达（通过 100.100.1.22） |
| 适用场景 | 需要从 Tailscale 网络内其他管理节点远程验证 canary-test |
| 优点 | 远程可达但仅限 Tailscale 授权节点；利用 Tailscale 的身份认证和加密 |
| 缺点 | 依赖 Tailscale daemon 正常运行；需确认 Tailscale IP 不变 |

### 推荐方案及理由

**推荐: 方案 A（`127.0.0.1:8081:8000`）**

理由:

1. **canary-test 是验证用途**: 其消费者是本机的 curl 或同一宿主机的 nginx/APISIX 反代，不需要跨网络访问。
2. **最小权限原则**: 测试容器没有任何理由被外部网络访问，绑定 127.0.0.1 是零暴露面。
3. **不依赖防火墙**: 即使宿主机防火墙规则被意外清空，端口仍然不可达。
4. **验证便利性**: 本机 curl 验证不受影响，且可以通过 APISIX 反代给需要的内部消费者。
5. **回滚简单**: 只需改回 `"8081:8000"` 即可恢复。

**备选方案**: 如果需要 Tailscale 网络内的远程验证能力，使用 **方案 C**。

### docker-compose.yml ports 段 Before/After 对比

```yaml
# ═══════════════════════════════════════════
# BEFORE — 当前状态（假设）
# ═══════════════════════════════════════════
services:
  webhook-ingress-canary-test:
    image: <canary-test-image>
    container_name: webhook-ingress-canary-test
    ports:
      - "8081:8000"              # ⚠️ 0.0.0.0 绑定，公网可能可达
    # ... 其他配置

# ═══════════════════════════════════════════
# AFTER — 推荐方案 A（127.0.0.1 绑定）
# ═══════════════════════════════════════════
services:
  webhook-ingress-canary-test:
    image: <canary-test-image>
    container_name: webhook-ingress-canary-test
    ports:
      - "127.0.0.1:8081:8000"    # ✅ 仅本机可达
    # ... 其他配置
```

---

## 3. 备份步骤

在修改 docker-compose.yml 之前，执行以下备份：

```bash
# 步骤 1: 创建带时间戳的备份副本
cp /path/to/docker-compose.yml /path/to/docker-compose.yml.bak.$(date +%Y%m%d-%H%M%S)

# 步骤 2: 同时保留一个固定名称的备份（方便回滚脚本引用）
cp /path/to/docker-compose.yml /path/to/docker-compose.yml.pre-hardening

# 步骤 3: 验证备份内容一致
diff /path/to/docker-compose.yml /path/to/docker-compose.yml.pre-hardening
# 预期: 无输出（文件完全一致）

# 步骤 4: 记录当前端口绑定状态（变更前快照）
ss -tlnp | grep 8081 > /tmp/canary-port-before-$(date +%Y%m%d-%H%M%S).txt
docker ps --filter name=webhook-ingress-canary-test --format '{{.Ports}}' >> /tmp/canary-port-before-$(date +%Y%m%d-%H%M%S).txt
```

> 将 `/path/to/` 替换为 node-22 上 docker-compose.yml 的实际路径。

---

## 4. 回滚步骤

如果变更后出现问题，执行以下回滚：

```bash
# 步骤 1: 恢复备份文件
cp /path/to/docker-compose.yml.pre-hardening /path/to/docker-compose.yml

# 步骤 2: 重新创建容器（使用 down/up 而非 restart，见注意事项）
cd /path/to/
docker compose down webhook-ingress-canary-test
docker compose up -d webhook-ingress-canary-test

# 步骤 3: 验证端口绑定已恢复
ss -tlnp | grep 8081
# 预期输出应包含: 0.0.0.0:8081（已恢复到原始状态）

# 步骤 4: 验证容器运行正常
docker ps --filter name=webhook-ingress-canary-test
curl -s http://127.0.0.1:8081/healthz
```

---

## 5. 验证步骤

### 5.1 变更前验证（Baseline）

```bash
# 在 node-22 上执行:

# 1. 确认当前端口绑定
ss -tlnp | grep 8081
# 预期 (BEFORE): LISTEN  0  4096  0.0.0.0:8081  0.0.0.0:*  users:(("docker-proxy",pid=...,fd=...))

# 2. 确认容器端口映射
docker ps --filter name=webhook-ingress-canary-test --format 'table {{.Names}}\t{{.Ports}}\t{{.Status}}'
# 预期 (BEFORE): 0.0.0.0:8081->8000/tcp
```

### 5.2 变更后验证（方案 A: 127.0.0.1 绑定）

```bash
# 在 node-22 上执行:

# 1. 确认端口绑定已收窄
ss -tlnp | grep 8081
# 预期 (AFTER): LISTEN  0  4096  127.0.0.1:8081  0.0.0.0:*  users:(("docker-proxy",pid=...,fd=...))
#               注意: 绑定地址从 0.0.0.0 变为 127.0.0.1

# 2. 确认容器端口映射已变更
docker ps --filter name=webhook-ingress-canary-test --format 'table {{.Names}}\t{{.Ports}}\t{{.Status}}'
# 预期 (AFTER): 127.0.0.1:8081->8000/tcp

# 3. 本机访问正常
curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8081/healthz
# 预期: 200

# 4. 本机通过完整请求验证
curl -v http://127.0.0.1:8081/healthz
# 预期: HTTP/1.1 200 OK（或相应的健康检查响应）
```

### 5.3 公网不可达验证

```bash
# 从外部节点执行（非 node-22 本机）:

# 1. 从公网尝试连接（需要在另一台有公网 IP 的机器上）
curl -v --connect-timeout 5 http://43.167.177.86:8081/healthz
# 预期 (AFTER): Connection timed out / Connection refused
# 预期 (BEFORE): 可能返回 200（如果无防火墙）

# 2. 从内网其他节点尝试连接
curl -v --connect-timeout 5 http://192.168.88.11:8081/healthz
# 预期 (AFTER): Connection refused（127.0.0.1 绑定不监听内网网卡）
# 预期 (BEFORE): 可能返回 200

# 3. 从 Tailscale 网络其他节点尝试连接
curl -v --connect-timeout 5 http://100.100.1.22:8081/healthz
# 预期 (AFTER): Connection refused（127.0.0.1 绑定不监听 Tailscale 网卡）
```

### 5.4 Tailscale 访问验证（仅适用于方案 C）

```bash
# 如果采用方案 C（绑定 Tailscale IP），验证:

# 1. 从 Tailscale 网络内其他授权节点
curl -v --connect-timeout 5 http://100.100.1.22:8081/healthz
# 预期 (AFTER, 方案C): 200 OK

# 2. 从公网（不应可达）
curl -v --connect-timeout 5 http://43.167.177.86:8081/healthz
# 预期 (AFTER, 方案C): Connection timed out / Connection refused
```

### 5.5 `ss -tlnp` 和 `docker ps` 输出预期汇总

**变更前 (BEFORE)**:

```
# ss -tlnp | grep 8081
LISTEN  0  4096  0.0.0.0:8081  0.0.0.0:*  users:(("docker-proxy",pid=XXXXX,fd=XX))

# docker ps --filter name=webhook-ingress-canary-test
CONTAINER ID  IMAGE  ...  STATUS       PORTS
abc123        ...    ...  Up X minutes  0.0.0.0:8081->8000/tcp
```

**变更后 — 方案 A (AFTER)**:

```
# ss -tlnp | grep 8081
LISTEN  0  4096  127.0.0.1:8081  0.0.0.0:*  users:(("docker-proxy",pid=YYYYY,fd=XX))

# docker ps --filter name=webhook-ingress-canary-test
CONTAINER ID  IMAGE  ...  STATUS       PORTS
abc123        ...    ...  Up X minutes  127.0.0.1:8081->8000/tcp
```

**变更后 — 方案 B (AFTER)**:

```
# ss -tlnp | grep 8081
# (无输出 — 8081 端口不再映射到宿主机)

# docker ps --filter name=webhook-ingress-canary-test
CONTAINER ID  IMAGE  ...  STATUS       PORTS
abc123        ...    ...  Up X minutes  (无端口映射)
```

**变更后 — 方案 C (AFTER)**:

```
# ss -tlnp | grep 8081
LISTEN  0  4096  100.100.1.22:8081  0.0.0.0:*  users:(("docker-proxy",pid=YYYYY,fd=XX))

# docker ps --filter name=webhook-ingress-canary-test
CONTAINER ID  IMAGE  ...  STATUS       PORTS
abc123        ...    ...  Up X minutes  100.100.1.22:8081->8000/tcp
```

---

## 6. 注意事项

### 6.1 Docker Compose restart vs down/up 的区别

| 操作 | 行为 | 端口绑定变更是否生效 |
|------|------|---------------------|
| `docker compose restart` | 重启容器进程，**不重新读取配置** | ❌ **不生效** — 仍使用旧端口绑定 |
| `docker compose up -d` (容器已存在) | 检测配置变更，自动重建容器 | ✅ **生效** |
| `docker compose down` + `docker compose up -d` | 销毁并重建容器 | ✅ **生效** |
| `docker compose up -d --force-recreate` | 强制重建容器 | ✅ **生效** |

**推荐操作顺序**:

```bash
# 方式 1: 安全平滑（推荐）
docker compose up -d webhook-ingress-canary-test
# Docker Compose 检测到 ports 变更，自动停止旧容器并创建新容器

# 方式 2: 显式重建（更明确）
docker compose down webhook-ingress-canary-test
docker compose up -d webhook-ingress-canary-test

# ⚠️ 不要使用:
docker compose restart webhook-ingress-canary-test
# 这不会应用端口绑定变更！
```

### 6.2 对 webhook-ingress 业务链路的影响

| 链路 | 是否影响 | 说明 |
|------|----------|------|
| Linear → webhook.exa.edu.kg → nginx → webhook-ingress:8000 | ❌ **不影响** | canary-test 是独立容器，不参与生产 webhook 转发链路 |
| APISIX → n8n:5678 | ❌ **不影响** | canary-test 与 APISIX→n8n 路由无关 |
| APISIX → webhook-ingress (.37:3100) | ❌ **不影响** | canary-test 不在 APISIX upstream 中 |
| canary-test 自身的健康检查 | ✅ **受影响** | 需要更新健康检查地址（如果有外部监控） |

**结论**: 端口收窄操作对现有 webhook-ingress 生产业务链路 **零影响**。canary-test 容器是独立的测试/验证容器，不参与任何生产流量路径。

### 6.3 其他注意事项

1. **健康检查脚本**: 如果有外部监控系统（如 cron 定时 curl 8081），需要更新为 `curl http://127.0.0.1:8081/healthz`（本机）或移除（如果是从外部节点监控）。

2. **Docker network**: canary-test 容器必须与需要访问它的其他容器在同一 Docker network 中，否则方案 B 的容器名访问不生效。

3. **日志验证**: 变更后检查容器日志确认无异常:
   ```bash
   docker logs --since 5m webhook-ingress-canary-test
   ```

4. **并行变更**: 如果同时修改多个容器的 ports 段，建议逐个变更并验证，避免批量操作导致不可预期的连锁故障。

5. **Tailscale IP 稳定性**: 方案 C 依赖 Tailscale IP 不变。默认情况下 Tailscale IP 是稳定的（基于节点 key），但如果重新认证或更换机器，IP 可能变化。建议使用 Tailscale MagicDNS 名称 (`node-22.tail5e888.ts.net`) 作为辅助验证。

---

*分析完成。本文档仅为分析输出，未执行任何命令或修改任何配置。*
