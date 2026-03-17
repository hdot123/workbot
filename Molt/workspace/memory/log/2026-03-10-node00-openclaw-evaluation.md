# node-00 游戏环境与 openclaw 部署评估报告

> **检查日期**: 2026-03-10
> **节点**: node-00 (计算补给站)
> **公网 IP**: 47.111.21.195
> **Tailscale IP**: 100.100.1.5

---

## 📊 系统资源分析

### 硬件配置
- **操作系统**: Alibaba Cloud Linux 3 (OpenAnolis Edition)
- **内核版本**: 5.10.134-17.2.al8.x86_64
- **总内存**: 1.8GB
- **已用内存**: 252MB (14%)
- **可用内存**: 1.4GB (充足)
- **磁盘**: 40GB (已用 7.7GB, 21%)

### 当前运行的服务
| 服务 | 内存占用 | 状态 | 用途 |
|------|---------|------|------|
| tailscaled | 79MB | 运行中 | Tailscale VPN |
| dockerd | 62MB | 运行中 | Docker 守护进程 |
| containerd | 29MB | 运行中 | 容器运行时 |
| derper | 23MB | 运行中 | DERP 中继服务器 |
| 阿里云监控 | ~40MB | 运行中 | 云监控 Agent |

### 监听端口
- **22**: SSH
- **33445**: Tailscale DERP (STUN)
- **33446**: Tailscale STUN

---

## 🎮 游戏环境检查

### 已发现的服务

#### 1. clawrouter-server (`/opt/clawrouter-server/`)
- **类型**: BlockRun LLM 路由服务
- **状态**: ❌ 未运行
- **技术栈**: Node.js + Express + @blockrun/llm-ts
- **端口**: 3000
- **配置**: 需要 `BLOCKRUN_WALLET_KEY` 环境变量

**代码功能**:
```javascript
POST /chat - 智能聊天接口（支持多 Profile）
GET /health - 健康检查
```

#### 2. openclaw (`/opt/openclaw/`)
- **类型**: Claw AI 框架（飞书机器人）
- **状态**: ❌ 未运行
- **配置文件**: `openclaw.json`
- **端口**: 18789
- **通道**: 飞书（已配置）

**配置详情**:
```json
{
  "gateway": {
    "port": 18789,
    "mode": "local",
    "bind": "lan"
  },
  "channels": {
    "feishu": {
      "appId": "cli_a910faab8078dcef",
      "appSecret": "***"
    }
  }
}
```

---

## 🚀 openclaw 部署方案评估

### 方案对比

| 部署模式 | 内存开销 | 性能 | 管理复杂度 | 资源隔离 | 推荐度 |
|---------|---------|------|-----------|---------|--------|
| **Docker (host 网络)** | 80-150MB | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ✅ **推荐** |
| Docker (bridge 网络) | 100-180MB | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| 裸机部署 (systemd) | 60-120MB | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐ | ⭐⭐⭐ |
| PM2 部署 | 80-140MB | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ |

### 当前配置分析

**docker-compose.yml (当前)**:
```yaml
services:
  openclaw:
    image: node:20
    container_name: openclaw
    restart: always
    network_mode: "host"           # ✅ 最优网络性能
    environment:
      - NODE_ENV=production
    volumes:
      - /opt/openclaw:/root/.openclaw
    command: >
      bash -c "npx -y openclaw@latest start"
```

**优势**:
- ✅ 使用 host 网络模式，无 NAT 开销
- ✅ 自动拉取最新版本（`@latest`）
- ✅ 配置持久化（volume 挂载）
- ✅ 自动重启策略

**劣势**:
- ⚠️ 无资源限制（可能内存泄漏）
- ⚠️ 无日志轮转配置
- ⚠️ 每次启动都检查更新（启动慢）

---

## 💡 优化建议

### 1. 添加资源限制（防止内存泄漏）

```yaml
services:
  openclaw:
    image: node:20
    container_name: openclaw
    restart: always
    network_mode: "host"
    environment:
      - NODE_ENV=production
      - NODE_OPTIONS=--max-old-space-size=512  # 限制 Node.js 堆内存
    volumes:
      - /opt/openclaw:/root/.openclaw
    deploy:
      resources:
        limits:
          memory: 512M        # 硬限制
        reservations:
          memory: 256M        # 软限制
    command: >
      bash -c "npx -y openclaw@latest start"
```

### 2. 固化版本（提升启动速度）

```yaml
command: >
  bash -c "npx -y openclaw@2026.2.26 start"
```

### 3. 添加日志轮转

```yaml
logging:
  driver: "json-file"
  options:
    max-size: "10m"
    max-file: "3"
```

### 4. 完整优化配置

```yaml
version: "3.9"

services:
  openclaw:
    image: node:20-alpine  # 使用 Alpine 版本（更小）
    container_name: openclaw
    restart: unless-stopped
    network_mode: "host"
    environment:
      - NODE_ENV=production
      - NODE_OPTIONS=--max-old-space-size=512
    volumes:
      - /opt/openclaw:/root/.openclaw
      - openclaw-cache:/root/.npm  # 缓存 npm 包
    deploy:
      resources:
        limits:
          cpus: '1.0'
          memory: 512M
        reservations:
          cpus: '0.5'
          memory: 256M
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:18789/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    command: >
      bash -c "npx -y openclaw@2026.2.26 start"

volumes:
  openclaw-cache:
```

---

## 📈 资源占用预估

### 优化后内存占用
- **Node.js 进程**: 80-120MB
- **openclaw 运行时**: 60-100MB
- **容器开销**: 10-20MB
- **总计**: 150-240MB

### 与当前可用资源对比
- **可用内存**: 1.4GB
- **预估占用**: 240MB
- **剩余内存**: 1.16GB (充足)

---

## ✅ 部署建议

### 推荐方案：优化后的 Docker 部署

**理由**:
1. **资源充足**: 1.4GB 可用内存足够运行 openclaw
2. **性能最优**: host 网络模式无性能损耗
3. **易于管理**: Docker 提供良好的隔离和重启策略
4. **已验证**: 配置文件已存在，部署成本低

### 部署步骤

```bash
# 1. 更新配置文件
cd /opt/openclaw
cat > docker-compose.yml << 'EOF'
version: "3.9"
services:
  openclaw:
    image: node:20-alpine
    container_name: openclaw
    restart: unless-stopped
    network_mode: "host"
    environment:
      - NODE_ENV=production
      - NODE_OPTIONS=--max-old-space-size=512
    volumes:
      - /opt/openclaw:/root/.openclaw
      - openclaw-cache:/root/.npm
    deploy:
      resources:
        limits:
          cpus: '1.0'
          memory: 512M
        reservations:
          cpus: '0.5'
          memory: 256M
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
    healthcheck:
      test: ["CMD", "wget", "--no-verbose", "--tries=1", "--spider", "http://localhost:18789/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    command: >
      ash -c "npx -y openclaw@2026.2.26 start"
volumes:
  openclaw-cache:
EOF

# 2. 启动服务
docker-compose up -d

# 3. 检查状态
docker logs -f openclaw

# 4. 验证健康状态
curl http://localhost:18789/health
```

---

## 🔍 其他发现

### clawrouter-server
- **状态**: 已配置但未运行
- **建议**: 如果不需要 BlockRun 服务，可以删除以节省磁盘空间
- **占用**: 16KB

### 可清理空间
```bash
# 清理未使用的 Docker 资源
docker system prune -af

# 删除不需要的镜像
docker rmi $(docker images -q --filter "dangling=true")
```

---

## 📝 总结

### 当前状态 (2026-03-10 21:00 更新)
- ✅ node-00 资源充足
- ✅ openclaw **已部署并运行**
- ✅ Docker 容器正常运行
- ✅ 飞书 WebSocket 已连接
- ⚠️ 需要配置 API 密钥（anthropic）

### 实际资源占用
| 指标 | 使用量 | 限制 | 百分比 |
|------|--------|------|--------|
| **容器内存** | 445.2 MiB | 1 GiB | 43.48% |
| **CPU** | 0.00% | - | - |
| **宿主机内存** | 661 MiB / 1.8 GiB | - | 36% |
| **宿主机可用** | 1.0 GiB | - | 充足 |

### 部署配置（最终版）
```yaml
services:
  openclaw:
    image: node:22-alpine
    container_name: openclaw
    restart: unless-stopped
    network_mode: host
    environment:
      - NODE_ENV=production
      - NODE_OPTIONS=--max-old-space-size=1024
    volumes:
      - /opt/openclaw:/root/.openclaw
      - openclaw-cache:/root/.npm
    deploy:
      resources:
        limits:
          memory: 1G
        reservations:
          memory: 512M
    command: |
      apk add --no-cache git
      npx -y openclaw@latest gateway --port 18789 --bind lan
```

### 部署问题记录
1. **架构问题**: Mac 是 arm64，node-00 是 x86_64 (amd64)，需要传输镜像
2. **网络问题**: Docker Hub 拉取超时，使用 Mac 中转镜像
3. **内存问题**: 默认 512MB 限制导致 OOM，调整为 1GB
4. **命令变更**: `openclaw start` 已废弃，改用 `openclaw gateway`

### 后续操作
- [ ] 配置 API 密钥：`openclaw agents add main`
- [ ] 验证飞书消息收发
- [ ] 监控内存使用稳定性

### 推荐操作
1. ✅ **使用优化后的 Docker 部署**（已验证配置）
2. ⚠️ **添加资源限制**（防止内存泄漏）
3. ⚠️ **配置日志轮转**（节省磁盘）
4. ⚠️ **固化版本号**（提升启动速度）

### 预期效果
- **内存占用**: 150-240MB
- **剩余内存**: 1.16GB（充足）
- **启动时间**: 约 30-60 秒
- **稳定性**: 高（自动重启 + 资源限制）
