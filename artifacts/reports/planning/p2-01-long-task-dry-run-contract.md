# Long-task Dry-run Contract

**文档编号**: P2-CONTRACT-001
**版本**: V1.0
**日期**: 2026-05-08
**关联 Linear Issue**: JTO-197
**P2 Project**: P2 — Long-task dry-run + GitLab CI feedback loop
**状态**: 设计稿（dry-run only）
**结论**: 真实 Factory dispatch 仍 FORBIDDEN

---

## 1. 概述

本文档定义 Factory 长任务（long-task）dry-run 的任务契约。所有 P2 长任务必须遵守此契约，任何违反均导致任务 BLOCKED。

**核心原则**：长任务必须可中断、可审计、可回滚，且在 dry-run 阶段不允许任何真实执行。

---

## 2. 契约字段定义

### 2.1 顶层字段清单

| # | 字段 | 类型 | 默认值 | 说明 |
|---|------|------|--------|------|
| 1 | `long_task` | bool | `true` | 标记此任务为长任务（运行时间 > 5 分钟预期） |
| 2 | `dry_run` | bool | `true` | 必须为 true；仅在 dry-run 模式下运行 |
| 3 | `no_write` | bool | `true` | 禁止写入生产文件系统 |
| 4 | `no_push` | bool | `true` | 禁止推送到任何远程仓库 |
| 5 | `no_deploy` | bool | `true` | 禁止部署到任何环境 |
| 6 | `github_push_forbidden` | bool | `true` | GitHub push 门控，fail-closed |
| 7 | `required_ci` | string | `"gitlab"` | 指定 CI 提供方为 GitLab |
| 8 | `max_fix_attempts` | int | `3` | 最大自动修复尝试次数 |
| 9 | `checkpoint_required` | bool | `true` | 要求子代理写入阶段性 checkpoint |
| 10 | `runlog_required` | bool | `true` | 要求子代理维护执行日志 |
| 11 | `heartbeat_required` | bool | `true` | 要求子代理定期发送心跳 |
| 12 | `acceptance_required` | bool | `true` | 要求独立验收子代理 |

### 2.2 字段验证规则

```
INVARIANT: long_task == true IMPLIES checkpoint_required == true
INVARIANT: long_task == true IMPLIES runlog_required == true
INVARIANT: long_task == true IMPLIES heartbeat_required == true
INVARIANT: dry_run == true IMPLIES no_write == true
INVARIANT: dry_run == true IMPLIES no_push == true
INVARIANT: dry_run == true IMPLIES no_deploy == true
INVARIANT: dry_run == true IMPLIES github_push_forbidden == true
INVARIANT: acceptance_required == true IMPLIES separate_acceptance_agent == true
INVARIANT: max_fix_attempts > 0 AND max_fix_attempts <= 5
```

---

## 3. Stop Condition

### 3.1 全局 Stop Condition

长任务在以下任一条件触发时必须立即停止：

| 条件 ID | 条件 | 类型 |
|---------|------|------|
| STOP-001 | `dry_run` 字段不存在或为 `false` | BLOCKED |
| STOP-002 | `github_push_forbidden` 为 `false` | BLOCKED |
| STOP-003 | `required_ci` 不为 `"gitlab"` | BLOCKED |
| STOP-004 | `max_fix_attempts` 超过限制 | BLOCKED |
| STOP-005 | 检测到 secret 泄露 | BLOCKED |
| STOP-006 | 子代理无证据停止（SubagentStop） | BLOCKED |
| STOP-007 | 心跳超时（> 120 秒无心跳） | BLOCKED |
| STOP-008 | checkpoint 缺失（阶段完成后无 checkpoint） | BLOCKED |
| STOP-009 | GitLab CI pipeline 失败 | CONDITIONAL STOP |
| STOP-010 | 人工干预指令 | STOP |

### 3.2 Stop Condition 评估流程

```
任务启动
  ├── 验证 dry_run == true         → FAIL: STOP-001
  ├── 验证 github_push_forbidden   → FAIL: STOP-002
  ├── 验证 required_ci             → FAIL: STOP-003
  ├── 进入执行阶段
  │     ├── 每 60s 检查心跳        → TIMEOUT: STOP-007
  │     ├── 阶段完成检查 checkpoint → MISSING: STOP-008
  │     ├── 子代理停止              → NO-EVIDENCE: STOP-006
  │     ├── secret scan             → FOUND: STOP-005
  │     └── fix attempt count       → EXCEEDED: STOP-004
  └── 完成 → 等待 acceptance
```

---

## 4. Blocked Reason 分类法

### 4.1 分类层级

| Category | Code | Reason | Resolution |
|----------|------|--------|------------|
| SAFETY | `SAF-001` | dry_run flag missing or false | 不允许执行，必须重新生成 payload |
| SAFETY | `SAF-002` | github_push_forbidden is false | 不允许执行，push gate 必须 fail-closed |
| SAFETY | `SAF-003` | Secret detected in payload/log | 立即停止，清理 secret 后重新生成 |
| SAFETY | `SAF-004` | Production issue detected | 跳过，仅 canary project issue 允许 |
| EXECUTION | `EXE-001` | Subagent stopped without evidence | 检查 runlog，恢复或重新分派 |
| EXECUTION | `EXE-002` | Heartbeat timeout (>120s) | 检查子代理状态，kill or recover |
| EXECUTION | `EXE-003` | Checkpoint missing | 阻断进入下一阶段 |
| EXECUTION | `EXE-004` | Max fix attempts exceeded | 停止自动修复，等待人工介入 |
| CI | `CI-001` | GitLab pipeline failed | 自动触发修复分派（未超过 max_fix_attempts） |
| CI | `CI-002` | Pipeline result unavailable | 等待重试，不标记完成 |
| ACCEPTANCE | `ACC-001` | Acceptance issue not found | 阻断关闭 |
| ACCEPTANCE | `ACC-002` | Acceptance subagent reported FAIL | 返回执行子代理修复 |
| ACCEPTANCE | `ACC-003` | Same subagent doing execution + acceptance | BLOCKED（必须独立验收） |

### 4.2 Blocked 输出格式

```json
{
  "blocked": true,
  "reason_code": "EXE-001",
  "reason_category": "EXECUTION",
  "message": "Subagent stopped without evidence at phase 2",
  "evidence": {
    "last_checkpoint": "phase-1-complete",
    "runlog_last_entry": "2026-05-08T10:23:45Z",
    "heartbeat_last_seen": "2026-05-08T10:23:40Z"
  },
  "resolution": "Check runlog for subagent exit reason, recover from phase-1-complete checkpoint"
}
```

---

## 5. 禁止真实执行规则

### 5.1 绝对禁止（在 dry-run 阶段不可覆盖）

| Rule ID | Rule | Rationale |
|---------|------|-----------|
| FORBID-001 | `dry_run` 必须为 `true` | P2 阶段仅 dry-run |
| FORBID-002 | 禁止调用 Factory API（真实 dispatch） | 仅本地模拟 |
| FORBID-003 | 禁止 `git push` 到任何 remote | GitHub push gate fail-closed |
| FORBID-004 | 禁止写入生产数据库 | no_write=true |
| FORBID-005 | 禁止修改 Linear issue 状态 | comment-only |
| FORBID-006 | 禁止修改 Linear issue 标签 | comment-only |
| FORBID-007 | 禁止创建 webhook | 不修改基础设施 |
| FORBID-008 | 禁止创建 APISIX route | 不修改基础设施 |
| FORBID-009 | 禁止输出 secret/token/password | secret scan = 0 |
| FORBID-010 | 禁止配置 FACTORY_API_KEY | 不允许真实 dispatch |

### 5.2 真实执行升级前置条件（未来参考）

真实执行升级需满足以下全部条件（P2-05 定义）：

1. ✅ GitLab CI pipeline success
2. ✅ pipeline_id 可验证
3. ✅ commit_sha 匹配
4. ✅ Linear issue 在 canary/project 范围内
5. ✅ Human approval 或明确 policy approval
6. ✅ max_fix_attempts 未超过
7. ✅ Secret scan = 0
8. ✅ GitHub push gate 仍 fail-closed
9. ✅ Rollback plan exists
10. ✅ Acceptance issue 已通过

**当前状态：以上条件均未满足，真实执行 FORBIDDEN。**

---

## 6. Payload 差异表：P1 Dispatch Payload vs P2 Long-task Dry-run Contract

### 6.1 新增字段（P2 独有）

| 字段 | P1 | P2 | 说明 |
|------|-----|-----|------|
| `long_task` | ❌ 不存在 | ✅ `true` | P2 引入长任务标记 |
| `checkpoint_required` | ❌ 不存在 | ✅ `true` | P2 要求阶段性 checkpoint |
| `runlog_required` | ❌ 不存在 | ✅ `true` | P2 要求执行日志 |
| `heartbeat_required` | ❌ 不存在 | ✅ `true` | P2 要求心跳信号 |
| `acceptance_required` | ❌ 不存在 | ✅ `true` | P2 要求独立验收子代理 |
| `max_fix_attempts` | 存在于 `loop_guard_policy` | ✅ 顶层字段 `3` | P2 提升为顶层契约字段 |
| `stop_condition` | 存在于 `stop_condition` dict | ✅ 扩展 STOP-001~010 | P2 新增长任务特有 stop condition |
| `blocked_reason` | ❌ 不存在 | ✅ 分类法 SAF/EXE/CI/ACC | P2 引入结构化 blocked reason |

### 6.2 变更字段

| 字段 | P1 值 | P2 值 | 说明 |
|------|-------|-------|------|
| `dispatch_type` | `"factory_main_thread"` | `"factory_long_task"` | P2 区分长任务类型 |
| `stop_condition` | 3 条（P1 safety） | 10 条（含长任务 safety） | P2 扩展 stop condition |
| `subagent_policy` | 通用 subagent | 含 checkpoint/runlog/heartbeat 策略 | P2 增强子代理约束 |

### 6.3 保留字段（不变）

| 字段 | P1 | P2 | 说明 |
|------|-----|-----|------|
| `dry_run` | `true` | `true` | 保持 dry-run |
| `no_write` | `true` | `true` | 保持禁止写入 |
| `no_push` | `true` | `true` | 保持禁止推送 |
| `no_deploy` | `true` | `true` | 保持禁止部署 |
| `github_push_forbidden` | `true` | `true` | 保持 push gate |
| `required_ci` | `"gitlab"` | `"gitlab"` | 保持 GitLab CI |
| `main_thread_policy` | 原有 | 原有 + 长任务协调 | P2 增加长任务协调职责 |
| `ci_policy` | 原有 | 原有 | 保持不变 |
| `loop_guard_policy` | 原有 | 原有 | 保持不变 |
| `source_event` | 原有 | 原有 | 保持不变 |

### 6.4 完整 P2 Long-task Payload 示例

```json
{
  "dispatch_mode": "dry_run",
  "dispatch_type": "factory_long_task",
  "dispatch_id": "disp_<uuid>",
  "generated_at": "<ISO-8601>",

  "long_task": true,
  "dry_run": true,
  "no_write": true,
  "no_push": true,
  "no_deploy": true,
  "github_push_forbidden": true,
  "required_ci": "gitlab",
  "max_fix_attempts": 3,
  "checkpoint_required": true,
  "runlog_required": true,
  "heartbeat_required": true,
  "acceptance_required": true,

  "stop_condition": {
    "STOP-001": "dry_run must be true",
    "STOP-002": "github_push_forbidden must be true",
    "STOP-003": "required_ci must be gitlab",
    "STOP-004": "max_fix_attempts exceeded",
    "STOP-005": "secret detected",
    "STOP-006": "subagent stopped without evidence",
    "STOP-007": "heartbeat timeout >120s",
    "STOP-008": "checkpoint missing after phase completion",
    "STOP-009": "GitLab CI pipeline failed",
    "STOP-010": "human intervention"
  },

  "linear_issue_id": "<issue_id>",
  "linear_issue_key": "JTO-XXX",
  "title": "<issue title>",
  "description": "<issue description>",
  "acceptance_criteria": ["<extracted from description>"],
  "project_id": "<project_id>",
  "project_name": "P2 — Long-task dry-run + GitLab CI feedback loop",
  "repo": "busiji/workbot",
  "target_branch": "branch-2",
  "suggested_branch_name": "factory/jto-xxx-<slug>",

  "ci_required": true,
  "gitlab_required": true,
  "max_bailian_agents": 10,
  "min_bailian_agents": 1,
  "required_review_agents": 1,

  "main_thread_policy": {
    "must_not_implement_code": true,
    "responsibilities": [
      "understand_goal", "decompose_tasks", "dispatch_subagents",
      "supervise", "summarize", "final_acceptance",
      "monitor_heartbeats", "verify_checkpoints", "review_runlogs"
    ],
    "must_summarize_after_subagents": true,
    "long_task_coordination": {
      "phase_decomposition_required": true,
      "checkpoint_verification_between_phases": true,
      "heartbeat_monitoring_interval_seconds": 60,
      "runlog_audit_on_completion": true
    }
  },

  "subagent_policy": {
    "implementation_by_bailian_only": true,
    "min_bailian_agents": 1,
    "max_bailian_agents": 10,
    "required_review_agents": 1,
    "recommended_split": ["development", "tests", "security", "documentation", "acceptance_audit"],
    "checkpoint_policy": {
      "format": "json",
      "fields": ["phase", "status", "timestamp", "evidence_summary"],
      "path_pattern": "workspace/memory/tmp/checkpoints/<issue_key>/phase-<N>.json"
    },
    "runlog_policy": {
      "format": "jsonl",
      "fields": ["timestamp", "action", "command_or_api", "result_summary", "duration_ms"],
      "path_pattern": "workspace/memory/tmp/runlogs/<issue_key>/runlog.jsonl"
    },
    "heartbeat_policy": {
      "interval_seconds": 60,
      "max_silence_seconds": 120,
      "format": "json",
      "fields": ["timestamp", "subagent_id", "phase", "progress_pct", "status"]
    }
  },

  "acceptance_policy": {
    "linear_acceptance_criteria_required": true,
    "gitlab_ci_must_pass": true,
    "review_subagent_must_report": "PASS_or_FAIL",
    "acceptance_subagent_must_be_independent": true,
    "acceptance_issue_id": "<P2-AC-XX issue_id>"
  },

  "blocked_reason_taxonomy": {
    "SAF-001": "dry_run flag missing or false",
    "SAF-002": "github_push_forbidden is false",
    "SAF-003": "Secret detected",
    "SAF-004": "Production issue detected",
    "EXE-001": "Subagent stopped without evidence",
    "EXE-002": "Heartbeat timeout",
    "EXE-003": "Checkpoint missing",
    "EXE-004": "Max fix attempts exceeded",
    "CI-001": "GitLab pipeline failed",
    "CI-002": "Pipeline result unavailable",
    "ACC-001": "Acceptance issue not found",
    "ACC-002": "Acceptance subagent reported FAIL",
    "ACC-003": "Same subagent doing execution + acceptance"
  },

  "source_event": {
    "canonical_event_id": "<event_id>",
    "idempotency_key": "<idempotency_key>",
    "raw_body_sha256": "<sha256>"
  }
}
```

---

## 7. 与 P1 Dispatch Payload 差异总结

| 维度 | P1 | P2 |
|------|-----|-----|
| 任务类型 | 短任务（单次 dispatch） | 长任务（多阶段执行） |
| dispatch_type | `factory_main_thread` | `factory_long_task` |
| 子代理监控 | 无 | checkpoint + runlog + heartbeat |
| Stop condition | 3 条（P1 safety） | 10 条（含执行监控） |
| Blocked reason | 无结构化分类 | SAF/EXE/CI/ACC 分类法 |
| 验收 | 内嵌于 acceptance_policy | 独立 acceptance issue + 独立子代理 |
| 修复循环 | max_fix_attempts 在 loop_guard | max_fix_attempts 提升为顶层契约 |
| 真实执行 | FORBIDDEN | FORBIDDEN（条件未满足） |

---

## 8. 不包含 Secret 声明

本文档不包含任何 API key、token、password、secret、private key 或其他敏感信息。

所有字段值均为布尔标记、枚举字符串、整数计数或结构定义。

---

**文档结束**
**P2-01 交付物 — Long-task Dry-run Contract V1.0**
