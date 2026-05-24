---
type: "KB:STATE"
title: "workbot State"
shortname: "workbot"
status: active
updated: "2026-05-22"
---

# workbot State

> 最后更新：2026-05-22
> 更新者：memory-fill

## 项目状态

| 字段 | 值 |
|------|-----|
| 状态 | active |
| 最后更新 | 2026-05-22 |
| 健康度 | green |
| 分支 | main（稳定） |
| memory 版本 | 0.4.0 |

## 上下文摘要

workbot 是一个多项目集成工作空间（monorepo），当前活跃子项目：
- **AEdu**：教育孪生系统，文档驱动开发阶段，含完整文档体系（13 个一级目录）
- **webhook-ingress**：Webhook 入口服务，Python/FastAPI/PostgreSQL，已有完整测试覆盖
- **memory-hook 系统**：跨平台（Factory/Codex/Claude）记忆钩子，核心工具链组件
- **Linear SDK**：@linear/sdk v83.0.0，用于项目管理和脚本（scripts/p2-linear-*.py）
- **cmux 运行时**：5+1 拓扑（pm/dev/qa/doc/rea + browser），多 Agent 协作

## 关键决策

| 日期 | 决策 | 状态 | 备注 |
|------|------|------|------|
| 2026-05-12 | 初始化项目记忆系统 | decided | 首次建立 .memory/ 目录 |
| 2026-03-25 | 确定 cmux 5+1 拓扑为正式运行时 | decided | 见 decisions 目录 |
| 2026-04-20 | Phase Git Convention (branch-1/branch-2) | decided | 任务隔离机制 |

## 当前工作区

- 主分支：main（通过 branch-1/branch-2 隔离任务）
- 运行时：cmux（5+1 拓扑）
- 全局 bot 绑定：pm-bot、dev-bot、qa-bot、doc-bot、rea-bot

## 待处理事项

- [ ] AEdu 核心引擎实现（StudentTwinAgent）
- [ ] webhook-ingress 生产部署
- [ ] memory-hook 跨平台稳定性验证

## 已完成的里程碑

- [x] 2026-05-12：项目记忆系统初始化完成
- [x] webhook-ingress 服务及测试框架建立
- [x] Linear 集成脚本（publish/resume/standardize）
- [x] cmux 运行时协议确立
