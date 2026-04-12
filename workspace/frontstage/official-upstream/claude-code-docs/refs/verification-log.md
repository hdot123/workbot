# Claude Code 官方来源核验日志

> 用途：记录每一条官方来源从“模型记忆 / 候选入口”演进到“已核验 / 跳转 / 归档 / 阻塞”的过程。
> 说明：当前日志先登记初始状态，后续每次核验都要追加记录。

| check_id | date | target_id | target_url | previous_status | new_status | method | result_summary | action |
|---|---|---|---|---|---|---|---|---|
| verify-001 | 2026-04-12 | claude-ref-001 | `https://www.anthropic.com/` | none | unverified-live | model-knowledge | 基于模型既有知识认定为高概率官方主站入口 | 待后续实时核验 |
| verify-002 | 2026-04-12 | claude-ref-002 | `https://docs.anthropic.com/` | none | unverified-live | model-knowledge | 基于模型既有知识认定为高概率官方文档根入口 | 待后续实时核验 |
| verify-003 | 2026-04-12 | claude-ref-003 | `https://docs.anthropic.com/en/docs/claude-code` | none | unverified-live | model-knowledge | 基于路径结构判断为高概率 Claude Code 栏目入口 | 待后续实时核验 |
| verify-004 | 2026-04-12 | claude-ref-004 | `https://console.anthropic.com/` | none | unverified-live | model-knowledge | 基于模型既有知识认定为官方控制台入口 | 待后续实时核验 |
| verify-005 | 2026-04-12 | claude-ref-005 | `https://docs.anthropic.com/en/api/overview` | none | unverified-live | model-knowledge | 基于模型既有知识认定为 API 文档旁证入口 | 待后续实时核验 |
| verify-006 | 2026-04-12 | claude-ref-006 | `https://docs.anthropic.com/en/docs/` | none | unverified-live | model-knowledge | 基于路径结构判断为高概率英文文档根路径 | 待后续实时核验 |

## 记录要求

- 每次状态变化都应追加一条，不覆盖历史
- `method` 需要明确：`model-knowledge / browser / crawler / manual-check / export`
- `result_summary` 只写核验事实，不写下游结论
