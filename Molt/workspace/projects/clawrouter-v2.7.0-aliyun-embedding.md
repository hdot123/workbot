# ClawRouter v2.7.0 阿里云 Embedding 接入完成报告

**版本**: v2.7.0
**部署日期**: 2026-03-15
**部署地址**: http://192.168.88.27:3000
**状态**: ✅ 生产环境运行中

> **CANONICAL**: `workspace/memory/kb/lessons/aliyun-embedding.md`

---

## 📋 版本锁定信息

### 核心变更
- **新增功能**: 阿里云 Embedding 支持
- **对外模型名**: `aliyun-embedding`
- **对内真实模型**: `text-embedding-v4`
- **向量维度**: 1024
- **重构范围**: `server.js` 中的 `AliyunEmbeddingProvider` 类与 `handleEmbeddings` 函数
- **向后兼容**: ✅ 完全兼容，不影响现有 Voyage 调用

### 技术栈
- **Node.js**: v18+
- **Docker**: 29.3.0
- **协议适配**: OpenAI 兼容格式
- **API 提供方**: 阿里云 DashScope

---

## 🎯 功能说明

### 对外统一入口
- 对外只暴露一个模型名：`aliyun-embedding`
- 对内固定映射到 `text-embedding-v4`
- 不暴露底层真实模型名

### 智能策略选择
按"有效文本条数"自动选择调用模式：

| 有效文本条数 | 调用模式 | 适用场景 |
|:------------:|---------|---------|
| = 1 | Realtime Sync | 在线检索 |
| > 1 | Async Batch | 文档入库 |
| = 0 | 400 错误 | 拒绝无效输入 |

### 无内部 Fallback
- 不做阿里云内部模型降级
- 任何失败都显式返回错误

---

## 📊 支持的 Embedding 模型

| 对外模型名 | 对内真实模型 | 维度 | 用途 |
|-----------|-------------|------|------|
| `aliyun-embedding` | `text-embedding-v4` | 1024 | 阿里云统一入口 |
| `voyage` | `voyage-4` (带 fallback) | 1024 | Voyage 通用入口 |

---

## 🔧 核心配置

### 环境变量

| 变量名 | 说明 | 默认值 | 必需 |
|-------|------|-------|:----:|
| `DASHSCOPE_API_KEY` | 阿里云 API Key | 无 | **是** |
| `DASHSCOPE_EMBEDDING_MODEL` | 内部真实模型 | `text-embedding-v4` | 否 |
| `DASHSCOPE_EMBEDDING_DIMENSION` | 向量维度 | `1024` | 否 |

### Batch 配置（代码内置）

| 参数 | 值 |
|-----|-----|
| 单批最大文本数 | 25 |
| 轮询间隔 | 1000ms |
| 单批超时 | 300000ms (5分钟) |
| UNKNOWN 状态容忍次数 | 5 |

---

## 📝 API 使用方式

### 端点
```
POST /v1/embeddings
```

### 请求格式（OpenAI 兼容）
```json
{
  "model": "aliyun-embedding",
  "input": "字符串或字符串数组"
}
```

### 响应格式（OpenAI 兼容）
```json
{
  "object": "list",
  "data": [{"object": "embedding", "index": 0, "embedding": [...]}],
  "model": "aliyun-embedding",
  "usage": {"prompt_tokens": 10, "total_tokens": 10}
}
```

---

## 🔍 使用示例

### 单条字符串 → Realtime Sync
```bash
curl -s http://192.168.88.27:3000/v1/embeddings \
  -H "Content-Type: application/json" \
  -d '{"model": "aliyun-embedding", "input": "查询文本"}'
```

### 多条数组 → Async Batch
```bash
curl -s http://192.168.88.27:3000/v1/embeddings \
  -H "Content-Type: application/json" \
  -d '{"model": "aliyun-embedding", "input": ["文档1", "文档2", "文档3"]}'
```

### 空输入 → 400 错误
```bash
curl -s http://192.168.88.27:3000/v1/embeddings \
  -H "Content-Type: application/json" \
  -d '{"model": "aliyun-embedding", "input": []}'
# 响应：{"error": "input 为空，请提供字符串或字符串数组"}
```

---

## ✅ 验收标准（全部通过）

1. ✅ 对外模型名统一为 `aliyun-embedding`
2. ✅ 对内真实模型 `text-embedding-v4` 不暴露
3. ✅ 单条有效文本走 realtime sync
4. ✅ 多条有效文本走 async batch
5. ✅ 空输入/全空白输入返回 400
6. ✅ 与 Voyage 并存，互不影响
7. ✅ 无内部 fallback，失败显式报错
8. ✅ `/health` 显示正确配置信息
9. ✅ `/v1/models` 只显示对外模型名

---

## 📚 相关文档

- **知识库 Canonical**: `workspace/memory/kb/lessons/aliyun-embedding.md`
- **多品牌协议基线**: `workspace/memory/kb/global/multi-brand-protocol-baseline.md`
- **ClawRouter 部署指南**: `workspace/memory/kb/global/clawrouter-deployment-guide.md`

---

## 📝 更新记录

| 日期 | 版本 | 变更内容 |
|------|------|----------|
| 2026-03-15 | v2.7.0 | 新增阿里云 Embedding 支持 |

---

**版本锁定时间**: 2026-03-15
**文档状态**: ✅ 最终确认
