# APISIX etcd 数据持久化与路由基线固化 — Phase 3.5 报告

**报告编号**: APISIX-ETCD-PERSISTENCE-PHASE3.5-001  
**日期**: 2026-05-09  
**执行人**: main-thread + qwen-worker  
**前置文档**: APISIX-ETCD-HARDENING-PHASE3-001  
**判定**: **PASS**

**脱敏声明**: 所有 secret/token/key 均已脱敏，无明文泄露。

---

## 1. 变更前状态

### 1.1 etcd 持久化状态

| 属性 | 值 |
|------|-----|
| 容器名 | apisix-etcd |
| 镜像 | bitnami/etcd:3.5.11 |
| Volume 挂载 | **无**（`[]`空数组） |
| 数据目录 | `/bitnami/etcd`（容器内，无持久化） |
| 端口映射 | `2379-2380/tcp`（仅容器内部，Phase 3 已收敛） |

### 1.2 路由基线

| 属性 | 值 |
|------|-----|
| route_count | 1 |
| route id | route-webhooks-factory-canary-v1 |
| uri | /webhooks/factory |
| upstream | 127.0.0.1:8080 |

### 1.3 APISIX config.yaml etcd 连接

```yaml
etcd:
  host:
    - "http://etcd:2379"    # Docker DNS
  prefix: "/apisix"
  timeout: 30
```

---

## 2. etcd 无持久化的风险说明

| 风险 | 影响 | 触发场景 |
|------|------|----------|
| **容器重建数据丢失** | 所有 APISIX 配置（路由、消费者、上游）丢失 | `docker compose down && up`、主机重启、镜像更新 |
| **配置无法自动恢复** | 需手动通过 Admin API 重建所有对象 | 任何导致容器被删除的操作 |
| **运维可靠性低** | 无法保证配置在意外重启后可用 | 系统维护、故障恢复 |

**Phase 3 中已实际触发此风险**: etcd 容器因端口映射变更被重建，路由数据丢失，需手动恢复。

---

## 3. 变更内容

### 3.1 docker-compose.yml — 添加 etcd volume

**变更前**:
```yaml
services:
  etcd:
    image: bitnami/etcd:3.5.11
    container_name: apisix-etcd
    # 无 volumes 段
    # ...
# 无顶层 volumes 声明
```

**变更后**:
```yaml
services:
  etcd:
    image: bitnami/etcd:3.5.11
    container_name: apisix-etcd
    volumes:
      - apisix_etcd_data:/bitnami/etcd    # ← 新增持久化
    # ...

volumes:
  apisix_etcd_data: {}                    # ← 新增顶层声明
```

### 3.2 未变更项

- **config.yaml**: 未变更
- **etcd 端口映射**: 仍为无宿主机映射（Phase 3 保持）
- **ALLOW_NONE_AUTHENTICATION**: 仍为 `yes`
- **APISIX 路由**: 未修改、未删除、未新增

---

## 4. Volume 配置片段

### 4.1 docker-compose.yml 完整 etcd 段

```yaml
services:
  etcd:
    image: bitnami/etcd:3.5.11
    container_name: apisix-etcd
    restart: unless-stopped
    environment:
      ETCD_ENABLE_V2: "true"
      ALLOW_NONE_AUTHENTICATION: "yes"
      ETCD_ADVERTISE_CLIENT_URLS: "http://etcd:2379"
      ETCD_LISTEN_CLIENT_URLS: "http://0.0.0.0:2379"
    volumes:
      - apisix_etcd_data:/bitnami/etcd
    networks:
      apisix-net:
        aliases:
          - etcd

volumes:
  apisix_etcd_data: {}
```

### 4.2 Docker volume 实际挂载验证

```
# docker inspect apisix-etcd --format "{{range .Mounts}}{{.Type}} {{.Source}} -> {{.Destination}}{{println}}{{end}}"
volume /var/lib/docker/volumes/apisix_apisix_etcd_data/_data -> /bitnami/etcd
```

---

## 5. 备份路径和 SHA256

```
/opt/apisix/backups/etcd-persistence-20260509-133915/
├── config.yaml
├── docker-compose.yml
└── routes-dump.json
```

| 文件 | SHA256 |
|------|--------|
| config.yaml | `172ac1dabe400146210c7fe25f9daac6d2742d2e7544d7ad9176025aa519ee8b` |
| docker-compose.yml | `e7a01efd2d35d89e9c6ec86f9bbc2d9b94cca09ec6aca4559defddb5c4bbd805` |

---

## 6. Route Baseline 对比

| 时刻 | route_count | route id |
|------|-------------|----------|
| 变更前 | 1 | route-webhooks-factory-canary-v1 |
| restart 后 | 1 | route-webhooks-factory-canary-v1 |
| down/up 后 | 1 | route-webhooks-factory-canary-v1 |
| 最终确认 | 1 | route-webhooks-factory-canary-v1 |

**结论**: 路由在所有破坏性测试中保持一致。

---

## 7. 重启/重建后 Route 仍存在的证据

### 7.1 docker compose restart

```
route_count=1
  route-webhooks-factory-canary-v1
```

### 7.2 docker compose down && docker compose up -d

```
route_count=1
  route-webhooks-factory-canary-v1
```

### 7.3 最终确认（down/up 后独立执行）

```
route_count=1
  route-webhooks-factory-canary-v1
admin=200
factory=502
```

**结论**: etcd 数据在 restart 和 down/up 两种破坏性测试中均未丢失。

---

## 8. 2379 仍未暴露的证据

```
# ss -tlnp | grep 2379
NO_2379_LISTENER

# docker ps
apisix-etcd      2379-2380/tcp           # 无 -> 映射
apisix-gateway   0.0.0.0:9080->9080/tcp, 127.0.0.1:9180->9180/tcp, 9443/tcp
```

**结论**: Phase 3 的 etcd 端口收敛未被 Phase 3.5 破坏。

---

## 9. /webhooks/factory 502 的归因说明

```
curl -s -o /dev/null -w "%{http_code}" -X POST http://127.0.0.1:9080/webhooks/factory \
  -H "Content-Type: application/json" -d '{}'
→ 502
```

**归因**:
- **route exists**: 是。APISIX 正确匹配 `/webhooks/factory`，代理到上游
- **upstream unavailable**: 是。上游配置为 `127.0.0.1:8080`，当前无服务监听宿主机 8080 端口
- **not caused by etcd persistence**: 是。502 在 Phase 3 变更前已存在，与 etcd 持久化无关

**这是 pre-existing upstream unavailable 状态，不是本次变更引起的问题。**

---

## 10. 回滚命令

```bash
ssh root@node-22 '
cd /opt/apisix
docker compose down

# 恢复备份
cp /opt/apisix/backups/etcd-persistence-20260509-133915/docker-compose.yml /opt/apisix/docker-compose.yml
cp /opt/apisix/backups/etcd-persistence-20260509-133915/config.yaml /opt/apisix/config.yaml

# 可选：删除持久化 volume（会清除 etcd 数据）
# docker volume rm apisix_apisix_etcd_data

docker compose up -d
sleep 10

echo "=== ROLLBACK VERIFY ==="
docker ps --filter name=apisix --format "{{.Names}}: {{.Ports}}"
ss -tlnp | grep 2379 || echo "NO_2379_LISTENER"
'
```

---

## 11. PASS 标准对照

| # | PASS 条件 | 证据 | 判定 |
|---|-----------|------|------|
| 1 | etcd 有明确持久化 volume | `volume /var/lib/docker/volumes/apisix_apisix_etcd_data/_data -> /bitnami/etcd` | **PASS** |
| 2 | 容器 restart 后 route 不丢失 | restart 后 route_count=1 | **PASS** |
| 3 | docker compose down/up 后 route 不丢失 | down/up 后 route_count=1 | **PASS** |
| 4 | route baseline 保持 1 条 | 所有测试均为 1 | **PASS** |
| 5 | route id 保持 route-webhooks-factory-canary-v1 | 所有测试均一致 | **PASS** |
| 6 | 2379 仍不映射宿主机 | `NO_2379_LISTENER` + docker ps 无映射 | **PASS** |
| 7 | APISIX Admin API 正常 | 正确 key=200, 无 key=401, 错误 key=401 | **PASS** |
| 8 | 无 secret 明文泄露 | 报告全部 [REDACTED] | **PASS** |
| 9 | 有备份、有回滚、有验证 | 备份路径+SHA256+回滚命令+验证证据齐全 | **PASS** |

---

## 12. 最终结论

**PASS**

etcd 持久化与路由基线固化完成：

1. **etcd 持久化**: 添加 Docker named volume `apisix_etcd_data` 挂载到 `/bitnami/etcd`
2. **数据持久性验证**: `docker compose restart` 和 `docker compose down && up` 两种破坏性测试中，路由均未丢失
3. **Phase 3 收敛保持**: 2379 端口仍不映射宿主机
4. **业务路由**: route-webhooks-factory-canary-v1 在所有测试中保持一致
5. **502 归因**: /webhooks/factory 的 502 是 pre-existing upstream unavailable，不是本次变更引起

---

**报告状态**: PASS  
**下一步**: Phase 4 — APISIX 9080 业务端口收敛
