---
type: [KB:LESSON]
title: "Lesson: workspace/memory/docs/ 的不可移动性"
created: 2026-03-05 03:15
updated: 2026-03-05 03:15
last_verified: 2026-03-05
status: active
tags: [memory, memorySearch, docs, critical]
confidence: high
source: Incident
version: v1.0
related: []
---

# Lesson: workspace/memory/docs/ 的不可移动性

## 事件背景

2026-03-05，在执行 MRD v2.1.2 规范迁移时，错误地将 `workspace/memory/docs/` 目录（245 个 OpenClaw 官方文档）移动到 `archive-memory/raw/openclaw-docs/`。

**错误原因**：误以为 `docs/` 只是「外部文档副本」，可以归档。

## 核心教训

### 1. `docs/` 是 memorySearch 的检索目标

`workspace/memory/docs/` 不是「随便放的文档」，而是 **OpenClaw memorySearch 功能的核心检索目标**。

```json
// openclaw.json 配置
"agents": {
  "defaults": {
    "workspace": "/Users/busiji/passkills/workspace",
    "memorySearch": {
      "provider": "openai",
      "model": "text-embedding-v4"
    }
  }
}
```

**memorySearch 只检索 `workspace/memory/` 目录**：
- `workspace/memory/docs/` - 官方文档（检索目标 1）
- `workspace/memory/log/` - 每日流水（检索目标 2）
- `workspace/memory/kb/` - 用户知识（检索目标 3）

### 2. 移动 docs/ 会破坏的功能

| 功能 | 影响 |
|------|------|
| 语义检索（embeddings） | ❌ 245 个官方文档无法被检索 |
| 全文检索（FTS5） | ❌ 索引重建时丢失官方文档 |
| 离线查询 | ❌ 无法离线查询官方文档 |

### 3. MRD v2.1.2 的精确定义

```
✅ 必须：workspace/memory/docs/** + workspace/memory/kb/**
```

这个定义不是随意的 —— 它是 **memorySearch 的检索范围**！

## 正确理解

### docs/ 存在的根本原因

> **让 memorySearch 能对官方文档进行语义检索（embeddings + FTS5），实现离线优先的知识查询。**

### 检索分离设计

| 目录 | 检索用途 | 写入权限 |
|------|---------|---------|
| `docs/` | 官方文档全文检索 | 只读（外部更新） |
| `kb/` | 用户知识检索 | read-first-CRUD |
| `archive-memory/` | **永不检索** | 归档写入 |

## 相关架构

### 官方文档路径关系

```
/Users/busiji/claw-docs/              # 真实的官方文档源（245 个文件）
        │
        └─复制→ workspace/memory/docs/  # memorySearch 检索目标（必须在 workspace 内）
```

**为什么需要复制而不是软链接？**
- memorySearch 检索的是 `workspace/memory/docs/**`
- 软链接可能导致路径解析问题
- 物理复制确保检索稳定性

**更新流程**：
```bash
# 从 claw-docs 更新到 workspace/memory/docs/
rm -rf workspace/memory/docs
cp -r /Users/busiji/claw-docs workspace/memory/docs
```

根据官方文档 `memory.md`：

```
~/.openclaw/workspace/
  ├── memory/
  │   ├── docs/                # 官方文档副本（检索目标）
  │   ├── log/                 # 每日流水
  │   └── kb/                  # 用户知识
  └── .memory/
      └── index.sqlite         # 派生索引（FTS5 + embeddings）
```

**派生索引永远可以从 Markdown 重建**，但前提是 Markdown 文件在正确位置。

## 修复记录

- **发现时间**：2026-03-05 03:05
- **修复时间**：2026-03-05 03:10
- **修复操作**：`mv archive-memory/raw/openclaw-docs/* workspace/memory/docs/`
- **状态**：✅ 已恢复

## 行动准则

### 移动任何目录前必须检查

1. **读取 MRD 规范** - 理解每个位置的用途
2. **检查 memorySearch 配置** - 确认检索范围
3. **理解功能依赖** - 移动会破坏什么
4. **先问后动** - 不确定时询问用户

### 永不移动的目录

- ❌ `workspace/memory/docs/` - memorySearch 检索目标
- ❌ `workspace/memory/kb/` - memorySearch 检索目标
- ❌ `workspace/memory/log/` - memorySearch 检索目标

### 可以归档的目录

- ✅ `archive-memory/raw/` - 冷存储，永不检索
- ✅ `standards/` 根目录 - 历史文档（已有 KB 替代）

---

## 一句话总结

> **`workspace/memory/docs/` 是 memorySearch 的离线向量检索知识库，移动它会破坏语义检索功能。**
