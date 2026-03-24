# sub2api 部署文档 (node-22)

**部署日期**: 2026-03-09
**服务器**: node-22 (43.167.177.86)
**系统**: OpenCloudOS 9.4
**访问方式**: Tailscale 内网 (HTTPS)
**部署者**: Molt 国王

---

## 📋 系统架构

```
┌─────────────┐
│   客户端     │
│  (浏览器)    │
└──────┬──────┘
       │ HTTPS (Tailscale 自动证书)
       ↓
┌─────────────────────────────────────────┐
│    Tailscale Serve (HTTPS 代理)          │
│  https://node22.tail5e888.ts.net:28080  │
└──────┬──────────────────────────────────┘
       │ HTTP (本地回环)
       ↓
┌─────────────────────────────────────────┐
│       sub2api 网关 (端口 28080)          │
│       http://localhost:28080            │
└──────┬──────────────────────────────────┘
       │
       ├─→ PostgreSQL (5432)
       └─→ Redis (6379)
```

---

## 🔐 访问信息

### 管理员凭据

| 项目 | 值 |
|------|-----|
| **管理员邮箱** | `admin@sub2api.local` |
| **管理员密码** | `ed09688bf40152b3ea565c2bf3c22d7b` |
| **访问地址** | `https://node22.tail5e888.ts.net:28080/` |

> ⚠️ **重要**: 首次登录后请立即修改密码！

### 安全凭据

| 项目 | 值 |
|------|-----|
| **JWT_SECRET** | `50c99d82afffdf6785fb54f80ce40176b45990d67fc33bf38184c85ba88d556c` |
| **TOTP_ENCRYPTION_KEY** | `7b3a8727cceda39821ebd4fc877a496d7448bf413ea9fa33689bca3db631185e` |
| **POSTGRES_PASSWORD** | `053100d95266557820acc4ba713cc420398b59925c52760514af8f82007d5b4b` |

---

## 🏗️ 部署配置

### 部署方式
- **方式**: Docker Compose (Local Directory)
- **镜像**: `weishaw/sub2api:latest`
- **端口**: 28080 (避免与现有服务冲突)
- **数据目录**: `/opt/sub2api-deploy/`
- **HTTPS**: Tailscale Serve 自动证书

### 容器列表

| 容器名 | 镜像 | 端口 | 状态 |
|--------|------|------|------|
| sub2api | weishaw/sub2api:latest | 28080→8080 | ✅ 健康运行 |
| sub2api-postgres | postgres:18-alpine | 5432 | ✅ 健康运行 |
| sub2api-redis | redis:8-alpine | 6379 | ✅ 健康运行 |

### 数据卷

| 目录 | 用途 |
|------|------|
| `/opt/sub2api-deploy/data/` | 应用数据 |
| `/opt/sub2api-deploy/postgres_data/` | PostgreSQL 数据 |
| `/opt/sub2api-deploy/redis_data/` | Redis 数据 |

### Tailscale Serve 配置

```bash
# 当前配置
https://node22.tail5e888.ts.net:28080 (tailnet only)
|-- / proxy http://localhost:28080
```

---

## 📝 部署步骤

### 1. 检查环境

```bash
# 检查 Docker 版本
docker --version
docker compose version

# 检查端口占用
netstat -tlnp | grep :28080
```

### 2. 部署准备

```bash
# 创建部署目录
cd /opt
mkdir -p sub2api-deploy && cd sub2api-deploy

# 下载并运行部署准备脚本
curl -sSL https://raw.githubusercontent.com/Wei-Shaw/sub2api/main/deploy/docker-deploy.sh | bash
```

### 3. 修改端口配置

```bash
# 修改端口为 28080 (避免与 8080 和 18080 冲突)
echo 'SERVER_PORT=28080' >> .env

# 清理重复配置
sed -i '/^SERVER_PORT=8080$/d' .env
```

### 4. 启动服务

```bash
# 启动所有服务
docker compose -f docker-compose.local.yml up -d

# 查看服务状态
docker compose -f docker-compose.local.yml ps

# 查看日志并获取管理员密码
docker compose -f docker-compose.local.yml logs sub2api | grep -A 5 'admin\|password'
```

### 5. 配置 Tailscale Serve (HTTPS)

```bash
# 配置 HTTPS 代理
tailscale serve --bg --https 28080 localhost:28080

# 查看配置
tailscale serve status
```

---

## 🔧 管理命令

### Docker 服务管理

```bash
# 查看服务状态
cd /opt/sub2api-deploy
docker compose -f docker-compose.local.yml ps

# 查看所有日志
docker compose -f docker-compose.local.yml logs -f

# 查看 sub2api 日志
docker compose -f docker-compose.local.yml logs -f sub2api

# 重启服务
docker compose -f docker-compose.local.yml restart

# 停止服务
docker compose -f docker-compose.local.yml down

# 启动服务
docker compose -f docker-compose.local.yml up -d
```

### Tailscale Serve 管理

```bash
# 查看配置
tailscale serve status

# 关闭 HTTPS 代理
tailscale serve --https=28080 off

# 重新启用 HTTPS 代理
tailscale serve --bg --https 28080 localhost:28080

# 重置所有配置
tailscale serve reset
```

### 升级

```bash
# 拉取最新镜像
docker compose -f docker-compose.local.yml pull

# 重新创建容器
docker compose -f docker-compose.local.yml up -d
```

### 备份与迁移

```bash
# 停止服务
docker compose -f docker-compose.local.yml down

# 打包数据目录
cd /opt
tar czf sub2api-backup-$(date +%Y%m%d).tar.gz sub2api-deploy/

# 恢复到新服务器
tar xzf sub2api-backup-*.tar.gz
cd sub2api-deploy/
docker compose -f docker-compose.local.yml up -d

# 配置 Tailscale Serve
tailscale serve --bg --https 28080 localhost:28080
```

---

## 🌐 功能说明

### 支持的上游服务

- **Claude** (Anthropic)
- **OpenAI**
- **Gemini** (Google)
- **Antigravity**

### 主要功能

- ✅ **多账户管理** - 支持多个上游账户（OAuth, API Key）
- ✅ **API Key 分发** - 为用户生成和管理 API Key
- ✅ **精准计费** - Token 级别使用追踪和成本计算
- ✅ **智能调度** - 智能账户选择，支持粘性会话
- ✅ **并发控制** - 每用户和每账户的并发限制
- ✅ **速率限制** - 可配置的请求和 Token 速率限制
- ✅ **管理面板** - Web 界面进行监控和管理

### 专用端点

| 端点 | 模型 |
|------|------|
| `/antigravity/v1/messages` | Claude 模型 |
| `/antigravity/v1beta/` | Gemini 模型 |

### Claude Code 配置示例

```bash
export ANTHROPIC_BASE_URL="https://node22.tail5e888.ts.net:28080/antigravity"
export ANTHROPIC_AUTH_TOKEN="sk-xxx"
```

---

## 🚨 故障排除

### 1. 端口被占用

**错误**: `bind: address already in use`

**解决方案**:
```bash
# 检查端口占用
netstat -tlnp | grep :28080

# 修改 .env 文件中的 SERVER_PORT
sed -i 's/SERVER_PORT=28080/SERVER_PORT=新端口/g' .env

# 重启服务
docker compose -f docker-compose.local.yml up -d

# 重新配置 Tailscale Serve
tailscale serve --https=28080 off
tailscale serve --bg --https 新端口 localhost:新端口
```

### 2. 容器无法启动

**检查日志**:
```bash
# 查看容器日志
docker compose -f docker-compose.local.yml logs sub2api

# 查看容器状态
docker compose -f docker-compose.local.yml ps
```

### 3. HTTPS 访问失败

**检查 Tailscale Serve**:
```bash
# 查看配置
tailscale serve status

# 重新配置
tailscale serve --https=28080 off
tailscale serve --bg --https 28080 localhost:28080
```

### 4. 数据库连接失败

**检查 PostgreSQL 容器**:
```bash
# 检查 PostgreSQL 状态
docker compose -f docker-compose.local.yml ps postgres

# 查看 PostgreSQL 日志
docker compose -f docker-compose.local.yml logs postgres
```

### 5. 忘记管理员密码

**重置密码**:
```bash
# 进入容器
docker exec -it sub2api sh

# 使用内置工具重置密码（如果有）
# 或者直接重置数据库
```

---

## 📚 相关资源

### 官方文档
- **项目地址**: https://github.com/Wei-Shaw/sub2api
- **在线演示**: https://demo.sub2api.org/
- **文档**: 项目 README.md

### 技术栈
- **后端**: Go 1.25.7, Gin, Ent
- **前端**: Vue 3.4+, Vite 5+, TailwindCSS
- **数据库**: PostgreSQL 15+
- **缓存/队列**: Redis 7+

---

## 📊 资源使用

### 端口分配

| 服务 | 端口 | 说明 |
|------|------|------|
| sub2api | 28080 | Web UI & API Gateway |
| PostgreSQL | 5432 | 数据库（容器内部） |
| Redis | 6379 | 缓存（容器内部） |

### Tailscale Serve 映射

| HTTPS 端口 | 后端地址 | 说明 |
|-----------|---------|------|
| 18789 | http://127.0.0.1:18789 | OpenClaw |
| 25432 | http://127.0.0.1:25432 | x-ui 面板 |
| **28080** | **http://localhost:28080** | **sub2api** |

### 系统要求

- **操作系统**: Linux (Docker 支持)
- **内存**: 建议 2GB+
- **磁盘**: 建议 10GB+ (用于数据存储)
- **网络**: Tailscale 网络连接

---

## 🔐 安全建议

1. **修改默认密码**: 首次登录后立即修改管理员密码
2. **使用 HTTPS**: 已通过 Tailscale Serve 自动配置 HTTPS
3. **定期备份**: 定期备份 `/opt/sub2api-deploy/` 目录
4. **监控日志**: 定期检查日志，发现异常及时处理
5. **更新凭据**: 定期更换 JWT_SECRET 和 TOTP_ENCRYPTION_KEY

---

## 📝 注意事项

### 端口冲突说明

- **8080**: 被 Python HTTP 服务器占用
- **18080**: 被 GOST 隧道占用
- **28080**: ✅ sub2api 使用（当前）

### 数据持久化

使用本地目录方式（`docker-compose.local.yml`）部署，数据存储在：
- `/opt/sub2api-deploy/data/`
- `/opt/sub2api-deploy/postgres_data/`
- `/opt/sub2api-deploy/redis_data/`

便于备份和迁移。

### Tailscale 访问

- **域名**: `node22.tail5e888.ts.net` (注意是 `node22`，不是 `node-22`)
- **证书**: Tailscale 自动管理，无需手动配置
- **范围**: 仅限 Tailscale 网络内部访问 (tailnet only)

---

## 🔄 更新历史

- **2026-03-09 00:24**: 初始部署完成
  - 使用 Docker Compose 方式部署
  - 端口配置为 28080
  - 生成管理员账户和密码
  - 配置 Tailscale Serve HTTPS 代理
  - 创建部署文档

---

**文档版本**: 1.0
**最后更新**: 2026-03-09
**维护者**: Molt (战术蟹王)
