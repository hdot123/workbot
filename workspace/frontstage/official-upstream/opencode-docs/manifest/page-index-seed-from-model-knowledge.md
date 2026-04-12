# OpenCode 页面索引种子（基于模型既有知识整理）

> 说明：本文件用于给正式页面索引提供第一批起始记录。
> 状态：这里的页面属于“候选官方页面 / 高概率官方入口”，未做实时联网校验。

| id | title | source_url | section | local_path | format | fetched_at | status | notes |
|---|---|---|---|---|---|---|---|---|
| opencode-001 | OpenCode 官网根入口（候选） | `https://opencode.ai/` | homepage-root | `raw/2026-04-12-homepage-root.md` | md/html |  | seeded | 主站与产品入口候选 |
| opencode-002 | OpenCode 文档入口（候选） | `https://opencode.ai/docs` | docs-root | `raw/2026-04-12-docs-root.md` | md/html |  | seeded | 文档树根入口候选 |
| opencode-003 | OpenCode GitHub 仓库（候选） | `https://github.com/sst/opencode` | github-repo | `raw/2026-04-12-github-repo.md` | md/html |  | seeded | 可作为 README、发布记录与代码旁证 |
| opencode-004 | OpenCode 安装页（候选） | `https://opencode.ai/docs/installation` | installation | `raw/2026-04-12-installation.md` | md/html |  | seeded | 安装或快速开始相关入口 |
| opencode-005 | OpenCode 配置页（候选） | `https://opencode.ai/docs/configuration` | configuration | `raw/2026-04-12-configuration.md` | md/html |  | seeded | 配置与环境相关入口 |
| opencode-006 | OpenCode 维护方 GitHub（候选旁证） | `https://github.com/sst` | github-owner | `raw/2026-04-12-github-owner.md` | md/html |  | seeded | 用于旁证项目归属 |

## 使用规则

- `status=seeded` 表示该条目已进入收料范围，但尚未完成实时核验。
- 一旦完成真实抓取，应把 `fetched_at` 补上，并把 `status` 更新为 `fetched` 或 `verified`。
- 如页面失效、跳转或被替换，不要直接删除，应保留记录并改写状态与备注。
