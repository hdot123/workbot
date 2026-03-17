# 端口映射说明

## 宿主机端口 100 → 容器端口 18789

### 访问方式

从宿主机访问 OpenClaw：

```bash
# Gateway API
curl http://localhost:100/v1/models

# 健康检查
curl http://localhost:100/health

# Web 界面（如果有）
open http://localhost:100
```

### 容器内部

容器内 OpenClaw 仍然监听 18789 端口：

```bash
# 进入容器
docker-compose exec openclaw bash

# 容器内访问
curl http://localhost:18789/health
```

### 端口冲突解决

如果宿主机 100 端口被占用，修改 `docker-compose.yml`：

```yaml
ports:
  - "其他端口:18789"  # 例如 "8080:18789"
```

### 防火墙配置

如需从外部访问，确保防火墙开放 100 端口：

```bash
# macOS
sudo /usr/libexec/ApplicationFirewall/socketfilterfw --add /Users/busiji/workbot/Molt

# Linux (ufw)
sudo ufw allow 100/tcp

# Linux (firewalld)
sudo firewall-cmd --add-port=100/tcp --permanent
sudo firewall-cmd --reload
```

### 端口选择原因

- **100**: 简短易记，低权限端口（需要 root 或 Docker）
- **18789**: OpenClaw 默认端口，容器内保持不变

### 其他常用端口

| 服务 | 容器端口 | 宿主机端口 | 说明 |
|------|---------|-----------|------|
| Gateway API | 18789 | 100 | HTTP API |
| Dashboard | 3000 | - | Web UI（可选） |
