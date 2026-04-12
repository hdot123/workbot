# Codex 原料提取与核对计划

## 目标

把 Codex 的官方文档原料沉淀为一套：

- 可追溯
- 可复核
- 可扩展
- 可用于后续 promotion 的上游证据层

## 当前阶段

当前已完成：

- 四层目录职责固定
- `refs/` 入口种子建立
- `manifest/` 覆盖跟踪建立
- `raw/` 落盘约定建立

当前未完成：

- 真实官方 URL 的实时核验
- 页面级原料正式落盘
- 页面到来源的一对一映射填充

## 推荐执行顺序

1. 从 `refs/official-links-from-model-knowledge.md` 拿第一批入口
2. 联网后核验这些入口的可达性与是否仍为官方现行路径
3. 对确认页面进行导出或抓取，落到 `raw/`
4. 在 `refs/page-source-map.md` 建立页面到来源映射
5. 在 `manifest/page-index-template.md` 或正式索引中登记页面
6. 在 `notes/review-notes-template.md` 写冲突点、重复页、待核点
7. 收敛后再做 promotion
