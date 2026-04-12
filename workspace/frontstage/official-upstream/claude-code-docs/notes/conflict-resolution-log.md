# Claude Code 冲突处理日志

> 用途：记录页面之间、版本之间、来源之间的冲突与处理结果。

| conflict_id | date | topic | involved_pages | conflict_type | description | current_decision | evidence | status |
|---|---|---|---|---|---|---|---|---|
| conflict-001 | 2026-04-12 | Claude Code 入口路径 | claude-code-002 | path-uncertain | 当前路径基于模型既有知识整理，尚未实时核验 | 暂保持候选状态，不进入最终事实层 | refs/official-links-from-model-knowledge.md | open |

## 冲突类型建议

- `path-uncertain`：路径不确定
- `duplicate`：重复页面
- `redirect-changed`：页面跳转变化
- `rule-conflict`：规则描述冲突
- `scope-conflict`：页面适用范围冲突
- `freshness-risk`：时效风险高

## 处理原则

- 冲突没有关闭前，不应直接 promotion
- 每个冲突都要能指回具体页面与来源
- 决策可以暂时保守，但必须写明依据
