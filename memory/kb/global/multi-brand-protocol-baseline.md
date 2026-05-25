---
type: [KB:GLOBAL]
title: "多品牌双协议集成技术基线"
created: 2026-03-10 16:38
updated: 2026-03-24 00:00
source: Manual
confidence: high
tags: [protocol, baseline, bailian, zhipu, anthropic, openai, source-material]
related: []
version: v1.5
status: superseded
last_verified: 2026-03-11
---

# 多品牌双协议集成技术基线

> SOURCE MATERIAL ONLY
> 本文件继承自旧项目材料，仅作历史来源，不具备当前默认解释权。

> 它不是 `workbot` 当前正式规范；若与现行 formal canonical 冲突，以当前本地 canonical 和地图裁决为准。

**适用对象**: 所有对接 Aliyun (百炼) / Zhipu (智谱) 的服务节点
**目标**: 让协议集成**永远可控、可追溯、可治理**
**范围**: 本文件只定义"协议规范/字段对齐/端点路由"，具体执行见项目实施文档

---

## 一、协议路径矩阵

| 品牌 | 协议 | Base URL | Endpoint | 思维链 |
|------|------|----------|----------|--------|
| **百炼** | OpenAI | `coding.dashscope.aliyuncs.com` | `/v1/chat/completions` | ✅ |
|  | Anthropic | `coding.dashscope.aliyuncs.com` | `/apps/anthropic/v1/messages` | ✅ |
| **智谱** | OpenAI | `open.bigmodel.cn` | `/api/paas/v4/chat/completions` | ✅ (glm-5/4.7) |
|  | Anthropic | `open.bigmodel.cn` | `/api/anthropic/v1/messages` | ❌ |

---

## 二、模型命名规范

### 平台标识符

| 平台 | 标识符 | 说明 |
|------|--------|------|
| 百炼 | `bailian` | 全称 |
| 智谱 | `zai` | 统一使用 `zai`（其他软件通用） |

### 模型别名规范

**智谱模型**（`zai` 平台）：
- `glm-5` = `glm-5-zai`（向后兼容）
- `glm-4.7` = `glm-4.7-zai`（向后兼容）
- `glm-4-plus`

**百炼模型**（`bailian` 平台）：
- `glm-5-bailian`（明确指定百炼上游）
- `glm-4.7-bailian`（明确指定百炼上游）
- `qwen3.5-plus`（百炼独有，无需后缀）
- `qwen3.5-plus-anthropic`（Anthropic 协议）

> **注意**: 百炼平台的其他品牌模型（MiniMax、kimi、deepseek）无需特殊后缀，默认走百炼路由。

### 百炼平台完整模型列表

| 系列 | 模型 ID | OpenAI 协议 | Anthropic 协议 | 思维链支持 |
|------|---------|-------------|----------------|-----------|
| **通义千问** | `qwen3.5-plus` | ✅ | ✅ | ✅ `reasoning_content` |
|  | `qwen3-max-2026-01-23` | ✅ | ✅ | ✅ `reasoning_content` |
|  | `qwen3-coder-next` | ✅ | ✅ | ✅ `reasoning_content` |
|  | `qwen3-coder-plus` | ✅ | ✅ | ✅ `reasoning_content` |
| **智谱** | `glm-5` | ✅ | ❌ | ✅ `reasoning_content` |
|  | `glm-4.7` | ✅ | ✅ | ✅ `reasoning_content` / `thinking` 块 |
|  | `glm-4-plus` | ✅ | ❌ | ❌ |
| **MiniMax** | `MiniMax-M2.5` | ✅ | ❌ | ❌ |
|  | `MiniMax-M2` | ✅ | ❌ | ❌ |
| **月之暗面** | `kimi-k2.5` | ✅ | ❌ | ❌ |
|  | `kimi-k2` | ✅ | ❌ | ❌ |
| **深度求索** | `deepseek-v3` | ✅ | ❌ | ❌ |

---

## 三、请求头规范

### 通用要求

**所有请求必须添加**:
```http
User-Agent: curl/8.5.0
```

### OpenAI 协议

```http
Authorization: Bearer sk-sp-xxx      # 百炼
Authorization: Bearer xxx.xxx         # 智谱
```

### Anthropic 协议

```http
x-api-key: sk-sp-xxx                  # 百炼
x-api-key: xxx.xxx                    # 智谱
anthropic-version: 2023-06-01
```

---

## 四、响应格式与字段对齐

### OpenAI 协议响应

```json
{
  "id": "chatcmpl-xxx",
  "model": "qwen3.5-plus",
  "choices": [{
    "finish_reason": "stop",
    "message": {
      "content": "回答文本",
      "reasoning_content": "思维链内容"
    }
  }],
  "usage": {
    "prompt_tokens": 20,
    "completion_tokens": 396,
    "completion_tokens_details": {
      "reasoning_tokens": 383
    }
  }
}
```

### Anthropic 协议响应

```json
{
  "id": "msg_xxx",
  "model": "glm-4.7",
  "content": [
    { "type": "thinking", "thinking": "思维链内容" },
    { "type": "text", "text": "回答文本" }
  ],
  "usage": {
    "input_tokens": 22,
    "output_tokens": 85
  },
  "stop_reason": "end_turn"
}
```

### 字段映射表

| 逻辑字段 | OpenAI | Anthropic | 内部映射 |
|----------|--------|-----------|----------|
| 输入 token | `prompt_tokens` | `input_tokens` | `usage.in` |
| 输出 token | `completion_tokens` | `output_tokens` | `usage.out` |
| 推理 token | `reasoning_tokens` | - | `usage.reasoning` |
| 停止原因 | `finish_reason` | `stop_reason` | `state.stop` |
| 文本内容 | `choices[0].message.content` | `content[type='text'].text` | `response.text` |
| 思维链 | `reasoning_content` | `thinking` 块 | `reasoning.text` |

---

## 五、思维链处理逻辑

### OpenAI 协议

```javascript
const message = response.choices[0].message;
const text = message.content;
const reasoning = message.reasoning_content;
```

### Anthropic 协议（百炼）

```javascript
const contentArray = response.content || [];
const textBlock = contentArray.find(block => block.type === 'text');
const thinkingBlock = contentArray.find(block => block.type === 'thinking');

const text = textBlock?.text;
const reasoning = thinkingBlock?.thinking;
```

### 网关层建议

1. **默认过滤思维链**：仅将 `text` 返回给上层应用
2. **可选保留**：将思维链存储至日志/调试系统
3. **统计上报**：将 `reasoning_tokens` 纳入成本统计

---

## 六、协议选择决策树

```
需要思维链？
├─ 是 → 百炼：qwen3.5-plus / qwen3-max / qwen3-coder-* / glm-4.7
│         (OpenAI 或 Anthropic 协议均可)
│      → 智谱：glm-5 / glm-4.7 (仅 OpenAI 协议)
└─ 否 → 任意协议/任意模型
        → MiniMax-M2.5 / MiniMax-M2
        → kimi-k2.5 / kimi-k2
        → deepseek-v3
        → glm-4-plus
```

---

## 七、验收标准

- ✅ 所有协议端点可达（HTTP 200）
- ✅ 思维链正确提取/过滤
- ✅ 字段映射准确无误
- ✅ 模型名称符合规范（无前缀）
- ✅ 请求头包含 `User-Agent: curl/8.5.0`

---

## 八、维护说明

- **API Key 管理**: 必须从环境变量获取，严禁明文写入代码
- **版本控制**: 端点变更时须更新协议矩阵并重新验收
- **思维链处理**: 所有对接百炼的代码必须包含思维链过滤逻辑

---

## 九、相关文档

- **部署文档**: [clawrouter-vm101.md](../projects/clawrouter-vm101.md)
- **node-11 档案**: [node-11.md](../projects/node-11.md) (已迁移)

---

**文档版本**: v1.5
**更新日期**: 2026-03-11
**状态**: active
**维护者**: Claude Code Automated Testing
**ClawRouter 版本**: v2.3.0（支持模型别名）
