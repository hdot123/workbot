# Claude Code 官方来源导航关系假设（基于模型既有知识）

> 说明：本文件不是事实结论，而是为后续核验提供导航假设。
> 用途：帮助从根入口向下枚举页面，而不是每次都从零开始找。

## 可能的导航层级

### 层级 1：官方主域

- `https://www.anthropic.com/`
  - 角色：主站入口
  - 预期用途：产品介绍、公告、产品页反查

### 层级 2：官方文档主域

- `https://docs.anthropic.com/`
  - 角色：官方文档根入口
  - 预期用途：文档树总入口、栏目发现、路径回溯

### 层级 3：英文文档根路径（候选）

- `https://docs.anthropic.com/en/docs/`
  - 角色：英文文档层级入口
  - 预期用途：确定 Claude Code 所在栏目与兄弟页面

### 层级 4：Claude Code 栏目入口（候选）

- `https://docs.anthropic.com/en/docs/claude-code`
  - 角色：Claude Code 相关文档根入口
  - 预期用途：继续发现安装、配置、权限、工作流、IDE 集成、排障等子页面

### 旁证入口

- `https://console.anthropic.com/`
  - 角色：产品控制台入口
  - 预期用途：旁证产品存在与访问方式
- `https://docs.anthropic.com/en/api/overview`
  - 角色：API 文档旁证入口
  - 预期用途：辅助判断 Claude Code 与 API / CLI 能力的交叉引用

## 核验顺序建议

1. 先验证 `docs.anthropic.com/`
2. 再验证 `en/docs/`
3. 再验证 `en/docs/claude-code`
4. 最后从 Claude Code 栏目向下展开子页面

## 注意

- 本文件只表达“高概率导航关系”，不是已验证站点地图
- 后续一旦联网核验，应把确认后的结构写回 `manifest/sitemap` 相关正式文件
