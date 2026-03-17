# ClawRouter v2.5.4 元数据增强完成报告

**版本**: v2.5.4 (元数据增强版)
**部署日期**: 2026-03-11
**部署地址**: http://192.168.88.27:3000 (内网) / http://100.100.1.27:3000 (Tailscale)
**状态**: ✅ 生产环境运行中

---

## 📋 版本锁定信息

### 核心变更
- **改进点**: `/v1/models` 端点元数据增强
- **重构范围**: 仅 `handleModels` 函数，不涉及路由逻辑
- **向后兼容**: ✅ 完全兼容，不影响现有调用方

### 技术栈
- **Node.js**: v18+
- **Docker**: 29.3.0
- **协议适配**: ProtocolAdapter (自定义)
- **代理**: SOCKS5 (100.100.1.22:7890)

---

## 🎯 元数据增强目标（已完成）

### 1. ✅ 模型 ID 唯一性
- **改进前**: 同一模型在不同协议下重复输出
- **改进后**: 每个模型 ID 只出现一次，用 `supported_protocols` 表达协议支持

### 2. ✅ 双协议能力明确
- **改进前**: 所有模型 `protocol` 字段都写死为 `"openai"`
- **改进后**:
  ```json
  {
    "supported_protocols": ["openai", "anthropic"],
    "routes": {
      "openai": "zai-openai",
      "anthropic": "zai-anthropic"
    }
  }
  ```

### 3. ✅ 能力标签清晰
- **改进前**: 无法区分 chat / embeddings / fast
- **改进后**:
  ```json
  "capabilities": ["chat"]
  "capabilities": ["embeddings"]
  "capabilities": ["chat", "fast", "json_output", "reasoning_filtered"]
  ```

### 4. ✅ Fast 模型元数据完整
- **改进前**: 缺少详细能力说明
- **改进后**:
  ```json
  {
    "id": "glm-4.7-fast",
    "owned_by": "clawrouter-gateway",
    "capabilities": ["chat", "fast", "json_output", "reasoning_filtered"],
    "description": "虚拟模型：自动注入 JSON 输出系统提示，不返回逻辑链内容"
  }
  ```

---

## 📊 最终模型清单（16 个）

### 智谱 GLM 系列（3 个）

| 模型 ID | 品牌 | 协议 | 能力 | 说明 |
|---------|------|------|------|------|
| `glm-5` | zhipu | openai, anthropic | chat | 智谱最新 |
| `glm-4.7` | zhipu | openai, anthropic | chat | 智谱稳定版 |
| `glm-4.7-fast` | zhipu | openai | chat, fast, json_output, reasoning_filtered | JSON 强制输出 |

### 百炼系列（11 个）

| 模型 ID | 品牌 | 协议 | 能力 | 说明 |
|---------|------|------|------|------|
| `glm-5-bailian` | bailian | openai, anthropic | chat | 百炼 GLM-5 |
| `glm-4.7-bailian` | bailian | openai, anthropic | chat | 百炼 GLM-4.7 |
| `qwen3.5-plus` | bailian | openai, anthropic | chat | 百炼 Qwen |
| `qwen3-max-2026-01-23` | bailian | openai, anthropic | chat | 百炼 Qwen-Max |
| `qwen3-coder-next` | bailian | openai, anthropic | chat | 百炼代码 |
| `qwen3-coder-plus` | bailian | openai, anthropic | chat | 百炼代码 Plus |
| `MiniMax-M2.5` | bailian | openai, anthropic | chat | 百炼 MiniMax |
| `kimi-k2.5` | bailian | openai, anthropic | chat | 百炼 Kimi |
| `deepseek-v3.2` | bailian | openai, anthropic | chat | 百炼 DeepSeek |
| `qwen3.5-plus-fast` | bailian | openai | chat, fast, json_output, reasoning_filtered | JSON 强制输出 |

### Voyage 向量系列（3 个）

| 模型 ID | 品牌 | 协议 | 能力 | 说明 |
|---------|------|------|------|------|
| `voyage-4` | voyage | openai | embeddings | 向量模型标准版 |
| `voyage-4-lite` | voyage | openai | embeddings | 向量模型轻量版 |
| `voyage-4-large` | voyage | openai | embeddings | 向量模型大型版 |

---

## 🔧 核心配置

### 路由配置
```javascript
ROUTES = {
  'bailian-openai': { brand: 'bailian', protocol: 'openai', upstreamModel: null },
  'bailian-anthropic': { brand: 'bailian', protocol: 'anthropic', upstreamModel: null },
  'zai-openai': { brand: 'zhipu', protocol: 'openai', upstreamModel: null },
  'zai-anthropic': { brand: 'zhipu', protocol: 'anthropic', upstreamModel: null },
  'voyage-embed': { brand: 'voyage', protocol: 'openai', upstreamModel: null }
}
```

### Fast 模型白名单
```javascript
FAST_MODEL_WHITELIST = ['glm-4.7', 'qwen3.5-plus']
```

### 默认路由
```javascript
DEFAULT_ROUTE = 'bailian-openai'
```

---

## 📝 API 端点

### 模型列表
```bash
GET /v1/models
```

**返回结构**:
```json
{
  "object": "list",
  "data": [
    {
      "object": "model",
      "id": "glm-5",
      "brand": "zhipu",
      "owned_by": "upstream",
      "supported_protocols": ["openai", "anthropic"],
      "capabilities": ["chat"],
      "routes": {
        "openai": "zai-openai",
        "anthropic": "zai-anthropic"
      },
      "upstream_models": {
        "openai": "glm-5",
        "anthropic": "glm-5"
      }
    }
  ],
  "default_route": "bailian-openai",
  "virtual_model_patterns": ["*-fast"],
  "fast_model_whitelist": ["glm-4.7", "qwen3.5-plus"],
  "notes": [
    "聊天模型默认支持双协议：/v1/chat/completions 对应 openai，/v1/messages 对应 anthropic。",
    "embeddings 模型仅用于 /v1/embeddings，不参与双协议。",
    "fast 虚拟模型仅对白名单模型开放，且当前只支持 openai 协议。"
  ]
}
```

### OpenAI 协议端点
```bash
POST /v1/chat/completions
POST /v1/embeddings
```

### Anthropic 协议端点
```bash
POST /v1/messages
```

### 健康检查
```bash
GET /health
```

**返回**:
```json
{
  "ok": true,
  "version": "2.5.4",
  "timestamp": "2026-03-11T15:05:44.610Z",
  "routes": ["bailian-openai", "bailian-anthropic", "zai-openai", "zai-anthropic", "voyage-embed"],
  "features": ["model-aliases", "fast-mode", "reasoning-filter", "socks5-proxy", "embeddings"],
  "fast_models": ["glm-4.7-fast", "qwen3.5-plus-fast"],
  "endpoints": ["/health", "/routes", "/v1/models", "/chat", "/v1/chat/completions", "/v1/messages", "/v1/embeddings"]
}
```

---

## 🔍 使用示例

### 1. 查看所有模型
```bash
curl http://192.168.88.27:3000/v1/models | jq '.data[] | {id, brand, capabilities}'
```

### 2. 查看双协议模型
```bash
curl http://192.168.88.27:3000/v1/models | jq '.data[] | select(.supported_protocols | length > 1)'
```

### 3. 查看 embeddings 模型
```bash
curl http://192.168.88.27:3000/v1/models | jq '.data[] | select(.capabilities | contains(["embeddings"]))'
```

### 4. 查看 fast 模型
```bash
curl http://192.168.88.27:3000/v1/models | jq '.data[] | select(.owned_by == "clawrouter-gateway")'
```

### 5. 调用 OpenAI 协议
```bash
curl -X POST http://192.168.88.27:3000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "glm-5",
    "messages": [{"role": "user", "content": "你好"}]
  }'
```

### 6. 调用 Anthropic 协议
```bash
curl -X POST http://192.168.88.27:3000/v1/messages \
  -H "Content-Type: application/json" \
  -d '{
    "model": "glm-5",
    "messages": [{"role": "user", "content": "你好"}],
    "max_tokens": 1024
  }'
```

---

## 🚀 部署信息

### 服务器信息
- **主机**: 192.168.88.27
- **容器名**: clawrouter
- **镜像**: clawrouter:latest
- **端口映射**: 3000:3000
- **工作目录**: /opt/clawrouter

### 备份文件
- **位置**: /opt/clawrouter/src/server.js.bak.<timestamp>
- **恢复命令**:
  ```bash
  ssh ubuntu@192.168.88.27 "sudo cp /opt/clawrouter/src/server.js.bak.<timestamp> /opt/clawrouter/src/server.js && sudo docker restart clawrouter"
  ```

### 环境变量
- **PORT**: 3000
- **LOG_LEVEL**: info
- **DEFAULT_ROUTE**: bailian-openai
- **FILTER_REASONING**: true
- **OUTBOUND_PROXY**: socks5://100.100.1.22:7890

---

## ✅ 验收标准（全部通过）

1. ✅ **模型 ID 唯一**: 16 个模型，每个 ID 只出现一次
2. ✅ **双协议表达**: 所有 chat 模型显示 `supported_protocols: ["openai", "anthropic"]`
3. ✅ **能力标签**: chat / embeddings / fast 清晰区分
4. ✅ **Fast 模型元数据**: 包含完整 capabilities 和 description
5. ✅ **向后兼容**: 现有调用方无需修改代码
6. ✅ **健康检查**: `/health` 返回正常
7. ✅ **模型列表**: `/v1/models` 返回结构正确

---

## 📚 相关文档

- [ClawRouter v2.6.0 重构计划](./clawrouter-v2.6.0-refactor-plan.md) (已取消，改为元数据增强)
- [百炼 Coding Plan 模型规格表](../memory/kb/reference/bailian-coding-plan-models.md)
- [多品牌协议基线 v1.2](./multi-brand-protocol-baseline-v1.1-final.md)

---

## 📝 更新记录

### 2026-03-11 v2.5.4 元数据增强
- ✅ 重构 `handleModels` 函数
- ✅ 实现模型 ID 唯一性
- ✅ 添加 `supported_protocols` 字段
- ✅ 添加 `capabilities` 字段
- ✅ 添加 `routes` 映射对象
- ✅ 添加 `upstream_models` 映射对象
- ✅ 完善 fast 模型元数据
- ✅ 添加顶层 `notes` 说明
- ✅ 部署到生产环境
- ✅ 验收测试通过

---

## 🎯 下一步计划

### 优先级 1: 监控与优化
- [ ] 添加 Prometheus 监控指标
- [ ] 优化响应过滤性能
- [ ] 添加请求日志记录

### 优先级 2: 功能增强
- [ ] 支持流式响应的 reasoning 过滤
- [ ] 添加模型健康检查
- [ ] 支持自定义系统提示词

### 优先级 3: 文档完善
- [ ] 编写 API 使用指南
- [ ] 编写故障排查手册
- [ ] 编写性能调优指南

---

**版本锁定时间**: 2026-03-11 23:10
**文档状态**: ✅ 最终确认
**负责人**: Claude (Sonnet 4.6)
