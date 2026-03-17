---
type: [KB:PROJECT]
title: "node-11 持续手册"
created: 2026-03-02 14:40
updated: 2026-03-10 18:38
source: Manual
confidence: high
tags: [node-11, alpine, clawrouter, blockrun, openclaw, lxc, deprecated]
related: [ct110, pve, tailscale-network]
version: v1.2
status: superseded
last_verified: 2026-03-10
superseded_by: workspace/memory/kb/global/clawrouter-deployment-guide.md
---

# node-11 持续手册

## 📋 基本信息

- **主机名**: node-11
- **IP 地址**: 192.168.88.29（局域网）/ 100.100.1.11（Tailscale）
- **系统**: Alpine Linux v3.22.0
- **用途**: ClawRouter LLM 路由服务、PVE LXC 容器
- **Node.js 版本**: v22.22.0
- **容器类型**: LXC（PVE 宿主机）

> ⚠️ **注意**: 之前的 Ubuntu 多租户配置 (192.168.88.30) 已 superseded，当前为 Alpine LXC 容器。

---

## 🌐 服务配置

### ClawRouter (BlockRun LLM Router)
- **端口**: 3000
- **服务名**: clawrouter (OpenRC)
- **访问**: http://192.168.88.29:3000
- **健康检查**: `GET /health` → `{"ok":true}`
- **Chat API**: `POST /chat` (JSON: `{"message": "...", "profile": "auto"}`)
- **支付方式**: x402/USDC on Base

### 支持的 Routing Profiles
| Profile | 说明 | 适用场景 |
|---------|------|----------|
| `free` | NVIDIA 免费模型 | 测试、简单查询 |
| `eco` | 预算优化 | 成本敏感场景 |
| `auto` | 智能路由（默认） | 通用 |
| `premium` | 最高质量 | 关键任务 |

---

## 🔑 账号与密钥

### BlockRun 钱包
- **环境变量**: `BASE_CHAIN_WALLET_KEY`
- **私钥**: `0x0e2e450a5f1f464fa12f775b8b821b0c19e1f4dc70472d1a45f647e5fcc40da3`
- **⚠️ 重要**: 需在 Base 链充值 USDC 才能调用 API
- **监控地址**: https://basescan.org/address/<wallet_address>

### SSH 访问
- **Host**: node-11 或 192.168.88.29
- **User**: root
- **Tailscale IP**: 100.100.1.11

---

## 📂 目录结构

### ClawRouter
- **代码目录**: `/opt/clawrouter-server/`
- **配置文件**: `/opt/clawrouter-server/.env`
- **服务脚本**: `/etc/init.d/clawrouter`
- **日志文件**: `/var/log/clawrouter.log`

---

## 🚀 常用命令

### 服务管理 (OpenRC)
```bash
# 查看状态
rc-service clawrouter status

# 启动/停止/重启
rc-service clawrouter start
rc-service clawrouter stop
rc-service clawrouter restart

# 查看日志
cat /var/log/clawrouter.log
tail -f /var/log/clawrouter.log
```

### 验证测试
```bash
# 健康检查
curl http://192.168.88.29:3000/health

# Chat API 测试
curl -X POST http://192.168.88.29:3000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello!", "profile": "auto"}'

# 检查端口
netstat -tlnp | grep 3000
```

---

## ✅ 验证方式

### 健康检查
1. **服务状态**: `rc-service clawrouter status` → started
2. **端口监听**: `netstat -tlnp | grep 3000` → LISTEN
3. **HTTP 访问**: `curl http://192.168.88.29:3000/health` → `{"ok":true}`

### 故障排查
1. **服务无法启动**: 检查 `/var/log/clawrouter.log`
2. **API 调用失败**: 检查钱包 USDC 余额
3. **支付错误**: 确认 Base 链网络正常

---

## 📚 相关文档

- **Tailscale 网络配置**: `workspace/memory/kb/reference/tailscale-network.md`
- **PVE 宿主机**: `workspace/memory/kb/projects/pve.md`
- **CT110 容器**: `workspace/memory/kb/projects/ct110.md`
- **BlockRun SDK**: https://github.com/BlockRunAI/blockrun-llm-ts

---

## ⚠️ 迁移声明

**本节点上的 ClawRouter 服务已于 2026-03-10 迁移至新服务器（Docker VM）。**

- **迁移日期**: 2026-03-10 18:38
- **新服务文档**: `workspace/memory/kb/global/clawrouter-deployment-guide.md`
- **备份文件**: `tmp/clawrouter-backup-20260310.tar.gz` (19MB)
- **新服务位置**: VM 101 (clawrouter-01)
- **协议升级**: 已集成多品牌协议基线 v1.2

**旧服务状态**: 已删除

---

## 🔄 更新历史

- **2026-03-10 18:38**: ClawRouter 服务迁移至 Docker VM，集成多品牌协议基线，旧服务删除
- **2026-03-08 18:00**: 重构为 Alpine LXC + ClawRouter 部署，旧 Ubuntu 配置 superseded
- **2026-03-02 14:40**: 初始创建，记录 Ubuntu 多租户 OpenClaw 配置
