---
type: [KB:LESSON]
title: "Ubuntu OpenClaw 部署经验"
created: 2026-03-02 14:53
updated: 2026-03-02 14:53
source: Manual
confidence: high
tags: [ubuntu, openclaw, deployment, nodejs, systemd]
related: [node-11, 2026-03-02-node-11-bailian-models]
version: v1.0
status: active
last_verified: 2026-03-02
---

# Ubuntu OpenClaw 部署经验

## 🚨 常见问题与解决方案

### 问题 1: Mise 安装失败

**症状**: Mise 安装脚本返回退出代码 255

**原因**: 可能是网络问题或脚本兼容性问题

**解决方案**: 使用 NodeSource 直接安装 Node.js

```bash
# 使用 NodeSource 安装 Node.js 22
curl -fsSL https://deb.nodesource.com/setup_22.x | bash -
apt install -y nodejs
```

**建议**: 在 Ubuntu 24.04 上，优先使用 NodeSource 或 apt 安装 Node.js，避免使用 Mise

---

### 问题 2: OpenClaw 包名错误

**症状**: `npm install -g openclaw-cli` 返回 404 Not Found

**原因**: npm 上的包名不是 openclaw-cli

**解决方案**: 使用官方安装脚本

```bash
# 使用官方安装脚本
curl -fsSL --proto '=https' --tlsv1.2 https://openclaw.ai/install.sh | bash -s -- --no-prompt --no-onboard
```

**建议**: 始终使用官方推荐的安装方法，不要猜测包名

---

### 问题 3: PM2 权限问题

**症状**: 普通用户无法全局安装 PM2，返回 EACCES 错误

**原因**: npm 全局目录需要 root 权限

**解决方案**: 使用 systemd 管理服务，而不是 PM2

```bash
# 创建 systemd 服务文件
cat > /etc/systemd/system/openclaw-<user>.service << 'EOF'
[Unit]
Description=OpenClaw Gateway for <User>
After=network.target

[Service]
Type=simple
User=<user>
WorkingDirectory=/home/<user>/.openclaw
Environment="OPENCLAW_CONFIG_PATH=/home/<user>/.openclaw/openclaw.json"
ExecStart=/usr/bin/openclaw gateway
Restart=on-failure
RestartSec=5s

[Install]
WantedBy=multi-user.target
EOF

# 启动服务
systemctl daemon-reload
systemctl start openclaw-<user>
systemctl enable openclaw-<user>
```

**建议**: 在生产环境中，优先使用 systemd 而不是 PM2，更稳定、更标准

---

### 问题 4: 安装脚本退出代码

**症状**: 安装脚本返回退出代码 255，但实际安装成功

**原因**: 可能是 post-install 任务失败，但核心安装成功

**解决方案**: 验证安装结果，而不是依赖退出代码

```bash
# 验证安装
which openclaw && openclaw --version
```

**建议**: 安装后总是验证，不要只看退出代码

---

### 问题 5: 自定义模型提供商配置

**症状**: 需要配置百炼等自定义模型提供商

**解决方案**: 使用 `models.providers` 配置 OpenAI 兼容 API

```json
{
  "models": {
    "mode": "merge",
    "providers": {
      "bailian": {
        "baseUrl": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "apiKey": "your-api-key",
        "api": "openai-completions",
        "models": [
          { "id": "coder-next", "name": "Coder Next" },
          { "id": "coder-plus", "name": "Coder Plus" }
        ]
      }
    }
  }
}
```

**关键配置**:
- `baseUrl`: 百炼的 OpenAI 兼容 API 地址
- `api`: 必须是 `openai-completions`
- `apiKey`: 百炼的 API Key

---

## 📋 部署检查清单

### 1. 系统准备
- [ ] 更新系统: `apt update && apt upgrade -y`
- [ ] 安装必要工具: `apt install -y curl wget git vim`
- [ ] 安装 Node.js: 使用 NodeSource
- [ ] 验证 Node.js: `node --version && npm --version`

### 2. OpenClaw 安装
- [ ] 使用官方安装脚本
- [ ] 验证安装: `openclaw --version`

### 3. 用户创建
- [ ] 创建用户: `useradd -m -s /bin/bash <user>`
- [ ] 创建配置目录: `mkdir -p /home/<user>/.openclaw`
- [ ] 设置权限: `chown -R <user>:<user> /home/<user>/.openclaw`

### 4. 配置文件
- [ ] 创建 openclaw.json
- [ ] 配置 gateway (port, bind, auth)
- [ ] 配置模型 (primary, fallbacks)
- [ ] 配置自定义提供商 (models.providers)

### 5. systemd 服务
- [ ] 创建服务文件: `/etc/systemd/system/openclaw-<user>.service`
- [ ] 重新加载: `systemctl daemon-reload`
- [ ] 启动服务: `systemctl start openclaw-<user>`
- [ ] 启用自启动: `systemctl enable openclaw-<user>`

### 6. 验证测试
- [ ] 检查服务状态: `systemctl status openclaw-<user>`
- [ ] 检查端口监听: `ss -tlnp | grep <port>`
- [ ] HTTP 访问测试: `curl -I http://<ip>:<port>/`

---

## 🔧 配置文件模板

### 基础配置（带百炼模型）

```json
{
  "gateway": {
    "port": 19010,
    "mode": "local",
    "bind": "lan",
    "controlUi": {
      "dangerouslyAllowHostHeaderOriginFallback": true
    },
    "auth": {
      "mode": "token",
      "token": "your-token-here"
    }
  },
  "agents": {
    "defaults": {
      "model": {
        "primary": "bailian/coder-next",
        "fallbacks": ["bailian/coder-plus", "bailian/qwen3-max", "bailian/glm-5"]
      }
    }
  },
  "models": {
    "mode": "merge",
    "providers": {
      "bailian": {
        "baseUrl": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "apiKey": "your-api-key",
        "api": "openai-completions",
        "models": [
          { "id": "coder-next", "name": "Coder Next" },
          { "id": "coder-plus", "name": "Coder Plus" },
          { "id": "qwen3-max", "name": "Qwen3 Max" },
          { "id": "glm-5", "name": "GLM-5" }
        ]
      }
    }
  }
}
```

---

## 📚 经验总结

### 最佳实践

1. **使用 systemd 管理服务**: 比 PM2 更稳定、更标准
2. **使用 NodeSource 安装 Node.js**: 比 Mise 更可靠
3. **使用官方安装脚本**: 不要猜测包名或安装方法
4. **验证安装结果**: 不要只看退出代码
5. **配置日志轮转**: 防止日志文件过大

### 避免的坑

1. **不要使用 Mise**: 在 Ubuntu 24.04 上可能失败
2. **不要猜测包名**: `openclaw-cli` 不存在，使用官方脚本
3. **不要使用 PM2**: 权限问题多，systemd 更好
4. **不要忽略验证**: 安装后必须验证
5. **不要硬编码 API Key**: 考虑使用环境变量

---

## 🔗 相关文档

- **node-11 持续手册**: `workspace/memory/kb/projects/node-11.md`
- **百炼模型选择决策**: `workspace/memory/kb/decisions/2026-03-02-node-11-bailian-models.md`

---

## 🔄 更新历史

- **2026-03-02 14:53**: 初始创建，记录 Ubuntu OpenClaw 部署经验
