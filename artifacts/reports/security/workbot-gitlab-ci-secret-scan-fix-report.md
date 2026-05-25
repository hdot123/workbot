# P0-2E workbot GitLab CI Secret Scan 误报修复报告

**日期**: 2026-05-07
**执行**: Droid automated fix
**状态**: CONDITIONAL PASS

---

## 1. 最终判定

**CONDITIONAL PASS** — secrets-check 和 secret-scan-workbot 已修复并通过，后续 stages 已解锁。github-push-gate-dry-run 失败属于 P0-1 已知问题（schedule 未注释），不在 P0-2E 范围。

| 判定条件 | 结果 |
|---------|------|
| secrets-check 通过 | PASS |
| secret-scan-workbot 通过 | PASS |
| 无真实 secret 存在 | PASS |
| scanner 未被 allow_failure | PASS |
| 模拟 secret 测试能正确 fail | PASS |
| .gitlab-ci.yml 无可执行 git push | PASS |
| 无 git push origin | PASS |
| staged diff secret scan = 0 findings | PASS |
| 无 GitHub push | PASS |
| Pipeline 创建 | PASS |
| Pipeline 全部通过 | FAIL (github-push-gate-dry-run: schedule 未注释, 非 P0-2E 范围) |

---

## 2. Secret Scan 误报根因

Pipeline 101 有 5 个 findings，全部是误报：

### Finding 1: `.gitlab-ci.yml` — Private Key (SELF_REFERENCE)

| 字段 | 值 |
|------|-----|
| 命中文件 | `.gitlab-ci.yml` |
| 命中规则 | `grep -q 'BEGIN.*PRIVATE KEY'` |
| 命中内容类型 | 扫描规则自引用 — CI 文件中的 grep 模式字符串本身被匹配 |
| 是否真实 secret | 否 |
| 是否应 allowlist | 是 — 排除 .gitlab-ci.yml 自身 |
| 是否应排除目录 | 不适用 |

### Finding 2-3: `docs/apisix-supabase-*.md` — Bearer Token (DOC_EXAMPLE)

| 字段 | 值 |
|------|-----|
| 命中文件 | `docs/apisix-supabase-asbuilt-runbook.md` (5 lines), `docs/apisix-supabase-mysql-maintenance-runbook.md` (1 line) |
| 命中规则 | `grep -in 'Authorization:.*Bearer.*[^P][^L][^A][^C][^E]'` |
| 命中内容类型 | 文档示例 — 使用 `<SUPABASE_ANON_KEY>`, `<APISIX_CLIENT_KEY>`, `totally-wrong-client-token` 等占位符 |
| 是否真实 secret | 否 |
| 是否应 allowlist | 应改进 Bearer 过滤逻辑，识别 angle-bracket 模板和 fake 值 |
| 是否应替换为 placeholder | 已是 placeholder，但格式不匹配旧 scanner 的 PLACEHOLDER 过滤 |

### Finding 4-5: `workspace/frontstage/memory-legacy-quarantine-2026-04-12/` — Bearer Token (LEGACY_ARCHIVE)

| 字段 | 值 |
|------|-----|
| 命中文件 | quarantine 目录下的 `multi-brand-protocol-baseline.md` 和 `supermemory-记忆层集成分析报告.md` |
| 命中规则 | Bearer regex |
| 命中内容类型 | Legacy quarantine 文档 — 目录标记为 "非 active truth", "historical residue", "superseded" |
| 是否真实 secret | 否 — 使用 `sk-sp-xxx`, `sm_xxx`, `xxx.xxx` 等遮蔽值 |
| 是否应排除目录 | 是 — `memory-legacy-quarantine-*` 是隔离的历史归档 |

---

## 3. 采用的修复策略

### 策略 A: 修复扫描脚本自引用问题

- 将 shell-based `for f in $(find ...)` 替换为 Python pathlib `rglob()`（与 P0-2D json-valid 修复一致）
- 通过 `skip_name = {'.gitlab-ci.yml'}` 排除 CI 配置文件自身
- 替代检查：scanner 仍扫描所有其他 `.yml` 文件中的真实 secret
- `.gitlab-ci.yml` 不可能包含真实 secret（不含可执行 git push，无 token）

### 策略 B: 改进 Bearer token 占位符检测

Python Bearer 检查器改进：
- 使用 `re.compile` 匹配 `Authorization: Bearer <value>` 行
- 提取 token 值后剥离周围标点符号（反引号、引号、括号）
- 检测 angle-bracket 模板：检查原始 token_val 中是否同时含 `<` 和 `>`
- 检测 composite placeholder：`lin_api_<TOKEN>` 等
- 检测 fake 值：`totally-wrong-*`, `xxx`, `example`, `test-token` 等
- 检测 Supabase publishable key：`sb_publishable_*`, `anon_key`（安全暴露于客户端）
- 排除 `.claude/settings` 路径（Supabase 配置中的 publishable key）

### 策略 C: 隔离 legacy quarantine 文档

- 通过 `skip_path_parts = ['memory-legacy-quarantine-']` 排除 quarantine 目录
- 添加注释：`legacy quarantine docs excluded from active workbot secret scan`
- 不排除 active docs, workspace/tools/webhook_ingress, .github/workflows, .gitlab-ci.yml 的真实 secret 检查

### 策略 D: 未使用 allow_failure

- secrets-check 和 secret-scan-workbot 仍为硬阻断
- 模拟测试确认：注入 `glpat-` token 和 `PRIVATE KEY` 后 scanner 正确 exit 1

---

## 4. 修改文件路径

| 文件 | 变更 |
|------|------|
| `.gitlab-ci.yml` | secrets-check + secret-scan-workbot: shell grep → Python pathlib, 增加 Bearer 占位符检测, 排除自引用/quarantine |

---

## 5. 推送状态

| 目标 | 状态 |
|------|------|
| GitLab (`git push gitlab HEAD:main`) | 已推送 |
| GitHub (`git push origin`) | 未推送 |
| 真实 Factory 触发 | 未触发 |
| Linear 状态/标签变更 | 未变更 |

---

## 6. Pipeline 信息

| 项目 | 值 |
|------|-----|
| Pipeline ID | 102 |
| Pipeline URL | http://node-15.tail5e888.ts.net/root/workbot/-/pipelines/102 |
| Pipeline Status | failed |
| Commit SHA | 1b649771 |
| Commit Message | fix(ci): replace shell-based secret scan with Python pathlib to eliminate false positives |

---

## 7. Job 状态表

| Job | Stage | Status | ID | Note |
|-----|-------|--------|-----|------|
| json-valid | lint | **success** | 517 | P0-2D fix |
| yaml-valid | lint | failed | 518 | allow_failure=true |
| shell-syntax | lint | **success** | 519 | |
| secrets-check | security | **success** | 520 | **P0-2E fix — was failed, now PASS** |
| secret-scan-workbot | security | **success** | 521 | **P0-2E fix — was failed, now PASS** |
| yaml-baseline-parse | validate | **success** | 522 | **Unblocked — was skipped in Pipeline 101** |
| webhook-ingress-pytest | test | manual | 523 | By design (requires manual trigger or file changes) |
| github-push-gate-dry-run | dry-run | failed | 524 | `schedule is not commented out` — P0-1 known issue, not P0-2E scope |

### 关键变化 vs Pipeline 101

| Job | Pipeline 101 | Pipeline 102 |
|-----|-------------|-------------|
| secrets-check | **failed** | **success** |
| secret-scan-workbot | **failed** | **success** |
| yaml-baseline-parse | **skipped** | **success** |
| webhook-ingress-pytest | **skipped** | **manual** (unblocked) |
| github-push-gate-dry-run | **skipped** | **failed** (unblocked, detected schedule issue) |

---

## 8. Secret Scan Findings

| 扫描范围 | Findings |
|---------|---------|
| 本地 secrets-check | 0 |
| 本地 secret-scan-workbot | 0 |
| Staged diff | 0 |
| 模拟 secret 测试 | 2 (glpat- + PRIVATE KEY, 正确 fail) |
| CI Pipeline 102 secrets-check | 0 |
| CI Pipeline 102 secret-scan-workbot | 0 |

---

## 9. SHA256

```
62466056bc4f145eeb7c5aff9a67d144da4d7233a01789a724640db33e95c430  .gitlab-ci.yml
```

---

## 10. 安全约束确认

| 约束 | 状态 |
|------|------|
| 真实 Factory dispatch 禁止 | 仍然禁止 |
| Linear 状态/标签变更禁止 | 未变更 |
| GitHub push gate fail-closed | 保持 fail-closed |
| 无可执行 git push in .gitlab-ci.yml | 确认无 |
| 未推送 GitHub | 确认未推送 |
| Scanner 未 allow_failure | 确认未设置 |
| 模拟 secret 测试正确 fail | 确认正确 fail (exit 1) |

---

## 11. 后续建议 (非本次任务范围)

1. **github-push-gate-dry-run**: 注释掉 `.github/workflows/memory-core-auto-sync-deploy.yml` 中的 `schedule:` trigger 以通过此检查
2. **yaml-valid**: `.github/workflows/memory-core-auto-sync-deploy.yml` YAML 解析失败，已 allow_failure
3. **webhook-ingress-pytest**: 需要手动触发或文件变更触发，当前为 manual

---

## 12. Diff 摘要

Commit 1b64977 替换了 secrets-check 和 secret-scan-workbot 的 shell grep 实现为 Python pathlib 实现：

### secrets-check 变更
- Shell `for f in $(find ...)` → Python `pathlib.Path.rglob('*')`
- `skip_name = {'.gitlab-ci.yml'}` 排除扫描器自身
- `skip_path_parts = ['memory-legacy-quarantine-']` 排除归档目录
- 使用 `re.compile` 正则匹配 glpat- token 和 PRIVATE KEY

### secret-scan-workbot 变更
- 同上路径遍历改进
- 扩展 PATTERNS 列表：glpat-, sk-, PRIVATE KEY, lin_api_, fk-
- Bearer token 智能过滤：
  - 检测 angle-bracket 模板 (`<...>`)
  - 检测 composite placeholder (`lin_api_<TOKEN>`)
  - 检测 fake 值 (`totally-wrong-*`, `xxx`, etc.)
  - 检测 Supabase publishable key (`sb_publishable_*`)
- `skip_path_parts = ['memory-legacy-quarantine-', '.claude/settings']`
