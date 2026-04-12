# Claude Code 栏目词表

> 用途：统一目录中对栏目、页面类别、主题范围的命名，避免后续漂移。

| section_key | display_name | meaning | examples | notes |
|---|---|---|---|---|
| docs-root | 文档根入口 | 文档站总入口 | docs.anthropic.com | 最上层入口 |
| docs-en-root | 英文文档根路径 | 英文文档导航层 | /en/docs/ | 可能是中间层 |
| claude-code-root | Claude Code 栏目根入口 | Claude Code 相关文档主入口 | /en/docs/claude-code | 首要栏目候选 |
| installation | 安装/接入 | 安装、初始化、启用等内容 | install, setup, getting started | 可是独立页，也可能是分节 |
| configuration | 配置/设置 | 环境、参数、偏好设置 | config, settings | |
| permissions | 权限/安全 | 权限模式、审批、沙箱、安全边界 | permissions, approval, sandbox | 高频关注区域 |
| workflows | 工作流 | 常见操作流与代理行为 | workflow, agent behavior, task flow | |
| ide-integration | IDE 集成 | 编辑器、插件、终端集成 | VS Code, JetBrains, editor integration | |
| troubleshooting | 故障排查 | 错误诊断、常见问题、修复路径 | troubleshoot, errors, FAQ | |
| release-notes | 发行说明 | 版本变更与行为变动 | changelog, release notes | 时效性高 |
| api-overview | API 旁证页 | 不是 Claude Code 主页面，但可辅助判断关系 | api overview | 旁证层 |
| console-root | 控制台入口 | 官方控制台页面 | console.anthropic.com | 旁证层 |
| homepage-root | 官网主站入口 | 官方主站与公告入口 | anthropic.com | 旁证层 |

## 使用规则

- 新建页面索引时，优先复用这里的 `section_key`
- 如果出现新栏目，先补词表，再补页面索引
- 同一页面可以有一个主 `section_key` 和若干辅助标签，但主键只保留一个
