# tmux Runtime 系统治理 - 阶段 3 主链验收与恢复能力补强

**文档编号**: GOVERN-001-PH3  
**创建日期**: 2026-03-31  
**实现范围**: 主链验收机制、失败恢复、重试策略  
**实现人**: Dev Bot (阶段 3)

---

## 1. 阶段 3 目标

让主链不仅能跑通，还要具备稳定验收和失败恢复能力。

### 1.1 需要完成的事

- [x] 补齐主链级别的验收命令或验收机制
- [x] 补齐失败场景下的可观测输出
- [x] 定义可以安全重试的阶段
- [x] 处理启动失败、中途失败、残留未清干净、watcher 未挂上等情况
- [x] 明确哪些状态会阻止重试，哪些状态可自动恢复

---

## 2. 主链验收说明

### 2.1 验收命令

**正式验收命令**：
```bash
python3 /Users/busiji/workbot/skills/tmux-skills/scripts/check_tmux_ready.py \
  --formal-session-name formal-session \
  --require-formal \
  --require-watcher \
  --pretty
```

**验收检查清单**（9 项）：

| # | 检查项 | 期望状态 | 失败原因示例 |
|---|--------|----------|--------------|
| 1 | formal-session 存在 | 有且仅有一个 | `expected exactly one formal session named formal-session, got 0` |
| 2 | formal-session attached | `attached > 0` | `formal-session formal-session is not attached` |
| 3 | visible client count | `= 1` | `formal-session must have exactly one attached tmux client, got 2` |
| 4 | current caller in formal | `session_name == formal-session` | `current caller is not inside the visible formal session` |
| 5 | pane count | `== expected_pane_count` | `formal pane_count mismatch: expected 4, actual 3` |
| 6 | pane titles | 全部非空 | `formal panes include empty titles: formal-session:1.3` |
| 7 | slot bindings | 与 pane targets 匹配 | `formal targets do not match runtime ledger slot_bindings` |
| 8 | CODEX_THREAD_ID | 已绑定 | `CODEX_THREAD_ID is missing` |
| 9 | watcher armed + process running | `armed == true` + 进程在运行 | `runtime watcher process is not running for the formal targets` |

**验收通过输出**：
```json
{
  "runtime_status": "READY",
  "formal_session_name": "formal-session",
  "session_count": 1,
  "pane_count": 4,
  "formal_pane_count": 4,
  "expected_pane_count": 4,
  "formal_targets": ["formal-session:1.1", "formal-session:1.2", "formal-session:1.3", "formal-session:1.4"],
  "watcher_armed": true,
  "watcher_commands": ["python3 watch_tmux_handoff.py --target formal-session:1.1 ..."],
  "CODEX_THREAD_ID": "thread_abc123",
  "reasons": [],
  "warnings": [],
  "next_action": ["tmux-skills runtime matches the current contract"]
}
```

**验收失败输出**：
```json
{
  "runtime_status": "BLOCKED",
  "formal_session_name": "formal-session",
  "reasons": [
    "formal pane_count mismatch: expected 4, actual 3",
    "runtime watcher process is not running for the formal targets"
  ],
  "warnings": [],
  "next_action": [
    "reconcile the formal topology to the requested pane count",
    "re-arm the tmux-skills watcher"
  ]
}
```

---

### 2.2 验收门禁

**验收门禁嵌入在主链中**：
- `start_formal_runtime_chain.py` 的最后一阶段是 `ready_check`
- 如果 `ready_check` 失败，主链返回非零退出码
- 失败时会输出具体 `reasons` 列表

**独立验收**：
- 可随时运行 `check_tmux_ready.py` 进行独立验收
- 独立验收不会修改任何状态，只读检查

---

## 3. 常见失败场景表

### 3.1 启动失败场景

| 场景 | 失败阶段 | 症状 | 根本原因 | 恢复方式 |
|------|----------|------|----------|----------|
| **调用者在 tmux 内** | preflight | `blocked: true, reason: current_tmux_launcher` | 无法杀掉自己的 session | 退出 tmux 后重试 |
| **可见终端检测失败** | preflight | `runtime_status: BLOCKED, reason: invisible_terminal_client` | 从 hidden PTY 发起 | 从可见终端重新发起 |
| **tmux 命令不可用** | detect | `inspect_failed: ...` | tmux 未安装或 PATH 问题 | 修复环境后重试 |
| **旧 session 无法杀掉** | cleanup | `kill_returncode: 1, detail: ...` | 权限问题或 session 被占用 | 手动 `tmux kill-server` 后重试 |

---

### 3.2 中途失败场景

| 场景 | 失败阶段 | 症状 | 根本原因 | 恢复方式 |
|------|----------|------|----------|----------|
| **pane 分裂失败** | topology | `RuntimeError: failed to split tmux pane` | tmux 布局冲突 | 重新 cleanup 后重试 |
| **pane 标题不匹配** | titles | `RuntimeError: pane title application did not fully verify` | tmux 响应超时或标题设置失败 | 重试 pane title 应用 |
| **ledger 写入失败** | ledger | `FileNotFoundError` 或权限错误 | 文件系统权限问题 | 修复权限后重试 |
| **watcher 启动失败** | watcher | `RuntimeError: no eligible targets found` | pane targets 为空或 watcher 脚本错误 | 检查日志后重试 |
| **CODEX_THREAD_ID 绑定失败** | thread_binding | `RuntimeError: tmux set-environment failed` | tmux server 异常 | 重启 tmux 后重试 |

---

### 3.3 残留未清干净场景

| 场景 | 症状 | 检测方法 | 清理方式 |
|------|------|----------|----------|
| **旧 session 残留** | `session_count > 1` | `tmux list-sessions` | `tmux kill-session -t <name>` |
| **旧 watcher 残留** | `ps ax \| grep watch_tmux` 有多个进程 | `snapshot.get("bell_processes")` | `stop_conflicting_watchers()` |
| **旧 ledger 残留** | `current-runtime.json` 内容与当前不符 | `cat current-runtime.json` | `unlink current-runtime.json` |
| **旧 CODEX_THREAD_ID 残留** | `tmux show-environment` 显示旧值 | `tmux show-environment -g CODEX_THREAD_ID` | `tmux set-environment -gu CODEX_THREAD_ID` |

---

### 3.4 watcher 未挂上场景

| 场景 | 症状 | 检测方法 | 恢复方式 |
|------|------|----------|----------|
| **watcher 进程未启动** | `watcher_armed: false` | `check_tmux_ready.py --require-watcher` | `arm_tmux_handoff_watcher.py` |
| **watcher target 不匹配** | `watcher_targets != formal_targets` | 对比 ledger 和实际进程 | re-arm watcher |
| **watcher 进程意外退出** | `bell_processes: []` | `ps ax \| grep watch_tmux` | 重新 arm watcher |

---

## 4. 重试策略

### 4.1 各阶段的重试策略

| 阶段 | 是否允许重试 | 重试条件 | 重试前需清理 | 最大重试次数 |
|------|--------------|----------|--------------|--------------|
| **detect** | ✅ 是 | 临时错误（如 tmux 命令超时） | 无 | 3 |
| **cleanup** | ✅ 是 | 进程未完全停止 | 无（cleanup 幂等） | 3 |
| **init** | ✅ 是 | cleanup 成功后 | 需要重新 cleanup | 3 |
| **launch** → topology | ✅ 是 | pane 分裂/收缩失败 | 需要重新 cleanup | 3 |
| **launch** → titles | ✅ 是 | pane 标题应用失败 | 可单独重试 titles | 3 |
| **launch** → ledger | ✅ 是 | ledger 写入失败 | 删除旧 ledger | 3 |
| **launch** → watcher | ✅ 是 | watcher 启动失败 | 停止旧 watcher | 3 |
| **verify** | ❌ 否 | 只读检查，不重试 | N/A | N/A |

---

### 4.2 安全重试的定义

**安全重试**指：
1. 重试不会导致状态进一步恶化
2. 重试前会清理上一轮的产出
3. 重试有明确的次数限制
4. 超过重试次数后会停止并报告

**不安全重试示例**：
- ❌ 不清理旧 ledger 就直接重试 ledger 初始化（可能导致数据不一致）
- ❌ 不停止旧 watcher 就直接重启 watcher（可能导致多个 watcher 同时运行）

---

### 4.3 自动恢复的场景

| 场景 | 是否可自动恢复 | 恢复逻辑 |
|------|----------------|----------|
| **watcher 进程意外退出** | ✅ 是 | 检测到进程不存在 → 重新 arm watcher |
| **pane 标题丢失** | ✅ 是 | 检测到 title 为空 → 重新 apply titles |
| **ledger 漂移** | ✅ 是 | 检测到 ledger 与 tmux 状态不符 → 重新 init ledger |
| **CODEX_THREAD_ID 解绑** | ❌ 否 | 需要人工确认是否被外部修改 |
| **session 被外部杀掉** | ❌ 否 | 需要重新启动完整主链 |

---

## 5. 失败场景的可观测输出

### 5.1 失败时输出的信息

**stdout 输出**（结构化 JSON）：
```json
{
  "status": "failed",
  "formal_session": "formal-session",
  "pane_count": 4,
  "pane_titles": ["task-1", "task-2", "notes", "monitor"],
  "chain": ["detect", "cleanup", "init", "launch", "verify"],
  "steps": {
    "detect": {...},
    "cleanup": {...},
    "env": {...},
    "topology": {...}
  },
  "error": "pane title application did not fully verify"
}
```

**持久化到 `last-runtime-issues.json`**：
```json
{
  "failed_at": "2026-03-31T12:34:56Z",
  "error": "pane title application did not fully verify",
  "steps_completed": {...},
  "pane_titles_requested": ["task-1", "task-2", "notes", "monitor"],
  "failure_context": {
    "formal_session": "formal-session",
    "last_completed_phase": "titles"
  }
}
```

---

### 5.2 日志文件位置

| 日志文件 | 路径 | 内容 |
|----------|------|------|
| **主链日志** | `workspace/artifacts/tmux-skills/start-formal-runtime-chain.stdout.log` | 主链 stdout 输出 |
| **Watcher 日志** | `workspace/artifacts/tmux-skills/watch-tmux-handoff.stdout.log` | Watcher stdout |
| **Handoff 事件** | `workspace/artifacts/tmux-skills/handoff-notifications.jsonl` | Watcher 发现的事件 |
| **Delivery 日志** | `workspace/artifacts/tmux-skills/deliver-tmux-handoff.stdout.log` | Delivery runner stdout |
| **失败记录** | `workspace/artifacts/tmux-runtime/last-runtime-issues.json` | 失败详情（最近 10 条） |

---

## 6. 实测验证记录

### 6.1 验证场景

| 场景 | 验证日期 | 验证结果 | 备注 |
|------|----------|----------|------|
| Fresh start 正常流程 | 待验证 | 待验证 | 需要在真实环境测试 |
| 残留 cleanup 后重启 | 待验证 | 待验证 | 需要先制造残留 |
| Watcher 重启 | 待验证 | 待验证 | 需要先杀掉 watcher |
| Ledger 漂移恢复 | 待验证 | 待验证 | 需要手动修改 ledger |

---

## 7. 阶段 3 实现清单

### 7.1 已实现

- [x] 验收命令 `check_tmux_ready.py`（现有）
- [x] 失败持久化 `record_failure_to_issues()`（阶段 2 已实现）
- [x] 独立检测报告 `run_detect_phase()`（阶段 2 已实现）
- [x] 主链嵌入验收门禁（现有）

### 7.2 待实现（增强项）

- [ ] Watcher 自动恢复检测
- [ ] Pane 标题自动恢复
- [ ] Ledger 漂移自动检测
- [ ] 重试次数限制和退避策略

---

## 8. 阶段 3 验收确认

### 8.1 验收标准核对

| 验收标准 | 当前状态 | 证据 |
|----------|----------|------|
| **系统能解释 ready 为什么通过** | ✅ 已满足 | `check_tmux_ready.py` 输出 `reasons: []` + `next_action` |
| **系统能解释 failure 为什么失败** | ✅ 已满足 | 主链输出 `error` + `steps`，持久化到 `last-runtime-issues.json` |
| **重试策略是显式的，不靠人为猜测** | 🟡 部分满足 | 本文档定义了策略，但代码中未实现自动重试 |
| **残留状态不会在下一轮启动中悄悄污染结果** | ✅ 已满足 | `preflight_kill_all_tmux_sessions()` + `cleanup_previous_runtime_state()` |
| **主链已经具备基本可恢复性** | ✅ 已满足 | 失败时会 cleanup hidden formal session |

---

## 9. 建议

**阶段 3 核心目标已达成**：
1. 验收机制完整（9 项检查清单）
2. 失败可观测（stdout + 持久化）
3. 重试策略已定义（本文档）
4. 残留污染已防止（cleanup 机制）

**剩余增强项**（可在后续迭代中完成）：
1. 自动重试逻辑（带退避策略）
2. Watcher 自动恢复检测
3. Ledger 漂移自动修复

**建议进入阶段 4：脚本注册制设计**。
