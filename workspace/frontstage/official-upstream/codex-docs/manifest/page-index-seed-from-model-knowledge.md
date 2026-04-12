# Codex 页面索引种子（基于模型既有知识整理）

> 说明：本文件用于给正式页面索引提供第一批起始记录。
> 状态：这里的页面属于“候选官方页面 / 高概率官方入口”，未做实时联网校验。

| id | title | source_url | section | local_path | format | fetched_at | status | notes |
|---|---|---|---|---|---|---|---|---|
| codex-001 | OpenAI Docs 根入口 | `https://platform.openai.com/docs` | docs-root | `raw/2026-04-12-docs-root.md` | md/html |  | seeded | 作为文档树根入口，后续可向下展开 |
| codex-002 | OpenAI Platform 根入口 | `https://platform.openai.com/` | platform-root | `raw/2026-04-12-platform-root.md` | md/html |  | seeded | 平台与文档旁证入口 |
| codex-003 | OpenAI Codex 研究页（候选历史入口） | `https://openai.com/index/openai-codex/` | codex-research | `raw/2026-04-12-codex-research.md` | md/html |  | seeded | 更偏历史/研究页，不一定是现行主入口 |
| codex-004 | API 参考根入口（候选） | `https://platform.openai.com/docs/api-reference` | api-reference | `raw/2026-04-12-api-reference.md` | md/html |  | seeded | 用于旁证 Codex 与 API 交叉关系 |
| codex-005 | Docs Guides 根路径（候选） | `https://platform.openai.com/docs/guides` | guides-root | `raw/2026-04-12-guides-root.md` | md/html |  | seeded | 用于向下枚举 Codex 相关指南 |
| codex-006 | OpenAI 官网根入口 | `https://openai.com/` | homepage-root | `raw/2026-04-12-homepage-root.md` | md/html |  | seeded | 用于反查产品公告与主站导航 |

## 使用规则

- `status=seeded` 表示该条目已进入收料范围，但尚未完成实时核验。
- 一旦完成真实抓取，应把 `fetched_at` 补上，并把 `status` 更新为 `fetched` 或 `verified`。
- 如页面失效、跳转或被替换，不要直接删除，应保留记录并改写状态与备注。
