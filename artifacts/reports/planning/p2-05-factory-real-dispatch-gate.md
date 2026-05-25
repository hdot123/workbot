# Factory Real-Dispatch Gate

**文档编号**: P2-GATE-005
**版本**: V1.0
**日期**: 2026-05-08
**关联 Linear Issue**: JTO-201
**P2 Project**: P2 — Long-task dry-run + GitLab CI feedback loop
**状态**: 设计稿（dry-run only, real dispatch FORBIDDEN）
**最终结论**: 真实 Factory dispatch 仍 FORBIDDEN

---

## 1. 概述

本文档定义从 dry-run 升级到真实 Factory dispatch 的门控条件。当前所有条件均未满足，真实执行 FORBIDDEN。

**核心原则**：fail-closed，任何 gate 条件不满足即 BLOCKED。

---

## 2. 当前状态

| Gate | 状态 | 说明 |
|------|------|------|
| 真实 Factory dispatch | ❌ FORBIDDEN | 所有 gate 条件未满足 |
| Factory API 调用 | ❌ FORBIDDEN | 不允许 |
| FACTORY_API_KEY 配置 | ❌ FORBIDDEN | 不允许 |

---

## 3. Gate 条件矩阵（10 项）

### Gate 1: GitLab CI Pipeline Success

| 属性 | 值 |
|------|-----|
| 要求 | Pipeline 状态必须为 `success` |
| 验证 | `payload.status == "success"` |
| 失败处理 | BLOCKED，触发修复分派（未超过 max_fix_attempts） |
| 当前状态 | ❌ 未满足 |

### Gate 2: Pipeline ID 可验证

| 属性 | 值 |
|------|-----|
| 要求 | pipeline_id 必须在 GitLab API 中可查询 |
| 验证 | `GET /api/v4/projects/:id/pipelines/:pipeline_id` 返回 200 |
| 失败处理 | BLOCKED，pipeline_id 无效或不可达 |
| 当前状态 | ❌ 未满足 |

### Gate 3: Commit SHA 匹配

| 属性 | 值 |
|------|-----|
| 要求 | pipeline commit_sha 必须匹配 Linear issue 关联的 commit |
| 验证 | `pipeline_commit_sha == linear_issue_commit_sha` |
| 失败处理 | BLOCKED，commit 不匹配 |
| 当前状态 | ❌ 未满足 |

### Gate 4: Linear Canary/Project Scope

| 属性 | 值 |
|------|-----|
| 要求 | Linear issue 必须在 canary project 范围内 |
| 验证 | `issue.project.id in CANARY_PROJECT_IDS` |
| Canary Project | P2 Project (`e8365417-e2d8-4834-ace2-98eff6adeeab`) |
| 失败处理 | BLOCKED，非 canary issue 不允许 |
| 当前状态 | ❌ 未满足 |

### Gate 5: Human/Policy Approval

| 属性 | 值 |
|------|-----|
| 要求 | 必须有明确的人工或 policy 审批 |
| 验证 | `approval.status == "approved"` AND `approval.approver in APPROVERS` |
| 审批方式 | Linear comment approval 或外部审批系统 |
| 当前状态 | ❌ 未满足 |

### Gate 6: Max Fix Attempts 未超过

| 属性 | 值 |
|------|-----|
| 要求 | 自动修复尝试次数 < max_fix_attempts (默认 3) |
| 验证 | `fix_attempt_count < 3` |
| 失败处理 | BLOCKED，等待人工介入 |
| 当前状态 | ✅ 满足（0 次修复） |

### Gate 7: Secret Scan = 0

| 属性 | 值 |
|------|-----|
| 要求 | 所有交付物 secret scan 必须为 0 |
| 验证 | `secret_scan_findings == 0` |
| 失败处理 | BLOCKED，立即停止，清理 secret |
| 当前状态 | ✅ 满足 |

### Gate 8: GitHub Push Gate Fail-Closed

| 属性 | 值 |
|------|-----|
| 要求 | GitHub push 门控必须 fail-closed |
| 验证 | `github_push_forbidden == true` |
| 失败处理 | BLOCKED，push gate 必须始终 fail-closed |
| 当前状态 | ✅ 满足 |

### Gate 9: Rollback Plan Exists

| 属性 | 值 |
|------|-----|
| 要求 | 必须存在明确的回滚计划 |
| 验证 | rollback checklist 存在且完整 |
| 当前状态 | ❌ 未满足（本文档提供 checklist 模板） |

### Gate 10: Acceptance Issue 已通过

| 属性 | 值 |
|------|-----|
| 要求 | 对应的 acceptance issue 必须 PASS |
| 验证 | `acceptance_verdict == "PASS"` |
| 当前状态 | ❌ 未满足（P2-AC-05 正在验收中） |

---

## 4. Gate 评估流程

```
Dispatch Request
  │
  ├── Gate 1: CI Pipeline Success? ── NO → BLOCKED
  ├── Gate 2: Pipeline ID Verifiable? ── NO → BLOCKED
  ├── Gate 3: Commit SHA Match? ── NO → BLOCKED
  ├── Gate 4: Canary Project Scope? ── NO → BLOCKED
  ├── Gate 5: Approval Received? ── NO → BLOCKED
  ├── Gate 6: Fix Attempts < Max? ── NO → BLOCKED
  ├── Gate 7: Secret Scan == 0? ── NO → BLOCKED
  ├── Gate 8: Push Gate Fail-Closed? ── NO → BLOCKED
  ├── Gate 9: Rollback Plan Exists? ── NO → BLOCKED
  ├── Gate 10: Acceptance PASS? ── NO → BLOCKED
  │
  └── ALL GATES PASS → ALLOWED (future only)
```

---

## 5. Blocked Reason Taxonomy

| 代码 | 原因 | 分类 | 恢复 |
|------|------|------|------|
| GATE-001 | CI pipeline 失败 | CI | 修复 pipeline 后重试 |
| GATE-002 | pipeline_id 不可验证 | CI | 检查 GitLab 连接 |
| GATE-003 | commit_sha 不匹配 | DATA | 重新触发 pipeline |
| GATE-004 | 非 canary project | SCOPE | 等待 canary 扩大 |
| GATE-005 | 审批未通过 | POLICY | 获取审批 |
| GATE-006 | 超过 max_fix_attempts | EXECUTION | 人工介入 |
| GATE-007 | Secret 检测 | SECURITY | 清理后重试 |
| GATE-008 | Push gate 未 fail-closed | SECURITY | 修复 gate |
| GATE-009 | 无回滚计划 | OPERATIONS | 创建 rollback plan |
| GATE-010 | Acceptance 未通过 | QA | 修复后重新验收 |

---

## 6. Upgrade Checklist（未来参考）

真实 dispatch 升级需完成：

- [ ] P2-01 ~ P2-08 全部完成并通过验收
- [ ] P2-AC-01 ~ P2-AC-09 全部 PASS
- [ ] GitLab CI pipeline success (dry-run)
- [ ] Linear dry-run comment flow 验证通过
- [ ] Audit upgrade (SQLite → PostgreSQL) 完成
- [ ] Factory API key 配置安全存储
- [ ] Canary project scope 定义
- [ ] Approval workflow 建立
- [ ] Rollback plan 审批通过
- [ ] 安全审计通过

---

## 7. Rollback Checklist（未来参考）

如果真实 dispatch 出现问题，按以下顺序回滚：

1. 立即停止 Factory dispatch
2. 记录 rollback 原因和时间
3. 恢复 Linear issue 到之前状态
4. 清理已创建的 Factory 资源
5. 通知相关人员
6. 审计回滚操作
7. 更新文档和 gate 条件
8. 重新评估是否允许再次 dispatch

---

## 8. 最终结论

**真实 Factory dispatch FORBIDDEN**

当前 10 个 gate 条件中仅有 3 个满足（Gate 6, 7, 8），其余 7 个未满足。

P2 阶段仅允许 dry-run 和 design，不允许任何真实执行。

---

## 9. 不包含 Secret 声明

本文档不包含任何 API key、token、password、secret、private key 或其他敏感信息。

---

**文档结束**
**P2-05 交付物 — Factory Real-Dispatch Gate V1.0**
