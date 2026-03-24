---
type: [KB:LESSON]
title: "Lesson: QMD 环境变量规范"
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

# Lesson: QMD 环境变量规范

## QMD_BLOCKED_COLLECTIONS

### 用途
设置 QMD MCP 服务的 collection 黑名单（被排除的不会检索）

### 格式
逗号分隔的 collection 名称列表

### 示例配置 (mcporter.json)
```json
"env": {
  "QMD_BLOCKED_COLLECTIONS": "myproject,claw-docs"
}
```

### 行为说明
- 未设置或为空: 允许访问所有 collections
- 设置后: 黑名单中的 collections 会被排除

### 当前配置
| Collection | 是否检索 | 说明 |
|------------|---------|------|
| passskills_main | ✅ 检索 | passkills 主目录 |
| daily-logs | ✅ 检索 | 日记 |
| workspace-memory | ✅ 检索 | 工作记忆 |
| myproject | ❌ 已排除 | Supabase SQL 文件 |
| claw-docs | ❌ 已排除 | OpenClaw 官方文档 |

### 源码位置
`/Users/busiji/passkills/mcp-hub/qmd/src/mcp.ts`

---
## Metadata
- date: 2026-03-01
- source: MEMORY.full.md
- evidence: "## QMD 环境变量规范" (标题明确)
- confidence: high
