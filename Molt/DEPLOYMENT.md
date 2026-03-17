# OpenClaw Molt 工作区 - 最终部署指南

**部署日期**: 2026-03-15
**目标路径**: /Users/busiji/workbot/Molt
**状态**: ✅ 部署就绪（基于官方文档）

---

## 部署概览

### 1. Workspace 复刻 ✅

- **源路径**: `/Users/busiji/passkills/workspace`
- **目标路径**: `/Users/busiji/workbot/Molt/workspace`
- **文件总数**: 462 个文件
- **总大小**: 约 3.96 MB
- **Markdown 文档**: 405 个

**复刻内容包括**：
- ✅ OpenClaw 核心文件（AGENTS.md, SOUL.md, TOOLS.md 等）
- ✅ 项目文档（projects/）
- ✅ 记忆存储（memory/）
- ✅ 文档库（docs/）
- ✅ 技能定义（skills/）

---

## 2. Docker 配置（基于官方文档）✅

### docker-compose.yml

**官方镜像**: `ghcr.io/openclaw/openclaw:latest`

**服务架构**：
- `openclaw-gateway` - 主服务（Gateway + Agent）
- `openclaw-cli` - CLI 工具（用于管理命令）

**端口映射**：
- `100:18789` - Gateway HTTP API (宿主机100端口映射到容器18789端口)

**Volume 挂载**：
- `./config:/root/.openclaw:rw` - 配置目录
- `./workspace:/root/.openclaw/workspace:rw` - 工作区
- `openclaw_home:/root:rw` - 持久化数据

**资源配置**：
- CPU 限制: 2 核
- 内存限制: 2GB
- 日志轮转: 10MB × 3 文件

**健康检查**：
- 端点: `/healthz`
- 间隔: 30s
- 超时: 10s

---

## 3. 管理工具 ✅

### manage.sh

提供完整的生命周期管理：

**首次安装**：
- ✅ `onboard` - 运行配置向导（首次必需）

**日常管理**：
- ✅ `start` - 启动 OpenClaw
- ✅ `stop` - 停止 OpenClaw
- ✅ `restart` - 重启 OpenClaw
- ✅ `logs` - 查看日志
- ✅ `status` - 查看状态
- ✅ `shell` - 进入容器
- ✅ `update` - 更新镜像
- ✅ `backup` - 备份工作区

**设备管理**：
- ✅ `devices list` - 列出设备
- ✅ `devices approve <id>` - 批准设备

**Dashboard**：
- ✅ `dashboard` - 获取 Dashboard Token

**使用示例**：
```bash
cd /Users/busiji/workbot/Molt
./manage.sh onboard   # 首次安装
./manage.sh start     # 启动服务
./manage.sh logs      # 查看日志
```

---

## 4. 文档 ✅

### 核心文档

1. **README.md** (4,873 字节)
   - 完整的项目文档
   - 目录结构说明
   - 日常管理命令
   - 故障排查指南
   - 备份与恢复

2. **QUICKSTART.md** (2,967 字节)
   - 快速启动指南
   - 前置要求
   - 首次安装步骤
   - 常用操作

3. **DEPLOYMENT.md** (5,074 字节)
   - 部署报告
   - 文件清单
   - 配置说明

4. **PORT.md** (1,311 字节)
   - 端口映射说明
   - 端口冲突解决
   - 防火墙配置

5. **.gitignore** (430 字节)
   - Git 忽略规则
   - 敏感文件保护

---

## 5. Workspace 内容

### 核心文件

| 文件 | 大小 | 说明 |
|------|------|------|
| AGENTS.md | 3,581 字节 | Agent 操作指令 |
| SOUL.md | 1,600 字节 | 人格定义 |
| TOOLS.md | 4,390 字节 | 工具定义 |
| IDENTITY.md | 906 字节 | 身份信息 |
| USER.md | 906 字节 | 用户信息 |
| HEARTBEAT.md | 1,345 字节 | 心跳任务 |
| MEMORY.md | 514 字节 | 记忆文件 |

### 子目录

| 目录 | 内容 |
|------|------|
| projects/ | 29 个项目文档（ClawRouter、Multi-brand 等） |
| memory/ | 知识库、日志、原始数据 |
| docs/ | 295 个文档文件 |
| skills/ | 技能定义（mcporter 等） |

---

## 6. 部署流程（基于官方文档）

### 步骤 1: 首次安装（Onboarding）

```bash
cd /Users/busiji/workbot/Molt
./manage.sh onboard
```

**Onboarding 会做什么**：
1. 拉取官方镜像 `ghcr.io/openclaw/openclaw:latest`
2. 运行配置向导
3. 选择 LLM Provider（Anthropic/OpenAI/等）
4. 输入 API Key
5. 生成配置文件 `config/openclaw.json`
6. 启动 Gateway

### 步骤 2: 验证启动

```bash
# 检查容器状态
./manage.sh status

# 健康检查
curl http://localhost:100/healthz | jq '.'

# 预期输出：
# {
#   "ok": true,
#   "version": "x.x.x",
#   ...
# }
```

### 步骤 3: 访问 Dashboard

```bash
./manage.sh dashboard
```

这将生成一个包含 Token 的 URL，在浏览器中打开并输入 Token 即可访问 Dashboard。

---

## 7. 目录结构

```
/Users/busiji/workbot/Molt/
├── .gitignore                # Git 忽略规则
├── config/                   # OpenClaw 配置目录（首次运行后生成）
│   ├── .gitkeep             # 占位文件
│   └── openclaw.json        # 主配置文件（onboarding 后生成）
├── docker-compose.yml        # Docker Compose 配置
├── manage.sh                 # 管理脚本（可执行）
├── README.md                 # 完整文档
├── QUICKSTART.md             # 快速启动指南
├── DEPLOYMENT.md             # 部署报告（本文件）
├── PORT.md                   # 端口映射说明
└── workspace/                # OpenClaw 工作区（100% 复刻）
    ├── AGENTS.md
    ├── SOUL.md
    ├── TOOLS.md
    ├── IDENTITY.md
    ├── USER.md
    ├── HEARTBEAT.md
    ├── MEMORY.md
    ├── projects/             # 项目文档
    ├── memory/               # 记忆存储
    ├── docs/                 # 文档库
    └── skills/               # 技能定义
```

---

## 8. 与官方文档的差异

### 遵循官方规范 ✅

1. **使用官方镜像**: `ghcr.io/openclaw/openclaw:latest`
2. **使用官方配置路径**:
   - 配置: `/root/.openclaw/`
   - 工作区: `/root/.openclaw/workspace/`
3. **使用官方 onboarding 流程**
4. **使用官方 health check**: `/healthz`
5. **使用官方 CLI 工具**: `openclaw-cli`

### 简化部署 ✅

1. **管理脚本**: 封装常用命令
2. **完整文档**: 本地化说明
3. **Workspace 预配置**: 100% 复刻已有工作区

---

## 9. 下一步操作

### 必需步骤

1. **运行 Onboarding**：
   ```bash
   cd /Users/busiji/workbot/Molt
   ./manage.sh onboard
   ```

2. **按提示完成配置**：
   - 选择 LLM Provider
   - 输入 API Key
   - 确认其他选项

3. **验证启动**：
   ```bash
   curl http://localhost:100/healthz
   ```

### 可选步骤

1. **访问 Dashboard**：`./manage.sh dashboard`
2. **自定义人格**：编辑 `workspace/SOUL.md`
3. **添加工具**：编辑 `workspace/TOOLS.md`
4. **配置通道**：WhatsApp/Telegram/Discord
5. **启用心跳**：修改 `workspace/HEARTBEAT.md`

---

## 10. 故障排查

### 容器无法启动

```bash
# 检查容器状态
./manage.sh status

# 查看错误日志
./manage.sh logs

# 检查配置文件
ls -la config/openclaw.json
```

### 工作区未加载

```bash
# 进入容器检查
./manage.sh shell
ls -la /root/.openclaw/workspace/
```

### 端口冲突

修改 `docker-compose.yml` 中的端口映射：
```yaml
ports:
  - "其他端口:18789"  # 例如 "8080:18789"
```

---

## 11. 备份与恢复

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

---

## 12. 相关文档

**本地文档**：
- README.md - 完整文档
- QUICKSTART.md - 快速启动
- PORT.md - 端口说明

**OpenClaw 官方文档**：
- [OpenClaw 官方文档](https://docs.openclaw.ai/)
- [Agent Workspace](https://docs.openclaw.ai/concepts/agent-workspace)
- [Memory](https://docs.openclaw.ai/concepts/memory)
- [Docker 部署](https://docs.openclaw.ai/install/docker)

---

**部署完成！** 🎉

运行 `./manage.sh onboard` 开始首次安装。

**镜像**: `ghcr.io/openclaw/openclaw:latest`
**端口**: `100:18789`
**工作区**: 100% 复刻完成
