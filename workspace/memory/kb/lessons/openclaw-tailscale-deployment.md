---
title: "OpenClaw + Tailscale 完美部署指南"
created: 2026-03-08 11:40
updated: 2026-03-11 11:55
source: Agent
confidence: high
tags: [openclaw, tailscale, deployment, proxy, https, docker, mcp, web-search]
related: [node-00, node-22]
version: v1.2
status: active
last_verified: 2026-03-11
---

# OpenClaw + Tailscale 完美部署指南

本指南是为了保证 100% 成功部署 [OpenClaw](https://openclaw.ai) 并通过 **Tailscale Serve** 提供内网 HTTPS 穿透访问而编写。

> **核心避坑指南（基于 node-00/node-22 故障排查总结）**：
> 1. **不要配置 `gateway.bind`**：无论是 `"0.0.0.0"` 还是 `"lan"`，都会导致冲突或拒绝启动。
> 2. **Docker 命令行不要加 `--bind` 参数**：`openclaw gateway --bind lan` 会覆盖配置文件，与 `auth.mode: "none"` 冲突导致启动失败。
> 3. **必须配置 `trustedProxies`**：添加 `100.64.0.0/10` (Tailscale CGNAT 网段)，否则 Tailscale Serve 代理无法正常工作。
> 4. **必须配置 `dangerouslyAllowHostHeaderOriginFallback: true`**：允许 Tailscale Serve 的 Host 头回退。
> 5. **Tailscale Serve 必须用 HTTPS**：`tailscale serve --bg --https=18789 127.0.0.1:18789`，否则报 SSL 错误。
> 6. **联网搜索 MCP 需要通用 API Key**：必须使用百炼通用 API Key（`sk-xxx`），不能使用 Coding Plan 专属 API Key（`sk-sp-xxx`）。

## 步骤 1：安装与初始化

1. 安装 Node.js (建议 v22) 和 pnpm：
   ```bash
   curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh | bash
   source ~/.bashrc
   nvm install 22
   npm install -g pnpm
   ```

2. 全局安装 OpenClaw，并运行初始化：
   ```bash
   pnpm install -g openclaw
   # 运行初始化向导（如果你想跳过所有人工确认，可加上 --non-interactive）
   openclaw onboard
   ```

## 步骤 2：配置 OpenClaw 监听与免密（关键）

1. 打开配置文件进行修改：
   ```bash
   nano ~/.openclaw/openclaw.json
   ```

2. 确保配置项按如下结构编写。请仔细检查以下几点：
   - **不要配置 `gateway.bind` 字段**（使用默认值）。
   - `auth` 必须设置为 `none` 模式。
   - `trustedProxies` 必须添加 `100.64.0.0/10`，这是 Tailscale 的 CGNAT 网段。
   - `controlUi.allowedOrigins` 必须涵盖 HTTP 和 HTTPS 的 localhost 以及 TS 域名。
   - `dangerouslyAllowHostHeaderOriginFallback` 必须设置为 `true`。

   ```json
   {
     "gateway": {
       "mode": "local",
       "port": 18789,
       "trustedProxies": [
         "127.0.0.1",
         "::1",
         "100.64.0.0/10"
       ],
       "auth": {
         "mode": "none"
       },
       "controlUi": {
         "allowedOrigins": [
           "http://localhost:18789",
           "http://127.0.0.1:18789",
           "http://您的机器名.tailxxxx.ts.net:18789",
           "https://您的机器名.tailxxxx.ts.net:18789"
         ],
         "dangerouslyAllowHostHeaderOriginFallback": true
       }
     }
   }
   ```

3. **Docker Compose 部署注意事项**：
   - 命令行**不要**加 `--bind` 参数：
     ```yaml
     # ❌ 错误示例
     command: npx openclaw gateway --port 18789 --bind lan

     # ✅ 正确示例
     command: npx openclaw gateway --port 18789
     ```
   - 使用 `network_mode: host` 获得最佳网络性能。

4. 可选：通过 `systemctl --user restart openclaw-gateway` 重启服务（裸机部署）。

## 步骤 3：配置底层 API Key（重要）

推荐直接使用环境变量或 `openclaw configure` 命令注入底层模型服务的密钥。

**方式 A（最稳健）：系统环境变量挂载**
```bash
echo 'export ANTHROPIC_API_KEY="sk-ant-xx..."' >> ~/.bashrc
source ~/.bashrc
systemctl --user restart openclaw-gateway
```

**方式 B：通过 Onboard 命令注入**
```bash
openclaw onboard --anthropic-api-key "sk-ant-xx..."
```

## 步骤 4：配置联网搜索 MCP（可选）

为 OpenClaw 添加联网搜索能力，支持实时信息检索。

### 前提条件

1. 已开通百炼 Coding Plan
2. 在百炼控制台开通"联网搜索 MCP 服务"（每月 2000 次免费额度）
3. 获取**百炼通用 API Key**（格式：`sk-xxx`，注意：不是 Coding Plan 专属 API Key `sk-sp-xxx`）

### 配置步骤

**1. 在容器内安装 MCPorter**
```bash
docker exec openclaw npm install -g mcporter
```

**2. 启用 MCPorter**
```bash
docker exec openclaw sh -c 'cd /root/.openclaw && npx -y openclaw@latest config set skills.entries.mcporter.enabled true'
```

**3. 添加联网搜索 MCP**
```bash
docker exec openclaw sh -c 'cd /root/.openclaw/workspace && mcporter config add WebSearch https://dashscope.aliyuncs.com/api/v1/mcps/WebSearch/mcp --transport http --header "Authorization=Bearer YOUR_API_KEY"'
```

> **重要**：将 `YOUR_API_KEY` 替换为百炼通用 API Key（`sk-xxx` 格式）

**4. 验证配置**
```bash
docker exec openclaw sh -c 'cd /root/.openclaw/workspace && mcporter list WebSearch --schema'
```

期望输出应包含：
```
function bailian_web_search(query: string, count?: number);
```

**5. 测试联网搜索**
```bash
docker exec openclaw sh -c 'cd /root/.openclaw/workspace && mcporter call WebSearch.bailian_web_search query="阿里云新闻" count=3'
```

**6. 重启容器使配置生效**
```bash
docker restart openclaw
```

### 使用方法

在 OpenClaw 对话中明确提及工具名称：
- "用 websearch MCP 搜索阿里云的最新动态"
- "使用 bailian_web_search 查询天气预报"

### 故障排查

**401 认证错误**：
- 检查是否使用了**通用 API Key**（`sk-xxx`），而非 Coding Plan 专属 Key（`sk-sp-xxx`）
- 确认已在百炼控制台开通联网搜索 MCP 服务

**工具未调用**：
- 在对话中明确提及 "websearch MCP" 或 "bailian_web_search"
- 检查 MCPorter 配置：`docker exec openclaw mcporter list`

## 步骤 5：配置 Tailscale Serve (HTTPS 内网穿透)

由于大部分客户端强制校验 TLS/HTTPS，我们需要让 Tailscale 接管外部 HTTPS 请求，并反向代理回本地 18789 的 OpenClaw 服务。

1. 清除旧的 HTTP 代理（如果有）：
   ```bash
   tailscale serve --http=18789 off
   ```

2. 启动 HTTPS 服务（后台运行）：
   ```bash
   tailscale serve --bg --https=18789 127.0.0.1:18789
   ```

3. 检查状态：
   ```bash
   tailscale serve status
   ```
   > 期望输出应当包含：`https://您的机器名.tailxxxx.ts.net:18789/ |-- proxy http://127.0.0.1:18789`

## 步骤 6：设备授权与 TUI 测试

1. 在操作设备上运行：`openclaw tui`。此时因为是第一次连接，会提示 `Error: pairing required`。
2. 保持那个界面卡在那，另开一个 SSH 窗口进入服务器，运行：
   ```bash
   openclaw devices list
   ```
3. 您会看到状态为 `Pending` 的授权申请（通常会有客户端 UUID 和请求 ID）。
4. 批准该请求：
   ```bash
   openclaw devices approve <此处的请求ID>
   ```

至此，控制端（TUI 或是浏览器访问 HTTPS 域名）会立刻变成 `connected` 状态。

---

## 常见问题排查

### 1. "Refusing to bind gateway to lan without auth"

**原因**：Docker Compose 命令行使用了 `--bind lan`，与 `auth.mode: "none"` 冲突。

**解决**：移除命令行中的 `--bind` 参数，让 gateway 使用默认绑定。

```yaml
# docker-compose.yml
command: npx openclaw gateway --port 18789
```

### 2. JSON5 解析失败 "invalid character"

**原因**：使用 heredoc 写入 JSON 时引号丢失。

**解决**：使用 `scp` 或正确的转义：
```bash
# 方法 1: scp 传输本地文件
scp openclaw.json root@server:/opt/openclaw/

# 方法 2: heredoc 使用转义引号
cat > config.json << 'EOF'
{"key": "value"}
EOF
```

### 3. "pairing required" 设备未授权

**原因**：新设备首次连接需要管理员批准。

**解决**：在服务器上批准设备请求：
```bash
openclaw devices list
openclaw devices approve <requestId>
```

### 4. Tailscale Serve 连接失败

**检查清单**：
- [ ] `trustedProxies` 包含 `100.64.0.0/10`
- [ ] `dangerouslyAllowHostHeaderOriginFallback: true`
- [ ] `allowedOrigins` 包含 HTTPS 的 TS 域名
- [ ] Tailscale Serve 使用 `--https` 而非 `--http`

### 5. 联网搜索 MCP 返回 401 错误

**原因**：使用了 Coding Plan 专属 API Key（`sk-sp-xxx`），而非百炼通用 API Key。

**解决**：
1. 在百炼控制台创建通用 API Key（`sk-xxx` 格式）
2. 重新配置 MCPorter：
   ```bash
   docker exec openclaw sh -c 'cd /root/.openclaw/workspace && mcporter config remove WebSearch'
   docker exec openclaw sh -c 'cd /root/.openclaw/workspace && mcporter config add WebSearch https://dashscope.aliyuncs.com/api/v1/mcps/WebSearch/mcp --transport http --header "Authorization=Bearer sk-xxx"'
   docker restart openclaw
   ```

---

## 完整 Docker Compose 示例

```yaml
version: "3.9"

services:
  openclaw:
    image: node:22-alpine
    container_name: openclaw
    restart: unless-stopped
    network_mode: host
    environment:
      - NODE_ENV=production
      - NODE_OPTIONS=--max-old-space-size=1024
    volumes:
      - /opt/openclaw:/root/.openclaw
      - openclaw-cache:/root/.npm
    deploy:
      resources:
        limits:
          memory: 1G
        reservations:
          memory: 512M
    logging:
      driver: json-file
      options:
        max-size: "10m"
        max-file: "3"
    command: |
      ash -c "apk add --no-cache git
      npx -y openclaw@latest gateway --port 18789"

volumes:
  openclaw-cache:
```

**部署命令**：
```bash
# 1. 上传配置文件
scp openclaw.json root@server:/opt/openclaw/

# 2. 启动容器
docker compose up -d

# 3. 配置 Tailscale Serve
tailscale serve --bg --https=18789 127.0.0.1:18789

# 4. 验证健康状态
curl https://您的机器名.tailxxxx.ts.net:18789/health
```
