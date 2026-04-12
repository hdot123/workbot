# Claude Code 页面索引种子（基于模型既有知识整理）

> 说明：本文件用于给正式页面索引提供第一批起始记录。
> 状态：这里的页面属于“候选官方页面 / 高概率官方入口”，未做实时联网校验。

| id | title | source_url | section | local_path | format | fetched_at | status | notes |
|---|---|---|---|---|---|---|---|---|
| claude-code-001 | Anthropic Docs 根入口 | `https://docs.anthropic.com/` | docs-root | `raw/2026-04-12-docs-root.md` | md/html |  | seeded | 作为文档树根入口，后续可向下展开 |
| claude-code-002 | Claude Code 文档入口（候选） | `https://docs.anthropic.com/en/docs/claude-code` | claude-code-root | `raw/2026-04-12-claude-code-root.md` | md/html |  | seeded | 首要收料入口 |
| claude-code-003 | Anthropic Docs 英文根路径（候选） | `https://docs.anthropic.com/en/docs/` | docs-en-root | `raw/2026-04-12-docs-en-root.md` | md/html |  | seeded | 便于回溯导航关系 |
| claude-code-004 | Anthropic API Overview（候选旁证） | `https://docs.anthropic.com/en/api/overview` | api-overview | `raw/2026-04-12-api-overview.md` | md/html |  | seeded | 用于旁证 CLI / API 交叉说明 |
| claude-code-005 | Anthropic Console 根入口 | `https://console.anthropic.com/` | console-root | `raw/2026-04-12-console-root.md` | md/html |  | seeded | 官方控制台入口，非文档正文 |
| claude-code-006 | Anthropic 官网根入口 | `https://www.anthropic.com/` | homepage-root | `raw/2026-04-12-homepage-root.md` | md/html |  | seeded | 用于反查产品主站导航与公告 |

## 使用规则

- `status=seeded` 表示该条目已进入收料范围，但尚未完成实时核验。
- 一旦完成真实抓取，应把 `fetched_at` 补上，并把 `status` 更新为 `fetched` 或 `verified`。
- 如页面失效、跳转或被替换，不要直接删除，应保留记录并改写状态与备注。
