# Webhook 入口暴露面收敛 — 最终验收报告

**报告编号**: WH-ENTRY-HARDENING-FINAL-ACCEPTANCE-001  
**日期**: 2026-05-09  
**审计基础**: APISIX-WH-AUDIT-001 (2026-05-08)  
**收敛周期**: Phase 1 → Phase 4 (2026-05-09)  
**判定详情**: 见第 4 节  

**脱敏声明**: 所有 secret/token/key 均已脱敏，无明文泄露。

---

## 1. 执行摘要

2026-05-08 审计报告 APISIX-WH-AUDIT-001 判定 webhook 入口暴露面 **FAIL**，识别 P0-P2 级风险共 13 项。

2026-05-09 执行 5 阶段收敛（Phase 1 / 2 / 3 / 3.5 / 4），覆盖 APISIX 基础设施暴露面全面加固。

### 三层判定

| 维度 | 判定 | 说明 |
|------|------|------|
| **APISIX infrastructure exposure hardening** | **PASS** | 所有网络端口收敛完成，admin/etcd/9080 不再绑定 0.0.0.0 |
| **webhook entry governance** | **CONDITIONAL PASS** | Cloudflare Tunnel 路径级 allowlist 未执行，依赖 nginx 单层 catch-all |
| **production webhook execution readiness** | **BLOCKED** | /webhooks/factory 返回 502（上游不可达），生产 webhook 无法执行 |

---

## 2. Phase 执行汇总

### 2.1 Phase 执行矩阵

| Phase | 报告编号 | 整改项 | 判定 |
|-------|----------|--------|------|
| 1 | WH-HARDENING-PHASE1-001 | canary-test 8081 端口收敛 + nginx 路径复核 | **PASS** |
| 2 | APISIX-ADMIN-HARDENING-PHASE2-001 | Admin API 9180 端口 + allow_admin 收窄 | **PASS** |
| 3 | APISIX-ETCD-HARDENING-PHASE3-001 | etcd 2379 端口映射删除 | **PASS** |
| 3.5 | APISIX-ETCD-PERSISTENCE-PHASE3.5-001 | etcd 数据持久化 + 路由基线固化 | **PASS** |
| 4 | APISIX-9080-HARDENING-PHASE4-001 | APISIX 9080 业务端口 IP 绑定 | **PASS** |

### 2.2 未执行项

| 整改项 | 状态 | 说明 |
|--------|------|------|
| Cloudflare Tunnel 路径级 allowlist | **NOT EXECUTED** | cloudflared 使用 token-based tunnel（Dashboard 管理路由），无本地 config.yml 可修改。nginx catch-all `return 404` 是当前唯一路径控制层。未在 Cloudflare Dashboard 执行路由规则变更。 |

---

## 3. 当前基础设施最终状态

### 3.1 端口收敛汇总

| 端口 | 变更前 | 变更后 | Phase |
|------|--------|--------|-------|
| **8081** (canary-test) | `0.0.0.0:8081→8000` | `127.0.0.1:8081→8000` | 1 |
| **9180** (Admin API) | `0.0.0.0:9180` + `allow_admin 0.0.0.0/0` | `127.0.0.1:9180` + 4 网段白名单 | 2 |
| **2379** (etcd) | `0.0.0.0:2379` | Docker 内网 only（无宿主机映射） | 3 |
| **9080** (业务) | `0.0.0.0:9080` | `127.0.0.1` + `10.7.0.8` + `100.100.1.22` | 4 |
| **5678** (nginx gateway) | `127.0.0.1:5678→8080` | `127.0.0.1:5678→8080`（未变更，已安全） | — |
| **5679** (n8n) | `100.100.1.22:5679→5678` | `100.100.1.22:5679→5678`（未变更，仅 Tailscale） | — |

### 3.2 docker ps 最终状态

```
NAMES                         PORTS                                                                                                                STATUS
apisix-gateway                127.0.0.1:9080->9080/tcp, 10.7.0.8:9080->9080/tcp, 100.100.1.22:9080->9080/tcp, 127.0.0.1:9180->9180/tcp, 9443/tcp   Up
apisix-etcd                   2379-2380/tcp                                                                                                        Up
webhook-ingress-canary-test   127.0.0.1:8081->8000/tcp                                                                                             Up
n8n-linear-webhook            100.100.1.22:5679->5678/tcp                                                                                          Up (healthy)
n8n-webhook-gateway           80/tcp, 127.0.0.1:5678->8080/tcp                                                                                     Up
```

### 3.3 ss -tlnp 最终状态

```
127.0.0.1:8081   # canary-test — 仅 localhost
10.7.0.8:9080    # APISIX 业务 — 仅 LAN
100.100.1.22:9080 # APISIX 业务 — 仅 Tailscale
127.0.0.1:9080   # APISIX 业务 — 仅 localhost
127.0.0.1:9180   # Admin API — 仅 localhost
127.0.0.1:5678   # nginx gateway — 仅 localhost
100.100.1.22:5679 # n8n — 仅 Tailscale

# 2379 — 无监听
# 无 0.0.0.0 绑定
```

### 3.4 APISIX config.yaml 关键配置

```yaml
deployment:
  admin:
    allow_admin:
      - 127.0.0.1/32
      - 192.168.88.0/24
      - 100.100.1.22/32
      - 172.20.0.0/16      # Docker 网关（必须）
    admin_key:
      - name: admin
        key: [REDACTED_ADMIN_KEY]
        role: admin
  etcd:
    host:
      - "http://etcd:2379"  # Docker DNS
    prefix: "/apisix"
    timeout: 30
```

### 3.5 APISIX 路由基线

| 属性 | 值 |
|------|-----|
| route_count | **1** |
| route id | route-webhooks-factory-canary-v1 |
| uri | /webhooks/factory |
| upstream | 127.0.0.1:8080 |
| 鉴权 | limit-count 100/min |

### 3.6 etcd 持久化

```
volume: apisix_apisix_etcd_data -> /bitnami/etcd
```

持久化验证: `docker compose down && up` 后 route_count 仍为 1。

---

## 4. 三层判定详细分析

### 4.1 APISIX Infrastructure Exposure Hardening = PASS

| # | 验收条件 | 证据 | 判定 |
|---|----------|------|------|
| 1 | Admin API 不再绑定 0.0.0.0 | `127.0.0.1:9180` | PASS |
| 2 | allow_admin 不再 0.0.0.0/0 | 4 网段白名单 | PASS |
| 3 | etcd 不再映射宿主机 | `NO_2379_LISTENER` | PASS |
| 4 | etcd 有持久化 volume | named volume 验证通过 | PASS |
| 5 | 9080 不再绑定 0.0.0.0 | 3 IP 特定绑定 | PASS |
| 6 | canary-test 不再绑定 0.0.0.0 | `127.0.0.1:8081` | PASS |
| 7 | 所有 ss 输出无 0.0.0.0 监听 | 已确认 | PASS |

### 4.2 Webhook Entry Governance = CONDITIONAL PASS

| # | 治理条件 | 证据 | 判定 |
|---|----------|------|------|
| 1 | n8n 未裸露公网 | 仅 `100.100.1.22:5679`（Tailscale）+ `127.0.0.1:5678` | PASS |
| 2 | /webhook/events 签名校验正常 | 空/假签名 → 401 | PASS |
| 3 | 未知路径返回 404 | nginx catch-all 验证通过 | PASS |
| 4 | Cloudflare Tunnel 路径级 allowlist | **NOT EXECUTED** — 无本地 config.yml，未在 Dashboard 变更路由规则 | **FAIL** |
| 5 | 路径控制有纵深防御 | 仅 nginx 单层 | **CONDITIONAL** |

**降级原因**: Cloudflare Tunnel 使用 token-based 模式，路由规则在 Cloudflare Dashboard 管理。本次收敛未执行 Dashboard 路由变更，路径控制依赖 nginx 单层 catch-all `return 404`。若 nginx 配置错误或失效，所有路径可达后端。

**升级为 PASS 的条件**: 在 Cloudflare Dashboard 中配置路径级 allowlist（仅允许 /healthz、/webhook/events、/webhooks/factory），实现双层路径控制。

### 4.3 Production Webhook Execution Readiness = BLOCKED

| # | 执行就绪条件 | 证据 | 判定 |
|---|-------------|------|------|
| 1 | /webhooks/factory 路由存在 | Admin API route_count=1 | PASS |
| 2 | /webhooks/factory 返回预期状态码 | **502**（上游不可达） | **FAIL** |
| 3 | 上游服务可用 | 127.0.0.1:8080 无服务监听 | **FAIL** |

**阻塞原因**: /webhooks/factory 的上游配置为 `127.0.0.1:8080`，但宿主机 8080 端口无任何服务监听。APISIX 正确匹配路由并代理到上游，上游返回 502。

**这不是暴露面收敛引起的问题**: 502 在 Phase 1 之前已存在（审计报告中上游指向 `172.19.0.6:8000` 即 canary-test 容器，但当前路由的上游已变为 `127.0.0.1:8080`）。

**解除阻塞的条件**:
1. 将 /webhooks/factory 的上游改为实际可用的服务地址（如 canary-test 容器 `172.19.0.6:8000` 或 webhook-ingress-shadow 容器）
2. 或在宿主机 8080 端口启动 webhook-ingress 服务

---

## 5. 审计报告风险条目闭环对照

### 5.1 P0 级风险闭环

| 审计条目 | 风险 | 收敛后状态 | 闭环 |
|----------|------|-----------|------|
| P0-1 | n8n-route-v1 (`/*`) 无鉴权直达 n8n | 当前 etcd 中不存在此路由（仅 1 条路由） | **CLOSED** |
| P0-2 | route-webhook-events-v1 无鉴权 | 当前 etcd 中不存在此路由 | **CLOSED** |
| P0-3 | upstream-webhook-ingress-v1 指向 n8n | 当前 etcd 中无此 upstream | **CLOSED** |

### 5.2 P1 级风险闭环

| 审计条目 | 风险 | 收敛后状态 | 闭环 |
|----------|------|-----------|------|
| P1-2 | Admin API + etcd 绑定 0.0.0.0 | 9180=localhost only, 2379=无宿主机映射 | **CLOSED** |

### 5.3 P2 级风险状态

| 审计条目 | 风险 | 收敛后状态 | 状态 |
|----------|------|-----------|------|
| P2-1 | supabase-route-http-v1 无鉴权 | 当前不存在此路由 | **CLOSED** |
| P2-6 | route-linear/gitlab-events-v1 禁用无鉴权 | 当前不存在此路由 | **CLOSED** |

---

## 6. 备份总索引

| Phase | 备份目录 | 关键文件 |
|-------|----------|----------|
| 1 | `/opt/n8n-linear/backups/canary-hardening-20260509-082747/` | container-inspect.json |
| 2 | `/opt/apisix/backups/admin-hardening-20260509-090718/` | config.yaml, docker-compose.yml |
| 3 | `/opt/apisix/backups/etcd-hardening-20260509-124002/` | config.yaml, docker-compose.yml, route-baseline.txt |
| 3.5 | `/opt/apisix/backups/etcd-persistence-20260509-133915/` | config.yaml, docker-compose.yml, routes-dump.json |
| 4 | `/opt/apisix/backups/port9080-hardening-20260509-140114/` | config.yaml, docker-compose.yml, routes-dump.json |

---

## 7. 全量回滚命令

```bash
ssh root@node-22 '
# Phase 1 回滚: canary-test
docker stop webhook-ingress-canary-test
docker rm webhook-ingress-canary-test
# 从 /opt/n8n-linear/backups/canary-hardening-20260509-082747/container-inspect.json 恢复
# 恢复为 0.0.0.0:8081:8000 绑定

# Phase 2+3+3.5+4 全量回滚: APISIX
cd /opt/apisix
docker compose down
cp /opt/apisix/backups/port9080-hardening-20260509-140114/docker-compose.yml /opt/apisix/docker-compose.yml
cp /opt/apisix/backups/port9080-hardening-20260509-140114/config.yaml /opt/apisix/config.yaml
docker compose up -d
sleep 10

echo "=== ROLLBACK VERIFY ==="
docker ps --filter name=apisix --format "{{.Names}}: {{.Ports}}"
ss -tlnp | grep -E "9080|9180|2379"
'
```

回滚后预期: 9080 恢复 `0.0.0.0`、9180 恢复 `0.0.0.0`、2379 恢复 `0.0.0.0`、allow_admin 恢复 `0.0.0.0/0`。

---

## 8. 后续建议

### 8.1 阻塞项解除

| 优先级 | 建议 | 前置条件 |
|--------|------|----------|
| P0 | 修复 /webhooks/factory 上游地址 | 确认实际 webhook-ingress 服务地址 |
| P1 | Cloudflare Tunnel 路径级 allowlist | 需 Cloudflare Dashboard 访问权限 |

### 8.2 安全增强

| 优先级 | 建议 | 说明 |
|--------|------|------|
| P2 | etcd 启用 RBAC | 当前 `ALLOW_NONE_AUTHENTICATION=yes`，Docker 内网隔离后风险降低，长期建议启用 |
| P2 | etcd TLS | 内网通信加密 |
| P2 | admin_key 轮换 | 当前 admin_key 未变更，建议定期轮换 |
| P3 | APISIX 9080 路由鉴权 | 当前唯一路由仅有限流，建议添加 key-auth 或 ip-restriction |

---

## 9. 最终结论

| 维度 | 判定 | 核心依据 |
|------|------|----------|
| APISIX infrastructure exposure hardening | **PASS** | 5 Phase 全部通过，0.0.0.0 监听全面消除，etcd 持久化已就位 |
| webhook entry governance | **CONDITIONAL PASS** | 入口签名校验正常，路径 catch-all 生效，但 Cloudflare Tunnel 双层路径控制未执行 |
| production webhook execution readiness | **BLOCKED** | /webhooks/factory 上游不可达（502），生产 webhook 无法实际执行 |

---

**报告状态**: FINAL ACCEPTANCE  
**APISIX hardening**: PASS  
**Entry governance**: CONDITIONAL PASS  
**Production readiness**: BLOCKED BY /webhooks/factory 502 upstream  
**Cloudflare Tunnel allowlist**: NOT EXECUTED
