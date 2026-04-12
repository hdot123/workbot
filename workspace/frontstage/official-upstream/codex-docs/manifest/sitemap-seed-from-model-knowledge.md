# Codex 站点地图种子（基于模型既有知识整理）

> 说明：本文件用于给正式站点地图提供第一批结构骨架。
> 状态：属于导航假设与候选栏目，不等于实时核验后的最终结构。

## 候选结构骨架

- homepage-root
  - platform-root
    - docs-root
      - guides-root
      - api-reference
      - codex-root
        - cli
        - workflows
        - permissions
        - configuration
        - troubleshooting
        - release-notes
  - codex-research

## 页面关系表

| parent_section | page_title | source_url | child_pages | remarks |
|---|---|---|---|---|
| homepage-root | OpenAI 官网根入口 | `https://openai.com/` | platform-root, codex-research | 主站与产品公告入口 |
| platform-root | OpenAI Platform 根入口 | `https://platform.openai.com/` | docs-root, api-reference | 平台入口与开发入口候选 |
| docs-root | OpenAI Docs 根入口 | `https://platform.openai.com/docs` | guides-root, codex-root, api-reference | 文档总入口候选 |
| guides-root | Docs Guides 根路径（候选） | `https://platform.openai.com/docs/guides` | codex-root | 指南导航层候选 |
| codex-research | OpenAI Codex 研究页（候选历史入口） | `https://openai.com/index/openai-codex/` | historical-context | 历史/研究入口，不一定是现行主入口 |

## 栏目说明

- `codex-root`：Codex 主入口或主栏目
- `cli`：CLI / 命令行相关内容
- `workflows`：工作流、使用方式、任务流相关内容
- `permissions`：权限、安全、批准策略相关内容
- `configuration`：配置、环境、设置相关内容
- `troubleshooting`：故障排查、错误处理、诊断相关内容
- `release-notes`：更新日志、版本变更、行为变动相关内容

## 使用方式

- 联网核验后，把真实结构写回正式 sitemap 文件。
- 如果发现某些栏目并非独立页面，而是同页分节，也要保留这里的栏目概念，作为覆盖范围标签继续使用。
