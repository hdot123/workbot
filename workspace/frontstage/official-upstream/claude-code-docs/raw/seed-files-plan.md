# Claude Code 第一批原始文件落盘计划

> 说明：本文件用于把第一批建议进入 `raw/` 的文件名和来源关系先固定下来。
> 状态：文件名基于当前既有知识设计，后续可根据真实页面标题微调，但建议保留稳定编号与日期前缀。

## 第一批建议落盘文件

| file_id | planned_filename | source_seed_id | candidate_url | purpose | priority | status | notes |
|---|---|---|---|---|---|---|---|
| raw-plan-001 | `2026-04-12-docs-root.md` | claude-seed-page-001 | `https://docs.anthropic.com/` | 固定文档树根入口 | P0 | planned | 用于向下展开栏目 |
| raw-plan-002 | `2026-04-12-claude-code-root.md` | claude-seed-page-002 | `https://docs.anthropic.com/en/docs/claude-code` | 固定 Claude Code 栏目根入口 | P0 | planned | 首要原料页面 |
| raw-plan-003 | `2026-04-12-docs-en-root.md` | claude-seed-page-003 | `https://docs.anthropic.com/en/docs/` | 固定英文文档导航层 | P1 | planned | 用于确认栏目层级 |
| raw-plan-004 | `2026-04-12-api-overview.md` | claude-seed-page-004 | `https://docs.anthropic.com/en/api/overview` | 作为 API/CLI 旁证页 | P2 | planned | 不是 Claude Code 主页面 |
| raw-plan-005 | `2026-04-12-console-root.md` | claude-seed-page-005 | `https://console.anthropic.com/` | 作为产品入口旁证 | P2 | planned | 不是文档正文页 |
| raw-plan-006 | `2026-04-12-homepage-root.md` | claude-seed-page-006 | `https://www.anthropic.com/` | 作为主站与公告旁证 | P2 | planned | 用于反查产品入口 |

## 文件落盘规则

- 抓到页面后，不要随手命名，优先使用这里的计划文件名。
- 若真实页面标题与预期明显不同，可以调整文件名，但要同步更新页面索引和来源映射。
- 每个进入 `raw/` 的文件都应附带 `frontmatter-template.md` 规定的元信息。

## 推荐执行顺序

1. 先落 `docs-root`
2. 再落 `claude-code-root`
3. 再落 `docs-en-root`
4. 最后补 API / Console / Homepage 旁证页

## 状态建议

- `planned`：已进入计划，但未开始抓取
- `collecting`：正在获取页面
- `stored`：页面已落盘
- `blocked`：页面无法获取或需要额外访问条件
