---
type: [KB:DECISION]
title: "4 Bot 协作工作流规划"
created: 2026-03-04
updated: 2026-03-04
last_verified: 2026-03-04
source: Manual
confidence: high
tags: [bot, workflow, gitlab, ci-cd, pmbot, devbot, qabot, docbot]
related: [node-11, node-22, bailian-coding-plan-models]
version: v1.0
status: planning
---

# 4 Bot 协作工作流规划

## 📋 概述

基于 GitLab CE + OpenClaw 的 4 机器人协作工作流，实现需求 → 开发 → 测试 → 文档的自动化流程。

---

## 🔄 工作流程

```
外部 → pmbot（需求澄清+任务拆解+验收标准）
         ↓
      devbot（实现方案+变更点+自测）
         ↓
      qabot（测试报告+缺陷列表+发布结论）
         ↓
      docbot（部署文档+Runbook+Release Notes）
         ↓
      pmbot → 外部（统一对外回复）
```

### 详细流程

1. **外部 → pmbot**: 需求/问题/变更
2. **pmbot 产出**: 需求澄清 + 任务拆解 + 验收标准（Definition of Done）
3. **pmbot → devbot**: 发"开发任务单"
4. **devbot 交付**: 实现方案 / 变更点 / 影响范围 / 自测结果（devbot 指挥自己的 Claude 编码）
5. **pmbot → qabot**: 发"测试任务单"（基于 devbot 交付）
6. **qabot 交付**: 测试报告 / 缺陷列表 / 是否可发布结论（qabot 指挥自己的 Claude 编码）
7. **pmbot → docbot**: 发"文档任务单"
8. **docbot 交付**: 更新后的部署文档/Runbook/Release Notes/FAQ
9. **pmbot → 外部**: 统一对外回复（可附文档链接/摘要）

---

## 🤖 4 Bot 配置

### 模型规划

| Bot | 职责 | 主模型 | 回退模型 | 理由 |
|-----|------|--------|----------|------|
| **pmbot** | 项目管理、需求分析、协调调度 | `bailian/qwen3-max` | → `bailian/glm-5` → `bailian/qwen3.5-plus` | 需要强推理能力，1M上下文处理复杂需求 |
| **devbot** | 开发、编码、自测 | `bailian/coder-next` | → `bailian/coder-plus` → `bailian/qwen3-max` → `bailian/glm-5` | 最新代码模型，适合开发任务 |
| **qabot** | 测试、缺陷分析、发布决策 | `bailian/coder-plus` | → `bailian/coder-next` → `bailian/qwen3-max` → `bailian/glm-4.7` | 稳定代码模型，适合测试任务 |
| **docbot** | 文档、Runbook、Release Notes | `bailian/qwen3.5-plus` | → `bailian/kimi-k2.5` → `bailian/glm-5` | 1M上下文 + 原生视觉，可处理截图 |

### 端口规划

| Bot | 端口 | 用户 | Token | 服务名 |
|-----|------|------|-------|--------|
| **pmbot** | 19020 | pm-bot | `pm-bot-token-19020` | `openclaw-pm-bot.service` |
| **devbot** | 19010 | dev-bot | `dev-bot-token-19010` | `openclaw-dev-bot.service` |
| **qabot** | 19050 | qa-bot | `qa-bot-token-19050` | `openclaw-qa-bot.service` |
| **docbot** | 19080 | doc-bot | `doc-bot-token-19080` | `openclaw-doc-bot.service` |

---

## 🏗️ 架构设计

```
                    ┌─────────────────────────────────────┐
                    │        GitLab CE (新服务器)          │
                    │   代码托管 + CI/CD + Issue + MR      │
                    └──────────────┬──────────────────────┘
                                   │ Webhook / API
          ┌────────────────────────┼────────────────────────┐
          ▼                        ▼                        ▼
    ┌──────────┐            ┌──────────┐            ┌──────────┐
    │  pmbot   │◄──────────►│  devbot  │◄──────────►│  qabot   │
    │ (协调者)  │            │  (开发)   │            │  (测试)   │
    │  :19020  │            │  :19010  │            │  :19050  │
    └────┬─────┘            └──────────┘            └──────────┘
         │                                                  │
         └──────────────────────┬───────────────────────────┘
                                ▼
                          ┌──────────┐
                          │  docbot  │
                          │  (文档)   │
                          │  :19080  │
                          └──────────┘
```

---

## 🖥️ 部署规划

| 服务器 | 位置 | 部署内容 | 状态 |
|--------|------|----------|------|
| **新服务器** | 本地 | GitLab CE + GitLab Runner | 🚚 在路上 |
| **node-11** | 192.168.88.30 | pmbot + devbot + qabot + docbot | ⏳ 待部署 pmbot + docbot |
| **node-22** | 43.167.177.86 | OpenClaw (备用) | ✅ 已部署 |

---

## 🔑 共享配置

### 百炼 API
- **API Key**: `sk-sp-fdf3de2a9f4a4bc4a00cd98052343a8d`
- **API Base URL**: `https://dashscope.aliyuncs.com/compatible-mode/v1`
- **提供商**: bailian

---

## 📝 待办事项

### 新服务器（GitLab CE）
- [ ] 硬件配置确认
- [ ] 系统安装（建议 Ubuntu 24.04）
- [ ] IP 地址分配
- [ ] GitLab CE Docker 部署
- [ ] GitLab Runner 安装
- [ ] 端口配置（HTTP/HTTPS/SSH）

### node-11（4 Bot）
- [x] devbot 部署 ✅
- [x] qabot 部署 ✅
- [ ] pmbot 部署
- [ ] docbot 部署
- [ ] GitLab 集成配置

### 工作流配置
- [ ] GitLab Webhook 配置
- [ ] CI/CD Pipeline 设计
- [ ] Bot 间通信协议
- [ ] 任务单格式定义

---

## 📚 相关文档

- [百炼 Coding Plan 模型规格表](/Users/busiji/passkills/workspace/memory/kb/reference/bailian-coding-plan-models.md)
- [node-11 持续手册](/Users/busiji/passkills/workspace/memory/kb/projects/node-11.md)
- [node-22 东京服务器](/Users/busiji/passkills/workspace/memory/kb/projects/node-22.md)

---

## 🔄 更新历史

- **2026-03-04**: 初始创建，规划 4 Bot 协作工作流
