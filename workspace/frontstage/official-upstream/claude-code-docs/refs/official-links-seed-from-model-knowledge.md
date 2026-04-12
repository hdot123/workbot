# Claude Code 官方链接种子（基于模型既有知识，未做实时联网校验）

> 作用：提供第一批可追踪的官方来源入口种子。
> 注意：本文件不是最终核验结果；这里只能作为收料起点与证据候选。

| id | title | url | confidence | why_it_looks_official | verification_status | notes |
|---|---|---|---|---|---|---|
| claude-seed-001 | Anthropic Docs 根入口 | `https://docs.anthropic.com/` | high | Anthropic 官方文档主域 | unverified-live | 可作为文档树根入口 |
| claude-seed-002 | Claude Code 文档入口（候选） | `https://docs.anthropic.com/en/docs/claude-code` | medium-high | 符合 Anthropic 文档路径结构与产品栏目命名 | unverified-live | 需后续确认是否仍为现行入口 |
| claude-seed-003 | Anthropic 官网根入口 | `https://www.anthropic.com/` | high | Anthropic 官方主站 | unverified-live | 可用于反查产品页或公告入口 |
| claude-seed-004 | Anthropic Console 根入口 | `https://console.anthropic.com/` | high | Anthropic 官方控制台域名 | unverified-live | 不等于文档页，但可作为产品入口旁证 |

## 使用方式

1. 先从高置信入口开始核对
2. 若入口可达，再继续枚举子页面
3. 枚举出的子页面不要直接写回这里，优先记入：
   - `refs/page-source-map.md`
   - `manifest/page-index-template.md` 或后续正式页面索引文件

## 约束

- 本文件允许记录“模型已知但未实时校验”的官方候选入口
- 本文件不输出分析结论
- 一旦完成联网核验，应把结果迁移或收敛到正式的 `official-links.md`
