# Voyage 向量模型代理配置文档

**日期**: 2026-03-12
**版本**: v1.0
**状态**: ✅ 已部署并验证

---

## 📋 架构概述

### 问题背景

Voyage 向量 API（api.voyageai.com）在国内访问不稳定，需要通过海外代理服务器访问。

### 解决方案

```
OpenClaw (MacBook)
    ↓
ClawRouter v2.5.6 (192.168.88.27:3000)
    ├─ Chat 模型 → 直连（智谱/百炼）
    └─ Voyage 向量 → gost 代理 (100.100.1.22:1082) → api.voyageai.com
```

### 设计原则

1. **智能路由**: 聊天模型直连，只有向量模型走代理
2. **代理隔离**: Voyage 专用代理端口（1082），不影响其他服务
3. **Tailscale 内网**: 通过 Tailscale 网络连接代理服务器

---

## 🖧 网络拓扑

### 节点信息

| 节点 | 角色 | 物理网络 | Tailscale | 位置 |
|------|------|----------|-----------|------|
| ClawRouter VM | 网关服务 | 192.168.88.27 | 100.100.1.27 | 本地 |
| node-22 | 代理服务器 | 10.7.0.8 | 100.100.1.22 | Tokyo |

### 端口映射

**ClawRouter (192.168.88.27)**
- `3000` - ClawRouter 主服务
- 支持 `/v1/completions`, `/v1/chat/completions`, `/v1/messages`, `/v1/embeddings`

**node-22 代理服务器 (100.100.1.22)**
- `1082` - Voyage HTTP 代理（本文档重点）
- `18081` - SOCKS5 代理（内网通用）
- `18082` - HTTP 代理（Docker 镜像拉取）
- `18443` - Shadowsocks 隧道（公网入口）
- `18080` - gost API 管理接口

---

## ⚙️ 配置详情

### 1. gost 代理服务器配置

**服务器**: node-22 (100.100.1.22)
**配置文件**: `/etc/gost/gost.yaml`

```yaml
services:
  # 1. 公网 TCP 入口 (18443 端口)
  - name: "fast-ss-tunnel"
    addr: ":18443"
    handler:
      type: "ss"
      auth:
        username: "chacha20-ietf-poly1305"
        password: "chacha20-ietf-poly1305"
    listener:
      type: "tcp"

  # 2. Tailscale SOCKS5 代理 (18081 端口)
  - name: "internal-socks5"
    addr: "100.100.1.22:18081"
    handler:
      type: "socks5"
    listener:
      type: "tcp"

  # 3. Tailscale HTTP 代理 (18082 端口，Docker 拉取镜像)
  - name: "internal-http-proxy"
    addr: "100.100.1.22:18082"
    handler:
      type: "http"
    listener:
      type: "tcp"

  # 4. Tailscale HTTP 代理 (1082 端口，Voyage 专用)
  - name: "voyage-proxy"
    addr: "100.100.1.22:1082"
    handler:
      type: "http"
    listener:
      type: "tcp"

# 5. 动态配置与管理 API
api:
  addr: "100.100.1.22:18080"
  pathPrefix: "/api"
  auth:
    username: "admin"
    password: "admin"
```

**部署步骤**:

```bash
# 1. 编辑配置文件
sudo nano /etc/gost/gost.yaml

# 2. 验证配置语法
gost -C /etc/gost/gost.yaml -t

# 3. 重启服务
sudo systemctl restart gost

# 4. 检查服务状态
sudo systemctl status gost

# 5. 验证端口监听
sudo netstat -tlnp | grep 1082
# 应该看到: tcp  0  0 100.100.1.22:1082  0.0.0.0:*  LISTEN  <pid>/gost
```

**systemd 服务文件**: `/etc/systemd/system/gost.service`

```ini
[Unit]
Description=GOST Service on Tokyo Node
After=network.target

[Service]
Type=simple
ExecStart=/usr/local/bin/gost -C /etc/gost/gost.yaml
Restart=on-failure
RestartSec=5s

[Install]
WantedBy=multi-user.target
```

### 2. ClawRouter 配置

**服务器**: ClawRouter VM (192.168.88.27)
**配置文件**: `/opt/clawrouter/.env`

```bash
# Voyage 专属代理配置
VOYAGE_PROXY=http://100.100.1.22:1082

# 注意：聊天模型不需要代理，ClawRouter 会自动直连
```

**关键代码变更** (server.js v2.5.6):

```javascript
// makeRequest 函数支持可选代理
function makeRequest(url, options, body, proxyUrl = null) {
  // 如果指定了代理，使用 curl 通过代理请求
  if (proxyUrl) {
    const curlCmd = `curl -s -x "${proxyUrl}" -X POST "${url}" ...`;
    // ...
  }
  // 否则直连
}

// handleChatCompletions - 聊天模型直连
async function handleChatCompletions(req, res) {
  // ...
  const response = await makeRequest(baseUrl, { method: 'POST', headers }, upstreamPayload, null);
  // 最后一个参数 null 表示不使用代理
}

// handleEmbeddings - Voyage 使用代理
async function handleEmbeddings(req, res) {
  // ...
  const response = await makeRequest(baseUrl, { method: 'POST', headers }, upstreamPayload, VOYAGE_PROXY);
  // 最后一个参数传入 VOYAGE_PROXY 环境变量
}
```

**重启 ClawRouter**:

```bash
cd /opt/clawrouter
sudo docker-compose down
sudo docker-compose up -d
```

### 3. OpenClaw 配置

**配置文件**: `~/.openclaw/openclaw.json`

```json
{
  "models": {
    "providers": {
      "clawrouter": {
        "baseUrl": "http://192.168.88.27:3000",
        "apiKey": "${CLAWROUTER_API_KEY}",
        "api": "openai-completions",
        "models": [
          // ... 16 个模型配置
          {
            "id": "voyage-4",
            "name": "Voyage 4 (向量)",
            "contextWindow": 32000,
            "maxTokens": 4096
          }
        ]
      }
    }
  },
  "agents": {
    "defaults": {
      "memorySearch": {
        "provider": "openai",
        "remote": {
          "baseUrl": "http://192.168.88.27:3000",
          "apiKey": "${CLAWROUTER_API_KEY}"
        },
        "model": "voyage-4"
      }
    }
  }
}
```

---

## ✅ 验证测试

### 1. 检查 gost 代理服务

```bash
# 在 node-22 上检查
ssh root@100.100.1.22 'systemctl status gost'
# 期望: Active: active (running)

ssh root@100.100.1.22 'netstat -tlnp | grep 1082'
# 期望: tcp  0  0 100.100.1.22:1082  0.0.0.0:*  LISTEN
```

### 2. 测试代理连通性

```bash
# 从 ClawRouter VM 测试代理
ssh ubuntu@192.168.88.27 'curl -s -m 5 -x http://100.100.1.22:1082 http://www.google.com > /dev/null && echo "proxy_ok" || echo "proxy_fail"'
# 期望: proxy_ok
```

### 3. 测试 Voyage API

```bash
# 直接测试 ClawRouter 的 embeddings 端点
curl -X POST http://192.168.88.27:3000/v1/embeddings \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${CLAWROUTER_API_KEY}" \
  -d '{"model":"voyage-4","input":"hello world"}' | jq '.data[0].embedding | length'
# 期望: 1024 (Voyage-4 的嵌入维度)

# 查看完整响应
curl -X POST http://192.168.88.27:3000/v1/embeddings \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${CLAWROUTER_API_KEY}" \
  -d '{"model":"voyage-4","input":"test"}'
# 期望: {"object":"list","data":[{"object":"embedding","embedding":[...],"index":0}],"model":"voyage-4","usage":{"prompt_tokens":1,"total_tokens":1}}
```

### 4. 验证智能路由

```bash
# 测试聊天模型（应该直连，不使用代理）
curl -X POST http://192.168.88.27:3000/v1/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${CLAWROUTER_API_KEY}" \
  -d '{"model":"qwen3.5-plus","messages":[{"role":"user","content":"test"}],"max_tokens":10}'

# 检查 ClawRouter 日志，应该看到直连请求
ssh ubuntu@192.168.88.27 'sudo docker logs --tail 20 clawrouter 2>&1 | grep -E "ROUTE|EMBEDDINGS"'
# 聊天请求应该没有 proxy 日志
# Voyage 请求应该有 "proxy: http://100.100.1.22:1082" 日志
```

### 5. 检查 ClawRouter 配置

```bash
# 检查环境变量
ssh ubuntu@192.168.88.27 'sudo docker exec clawrouter env | grep VOYAGE_PROXY'
# 期望: VOYAGE_PROXY=http://100.100.1.22:1082

# 检查健康端点
curl -s http://192.168.88.27:3000/health | jq '.proxy'
# 期望: {
#   "voyage": "http://100.100.1.22:1082",
#   "chat": "direct (no proxy)"
# }
```

---

## 🔧 故障排查

### 问题 1: 代理连接失败

**症状**:
```json
{"error":"代理请求失败：Command failed: curl -s -x \"http://100.100.1.22:1082\" ..."}
```

**诊断步骤**:

1. 检查 gost 服务状态
```bash
ssh root@100.100.1.22 'systemctl status gost'
```

2. 检查端口监听
```bash
ssh root@100.100.1.22 'netstat -tlnp | grep 1082'
```

3. 检查 Tailscale 连接
```bash
# 在 ClawRouter VM 上 ping 代理服务器
ping 100.100.1.22
```

4. 测试代理端口
```bash
# 从 ClawRouter VM 测试
ssh ubuntu@192.168.88.27 'nc -zv 100.100.1.22 1082'
```

**常见原因**:
- gost 服务未启动
- 配置文件 YAML 格式错误（缩进问题）
- Tailscale 连接中断
- 防火墙阻止连接

### 问题 2: ClawRouter 使用错误代理

**症状**:
```bash
sudo docker exec clawrouter env | grep VOYAGE_PROXY
# 显示: VOYAGE_PROXY=http://100.100.1.22:7890 (旧端口)
```

**解决方案**:
```bash
# 1. 更新 .env 文件
sudo sed -i 's|VOYAGE_PROXY=http://100.100.1.22:7890|VOYAGE_PROXY=http://100.100.1.22:1082|' /opt/clawrouter/.env

# 2. 重新创建容器（restart 不会重新加载 .env）
cd /opt/clawrouter
sudo docker-compose down
sudo docker-compose up -d

# 3. 验证
sudo docker exec clawrouter env | grep VOYAGE_PROXY
```

### 问题 3: Voyage API 返回 401

**症状**:
```json
{"error":"Unauthorized","message":"Invalid API key"}
```

**诊断**:
```bash
# 检查 VOYAGE_API_KEY 环境变量
ssh ubuntu@192.168.88.27 'sudo cat /opt/clawrouter/.env | grep VOYAGE_API_KEY'
```

**解决方案**:
- 确认 API Key 有效
- 检查 API Key 是否正确配置在 .env 文件中
- 重启 ClawRouter 容器

### 问题 4: gost 配置语法错误

**症状**:
```
Main PID: 1120550 (code=exited, status=1/FAILURE)
```

**诊断**:
```bash
# 测试配置文件
gost -C /etc/gost/gost.yaml -t
```

**常见错误**:
- YAML 缩进不一致（使用空格，不要用 Tab）
- 服务配置放在 `api:` 部分之后（应该在 `services:` 列表中）
- 端口号格式错误（应该是 `"100.100.1.22:1082"` 而不是 `100.100.1.22:1082`）

---

## 📊 性能监控

### 监控指标

**1. 代理延迟**
```bash
# 测试代理响应时间
time curl -s -x http://100.100.1.22:1082 https://api.voyageai.com/v1/embeddings > /dev/null
```

**2. Voyage API 调用成功率**
```bash
# 查看 ClawRouter 日志中的 Voyage 请求
ssh ubuntu@192.168.88.27 'sudo docker logs --tail 100 clawrouter 2>&1 | grep EMBEDDINGS'
```

**3. gost 连接数**
```bash
# 在 node-22 上查看连接数
ssh root@100.100.1.22 'netstat -an | grep :1082 | grep ESTABLISHED | wc -l'
```

### 日志位置

- **ClawRouter**: `sudo docker logs clawrouter`
- **gost**: `sudo journalctl -u gost -f`
- **OpenClaw**: `~/.openclaw/logs/`

---

## 🔄 维护操作

### 更新 Voyage API Key

```bash
# 1. 在 ClawRouter VM 上更新 .env
ssh ubuntu@192.168.88.27
sudo nano /opt/clawrouter/.env
# 修改 VOYAGE_API_KEY=pa-xxxx

# 2. 重启容器
cd /opt/clawrouter
sudo docker-compose restart

# 3. 验证
curl -X POST http://192.168.88.27:3000/v1/embeddings \
  -H "Authorization: Bearer ${CLAWROUTER_API_KEY}" \
  -d '{"model":"voyage-4","input":"test"}'
```

### 更换代理端口

```bash
# 1. 修改 gost 配置
ssh root@100.100.1.22
sudo nano /etc/gost/gost.yaml
# 修改 addr: "100.100.1.22:新端口"

# 2. 重启 gost
sudo systemctl restart gost

# 3. 更新 ClawRouter 配置
ssh ubuntu@192.168.88.27
sudo nano /opt/clawrouter/.env
# 修改 VOYAGE_PROXY=http://100.100.1.22:新端口

# 4. 重建容器
cd /opt/clawrouter
sudo docker-compose down && sudo docker-compose up -d
```

### 临时禁用代理

```bash
# 方法 1: 从 .env 中移除 VOYAGE_PROXY
ssh ubuntu@192.168.88.27
sudo sed -i '/VOYAGE_PROXY/d' /opt/clawrouter/.env
cd /opt/clawrouter && sudo docker-compose down && sudo docker-compose up -d

# 方法 2: 设置为空字符串
sudo sed -i 's|VOYAGE_PROXY=.*|VOYAGE_PROXY=|' /opt/clawrouter/.env
cd /opt/clawrouter && sudo docker-compose restart
```

---

## 📚 相关文档

- [ClawRouter 部署文档](/Users/busiji/passkills/workspace/projects/clawrouter-vm101.md)
- [OpenClaw 迁移报告](/Users/busiji/passkills/workspace/projects/openclaw-clawrouter-migration-2026-03-12.md)
- [多品牌协议基线](/Users/busiji/passkills/workspace/projects/multi-brand-protocol-baseline-v1.1-final.md)
- [gost 官方文档](https://gost.run/)
- [Voyage API 文档](https://docs.voyageai.com/)

---

## 📝 变更历史

| 日期 | 版本 | 变更内容 |
|------|------|----------|
| 2026-03-12 | v1.0 | 初始版本，配置 Voyage 专用代理（1082 端口） |

---

## 👥 联系方式

如有问题，请检查：
1. ClawRouter 健康端点: http://192.168.88.27:3000/health
2. gost 服务状态: `systemctl status gost`
3. Tailscale 连接状态: `tailscale status`
