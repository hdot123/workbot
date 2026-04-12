# Codex 覆盖范围跟踪

> 用途：跟踪当前原料收集与核对覆盖到什么程度。

| area | description | expected_source_type | current_status | refs_ready | raw_ready | manifest_ready | notes_ready | remarks |
|---|---|---|---|---|---|---|---|---|
| docs-root | 文档根入口 | docs | seeded | yes | no | partial | no | 已有入口种子，待实时核验 |
| platform-root | 平台根入口 | console | seeded | yes | no | partial | no | 已有入口种子，待实时核验 |
| codex-root | Codex 主入口 | docs/homepage | planned | partial | no | no | no | 当前主入口尚未收敛 |
| api-reference | API 参考 | api-doc | planned | partial | no | no | no | 具体 Codex 关联页待发现 |
| guides | 指南类页面 | docs | planned | partial | no | no | no | 需从 guides 下枚举 |
| cli | CLI / 命令行 | docs | planned | partial | no | no | no | 是否独立栏目待确认 |
| workflows | 工作流 / 使用方式 | docs | planned | partial | no | no | no | 具体页面待发现 |
| troubleshooting | 故障排查 | docs | planned | partial | no | no | no | 具体页面待发现 |
| release-notes | 发行说明 / 变更日志 | changelog | planned | partial | no | no | no | 路径待确认 |

## 状态含义

- `seeded`：已有可信入口种子，但未完整核验
- `planned`：已纳入覆盖范围，但还未拿到正式页面
- `collecting`：正在落原料
- `indexed`：页面索引已建立
- `reviewing`：正在人工核对
- `done`：该区域达到当前阶段收敛
