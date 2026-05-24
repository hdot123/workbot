---
type: [KB:REFERENCE]
title: "MCP 视觉理解架构"
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

# MCP 视觉理解架构

**更新时间**: 2026-03-02
**来源**: 智谱官方文档 / 指挥官纠正

---

## ⚠️ 重要纠正

### ❌ 错误理解
```
glm-5 (遇到图片)
    ↓ (自动调用)
glm-4.6V (处理图片)
```

### ✅ 正确理解
```
任何模型 (glm-5 / qwen3.5-plus / 其他)
    ↓ (调用 MCP 工具)
MCP Server (视觉理解能力)
    ↓ (底层技术实现)
GLM-4.6V (作为 MCP Server 的底层模型，不直接暴露)
```

---

## 🔧 MCP 视觉工具列表

| 工具名称 | 功能 | 用途 |
|----------|------|------|
| `image_analysis` | 通用图像理解 | 通用图片分析 |
| `extract_text_from_screenshot` | OCR 提取文字 | 截图文字提取 |
| `diagnose_error_screenshot` | 错误截图分析 | 解析错误，给出修复建议 |
| `understand_technical_diagram` | 技术图纸解读 | 架构图、流程图、UML |
| `analyze_data_visualization` | 数据可视化分析 | 仪表盘、统计图表 |
| `ui_to_artifact` | UI 截图转代码 | 生成代码/设计规范 |
| `ui_diff_check` | UI 对比 | 识别视觉差异 |
| `video_analysis` | 视频分析 | MP4/MOV/M4V (最大 8M) |

---

## 📦 MCP Server 配置

**NPM 包**: `@z_ai/mcp-server`

**环境变量**:
| 变量 | 说明 | 默认值 |
|------|------|--------|
| `Z_AI_API_KEY` | 智谱 API KEY | 必需 |
| `Z_AI_MODE` | 服务平台 | ZHIPU |

**安装方式**:
```bash
claude mcp add -s user zai-mcp-server --env Z_AI_API_KEY=your_api_key -- npx -y "@z_ai/mcp-server"
```

---

## 🎯 关键要点

1. **GLM-4.6V 不是独立模型**
   - 它只是 MCP Server 的底层实现
   - 不直接暴露给调用者

2. **任何模型都可以获得视觉能力**
   - 通过调用 MCP 工具
   - 不限于智谱模型

3. **调用链是模型 → MCP 工具 → MCP Server**
   - 不是模型 → 模型

---

## 📚 参考文档

- 官方文档: https://docs.bigmodel.cn/cn/coding-plan/mcp/vision-mcp-server
- NPM 包: https://www.npmjs.com/package/@z_ai/mcp-server

---

**教训**: 2026-03-02 - 之前错误理解了 MCP 视觉处理逻辑，指挥官纠正后记录此文档
