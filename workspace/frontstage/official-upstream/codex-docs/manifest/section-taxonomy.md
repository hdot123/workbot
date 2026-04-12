# Codex 栏目词表

> 用途：统一目录中对栏目、页面类别、主题范围的命名，避免后续漂移。

| section_key | display_name | meaning | examples | notes |
|---|---|---|---|---|
| homepage-root | 官网根入口 | OpenAI 主站入口 | openai.com | 最上层入口 |
| platform-root | Platform 根入口 | 开发平台与产品控制台入口 | platform.openai.com | 平台层入口 |
| docs-root | 文档根入口 | OpenAI Docs 总入口 | /docs | 文档树根入口 |
| guides-root | Guides 根路径 | 指南类页面导航层 | /docs/guides | 候选中间层 |
| codex-root | Codex 主入口 | Codex 现行主栏目或主页面 | codex docs page | 当前未收敛 |
| codex-research | Codex 研究页 | 更偏历史/研究背景的 Codex 页面 | openai-codex index page | 不一定代表现行文档 |
| api-reference | API 参考 | API 参考或接口级文档 | api-reference | 旁证层或交叉层 |
| cli | CLI / 命令行 | 命令行安装、使用、参数 | cli, terminal | 可能独立页或分节 |
| workflows | 工作流 | 常见使用流程、任务流、代理行为 | workflow, task flow | |
| permissions | 权限/安全 | 审批、权限模式、安全边界 | permissions, approval, sandbox | 高频关注区域 |
| configuration | 配置/设置 | 配置项、环境、偏好设置 | config, settings | |
| troubleshooting | 故障排查 | 错误诊断、修复路径、常见问题 | troubleshoot, errors, FAQ | |
| release-notes | 发行说明 | 版本变更与行为变动 | changelog, release notes | 时效性高 |

## 使用规则

- 新建页面索引时，优先复用这里的 `section_key`
- 如果出现新栏目，先补词表，再补页面索引
- 同一页面可以有一个主 `section_key` 和若干辅助标签，但主键只保留一个
