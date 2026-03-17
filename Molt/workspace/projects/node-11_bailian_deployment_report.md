# node-11 百炼 Coding Plan 部署报告

> CANONICAL: workspace/memory/kb/projects/node-11.md

**部署日期**: 2026-03-02  
**执行者**: Molt 国王  
**指挥官**: HT  
**状态**: ✅ 部署成功

---

## 📋 系统信息

### 服务器信息
- **主机名**: ubuntu-2404
- **IP 地址**: 192.168.88.30
- **系统**: Ubuntu 24.04 LTS (Noble Numbat)
- **内核**: Linux (具体版本未记录)
- **硬件**: 11GB RAM
- **用途**: 计算节点，运行 dev-bot 和 qa-bot

### 软件版本
- **Node.js**: v22.22.0 (通过 NodeSource 安装)
- **npm**: 10.9.4
- **OpenClaw**: v2026.3.1
- **进程管理**: systemd (未使用 PM2)

---

## 🎯 部署目标

### Dev Bot
- **端口**: 19010
- **模型优先级**: coder-next → coder-plus → qwen3-max → glm-5
- **用途**: 开发任务

### QA Bot
- **端口**: 19050
- **模型优先级**: coder-plus → coder-next → qwen3-max → glm-4.7
- **用途**: QA 任务

### Reserved
- **端口**: 19090
- **模型优先级**: 与 dev-bot 相同
- **用途**: 预留（未启动）

### 共享配置
- **API Key**: sk-sp-fdf3de2a9f4a4bc4a00cd98052343a8d (百炼 Coding Plan)
- **API Base URL**: https://dashscope.aliyuncs.com/compatible-mode/v1

---

## 📝 部署步骤

### 1. 系统准备

```bash
# 更新系统
apt update && apt upgrade -y

# 安装必要工具
apt install -y curl wget git vim
```

### 2. 安装 Node.js 22

```bash
# 使用 NodeSource 安装 Node.js 22
curl -fsSL https://deb.nodesource.com/setup_22.x | bash -
apt install -y nodejs

# 验证安装
node --version  # v22.22.0
npm --version   # 10.9.4
```

**注意**: 最初尝试使用 Mise 安装 Node.js，但 Mise 安装脚本返回退出代码 255，因此改用 NodeSource。

### 3. 安装 OpenClaw

```bash
# 使用官方安装脚本
curl -fsSL --proto '=https' --tlsv1.2 https://openclaw.ai/install.sh | bash -s -- --no-prompt --no-onboard

# 验证安装
openclaw --version  # 2026.3.1
```

**注意**: 
- `npm install -g openclaw-cli` 会返回 404 错误（包名不对）
- 安装脚本可能返回退出代码 255，但 OpenClaw 实际上已成功安装

### 4. 创建用户

```bash
# 创建3个用户
useradd -m -s /bin/bash dev-bot
useradd -m -s /bin/bash qa-bot
useradd -m -s /bin/bash reserved
```

### 5. 配置 OpenClaw

#### 5.1 dev-bot 配置

**配置文件**: `/home/dev-bot/.openclaw/openclaw.json`

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
      "token": "dev-bot-token-19010"
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
        "apiKey": "sk-sp-fdf3de2a9f4a4bc4a00cd98052343a8d",
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

#### 5.2 qa-bot 配置

**配置文件**: `/home/qa-bot/.openclaw/openclaw.json`

```json
{
  "gateway": {
    "port": 19050,
    "mode": "local",
    "bind": "lan",
    "controlUi": {
      "dangerouslyAllowHostHeaderOriginFallback": true
    },
    "auth": {
      "mode": "token",
      "token": "qa-bot-token-19050"
    }
  },
  "agents": {
    "defaults": {
      "model": {
        "primary": "bailian/coder-plus",
        "fallbacks": ["bailian/coder-next", "bailian/qwen3-max", "bailian/glm-4.7"]
      }
    }
  },
  "models": {
    "mode": "merge",
    "providers": {
      "bailian": {
        "baseUrl": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "apiKey": "sk-sp-fdf3de2a9f4a4bc4a00cd98052343a8d",
        "api": "openai-completions",
        "models": [
          { "id": "coder-next", "name": "Coder Next" },
          { "id": "coder-plus", "name": "Coder Plus" },
          { "id": "qwen3-max", "name": "Qwen3 Max" },
          { "id": "glm-4.7", "name": "GLM-4.7" },
          { "id": "glm-5", "name": "GLM-5" }
        ]
      }
    }
  }
}
```

#### 5.3 reserved 配置

**配置文件**: `/home/reserved/.openclaw/openclaw.json`

与 dev-bot 配置类似，端口改为 19090，token 改为 "reserved-token-19090"。

### 6. 创建 systemd 服务

#### 6.1 dev-bot 服务

**服务文件**: `/etc/systemd/system/openclaw-dev-bot.service`

```ini
[Unit]
Description=OpenClaw Gateway for Dev Bot
After=network.target

[Service]
Type=simple
User=dev-bot
WorkingDirectory=/home/dev-bot/.openclaw
Environment="OPENCLAW_CONFIG_PATH=/home/dev-bot/.openclaw/openclaw.json"
ExecStart=/usr/bin/openclaw gateway
Restart=on-failure
RestartSec=5s

[Install]
WantedBy=multi-user.target
```

#### 6.2 qa-bot 服务

**服务文件**: `/etc/systemd/system/openclaw-qa-bot.service`

```ini
[Unit]
Description=OpenClaw Gateway for QA Bot
After=network.target

[Service]
Type=simple
User=qa-bot
WorkingDirectory=/home/qa-bot/.openclaw
Environment="OPENCLAW_CONFIG_PATH=/home/qa-bot/.openclaw/openclaw.json"
ExecStart=/usr/bin/openclaw gateway
Restart=on-failure
RestartSec=5s

[Install]
WantedBy=multi-user.target
```

#### 6.3 reserved 服务

**服务文件**: `/etc/systemd/system/openclaw-reserved.service`

与 dev-bot 服务类似，User 和路径改为 reserved。

### 7. 启动服务

```bash
# 重新加载 systemd 配置
systemctl daemon-reload

# 启动并启用 dev-bot 服务
systemctl start openclaw-dev-bot
systemctl enable openclaw-dev-bot

# 启动并启用 qa-bot 服务
systemctl start openclaw-qa-bot
systemctl enable openclaw-qa-bot

# reserved 服务暂不启动
```

---

## 🔍 验证测试

### 服务状态

```bash
# 检查 dev-bot 服务状态
systemctl status openclaw-dev-bot

# 检查 qa-bot 服务状态
systemctl status openclaw-qa-bot
```

**预期结果**:
- Active: active (running)
- [gateway] agent model: bailian/coder-next (dev-bot)
- [gateway] agent model: bailian/coder-plus (qa-bot)

### 端口监听

```bash
# 检查端口监听
ss -tlnp | grep -E '19010|19050|19090'
```

**预期结果**:
```
LISTEN 0 511 0.0.0.0:19010 0.0.0.0:* users:(("openclaw-gatewa",pid=4351,fd=22))
LISTEN 0 511 0.0.0.0:19050 0.0.0.0:* users:(("openclaw-gatewa",pid=4477,fd=22))
```

### HTTP 访问测试

```bash
# 测试 dev-bot 访问
curl -s -o /dev/null -w "%{http_code}" http://192.168.88.30:19010/

# 测试 qa-bot 访问
curl -s -o /dev/null -w "%{http_code}" http://192.168.88.30:19050/
```

**预期结果**: HTTP 200

---

## 🌐 访问方式

### HTTP 访问（局域网）

**dev-bot**:
- URL: `http://192.168.88.30:19010/`
- Token: `dev-bot-token-19010`
- 使用方式: `http://192.168.88.30:19010/?token=dev-bot-token-19010`

**qa-bot**:
- URL: `http://192.168.88.30:19050/`
- Token: `qa-bot-token-19050`
- 使用方式: `http://192.168.88.30:19050/?token=qa-bot-token-19050`

**reserved**（未启动）:
- URL: `http://192.168.88.30:19090/`
- Token: `reserved-token-19090`

### HTTPS 访问（如需配置）

需要配置 Caddy 反向代理和 Tailscale 证书，参考原 Debian 版部署文档。

---

## 🔧 服务管理

### 启动服务

```bash
systemctl start openclaw-dev-bot
systemctl start openclaw-qa-bot
systemctl start openclaw-reserved  # 如需启动
```

### 停止服务

```bash
systemctl stop openclaw-dev-bot
systemctl stop openclaw-qa-bot
systemctl stop openclaw-reserved
```

### 重启服务

```bash
systemctl restart openclaw-dev-bot
systemctl restart openclaw-qa-bot
```

### 查看日志

```bash
# 查看 systemd 日志
journalctl -u openclaw-dev-bot -f
journalctl -u openclaw-qa-bot -f

# 查看 OpenClaw 日志
tail -f /tmp/openclaw-1000/openclaw-2026-03-02.log  # dev-bot
tail -f /tmp/openclaw-1001/openclaw-2026-03-02.log  # qa-bot
```

### 检查服务状态

```bash
systemctl status openclaw-dev-bot
systemctl status openclaw-qa-bot
```

---

## 🚨 故障排除

### 问题 1: 服务无法启动

**症状**: `systemctl status openclaw-dev-bot` 显示 failed

**排查步骤**:
1. 检查配置文件语法: `cat /home/dev-bot/.openclaw/openclaw.json`
2. 检查日志: `journalctl -u openclaw-dev-bot -n 50`
3. 检查端口占用: `ss -tlnp | grep 19010`
4. 手动启动测试: `su - dev-bot -c "openclaw gateway"`

### 问题 2: 模型调用失败

**症状**: 日志显示 API 调用错误

**排查步骤**:
1. 检查 API Key 是否有效
2. 检查网络连接: `curl -I https://dashscope.aliyuncs.com`
3. 检查模型名称是否正确
4. 检查 API 配额是否用完

### 问题 3: 端口被占用

**症状**: `listen tcp :19010: bind: address already in use`

**解决方法**:
```bash
# 查找占用端口的进程
lsof -i :19010

# 杀掉进程
kill -9 <PID>

# 重启服务
systemctl restart openclaw-dev-bot
```

### 问题 4: 权限问题

**症状**: 服务启动失败，日志显示权限错误

**解决方法**:
```bash
# 检查文件权限
ls -la /home/dev-bot/.openclaw/

# 修复权限
chown -R dev-bot:dev-bot /home/dev-bot/.openclaw/
```

---

## 📚 经验教训

### 1. Mise 安装失败

**问题**: Mise 安装脚本返回退出代码 255

**原因**: 可能是网络问题或脚本兼容性问题

**解决**: 使用 NodeSource 直接安装 Node.js，更稳定可靠

**建议**: 在 Ubuntu 24.04 上，优先使用 NodeSource 或 apt 安装 Node.js

### 2. OpenClaw 包名错误

**问题**: `npm install -g openclaw-cli` 返回 404

**原因**: npm 上的包名不是 openclaw-cli

**解决**: 使用官方安装脚本: `curl -fsSL https://openclaw.ai/install.sh | bash`

**建议**: 始终使用官方推荐的安装方法

### 3. PM2 权限问题

**问题**: 普通用户无法全局安装 PM2 (EACCES)

**原因**: npm 全局目录需要 root 权限

**解决**: 使用 systemd 管理服务，而不是 PM2

**建议**: 在生产环境中，优先使用 systemd 而不是 PM2

### 4. 安装脚本退出代码

**问题**: 安装脚本返回退出代码 255，但实际安装成功

**原因**: 可能是 post-install 任务失败，但核心安装成功

**解决**: 验证安装结果，而不是依赖退出代码

**建议**: 安装后总是验证: `which openclaw && openclaw --version`

### 5. 百炼 API 配置

**问题**: 需要配置自定义模型提供商

**解决**: 使用 `models.providers` 配置百炼的 OpenAI 兼容 API

**关键配置**:
- baseUrl: `https://dashscope.aliyuncs.com/compatible-mode/v1`
- api: `openai-completions`
- apiKey: 百炼的 API Key

---

## 📊 资源使用

### 端口分配

| 服务 | 端口 | 说明 | 状态 |
|------|------|------|------|
| dev-bot | 19010 | 开发 Bot | ✅ 运行中 |
| qa-bot | 19050 | QA Bot | ✅ 运行中 |
| reserved | 19090 | 预留 Bot | ⏸️ 未启动 |

### 用户分配

| 用户 | 家目录 | 配置目录 | 用途 |
|------|--------|----------|------|
| dev-bot | /home/dev-bot | /home/dev-bot/.openclaw | 开发任务 |
| qa-bot | /home/qa-bot | /home/qa-bot/.openclaw | QA 任务 |
| reserved | /home/reserved | /home/reserved/.openclaw | 预留 |

### 系统资源

- **内存使用**: dev-bot ~376MB, qa-bot ~354MB
- **CPU 使用**: 启动时较高，稳定后较低
- **磁盘使用**: Node.js + OpenClaw ~237MB

---

## 🔐 安全建议

1. **API Key 管理**:
   - 定期更换 API Key
   - 不要在公开的代码仓库中提交 API Key
   - 考虑使用环境变量而不是直接写在配置文件中

2. **网络安全**:
   - 当前配置绑定到 lan (0.0.0.0)，确保只在可信网络中使用
   - 考虑配置防火墙规则，限制端口访问
   - 如需公网访问，配置 Caddy + Tailscale 证书

3. **Token 管理**:
   - 当前使用的 token 较简单，建议使用更强的随机 token
   - 定期更换 token

4. **日志监控**:
   - 定期检查日志，发现异常及时处理
   - 考虑配置日志轮转，防止日志文件过大

---

## 📋 后续工作

### 短期（1周内）

1. **功能测试**:
   - 测试百炼模型的实际调用
   - 验证模型优先级是否正常工作
   - 测试 failover 机制

2. **监控配置**:
   - 配置服务监控
   - 设置告警机制
   - 记录资源使用情况

3. **文档完善**:
   - 补充实际使用案例
   - 记录常见问题及解决方法

### 中期（1个月内）

1. **HTTPS 配置**:
   - 配置 Caddy 反向代理
   - 配置 Tailscale 证书
   - 启用 HTTPS 访问

2. **性能优化**:
   - 根据实际使用情况调整配置
   - 优化模型调用策略
   - 监控和优化资源使用

3. **reserved 用户**:
   - 根据需求决定是否启动
   - 配置特定的模型优先级
   - 测试和验证

### 长期（3个月内）

1. **扩展部署**:
   - 考虑在其他节点部署类似服务
   - 实现负载均衡
   - 配置高可用

2. **自动化**:
   - 编写自动化部署脚本
   - 配置 CI/CD 流程
   - 实现自动化测试

---

## 📞 联系信息

- **部署执行者**: Molt 国王 (战术蟹王)
- **指挥官**: HT
- **部署日期**: 2026-03-02
- **文档版本**: 1.0

---

## 🔗 相关文档

- [node-11 多租客部署文档 (Debian 版)](./node-11_multi_tenant_deployment.md)
- [node-11 多租客部署文档 (Ubuntu 版)](./node-11_multi_tenant_deployment_ubuntu.md)
- [记忆系统升级报告](../memory/reflections/2026-03-02-memory-upgrade-report.md)

---

**最后更新**: 2026-03-02 13:40  
**状态**: ✅ 部署成功，文档完成
