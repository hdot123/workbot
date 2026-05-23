# Subagent Long-task Execution Policy

**文档编号**: P2-POLICY-002
**版本**: V1.0
**日期**: 2026-05-08
**关联 Linear Issue**: JTO-198
**P2 Project**: P2 — Long-task dry-run + GitLab CI feedback loop
**状态**: 设计稿（dry-run only）

---

## 1. 概述

本文档定义 Factory 长任务中子代理的执行策略，包括 checkpoint、runlog、heartbeat、停止条件和父代理恢复机制。

**核心原则**：子代理的一切行为必须可审计、可恢复、可验证。

---

## 2. Checkpoint 策略

### 2.1 Checkpoint 文件格式

```json
{
  "checkpoint_version": "1.0",
  "issue_key": "JTO-XXX",
  "phase": 3,
  "phase_name": "acceptance_audit",
  "status": "complete",
  "timestamp": "2026-05-08T10:30:00Z",
  "evidence_summary": "All 12 test cases passed, secret scan 0 findings",
  "artifacts": [
    "p2-ac-XX-report.md",
    "workspace/memory/tmp/checkpoints/JTO-XXX/phase-3.json"
  ],
  "next_phase": null,
  "can_proceed": true,
  "block_reason": null
}
```

### 2.2 Checkpoint 路径规范

```
workspace/memory/tmp/checkpoints/<issue_key>/phase-<N>.json
```

- `<issue_key>`: Linear issue 标识符（如 `JTO-198`）
- `<N>`: 阶段编号，从 1 开始
- 文件必须以 `.json` 结尾
- 每个阶段最多 1 个 checkpoint 文件

### 2.3 Checkpoint 写入时机

| 时机 | 必须写入 | 字段要求 |
|------|---------|---------|
| 阶段开始 | 可选 | `status: "started"` |
| 阶段完成 | **必须** | `status: "complete"`, `evidence_summary` |
| 阶段失败 | **必须** | `status: "failed"`, `block_reason` |
| 子代理停止 | **必须** | `status: "stopped"`, `block_reason` |

### 2.4 Checkpoint 验证规则

```
INVARIANT: 阶段完成 → 必须有 checkpoint (status=complete)
INVARIANT: checkpoint 缺失 → BLOCKED (STOP-008)
INVARIANT: checkpoint 阶段编号必须递增
INVARIANT: 最后 checkpoint 的 issue_key 必须匹配当前任务
```

---

## 3. Runlog 策略

### 3.1 Runlog 格式 (JSONL)

每行一条 JSON 记录：

```json
{"timestamp":"2026-05-08T10:25:30Z","action":"read_file","command_or_api":"Read /Users/busiji/workbot/file.md","result_summary":"Read 356 lines","duration_ms":45}
{"timestamp":"2026-05-08T10:25:31Z","action":"edit_file","command_or_api":"Edit p2-01-contract.md","result_summary":"Added section 5","duration_ms":120}
{"timestamp":"2026-05-08T10:26:00Z","action":"execute_command","command_or_api":"rg -i 'secret' p2-01.md","result_summary":"0 findings","duration_ms":350}
```

### 3.2 Runlog 路径规范

```
workspace/memory/tmp/runlogs/<issue_key>/runlog.jsonl
```

### 3.3 Runlog 字段定义

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `timestamp` | ISO-8601 | ✅ | 动作执行时间 |
| `action` | string | ✅ | 动作类型 |
| `command_or_api` | string | ✅ | 执行的命令或 API 调用 |
| `result_summary` | string | ✅ | 执行结果摘要（脱敏） |
| `duration_ms` | int | ✅ | 执行耗时（毫秒） |

### 3.4 允许的 action 类型

| Action | 说明 | 示例 |
|--------|------|------|
| `read_file` | 读取文件 | Read tool |
| `edit_file` | 编辑文件 | Edit/Create tool |
| `execute_command` | 执行 shell 命令 | Execute tool |
| `api_call` | 调用外部 API | Linear, GitLab |
| `tool_call` | 调用其他工具 | Grep, Glob |
| `phase_start` | 阶段开始 | 标记阶段切换 |
| `phase_end` | 阶段完成 | 标记阶段完成 |
| `error` | 错误发生 | 错误记录 |
| `stop` | 子代理停止 | 停止原因 |

### 3.5 Runlog 验收规则

Acceptance 子代理必须审查：

1. **完整性**: 每个阶段有 phase_start → phase_end 配对
2. **无遗漏**: 所有 deliverable 的创建/编辑操作有记录
3. **无 secret**: result_summary 中无敏感信息泄露
4. **时间连续**: 无超过 120 秒的静默间隙（除非长命令标记）
5. **错误可见**: 所有 error 有对应 resolution 或 stop

---

## 4. Heartbeat 策略

### 4.1 Heartbeat 格式

```json
{
  "heartbeat_version": "1.0",
  "timestamp": "2026-05-08T10:26:00Z",
  "subagent_id": "bailian-worker-1",
  "phase": 2,
  "phase_name": "implementation",
  "progress_pct": 45,
  "status": "running",
  "next_action": "Reading acceptance criteria from Linear",
  "estimated_remaining_seconds": 300
}
```

### 4.2 Heartbeat 输出策略

| 参数 | 值 | 说明 |
|------|-----|------|
| 间隔 | 每 60 秒 | 子代理必须每 60 秒输出一次心跳 |
| 最大静默 | 120 秒 | 超过 120 秒无心跳 → BLOCKED (STOP-007) |
| 输出目标 | 文件 + 日志 | 写入 `workspace/memory/tmp/heartbeats/<issue_key>/` |
| 格式 | JSON | 单行 JSON，便于解析 |

### 4.3 Heartbeat 路径

```
workspace/memory/tmp/heartbeats/<issue_key>/heartbeat-<N>.json
```

`<N>` 为心跳序号，从 1 开始递增。

### 4.4 长命令 Heartbeat 规则

当子代理执行长命令（预期 > 60 秒）时：

1. 必须在命令启动前输出 "pre-command heartbeat"
2. 使用 `tee` / `timeout` / `verbose` 确保输出可见
3. 命令结束后立即输出 "post-command heartbeat"
4. 如果命令无输出，必须在命令执行期间写入临时心跳文件

---

## 5. 长命令规范

### 5.1 长命令判定

| 预期耗时 | 分类 | 要求 |
|----------|------|------|
| < 30 秒 | 短命令 | 正常执行 |
| 30-120 秒 | 中命令 | 执行前标记，结束后验证 |
| > 120 秒 | 长命令 | 必须 tee + timeout + 心跳 |

### 5.2 长命令执行模板

```bash
# 1. 前置心跳
echo '{"timestamp":"...","action":"long_command_start","command":"...","estimated_seconds":300}' >> runlog.jsonl

# 2. 使用 tee + timeout 执行
timeout 600s bash -c 'your_long_command_here 2>&1 | tee /tmp/command-output.log'
EXIT_CODE=$?

# 3. 后置心跳 + 结果记录
echo '{"timestamp":"...","action":"long_command_end","exit_code":'$EXIT_CODE',"output_lines":'$(wc -l < /tmp/command-output.log)'}' >> runlog.jsonl
```

### 5.3 禁止的长命令行为

| 行为 | 判定 | 原因 |
|------|------|------|
| 无 tee 的后台命令 | BLOCKED | 输出丢失，无法审计 |
| 无 timeout 的命令 | BLOCKED | 可能无限挂起 |
| 静默超过 120 秒 | BLOCKED | 心跳超时 |
| 无限循环 | BLOCKED | 违反 max_fix_attempts |

---

## 6. SubagentStop 处理原则

### 6.1 停止分类

| 类型 | 定义 | 必须有 |
|------|------|--------|
| 有证据停止 | 停止时提供了完整证据链 | 最后 checkpoint + runlog 尾部 + 停止原因 |
| 无证据停止 | 停止时无任何记录 | ❌ 禁止 |

### 6.2 无证据停止 = BLOCKED

```
IF subagent_stopped AND NOT has_last_checkpoint AND NOT has_recent_runlog:
    → BLOCKED (EXE-001)
    → 父代理必须调查停止原因
    → 不可直接进入下一个 issue
```

### 6.3 有证据停止 = CONDITIONAL STOP

```
IF subagent_stopped AND has_last_checkpoint AND has_recent_runlog:
    → CONDITIONAL STOP
    → 父代理审查证据
    → 决定：恢复 / 重新分派 / BLOCKED
```

---

## 7. Block / Allow 停止条件矩阵

### 7.1 Block 条件（必须停止）

| 条件 | 代码 | 触发 | 恢复 |
|------|------|------|------|
| dry_run != true | SAF-001 | payload 验证失败 | 重新生成 payload |
| github_push_forbidden == false | SAF-002 | payload 验证失败 | 重新生成 payload |
| Secret 检测 | SAF-003 | 任何输出含 secret | 清理后重新执行 |
| 无证据停止 | EXE-001 | 子代理无记录停止 | 调查 + 重新分派 |
| 心跳超时 | EXE-002 | 120 秒无心跳 | kill + 从 checkpoint 恢复 |
| Checkpoint 缺失 | EXE-003 | 阶段完成无 checkpoint | BLOCKED 进入下一阶段 |
| 超过 max_fix_attempts | EXE-004 | 自动修复超过 3 次 | 等待人工介入 |
| CI pipeline 失败 | CI-001 | GitLab pipeline 失败 | 触发修复分派 |

### 7.2 Allow 条件（可继续）

| 条件 | 要求 |
|------|------|
| 阶段完成 | checkpoint (status=complete) + runlog 完整 |
| 心跳正常 | 最近心跳 < 60 秒 |
| Secret scan | 0 findings |
| 无错误 | 或所有错误已解决 |
| 未超过 max_fix_attempts | fix_count < 3 |

---

## 8. 父代理恢复中断任务规则

### 8.1 恢复流程

```
子代理中断
  │
  ├── 有证据停止？
  │     ├── YES → 审查最后 checkpoint
  │     │        ├── phase N complete → 从 phase N+1 恢复
  │     │        ├── phase N failed → 重新执行 phase N
  │     │        └── 无 checkpoint → BLOCKED
  │     │
  │     └── NO → BLOCKED (EXE-001)
  │               ├── 调查 runlog 尾部
  │               ├── 检查最后心跳
  │               └── 决定：重新分派 / 人工介入
  │
  └── 恢复执行
        ├── 新子代理从 checkpoint 继承上下文
        ├── 重新验证 stop condition
        └── 继续执行
```

### 8.2 恢复上下文传递

新子代理必须接收：

1. 原始 Linear issue 描述
2. 最后 checkpoint（含 phase 信息）
3. 完整 runlog（用于审计）
4. 停止原因（如有）
5. 已完成的阶段列表

---

## 9. Acceptance 子代理审查 Runlog 规则

### 9.1 审查清单

| 检查项 | 通过标准 |
|--------|---------|
| 阶段完整性 | phase_start/phase_end 配对完整 |
| 操作可见性 | 所有 deliverable 创建/编辑有 runlog 记录 |
| 时间连续性 | 无 >120 秒未解释的静默间隙 |
| 错误透明度 | 所有 error 有记录且有 resolution/stop |
| Secret 安全 | result_summary 中无 API key/token/password |
| 命令合法性 | 无禁止命令（git push, Factory API call 等） |

### 9.2 审查输出格式

```json
{
  "runlog_audit": {
    "total_entries": 150,
    "phase_start_count": 3,
    "phase_end_count": 3,
    "error_count": 2,
    "error_resolved_count": 2,
    "max_silence_seconds": 45,
    "secret_findings": 0,
    "prohibited_commands": 0,
    "verdict": "PASS"
  }
}
```

### 9.3 审查失败处理

如果 runlog 审计不通过：

1. 输出详细失败原因
2. BLOCKED 验收报告
3. 返回 implementation 子代理修复
4. 不进入下一个 issue

---

## 10. 无限循环防护

### 10.1 防护规则

| 规则 | 实现 |
|------|------|
| max_fix_attempts | 全局限制 3 次，每次尝试必须有不同修复策略 |
| 修复策略不重复 | 每次修复必须记录策略描述，不可重复相同策略 |
| 阶段超时 | 单阶段执行超过 15 分钟自动停止 |
| 心跳监控 | 心跳丢失触发停止 |

### 10.2 修复循环日志

```json
{
  "fix_attempt": 2,
  "max_attempts": 3,
  "strategy": "Added missing checkpoint write after phase 3",
  "previous_strategies": ["Added error handling to phase 2"],
  "timestamp": "2026-05-08T11:00:00Z"
}
```

---

## 11. 不包含 Secret 声明

本文档不包含任何 API key、token、password、secret、private key 或其他敏感信息。

所有示例均为结构定义和 schema 描述。

---

**文档结束**
**P2-02 交付物 — Subagent Long-task Execution Policy V1.0**
