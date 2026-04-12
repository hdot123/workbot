# official-upstream 漂移与缺口清单

## 漂移项

### D-001 根目录 README 未回写

- 路径：`workspace/frontstage/official-upstream/README.md`
- 现状：仍为早期简版说明
- 影响：根目录入口说明与当前四层架构不一致
- 建议：本地直接覆盖为正式版入口说明

### D-002 Codex 目录导航状态滞后

- 路径：`workspace/frontstage/official-upstream/codex-docs/DIRECTORY-NAV.md`
- 现状：仍显示“页面级索引种子待补、来源核验日志待补”
- 实际：这些文件已补齐
- 建议：回写当前状态

### D-003 OpenCode 目录导航状态滞后

- 路径：`workspace/frontstage/official-upstream/opencode-docs/DIRECTORY-NAV.md`
- 现状：仍显示“页面级索引种子待补、来源核验日志待补”
- 实际：这些文件已补齐
- 建议：回写当前状态

## 共同缺口

### G-001 真实 raw 文件尚未落盘

- 三组目录都已有 `seed-files-plan`
- 但尚缺第一批真实页面原文文件

### G-002 候选链接尚未实时核验

- 当前 `official-links-from-model-knowledge.md` 仍是候选层
- `verification-log.md` 目前只有 `model-knowledge` 初始记录

### G-003 页面到来源映射尚未实填

- `page-source-map.md` 目前仍以模板为主
- 尚未建立真实页面与真实来源的一对一映射

### G-004 证据链尚未挂真实 claim

- `evidence-chain-template.md` 已建
- 但尚未填入真实命题与 promotion-ready 状态

## 修复顺序建议

1. 先修文档漂移
2. 再核验 P0 入口
3. 再落第一批 raw 原文
4. 再填 page-source-map
5. 最后挂第一批真实 evidence chain
