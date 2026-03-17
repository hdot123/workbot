# 多品牌双协议集成验证报告

**测试日期**: 2026-03-10
**基线版本**: STD-PROT-2026-0310 v1.0
**执行人**: Claude Code Automated Testing

---

## 📊 测试总览

| 品牌 | 协议 | 状态 | 关键发现 |
|------|------|------|---------|
| **Zhipu (智谱)** | OpenAI | ✅ 通过 | 所有字段验证通过 |
| **Zhipu (智谱)** | Anthropic | ✅ 通过 | ID 前缀符合 `msg_` 规范 |
| **Aliyun (百炼)** | OpenAI | ❌ 失败 | API Key 认证失败 (401) |
| **Aliyun (百炼)** | Anthropic | ❌ 失败 | 模型名称不支持 (400) |

**总体通过率**: 50% (2/4)

---

## ✅ Zhipu (智谱) - 验证通过

### 1. OpenAI 协议测试

**端点**: `https://open.bigmodel.cn/api/paas/v4/chat/completions`
**模型**: `glm-4-plus`

#### 响应结构验证
```json
{
  "hasChoices": true,
  "hasMessage": true,
  "hasContent": true,
  "hasUsage": true,
  "hasPromptTokens": true,
  "hasCompletionTokens": true,
  "responseId": "2026031015344695376559bacf4c6f"
}
```

**字段对齐验证**:
- ✅ `choices[0].message.content` 存在 → 映射至 `response.text`
- ✅ `usage.prompt_tokens` = 27 → 映射至 `usage.in`
- ✅ `usage.completion_tokens` = 7 → 映射至 `usage.out`
- ✅ ID 格式：时间戳 + 随机字符串（非 OpenAI 标准 `chatcmpl-` 前缀）

**实际响应**:
```json
{
  "id": "2026031015344695376559bacf4c6f",
  "content": "1+1等于2。",
  "usage": {
    "completion_tokens": 7,
    "prompt_tokens": 27,
    "total_tokens": 34
  }
}
```

---

### 2. Anthropic 协议测试

**端点**: `https://open.bigmodel.cn/api/anthropic/v1/messages`
**模型**: `glm-4.7`

#### 响应结构验证
```json
{
  "hasId": true,
  "idPrefix": true,
  "hasContent": true,
  "hasText": true,
  "hasUsage": true,
  "hasInputTokens": true,
  "hasOutputTokens": true,
  "hasStopReason": true
}
```

**字段对齐验证**:
- ✅ `id` = `msg_20260310153447b205ffd3bc3f4c0f` → 符合 `msg_` 前缀规范
- ✅ `content[0].text` 存在 → 映射至 `response.text`
- ✅ `usage.input_tokens` = 22 → 映射至 `usage.in`
- ✅ `usage.output_tokens` = 12 → 映射至 `usage.out`
- ✅ `stop_reason` = `end_turn` → 映射至 `state.stop`

**实际响应**:
```json
{
  "id": "msg_20260310153447b205ffd3bc3f4c0f",
  "content": "在标准算术中，1+1等于2。",
  "usage": {
    "input_tokens": 22,
    "output_tokens": 12,
    "cache_read_input_tokens": 0,
    "server_tool_use": {
      "web_search_requests": 0
    },
    "service_tier": "standard"
  },
  "stop_reason": "end_turn"
}
```

**基线符合性**:
- ✅ System 提示词在顶层（未在 messages 数组内）
- ✅ 响应 ID 符合 `msg_` 前缀规范
- ✅ 所有必需字段完整

---

## ❌ Aliyun (百炼) - 验证失败

### 1. OpenAI 协议测试失败

**错误代码**: `401 Unauthorized`
**错误信息**: `invalid_api_key`

```json
{
  "error": {
    "message": "Incorrect API key provided. For details, see: https://help.aliyun.com/zh/model-studio/error-code#apikey-error",
    "type": "invalid_request_error",
    "param": null,
    "code": "invalid_api_key"
  },
  "request_id": "defd28a0-5bf9-9032-9ed7-ce29a5dc0916"
}
```

**诊断**:
- 🔍 API Key 格式：`sk-sp-fdf3de2a9f4a4bc4a00cd98052343a8d`
- 🔍 可能原因：
  1. Key 已过期或被撤销
  2. Key 权限不足（需要 Model Studio 权限）
  3. Key 格式不符合百炼规范（可能需要 `sk-` 开头的不同格式）

**建议**:
- [ ] 检查百炼控制台 Key 状态
- [ ] 确认 Key 是否有 `qwen-plus` 模型的调用权限
- [ ] 验证 Key 是否需要额外的 Header（如 `X-DashScope-SSE`）

---

### 2. Anthropic 协议测试失败

**错误代码**: `400 Bad Request`
**错误信息**: `model is not supported`

```json
{
  "error": {
    "code": "invalid_parameter_error",
    "message": "model `claude-3-5-sonnet-20241022` is not supported.",
    "param": null,
    "type": "invalid_request_error"
  },
  "request_id": "7782b251-1161-9ac5-9c30-aa1f8e27e96d"
}
```

**诊断**:
- 🔍 使用的模型：`claude-3-5-sonnet-20241022`
- 🔍 百炼 Coding Plan 可能支持的模型列表未知

**建议**:
- [ ] 查询百炼 Coding Plan 支持的 Anthropic 模型列表
- [ ] 尝试使用 `claude-3-sonnet-20240229` 或其他版本
- [ ] 联系阿里云确认 Coding Plan 的模型支持范围

---

## 🔍 基线文档修正建议

基于测试结果，建议对 **STD-PROT-2026-0310** 进行以下补充：

### 1. Zhipu (智谱) 补充信息

```markdown
### 2. Zhipu (智谱) 规范

* **OpenAI 协议标准**：
  * **端点特性**：强制映射至 `/v4/` 路由
  * **统计字段**：消耗信息映射至 `usage.prompt_tokens`
  * **ID 格式**：响应 ID 为时间戳 + 随机字符串（非标准 OpenAI 格式）

* **Anthropic 协议标准**：
  * **System 剥离**：必须从 `messages` 中提取并移动至顶层 `system` 字段
  * **思维链控制**：针对 `glm-4.7` 模型，响应解析逻辑必须适配 `thinking` 字段
  * **ID 格式**：响应 ID 符合 `msg_` 前缀规范
  * **扩展字段**：响应包含 `cache_read_input_tokens`、`server_tool_use`、`service_tier`
```

### 2. Aliyun (百炼) 待确认项

需要在基线文档中补充：
- [ ] **模型列表**：Coding Plan 支持的具体 Anthropic 模型名称
- [ ] **Key 格式**：确认 API Key 的标准格式和权限范围
- [ ] **额外 Header**：是否需要特殊的鉴权 Header

---

## 📋 下一步行动

### 立即行动
1. **获取正确的百炼配置**：
   - 确认有效的 API Key
   - 获取支持的 Anthropic 模型列表

2. **补充测试**：
   - 测试百炼 OpenAI 协议的正确模型名称
   - 验证百炼 Anthropic 协议的模型可用性

### 基线文档更新
3. **更新 STD-PROT-2026-0310**：
   - 添加 Zhipu 的 ID 格式说明
   - 补充 Aliyun 的模型列表（待确认后）
   - 添加测试验证结果引用

---

## 🎯 验收结论

### 通过项 ✅
- Zhipu OpenAI 协议：完全符合基线规范
- Zhipu Anthropic 协议：完全符合基线规范

### 待定项 ⏸️
- Aliyun OpenAI 协议：需更换有效 API Key
- Aliyun Anthropic 协议：需确认支持的模型列表

### 基线符合度
- **Zhipu (智谱)**：100% 符合基线定义
- **Aliyun (百炼)**：待验证（配置问题）

---

**报告生成时间**: 2026-03-10 15:34:47 CST
**测试脚本**: `/Users/busiji/passkills/tmp/protocol-test.js`
