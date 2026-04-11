---
type: [KB:LESSON]
title: "Lesson: 配置相关经验"
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

# Lesson: 配置相关经验

## memorySearch 配置
1. **位置**: 应放在 `agents.defaults.memorySearch` 下，而非顶级节点
2. **格式 (阿里云 text-embedding-v4)**:
   ```json
   "memorySearch": {
     "provider": "openai",
     "model": "text-embedding-v4",
     "remote": {
       "baseUrl": "https://dashscope.aliyuncs.com/compatible-mode/v1",
       "apiKey": "${ALIBABA_API_KEY}"
     }
   }
   ```
   - ⚠️ 使用阿里云 text-embedding-v4，不是 Gemini
   - ⚠️ 不要随意改成 "provider": "gemini"

## 环境变量命名
- Google 模型: 使用 `GEMINI_API_KEY`，而非 `GOOGLE_API_KEY`

## API Key 安全
- 绝对禁止在聊天框发送真实的 API Key，会被写入 sessions.jsonl

## 约定优于配置
- 不需要指定 model，系统底层会自动映射最优模型

## SSH 配置
- **Homebrew OpenSSH**: 不支持 macOS 特有的 `UseKeychain` 和 `AddKeysToAgent`
- **Ubuntu 24.04**: SSH 服务名称是 `ssh` 而不是 `sshd`

---
## Metadata
- date: 2026-03-01
- source: MEMORY.full.md
- evidence: "### 配置相关" (标题明确)
- confidence: high
