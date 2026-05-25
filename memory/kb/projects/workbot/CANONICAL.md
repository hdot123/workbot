---
type: "KB:PROJECT"
title: "workbot Project Canonical"
shortname: "workbot"
status: active
created: "2026-05-12"
updated: "2026-05-22"
scope: project
source: local-canonical
confidence: high
tags: [project, education, ai-agent, automation, cmux]
---

# workbot Project Canonical

## 目标

workbot 是一个集成化的 AI 工作空间，包含多个子项目和工具，旨在提供完整的 AI 辅助开发、教育和自动化能力。

核心定位：
- 教育智能化：通过 AEdu 项目实现教育孪生系统
- 工具链整合：通过 opencli 实现网站和应用的 CLI 化
- AI Agent 协作：通过 Claude Code + cmux 实现多 Agent 智能协作
- 知识管理：通过 Obsidian 和共享文档实现知识沉淀
- Webhook 自动化：webhook-ingress 服务处理外部事件

## 仓库

| 位置 | 路径 |
|------|------|
| 本地仓库 | `/Users/busiji/workbot` |
| CI | GitLab CI (.gitlab-ci.yml) |
| GitHub 镜像 | 只读镜像（单向同步） |

## Truth Basis

### Source Refs
- `workspace/INDEX.md`
- `project-map/INDEX.md`

### Authority Refs
- `.memory/CANONICAL.md`
- `AGENTS.md`
- `CLAUDE.md`

### Conflict Status
- `active`

## 项目信息

| 字段 | 值 |
|------|-----|
| 项目名称 | workbot |
| 项目类型 | 多项目集成工作空间（monorepo） |
| 主语言 | Python（后端/工具）、TypeScript/Node.js（SDK/CLI） |
| 创建日期 | 2024 |
| 运行时 | cmux（5+1 拓扑：pm/dev/qa/doc/rea + browser） |

## 子项目

| 子项目 | 路径 | 说明 | 状态 |
|--------|------|------|------|
| AEdu | `AEdu/` | 教育孪生系统（StudentTwinAgent），13 个一级文档目录 | 进行中 |
| webhook-ingress | `tools/webhook_ingress/` | Webhook 入口服务（Python/FastAPI/PostgreSQL） | 活跃 |
| memory-hook | `tools/memory_hook_*` | 多平台记忆钩子系统（Codex/Claude/Factory） | 活跃 |
| Linear SDK | `package/` | @linear/sdk 83.0.0，Linear GraphQL API 客户端 | 稳定 |
| app/models | `app/models/` | 数据模型 | 活跃 |
| safe-1password-mcp | `app/safe-1password-mcp/` | 1Password MCP 安全集成 | 活跃 |

## 编码规范

- Python：pytest 单元测试、类型注解
- TypeScript：ESM + CJS 双格式输出、vitest 测试
- 所有 JSON 文件通过 CI lint 校验
- GitLab CI 门禁：lint → security → validate → test → dry-run

## 架构约束

- cmux 是唯一的正式运行时载体（5+1 拓扑）
- GitLab → GitHub 单向同步（禁止直推 GitHub）
- Phase Git Convention：branch-1（稳定）+ branch-2（任务隔离）
- .claude/agents/ 是项目级 bot 绑定层（pm-bot、dev-bot、qa-bot、doc-bot、rea-bot）
- 全局 bot 本体在 ~/.claude/agents/

## 命名约定

- 测试文件：test_*.py（Python）
- 文档编号：WORKBOT-xxx、STR/KB/TWIN/GRAPH/OBS 等前缀（AEdu）
- 脚本：snake_case.py
- 配置：TOML/YAML

## 工具链

| 工具 | 版本/说明 |
|------|----------|
| Python | 3.x（.venv 虚拟环境） |
| Node.js | >=18.x |
| pytest | 测试框架 |
| vitest | TypeScript 测试框架 |
| cmux | 多 Agent 运行时 |
| GitLab CI | CI/CD 管线 |
| memory-core | 记忆系统（v0.4.0） |
| Linear SDK | v83.0.0（项目管理） |
| opencli | CLI 工具框架 |

## 变更日志

| 日期 | 版本 | 变更内容 |
|------|------|----------|
| 2026-05-12 | 1.0.0 | 初始规范建立 |
| 2026-05-22 | 1.1.0 | 补全 CANONICAL/STATE/NOW 项目信息 |
