---
type: [KB:LESSON]
title: "Tailscale 基线部署 SOP"
created: 2026-02-25
updated: 2026-03-05
source: Manual
confidence: high
tags: [tailscale, sop, deployment, network, ssh, derp]
related: [tailscale-network, pve, node-11, node-22]
version: v1.0
status: active
last_verified: 2026-03-05
---

# Tailscale 基线部署标准操作程序 (SOP-006)

> **适用范围**: 所有需要通过 Tailscale 组网的节点
> **关联项目**: Operation Nexus V4.1.2

## 目的

本文档定义了 Tailscale 网络的标准化部署和配置方案，包括：
- DERP（Designated Encrypted Relay for Packets）中继服务器部署
- Tailscale SSH 配置
- ACL（访问控制列表）配置
- 运维和故障排查指南

---

## 架构设计

### 网络拓扑

```
┌─────────────────────────────────────────────────────────┐
│                    Tailscale 控制平面                      │
│              (controlplane.tailscale.com)                │
└────────────────────┬────────────────────────────────────┘
                     │
        ┌────────────┴────────────┐
        │                         │
   ┌────▼────┐               ┌────▼────┐
   │  node-00  │               │  node-01  │
   │ 计算站  │◄─────────────►│ 主控站  │
   └─────────┘  DERP Relay   └─────────┘
```

### 节点角色定义

| 节点名称 | 角色 | Tailscale IP | 公网 IP | DERP 角色 |
|---------|------|--------------|---------|-----------|
| node-00 | 计算补给站 | 100.100.1.5 | 47.111.21.195 | DERP Server (node-00) |
| node-01 | 主控/记忆中枢 | 100.100.1.9 | 116.62.168.71 | DERP Server (node-01) |

### DERP 架构

**Region 900: cn-relay (Hangzhou Dual-Relay)**

- **双节点冗余**: node-00 和 node-01 都运行 DERP 服务器
- **自动故障转移**: 当一个节点不可用时，自动切换到另一个
- **低延迟**: 本地中继减少网络延迟

---

## DERP 服务器部署

### 前置条件

- Docker 已安装并运行
- 端口 33445 (DERP) 和 33446 (STUN) 已开放
- 服务器有公网 IP
- Tailscale 客户端已安装并认证

### 部署步骤

#### 1. 创建目录结构

```bash
mkdir -p /opt/derp/certs
cd /opt/derp
```

#### 2. 创建 Docker Compose 配置

创建 `/opt/derp/docker-compose.yml`:

```yaml
services:
  tailscale-derp:
    image: crpi-huy8s6hrw10gs16i.cn-hangzhou.personal.cr.aliyuncs.com/soul-legion/molt-net:latest
    container_name: tailscale-derp
    restart: always
    network_mode: "host"
    volumes:
      - /opt/derp/certs:/app/certs
    environment:
      - DERP_DOMAIN=<SERVER_IP>           # 替换为服务器公网 IP
      - DERP_CERT_MODE=manual
      - DERP_CERT_DIR=/app/certs
      - DERP_ADDR=:33445
      - DERP_STUN=true
      - DERP_STUN_PORT=33446
      - DERP_HTTP_PORT=-1
      - DERP_VERIFY_CLIENTS=false        # 生产环境建议 true
```

#### 3. 启动 DERP 服务器

```bash
docker compose up -d
```

#### 4. 获取证书指纹

```bash
docker logs tailscale-derp 2>&1 | grep -i 'sha256'
```

**重要**: 记录完整的 `CertName` 值，稍后配置 DERP map 时需要使用。

#### 5. 验证 DERP 服务

```bash
curl -k https://localhost:33445
```

预期输出显示 DERP 服务 HTML 页面。

---

## Tailscale SSH 配置

### 启用 Tailscale SSH

```bash
# 启用 Tailscale SSH
tailscale up --ssh

# 如果有其他非默认配置，需要保留
tailscale up --ssh --accept-dns=false --advertise-tags=tag:aliyun
```

### 验证 SSH 状态

```bash
# 检查 Tailscale SSH 是否启用
tailscale debug prefs | grep -i ssh
```

### ACL 配置

在 Tailscale 管理控制台 (https://login.tailscale.com/admin/acls) 配置基础 SSH ACL：

```json
{
  "ssh": [
    {
      "action": "accept",
      "src": ["xun201811@gmail.com", "tag:aliyun"],
      "dst": ["tag:aliyun"],
      "users": ["root", "busiji"]
    }
  ]
}
```

---

## 完整部署流程

### 新节点部署清单

#### 步骤 1: 安装 Tailscale

```bash
# Ubuntu/Debian
curl -fsSL https://tailscale.com/install.sh | sh

# 启动并认证
tailscale up --advertise-tags=tag:aliyun
```

#### 步骤 2: 启用 Tailscale SSH

```bash
tailscale up --ssh --advertise-tags=tag:aliyun
```

#### 步骤 3: 部署 DERP 服务器（如需要）

参考上文 DERP 服务器部署章节。

#### 步骤 4: 更新 ACL 配置

在 Tailscale 管理控制台更新：
- 添加新节点到 tagOwners
- 更新 DERP map（如果部署了 DERP 服务器）
- 更新 SSH ACL

#### 步骤 5: 验证连接

```bash
# 检查节点状态
tailscale status

# 测试 SSH 连接
ssh root@<TAILSCALE_IP>

# 检查 DERP 连接
journalctl -u tailscaled -n 20 | grep -i derp
```

---

## 运维指南

### 日常检查

#### 每日检查项

```bash
# 1. 检查 Tailscale 状态
tailscale status

# 2. 检查 DERP 连接
journalctl -u tailscaled -n 20 | grep -i derp

# 3. 检查 DERP 服务器状态
docker ps | grep derp
docker logs tailscale-derp --tail 20

# 4. 检查 SSH 连接
ssh root@<OTHER_NODE> "hostname"
```

#### 每周检查项

- 检查证书有效期（如使用自定义证书）
- 检查 DERP 服务器日志是否有异常
- 验证 ACL 配置是否符合安全要求
- 更新 DERP 服务器镜像（如有更新）

### 常用命令

```bash
# Tailscale
tailscale status                    # 查看状态
tailscale up --ssh                  # 启用 SSH
tailscale ip                        # 查看 IP
tailscale logout                    # 登出

# DERP
docker ps | grep derp               # 查看容器
docker logs tailscale-derp          # 查看日志
docker restart tailscale-derp       # 重启服务

# 诊断
journalctl -u tailscaled -n 50      # 查看日志
ss -tlnp | grep 33445              # 检查端口
curl -k https://localhost:33445    # 测试 DERP
```

---

## 故障排查

### DERP 连接失败

**症状**:
```
magicsock: derp.Recv(derp-900): cert hash does not match expected cert hash
```

**原因**: DERP map 中的证书指纹与实际证书不匹配

**解决方案**:
1. 获取正确的证书指纹：`docker logs tailscale-derp 2>&1 | grep -i 'sha256'`
2. 更新 ACL 中的 DERP map 配置
3. 等待几分钟让配置同步

### Tailscale SSH 无法连接

**症状**:
```
tailscale: tailnet policy does not permit you to SSH to this node
```

**原因**: ACL 配置不允许当前用户访问目标节点

**解决方案**:
1. 检查 ACL 配置中的 `ssh` 部分
2. 确认 `src` 包含当前用户的邮箱或标签
3. 确认 `dst` 包含目标节点的标签
4. 确认 `users` 包含目标系统用户

### DERP 证书域名不匹配

**症状**:
```
derper: can not start cert provider: cert invalid for hostname "47.111.21.195"
```

**原因**: 使用了为其他 IP 生成的证书

**解决方案**:
1. 删除错误的证书文件：`rm -f /opt/derp/certs/*`
2. 重启 DERP 容器生成新的自签名证书
3. 获取新证书指纹并更新 DERP map

---

## 安全最佳实践

### ACL 配置原则

1. **最小权限原则**: 只授予必要的访问权限
2. **标签分组**: 使用标签对节点进行分组管理
3. **明确源和目标**: 避免使用通配符 `*`，除非必要

### DERP 服务器安全

1. **证书管理**: 生产环境使用 `DERP_VERIFY_CLIENTS=true`，定期更新证书
2. **网络隔离**: DERP 服务器应放在受保护的网络区域
3. **监控和日志**: 定期检查 DERP 服务器日志

---

## 相关文档

- **Tailscale 网络配置**: `memory/docs/references/technical-baselines/tailscale-network.md`
- **PVE 宿主机**: `memory/kb/projects/pve.md`
- **SOP 原始文件**: `/Users/busiji/passkills/standards/sop-006-tailscale-baseline.md`

---

## 更新历史

- **2026-03-05**: 更新验证，SOP 完整内容确认
- **2026-03-04**: 迁移至 MRD 规范位置 `kb/lessons/`，添加 frontmatter
- **2026-02-25**: 初始版本 (v1.0.0)
