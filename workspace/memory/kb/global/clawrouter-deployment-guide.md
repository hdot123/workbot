---
type: [KB:GLOBAL]
title: "ClawRouter 多品牌协议集成部署指南"
created: 2026-03-10 18:38
updated: 2026-03-24 00:00
source: Manual
confidence: high
tags: [deployment, clawrouter, docker, multi-brand, protocol, baseline]
related:
  - multi-brand-protocol-baseline
  - pve-docker-template-deployment-guide
  - node-11
version: v1.0
status: superseded
last_verified: 2026-03-10
---

# ClawRouter 多品牌协议集成部署指南

> SOURCE MATERIAL ONLY
> 本文件继承自旧项目材料，仅作历史来源，不具备当前默认解释权。

> **唯一真相声明**: 本文档为 ClawRouter 部署的最高规范。若与其他文档冲突，**以此为准**。

**适用对象**: 需要部署 ClawRouter 服务的所有节点
**目标**: 让部署过程**标准化、可重复、可追溯**
**范围**: 本文件定义"部署流程/配置规范/验证标准"，具体执行见项目实施脚本

---

## 📋 部署目标

将 **ClawRouter** 从 **node-11 (Alpine LXC)** 迁移到 **新服务器 (Docker VM)**，并集成 **多品牌协议基线**。

### 迁移路径

```
node-11 (Alpine LXC)
  └─ /opt/clawrouter-server/     # 旧位置
      └─ .env                     # 旧配置
      └─ server.js                # 旧代码

       ⬇️  迁移

新服务器 (Docker VM)
  └─ /opt/clawrouter/             # 新位置
      └─ .env                     # 新配置（集成多品牌基线）
      └─ docker-compose.yml       # 容器编排
      └─ src/                     # 代码
```

---

## 🚀 部署流程

### 阶段一：前置准备（已完成 ✅）

- [x] 备份 node-11 clawrouter 配置
  - 备份文件: `tmp/clawrouter-backup-20260310.tar.gz` (19MB)
  - 包含: `/opt/clawrouter-server/` + `/etc/init.d/clawrouter`

### 阶段二：创建新虚拟机

**执行位置**: PVE 宿主机 Shell

```bash
# ============================================
# 1. 从模板克隆新虚拟机
# ============================================
VM_ID=101
TEMPLATE_ID=9000

qm clone $TEMPLATE_ID $VM_ID \
    --name "clawrouter-01" \
    --full false

# ============================================
# 2. 配置 Cloud-init
# ============================================
# 设置用户名
qm set $VM_ID --ciuser ubuntu

# 设置 SSH 公钥
qm set $VM_ID --sshkeys ~/.ssh/id_rsa.pub

# 设置网络（DHCP）
qm set $VM_ID --ipconfig0 ip=dhcp

# ============================================
# 3. 启动虚拟机
# ============================================
qm start $VM_ID

# ============================================
# 4. 等待虚拟机启动（约 1-2 分钟）
# ============================================
sleep 120

# ============================================
# 5. 获取 IP 地址
# ============================================
VM_IP=$(qm guest exec $VM_ID -- ip -4 addr show eth0 | grep -oP '(?<=inet\s)\d+(\.\d+){3}')
echo "VM IP: $VM_IP"
```

### 阶段三：配置 Docker 环境

**执行位置**: 新虚拟机内部 (SSH 登录)

```bash
# ============================================
# 1. SSH 登录
# ============================================
ssh ubuntu@$VM_IP

# ============================================
# 2. 切换到 root
# ============================================
sudo -i

# ============================================
# 3. 验证 Docker 环境
# ============================================
docker --version
docker compose version
docker run --rm hello-world

# ============================================
# 4. 创建项目目录
# ============================================
mkdir -p /opt/clawrouter
cd /opt/clawrouter

# ============================================
# 5. 创建子目录结构
# ============================================
mkdir -p {src,config,logs,data}
```

### 阶段四：迁移 clawrouter 代码

**执行位置**: 本地 Mac

```bash
# ============================================
# 1. 解压备份文件
# ============================================
cd /Users/busiji/passkills/tmp
tar -xzf clawrouter-backup-20260310.tar.gz

# ============================================
# 2. 查看旧配置文件
# ============================================
cat opt/clawrouter-server/.env

# ============================================
# 3. 上传代码到新服务器
# ============================================
scp -r opt/clawrouter-server/* ubuntu@$VM_IP:/tmp/clawrouter-src/

# ============================================
# 4. SSH 到新服务器，移动文件到正确位置
# ============================================
ssh ubuntu@$VM_IP
sudo mv /tmp/clawrouter-src/* /opt/clawrouter/src/
```

### 阶段五：配置多品牌协议基线

**执行位置**: 新虚拟机内部

#### 5.1 创建 `.env` 配置文件

```bash
cat > /opt/clawrouter/.env <<'EOF'
# ============================================
# ClawRouter 配置文件（多品牌协议基线 v1.2）
# ============================================

# 服务配置
PORT=3000
NODE_ENV=production

# ============================================
# Aliyun (百炼) 配置
# ============================================
BAILIAN_API_KEY=sk-sp-fdf3de2a9f4a4bc4a00cd98052343a8d

# OpenAI 协议端点
BAILIAN_OPENAI_BASE_URL=https://coding.dashscope.aliyuncs.com/v1
BAILIAN_OPENAI_MODELS=qwen3.5-plus,glm-4.7

# Anthropic 协议端点
BAILIAN_ANTHROPIC_BASE_URL=https://coding.dashscope.aliyuncs.com/apps/anthropic/v1
BAILIAN_ANTHROPIC_MODELS=glm-4.7

# ============================================
# Zhipu (智谱) 配置
# ============================================
ZHIPU_API_KEY=2cce0299c67444759ff2ec091a9a1e0c.2v7KjqRUMROd44Rt

# OpenAI 协议端点
ZHIPU_OPENAI_BASE_URL=https://open.bigmodel.cn/api/paas/v4
ZHIPU_OPENAI_MODELS=glm-5,glm-4.7,glm-4-plus

# Anthropic 协议端点
ZHIPU_ANTHROPIC_BASE_URL=https://open.bigmodel.cn/api/anthropic/v1
ZHIPU_ANTHROPIC_MODELS=glm-5,glm-4.7

# ============================================
# 协议路由配置
# ============================================
# 默认路由策略：bailian-openai, zhipu-openai, bailian-anthropic, zhipu-anthropic
DEFAULT_ROUTE=bailian-openai

# 思维链处理：extract（提取）, filter（过滤）, passthrough（透传）
REASONING_MODE=extract

# ============================================
# 网关配置
# ============================================
# 字段映射统一
ENABLE_FIELD_MAPPING=true

# 日志级别
LOG_LEVEL=info

# 健康检查端点
HEALTH_CHECK_ENABLED=true
EOF

# 设置权限
chmod 600 /opt/clawrouter/.env
```

#### 5.2 创建 `docker-compose.yml`

```bash
cat > /opt/clawrouter/docker-compose.yml <<'EOF'
version: '3.8'

services:
  clawrouter:
    image: node:22-alpine
    container_name: clawrouter
    restart: unless-stopped
    ports:
      - "3000:3000"
    volumes:
      - ./src:/app
      - ./config:/app/config
      - ./logs:/app/logs
      - ./data:/app/data
    environment:
      - NODE_ENV=production
    env_file:
      - .env
    working_dir: /app
    command: node server.js
    healthcheck:
      test: ["CMD", "wget", "--quiet", "--tries=1", "--spider", "http://localhost:3000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
EOF
```

#### 5.3 更新 `server.js` 代码

**创建多品牌协议适配器**:

```bash
cat > /opt/clawrouter/src/protocol-adapter.js <<'EOF'
/**
 * 多品牌协议适配器
 * 基于: multi-brand-protocol-baseline.md v1.2
 */

class ProtocolAdapter {
  constructor(config) {
    this.config = config;
  }

  /**
   * 根据品牌和协议选择端点
   */
  selectEndpoint(brand, protocol) {
    const key = `${brand}_${protocol}_BASE_URL`;
    return process.env[key];
  }

  /**
   * 统一字段映射
   */
  normalizeResponse(response, brand, protocol) {
    if (protocol === 'openai') {
      return {
        usage: {
          in: response.usage?.prompt_tokens,
          out: response.usage?.completion_tokens,
          reasoning: response.usage?.completion_tokens_details?.reasoning_tokens
        },
        state: {
          stop: response.choices?.[0]?.finish_reason
        },
        response: {
          text: response.choices?.[0]?.message?.content,
          reasoning: response.choices?.[0]?.message?.reasoning_content
        }
      };
    } else if (protocol === 'anthropic') {
      const contentArray = response.content || [];
      const textBlock = contentArray.find(b => b.type === 'text');
      const thinkingBlock = contentArray.find(b => b.type === 'thinking');

      return {
        usage: {
          in: response.usage?.input_tokens,
          out: response.usage?.output_tokens
        },
        state: {
          stop: response.stop_reason
        },
        response: {
          text: textBlock?.text,
          reasoning: thinkingBlock?.thinking
        }
      };
    }
  }
}

module.exports = ProtocolAdapter;
EOF
```

### 阶段六：启动服务

**执行位置**: 新虚拟机内部

```bash
# ============================================
# 1. 启动 Docker 容器
# ============================================
cd /opt/clawrouter
docker compose up -d

# ============================================
# 2. 查看容器状态
# ============================================
docker compose ps

# ============================================
# 3. 查看日志
# ============================================
docker compose logs -f clawrouter

# ============================================
# 4. 验证健康检查
# ============================================
curl http://localhost:3000/health
```

### 阶段七：验证测试

**执行位置**: 新虚拟机内部

```bash
# ============================================
# 测试脚本
# ============================================
cat > /tmp/test-clawrouter.sh <<'EOF'
#!/bin/bash

BASE_URL="http://localhost:3000"

echo "🧪 ClawRouter 多品牌协议集成测试"
echo "=================================="

# 1. 健康检查
echo -e "\n1. 健康检查"
curl -s $BASE_URL/health | jq .

# 2. 百炼 OpenAI 协议测试
echo -e "\n2. 百炼 OpenAI 协议 (qwen3.5-plus)"
curl -s -X POST $BASE_URL/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "1+1等于几？", "profile": "bailian-openai", "model": "qwen3.5-plus"}' | jq .

# 3. 百炼 Anthropic 协议测试
echo -e "\n3. 百炼 Anthropic 协议 (glm-4.7)"
curl -s -X POST $BASE_URL/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "1+1等于几？", "profile": "bailian-anthropic", "model": "glm-4.7"}' | jq .

# 4. 智谱 OpenAI 协议测试
echo -e "\n4. 智谱 OpenAI 协议 (glm-5)"
curl -s -X POST $BASE_URL/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "1+1等于几？", "profile": "zhipu-openai", "model": "glm-5"}' | jq .

# 5. 智谱 Anthropic 协议测试
echo -e "\n5. 智谱 Anthropic 协议 (glm-4.7)"
curl -s -X POST $BASE_URL/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "1+1等于几？", "profile": "zhipu-anthropic", "model": "glm-4.7"}' | jq .

echo -e "\n✅ 测试完成！"
EOF

chmod +x /tmp/test-clawrouter.sh
/tmp/test-clawrouter.sh
```

---

## 🔧 配置清单

### 环境变量

| 变量名 | 说明 | 示例值 |
|--------|------|--------|
| `BAILIAN_API_KEY` | 百炼 API Key | `sk-sp-xxx` |
| `ZHIPU_API_KEY` | 智谱 API Key | `xxx.xxx` |
| `BAILIAN_OPENAI_BASE_URL` | 百炼 OpenAI 端点 | `https://coding.dashscope.aliyuncs.com/v1` |
| `BAILIAN_ANTHROPIC_BASE_URL` | 百炼 Anthropic 端点 | `https://coding.dashscope.aliyuncs.com/apps/anthropic/v1` |
| `ZHIPU_OPENAI_BASE_URL` | 智谱 OpenAI 端点 | `https://open.bigmodel.cn/api/paas/v4` |
| `ZHIPU_ANTHROPIC_BASE_URL` | 智谱 Anthropic 端点 | `https://open.bigmodel.cn/api/anthropic/v1` |
| `DEFAULT_ROUTE` | 默认路由 | `bailian-openai` |
| `REASONING_MODE` | 思维链处理模式 | `extract` |

### 目录结构

```
/opt/clawrouter/
├── docker-compose.yml     # 容器编排
├── .env                   # 环境变量
├── src/                   # 源代码
│   ├── server.js          # 主服务
│   └── protocol-adapter.js # 协议适配器
├── config/                # 配置文件
├── logs/                  # 日志目录
└── data/                  # 数据持久化
```

---

## ✅ 验收标准

### 必须通过

- [ ] **Docker 容器运行**: `docker compose ps` 显示 healthy
- [ ] **健康检查**: `GET /health` 返回 `{"ok":true}`
- [ ] **百炼 OpenAI**: 测试通过，包含 `reasoning_content`
- [ ] **百炼 Anthropic**: 测试通过，正确提取 `text` 块
- [ ] **智谱 OpenAI**: 测试通过，包含 `reasoning_content`
- [ ] **智谱 Anthropic**: 测试通过，标准响应
- [ ] **字段映射**: 所有协议的 `usage.in`/`usage.out` 正确映射

### 建议验证

- [ ] **日志轮转**: 验证 `max-size` 和 `max-file` 生效
- [ ] **性能基准**: 响应时间 < 5s（简单查询）
- [ ] **监控接入**: 日志可被收集系统读取

---

## 🧹 清理旧服务

**执行位置**: node-11 (Alpine LXC)

```bash
# ============================================
# 1. 停止服务
# ============================================
rc-service clawrouter stop

# ============================================
# 2. 禁用开机自启
# ============================================
rc-update del clawrouter default

# ============================================
# 3. 删除服务脚本
# ============================================
rm /etc/init.d/clawrouter

# ============================================
# 4. 备份并删除代码目录
# ============================================
# 备份已在上一步完成，现在删除
rm -rf /opt/clawrouter-server

# ============================================
# 5. 删除日志文件
# ============================================
rm -f /var/log/clawrouter.log

# ============================================
# 6. 验证清理
# ============================================
rc-service clawrouter status  # 应该显示 "does not exist"
ls /opt/clawrouter-server     # 应该不存在
```

---

## 📊 迁移对比

| 项目 | 旧环境 (node-11) | 新环境 (VM 101) |
|------|------------------|-----------------|
| **系统** | Alpine Linux v3.22 | Ubuntu 24.04 |
| **容器** | LXC | Docker |
| **运行方式** | OpenRC 服务 | Docker Compose |
| **代码位置** | `/opt/clawrouter-server/` | `/opt/clawrouter/` |
| **协议支持** | 单一协议 | 多品牌双协议 |
| **配置管理** | `.env` 文件 | `.env` + `docker-compose.yml` |
| **日志管理** | `/var/log/clawrouter.log` | Docker logs + json-file |
| **监控** | 无 | Docker healthcheck |
| **迁移状态** | 待删除 | 已部署 |

---

## 🔄 回滚方案

如果新服务器出现问题，可以快速回滚：

### 方案 A: 重新启动 node-11 服务

```bash
# 在 node-11 上执行
cd /opt
tar -xzf /tmp/clawrouter-backup-20260310.tar.gz
rc-update add clawrouter default
rc-service clawrouter start
```

### 方案 B: 并行运行（推荐）

保留 node-11 服务，使用不同端口：

```bash
# node-11: 端口 3000（旧）
# 新服务器: 端口 3001（新）

# 逐步切换流量到新服务器
```

---

## 📚 相关文档

- **多品牌协议基线**: `workspace/memory/kb/global/multi-brand-protocol-baseline.md`
- **PVE Docker 模板**: `workspace/memory/kb/global/pve-docker-template-deployment-guide.md`
- **node-11 档案**: `workspace/memory/kb/projects/node-11.md`

---

## 📝 维护记录

| 日期 | 版本 | 变更内容 |
|------|------|----------|
| 2026-03-10 | v1.0 | 初始版本，基于多品牌协议基线 v1.2 |

---

**文档维护**: 此文档已保存至项目记忆系统，可通过 AI 助手快速查阅和更新。
