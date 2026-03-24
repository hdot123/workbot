# MiroFish 部署文档

**部署日期**: 2026-03-10
**服务器**: node-111 (PVE 虚拟机)
**系统**: Ubuntu 24.04.4 LTS
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
│  https://node111.tail5e888.ts.net:3000  │
└──────┬──────────────────────────────────┘
       │ HTTP (本地回环)
       ↓
┌─────────────────────────────────────────┐
│       MiroFish 容器 (端口 3000/5001)      │
│       http://localhost:3000 (前端)       │
│       http://localhost:5001 (后端)       │
└─────────────────────────────────────────┘
```

---

## 🔐 访问信息

### 服务器信息

| 项目 | 值 |
|------|-----|
| **主机名** | `mirofish` |
| **IP 地址** | `192.168.88.31` |
| **系统** | Ubuntu 24.04.4 LTS |
| **内核** | `6.17.13-1-pve` |
| **内存** | 4GB |
| **CPU** | 4 核 |
| **磁盘** | 22GB (nvme-dot) |

### 服务访问

| 服务 | 内网地址 | Tailscale 地址 | 说明 |
|------|---------|---------------|------|
| **前端** | `http://192.168.88.31:3000` | `https://node111.tail5e888.ts.net:3000` | Vue 3 前端 |
| **后端 API** | `http://192.168.88.31:5001` | `https://node111.tail5e888.ts.net:5001` | Flask API |

### SSH 连接

```bash
# 局域网
ssh root@192.168.88.31

# Tailscale
ssh root@100.100.1.31
```

---

## 🏗️ 部署详情

### PVE 虚拟机配置

- **VM ID**: 111
- **名称**: `mirofish`
- **存储**: nvme-dot (主磁盘) + local-lvm (Cloud-Init)
- **网络**: vmbr0 (桥接模式)
- **Cloud-Init**: 已配置 SSH 公钥

### Docker 服务

```bash
# 容器名称
mirofish

# 镜像
ghcr.nju.edu.cn/666ghj/mirofish:latest

# 端口映射
3000:3000  # 前端
5001:5001  # 后端 API

# 数据卷
/opt/MiroFish/backend/uploads:/app/backend/uploads
```

---

## 🔧 管理命令

### 服务管理

```bash
# 查看服务状态
cd /opt/MiroFish
docker compose ps

# 查看日志
docker compose logs -f

# 重启服务
docker compose restart

# 停止服务
docker compose down

# 启动服务
docker compose up -d
```

### 更新服务

```bash
# 拉取最新镜像
cd /opt/MiroFish
docker compose pull

# 重新创建容器
docker compose up -d
```

### 备份与恢复

```bash
# 备份数据
cd /opt
tar czf mirofish-backup-$(date +%Y%m%d).tar.gz MiroFish/backend/uploads/

# 恢复数据
tar xzf mirofish-backup-*.tar.gz
```

---

## ⚙️ 配置文件

### .env 文件位置

```bash
/opt/MiroFish/.env
```

### 环境变量

```bash
# LLM API配置（使用阿里百炼 Coding Plan）
LLM_API_KEY=sk-sp-fdf3de2a9f4a4bc4a00cd98052343a8d
LLM_BASE_URL=https://coding.dashscope.aliyuncs.com/apps/anthropic
LLM_MODEL_NAME=qwen3.5-plus

# Zep Cloud 配置（记忆图谱）
ZEP_API_KEY=z_1dWlkIjoiZmFkZTllZmMtY2NlOS00MzMzLWI4ZTgtYmRhMGRjYjk0OGU0In0.1taekFaJKzFv7fqjIegF-drB5mi53Y-dYnf0Q5oJrtnC-7MdCamzQ2vbqESmpZdCIUksHOWrVAQbisYtFR6GlQ
```

**配置状态**: ⚠️ 需要更新为 Coding Plan 端点（2026-03-10 06:30）

> **重要**: 需要使用 **阿里百炼 Coding Plan** 专用端点：
> - Base URL: `https://coding.dashscope.aliyuncs.com/apps/anthropic`
> - 模型: `qwen3.5-plus`
> - 标准 OpenAI SDK 兼容格式

### 修改配置

**更新为 Coding Plan 端点**（需要执行）：

```bash
# 1. SSH 到虚拟机
ssh root@192.168.88.31

# 2. 更新 .env 文件
cd /opt/MiroFish
cat > .env << 'EOF'
# LLM API配置（使用阿里百炼 Coding Plan）
LLM_API_KEY=sk-sp-fdf3de2a9f4a4bc4a00cd98052343a8d
LLM_BASE_URL=https://coding.dashscope.aliyuncs.com/apps/anthropic
LLM_MODEL_NAME=qwen3.5-plus

# Zep Cloud 配置（记忆图谱）
ZEP_API_KEY=z_1dWlkIjoiZmFkZTllZmMtY2NlOS00MzMzLWI4ZTgtYmRhMGRjYjk0OGU0In0.1taekFaJKzFv7fqjIegF-drB5mi53Y-dYnf0Q5oJrtnC-7MdCamzQ2vbqESmpZdCIUksHOWrVAQbisYtFR6GlQ
EOF

# 3. 验证配置
cat .env

# 4. 重启服务
docker compose restart

# 5. 查看日志
docker compose logs -f backend
```

---

## 🌐 网络配置

### Tailscale Serve 配置（可选）

如果需要通过 Tailscale 访问：

```bash
# 配置 HTTPS 代理
tailscale serve --bg --https 3000 localhost:3000
tailscale serve --bg --https 5001 localhost:5001

# 查看配置
tailscale serve status

# 关闭代理
tailscale serve --https=3000 off
tailscale serve --https=5001 off
```

---

## 📊 资源使用

### 端口分配

| 端口 | 服务 | 说明 |
|------|------|------|
| 3000 | 前端 | Vue 3 Web UI |
| 5001 | 后端 | Flask API |

### 系统资源

| 资源 | 配置 | 实际使用 |
|------|------|---------|
| **内存** | 4GB | ~500MB |
| **CPU** | 4 核 | <10% |
| **磁盘** | 22GB | ~5GB (镜像+数据) |

---

## 🚨 故障排除

### 1. 服务无法启动

**检查日志**:
```bash
docker compose logs -f
```

### 2. 端口被占用

**检查端口**:
```bash
netstat -tlnp | grep -E ':(3000|5001)'
```

**解决方案**:
```bash
# 修改 docker-compose.yml 中的端口
ports:
  - "3001:3000"  # 改为其他端口
```

### 3. 前端访问 404

**原因**: 前端正在构建中

**解决方案**:
```bash
# 等待 30-60 秒后重试
sleep 30
curl http://localhost:3000
```

### 4. API Key 未配置或验证失败

**错误**: 后端日志显示 API 错误

**重要**: 如果使用 **阿里百炼 Coding Plan**，需要使用专用端点：
- Base URL: `https://coding.dashscope.aliyuncs.com/apps/anthropic`
- 模型: `qwen3.5-plus`
- 格式: 标准 OpenAI SDK 兼容

**诊断步骤**:
```bash
# 测试阿里百炼 Coding Plan API
curl -s -X POST https://coding.dashscope.aliyuncs.com/apps/anthropic \
  -H 'Authorization: Bearer YOUR_API_KEY' \
  -H 'Content-Type: application/json' \
  -d '{"model":"qwen3.5-plus","messages":[{"role":"user","content":"你好"}],"max_tokens":10}'
```

**常见问题**:
1. **"Incorrect API key provided"** - API Key 无效或端点错误
   - 确认使用正确的端点（Coding Plan 使用 `coding.dashscope.aliyuncs.com`）
   - 验证 API Key 格式正确（以 `sk-sp-` 开头）
   - 检查模型名称是否正确（Coding Plan 使用 `qwen3.5-plus`）

2. **"404 page not found"** - Zep Cloud API Key 无效
   - 检查 Zep Cloud 账户状态
   - 验证 API Key 是否有效

**解决方案**:
```bash
# 配置 .env 文件
cd /opt/MiroFish
nano .env

# 重启服务
docker compose restart

# 查看日志验证
docker compose logs -f backend
```

---

## 📝 API 端点

### 健康检查

```bash
# 后端健康检查
curl http://192.168.88.31:5001/health

# 返回
{
  "service": "MiroFish Backend",
  "status": "ok"
}
```

### 主要 API

- **POST** `/api/predict` - 创建预测任务
- **GET** `/api/status` - 获取任务状态
- **GET** `/api/results` - 获取预测结果

---

## 🔐 安全建议

1. **配置 API Key**: 首次使用前配置有效的 LLM API Key
2. **使用 HTTPS**: 通过 Tailscale Serve 或反向代理启用 HTTPS
3. **定期备份**: 定期备份 `/opt/MiroFish/backend/uploads/` 目录
4. **监控日志**: 定期检查日志，5. **资源限制**: 配置 Docker 资源限制（如需要）

---

## 📚 相关资源

### 官方文档
- **项目地址**: https://github.com/666ghj/MiroFish
- **在线 Demo**: mirofish-live-demo
- **CAMEL-AI**: https://github.com/camel-ai/camel
- **Zep Cloud**: https://www.getzep.com/

### 技术栈
- **后端**: Python 3.11+, Flask, CAMEL-AI, Zep Cloud
- **前端**: Vue 3, Vite
- **部署**: Docker Compose

---

## 🔄 更新历史

- **2026-03-10 03:47**: 初始部署完成
  - 创建 PVE 虚拟机 (VM ID=111)
  - 安装 Docker 和 Docker Compose
  - 克隆 MiroFish 项目
  - 配置 .env 文件（占位符）
  - 启动 Docker 服务
  - 验证服务运行状态

- **2026-03-10 05:49**: API Key 配置 ⚠️
  - 配置阿里百炼 API Key (qwen-plus 模型)
  - 配置 Zep Cloud API Key (智能体记忆系统)
  - 重启服务使配置生效
  - **问题**: API Key 验证失败（"Incorrect API key provided"）
  - **待办**: 需要验证 API Key 有效性和权限

- **2026-03-10 06:20**: 故障排查文档更新
  - 添加 API Key 验证诊断步骤
  - 参考 node-11 部署文档验证配置格式
  - 测试多个模型名称（qwen-plus, qwen3-max, coder-plus 等）
  - 所有测试均返回 "Incorrect API key provided" 错误

---

**文档版本**: 1.1
**最后更新**: 2026-03-10 06:20
**维护者**: Molt (战术蟹王)
