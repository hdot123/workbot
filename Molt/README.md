# OpenClaw Molt 工作区

这是一个完整的 OpenClaw 工作区复刻，包含 Molt 的记忆、人格、工具定义和项目文档。

## 目录结构

```
Molt/
├── config/                 # OpenClaw 配置目录（首次运行后生成）
│   └── openclaw.json      # 主配置文件
├── workspace/              # OpenClaw 工作区
│   ├── AGENTS.md          # Agent 操作指令
│   ├── SOUL.md            # 人格定义
│   ├── TOOLS.md           # 工具定义
│   ├── IDENTITY.md        # 身份信息
│   ├── USER.md            # 用户信息
│   ├── HEARTBEAT.md       # 心跳任务
│   ├── MEMORY.md          # 记忆文件
│   ├── projects/          # 项目文档
│   ├── memory/            # 记忆存储
│   └── docs/              # 文档库
├── docker-compose.yml     # Docker Compose 配置
├── manage.sh              # 管理脚本（可执行）
└── README.md              # 本文件
```

## 快速启动

### 1. 首次安装（Onboarding）

```bash
cd /Users/busiji/workbot/Molt
./manage.sh onboard
```

这将：
1. 拉取 OpenClaw 官方镜像
2. 运行配置向导
3. 生成配置文件
4. 启动 Gateway

### 2. 访问 OpenClaw

启动后，OpenClaw 将在以下端口提供服务：

- **Gateway API**: http://localhost:100
- **健康检查**: http://localhost:100/healthz
- **模型列表**: http://localhost:100/v1/models

### 3. 获取 Dashboard Token

```bash
./manage.sh dashboard
```

然后在浏览器中打开提供的 URL，输入 Token 进行认证。

## 日常管理

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

## 设备管理

### 列出设备
```bash
./manage.sh devices list
```

### 批准设备
```bash
./manage.sh devices approve <device-id>
```

## 工作区说明

### 核心文件

- **AGENTS.md**: 定义 Agent 的操作规则和指令
- **SOUL.md**: 定义 Agent 的人格和行为准则
- **TOOLS.md**: 定义可用的工具和权限
- **MEMORY.md**: 长期记忆存储

### 项目文档

`workspace/projects/` 包含：
- ClawRouter 部署文档
- Voyage 代理配置
- Multi-brand 协议基线
- 其他项目产物

### 记忆存储

`workspace/memory/` 包含：
- `kb/`: 知识库（全局知识、经验教训）
- `log/`: 工作日志
- `raw/`: 原始数据

## 修改配置

### 修改人格

编辑 `workspace/SOUL.md`：

```bash
vim workspace/SOUL.md
./manage.sh restart
```

### 修改工具

编辑 `workspace/TOOLS.md`：

```bash
vim workspace/TOOLS.md
./manage.sh restart
```

### 修改主配置

编辑 `config/openclaw.json`：

```bash
vim config/openclaw.json
./manage.sh restart
```

## 端口映射

| 宿主机端口 | 容器端口 | 说明 |
|-----------|---------|------|
| **100** | 18789 | OpenClaw Gateway API |

### 端口冲突

如果端口 100 被占用，修改 `docker-compose.yml` 中的端口映射：

```yaml
ports:
  - "其他端口:18789"  # 例如 "8080:18789"
```

## 故障排查

### 1. 容器无法启动

```bash
# 检查容器状态
./manage.sh status

# 查看错误日志
./manage.sh logs
```

### 2. 配置文件不存在

```bash
# 检查配置文件
ls -la config/openclaw.json

# 如果不存在，重新运行 onboarding
./manage.sh onboard
```

### 3. 工作区未加载

```bash
# 进入容器检查
./manage.sh shell
ls -la /root/.openclaw/workspace/
```

### 4. 端口被占用

```bash
# 检查端口占用
lsof -i :100

# 修改端口映射
vim docker-compose.yml
```

## 备份与恢复

### 备份

```bash
./manage.sh backup
# 生成 workspace-backup-YYYYMMDD-HHMMSS.tar.gz
```

### 恢复

```bash
tar -xzf workspace-backup-20260315.tar.gz -C /Users/busiji/workbot/Molt/
./manage.sh restart
```

## 资源限制

当前配置的资源限制：

- CPU: 最多 2 核
- 内存: 最多 2GB

可以根据需要调整 `docker-compose.yml` 中的 `deploy.resources` 部分。

## 相关文档

- **本地文档**：
  - [QUICKSTART.md](QUICKSTART.md) - 快速启动指南
  - [DEPLOYMENT.md](DEPLOYMENT.md) - 部署报告
  - [PORT.md](PORT.md) - 端口映射说明

- **OpenClaw 官方文档**：
  - [OpenClaw 官方文档](https://docs.openclaw.ai/)
  - [Agent Workspace](https://docs.openclaw.ai/concepts/agent-workspace)
  - [Memory](https://docs.openclaw.ai/concepts/memory)
  - [Docker 部署](https://docs.openclaw.ai/install/docker)

---

**创建日期**: 2026-03-15
**版本**: v2.0
**状态**: Ready for deployment
**镜像**: ghcr.io/openclaw/openclaw:latest
