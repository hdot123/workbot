# OpenClaw Molt - 快速启动指南

## 前置要求

1. **OrbStack** 或 **Docker Desktop** 已安装并运行
2. **API Key** 已准备好（至少需要 Anthropic 或 OpenAI API Key）

## 启动步骤

### 1. 首次安装（Onboarding）

```bash
cd /Users/busiji/workbot/Molt
./manage.sh onboard
```

这将运行 OpenClaw 配置向导，按提示选择：
1. **LLM Provider**: Anthropic Claude / OpenAI / 等
2. **API Key**: 输入你的 API Key
3. **Gateway Port**: 18789（容器内，已映射到宿主机100端口）
4. **其他选项**: 按需选择

### 2. 验证启动

```bash
# 检查容器状态
./manage.sh status

# 健康检查
curl http://localhost:100/healthz | jq '.'

# 预期输出：
# {
#   "ok": true,
#   ...
# }
```

### 3. 获取 Dashboard Token

```bash
./manage.sh dashboard
```

这将生成一个包含 Token 的 URL，在浏览器中打开并输入 Token 即可访问 Dashboard。

## 常用操作

### 启动服务
```bash
./manage.sh start
```

### 停止服务
```bash
./manage.sh stop
```

### 重启服务
```bash
./manage.sh restart
```

### 查看日志
```bash
./manage.sh logs
```

### 查看状态
```bash
./manage.sh status
```

### 进入容器
```bash
./manage.sh shell
```

### 更新镜像
```bash
./manage.sh update
./manage.sh restart
```

### 备份工作区
```bash
./manage.sh backup
```

## 修改工作区文件

工作区文件位于 `workspace/` 目录，修改后会立即生效（部分文件可能需要重启容器）。

### 修改人格
```bash
vim workspace/SOUL.md
./manage.sh restart
```

### 修改记忆
```bash
vim workspace/MEMORY.md
```

### 修改工具
```bash
vim workspace/TOOLS.md
./manage.sh restart
```

## 设备管理

### 列出设备
```bash
./manage.sh devices list
```

### 批准设备
```bash
./manage.sh devices approve <device-id>
```

## 故障排查

### 容器无法启动

1. 检查 Docker/OrbStack 是否运行：
   ```bash
   docker info
   ```

2. 检查配置文件是否存在：
   ```bash
   ls -la config/openclaw.json
   ```

3. 查看错误日志：
   ```bash
   docker compose logs openclaw-gateway
   ```

### 端口被占用

修改 `docker-compose.yml` 中的端口映射：
```yaml
ports:
  - "其他端口:18789"  # 例如 "8080:18789"
```

### 工作区未加载

检查挂载是否正确：
```bash
./manage.sh shell
ls -la /root/.openclaw/workspace/
```

## 访问地址

启动成功后：

- **Gateway API**: http://localhost:100
- **健康检查**: http://localhost:100/healthz
- **模型列表**: http://localhost:100/v1/models

## 下一步

1. 配置 WhatsApp/Telegram/Discord 等通道（可选）
2. 自定义 `SOUL.md` 人格
3. 添加自定义工具到 `TOOLS.md`
4. 在 `HEARTBEAT.md` 中配置定时任务

## 相关文档

- [README.md](README.md) - 完整文档
- [DEPLOYMENT.md](DEPLOYMENT.md) - 部署报告
- [OpenClaw 官方文档](https://docs.openclaw.ai/)

---

**需要帮助？** 运行 `./manage.sh` 查看所有可用命令。
