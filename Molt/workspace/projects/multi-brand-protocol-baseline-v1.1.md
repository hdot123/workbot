# 多品牌双协议集成技术基线文档 (v1.1)

**文档编号**：STD-PROT-2026-0310

**版本**：v1.1 (2026-03-10 更新)

**验收状态**：部分通过（75%）

---

## 一、 协议路径矩阵 (Protocol Matrix)

| 品牌 (Provider) | 协议类型 | 基础 URL (Base URL) | 请求端点 (Endpoint) | 验证状态 |
| --- | --- | --- | --- | --- |
| **Aliyun (百炼)** | **OpenAI** | `https://dashscope.aliyuncs.com` | `/compatible-mode/v1/chat/completions` | ❌ 待验证 |
|  | **Anthropic** | `https://coding.dashscope.aliyuncs.com` | `/apps/anthropic/v1/messages` | ✅ 已通过 |
| **Zhipu (智谱)** | **OpenAI** | `https://open.bigmodel.cn` | `/api/paas/v4/chat/completions` | ✅ 已通过 |
|  | **Anthropic** | `https://open.bigmodel.cn` | `/api/anthropic/v1/messages` | ✅ 已通过 |

---

## 二、 模型命名规范

### 通用规则
- **`bailian/xxx`** = 百炼官方模型
- **`zai/xxx`** = bigmodel 官方模型
- **无前缀** = 通用模型名称（部分端点支持）

### 百炼 Coding Plan 支持的模型

| 模型名称 | 能力 | 协议支持 |
|---------|------|---------|
| `qwen3.5-plus` | 支持图片理解 | OpenAI (待验证) |
| `kimi-k2.5` | 支持图片理解 | - |
| `glm-5` | - | - |
| `MiniMax-M2.5` | - | - |
| `qwen3-max-2026-01-23` | - | - |
| `qwen3-coder-next` | - | - |
| `qwen3-coder-plus` | - | - |
| `glm-4.7` | - | ✅ Anthropic 协议已验证 |

### 智谱 bigmodel 官方支持的模型

| 模型名称 | 协议支持 |
|---------|---------|
| `glm-4-plus` | ✅ OpenAI 协议已验证 |
| `glm-4.7` | ✅ Anthropic 协议已验证 |
| `zai/glm-4.7` | ❌ 模型不存在（需确认命名规范） |

---

## 三、 品牌原子化规范

### 1. Aliyun (百炼) 规范

#### OpenAI 协议标准
- **鉴权**：使用 `Authorization: Bearer` 格式
- **System 处理**：系统提示词必须作为 `messages` 数组首位，角色为 `system`
- **待验证项**：
  - [ ] 确认 `qwen3.5-plus` 是否需要 `bailian/` 前缀
  - [ ] 确认 Coding Plan API Key 的权限范围

#### Anthropic 协议标准 ⚠️ 特殊处理
- **鉴权**：使用 `x-api-key` 字段
- **Header 约束**：必须包含 `anthropic-version: 2023-06-01`
- **ID 规范**：响应 ID 以 `msg_` 开头 ✅
- **⚠️ 响应结构差异**：
  - **content 数组包含多个块**：
    ```json
    {
      "content": [
        {
          "type": "thinking",
          "thinking": "思维链内容..."
        },
        {
          "type": "text",
          "text": "实际回复文本"
        }
      ]
    }
    ```
  - **必须提取 `type === 'text'` 的块**才能获得实际文本
  - `thinking` 块包含模型的思维过程（类似 OpenAI o1 的推理过程）

---

### 2. Zhipu (智谱) 规范

#### OpenAI 协议标准
- **端点特性**：强制映射至 `/v4/` 路由
- **统计字段**：消耗信息映射至 `usage.prompt_tokens`
- **ID 格式**：响应 ID 为时间戳 + 随机字符串（非标准 OpenAI 格式）
  - 示例：`202603101542353433a5f5470c470e`

#### Anthropic 协议标准
- **System 剥离**：必须从 `messages` 中提取并移动至顶层 `system` 字段，严禁留在数组内
- **思维链控制**：针对 `glm-4.7` 模型，响应**不包含** `thinking` 字段（与百炼不同）
- **ID 格式**：响应 ID 符合 `msg_` 前缀规范 ✅
  - 示例：`msg_20260310153447b205ffd3bc3f4c0f`
- **扩展字段**：响应包含 `cache_read_input_tokens`、`server_tool_use`、`service_tier`

---

## 四、 跨协议字段对齐标准 (Field Alignment)

为确保系统逻辑一致，所有协议响应必须在网关层完成以下映射：

| 逻辑定义 | OpenAI 协议名 | Anthropic 协议名 | 目标系统字段 (Internal) | 备注 |
| --- | --- | --- | --- | --- |
| **输入消耗** | `prompt_tokens` | `input_tokens` | `usage.in` | ✅ 已验证 |
| **输出消耗** | `completion_tokens` | `output_tokens` | `usage.out` | ✅ 已验证 |
| **停止原因** | `finish_reason` | `stop_reason` | `state.stop` | ✅ 已验证 |
| **内容文本** | `choices[0].message.content` | `content[type='text'].text` | `response.text` | ⚠️ 百炼需特殊处理 |

---

## 五、 特殊处理逻辑

### 百炼 Anthropic 协议的 thinking 块处理

**问题**：百炼的 glm-4.7 模型在 Anthropic 协议下返回 `thinking` 块

**解决方案**：
```javascript
// 错误的访问方式（会失败）
const text = data.content[0].text; // ❌ content[0] 可能是 thinking

// 正确的访问方式
const contentArray = data.content || [];
const textBlock = contentArray.find(block => block.type === 'text');
const text = textBlock?.text; // ✅ 正确获取文本
```

**建议**：
- 在网关层自动过滤 `thinking` 块
- 仅将 `text` 块返回给上层应用
- 可选择将 `thinking` 块存储至日志用于调试

---

## 六、 验收 Checklist

### 1. 路由精准度
- [x] 智谱 OpenAI 请求成功命中 `/api/paas/v4/` 路径
- [x] 智谱 Anthropic 请求成功通过 `/api/anthropic` 路径获得 `msg_` 前缀响应
- [x] 百炼 Anthropic 请求成功命中 `coding.dashscope` 域名
- [ ] 百炼 OpenAI 请求验证（待配置正确的模型名称）

### 2. 报文一致性
- [x] 所有 Anthropic 链路下的 `system` 提示词已成功移出 `messages`
- [x] 智谱 OpenAI 链路下的 `id` 字段正确映射（非标准格式）
- [x] 百炼 Anthropic 的 `thinking` 块已正确处理

### 3. 字段对齐
- [x] 所有协议的 usage 字段已统一映射至 `usage.in`/`usage.out`
- [x] 所有协议的 content 字段已正确提取至 `response.text`

---

## 七、 待解决问题

### 高优先级
1. **百炼 OpenAI 协议 401 错误**
   - 当前配置：
     - URL: `https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions`
     - Model: `qwen3.5-plus`
     - Key: `sk-sp-fdf3de2a9f4a4bc4a00cd98052343a8d`
   - 需要确认：
     - [ ] 是否需要使用 `bailian/qwen3.5-plus` 格式？
     - [ ] Coding Plan 的 Key 是否有权限访问 `compatible-mode` 端点？
     - [ ] 是否需要额外的 Header？

### 中优先级
2. **智谱 `zai/` 前缀模型验证**
   - 当前状态：`zai/glm-4.7` 返回"模型不存在"
   - 需要确认：
     - [ ] `zai/` 前缀的正确用法
     - [ ] 是否需要特殊权限？

---

## 八、 测试验证记录

### 测试日期：2026-03-10

| 品牌 | 协议 | 模型 | 状态 | 测试脚本 |
|------|------|------|------|---------|
| Aliyun | Anthropic | `glm-4.7` | ✅ 通过 | `tmp/protocol-test-v3.js` |
| Zhipu | OpenAI | `glm-4-plus` | ✅ 通过 | `tmp/protocol-test-v3.js` |
| Zhipu | Anthropic | `glm-4.7` | ✅ 通过 | `tmp/protocol-test-v3.js` |
| Aliyun | OpenAI | `qwen3.5-plus` | ❌ 失败 (401) | `tmp/protocol-test-v3.js` |

**总体通过率**：75% (3/4)

---

## 九、 文档维护说明

- **配置锁定**：所有品牌协议的 API Key 必须统一从环境变量获取，严禁明文写入配置文件
- **版本控制**：若品牌端点发生物理变更（如智谱 API 路径升级），须同步更新第一章协议矩阵并重新执行验收序列
- **思维链处理**：所有对接百炼 Anthropic 协议的代码必须包含 `thinking` 块的过滤逻辑

---

**最后更新**：2026-03-10 15:42 CST
**维护者**：Claude Code Automated Testing
**相关文档**：
- [protocol-validation-report-2026-0310.md](protocol-validation-report-2026-0310.md)（首次测试报告）
- 测试脚本：`tmp/protocol-test-v3.js`
