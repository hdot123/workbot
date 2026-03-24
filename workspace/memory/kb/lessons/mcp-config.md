---
type: [KB:LESSON]
title: "Lesson: MCP 配置规范"
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

# Lesson: MCP 配置规范

## 核心原则
- 本地文件系统桥接 MCP 是冗余的，原生工具 (read/write/edit) 功能更强大
- QMD 黑名单模式: 使用 `QMD_BLOCKED_COLLECTIONS` 而非白名单

## 服务分类

### 应该保留 (enabled: true)
- 云数据库: Supabase, PostgreSQL
- 计算引擎: QMD (语义搜索)
- 外部 API: 智谱联网检索
- 运维工具: 自动化脚本执行器

### 应该禁用 (enabled: false)
- 本地文件系统桥接: gaokao-files, planning-with-files, claw-docs 等
- 原因: 原生工具功能更强大、更高效

## 推荐工具
- **web-search-prime**: 联网搜索 (稳定、快速 3-4秒)
- **zread**: GitHub 仓库分析 (稳定 4-6秒)
- **原生 image**: OCR 任务 (稳定 ~3秒)

## 不推荐
- **zai-mcp-server 视觉识别**: 不稳定，经常超时 (60秒+)

---

## mcporter CLI 配置路径问题

### 问题描述
mcporter CLI 默认寻找 `./config/mcporter.json`，而不是 `./mcporter.json`。

### 解决方案：创建符号链接

```bash
# 在 passkills 目录下创建 config 目录
mkdir -p config

# 创建符号链接
ln -sf ../mcporter.json config/mcporter.json

# 验证
mcporter list
```

### 符号链接原理

```
/Users/busiji/passkills/
├── mcporter.json          ← 实际配置文件
└── config/
    └── mcporter.json      ← 符号链接（指向 ../mcporter.json）
```

### 为什么用符号链接而不是复制文件？

| 方式 | 优点 | 缺点 |
|------|------|------|
| **符号链接** | 修改原文件自动生效，无需维护两份文件 | 需要理解符号链接概念 |
| **复制文件** | 简单直接 | 修改原文件后需要重新复制 |

### 验证结果

```bash
mcporter list
# 输出: 12 servers (11 healthy; 1 offline)
```

### 经验总结

- mcporter CLI 默认配置路径：`./config/mcporter.json`
- 使用符号链接可以保持配置文件的单一来源
- 避免维护多份配置文件，减少出错可能

---
## Metadata
- date: 2026-03-01
- source: MEMORY.full.md
- evidence: "### MCP 相关" (标题明确)
- confidence: high
- updated: 2026-03-02 (添加 mcporter CLI 配置路径经验)
