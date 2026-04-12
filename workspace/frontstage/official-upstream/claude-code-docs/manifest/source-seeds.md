# Claude Code 页面种子清单（基于模型既有知识整理）

> 说明：本文件用于把 Claude Code 相关页面的第一批收料方向先固定下来。
> 状态：这些条目是候选栏目/候选页面方向，不等于已核验的现行页面地图。

| seed_id | area | candidate_title | candidate_url | parent_ref | priority | status | notes |
|---|---|---|---|---|---|---|---|
| claude-seed-page-001 | docs-root | Anthropic Docs 根入口 | `https://docs.anthropic.com/` | claude-ref-002 | P0 | seeded | 文档树根入口 |
| claude-seed-page-002 | claude-code-root | Claude Code 文档入口（候选） | `https://docs.anthropic.com/en/docs/claude-code` | claude-ref-003 | P0 | seeded | Claude Code 相关页面的首要起点 |
| claude-seed-page-003 | docs-en-root | 英文文档根路径（候选） | `https://docs.anthropic.com/en/docs/` | claude-ref-006 | P1 | seeded | 用于回溯导航层级 |
| claude-seed-page-004 | api-overview | API Overview（候选旁证） | `https://docs.anthropic.com/en/api/overview` | claude-ref-005 | P2 | seeded | 用于旁证 CLI / API 交叉说明 |
| claude-seed-page-005 | console-root | Console 根入口 | `https://console.anthropic.com/` | claude-ref-004 | P2 | seeded | 产品入口旁证，不直接等于文档页 |
| claude-seed-page-006 | homepage-root | Anthropic 官网根入口 | `https://www.anthropic.com/` | claude-ref-001 | P2 | seeded | 用于反查产品公告或主站导航 |

## 推荐优先级

- `P0`：先核验，优先开始收料
- `P1`：用于补齐站点结构
- `P2`：作为旁证或交叉引用入口

## 使用方式

1. 先从 `P0` 种子开始
2. 页面核验成功后，把真实页面登记进页面索引
3. 如发现子页面，继续补到 `page-index` 和 `page-source-map`
4. 如发现候选路径失效，保留记录但调整状态，不要直接删除
