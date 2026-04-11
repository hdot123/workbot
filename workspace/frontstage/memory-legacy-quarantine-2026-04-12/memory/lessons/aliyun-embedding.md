---
type: [KB:LESSON]
title: "阿里云 Embedding 接入经验"
created: 2026-03-15 10:00
updated: 2026-03-15 16:30
source: Manual
confidence: high
tags: [embedding, aliyun, dashscope, clawrouter, provider-integration]
related: [multi-brand-protocol-baseline, clawrouter-deployment-guide]
version: v1.0
status: active
last_verified: 2026-03-15
---

# 阿里云 Embedding 接入经验（Canonical）

> 本文档为 ClawRouter 接入阿里云 Embedding 的可复用经验沉淀。后续类似 provider / embedding 接入应参考此规范。

---

## 一、设计原则

### 1.1 统一入口原则
- **对外只暴露一个模型名**，不暴露底层真实模型
- 底层模型变更不影响调用方
- 调用方无需关心 API 复杂性

### 1.2 智能策略选择
- **按"有效文本条数"判断**，不是按原始 input 类型
- Query 和 Documents 的区别属于**内部执行策略**，不是对外模型差异
- 调用方只需关注业务语义

### 1.3 无隐式降级
- 不做内部 fallback
- 任何失败都显式返回错误
- 调用方可以明确感知并处理异常

---

## 二、模型命名规范

### 2.1 命名对照表

| 层级 | 名称 | 说明 |
|-----|------|------|
| **对外模型名** | `aliyun-embedding` | 调用方在请求中使用的名称 |
| **对内真实模型** | `text-embedding-v4` | API 提供方的真实模型名 |

### 2.2 接口暴露规则

| 接口 | 显示内容 | 原因 |
|-----|---------|------|
| `/v1/models` | 只显示 `aliyun-embedding` | 生产环境调用方只需看到对外名称 |
| `/health` | 显示对外名 + 内部真实名 | 运维调试时需查看底层配置 |

---

## 三、策略选择规则

### 3.1 核心原则

**按"有效文本条数"判断，不是按原始 input 类型判断。**

### 3.2 "有效文本"定义

有效文本需同时满足：
- 类型为 `string`
- `trim()` 后长度 > 0

### 3.3 策略路由表

| 有效文本条数 | 调用模式 | 适用场景 | 特点 |
|:------------:|---------|---------|------|
| = 1 | Realtime Sync | 在线检索 | 低延迟，实时响应 |
| > 1 | Async Batch | 文档入库 | 支持大批量，异步处理 |
| = 0 | 返回 400 错误 | - | 拒绝无效输入 |

### 3.4 输入清洗示例

| 原始 input | 清洗后 | 有效条数 | 策略 |
|-----------|--------|:-------:|------|
| `"查询文本"` | `["查询文本"]` | 1 | realtime |
| `["查询文本"]` | `["查询文本"]` | 1 | realtime |
| `["文档1", "文档2"]` | `["文档1", "文档2"]` | 2 | batch |
| `["有效", "   ", ""]` | `["有效"]` | 1 | realtime |
| `["  ", "", "   "]` | `[]` | 0 | 400 |
| `[]` | `[]` | 0 | 400 |

---

## 四、错误处理规范

### 4.1 错误类型与响应

| 错误场景 | HTTP 状态码 | 错误信息模式 |
|---------|:----------:|-------------|
| 空输入 | 400 | `input 为空，请提供字符串或字符串数组` |
| 全空白输入 | 400 | `没有可用于 embedding 的有效文本（全部为空或空白）` |
| 不支持的模型名 | 400 | `未知的 embedding 模型: xxx` |
| 缺少 API Key | 500 | `DASHSCOPE_API_KEY 未配置` |
| Batch 任务失败 | 500 | `Batch 任务失败 (batch N): 错误详情` |
| Batch 任务取消 | 500 | `Batch 任务被取消 (batch N)` |
| Batch 任务超时 | 500 | `Batch 任务超时: task_id=xxx` |

### 4.2 边界行为

| 场景 | 行为 |
|-----|------|
| 混合有效文本和空白 | 过滤空白，按有效文本条数选择策略 |
| 超长文本 | 自动截断（约 8000 tokens / 16000 字符） |
| 大批量文本（>25条） | 自动分批，每批最多 25 条，顺序处理 |
| Batch 结果顺序 | 按 `text_index` 严格排序 |
| Batch 结果缺少 `text_index` | 显式报错，拒绝该批结果 |

---

## 五、环境变量配置

### 5.1 必需配置

| 变量名 | 说明 | 必需 |
|-------|------|:----:|
| `DASHSCOPE_API_KEY` | 阿里云 DashScope API Key | **是** |

### 5.2 可选配置

| 变量名 | 说明 | 默认值 |
|-------|------|-------|
| `DASHSCOPE_EMBEDDING_MODEL` | 内部真实模型名 | `text-embedding-v4` |
| `DASHSCOPE_EMBEDDING_DIMENSION` | 向量维度 | `1024` |

### 5.3 Batch 轮询配置（代码内置）

| 参数 | 默认值 |
|-----|-------|
| 单批最大文本数 | 25 |
| 轮询间隔 | 1000ms |
| 单批超时时间 | 300000ms (5分钟) |
| UNKNOWN 状态最大容忍次数 | 5 |

---

## 六、API 响应格式

### 6.1 OpenAI 兼容响应

```json
{
  "object": "list",
  "data": [
    {
      "object": "embedding",
      "index": 0,
      "embedding": [0.123, -0.456, ...]
    }
  ],
  "model": "aliyun-embedding",
  "usage": {
    "prompt_tokens": 10,
    "total_tokens": 10
  }
}
```

### 6.2 Usage 字段说明

| 模式 | `prompt_tokens` | 说明 |
|-----|----------------|------|
| Realtime Sync | 真实值 | - |
| Async Batch | 可能为 0 | 上游未返回时为 0，不代表真实消耗为 0 |

---

## 七、与现有 Provider 共存

### 7.1 Voyage 共存规则

| 特性 | aliyun-embedding | voyage |
|-----|-----------------|--------|
| 对外模型名 | `aliyun-embedding` | `voyage` |
| 内部 fallback | 无 | 有（级联） |
| 代理需求 | 无（国内直连） | 需要 SOCKS5 |
| 适用场景 | 国内低延迟、大批量 | 海外模型 |

### 7.2 路由隔离
- 两个 provider 通过 `MODEL_ALIASES` 完全隔离
- 互不影响，可独立升级/替换

---

## 八、可复用检查清单

后续接入新 Embedding Provider 时，确认以下事项：

- [ ] 对外模型名是否统一且不暴露真实模型
- [ ] 是否按"有效文本条数"而非 input 类型判断策略
- [ ] 是否有显式错误处理（无隐式 fallback）
- [ ] 空输入/全空白输入是否返回 400
- [ ] `/v1/models` 是否只显示对外名称
- [ ] `/health` 是否显示完整配置用于调试
- [ ] 是否与现有 provider 隔离共存

---

## 九、实施验证（v2.7.0）

### 9.1 生产环境验收
- **部署地址**: http://192.168.88.27:3000
- **版本**: ClawRouter v2.7.0
- **状态**: ✅ 生产环境运行中
- **验收日期**: 2026-03-15

### 9.2 功能验证结果
- ✅ 对外模型名统一为 `aliyun-embedding`
- ✅ 对内真实模型 `text-embedding-v4` 不暴露
- ✅ 单条有效文本走 realtime sync
- ✅ 多条有效文本走 async batch
- ✅ 空输入/全空白输入返回 400
- ✅ 与 Voyage 并存，互不影响
- ✅ 无内部 fallback，失败显式报错
- ✅ `/health` 显示正确配置信息
- ✅ `/v1/models` 只显示对外模型名

### 9.3 关键文件变更
- `server.js`:
  - 新增 `AliyunEmbeddingProvider` 类
  - 更新 `handleEmbeddings()` 函数
  - 更新 `ROUTES` 和 `MODEL_ALIASES`
  - 更新 `/health` 响应
- `protocol-adapter.js`:
  - 支持 `aliyun` brand

### 9.4 实际遇到的问题与解决

| 问题 | 原因 | 解决方案 |
|-----|------|---------|
| Batch 结果顺序不一致 | 阿里云返回结果未按输入顺序 | 按 `text_index` 严格重排 |
| Usage 字段不准确 | Async Batch 模式上游未返回 `prompt_tokens` | 文档明确说明，返回 0 表示缺失 |
| 空输入进入业务逻辑 | 未校验清洗后有效文本条数 | 增加保护，直接返回 400 |

---

## 十、变更记录

| 日期 | 版本 | 变更内容 |
|------|------|----------|
| 2026-03-15 | v1.0 | 初始版本，沉淀阿里云 Embedding 接入经验 |
| 2026-03-15 | v1.0 | 补充实施验证结果与问题解决 |

---

*文档版本：v1.0*
*更新日期：2026-03-15*
*状态：active*
