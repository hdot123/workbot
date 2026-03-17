---
type: [KB:PROJECT]
title: "Main Project - Operation Nexus V4.1.2"
created: 2026-03-04
updated: 2026-03-08
source: Manual
confidence: high
tags: [nexus, architecture, core]
related: [node-00, node-01, node-11, node-22, pve]
version: v4.1.2
status: active
last_verified: 2026-03-08
---

# Main Project - Operation Nexus V4.1.2

## 基本信息
- **项目名称**: Operation Nexus V4.1.2
- **文档版本**: V4.1.2 (逻辑与软件全锁死版)
- **密级**: 核心机密
- **发布状态**: 已归档 / 正式生效
- **核心指令**: 有状态组件绝对集权，无状态组件受控溢出

## 核心架构

### 命名规范
- **node-0x**: 阿里云 (Aliyun) 节点
- **node-1x**: 本地/局域网 (Local) 节点
- **node-2x**: 腾讯云 (Tencent Cloud) 节点

### 节点角色定义
| 节点 | 角色 | 硬件 | Tailscale IP | 公网 IP | 职责 |
|------|------|------|-------------|---------|------|
| node-01 | 主控/记忆中枢 | 4GB | 100.100.1.9 | 116.62.168.71 | 控制面、持久化数据、核心组件 |
| node-00 | 计算补给站 | 2GB | 100.100.1.5 | 47.111.21.195 | 冷备、计算溢出 |
| node-12 | 待定义 | TBD | 100.100.1.12 | TBD | 新节点(Debian 12) |
| node-13 | 待定义 | TBD | 100.100.1.13 | TBD | 新节点 |

### 强制放置策略
- 有状态锁定: Weaviate、Redis、ArgoCD 必须锁定在 node-01
- 即使 node-01 宕机，禁止自动漂移至 node-00

### 数据库架构 (CHITIN-VAULT)
| 代号 | Supabase ID | 职能 |
|------|-------------|------|
| CHITIN-CORE | sxxrocexjssubvhttwvq | 数据库备份 |
| GAOKAO-PROJECT | axtbgfmitrsflqiwudni | 业务数据、源码逻辑、运行日志 |

## 部署文件位置
- 部署清单: `/Users/busiji/MyProject/xai-legion-manifests/`
- 存储配置: `base/storage/*.yaml`
- 数据库部署: `base/deployment/*.yaml`
- 网络配置: `base/network/k3s-network-config.yaml`

## 待完成任务
- [ ] ConfigMap (应用配置)
- [ ] SealedSecrets (密钥管理)
- [ ] ArgoCD Application (GitOps 配置)
- [ ] 部署文档与 README

---
## Metadata
- date: 2026-03-01
- source: MEMORY.full.md
- evidence: "## Operation Nexus V4.1.2 - xAI 2026 军团全量架构" (标题明确)
- confidence: high
