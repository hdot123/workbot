---
type: [KB:REFERENCE]
title: "Tailscale 网络配置手册"
created: 2026-03-04
updated: 2026-03-08
source: Manual
confidence: high
tags: [tailscale, network, vpn, ssh, remote]
related: [pve, node-11, node-22, node-00, node-01]
version: v1.1
status: active
last_verified: 2026-03-08
---

# Tailscale 网络配置手册

## 网络拓扑

### Tailnet 概览

```
┌─────────────────────────────────────────────────────────┐
│                    Tailscale 控制平面                      │
│              (controlplane.tailscale.com)                │
└────────────────────┬────────────────────────────────────┘
                     │
        ┌────────────┴────────────┬────────────┬────────────┐
        │                         │            │            │
   ┌────▼────┐               ┌────▼────┐  ┌───▼───┐  ┌────▼────┐
   │  PVE    │               │ node-11  │  │node-22 │  │ node-00   │
   │ 主控站  │               │ 多租户  │  │ 东京  │  │ 计算站  │
   └─────────┘               └─────────┘  └───────┘  └─────────┘
```

## 节点名规范及清单

**主机命名标准 (Hostname Rule)**:
- **`node-0x`** 系列: 阿里云服务器
- **`node-1x`** 系列: 局域网本地机器
- **`node-2x`** 系列: 腾讯云服务器

| 节点名称 | 角色 | Tailscale IP | 局域网 IP | 公网 IP | 用途 |
|----------|------|--------------|-----------|---------|------|
| **PVE/g** | 主控/虚拟化 | `100.100.1.2` | 192.168.88.9 | - | LXC 容器宿主机 |
| **node-11** | 多租户 OpenClaw | `100.100.1.11` | 192.168.88.11 | 47.111.21.195 | dev-bot, qa-bot |
| **node-22** | 东京节点 | `100.100.1.22` | - | 116.62.168.71 | 海外备份 |
| **node-00** | 计算补给站 | `100.100.1.5` | - | 47.111.21.195 | 冷备、计算溢出 |
| **node-12** | 待定义 | `100.100.1.12` | - | TBD | 新节点 |
| **node-13** | 待定义 | `100.100.1.13` | - | TBD | 新节点 |

### DERP 中继配置

**Region 900: cn-relay (Hangzhou Dual-Relay)**

| 节点 | DERP ID | 端口 | 状态 |
|------|---------|------|------|
| node-00 | 901 | 33445 (DERP), 33446 (STUN) | ✅ |
| node-01 | 902 | 33445 (DERP), 33446 (STUN) | ✅ |

---

## SSH 访问配置

### 通过 Tailscale SSH

```bash
# PVE 宿主机
ssh root@100.100.1.2

# node-11 (Ubuntu)
ssh root@100.100.1.11

# node-22 (东京)
ssh root@100.100.1.22

# node-00 (计算站)
ssh root@100.100.1.5
```

### SSH 配置文件 (~/.ssh/config)

```
# PVE 宿主机
Host pve g
    HostName 192.168.88.9
    User root
    IdentityFile ~/.ssh/id_ed25519

# CT110 (Mihomo 容器)
Host ct110 mihomo
    HostName 192.168.88.29
    User root
    IdentityFile ~/.ssh/id_ed25519
    ProxyJump root@100.100.1.2

# node-11
Host node-11
    HostName 100.100.1.11
    User root
    IdentityFile ~/.ssh/id_ed25519

# node-22
Host node-22 tokyo
    HostName 100.100.1.22
    User root
    IdentityFile ~/.ssh/id_ed25519
```

---

## Tailscale Serve/Funnel 配置

### Serve 模式（内网访问）

适用于：Gateway 控制面板、内部服务暴露

```bash
# 启动 Serve（HTTPS，内网访问）
tailscale serve --bg --https 8443 http://127.0.0.1:18789

# 查看状态
tailscale serve status

# 访问地址
# https://<hostname>.tailnet-name.ts.net:8443
```

### Funnel 模式（公网访问）

适用于：需要公网访问的服务

```bash
# 启动 Funnel（HTTPS，公网访问）
tailscale funnel --bg --https 8443 http://127.0.0.1:18789

# 查看状态
tailscale funnel status

# 访问地址
# https://<hostname>.tailnet-name.ts.net:8443（任何地方可访问）
```

### OpenClaw Gateway 集成

```json5
{
  gateway: {
    bind: "loopback",
    tailscale: { mode: "serve" },
    auth: {
      mode: "token",
      allowTailscale: true  // Tailscale 身份认证
    },
  },
}
```

```bash
# 启动 Gateway with Serve
openclaw gateway --tailscale serve

# 启动 Gateway with Funnel（需要密码）
openclaw gateway --tailscale funnel --auth password
```

---

## 常用命令

### 状态检查

```bash
# 查看节点状态
tailscale status

# JSON 格式输出
tailscale status --json | jq '.Peer'

# 查看本机 IP
tailscale ip -4
tailscale ip -6

# 查看 DNS
tailscale dns status
```

### 连接管理

```bash
# 登录
tailscale up

# 带参数登录（广告标签）
tailscale up --advertise-tags=tag:production

# 启用 SSH
tailscale up --ssh

# 登出
tailscale logout
```

### 故障排查

```bash
# 查看连接详情
tailscale debug prefs

# 网络诊断
tailscale debug ping <hostname>

# 查看 DERPs
tailscale netcheck

# 重置
tailscale reset
```

---

## 安全配置

### ACL 访问控制

在 Tailscale 管理控制台 (https://login.tailscale.com/admin/acls) 配置：

```json
{
  "acls": [
    {
      "action": "accept",
      "src": ["tag:production"],
      "dst": ["tag:production:*"]
    },
    {
      "action": "accept",
      "src": ["autogroup:members"],
      "dst": ["tag:production:22,80,443"]
    }
  ],
  "tagOwners": {
    "tag:production": ["autogroup:admin"]
  }
}
```

### 推荐配置

1. **启用 SSH**: `tailscale up --ssh`
2. **使用标签**: 生产环境节点使用 `--advertise-tags=tag:production`
3. **限制访问**: 通过 ACL 限制只有授权用户可以访问敏感端口

---

## 节点部署指南

### Ubuntu/Debian

```bash
# 安装
curl -fsSL https://tailscale.com/install.sh | sh

# 启动
tailscale up --ssh --advertise-tags=tag:production

# 开机自启
systemctl enable tailscaled
systemctl start tailscaled
```

### Alpine Linux (CT110)

```bash
# 安装
apk add tailscale

# 启动
tailscale up --ssh

# 开机自启
rc-update add tailscaled
rc-service tailscaled start
```

### macOS

```bash
# 从 Mac App Store 或官网下载
# https://tailscale.com/download

# 登录后自动运行
# 系统偏好设置 → Tailscale → 登录
```

---

## 应用场景

### 1. 远程访问 PVE 管理界面

```bash
# 在 PVE 上启动 Serve
tailscale serve --bg --https 8443 https://192.168.88.9:8006

# 访问
open https://pve.tailnet-name.ts.net:8443
```

### 2. OpenClaw 远程 Gateway

```bash
# 在 node-11 上启动 Gateway with Serve
openclaw gateway --tailscale serve

# 从 Mac 访问
# https://node-11.tailnet-name.ts.net:8443
```

### 3. SSH 跳板机

```bash
# 通过 PVE 访问 CT110
ssh -J root@100.100.1.2 root@192.168.88.29

# 或使用 SSH 配置（推荐）
ssh ct110
```

---

## 故障排查

### 常见问题

**1. 无法连接节点**
```bash
# 检查 Tailscale 状态
tailscale status

# 检查防火墙
iptables -L -n | grep tailscale
```

**2. DERP 连接失败**
```bash
# 查看 DERPs 延迟
tailscale netcheck

# 检查 DERP 容器
docker ps | grep tailscale-derp
docker logs tailscale-derp --tail 50
```

**3. SSH 无法登录**
```bash
# 检查 Tailscale SSH 是否启用
tailscale debug prefs | grep -i ssh

# 重新启用 SSH
tailscale up --ssh --force-reauth
```

---

## 相关文档

- **SOP-006**: `standards/sop-006-tailscale-baseline.md` - Tailscale 基线部署标准
- **OpenClaw Gateway**: `memory/docs/tailscale.md`
- **PVE 宿主机**: `memory/kb/projects/pve.md`
- **node-11**: `memory/kb/projects/node-11.md`
- **node-22**: `memory/kb/projects/node-22.md`

---

## 更新历史

- **2026-03-04**: 初始创建，汇总现有 Tailscale 网络配置
