# OpenCode 站点地图种子（基于模型既有知识整理）

> 说明：本文件用于给正式站点地图提供第一批结构骨架。
> 状态：属于导航假设与候选栏目，不等于实时核验后的最终结构。

## 候选结构骨架

- homepage-root
  - docs-root
    - installation
    - configuration
    - permissions
    - workflows
    - troubleshooting
    - release-notes
  - github-repo
    - github-owner

## 页面关系表

| parent_section | page_title | source_url | child_pages | remarks |
|---|---|---|---|---|
| homepage-root | OpenCode 官网根入口（候选） | `https://opencode.ai/` | docs-root, github-repo | 主站与产品入口候选 |
| docs-root | OpenCode 文档入口（候选） | `https://opencode.ai/docs` | installation, configuration, permissions, workflows, troubleshooting, release-notes | 文档树根入口候选 |
| github-repo | OpenCode GitHub 仓库（候选） | `https://github.com/sst/opencode` | github-owner | 代码、README、发布记录旁证 |

## 栏目说明

- `installation`：安装与快速开始相关内容
- `configuration`：配置、环境、设置相关内容
- `permissions`：权限、安全、批准策略相关内容
- `workflows`：工作流、常用使用方式相关内容
- `troubleshooting`：故障排查、错误处理、诊断相关内容
- `release-notes`：更新日志、版本变更、行为变动相关内容
