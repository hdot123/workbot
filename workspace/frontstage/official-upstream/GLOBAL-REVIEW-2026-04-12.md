# official-upstream 全局复核（2026-04-12）

## 复核范围

- `claude-code-docs/`
- `codex-docs/`
- `opencode-docs/`

## 根目录规则

根目录四层约定已经明确写入 `STRUCTURE.md`：

- `raw/` 看原文
- `manifest/` 看覆盖范围
- `refs/` 看官方来源证明
- `notes/` 看人工整理线索

且 `refs/` 的职责约束已经写死：只放官方来源证明，不放下游结论。

## 当前总体判断

### 1. 三组目录都已经跨过“空骨架”阶段

目前三组目录都不只是空文件夹，而是已经具备：

- 项目说明
- 总览或目录导航
- 官方入口候选
- 页面来源映射模板
- 覆盖范围跟踪
- 页面索引模板或页面种子
- raw 落盘规范
- 核对计划或 promotion 检查

### 2. Claude Code 完整度最高

`claude-code-docs/` 目前完成度最高，已经形成从：

- 目录导航
- 入口种子
- 页面级种子
- 站点地图种子
- 来源核验日志
- raw 文件计划
- 证据链模板
- 冲突处理日志
- 栏目词表

到 promotion 前检查的一整套闭环。

### 3. Codex 与 OpenCode 已经进入“可直接收料”状态

`codex-docs/` 与 `opencode-docs/` 目前已经接近 Claude 的结构成熟度，足以开始：

- 核验候选入口
- 落第一批 raw 文件
- 建页面到来源映射
- 做首轮人工核对

## 已发现的文档漂移

### 漂移 1：根目录 `README.md` 仍是旧版

当前根目录正式入口说明并未原地更新，旧 `README.md` 仍停留在最早的简版状态。

### 漂移 2：`codex-docs/DIRECTORY-NAV.md` 状态字段已滞后

该文件仍写着：

- 页面级索引种子：待补
- 来源核验日志：待补

但这些文件实际上已经在后续补齐。

### 漂移 3：`opencode-docs/DIRECTORY-NAV.md` 状态字段已滞后

该文件也仍写着：

- 页面级索引种子：待补
- 来源核验日志：待补

但这些文件实际上已经在后续补齐。

## 当前共同缺口

三组目录当前共同缺的，不再是骨架，而是“真实内容层”：

1. 真实官方页面原文尚未正式落入 `raw/`
2. 官方候选 URL 尚未做实时联网核验
3. `page-source-map` 仍以模板为主，尚未填充真实页面映射
4. 证据链模板已建，但还没有挂上真实 claim

## 下一步建议顺序

### 优先级 P0

- 先修正根目录 `README.md` 与两个滞后的 `DIRECTORY-NAV.md`
- 对三组 `official-links-from-model-knowledge.md` 做首轮实时核验
- 开始把第一批 P0 页面真实落盘到 `raw/`

### 优先级 P1

- 填充 `page-source-map.md`
- 把 `page-index-seed` 中真实抓到的页面改为 `fetched`
- 开始记录第一批真实 claim 到 `evidence-chain-template.md`

### 优先级 P2

- 做冲突收敛
- 做 freshness 标记
- 准备小范围 promotion 试运行

## 结论

截至 2026-04-12，这套 `official-upstream` 已经完成了：

- 目录职责固定
- 三项目统一建模
- 上游证据层与收料层框架落盘

尚未完成的是：

- 实时核验
- 真实原文落盘
- 证据链实填
- 文档状态回写收口
