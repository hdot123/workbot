# Node-22 服务器项目部署文档

> 文档编号：NODE22-001
> 版本：V1.0
> 创建日期：2026-03-20
> 最后更新：2026-03-20
> 维护人：系统管理员

---

## 1. 服务器概述

### 1.1 基本信息
- **服务器名称**: node-22
- **内网 IP**: 10.7.0.8
- **Tailscale IP**: 100.100.1.22
- **公网 IP**: 43.167.177.86
- **用途**: AI API 代理服务
- **操作系统**: Ubuntu 22.04 LTS

### 1.2 服务历史
- **2026-03-08**: 原始部署 Sub2API（企业级 API 网关）
- **2026-03-20 23:00**: 尝试迁移至 AIClient-2-API（端口 28081）
- **2026-03-20 23:30**: 恢复 Sub2API 服务（端口 28080）

### 1.3 当前运行服务
- **Sub2API** (端口 28080): ✅ 运行中
- **AIClient-2-API** (端口 28081): ✅ 运行中

---

## 2. Sub2API 部署记录（当前运行）

### 2.1 部署架构
```
┌─────────────┐       ┌─────────────┐       ┌─────────────┐
│  sub2api    │──────▶│  PostgreSQL  │       │    Redis    │
│  :28080     │       │  :5432      │       │   :6379      │
└─────────────┘       └─────────────┘       └─────────────┘
```

### 2.2 容器列表

| 容器名称 | 镜像 | 端口映射 | 状态 | 用途 |
|---------|------|---------|------|------|
| sub2api | weishaw/sub2api:latest | 28080:8080 | 运行中 | 主服务 |
| sub2api-postgres | postgres:18-alpine | 5432 | 运行中 | 数据库 |
| sub2api-redis | redis:8-alpine | 6379 | 运行中 | 缓存 |

### 2.3 配置详情

#### 2.3.1 环境变量配置

```bash
# 数据库配置
DATABASE_HOST=postgres
DATABASE_PORT=5432
DATABASE_USER=sub2api
DATABASE_PASSWORD=053100d95266557820acc4ba713cc420398b59925c52760514af8f82007d5b4b
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_DB=0
DATABASE_DBNAME=sub2api
DATABASE_SSLMODE=disable
DATABASE_MAX_OPEN_CONNS=256
DATABASE_MAX_IDLE_CONNS=128
DATABASE_CONN_MAX_LIFETIME_MINUTES=30
DATABASE_CONN_MAX_IDLE_TIME_MINUTES=5

# Redis 配置
REDIS_ENABLE_TLS=false
REDIS_MIN_IDLE_CONNS=256

# 管理员账号
ADMIN_EMAIL=admin@sub2api.local
ADMIN_PASSWORD=b748c3a336e0cbf7093938cc81068047

# JWT 和加密
JWT_SECRET=984643d489105dfdb09657f3182d00113af54a22ddd91d79c026823b71705033
TOTP_ENCRYPTION_KEY=4fc10610ec0a17faae5be0c8580e028a91192b4a40250f29a8fbbaaca3882a50

# 服务器配置
SERVER_PORT=28081
SERVER_MODE=release
SECURITY_URL_ALLOWLIST_ENABLED=false
SECURITY_URL_ALLOWLIST_ALLOW_PRIVATE_HOSTS=true
SECURITY_URL_ALLOWLIST_ALLOW_INSECURE_HTTP=true

# 代理配置（通过 Cloudflare WARP）
HTTP_PROXY=socks5h://127.0.0.1:40000
HTTPS_PROXY=socks5h://127.0.0.1:40000
ALL_PROXY=socks5h://127.0.0.1:40000
NO_PROXY=localhost,127.0.0.1,::1
```

#### 2.3.2 数据卷挂载

```bash
/opt/sub2api-deploy/data:/app/data
```

#### 2.3.3 网络配置

```bash
网络名称: sub2api-deploy_sub2api-network
网络模式: bridge
```

#### 2.3.4 代理配置

- **代理类型**: SOCKS5
- **代理地址**: 127.0.0.1:40000 (Cloudflare WARP)
- **绕过代理**: localhost, 127.0.0.1, ::1

### 2.4 Docker Compose 配置文件

**文件位置**: `/opt/muxing/docker-compose.yml`

<details>
<summary>点击查看完整配置</summary>

```yaml
services:
  muxing:
    image: weishaw/sub2api:latest
    container_name: sub2api_core
    restart: unless-stopped
    environment:
      - AUTO_SETUP=true
      - TZ=Asia/Shanghai
      - SERVER_MODE=release
      - RUN_MODE=standard
      - SERVER_HOST=0.0.0.0
      - SERVER_PORT=28081
      - DATABASE_HOST=${DATABASE_HOST}
      - DATABASE_PORT=${DATABASE_PORT}
      - DATABASE_USER=${DATABASE_USER}
      - DATABASE_PASSWORD=${DATABASE_PASSWORD}
      - DATABASE_DBNAME=${DATABASE_DBNAME}
      - DATABASE_SSLMODE=${DATABASE_SSLMODE}
      - DATABASE_MAX_OPEN_CONNS=5
      - DATABASE_MAX_IDLE_CONNS=2
      - DATABASE_CONN_MAX_LIFETIME_MINUTES=5
      - DATABASE_CONN_MAX_IDLE_TIME_MINUTES=5
      - REDIS_HOST=${REDIS_HOST}
      - REDIS_PORT=${REDIS_PORT}
      - REDIS_PASSWORD=${REDIS_PASSWORD}
      - REDIS_DB=${REDIS_DB}
      - REDIS_MIN_IDLE_CONNS=5
      - REDIS_ENABLE_TLS=${REDIS_ENABLE_TLS}
      - ADMIN_EMAIL=${ADMIN_EMAIL}
      - ADMIN_PASSWORD=${ADMIN_PASSWORD}
      - JWT_SECRET=${JWT_SECRET}
      - TOTP_ENCRYPTION_KEY=${TOTP_ENCRYPTION_KEY}
      - SECURITY_URL_ALLOWLIST_ENABLED=false
      - SECURITY_URL_ALLOWLIST_ALLOW_PRIVATE_HOSTS=true
      - SECURITY_URL_ALLOWLIST_ALLOW_INSECURE_HTTP=true
      - HTTP_PROXY=socks5h://127.0.0.1:40000
      - HTTPS_PROXY=socks5h://127.0.0.1:40000
      - ALL_PROXY=socks5h://127.0.0.1:40000
      - NO_PROXY=localhost,127.0.0.1,::1
    healthcheck:
      test: ["CMD", "curl", "-f", "http://127.0.0.1:28081/health"]
      interval: 30s
      timeout: 10s
      retries: 5
      start_period: 30s
```

</details>

### 2.5 访问信息

#### 通过 Tailscale 域名（推荐，需要带端口）
由于多个服务共用域名，必须通过端口号区分：
- **Web UI**: https://node-22.tail5e888.ts.net:28080
- **API 端点**: https://node-22.tail5e888.ts.net:28080/v1
- **健康检查**: https://node-22.tail5e888.ts.net:28080/health

#### 通过 Tailscale IP（需要带端口）
- **Web UI**: http://100.100.1.22:28080
- **API 端点**: http://100.100.1.22:28080/v1
- **健康检查**: http://100.100.1.22:28080/health

#### 通过内网 IP（需要带端口）
- **Web UI**: http://10.7.0.8:28080
- **API 端点**: http://10.7.0.8:28080/v1
- **健康检查**: http://10.7.0.8:28080/health

- **状态**: ✅ 已恢复运行（2026-03-20 23:30）

### 2.6 管理员账号

- **邮箱**: huhuun17@gmail.com
- **密码**: 需要重置或从数据库中查询

---

## 3. AIClient-2-API 部署信息

### 3.1 部署详情

**部署时间**: 2026-03-20 23:16
**状态**: ✅ 运行中
**镜像**: justlikemaki/aiclient-2-api:latest
**容器名称**: aiclient2api
**端口映射**:
- 28081:3000 (Web UI 和 API)
- 8085-8087:8085-8087 (OAuth 回调)
- 1455:1455 (Codex OAuth)
- 19876-19880:19876-19880 (Kiro OAuth)

**配置目录**: `/opt/aiclient2api/configs`
**状态**: 运行中（健康） ✅
**代理配置**: SOCKS5 (127.0.0.1:40000)

### 3.2 访问信息

#### 通过 Tailscale 域名（推荐，需要带端口）
由于多个服务共用域名，必须通过端口号区分：
- **Web UI**: https://node-22.tail5e888.ts.net:28081
- **API 端点**: https://node-22.tail5e888.ts.net:28081/v1
- **健康检查**: https://node-22.tail5e888.ts.net:28081/health

- **默认密码**: admin123

#### 通过内网 IP
- **Web UI**: http://10.7.0.8:28081
- **API 端点**: http://10.7.0.8:28081/v1
- **健康检查**: http://10.7.0.8:28081/health

#### 通过公网 IP（不推荐）
- **Web UI**: http://43.167.177.86:28081
- **API 端点**: http://43.167.177.86:28081/v1
- **健康检查**: http://43.167.177.86:28081/health

- **默认密码**: admin123

### 4.3 配置文件

#### 4.3.1 主配置文件 (config.json)
```json
{
  "REQUIRED_API_KEY": "sk-node22-aiclient2api-2026",
  "SERVER_PORT": 3000,
  "HOST": "0.0.0.0",
  "MODEL_PROVIDER": "gemini-cli-oauth",
  "SYSTEM_PROMPT_FILE_PATH": "configs/input_system_prompt.txt",
  "SYSTEM_PROMPT_MODE": "overwrite",
  "PROMPT_LOG_MODE": "none",
  "REQUEST_MAX_RETRIES": 3,
  "REQUEST_BASE_DELAY": 1000,
  "PROVIDER_POOLS_FILE_PATH": "configs/provider_pools.json",
  "MAX_ERROR_COUNT": 3,
  "PROXY_URL": "socks5h://127.0.0.1:40000",
  "PROXY_ENABLED_PROVIDERS": [
    "gemini-cli-oauth",
    "gemini-antigravity"
  ],
  "LOG_ENABLED": true,
  "LOG_OUTPUT_MODE": "all",
  "LOG_LEVEL": "info",
  "LOG_DIR": "logs",
  "LOG_INCLUDE_REQUEST_ID": true,
  "LOG_INCLUDE_TIMESTAMP": true,
  "LOG_MAX_FILE_SIZE": 10485760,
  "LOG_MAX_FILES": 10
}
```

#### 4.3.2 密码文件 (pwd)
```
admin123
```

### 4.2 功能对比

| 功能 | Sub2API | AIClient-2-API |
|------|---------|----------------|
| 数据库需求 | ✅ PostgreSQL | ❌ 无需 |
| 缓存需求 | ✅ Redis | ❌ 无需 |
| 用户管理 | ✅ 多租户 | ❌ 单用户 |
| 计费功能 | ✅ 精确计费 | ❌ 无 |
| 账户池管理 | ✅ 智能调度 | ✅ 账户池轮询 |
| Web UI | ✅ 完整后台 | ✅ 简单界面 |
| 资源占用 | ~500MB+ | ~200MB |

---

## 5. 备份与恢复

### 5.1 配置备份
- **备份位置**: 本文档
- **备份时间**: 2026-03-20
- **备份内容**: 环境变量、端口映射、数据卷

### 5.2 恢复步骤（如需回滚）
```bash
# 1. 停止 AIClient-2-API
docker stop aiclient2api

# 2. 重新启动 sub2api
cd /opt/muxing
docker-compose up -d

# 3. 恢复数据（如有需要）
# 数据已持久化在 /opt/sub2api-deploy/data
```

---

## 6. 运维记录

### 6.1 日常维护
- 定期检查容器健康状态
- 监控日志输出
- 检查磁盘空间使用

### 6.2 故障排查
- 查看日志: `docker logs aiclient2api`
- 进入容器: `docker exec -it aiclient2api sh`
- 健康检查: `curl http://100.100.1.22:28081/health`

---

## 7. 相关链接

- [Sub2API GitHub](https://github.com/Wei-Shaw/sub2api)
- [AIClient-2-API GitHub](https://github.com/justlovemaki/aiclient-2-api)
- [Docker Hub - AIClient-2-API](https://hub.docker.com/r/justlikemaki/aiclient-2-api)

---

**文档状态**: ✅ 已完成
**审批人**: 系统管理员
**下次更新**: 按需更新

### 4.4 部署命令

```bash
# 启动容器（使用 28081 端口）
docker run -d \
  --name aiclient2api \
  --restart unless-stopped \
  -p 28081:3000 \
  -p 8085-8087:8085-8087 \
  -p 1455:1455 \
  -p 19876-19880:19876-19880 \
  -v /opt/aiclient2api/configs:/app/configs \
  -e HTTP_PROXY=socks5h://127.0.0.1:40000 \
  -e HTTPS_PROXY=socks5h://127.0.0.1:40000 \
  -e ALL_PROXY=socks5h://127.0.0.1:40000 \
  -e NO_PROXY=localhost,127.0.0.1,::1 \
  justlikemaki/aiclient-2-api:latest

# 查看日志
docker logs -f aiclient2api

# 停止容器
docker stop aiclient2api

# 重启容器
docker restart aiclient2api

# 进入容器
docker exec -it aiclient2api sh
```

### 4.5 容器管理

```bash
# 查看容器状态
docker ps | grep aiclient2api

# 查看健康状态（通过 Tailscale IP）
curl http://100.100.1.22:28081/health

# 查看健康状态（通过内网 IP）
curl http://10.7.0.8:28081/health

# 查看 Web UI（通过 Tailscale）
open http://100.100.1..22:28081
```

### 4.6 迁移记录

#### 从 Sub2API 迁移到 AIClient-2-API

**迁移原因**:
1. **资源占用**: AIClient-2-API 无需数据库，内存占用 ~200MB vs Sub2API ~500MB+
2. **部署复杂度**: 单容器 vs 3 容器
3. **使用场景**: 个人/小团队使用，满足当前需求

**迁移时间线**:
- 2026-03-20 23:00: 开始迁移操作
- 2026-03-20 23:03: 停止 sub2api 容器（第一次尝试）
- 2026-03-20 23:10: 停止所有 sub2api 相关容器（sub2api, sub2api_core）
- 2026-03-20 23:16: 部署 AIClient-2-API 容器到 28081 端口
- 2026-03-20 23:16: 验证服务正常 ✅

**端口复用说明**:
- 原 sub2api_core 内部端口: 28081
- 现 AIClient-2-API 外部端口: 28081
- **端口复用成功**: 统一使用 28081 访问新服务

**保留的配置**:
- 代理设置: SOCKS5 (127.0.0.1:40000)
- API Key: sk-node22-aiclient2api-2026
- Web UI 密码: admin123

**不再需要**:
- PostgreSQL 数据库
- Redis 缓存
- 多租户管理
- 计费系统

---

## 5. 功能对比

### 5.1 架构对比

| 维度 | Sub2API | AIClient-2-API |
|------|---------|----------------|
| 数据库 | PostgreSQL | 无需 |
| 缓存 | Redis | 无需 |
| 容器数量 | 3 个 | 1 个 |
| 内存占用 | ~500MB+ | ~200MB |
| 用户管理 | 多租户 | 单用户 |
| 计费功能 | 精确计费 | 无 |
| Web UI | 完整后台 | 简单界面 |

### 5.2 功能保留情况

| 功能 | 状态 | 说明 |
|------|------|------|
| API 代理 | ✅ 保留 | 核心功能 |
| OAuth 授权 | ✅ 保留 | Gemini/Antigravity/Qwen/Kiro |
| 账户池管理 | ✅ 保留 | 轮询、故障转移 |
| 代理支持 | ✅ 保留 | SOCKS5 代理 |
| Web UI | ✅ 保留 | 简化版管理界面 |
| 多用户管理 | ❌ 移除 | 单用户模式 |
| 计费系统 | ❌ 移除 | 无需计费 |
| 数据持久化 | ✅ 简化 | 文件存储（JSON） |

---

## 6. 后续优化

### 6.1 配置优化
- [ ] 添加 OAuth 凭证文件
- [ ] 配置提供商账户池
- [ ] 添加系统提示词
- [ ] 配置模型映射

### 6.2 监控优化
- [ ] 配置日志收集
- [ ] 添加性能监控
- [ ] 配置告警规则

---

**文档状态**: ✅ 已完成
**最后更新**: 2026-03-20 23:05
**审批人**: 系统管理员
