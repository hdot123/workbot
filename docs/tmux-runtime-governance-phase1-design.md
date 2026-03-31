# tmux Runtime 系统治理 - 阶段 1 主链方案设计

**文档编号**: GOVERN-001-PH1  
**创建日期**: 2026-03-31  
**设计范围**: tmux runtime 主链收敛  
**设计人**: Dev Bot (阶段 1)

---

## 1. 主链设计总览

### 1.1 固定主链

```
┌──────────────────────────────────────────────────────────────────────────┐
│                        FORMAL RUNTIME MAIN CHAIN                         │
│                                                                          │
│  detect_old_state → cleanup → init → launch → verify                     │
│                                                                          │
│  阶段 0        阶段 1      阶段 2    阶段 3    阶段 4                      │
│  detect        cleanup   init      launch  verify                        │
└──────────────────────────────────────────────────────────────────────────┘
```

### 1.2 主链阶段映射

| 阶段编号 | 阶段名称 | 对应脚本/函数 | 输出状态 |
|----------|----------|---------------|----------|
| **阶段 0** | `detect_old_state` | `inspect_runtime()` + 预检查逻辑 | `detection_report` |
| **阶段 1** | `cleanup` | `cleanup_previous_runtime_state()` + `preflight_kill_all_tmux_sessions()` | `cleanup_report` |
| **阶段 2** | `init` | `init_tmux_env.py` | `init_report` |
| **阶段 3** | `launch` | `build_tmux_topology.py` → `init_tmux_panes.py` → `bind_tmux_thread_id()` | `launch_report` |
| **阶段 4** | `verify` | `check_tmux_ready.py` + `arm_tmux_handoff_watcher.py` | `verify_report` |

---

## 2. 阶段边界详细说明

### 2.1 阶段 0: detect_old_state

**职责**：审计当前 tmux 现场，识别所有可能污染新启动的旧状态残留。

**输入**：
- 无（仅读取当前系统状态）

**输出**：
```json
{
  "detection_status": "CLEAN" | "RESIDUE_DETECTED" | "INSPECT_FAILED",
  "tmux_server_exists": bool,
  "sessions": [
    {
      "session_name": "formal-session",
      "attached": 1,
      "is_formal": true,
      "is_bootstrap": false,
      "should_be_killed": true
    }
  ],
  "formal_session_detected": {
    "exists": true,
    "attached_count": 1,
    "visible_client_count": 1,
    "is_current_session": false
  },
  "watcher_processes": [
    {"pid": 12345, "command": "watch_tmux_handoff.py --target formal-session:1.1"}
  ],
  "bridge_process": {
    "pid_file_exists": true,
    "pid": 12346,
    "is_running": true
  },
  "state_files": {
    "ledger_exists": true,
    "issues_exists": false,
    "handoff_log_exists": true,
    "queue_items_count": 0
  },
  "current_caller_context": {
    "inside_tmux": true,
    "session_name": "formal-session",
    "visible_terminal_client": true,
    "codex_hosted": false
  },
  "reasons": [],
  "warnings": []
}
```

**成功条件**：
- 成功完成状态审计
- 输出完整的 `detection_report`

**失败条件**：
- `tmux` 命令不可用
- 无法读取必要状态文件

**是否允许重试**：是（无副作用的只读检查）

**是否允许跳过**：否（必须知道当前现场状态）

**会生成或消费的状态文件**：
- 读取：`current-runtime.json`, `tmux list-sessions`, `tmux list-clients`, `ps ax`
- 不生成任何文件

---

### 2.2 阶段 1: cleanup

**职责**：清理所有检测到的旧状态残留，为新启动准备干净环境。

**输入**：
- `detection_report`（来自阶段 0）

**输出**：
```json
{
  "cleanup_status": "COMPLETED" | "PARTIAL" | "BLOCKED" | "NOT_REQUIRED",
  "sessions_killed": ["formal-session", "tbot"],
  "watcher_processes_stopped": [12345],
  "bridge_process_stopped": 12346,
  "files_removed": [
    "/workspace/artifacts/tmux-runtime/current-runtime.json",
    "/workspace/artifacts/tmux-skills/handoff-notifications.jsonl"
  ],
  "queue_items_cleared": 0,
  "tmux_env_cleared": {
    "CODEX_THREAD_ID": "cleared" | "not_cleared" | "no_tmux_server"
  },
  "final_state": {
    "tmux_sessions_remaining": 0,
    "tmux_server_stopped": false
  },
  "reasons": [],
  "warnings": []
}
```

**成功条件**：
- 所有旧 session 被杀掉（包括 `formal-session` 和 `tbot`）
- 所有旧 watcher 进程被停止
- 所有状态文件被删除
- delivery queue 被清空
- `CODEX_THREAD_ID` tmux 环境变量被 unset

**失败条件**：
- 当前调用者本身在 tmux 内（无法杀掉自己的 session）
- 某个 session 无法被杀掉（权限问题）

**是否允许重试**：是（某些进程可能需要 SIGKILL 才能停止）

**是否允许跳过**：否（旧状态残留会污染新启动）

**会生成或消费的状态文件**：
- 删除：`current-runtime.json`, `last-runtime-issues.json`, `handoff-*.jsonl`, `*.sqlite3`, `*.log`
- 清空：`delivery-queue/*.json`
- 修改：tmux 环境变量 `CODEX_THREAD_ID`

---

### 2.3 阶段 2: init

**职责**：创建并初始化 formal session 环境。

**输入**：
- `cleanup_report`（来自阶段 1）
- 命令行参数：`--formal-session`, `--formal-cwd`

**输出**：
```json
{
  "init_status": "COMPLETED" | "BLOCKED",
  "formal_session": {
    "name": "formal-session",
    "created": true,
    "cwd": "/Users/busiji/workbot",
    "detached": true
  },
  "window_initialized": {
    "window_index": "1",
    "window_title": "formal-session"
  },
  "primary_pane": {
    "target": "formal-session:1.1",
    "pane_title": "formal-session"
  },
  "actions": [
    "window_title=formal-session",
    "pane_title=formal-session"
  ],
  "session_count_after": 1,
  "bootstrap_sessions": [],
  "extra_formal_sessions": [],
  "runtime_status": "ATTACH_PENDING" | "SURFACE_READY" | "BLOCKED"
}
```

**成功条件**：
- 创建了一个且仅一个 detached formal session
- 窗口标题已设置
- primary pane 标题已设置
- 没有其他 session 残留

**失败条件**：
- 调用者不在可见终端（`require_visible_terminal_launcher()` 失败）
- tmux cleanup 未完全（还有旧 session 残留）
- tmux 创建失败

**是否允许重试**：是（前提是 cleanup 阶段成功完成）

**是否允许跳过**：否（必须创建 formal session）

**会生成或消费的状态文件**：
- 消费：cleanup 阶段的清理结果
- 生成：新的 tmux session（detached 状态）

---

### 2.4 阶段 3: launch

**职责**：构建 pane 拓扑、应用标题、绑定 thread ID、初始化 ledger、启动 watcher。

**输入**：
- `init_report`（来自阶段 2）
- 命令行参数：`--codex-thread-id`, `--pane-title[]`, `--task-id`

**输出**：
```json
{
  "launch_status": "COMPLETED" | "BLOCKED",
  "topology": {
    "target_pane_count": 4,
    "pane_count_before": 1,
    "pane_count_after": 4,
    "actions": [
      "split-window:-v:formal-session:1.1",
      "select-layout:tiled:2x2",
      ...
    ],
    "pane_targets": [
      "formal-session:1.1",
      "formal-session:1.2",
      "formal-session:1.3",
      "formal-session:1.4"
    ],
    "ok": true
  },
  "pane_titles": {
    "verified": true,
    "formal_pane_count": 4,
    "entries": [
      {"target": "formal-session:1.1", "pane_title": "task-1", "title_applied": true},
      {"target": "formal-session:1.2", "pane_title": "task-2", "title_applied": true},
      {"target": "formal-session:1.3", "pane_title": "notes", "title_applied": true},
      {"target": "formal-session:1.4", "pane_title": "monitor", "title_applied": true}
    ],
    "slot_bindings": {
      "pane_1": {"pane_title": "task-1", "target": "formal-session:1.1"},
      "pane_2": {"pane_title": "task-2", "target": "formal-session:1.2"},
      "pane_3": {"pane_title": "notes", "target": "formal-session:1.3"},
      "pane_4": {"pane_title": "monitor", "target": "formal-session:1.4"}
    }
  },
  "thread_binding": {
    "CODEX_THREAD_ID": "thread_abc123",
    "bound": true
  },
  "ledger": {
    "task_id": "task-001",
    "pane_count": 4,
    "runtime_status": "READY",
    "codex_thread_bound": true,
    "created_at": "2026-03-31T10:00:00Z"
  },
  "watcher": {
    "status": "armed",
    "targets": [
      "formal-session:1.1",
      "formal-session:1.2",
      "formal-session:1.3",
      "formal-session:1.4"
    ],
    "pid": 54321,
    "transport": "codex"
  },
  "topology_fingerprint": "abc123..."
}
```

**成功条件**：
- pane 数量达到要求
- 所有 pane 标题已应用并验证
- `CODEX_THREAD_ID` 已绑定到 tmux env
- ledger 已初始化并写入
- watcher 已启动并记录 PID

**失败条件**：
- topology 构建失败（pane 分裂/收缩失败）
- pane 标题应用失败
- `CODEX_THREAD_ID` 绑定失败
- ledger 写入失败
- watcher 启动失败

**是否允许重试**：部分允许（topology/pane titles 可重试；ledger/watcher 需要先清理再重试）

**是否允许跳过**：否（这是核心启动阶段）

**会生成或消费的状态文件**：
- 生成：`current-runtime.json`（ledger）
- 修改：tmux 环境变量 `CODEX_THREAD_ID`
- 启动后台进程：watcher

---

### 2.5 阶段 4: verify

**职责**：验收整个启动链路，确认 formal runtime 真正 ready。

**输入**：
- `launch_report`（来自阶段 3）

**输出**：
```json
{
  "runtime_status": "READY" | "BLOCKED",
  "formal_session_name": "formal-session",
  "session_count": 1,
  "pane_count": 4,
  "formal_pane_count": 4,
  "expected_pane_count": 4,
  "formal_targets": [
    "formal-session:1.1",
    "formal-session:1.2",
    "formal-session:1.3",
    "formal-session:1.4"
  ],
  "watcher_targets": [...],
  "watcher_armed": true,
  "watcher_commands": ["python3 watch_tmux_handoff.py --target ..."],
  "CODEX_THREAD_ID": "thread_abc123",
  "formal_client_count": 1,
  "current_visible_formal_client": true,
  "reasons": [],
  "warnings": [],
  "next_action": ["tmux-skills runtime matches the current contract"]
}
```

**成功条件**（必须全部满足）：
1. 有且仅有一个 `formal-session`
2. `formal-session` 已 attached
3. 有且仅有一个 attached tmux client
4. 当前调用者在 visible formal client 内
5. pane count 匹配预期
6. 所有 pane 都有非空标题
7. pane targets 匹配 ledger slot_bindings
8. `CODEX_THREAD_ID` 已绑定
9. watcher 已 armed 且进程在运行

**失败条件**：
- 任一成功条件不满足

**是否允许重试**：否（verify 是只读检查；失败时应返回具体原因，由上层决定重试哪个阶段）

**是否允许跳过**：否（必须有验收门禁）

**会生成或消费的状态文件**：
- 读取：`current-runtime.json`, tmux 状态
- 不生成任何文件

---

## 3. Fresh Start 规则

### 3.1 Fresh Start 的正式语义

**Fresh Start** 定义为：

> 从可见终端发起的、完整的、不依赖任何历史状态的 tmux runtime 启动流程。

**必要条件**：
1. 调用者必须在**可见终端**（非 hidden PTY，非 tmux 内部）
2. 启动前必须执行**完整 cleanup**
3. 必须创建**新的** `formal-session`
4. 必须重新绑定 `CODEX_THREAD_ID`
5. 必须重新初始化 ledger
6. 必须重新挂载 watcher

### 3.2 Fresh Start 与 Continuation 的区别

| 模式 | Fresh Start | Continuation |
|------|-------------|--------------|
| **触发条件** | 无现有 runtime 或用户显式要求 fresh | 现有 runtime 仍然有效，只需补充 |
| **Cleanup** | 完整清理 | 不清理 |
| **Session** | 新建 | 复用 |
| **Ledger** | 新建 | 更新 |
| **Watcher** | 重新启动 | 可选 re-arm |
| **使用场景** | 每日首次启动、污染恢复 | pane 数量调整、标题变更 |

**当前实现**：
- `start_formal_runtime_chain.py` 默认执行 Fresh Start
- `--continue-inside-formal` 模式用于 Continuation（内部使用）

---

## 4. 旧状态检测语义

### 4.1 检测范围

| 检测对象 | 检测方式 | 判定标准 |
|----------|----------|----------|
| **旧 session** | `tmux list-sessions` | 任何存在的 session 都是旧残留 |
| **旧 formal-session** | `tmux list-sessions` + `list-clients` | 检查 attached count 和 visible client count |
| **旧 watcher** | `ps ax -o pid=,command=` | 进程名含 `watch_tmux_handoff.py` |
| **旧 bridge** | PID 文件 + `ps` 检查 | PID 文件存在且进程在运行 |
| **旧 ledger** | 文件存在性检查 | `current-runtime.json` 存在 |
| **旧 CODEX_THREAD_ID** | `tmux show-environment` | 环境变量已设置 |

### 4.2 检测报告

```json
{
  "detection_status": "RESIDUE_DETECTED",
  "residue_items": [
    {
      "type": "session",
      "name": "formal-session",
      "severity": "HIGH",
      "action": "kill-session"
    },
    {
      "type": "watcher",
      "pid": 12345,
      "severity": "MEDIUM",
      "action": "stop_watcher"
    }
  ],
  "cleanup_required": true
}
```

---

## 5. Cleanup 的范围与标准

### 5.1 Cleanup 范围

| 清理对象 | 清理方式 | 清理标准 |
|----------|----------|----------|
| **所有 tmux sessions** | `tmux kill-session -t <name>` | 无任何 session 残留 |
| **所有 watcher 进程** | `kill -TERM` → `kill -KILL` | 无 watcher 进程残留 |
| **Bridge 进程** | `kill -TERM` + 删除 PID 文件 | 无 bridge 进程残留 |
| **Ledger 文件** | `unlink()` | 文件不存在 |
| **Issues 文件** | `unlink()` | 文件不存在 |
| **Handoff 日志** | `unlink()` | 文件不存在 |
| **SQLite DB** | `unlink()` | 文件不存在 |
| **Delivery Queue** | 删除目录下所有 `.json` 文件 | 目录为空 |
| **CODEX_THREAD_ID** | `tmux set-environment -gu` | 环境变量不存在 |

### 5.2 Cleanup 成功标准

```json
{
  "cleanup_status": "COMPLETED",
  "verification": {
    "tmux_sessions_remaining": 0,
    "watcher_processes_remaining": 0,
    "bridge_process_running": false,
    "state_files_remaining": 0,
    "queue_items_remaining": 0,
    "codex_thread_id_bound": false
  }
}
```

---

## 6. Init 的边界

### 6.1 Init 负责什么

- 创建 detached formal session
- 设置窗口标题
- 设置 primary pane 标题
- （可选）发送 startup command

### 6.2 Init 不负责什么

- **不负责** attach session（这是后续阶段的事）
- **不负责** pane 分裂/布局（这是 launch 阶段的事）
- **不负责** ledger 初始化（这是 launch 阶段的事）
- **不负责** watcher 挂载（这是 launch 阶段的事）

### 6.3 Init 的边界约束

```
┌─────────────────────────────────────────────────────────┐
│                    INIT BOUNDARY                        │
│                                                         │
│  输入：clean tmux (no sessions) + visible terminal      │
│  输出：detached formal session (ready for attach)       │
│                                                         │
│  不依赖：任何后续阶段的状态                             │
│  不产生：ledger / watcher / pane topology               │
└─────────────────────────────────────────────────────────┘
```

---

## 7. Launch 的唯一正式入口

### 7.1 Launch 的正式入口

**唯一正式入口**：`start_formal_runtime_chain.py`（通过 `--continue-inside-formal` 模式）

**内部调用顺序**：
1. `build_tmux_topology.py` → 构建 pane 拓扑
2. `init_tmux_panes.py` → 应用 pane 标题
3. `bind_tmux_thread_id()` → 绑定 `CODEX_THREAD_ID`
4. `init_runtime_ledger.py` → 初始化 ledger
5. `arm_tmux_handoff_watcher.py` → 启动 watcher

### 7.2 禁止的直调方式

以下调用方式应被禁止（或至少被标记为不支持）：

- ❌ `python3 build_tmux_topology.py --session formal-session`（跳过 init）
- ❌ `python3 init_tmux_panes.py --target formal-session:1.1 --pane-title task-1`（跳过 topology）
- ❌ `python3 arm_tmux_handoff_watcher.py`（跳过 ledger 初始化）

**原因**：直调可能导致状态不一致（如 ledger 与 topology 不匹配）

---

## 8. Verify 的 Ready 判定标准

### 8.1 Ready 判定清单

| 检查项 | 期望状态 | 失败处理 |
|--------|----------|----------|
| **formal-session 存在** | 有且仅有一个 | BLOCKED |
| **formal-session attached** | `attached > 0` | BLOCKED |
| **visible client count** | `= 1` | BLOCKED |
| **current caller in formal** | `session_name == formal-session` | BLOCKED |
| **pane count** | `== expected_pane_count` | BLOCKED |
| **pane titles** | 全部非空 | BLOCKED |
| **slot bindings** | 与 pane targets 匹配 | BLOCKED |
| **CODEX_THREAD_ID** | 已绑定 | BLOCKED |
| **watcher armed** | `armed == true` | BLOCKED |
| **watcher process** | 进程在运行 | BLOCKED |

### 8.2 "tmux session 存在"与"runtime ready"的区别

| 状态 | tmux session 存在 | Runtime Ready |
|------|-------------------|---------------|
| **定义** | `tmux list-sessions` 能查到 `formal-session` | 所有 verify 检查项通过 |
| **检查方式** | 只读检查 | 只读检查 |
| **依赖状态** | 仅需 session 存在 | 需要 session + attached + pane + titles + ledger + watcher |
| **可否调用** | 不可（可能未初始化完成） | 可（已准备好接收工作） |

**关键区别**：
- "tmux session 存在"只是 init 阶段的产出
- "Runtime Ready"是完整主链的产出

---

## 9. Hidden PTY / Visible Terminal 职责边界

### 9.1 Hidden PTY 能做什么

| 操作 | 是否允许 | 说明 |
|------|----------|------|
| 调用 `start_formal_runtime_chain.py` | ❌ 不允许 | 必须在可见终端启动 |
| 读取状态 | ✅ 允许 | 只读操作 |
| 发送命令到已有 pane | ✅ 允许 | 运行态操作 |

### 9.2 Hidden PTY 不能做什么

| 操作 | 是否允许 | 说明 |
|------|----------|------|
| 发起 fresh start | ❌ 不允许 | 必须在可见终端 |
| 直接 attach formal session | ❌ 不允许 | hidden PTY 无法成为 visible client |
| 作为 watcher 上报目标 | ❌ 不允许 | watcher 必须上报到 visible window |

### 9.3 Visible Terminal 的职责

| 操作 | 是否必须 | 说明 |
|------|----------|------|
| Fresh start 启动 | ✅ 必须 | 唯一合法的启动上下文 |
| Attach formal session | ✅ 必须 | 使 `session_attached > 0` |
| 成为 watcher 上报目标 | ✅ 必须 | `CODEX_THREAD_ID` 必须指向 visible window |

---

## 10. Formal Runtime Ready 的机器可检查条件

### 10.1 机器可检查条件清单

```python
def is_runtime_ready(snapshot: dict) -> tuple[bool, list[str]]:
    reasons = []
    
    # Check 1: single formal session
    formal_sessions = [s for s in snapshot['sessions'] if s['session_name'] == 'formal-session']
    if len(formal_sessions) != 1:
        reasons.append(f"expected 1 formal-session, got {len(formal_sessions)}")
    
    # Check 2: attached
    if int(formal_sessions[0].get('attached', 0)) <= 0:
        reasons.append("formal-session not attached")
    
    # Check 3: single visible client
    formal_clients = [c for c in snapshot['clients'] if c['session_name'] == 'formal-session']
    if len(formal_clients) != 1:
        reasons.append(f"expected 1 formal client, got {len(formal_clients)}")
    
    # Check 4: visible terminal client
    if not formal_clients[0].get('visible_terminal_client'):
        reasons.append("formal client not in visible terminal")
    
    # Check 5: pane count
    formal_panes = [p for p in snapshot['panes'] if p['session_name'] == 'formal-session']
    if len(formal_panes) != snapshot['runtime_ledger'].get('pane_count'):
        reasons.append("pane count mismatch")
    
    # Check 6: pane titles
    empty_titles = [p['target'] for p in formal_panes if not p['pane_title_normalized'].strip()]
    if empty_titles:
        reasons.append(f"empty pane titles: {empty_titles}")
    
    # Check 7: CODEX_THREAD_ID
    if not snapshot.get('CODEX_THREAD_ID'):
        reasons.append("CODEX_THREAD_ID not bound")
    
    # Check 8: watcher armed
    if not snapshot['runtime_ledger'].get('watcher', {}).get('armed'):
        reasons.append("watcher not armed")
    
    # Check 9: watcher process running
    if not snapshot.get('bell_processes'):
        reasons.append("watcher process not running")
    
    return len(reasons) == 0, reasons
```

---

## 11. Watcher 挂载与 Runtime Ready 的关系

### 11.1 关系说明

**Watcher 挂载是 Runtime Ready 的必要条件，但不是充分条件。**

```
┌─────────────────────────────────────────────────────────┐
│              WATCHER vs RUNTIME READY                   │
│                                                         │
│  Watcher Armed → Yes                                    │
│                    │                                    │
│                    ▼                                    │
│  Runtime Ready → 还需要检查：                            │
│                    - formal session attached            │
│                    - visible client count = 1           │
│                    - pane count matches                 │
│                    - pane titles applied                │
│                    - CODEX_THREAD_ID bound              │
│                    - watcher process running            │
│                                                         │
│  结论：Watcher 挂载是必要条件之一，但不能单独决定 Ready    │
└─────────────────────────────────────────────────────────┘
```

### 11.2 挂载时机

**Watcher 必须在以下阶段之后挂载**：
1. pane topology 构建完成
2. pane titles 应用完成
3. ledger 初始化完成
4. `CODEX_THREAD_ID` 绑定完成

**原因**：watcher 需要知道要监控哪些 targets，这些 targets 来自 ledger 的 slot_bindings。

---

## 12. 失败恢复/重试策略

### 12.1 各阶段的重试策略

| 阶段 | 是否允许重试 | 重试条件 | 重试前需清理 |
|------|--------------|----------|--------------|
| **detect** | 是 | 临时错误（如 tmux 命令超时） | 无 |
| **cleanup** | 是 | 进程未完全停止 | 无（cleanup 幂等） |
| **init** | 是 | cleanup 成功后 | 需要重新 cleanup |
| **launch** | 部分 | topology/pane titles 可重试 | ledger/watcher 需要先清理 |
| **verify** | 否 | 只读检查，不重试 | N/A |

### 12.2 失败恢复流程

```
┌─────────────────────────────────────────────────────────┐
│                  FAILURE RECOVERY                       │
│                                                         │
│  如果阶段 N 失败：                                        │
│  1. 记录失败原因到 last-runtime-issues.json             │
│  2. 判断是否可重试：                                      │
│     - 可重试：清理阶段 N 的产出 → 重试阶段 N              │
│     - 不可重试：返回失败报告，由上层决定是否重试         │
│  3. 重试次数限制：每个阶段最多重试 3 次                     │
│  4. 超过重试限制：标记为 BLOCKED，需要人工介入          │
│                                                         │
│  特殊规则：                                              │
│  - cleanup 失败：不得继续后续阶段                        │
│  - verify 失败：不得声称 READY                           │
└─────────────────────────────────────────────────────────┘
```

### 12.3 常见失败场景表

| 场景 | 失败阶段 | 原因 | 恢复方式 |
|------|----------|------|----------|
| **调用者在 tmux 内** | cleanup | 无法杀掉自己的 session | 退出 tmux 后重试 |
| **tmux 命令不可用** | detect | tmux 未安装或 PATH 问题 | 修复环境后重试 |
| **旧 watcher 未停止** | cleanup | SIGTERM 无效 | 发送 SIGKILL |
| **pane 分裂失败** | launch | tmux 布局冲突 | 重新 cleanup 后重试 |
| **pane 标题不匹配** | launch | tmux 响应超时 | 重试 pane title 应用 |
| **ledger 写入失败** | launch | 文件系统权限问题 | 修复权限后重试 |
| **watcher 启动失败** | launch | 端口占用或脚本报错 | 检查日志后重试 |
| **verify 不通过** | verify | 某个检查项失败 | 返回具体原因，由上层决定 |

---

## 13. 对现有脚本的映射方案

### 13.1 保留

| 脚本 | 映射到阶段 | 说明 |
|------|------------|------|
| `start_formal_runtime_chain.py` | 主编排（覆盖所有阶段） | 保留为唯一对外入口 |
| `check_tmux_ready.py` | verify（阶段 4） | 保留为验收命令 |
| `arm_tmux_handoff_watcher.py` | launch → watcher 挂载 | 保留，但只能由 orchestrator 调用 |
| `watch_tmux_handoff.py` | 运行态 | 保留为 watcher worker |
| `tmux_handoff_app_bridge.py` | 运行态 | 保留为 bridge 常驻 |

### 13.2 合并

| 被合并项 | 合并到 | 说明 |
|----------|--------|------|
| `cleanup_previous_runtime_state()` | cleanup 阶段 | 已是 `start_formal_runtime_chain.py` 内部函数 |
| `preflight_kill_all_tmux_sessions()` | cleanup 阶段 | 已是 `start_formal_runtime_chain.py` 内部函数 |

### 13.3 下沉（降为内部工具函数）

| 脚本 | 下沉为 | 说明 |
|------|--------|------|
| `inspect_tmux_runtime.py` | detect 工具函数 | 不再独立调用 |
| `verify_tmux_runtime.py` | verify 工具函数 | 不再独立调用 |
| `verify_pane_identity.py` | verify 工具函数 | 不再独立调用 |

### 13.4 废弃

| 脚本 | 废弃理由 | 替代方案 |
|------|----------|----------|
| `agents/tmux-runtime-bot.md` | 已弃用文档 | 无 |
| `build_tmux_db_write_instruction.py` | 旧 delivery 链路 | `tmux_handoff_app_bridge.py` |
| `load_local_identity.py` | 旧身份加载 | 无 |
| `tbot` bootstrap | 可能导致双 session 污染 | 直接 fresh start |

---

## 14. 阶段 1 验收确认

- [x] 主链只有一条，没有多个并列正式路径
- [x] fresh start 的行为规则是明确且一致的
- [x] ready 判定不是表面状态，而是完整状态校验
- [x] launch 阶段的正式启动边界清晰
- [x] 每个阶段都能解释"为什么通过""为什么失败"
- [x] 后续实现可以严格按该方案落地，而不是边做边猜

---

## 15. 下一步建议

建议进入**阶段 2：主链落地实现**，按本设计方案实现以下内容：

1. **统一 orchestrator**：强化 `start_formal_runtime_chain.py` 作为唯一入口
2. **阶段函数拆分**：将各阶段逻辑拆分为独立函数，便于测试
3. **阶段日志输出**：每个阶段输出结构化报告
4. **失败原因记录**：失败时写入 `last-runtime-issues.json`
5. **门禁强化**：verify 阶段不通过时不得声称 READY
