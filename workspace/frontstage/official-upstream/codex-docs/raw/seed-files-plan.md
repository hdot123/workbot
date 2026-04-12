# Codex 第一批原始文件落盘计划

> 说明：本文件用于把第一批建议进入 `raw/` 的文件名和来源关系先固定下来。
> 状态：文件名基于当前既有知识设计，后续可根据真实页面标题微调，但建议保留稳定编号与日期前缀。

## 第一批建议落盘文件

| file_id | planned_filename | source_seed_id | candidate_url | purpose | priority | status | notes |
|---|---|---|---|---|---|---|---|
| raw-plan-001 | `2026-04-12-docs-root.md` | codex-seed-page-001 | `https://platform.openai.com/docs` | 固定文档树根入口 | P0 | planned | 用于向下展开栏目 |
| raw-plan-002 | `2026-04-12-platform-root.md` | codex-seed-page-002 | `https://platform.openai.com/` | 固定平台根入口 | P0 | planned | 平台与文档旁证入口 |
| raw-plan-003 | `2026-04-12-codex-research.md` | codex-seed-page-003 | `https://openai.com/index/openai-codex/` | 固定历史/研究上下文页 | P1 | planned | 不一定是现行主入口 |
| raw-plan-004 | `2026-04-12-api-reference.md` | codex-seed-page-004 | `https://platform.openai.com/docs/api-reference` | 固定 API 旁证页 | P1 | planned | 用于判断 Codex 与 API 关系 |
| raw-plan-005 | `2026-04-12-guides-root.md` | codex-seed-page-005 | `https://platform.openai.com/docs/guides` | 固定 Guides 导航层 | P1 | planned | 用于发现 Codex 相关指南 |
| raw-plan-006 | `2026-04-12-homepage-root.md` | codex-seed-page-006 | `https://openai.com/` | 固定官网主站入口 | P2 | planned | 用于反查产品公告与主站导航 |

## 文件落盘规则

- 抓到页面后，不要随手命名，优先使用这里的计划文件名。
- 若真实页面标题与预期明显不同，可以调整文件名，但要同步更新页面索引和来源映射。
- 每个进入 `raw/` 的文件都应附带 `frontmatter-template.md` 规定的元信息。
