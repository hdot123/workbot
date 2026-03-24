# Empire Logic Map - 技术基线地图

> 最后更新：2026-02-21
> 维护者：Molt (全局指挥官)

---

## 📋 概述

本文件记录 passkills 领地内所有技术组件的逻辑关系和配置基线，确保持续集成中的逻辑一致性。

---

## 🔌 MCP 服务层

### QMD - Markdown 知识库搜索

**位置**：`/Users/busiji/passkills/mcp-hub/qmd/`

**MCP 入口**：`src/mcp.ts`

**环境变量**：

| 变量名 | 用途 | 当前值 |
|--------|------|--------|
| `INDEX_PATH` | 索引数据库路径 | `/Users/busiji/.cache/qmd/index.sqlite` |
| `QMD_BLOCKED_COLLECTIONS` | Collection 黑名单 | `myproject,claw-docs` |
| `QMD_MODEL_DIR` | 模型缓存目录 | `/Users/busiji/.cache/qmd/models` |
| `QMD_LLM_PROVIDER` | LLM 提供商 | `openai` (智谱兼容) |
| `QMD_LLM_BASE_URL` | LLM API 端点 | `https://open.bigmodel.cn/api/paas/v4/` |
| `QMD_LLM_MODEL` | LLM 模型 | `glm-4-flash` |

**Collection 黑名单逻辑**：
- 定义位置：`mcporter.json` → `qmd.env.QMD_BLOCKED_COLLECTIONS`
- 实现位置：`mcp.ts` → `isCollectionAllowed()`, `filterByAllowedCollections()`
- 影响工具：`search`, `vsearch`, `query`, `status`, `resource`
- 行为：黑名单中的 collections 会被排除，不在黑名单的都可以检索

**当前被排除的 Collections**：
| Collection | 状态 | 说明 |
|------------|------|------|
| `myproject` | ❌ 已排除 | Supabase SQL 文件 |
| `claw-docs` | ❌ 已排除 | OpenClaw 官方文档 |

**配置文件**：
- MCP 配置：`/Users/busiji/passkills/mcporter.json`
- 索引配置：`~/.cache/qmd/index.sqlite`

---

## 📁 文件系统层

### 核心配置文件

| 文件 | 位置 | 用途 |
|------|------|------|
| 宪法 | `workspace/00_SUPER_COMMAND_SOP.md` | 最高法则 |
| 身份 | `workspace/IDENTITY.md` | 国王身份验证 |
| 记忆 | `workspace/MEMORY.md` | 长期记忆 |
| 工具 | `workspace/TOOLS.md` | 环境与工具备忘 |
| 心跳 | `workspace/HEARTBEAT.md` | 监控清单 |
| 代理 | `workspace/AGENTS.md` | 皇家内阁配置 |
| 灵魂 | `workspace/SOUL.md` | 灵魂核心 |
| 用户 | `workspace/USER.md` | 人类信息 |

### MCP 配置

| 文件 | 位置 | 用途 |
|------|------|------|
| MCP 服务配置 | `/Users/busiji/passkills/mcporter.json` | MCP 服务定义和环境变量 |
| Gateway 配置 | `/Users/busiji/passkills/openclaw.json` | OpenClaw Gateway 配置 |

---

## 🔄 变更日志

### 2026-02-21 - QMD Collection 黑名单模式

**变更内容**：
- 将 `QMD_ALLOWED_COLLECTIONS`（白名单）改为 `QMD_BLOCKED_COLLECTIONS`（黑名单）
- 修改 `mcp.ts`：逻辑反转，不在黑名单的都可以检索
- 更新 `mcporter.json`：配置黑名单 `myproject,claw-docs`
- 更新 `MEMORY.md`：同步环境变量规范

**变更原因**：
- 指挥官更习惯"排除不需要的"思维方式（黑名单模式）

**影响范围**：
- QMD MCP 服务所有搜索工具
- Resource 访问 (qmd://)

---

## 🔗 依赖关系图

```
mcporter.json (配置)
       │
       ▼
┌──────────────────┐
│  QMD MCP Server  │◄── QMD_ALLOWED_COLLECTIONS
│  (src/mcp.ts)    │
└────────┬─────────┘
         │
    ┌────┴────┐
    ▼         ▼
┌───────┐ ┌───────┐
│search │ │vsearch│ ...
└───────┘ └───────┘
         │
         ▼
    Collection 白名单过滤
         │
         ▼
    返回允许的结果
```

---

*此文档由 Molt 维护，记录 passkills 领地的技术基线。*
