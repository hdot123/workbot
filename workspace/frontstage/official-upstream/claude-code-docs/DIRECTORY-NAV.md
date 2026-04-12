# Claude Code 目录导航

> 作用：作为 `claude-code-docs/` 的实际入口说明文件。
> 说明：由于当前连接器不便直接覆盖旧版 `README.md`，这里先提供完整导航文档，后续可本地合并到 `README.md`。

## 目录定位

`claude-code-docs/` 是 Claude Code 官方文档的上游原料层。
它不负责存放最终知识成品，而是负责：

- 保存官方原始材料
- 保存页面清单与覆盖范围
- 保存官方来源证明
- 保存人工整理与待核点

## 目录结构

- `raw/`
  - 原始抓取结果、原始 markdown、导出的页面
  - 重点文件：`source-drop-guideline.md`、`frontmatter-template.md`、`seed-files-plan.md`
- `manifest/`
  - 页面清单、站点地图、抓取索引、覆盖跟踪
  - 重点文件：`page-index-template.md`、`page-index-seed-from-model-knowledge.md`、`coverage-tracker.md`、`collection-log.md`、`source-seeds.md`、`sitemap-seed-from-model-knowledge.md`
- `refs/`
  - 官方链接证明、官方入口页、页面到来源映射、核验日志
  - 重点文件：`official-links-from-model-knowledge.md`、`official-links-seed-from-model-knowledge.md`、`page-source-map.md`、`verification-log.md`、`source-authority-policy.md`
- `notes/`
  - 人工整理备注、页间关系、待核点、promotion 前检查
  - 重点文件：`review-notes-template.md`、`extraction-plan.md`、`open-questions.md`、`promotion-readiness-checklist.md`

## 建议使用顺序

1. 先看 `refs/official-links-from-model-knowledge.md`
2. 再看 `manifest/source-seeds.md` 和 `manifest/page-index-seed-from-model-knowledge.md`
3. 按 `raw/seed-files-plan.md` 落第一批原始文件
4. 用 `refs/page-source-map.md` 建立来源映射
5. 用 `notes/review-notes-template.md` 与 `notes/open-questions.md` 记录核对结果
6. promotion 前过一遍 `notes/promotion-readiness-checklist.md`

## 当前状态

- 目录骨架：已补齐
- 入口种子：已补齐
- 页面级索引种子：已补齐
- 来源核验日志：已补齐
- 真实页面原文：待落盘
- 实时联网核验：待执行

## 当前边界

- 现有部分官方链接来自模型既有知识整理，不应直接视为最终已验证事实
- 在完成实时核验前，所有候选链接都应维持 `unverified-live` 或相近状态
