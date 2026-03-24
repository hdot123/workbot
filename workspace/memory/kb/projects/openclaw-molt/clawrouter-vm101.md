---
type: [KB:PROJECT]
title: "ClawRouter (VM 101)"
created: 2026-03-10 21:55
updated: 2026-03-12 13:15
source: Manual
confidence: high
tags: [clawrouter, vm-101, multi-brand-protocol, metadata-enhancement, voyage-proxy, model-fallback]
related:
  - multi-brand-protocol-baseline
  - clawrouter-deployment-guide
  - voyage-proxy-config-2026-03-12
version: v2.5.7
status: active
last_verified: 2026-03-12
---

# ClawRouter (VM 101)

## 基本信息

| 项目 | 值 |
|------|-----|
| **服务器** | VM 101 (clawrouter-01) |
| **IP 地址** | 192.168.88.27 |
| **端口** | 3000 |
| **状态** | ✅ 运行中 |
| **版本** | v2.5.7（模型级 fallback：voyage-4 → voyage-4-lite） |

---

## 端点配置

### 上游端点

| 品牌 | 协议 | 端点 |
|------|------|------|
| 百炼 | OpenAI | `coding.dashscope.aliyuncs.com/v1/chat/completions` |
| 百炼 | Anthropic | `coding.dashscope.aliyuncs.com/apps/anthropic/v1/messages` |
| 智谱 | OpenAI | `open.bigmodel.cn/api/paas/v4/chat/completions` |
| 智谱 | Anthropic | `open.bigmodel.cn/api/anthropic/v1/messages` |

---

## 验收状态

| 端点 | 状态 |
|------|------|
| `GET /health` | ✅ |
| `GET /v1/models` | ✅（v2.5.6: 16 模型 + 元数据增强） |
| `POST /v1/chat/completions` | ✅（过滤 reasoning_content，直连） |
| `POST /v1/completions` | ✅（v2.5.6 新增，OpenClaw 兼容，直连） |
| `POST /v1/chat/completions?stream=true` | ✅（过滤 delta.reasoning_content） |
| `POST /v1/messages` | ✅（过滤 thinking 块，直连） |
| `POST /v1/embeddings` | ✅（Voyage 通过代理 100.100.1.22:1082） |

---

## 代理配置（v2.5.6）

### 智能路由架构

| 模型类型 | 路由策略 | 代理地址 |
|---------|---------|---------|
| **聊天模型**（智谱/百炼） | 直连 | 无 |
| **向量模型**（Voyage） | 通过代理 | `http://100.100.1.22:1082` |

### 代理服务器信息

**节点**: node-22 (Tokyo)
- **物理 IP**: 10.7.0.8
- **Tailscale IP**: 100.100.1.22
- **服务**: gost v3.2.7
- **Voyage 专用端口**: 1082 (HTTP 代理)

**配置文件**: `/etc/gost/gost.yaml` (node-22)
```yaml
- name: "voyage-proxy"
  addr: "100.100.1.22:1082"
  handler:
    type: "http"
  listener:
    type: "tcp"
```

**详细文档**: [voyage-proxy-config-2026-03-12.md](../../../../projects/voyage-proxy-config-2026-03-12.md)

### OpenClaw Embeddings 配置

**正确配置**:
```json
{
  "memorySearch": {
    "provider": "openai",
    "remote": {
      "baseUrl": "http://192.168.88.27:3000/v1",  // ⚠️ 必须包含 /v1
      "apiKey": "${CLAWROUTER_API_KEY}"
    },
    "model": "voyage-4"
  }
}
```

**路径拼接说明**:
- OpenClaw 使用 `provider: "openai"` 会自动添加 `/embeddings`
- 最终请求路径: `{baseUrl}/embeddings` → `/v1/embeddings` ✅

**常见错误**:
| baseUrl 配置 | 最终路径 | 结果 |
|-------------|---------|------|
| `http://192.168.88.27:3000` | `/embeddings` | ❌ 404 |
| `http://192.168.88.27:3000/v1` | `/v1/embeddings` | ✅ 200 |

**故障排查**:
```bash
# ❌ 错误：直接请求 /embeddings
curl -X POST http://192.168.88.27:3000/embeddings \
  -H "Authorization: Bearer ${CLAWROUTER_API_KEY}" \
  -d '{"model":"voyage-4","input":"test"}'
# 返回: {"error":"Not Found","path":"/embeddings"}

# ✅ 正确：请求 /v1/embeddings
curl -X POST http://192.168.88.27:3000/v1/embeddings \
  -H "Authorization: Bearer ${CLAWROUTER_API_KEY}" \
  -d '{"model":"voyage-4","input":"test"}' | jq '.data[0].embedding | length'
# 返回: 1024
```

**代理验证**:
```bash
# 检查 ClawRouter 代理配置
curl -s http://192.168.88.27:3000/health | jq '.proxy'
# 返回: {"voyage":"http://100.100.1.22:1082","chat":"direct (no proxy)"}

# 测试代理连通性（从 ClawRouter VM）
ssh ubuntu@192.168.88.27 'curl -s -m 5 -x http://100.100.1.22:1082 http://www.google.com > /dev/null && echo "proxy_ok" || echo "proxy_fail"'
```

---

## 版本历史

### v2.5.7 (2026-03-12) - 模型级 Fallback
**变更**:
- 实现模型级 fallback 机制（voyage-4 → voyage-4-lite）
- 修改 `handleEmbeddings` 函数支持自动重试
- 新增 `FALLBACK_MAP` 配置对象
- 新增 `[FALLBACK]` 日志标签
- `/health` 端点新增 `fallback` 字段显示配置

**验证**:
- ✅ voyage-4 正常调用测试通过（1024 维嵌入）
- ✅ fallback 日志记录正常
- ✅ 健康端点显示 fallback 配置

**状态**: ✅ 生产环境运行中

### v2.5.6 (2026-03-12) - OpenClaw 兼容 + 智能代理
**变更**:
- 新增 `/v1/completions` 端点（兼容 OpenClaw 的 `openai-completions` API）
- 实现智能代理路由（Chat 直连，Voyage 走代理）
- 新增 `VOYAGE_PROXY` 环境变量配置
- 修改 `makeRequest` 函数支持可选代理参数
- Voyage 向量模型通过 gost 代理访问（100.100.1.22:1082）

**验证**:
- ✅ 聊天模型直连测试通过（qwen3.5-plus）
- ✅ Voyage 向量模型通过代理测试通过（1024 维嵌入）
- ✅ OpenClaw 集成测试通过

**状态**: ✅ 生产环境运行中

### v2.5.4 (2026-03-11) - 元数据增强
**变更**:
- 重构 `handleModels` 函数
- 实现模型 ID 唯一性（每个 ID 只出现一次）
- 新增 `supported_protocols` 字段（双协议能力表达）
- 新增 `capabilities` 字段（chat/embeddings/fast）
- 新增 `routes` 映射对象（协议 → 路由）
- 新增 `upstream_models` 映射对象（协议 → 上游模型）
- 完善 fast 模型元数据（description + capabilities）

**模型清单**: 16 个（14 基础 + 2 fast）

**产出文档**: [clawrouter-v2.5.4-metadata-enhancement-final.md](../../../../projects/clawrouter-v2.5.4-metadata-enhancement-final.md)

**状态**: ✅ 生产环境运行中

### v2.3 (2026-03-11) - 模型别名映射
**变更**:
- 新增 `MODEL_ALIASES` 映射表
- 统一使用 `zai` 标识符
- 新增 `/v1/models` 端点
- 保持向后兼容

**状态**: superseded

---

## 相关文档

- **部署指南**: [clawrouter-deployment-guide.md](../../global/clawrouter-deployment-guide.md)
- **协议基线**: [multi-brand-protocol-baseline.md](../../global/multi-brand-protocol-baseline.md)

---

**最后更新**: 2026-03-12 13:15 (v2.5.7 模型级 Fallback)
