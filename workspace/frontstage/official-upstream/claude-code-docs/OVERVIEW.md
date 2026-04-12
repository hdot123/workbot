# Claude Code 上游原料总览

> 状态：本目录已具备可收料、可追溯、可做 promotion 前核对的基本骨架。
> 说明：其中涉及官方 URL 的“已知入口”部分，当前基于模型既有知识整理，未做实时联网校验。

## 目录用途

`claude-code-docs/` 用于沉淀 Claude Code 的官方文档上游原料，而不是最终整理后的知识成品。

## 四层职责

- `raw/`
  - 存放原始抓取结果、原始 markdown、导出的页面
- `manifest/`
  - 存放页面清单、站点地图、抓取索引、覆盖范围跟踪
- `refs/`
  - 存放官方来源证明、入口页、URL 清单、页面到来源映射
- `notes/`
  - 存放人工整理备注、页间关系、待核点、缺口说明

## 当前已有文件

### 根目录

- `README.md`：目录占位说明
- `PROJECT.md`：项目说明、状态字段、命名建议
- `OVERVIEW.md`：本文件，作为目录导航

### raw/

- `README.md`：目录占位
- `source-drop-guideline.md`：原始材料落盘约定

### manifest/

- `README.md`：目录占位
- `page-index-template.md`：页面级索引模板
- `sitemap-template.md`：站点地图模板
- `coverage-tracker.md`：覆盖范围跟踪表
- `collection-log.md`：收料轮次记录

### refs/

- `index.md`：refs 层职责说明
- `official-links.md`：官方链接模板
- `official-links-seed-from-model-knowledge.md`：基于模型既有知识整理的已知官方入口种子
- `page-source-map.md`：页面到来源映射模板
- `source-authority-policy.md`：什么算官方来源的判定规则

### notes/

- `README.md`：目录占位
- `review-notes-template.md`：人工核对模板
- `extraction-plan.md`：原料收集与核对计划
- `open-questions.md`：待核点与未决问题

## 当前建议使用顺序

1. 先看 `refs/official-links-seed-from-model-knowledge.md`，拿到已知官方入口种子
2. 再看 `manifest/coverage-tracker.md`，明确哪些栏目已覆盖、哪些未覆盖
3. 收到页面后按 `raw/source-drop-guideline.md` 落盘
4. 在 `manifest/page-index-template.md` 或后续正式索引文件中登记页面
5. 在 `notes/review-notes-template.md` 记录冲突点、重复页、待核点

## 当前限制

- 真实官方 URL 尚未做实时联网校验
- 已有种子链接只能视为“高概率官方来源入口”，不应直接等同于最终验证结论
- 若后续允许联网，应优先把 `refs/official-links-seed-from-model-knowledge.md` 升级为经核验版 `official-links.md`
