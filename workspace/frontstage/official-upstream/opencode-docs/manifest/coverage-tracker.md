# OpenCode 覆盖范围跟踪

> 用途：跟踪当前原料收集与核对覆盖到什么程度。

| area | description | expected_source_type | current_status | refs_ready | raw_ready | manifest_ready | notes_ready | remarks |
|---|---|---|---|---|---|---|---|---|
| homepage-root | 官网根入口 | homepage | seeded | yes | no | partial | no | 已有入口种子，待实时核验 |
| docs-root | 文档根入口 | docs | seeded | yes | no | partial | no | 已有入口种子，待实时核验 |
| github-repo | 官方仓库 | github | seeded | yes | no | partial | no | 可作为 README 与发布旁证 |
| installation | 安装/接入 | docs | planned | partial | no | no | no | 具体子页待确认 |
| configuration | 配置/设置 | docs | planned | partial | no | no | no | 具体子页待确认 |
| permissions | 权限/安全 | docs | planned | partial | no | no | no | 是否独立栏目待确认 |
| workflows | 工作流 / 使用方式 | docs | planned | partial | no | no | no | 具体页面待发现 |
| troubleshooting | 故障排查 | docs | planned | partial | no | no | no | 具体页面待发现 |
| release-notes | 发行说明 / 变更日志 | changelog/github | planned | partial | no | no | no | 可能在官网或 GitHub 发布页 |

## 状态含义

- `seeded`：已有可信入口种子，但未完整核验
- `planned`：已纳入覆盖范围，但还未拿到正式页面
- `collecting`：正在落原料
- `indexed`：页面索引已建立
- `reviewing`：正在人工核对
- `done`：该区域达到当前阶段收敛
