# OpenCode 栏目词表

> 用途：统一目录中对栏目、页面类别、主题范围的命名，避免后续漂移。

| section_key | display_name | meaning | examples | notes |
|---|---|---|---|---|
| homepage-root | 官网根入口 | OpenCode 主站入口 | opencode.ai | 最上层入口 |
| docs-root | 文档根入口 | OpenCode Docs 总入口 | /docs | 文档树根入口 |
| github-repo | 官方仓库 | 官方代码仓库与 README 入口 | github.com/sst/opencode | 旁证层或主事实层待核验 |
| github-owner | 维护方 GitHub | 维护方组织或用户主页 | github.com/sst | 归属旁证 |
| opencode-root | OpenCode 主入口 | OpenCode 现行主栏目或主页面 | docs main page | 当前未收敛 |
| installation | 安装/接入 | 安装、初始化、启用等内容 | install, quickstart | |
| configuration | 配置/设置 | 配置项、环境、偏好设置 | config, settings | |
| permissions | 权限/安全 | 权限模式、批准策略、安全边界 | permissions, approval, sandbox | 高频关注区域 |
| workflows | 工作流 | 常见使用流程、任务流 | workflow, task flow | |
| troubleshooting | 故障排查 | 错误诊断、修复路径、FAQ | troubleshoot, errors, FAQ | |
| release-notes | 发行说明 | 版本变更与行为变动 | changelog, releases | 时效性高 |

## 使用规则

- 新建页面索引时，优先复用这里的 `section_key`
- 如果出现新栏目，先补词表，再补页面索引
- 同一页面可以有一个主 `section_key` 和若干辅助标签，但主键只保留一个
