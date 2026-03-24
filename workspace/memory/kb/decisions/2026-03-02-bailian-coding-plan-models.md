---
type: [KB:DECISION]
title: "百炼 Coding Plan 模型规格 (2026-03-02)"
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

# 百炼 Coding Plan 模型规格 (2026-03-02)

**来源**: 指挥官提供 / 百炼官方文档
**更新**: 2026-03-02

---

## ⚠️ 重要说明

**百炼 Coding Plan 当前仅可以使用支持的模型列表中的模型，使用其他模型会报错。**

---

## 📊 模型上下文长度

| 模型名称 | 上下文长度 (Tokens) | 备注 |
|----------|-------------------|------|
| **qwen3.5-plus** | **1,000,000** | ✅ 百万级上下文 |
| **qwen3-coder-plus** | **1,000,000** | ✅ 百万级上下文 |
| qwen3-max-2026-01-23 | 262,144 | |
| qwen3-coder-next | 262,144 | |
| kimi-k2.5 | 262,144 | |
| MiniMax-M2.5 | 204,800 | |
| glm-5 | 202,752 | |
| glm-4.7 | 202,752 | |

---

## 📝 超出上下文长度处理

**策略**:
1. **滑动窗口** - 保留最近的对话内容
2. **摘要压缩** - 对早期对话进行摘要
3. **截断** - 超出部分自动丢弃

**OpenClaw 本地管理**:
- 当前会话显示 `Context: 99k/1.0m (10%)` 是 OpenClaw 的本地上下文管理
- 实际模型支持上限参考上表

---

## ✅ 推荐模型

**长上下文需求 (1M)**:
- `bailian/qwen3.5-plus`
- `bailian/qwen3-coder-plus`

**编程任务**:
- `bailian/qwen3-coder-next` (262K)
- `bailian/qwen3-coder-plus` (1M)

**通用任务**:
- `bailian/qwen3.5-plus` (1M)
- `zai/glm-5` (202K)

---

**Source**: 百炼官方文档 / 指挥官确认
