# Claude Code 站点地图种子（基于模型既有知识整理）

> 说明：本文件用于给正式站点地图提供第一批结构骨架。
> 状态：属于导航假设与候选栏目，不等于实时核验后的最终结构。

## 候选结构骨架

- docs-root
  - docs-en-root
    - claude-code-root
      - installation
      - configuration
      - permissions
      - workflows
      - ide-integration
      - troubleshooting
      - release-notes

## 页面关系表

| parent_section | page_title | source_url | child_pages | remarks |
|---|---|---|---|---|
| docs-root | Anthropic Docs 根入口 | `https://docs.anthropic.com/` | docs-en-root, claude-code-root | 文档总入口候选 |
| docs-en-root | Anthropic Docs 英文根路径（候选） | `https://docs.anthropic.com/en/docs/` | claude-code-root | 英文文档导航层 |
| claude-code-root | Claude Code 文档入口（候选） | `https://docs.anthropic.com/en/docs/claude-code` | installation, configuration, permissions, workflows, ide-integration, troubleshooting, release-notes | 首要栏目根候选 |
| claude-code-root | Claude Code 文档入口（候选） | `https://docs.anthropic.com/en/docs/claude-code` | API / CLI 交叉引用 | 可能与 API 文档交叉 |

## 栏目说明

- `installation`：安装与接入相关内容
- `configuration`：配置、设置、环境相关内容
- `permissions`：权限、安全、沙箱、批准策略相关内容
- `workflows`：常见工作流、操作流程、代理行为相关内容
- `ide-integration`：编辑器与 IDE 集成相关内容
- `troubleshooting`：故障排查、错误处理、诊断相关内容
- `release-notes`：更新日志、版本变更、行为变动相关内容

## 使用方式

- 联网核验后，把真实结构写回正式 sitemap 文件。
- 如果发现某些栏目并非独立页面，而是同页分节，也要保留这里的栏目概念，作为覆盖范围标签继续使用。
