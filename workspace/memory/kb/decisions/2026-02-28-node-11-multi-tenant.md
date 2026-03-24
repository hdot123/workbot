---
type: [KB:DECISION]
title: "Decision: node-11 多租客环境部署"
created: 2026-03-04
updated: 2026-03-04
last_verified: 2026-03-04
status: active
tags: []
confidence: high
source: Manual
version: v1.0
related: []
---

# Decision: node-11 多租客环境部署

## 基本信息
- **日期**: 2026-02-28
- **决策**: 在 node-11 上部署 OpenClaw 多租客环境
- **结果**: ✅ 部署完成

## 核心内容
- 部署模式: Mise + PM2 + 多账户共享
- 业务账户: user1, user2, user3
- 端口分配: 18810, 18820, 18830
- 反向代理: Caddy

## 影响
- 验证 Mise 部署方案在受限 CPU 上的可行性
- 建立多租户隔离模式

---
## Metadata
- date: 2026-02-28
- source: MEMORY.full.md
- evidence: "2026-02-28 | node-11多租客环境部署"
- confidence: high
