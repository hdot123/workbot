# Codex 上游原料总览

> 状态：本目录已进入骨架补齐阶段。
> 说明：其中涉及官方 URL 的“已知入口”部分，当前基于模型既有知识整理，未做实时联网校验。

## 目录用途

`codex-docs/` 用于沉淀 Codex 的官方文档上游原料，而不是最终整理后的知识成品。

## 四层职责

- `raw/`：存放原始抓取结果、原始 markdown、导出的页面
- `manifest/`：存放页面清单、站点地图、抓取索引、覆盖范围跟踪
- `refs/`：存放官方来源证明、入口页、URL 清单、页面到来源映射
- `notes/`：存放人工整理备注、页间关系、待核点、缺口说明

## 当前建议使用顺序

1. 先看 `refs/official-links-from-model-knowledge.md`
2. 再看 `manifest/source-seeds.md`
3. 收到页面后按 `raw/source-drop-guideline.md` 落盘
4. 在 `refs/page-source-map.md` 建立来源映射
5. 在 `manifest/page-index-template.md` 或正式页面索引中登记页面
6. 在 `notes/review-notes-template.md` 记录冲突点、重复页、待核点

## 当前限制

- 真实官方 URL 尚未做实时联网核验
- 已有种子链接只能视为“高概率官方来源入口”，不应直接等同于最终验证结论
- 若后续允许联网，应优先把 `refs/official-links-from-model-knowledge.md` 升级为经核验版 `official-links.md`
