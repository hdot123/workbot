# 🔄 CI Pipeline 验收 — [描述]

> **Pipeline ID**: `<pipeline_id>`
> **GitLab Project**: `<project>`
> **Branch**: `<branch>`
> **Commit SHA**: `<commit_sha>`
> **Trigger**: manual / merge_request / schedule / webhook

---

## Pipeline 信息
| 字段 | 值 |
|------|-----|
| pipeline_id | |
| pipeline_url | |
| triggered_at | |
| duration | |

## Job 清单
| Job Name | Stage | Status | Duration | Log URL |
|----------|-------|--------|----------|---------|
| | | | | |

## 验收标准
- [ ] pipeline_status = success
- [ ] 所有 job_status = success
- [ ] commit_sha 与预期一致
- [ ] branch 与预期一致
- [ ] 无 skipped/canceled job（除非有明确豁免）
- [ ] pipeline 日志无 ERROR 级别异常
- [ ] 代码覆盖率未下降
- [ ] 安全扫描无新增 HIGH/CRITICAL

## 证据快照
| 证据项 | 值 |
|--------|-----|
| pipeline_id | |
| pipeline_status | |
| commit_sha | |
| branch | |
| coverage % | |
| scan_result | |

## 失败处理
- pipeline_status ≠ success → 创建 T6-CIFix 任务
- 单 job 失败 → 记录 job_name + error log + 根因分析

## GitHub Push Gate（如适用）
- [ ] pipeline_status = success 已确认
- [ ] 准备创建 T10-PushGate 任务

## ⚠️ 硬规则
- ❌ pipeline failed/canceled/skipped 均不得标记 Done
- ❌ 100% 禁止绕过 CI 直接推 GitHub
