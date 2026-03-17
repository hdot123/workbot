---
type: [KB:LESSON]
title: "Lesson: Git 安全边界"
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

# Lesson: Git 安全边界

## 必须排除的敏感文件
- `agents/**/sessions/sessions.json` - 会话令牌、对话历史、敏感配置
- `devices/paired.json` - 设备配对信息、加密密钥

## 正确的 .gitignore 配置
```gitignore
# Security - Runtime state and tokens
agents/**/sessions/
devices/paired.json

# Security - OpenClaw runtime caches
agents/**/models.json
agents/**/auth-profiles.json
agents/**/auth.json
```

## OpenClaw 运行时缓存文件安全
- OpenClaw 会将环境变量解析并写入运行时缓存文件
- 例如: `${ZHIPU_API_KEY}` → 实际值
- 如果提交到 Git，会导致 API Key 泄露

## 安全事件处理流程
1. 发现泄露: `git log --all --full-history -- <file>`
2. 更新 .gitignore
3. 取消跟踪: `git rm --cached <file>`
4. 提交变更
5. **轮换 API Key**

## 核心原则
- **运行时状态** (`sessions/`, `devices/`) 与 **源码配置** 应该严格隔离
- **运行时缓存 ≠ 源码配置** - 运行时生成的文件不应该被提交
- 定期审查 Git 状态，防止敏感信息泄露

---
## Metadata
- date: 2026-03-01
- source: MEMORY.full.md
- evidence: "### Git 相关" (标题明确)
- confidence: high
