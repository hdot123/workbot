# 🚪 GitHub Push Gate — [描述]

> **Gate ID**: `GATE-YYYYMMDD-NNN`
> **Status**: pending / approved / rejected / completed

---

## 适用场景
- GitLab CI 通过后同步到 GitHub
- 发布到 GitHub remote
- 本地 GitLab 到 GitHub 的镜像/同步

## 不适用场景
- 未经过 GitLab CI 的代码
- CI failed/canceled/skipped 的代码
- 子代理或人工直接 push GitHub

## 必须证据（11 项）
| # | 证据项 | 值 | 验证 |
|---|--------|-----|------|
| E1 | Linear issue key | | |
| E2 | GitLab project | | |
| E3 | GitLab branch | | |
| E4 | commit_sha | | |
| E5 | pipeline_id | | |
| E6 | pipeline_status | **= success** | |
| E7 | pipeline_url | | |
| E8 | GitHub remote | | |
| E9 | GitHub branch | | |
| E10 | push timestamp | | |
| E11 | push result | success/failed | |

## 硬规则
- ❌ 没有 pipeline_id → 禁止推送
- ❌ pipeline_status ≠ success → 禁止推送
- ❌ commit_sha 不匹配 → 禁止推送
- ❌ branch 不匹配 → 禁止推送
- ❌ Linear issue key 未记录 → 禁止推送
- ❌ Factory 主线程直接 git push → 违规
- ❌ bailian 子代理直接 git push → 违规
- ❌ 人工绕过 GitLab CI → 违规

## 验收标准
- [ ] GitLab CI success 已确认
- [ ] commit_sha 匹配 CI 通过的 commit
- [ ] branch 匹配 CI 通过的 branch
- [ ] Linear 已记录 CI 通过
- [ ] GitHub push 发生在 CI success **之后**
- [ ] 没有绕过 GitLab CI 的 push
- [ ] 推送结果已记录

## 回滚方案
- push 失败 → 记录失败原因，不重试（需重新走 Gate）
- 发现绕过 CI → 立即标记违规，冻结后续同步，回退到 GitLab-only
- GitHub 状态异常 → 回退到 GitLab-only 状态

## ⚠️ 唯一允许路径
```
本地/内部 GitLab → GitLab CI 通过 → GitHub push/sync
```
无例外。不设默认例外。
