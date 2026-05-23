# APISIX 9080 业务端口暴露面收敛 — Phase 4 报告

**报告编号**: APISIX-9080-HARDENING-PHASE4-001  
**日期**: 2026-05-09  
**执行人**: main-thread + qwen-worker  
**前置文档**: APISIX-ETCD-PERSISTENCE-PHASE3.5-001, APISIX-ETCD-HARDENING-PHASE3-001, APISIX-ADMIN-HARDENING-PHASE2-001  
**判定**: **PASS**

**脱敏声明**: 所有 secret/token/key 均已脱敏，无明文泄露。

---

## 1. 变更前状态

### 1.1 APISIX 9080 端口绑定

```
# docker ps
apisix-gateway  0.0.0.0:9080->9080/tcp, [::]:9080->9080/tcp, 127.0.0.1:9180->9180/tcp, 9443/tcp

# ss -tlnp | grep 9080
LISTEN 0 4096 0.0.0.0:9080 0.0.0.0:*  users:(("docker-proxy",...))
```

**风险**: `0.0.0.0:9080` 表示所有网络接口均可访问 APISIX 业务端口。

### 1.2 服务器实际 IP 地址

| 网络接口 | IP 地址 | 用途 |
|----------|---------|------|
| loopback | `127.0.0.1` | 本机管理，Cloudflare Tunnel |
| LAN | `10.7.0.8` | 内网访问（非之前假设的 192.168.88.11） |
| Tailscale | `100.100.1.22` | Tailscale VPN 管理 |

### 1.3 路由基线

| 属性 | 值 |
|------|-----|
| route_count | 1 |
| route id | route-webhooks-factory-canary-v1 |
| uri | /webhooks/factory |

### 1.4 Phase 2/3/3.5 保持确认

| 端口 | Phase 2/3 状态 | 变更前确认 |
|------|---------------|-----------|
| 9180 | `127.0.0.1:9180` | **保持** |
| 2379 | 无宿主机映射 | **保持** |
| etcd volume | `apisix_etcd_data:/bitnami/etcd` | **保持** |

---

## 2. 变更内容

### 2.1 docker-compose.yml — 9080 端口绑定收窄

**变更前**:
```yaml
services:
  apisix:
    ports:
      - "9080:9080"              # 0.0.0.0:9080
      - "127.0.0.1:9180:9180"    # Phase 2 已收窄
```

**变更后**:
```yaml
services:
  apisix:
    ports:
      - "127.0.0.1:9080:9080"       # 仅本机（Cloudflare Tunnel）
      - "10.7.0.8:9080:9080"        # 仅 LAN（内网访问）
      - "100.100.1.22:9080:9080"    # 仅 Tailscale（VPN 管理）
      - "127.0.0.1:9180:9180"       # Admin API（Phase 2 保持）
```

### 2.2 未变更项

- **config.yaml**: 未变更
- **etcd 配置**: 未变更（volume 持久化保持）
- **业务路由**: 未修改、未删除、未新增
- **9180 绑定**: 保持 `127.0.0.1:9180`
- **2379 绑定**: 保持无宿主机映射

---

## 3. 备份路径和 SHA256

```
/opt/apisix/backups/port9080-hardening-20260509-140114/
├── config.yaml
├── docker-compose.yml
└── routes-dump.json
```

| 文件 | SHA256 |
|------|--------|
| config.yaml | `172ac1dabe400146210c7fe25f9daac6d2742d2e7544d7ad9176025aa519ee8b` |
| docker-compose.yml | `6062eb5b7b2b277e76eefedb801cee724c4c2eb7292aceae4df5070c1ca12487` |

---

## 4. 变更后端口证据

### 4.1 docker ps

```
NAMES            PORTS                                                                                                                STATUS
apisix-gateway   127.0.0.1:9080->9080/tcp, 10.7.0.8:9080->9080/tcp, 100.100.1.22:9080->9080/tcp, 127.0.0.1:9180->9180/tcp, 9443/tcp   Up 2 minutes
apisix-etcd      2379-2380/tcp                                                                                                        Up 18 minutes
```

**对比**: 9080 从 `0.0.0.0:9080->9080/tcp` 变为 3 个特定 IP 绑定。

### 4.2 ss -tlnp

```
# ss -tlnp | grep 9080
LISTEN 0 4096 100.100.1.22:9080  0.0.0.0:*  users:(("docker-proxy",...))
LISTEN 0 4096 10.7.0.8:9080     0.0.0.0:*  users:(("docker-proxy",...))
LISTEN 0 4096 127.0.0.1:9080     0.0.0.0:*  users:(("docker-proxy",...))
```

**结论**: 不存在 `0.0.0.0:9080` 监听。

---

## 5. 当前实际绑定 IP

| 绑定地址 | 用途 | 来源 |
|----------|------|------|
| `127.0.0.1:9080` | 本机管理，Cloudflare Tunnel 回源 | 永久 |
| `10.7.0.8:9080` | 内网 LAN 访问 | `ip addr` 实际输出 |
| `100.100.1.22:9080` | Tailscale VPN 访问 | `tailscale ip -4` 实际输出 |

---

## 6. Route Baseline 对比

| 时刻 | route_count | route id |
|------|-------------|----------|
| 变更前 | 1 | route-webhooks-factory-canary-v1 |
| 变更后 | 1 | route-webhooks-factory-canary-v1 |

**结论**: 路由数量和 ID 无变化。

---

## 7. Admin API 验证

| 测试 | 结果 |
|------|------|
| 正确 admin_key | **200** |
| 无 admin_key | **401** |
| 错误 admin_key | **401** |

---

## 8. /webhooks/factory 502 归因说明

```
curl -s -o /dev/null -w "%{http_code}" -X POST http://127.0.0.1:9080/webhooks/factory \
  -H "Content-Type: application/json" -d '{}'
→ 502
```

**归因**:
- **route exists**: 是。APISIX 正确匹配 `/webhooks/factory`
- **upstream unavailable**: 是。上游配置为 `127.0.0.1:8080`，当前无服务监听
- **not caused by 9080 hardening**: 是。502 在所有 Phase 前已存在

**这是 pre-existing upstream unavailable 状态。**

---

## 9. 2379 / 9180 未回退暴露的证据

### 9.1 ss -tlnp 2379

```
NO_2379_LISTENER
```

### 9.2 ss -tlnp 9180

```
LISTEN 0 4096 127.0.0.1:9180 0.0.0.0:*  users:(("docker-proxy",...))
```

### 9.3 docker ps

```
apisix-gateway  ..., 127.0.0.1:9180->9180/tcp, ...    # 9180 仅 localhost
apisix-etcd     2379-2380/tcp                          # 2379 无宿主机映射
```

**结论**: Phase 2/3 的收敛成果未被破坏。

---

## 10. 回滚命令

```bash
ssh root@node-22 '
cd /opt/apisix
docker compose down apisix

# 恢复备份
cp /opt/apisix/backups/port9080-hardening-20260509-140114/docker-compose.yml /opt/apisix/docker-compose.yml
cp /opt/apisix/backups/port9080-hardening-20260509-140114/config.yaml /opt/apisix/config.yaml

docker compose up -d apisix
sleep 10

echo "=== ROLLBACK VERIFY ==="
docker ps --filter name=apisix --format "{{.Names}}: {{.Ports}}"
ss -tlnp | grep 9080
'
```

回滚后预期:
- `docker ps` → 恢复 `0.0.0.0:9080->9080/tcp`
- `ss -tlnp | grep 9080` → 恢复 `0.0.0.0:9080`

---

## 11. PASS 标准对照

| # | PASS 条件 | 证据 | 判定 |
|---|-----------|------|------|
| 1 | 9080 不再绑定 0.0.0.0 | `ss` 仅显示 3 个特定 IP | **PASS** |
| 2 | 9080 仅绑定必要地址 | `127.0.0.1` + `10.7.0.8` + `100.100.1.22` | **PASS** |
| 3 | route_count 保持 1 | 变更前=1, 变更后=1 | **PASS** |
| 4 | route id 保持 | route-webhooks-factory-canary-v1 | **PASS** |
| 5 | Admin API 正常 | 正确 key=200, 无 key=401 | **PASS** |
| 6 | 2379 仍无宿主机监听 | `NO_2379_LISTENER` | **PASS** |
| 7 | 9180 仍只在受控地址 | `127.0.0.1:9180` | **PASS** |
| 8 | 无 secret 明文泄露 | 报告全部 [REDACTED] | **PASS** |
| 9 | 有备份、有回滚、有验证 | 备份路径+SHA256+回滚命令+验证证据齐全 | **PASS** |

---

## 12. 四阶段收敛总览

| Phase | 整改项 | 变更前 | 变更后 | 判定 |
|-------|--------|--------|--------|------|
| 1 | canary-test 8081 | `0.0.0.0:8081` | `127.0.0.1:8081` | PASS |
| 2 | Admin API 9180 | `0.0.0.0:9180` + `allow_admin 0.0.0.0/0` | `127.0.0.1:9180` + 4 网段白名单 | PASS |
| 3 | etcd 2379 | `0.0.0.0:2379` | Docker 内网 only | PASS |
| 3.5 | etcd 持久化 | 无 volume | named volume | PASS |
| **4** | **9080 业务端口** | **`0.0.0.0:9080`** | **3 IP 绑定** | **PASS** |

---

## 13. 最终结论

**PASS**

APISIX 9080 业务端口收敛完成：

1. **9080 不再绑定 0.0.0.0**: 收窄到 `127.0.0.1` + `10.7.0.8`(LAN) + `100.100.1.22`(Tailscale)
2. **所有合法客户端覆盖**: Cloudflare Tunnel(localhost)、内网(LAN)、Tailscale VPN
3. **Phase 2/3/3.5 成果保持**: 9180 仍仅 localhost、2379 仍无宿主机映射、etcd 仍有持久化
4. **业务路由不受影响**: route_count=1, /webhooks/factory 路由存在

**至此，webhook 入口暴露面收敛全部 4+1 阶段均已完成并通过验收。**

---

**报告状态**: PASS  
**收敛完成**: Phase 1 + Phase 2 + Phase 3 + Phase 3.5 + Phase 4 全部 PASS
