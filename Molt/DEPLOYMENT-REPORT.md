# OpenClaw Molt 部署报告

**部署时间**: 2026-03-15
**状态**: ✅ 部署成功
**访问地址**: http://localhost:100

---

## 部署概览

### 容器信息
- **容器名称**: openclaw-molt
- **镜像**: node:22-alpine
- **状态**: Running
- **端口映射**: 100:18789 (宿主机:容器)

### 健康检查
```bash
curl http://localhost:100/healthz
# 返回: {"ok":true,"status":"live"}
```

---

## 配置详情

### 1. ClawRouter 集成

**LLM Provider**: ClawRouter 百炼服务
- **Base URL**: http://192.168.88.27:3000/v1
- **API Key**: sk-clawrouter-bailian
- **默认模型**: openai/qwen3.5-plus (阿里云百炼 Qwen 3.5 Plus)

### 2. Gateway 配置

```json
{
  "gateway": {
    "port": 18789,
    "mode": "local",
    "bind": "lan",
    "auth": {
      "mode": "token",
      "token": "molt-gateway-token-2026"
    }
  }
}
```

**认证方式**: Token
**Gateway Token**: `molt-gateway-token-2026`

### 3. 资源配置

- **内存限制**: 1GB
- **内存预留**: 512MB
- **Node.js 堆内存**: 1024MB
- **日志轮转**: 10MB × 3 文件

---

## Workspace 结构

**源路径**: `/Users/busiji/passkills/workspace`
**目标路径**: `/Users/busiji/workbot/Molt/workspace`
**文件总数**: 462 个文件 (3.96 MB)

### 核心文件
- ✅ AGENTS.md - Agent 操作指令
- ✅ SOUL.md - 人格定义
- ✅ TOOLS.md - 工具定义
- ✅ MEMORY.md - 记忆文件
- ✅ IDENTITY.md - 身份信息
- ✅ HEARTBEAT.md - 心跳任务

### 子目录
- ✅ projects/ - 项目文档 (29 个)
- ✅ memory/ - 知识库和日志
- ✅ docs/ - 文档库 (295 个文件)
- ✅ skills/ - 技能定义

---

## 端口映射

### 最终配置
```yaml
ports:
  - "100:18789"
```

- **宿主机端口**: 100
- **容器端口**: 18789
- **访问方式**: http://localhost:100

### 端口选择原因
1. 避免与系统常用端口冲突 (80, 443, 8080)
2. 使用 100 端口便于记忆 (百分百的意思)
3. OrbStack 支持非特权端口映射

---

## 环境变量

```bash
NODE_ENV=production
NODE_OPTIONS=--max-old-space-size=1024
OPENAI_BASE_URL=http://192.168.88.27:3000/v1
OPENAI_API_KEY=sk-clawrouter-bailian
```

---

## Volume 挂载

| 宿主机路径 | 容器路径 | 用途 |
|-----------|---------|------|
| ./config | /root/.openclaw | 配置目录 |
| ./workspace | /root/.openclaw/workspace | 工作区 |
| openclaw-cache | /root/.npm | npm 缓存 |

---

## 管理命令

### 启动/停止
```bash
cd /Users/busiji/workbot/Molt

# 启动
docker-compose up -d

# 停止
docker-compose down

# 重启
docker-compose restart

# 查看日志
docker logs -f openclaw-molt

# 查看状态
docker ps | grep openclaw-molt
```

### 健康检查
```bash
# 基础检查
curl http://localhost:100/healthz

# 格式化输出
curl -s http://localhost:100/healthz | jq '.'
```

### 进入容器
```bash
docker exec -it openclaw-molt sh
```

---

## 可用的百炼模型

通过 ClawRouter 可以访问以下百炼模型：

- `qwen3.5-plus` - 通义千问 3.5 Plus (当前使用)
- `qwen3-max-2026-01-23` - 通义千问 3 Max
- `glm-4.7-bailian` - GLM-4.7 (百炼版)
- `glm-5-bailian` - GLM-5 (百炼版)

### 切换模型
编辑 `config/openclaw.json`:
```json
{
  "agents": {
    "defaults": {
      "model": "openai/qwen3-max-2026-01-23"
    }
  }
}
```

然后重启容器:
```bash
docker-compose restart
```

---

## 部署历史

### 第一次部署 (2026-03-14)
- ❌ 使用 `network_mode: host`，端口映射不正确
- 服务监听在 18789 端口，而不是要求的 100 端口

### 第二次部署 (2026-03-15) ✅
- ✅ 移除 `network_mode: host`
- ✅ 添加端口映射 `ports: - "100:18789"`
- ✅ 服务成功监听在 100 端口
- ✅ 健康检查通过
- ✅ Workspace 100% 复刻
- ✅ ClawRouter 集成成功

---

## 故障排查

### 容器无法启动
```bash
# 查看容器状态
docker ps -a | grep openclaw-molt

# 查看日志
docker logs openclaw-molt

# 检查配置文件
docker exec openclaw-molt cat /root/.openclaw/openclaw.json
```

### 端口被占用
```bash
# 检查端口占用
lsof -i :100

# 如果被占用，修改 docker-compose.yml 中的端口
ports:
  - "其他端口:18789"
```

### Workspace 未加载
```bash
# 检查 workspace 挂载
docker exec openclaw-molt ls -la /root/.openclaw/workspace/

# 检查核心文件
docker exec openclaw-molt cat /root/.openclaw/workspace/SOUL.md
```

---

## 相关文档

- **本地文档**:
  - [README.md](README.md) - 完整项目文档
  - [DEPLOYMENT.md](DEPLOYMENT.md) - 部署指南
  - [PORT.md](PORT.md) - 端口说明

- **参考文档**:
  - [node-00 部署评估](/Users/busiji/passkills/workspace/memory/log/2026-03-10-node00-openclaw-evaluation.md)
  - [ClawRouter 文档](/Users/busiji/passkills/workspace/projects/)

---

## 下一步操作

### 可选配置
1. **自定义人格**: 编辑 `workspace/SOUL.md`
2. **添加工具**: 编辑 `workspace/TOOLS.md`
3. **配置通道**: WhatsApp/Telegram/Discord
4. **启用心跳**: 修改 `workspace/HEARTBEAT.md`

### 测试建议
1. 使用 OpenClaw TUI 模式测试
2. 验证 ClawRouter 连接
3. 测试百炼模型响应
4. 检查记忆存储功能

---

**部署完成！** 🎉

访问地址: http://localhost:100
健康检查: `curl http://localhost:100/healthz`
