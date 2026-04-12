# official-upstream 首批收料 Runbook

## 目标

把三组目录从“模板/种子齐全”推进到“已有第一批真实原文文件”。

## 通用步骤

1. 从各项目 `manifest/source-seeds.md` 中拿 P0 入口
2. 对入口做实时核验
3. 把核验结果追加到 `refs/verification-log.md`
4. 按 `raw/seed-files-plan.md` 的文件名把原文落到 `raw/`
5. 为每个 raw 文件补 `frontmatter-template.md` 规定的元信息
6. 在 `manifest/page-index-seed-from-model-knowledge.md` 或正式 page index 中，把对应条目标记为 `fetched`
7. 在 `refs/page-source-map.md` 建立页面到来源映射
8. 如存在冲突或不确定点，写入 `notes/review-notes-template.md` 或 `notes/open-questions.md`

## 三组优先顺序

### Claude Code

优先收：

1. `docs-root`
2. `claude-code-root`
3. `docs-en-root`

### Codex

优先收：

1. `docs-root`
2. `platform-root`
3. `codex-research`

### OpenCode

优先收：

1. `homepage-root`
2. `docs-root`
3. `github-repo`

## 成功标准

完成以下 4 点，算首批收料成功：

- 至少 1 个 P0 页面真实落入 `raw/`
- 对应来源已写入 `verification-log`
- `page-source-map` 已建立映射
- `page-index` 已从 `seeded` 推进到 `fetched`
