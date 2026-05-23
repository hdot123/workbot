# Webhook 入口暴露面收敛 — 第一批低风险变更报告

**报告编号**: WH-HARDENING-PHASE1-001  
**日期**: 2026-05-09  
**执行人**: main-thread  
**前置文档**: WH-EXPOSURE-HARDENING-001, APISIX-WH-AUDIT-001  
**判定**: **PASS**

**脱敏声明**: 本报告所有 secret/token/key 均已脱敏，无明文泄露。

---

## 1. 变更摘要

| # | 变更项 | 变更前 | 变更后 | 状态 |
|---|--------|--------|--------|------|
| 一 | canary-test 容器端口 | `0.0.0.0:8081→8000` | `127.0.0.1:8081→8000` | **已完成** |
| 二 | Cloudflare/nginx 路径控制 | 已复核，未改动 | 确认合规 | **已验证** |

**未变更项**（不在第一批范围内）:
- APISIX Admin API (9180) — 不处理
- etcd (2379) — 不处理
- APISIX 9080 — 不处理

---

## 2. 一、canary-test 容器端口收敛

### 2.1 变更前状态

```
# docker ps
webhook-ingress-canary-test   0.0.0.0:8081->8000/tcp, [::]:8081->8000/tcp   Up 47 hours

# ss -tlnp | grep 8081
LISTEN 0 4096 0.0.0.0:8081 0.0.0.0:*  users:(("docker-proxy",pid=1936783,fd=7))
LISTEN 0 4096 [::]:8081    [::]:*     users:(("docker-proxy",pid=1936788,fd=7))
```

**风险**: 8081 端口绑定 `0.0.0.0`，公网 IP (43.167.177.86) 上 8081 端口理论上可达（取决于防火墙）。

### 2.2 容器信息

| 属性 | 值 |
|------|-----|
| 容器名 | webhook-ingress-canary-test |
| 镜像 | webhook-ingress:factory-adapter |
| 网络 | n8n-linear_default |
| 模式 | canary_dryrun |
| 启动方式 | docker run（非 docker-compose 管理） |
| 卷挂载 | 无 |
| 重启策略 | no |

### 2.3 执行步骤

```bash
# 步骤 1: 备份容器完整配置
TS=$(date +%Y%m%d-%H%M%S)
mkdir -p /opt/n8n-linear/backups/canary-hardening-${TS}
docker inspect webhook-ingress-canary-test > /opt/n8n-linear/backups/canary-hardening-${TS}/container-inspect.json

# 步骤 2: 记录变更前端口状态
ss -tlnp | grep 8081 > /opt/n8n-linear/backups/canary-hardening-${TS}/ss-8081-before.txt
docker ps --filter name=webhook-ingress-canary-test --format "{{.Names}}: {{.Ports}}" > /opt/n8n-linear/backups/canary-hardening-${TS}/docker-ps-before.txt

# 步骤 3: 停止并删除旧容器
docker stop webhook-ingress-canary-test
docker rm webhook-ingress-canary-test

# 步骤 4: 从备份中提取 WEBHOOK_DATABASE_URL
DB_URL=$(python3 -c "
import json
with open('/opt/n8n-linear/backups/canary-hardening-${TS}/container-inspect.json') as f:
    data = json.load(f)
for e in data[0]['Config']['Env']:
    if e.startswith('WEBHOOK_DATABASE_URL='):
        print(e.split('=',1)[1])
        break
")

# 步骤 5: 使用 127.0.0.1:8081 重建容器
docker run -d \
  --name webhook-ingress-canary-test \
  --network n8n-linear_default \
  -p 127.0.0.1:8081:8000 \
  -e WEBHOOK_INGRESS_MODE=canary_dryrun \
  -e FACTORY_LIFECYCLE_ENABLED=true \
  -e WEBHOOK_LOG_LEVEL=INFO \
  -e "WEBHOOK_DATABASE_URL=${DB_URL}" \
  -e LINEAR_WEBHOOK_SECRET=[REDACTED] \
  -e WEBHOOK_SECRET_FACTORY=[REDACTED] \
  webhook-ingress:factory-adapter
```

### 2.4 变更后状态

```
# docker ps
webhook-ingress-canary-test   127.0.0.1:8081->8000/tcp   Up 23 minutes

# ss -tlnp | grep 8081
LISTEN 0 4096 127.0.0.1:8081 0.0.0.0:*  users:(("docker-proxy",pid=2659422,fd=7))
```

**结果**: 端口绑定从 `0.0.0.0:8081` 收窄为 `127.0.0.1:8081`，仅本机 loopback 可达。

### 2.5 备份路径

```
/opt/n8n-linear/backups/canary-hardening-20260509-082747/
├── container-inspect.json       # 完整容器配置备份（含环境变量、端口绑定、网络等）
├── ss-8081-before.txt           # 变更前 ss 端口监听状态
└── docker-ps-before.txt         # 变更前 docker ps 端口映射
```

---

## 3. 二、Cloudflare/nginx 路径控制复核

### 3.1 当前 nginx 配置（未改动）

```nginx
server {
    listen 8080;
    server_name _;

    location = /healthz {
        proxy_pass http://n8n:5678/healthz;
        # ... proxy headers ...
    }

    location = /webhook/events {
        proxy_pass http://webhook-ingress-shadow:8000/webhooks/linear;
        # ... proxy headers ...
    }

    location = /webhooks/factory {
        proxy_pass http://apisix-gateway:9080/webhooks/factory;
        # ... proxy headers ...
    }

    location / {
        return 404;
    }
}
```

### 3.2 Cloudflare Tunnel 架构

- cloudflared 使用 **token-based tunnel**（Cloudflare Dashboard 管理路由），无本地 config.yml
- 隧道入口: `webhook.exa.edu.kg` → cloudflared → nginx gateway (127.0.0.1:5678→8080)
- 路径控制依赖 nginx `location / { return 404; }` catch-all

### 3.3 路径验证结果

#### 通过 nginx gateway 本地验证（127.0.0.1:5678）

| 路径 | 方法 | 预期 | 实际 | 判定 |
|------|------|------|------|------|
| `/healthz` | GET | 200 | **200** | PASS |
| `/webhook/events` | POST 空 body | 401 | **401** | PASS |
| `/webhook/events` | POST 假签名 `sha256=fake...` | 401 | **401** | PASS |
| `/webhooks/factory` | POST 空 body | 401 | **401** | PASS |
| `/random-path-xyz` | GET | 404 | **404** | PASS |
| `/` | GET | 404 | **404** | PASS |
| `/admin` | GET | 404 | **404** | PASS |

#### 通过公网域名验证（https://webhook.exa.edu.kg）

| 路径 | 方法 | 预期 | 实际 | 判定 |
|------|------|------|------|------|
| `/healthz` | GET | 200 | **200** | PASS |
| `/webhook/events` | POST 空 body | 401 | **401** | PASS |
| `/webhook/events` | POST 假签名 | 401 | **401** | PASS |
| `/random-path-xyz` | GET | 404 | **404** | PASS |
| `/` | GET | 404 | **404** | PASS |
| `/admin` | GET | 404 | **404** | PASS |
| `/api` | GET | 404 | **404** | PASS |

### 3.4 结论

nginx catch-all `location / { return 404; }` 正常生效。所有未明确配置的路径均返回 404。无需修改。

---

## 4. 变更后完整证据

### 4.1 docker ps 端口映射（变更后）

```
NAMES                         PORTS                                                                                                STATUS
webhook-ingress-canary-test   127.0.0.1:8081->8000/tcp                                                                             Up 23 minutes
tailscale-socks-proxy                                                                                                              Up 33 hours
apisix-gateway                0.0.0.0:9080->9080/tcp, [::]:9080->9080/tcp, 0.0.0.0:9180->9180/tcp, [::]:9180->9180/tcp, 9443/tcp   Up 46 hours
apisix-etcd                   0.0.0.0:2379->2379/tcp, [::]:2379->2379/tcp, 2380/tcp                                                Up 46 hours
webhook-ingress-shadow        8000/tcp                                                                                             Up 4 days
n8n-linear-webhook            100.100.1.22:5679->5678/tcp                                                                          Up 4 days (healthy)
n8n-linear-postgres           5432/tcp                                                                                             Up 4 days (healthy)
n8n-webhook-gateway           80/tcp, 127.0.0.1:5678->8080/tcp                                                                     Up 4 days
cloudflared-webhook                                                                                                                Up 5 days
codex-proxy                   11434/tcp, 127.0.1:11455->1455/tcp, 127.0.0.1:18080->8080/tcp                                        Up 12 days (healthy)
```

### 4.2 ss -tlnp 端口 8081（变更后）

```
LISTEN 0 4096 127.0.0.1:8081 0.0.0.0:*  users:(("docker-proxy",pid=2659422,fd=7))
```

**对比**: 变更前 `0.0.0.0:8081` → 变更后 `127.0.0.1:8081`

### 4.3 公网 8081 不可达验证

```bash
curl -s -o /dev/null -w "%{http_code}" --connect-timeout 5 http://43.167.177.86:8081/healthz
# 结果: 000 (HTTP code 000 = connection timeout)
# curl exit code: 28 (CURLE_OPERATION_TIMEDOUT)
```

**结论**: 公网 IP:8081 不可达。

### 4.4 /webhook/events 签名校验验证

```
# 空签名 POST
curl -s -o /dev/null -w "%{http_code}" -X POST https://webhook.exa.edu.kg/webhook/events -H "Content-Type: application/json" -d '{}'
→ 401

# 假签名 POST
curl -s -o /dev/null -w "%{http_code}" -X POST https://webhook.exa.edu.kg/webhook/events -H "Content-Type: application/json" -H "Linear-Signature: sha256=fakesignature1234567890abcdef" -d '{"test":true}'
→ 401
```

**结论**: HMAC 签名校验正常，空签名和假签名均返回 401。

### 4.5 未知路径验证

```
curl https://webhook.exa.edu.kg/random-path-xyz → 404
curl https://webhook.exa.edu.kg/                → 404
curl https://webhook.exa.edu.kg/admin           → 404
curl https://webhook.exa.edu.kg/api             → 404
```

**结论**: nginx catch-all 正常，未知路径返回 404。

---

## 5. 回滚步骤

### 5.1 canary-test 容器回滚

```bash
ssh root@node-22

# 步骤 1: 从备份中提取 DB URL
DB_URL=$(python3 -c "
import json
with open('/opt/n8n-linear/backups/canary-hardening-20260509-082747/container-inspect.json') as f:
    data = json.load(f)
for e in data[0]['Config']['Env']:
    if e.startswith('WEBHOOK_DATABASE_URL='):
        print(e.split('=',1)[1])
        break
")

# 步骤 2: 停止当前容器
docker stop webhook-ingress-canary-test
docker rm webhook-ingress-canary-test

# 步骤 3: 恢复原始 0.0.0.0 绑定
docker run -d \
  --name webhook-ingress-canary-test \
  --network n8n-linear_default \
  -p 8081:8000 \
  -e WEBHOOK_INGRESS_MODE=canary_dryrun \
  -e FACTORY_LIFECYCLE_ENABLED=true \
  -e WEBHOOK_LOG_LEVEL=INFO \
  -e "WEBHOOK_DATABASE_URL=${DB_URL}" \
  -e LINEAR_WEBHOOK_SECRET=[FROM_BACKUP] \
  -e WEBHOOK_SECRET_FACTORY=[FROM_BACKUP] \
  webhook-ingress:factory-adapter

# 步骤 4: 验证回滚
ss -tlnp | grep 8081
# 预期: 0.0.0.0:8081 恢复
```

### 5.2 nginx 无需回滚（本次未修改）

---

## 6. 验收标准对照

| # | PASS 条件 | 证据 | 判定 |
|---|-----------|------|------|
| 1 | n8n 仍未裸露公网 | n8n-linear-webhook 仅 `100.100.1.22:5679`（Tailscale），n8n-webhook-gateway 仅 `127.0.0.1:5678` | **PASS** |
| 2 | /webhook/events 空签名返回 401 | 公网 curl → 401 | **PASS** |
| 3 | /webhook/events 假签名返回 401 | 公网 curl → 401 | **PASS** |
| 4 | APISIX Admin API 不再 0.0.0.0/0 | 不在本次范围（未改） | N/A |
| 5 | canary-test 不再绑定 0.0.0.0 | `127.0.0.1:8081->8000/tcp` + ss 确认 | **PASS** |
| 6 | etcd 不再公网可达 | 不在本次范围（未改） | N/A |
| 7 | APISIX 9080 不对公网开放 | 不在本次范围（未改） | N/A |
| 8 | nginx 对未知路径返回 404/403 | 4 个未知路径全部 404 | **PASS** |
| 9 | 现有 webhook 业务链路不被破坏 | /healthz=200, /webhook/events 签名校验正常, /webhooks/factory=401 | **PASS** |
| 10 | 所有证据脱敏 | secret/token/key 均为 [REDACTED] 占位符 | **PASS** |
| 11 | 提供回滚步骤 | 见第 5 节 | **PASS** |
| 12 | 公网 8081 不可访问 | curl exit=28 (timeout), HTTP code=000 | **PASS** |

---

## 7. 最终结论

**PASS**

第一批低风险收敛已完成并验证通过：

1. **canary-test 端口收敛**: `0.0.0.0:8081→8000` → `127.0.0.1:8081→8000`。公网不可达，本机访问正常，容器状态 running，模式 canary_dryrun 正确。
2. **Cloudflare/nginx 路径控制**: 复核确认合规。nginx catch-all 正常返回 404，所有已知路径行为正确（/healthz=200, 空/假签名=401），未知路径全部 404。
3. **业务链路不受影响**: webhook 签名校验正常，无路由被删除或修改。

所有配置变更已备份，回滚步骤已提供。

---

**报告状态**: PASS  
**下一步**: 第二批 — APISIX Admin API (9180) + etcd (2379) + APISIX 9080 收敛
