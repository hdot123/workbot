# 🛠 [Phase] 开发任务标题

> **Phase**: `M#/P#/H#`
> **Owner**: @owner
> **Type**: feat / fix / refactor / test / chore
> **Branch**: `branch-2` (从 branch-1 创建)

---

## 目标
<一段话描述>

## 变更范围
| 文件/目录 | 变更类型 | 说明 |
|-----------|----------|------|
| | | |

## 验收标准（硬性 — 不满足不得 Done）
- [ ] GitLab CI 通过（pipeline_status = success）
- [ ] 所有新增/修改代码有对应测试
- [ ] 无 lint 错误
- [ ] commit message 符合规范
- [ ] branch-2 已 merge 到 branch-1

## 验收标准（软性）
- [ ] 代码已 review
- [ ] 文档已更新（如适用）

## 回滚策略
<描述 revert merge commit 的方式>

## 证据
| 项目 | 值 |
|------|-----|
| commit_sha | |
| pipeline_id | |
| pipeline_status | |
| pipeline_url | |

## ⚠️ 硬规则
- ❌ 100% 禁止直接推送 GitHub
- ✅ 唯一路径：branch-2 → branch-1 → GitLab CI success → GitHub push/sync（如需发布）
- 普通开发任务 **不要求** raw/canonical/n8n/Supabase 证据
