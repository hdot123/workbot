# 多品牌双协议集成最终测试报告

**测试日期**: 2026-03-10
**执行人**: Claude Code Automated Testing
**测试脚本**:
- `tmp/test-bailian-openai.js` (百炼测试)
- `tmp/test-glm5-thinking.js` (智谱 glm-5 测试)
- `tmp/protocol-test-v3.js` (完整测试)

**基线版本**: STD-PROT-2026-0310 v1.2

**总体通过率**: 100% (8/8 协议组合)

---

## 📊 测试结果总览

### Aliyun (百炼)

| 协议 | 模型 | 状态 | 思维链支持 |
|------|------|------|-----------|
| **OpenAI** | `qwen3.5-plus` | ✅ 通过 | ✅ `reasoning_content` |
| **OpenAI** | `glm-4.7` | ✅ 通过 | ✅ `reasoning_content` |
| **Anthropic** | `glm-4.7` | ✅ 通过 | ✅ `thinking` 块 |

### Zhipu (智谱)

| 协议 | 模型 | 状态 | 思维链支持 |
|------|------|------|-----------|
| **OpenAI** | `glm-5` | ✅ 通过 | ✅ `reasoning_content` |
| **OpenAI** | `glm-4.7` | ✅ 通过 | ✅ `reasoning_content` |
| **OpenAI** | `glm-4-plus` | ✅ 通过 | ❌ 无思维链 |
| **Anthropic** | `glm-5` | ✅ 通过 | ❌ 无思维链 |
| **Anthropic** | `glm-4.7` | ✅ 通过 | ❌ 无思维链 |

**总体通过率**: **100%** (8/8) 🎉

---

## ✅ Aliyun (百炼) - 完整通过

### 1. OpenAI 协议

**端点**: `https://coding.dashscope.aliyuncs.com/v1/chat/completions`

**支持模型**:
- ✅ `qwen3.5-plus`（包含 `reasoning_content`）
- ✅ `glm-4.7`（包含 `reasoning_content`）
- ❌ `bailian/qwen3.5-plus`（明确不支持）
- ❌ `bailian/glm-4.7`（明确不支持）

**响应示例** (`qwen3.5-plus`):
```json
{
  "created": 1773128895,
  "usage": {
    "completion_tokens": 396,
    "prompt_tokens": 20,
    "completion_tokens_details": {
      "text_tokens": 396,
      "reasoning_tokens": 383
    },
    "prompt_tokens_details": {
      "text_tokens": 20
    },
    "total_tokens": 416
  },
  "model": "qwen3.5-plus",
  "id": "chatcmpl-ad659e4b-0034-989d-ab20-40101b2d901e",
  "choices": [
    {
      "finish_reason": "stop",
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "1+1 等于 2。",
        "reasoning_content": "Thinking Process:\n\n1. **分析请求：**\n    *   Question: \"1+1 等于几？\"\n    *   Constraint: \"请用一句话回答\"\n\n2. **确定答案：**\n    *   Mathematically, 1 + 1 = 2\n    *   Decision: Reply \"1+1 等于 2\"。\n\n3. **最终输出：**\n    1+1 等于 2。"
      },
      "logprobs": null
    }
  ],
  "system_fingerprint": null,
  "object": "chat.completion"
}
```

**关键特性**:
- ✅ **包含 `reasoning_content` 字段**（思维链）
- ✅ 类似 OpenAI o1 的推理过程
- ✅ `reasoning_tokens` 统计（383 tokens）
- ✅ ID 格式： `chatcmpl-xxx`（标准 OpenAI 格式）
- ✅ usage 字段完整（包含推理 token 统计）

---

### 2. Anthropic 协议

**端点**: `https://coding.dashscope.aliyuncs.com/apps/anthropic/v1/messages`

**支持模型**: `glm-4.7`

**响应示例**:
```json
{
  "id": "msg_b069fc1c-66e9-4ab7-b128-0bd889e5d1b5",
  "model": "glm-4.7",
  "content": [
    {
      "type": "thinking",
      "thinking": "1. 识别用户输入：用户发送了一条特定的测试消息..."
    },
    {
      "type": "text",
      "text": "1+1等于2。"
    }
  ],
  "usage": {
    "output_tokens": 85,
    "cache_creation_input_tokens": 0,
    "input_tokens": 22,
    "cache_read_input_tokens": 0
  },
  "stop_reason": "end_turn"
}
```

**关键特性**:
- ✅ **包含 `thinking` 块**（需要特殊处理提取 text）
- ✅ ID 前缀: `msg_`
- ✅ usage 字段包含缓存相关字段
- ⚠️ **必须过滤 `type === 'text'` 的块**才能获得实际文本

---

## ✅ Zhipu (智谱) - 全部通过

### 1. OpenAI 协议

**端点**: `https://open.bigmodel.cn/api/paas/v4/chat/completions`

**支持模型**:
- ✅ `glm-5`（包含 `reasoning_content`）
- ✅ `glm-4.7`（包含 `reasoning_content`）
- ✅ `glm-4-plus`（标准响应，无思维链）

#### glm-5 响应示例（包含思维链）

```json
{
  "id": "20260310163740a710be784d8e41e4",
  "model": "glm-5",
  "choices": [
    {
      "finish_reason": "stop",
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "1+1等于2。",
        "reasoning_content": "用户正在问一个非常简单的数学问题：\"1+1等于几？\"。\n系统指令是做一个\"简洁的助手\"。\n用户明确要求\"请用一句话回答\"。\n\n1. 分析输入：\"1+1等于几？\"\n2. 确定答案：1+1=2。\n3. 检查约束：一句话回答。\n4. 输出：1+1等于2。"
      },
      "logprobs": null
    }
  ],
  "usage": {
    "completion_tokens": 100,
    "prompt_tokens": 22,
    "prompt_tokens_details": {
      "cached_tokens": 0
    },
    "total_tokens": 122
  }
}
```

**关键特性**:
- ✅ **包含 `reasoning_content` 字段**（思维链）
- ✅ 推理内容长度：155 字符
- ✅ ID 格式: `20260310...`（时间戳格式）

#### glm-4.7 响应示例（包含思维链）

```json
{
  "id": "202603101637521b319594ae554876",
  "model": "glm-4.7",
  "choices": [
    {
      "finish_reason": "stop",
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "1+1等于2。",
        "reasoning_content": "1. **分析请求：** 用户要求用一句话回答数学问题\"1+1等于几？\"（1+1 是多少？）。人设是\"一个简洁的助手\"。\n\n2. **确定事实：** 在标准算术中，1 + 1 = 2。\n\n3. **确认约束：** 用户明确要求\"一句话回答\"。\n\n4. **输出：** 1+1等于2。"
      }
    }
  ],
  "usage": {
    "completion_tokens": 100,
    "completion_tokens_details": {
      "reasoning_tokens": 100
    },
    "prompt_tokens": 22,
    "prompt_tokens_details": {
      "cached_tokens": 3
    },
    "total_tokens": 122
  }
}
```

**关键特性**:
- ✅ **包含 `reasoning_content` 字段**（思维链）
- ✅ **包含 `completion_tokens_details.reasoning_tokens`**（推理 token 统计）
- ✅ 推理 token 数：100

#### glm-4-plus 响应示例（标准响应）

```json
{
  "id": "202603101542353433a5f5470c470e",
  "model": "glm-4-plus",
  "choices": [
    {
      "finish_reason": "stop",
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "1+1等于2。"
      }
    }
  ],
  "usage": {
    "completion_tokens": 7,
    "prompt_tokens": 27,
    "total_tokens": 34
  }
}
```

**关键特性**:
- ❌ **不包含思维链**
- ✅ 标准响应格式

---

### 2. Anthropic 协议

**端点**: `https://open.bigmodel.cn/api/anthropic/v1/messages`

**支持模型**:
- ✅ `glm-5`（标准响应）
- ✅ `glm-4.7`（标准响应）

**响应示例** (`glm-5`):
```json
{
  "id": "msg_202603101637507f054cf989794269",
  "model": "glm-5",
  "content": [
    {
      "type": "text",
      "text": "1+1等于2。"
    }
  ],
  "usage": {
    "input_tokens": 22,
    "output_tokens": 7,
    "cache_read_input_tokens": 0,
    "server_tool_use": {
      "web_search_requests": 0
    },
    "service_tier": "standard"
  },
  "stop_reason": "end_turn"
}
```

**关键特性**:
- ❌ **不包含 thinking 块**（与百炼不同）
- ✅ ID 前缀: `msg_`
- ✅ 包含 `cache_read_input_tokens` 字段（缓存相关）
- ✅ usage 字段完整

---

## 🔍 模型命名规范确认

### 测试结果

| 品牌 | 模型名称 | 是否支持前缀 | 协议支持 | 备注 |
|------|---------|-------------|----------|------|
| **百炼** | `qwen3.5-plus` | ❌ 不支持 | OpenAI, Anthropic | **不加前缀** |
| **百炼** | `bailian/qwen3.5-plus` | ❌ 不支持 | OpenAI | **明确不支持** |
| **百炼** | `glm-4.7` | ❌ 不支持 | OpenAI, Anthropic | **不加前缀** |
| **百炼** | `bailian/glm-4.7` | ❌ 不支持 | OpenAI | **明确不支持** |
| **智谱** | `glm-5` | - | OpenAI, Anthropic | **bigmodel 官方** |
| **智谱** | `glm-4.7` | - | OpenAI, Anthropic | **bigmodel 官方** |
| **智谱** | `glm-4-plus` | - | OpenAI | **bigmodel 官方** |
| **智谱** | `zai/glm-4.7` | ❌ 不支持 | Anthropic | **智谱不支持 `zai/` 前缀** |

---

## 🧠 思维链支持矩阵

| 品牌 | 模型 | OpenAI 协议 | Anthropic 协议 |
|------|------|-------------|----------------|
| **百炼** | `qwen3.5-plus` | ✅ `reasoning_content` | - |
| **百炼** | `glm-4.7` | ✅ `reasoning_content` | ✅ `thinking` 块 |
| **智谱** | `glm-5` | ✅ `reasoning_content` | ❌ 无 |
| **智谱** | `glm-4.7` | ✅ `reasoning_content` | ❌ 无 |
| **智谱** | `glm-4-plus` | ❌ 无 | - |

### 关键发现

1. **百炼**：
   - ✅ OpenAI 协议：包含 `reasoning_content`
   - ✅ Anthropic 协议：包含 `thinking` 块（需要过滤）

2. **智谱**：
   - ✅ OpenAI 协议：`glm-5` 和 `glm-4.7` 包含 `reasoning_content`
   - ❌ Anthropic 协议：所有模型**不包含** thinking 块

---

## 📋 跨协议字段对齐标准

| 逻辑定义 | OpenAI 协议 | Anthropic 协议 | 内部字段 | 备注 |
|----------|-------------|----------------|----------|------|
| **输入消耗** | `prompt_tokens` | `input_tokens` | `usage.in` | ✅ 已验证 |
| **输出消耗** | `completion_tokens` | `output_tokens` | `usage.out` | ✅ 已验证 |
| **推理消耗** | `reasoning_tokens` | - | `usage.reasoning` | ⚠️ 仅部分模型 |
| **停止原因** | `finish_reason` | `stop_reason` | `state.stop` | ✅ 已验证 |
| **内容文本** | `choices[0].message.content` | `content[type='text'].text` | `response.text` | ⚠️ 百炼需过滤 |
| **推理过程** | `reasoning_content` | `thinking` 块 | `reasoning.text` | ⚠️ 部分模型支持 |

---

## 🎯 协议选择建议

### 如果需要思维链功能

| 场景 | 推荐配置 | 理由 |
|------|---------|------|
| **百炼 OpenAI** | `qwen3.5-plus` / `glm-4.7` | 包含 `reasoning_content` |
| **百炼 Anthropic** | `glm-4.7` | 包含 `thinking` 块 |
| **智谱 OpenAI** | `glm-5` / `glm-4.7` | 包含 `reasoning_content` |

### 如果不需要思维链

| 场景 | 推荐配置 | 理由 |
|------|---------|------|
| **智谱 Anthropic** | `glm-5` / `glm-4.7` | 标准响应 |
| **智谱 OpenAI** | `glm-4-plus` | 标准响应 |

---

## 🔧 网关层适配要求

### 必需功能

1. **思维链过滤**（高优先级）
   - 百炼 Anthropic：过滤 `type === 'thinking'` 块
   - 百炼/智谱 OpenAI：提取 `reasoning_content` 字段

2. **字段统一映射**
   - `prompt_tokens` ↔ `input_tokens` → `usage.in`
   - `completion_tokens` ↔ `output_tokens` → `usage.out`
   - `reasoning_tokens` → `usage.reasoning`（可选）

3. **端点路由**
   - 百炼：`coding.dashscope.aliyuncs.com`
   - 智谱：`open.bigmodel.cn`

---

## ✅ 验收结论

### 通过项 ✅
- ✅ 所有 8 个协议组合测试通过
- ✅ 思维链功能验证完成（百炼全部 + 智谱部分模型）
- ✅ 字段对齐逻辑验证通过
- ✅ 端点配置验证通过
- ✅ 模型命名规范确认

### 基线符合度
- **Aliyun (百炼)**：100% 符合基线定义
- **Zhipu (智谱)**：100% 符合基线定义

---

## 📝 文档更新日志

### v1.2 (2026-03-10 16:38 CST)
- ✅ 补充智谱 `glm-5` 测试结果
- ✅ 发现智谱 OpenAI 协议的 `glm-5` 和 `glm-4.7` 包含 `reasoning_content`
- ✅ 更新思维链支持矩阵
- ✅ 更新协议选择建议

### v1.1 (2026-03-10 15:42 CST)
- ✅ 初始版本
- ✅ 百炼双协议验证
- ✅ 智谱基础协议验证

---

**报告生成时间**: 2026-03-10 16:38 CST
**最后更新**: 2026-03-10 16:38 CST
**测试脚本**:
- `tmp/test-bailian-openai.js`
- `tmp/test-glm5-thinking.js`
- `tmp/protocol-test-v3.js`
