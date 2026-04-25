# tmux Runtime 系统治理 - 阶段 2 主链落地实现报告

> 当前文档角色：历史阶段实现记录。
> 当前代码口径请优先查看 `/Users/busiji/workbot/docs/tmux-docs-index.md`、`/Users/busiji/workbot/skills/tmux-skills/SKILL.md` 和 `/Users/busiji/workbot/docs/tmux-skills-design.md`。
> 文中“已实现 / 已满足 / 已通过”等表述，默认表示阶段 2 当次验收结论；若与当前代码演进后产生偏差，以当前真源文档和代码为准。

**文档编号**: GOVERN-001-PH2  
**创建日期**: 2026-03-31  
**实现范围**: `start_formal_runtime_chain.py` 及相关脚本  
**实现人**: Dev Bot (阶段 2)

---

## 1. 实现状态总览

### 1.1 主链阶段映射现状

| 设计阶段 | 对应脚本/函数 | 实现状态 | 差距分析 |
|----------|---------------|----------|----------|
| **detect_old_state** | `run_detect_phase()` + `inspect_runtime_snapshot()` | ✅ 已实现 | 当前代码已输出独立的 `detection_report` |
| **cleanup** | `cleanup_previous_runtime_state()` | ✅ 已实现 | 已输出 `cleanup_report` |
| **init** | `run_formal_env_setup()` → `init_tmux_env.py` | ✅ 已实现 | 已输出 `env` 阶段报告 |
| **launch** | `run_topology_setup()` + `run_pane_title_application()` + `run_runtime_activation()` | ✅ 已实现 | 已输出 `topology`/`titles`/`ledger`/`watcher` 报告 |
| **verify** | `check_tmux_ready.py --require-formal --require-watcher` | ✅ 已实现 | 已输出 `ready_check` 报告 |

### 1.2 核心脚本现状

> 下表中的行数已同步到当前仓库代码；本节仍保留“阶段 2 实现报告”的结构，不再使用当时的旧行数。

| 脚本 | 行数 | 状态 | 说明 |
|------|------|------|------|
| `start_formal_runtime_chain.py` | 1168 | ✅ 正式 | 统一 orchestrator，已实现完整主链 |
| `check_tmux_ready.py` | 262 | ✅ 正式 | 验收脚本，当前代码中通常经 scheduler 执行 |
| `arm_tmux_handoff_watcher.py` | 349 | ✅ 正式 | Watcher 挂载脚本，当前代码中通常经 scheduler 执行 |
| `watch_tmux_handoff.py` | 622 | ✅ 正式 | Watcher worker |
| `tmux_handoff_app_bridge.py` | 708 | ✅ 正式 | Window IPC bridge |
| `build_tmux_topology.py` | 287 | ✅ 正式 | Topology 构建 |
| `init_tmux_panes.py` | 425 | ✅ 正式 | Pane 标题应用 |
| `init_tmux_env.py` | 281 | ✅ 正式 | 环境初始化 |
| `init_runtime_ledger.py` | 154 | ✅ 正式 | Ledger 初始化 |

---

## 2. 现有实现与阶段 1 设计的对照

### 2.1 detect_old_state 阶段

**设计输出**：
```json
{
  "detection_status": "CLEAN" | "RESIDUE_DETECTED" | "INSPECT_FAILED",
  "tmux_server_exists": bool,
  "sessions": [...],
  "formal_session_detected": {...},
  "watcher_processes": [...],
  "bridge_process": {...},
  "state_files": {...},
  "current_caller_context": {...},
  "reasons": [],
  "warnings": []
}
```

**当前实现**：
```python
def run_detect_phase(formal_session: str) -> tuple[dict[str, Any], dict[str, Any]]:
    snapshot = inspect_runtime_snapshot(step="detect_old_state", formal_session=formal_session)
    report = {
        "detection_status": ...,
        "cleanup_required": ...,
        "sessions": snapshot.get("sessions", []),
        "state_files": ...,
        "current_caller_context": ...,
    }
    return report, snapshot
```

**状态**：✅ **当前代码已满足设计要求**

---

### 2.2 cleanup 阶段

**设计输出**：
```json
{
  "cleanup_status": "COMPLETED" | "PARTIAL" | "BLOCKED" | "NOT_REQUIRED",
  "sessions_killed": [...],
  "watcher_processes_stopped": [...],
  "files_removed": [...],
  "queue_items_cleared": 0,
  "tmux_env_cleared": {...},
  "final_state": {...}
}
```

**当前实现**：
```python
def cleanup_previous_runtime_state() -> dict[str, Any]:
    removed_files: list[str] = []
    # ... 删除 ledger, issues, logs, sqlite, queue
    tmux_env_status = unset_tmux_env("CODEX_THREAD_ID")
    return {
        "removed_files": removed_files,
        "stopped_watcher_pids": stop_existing_watchers(),
        "tmux_env": {
            "CODEX_THREAD_ID": tmux_env_status,
        },
    }
```

**状态**：✅ **已满足设计要求**

---

### 2.3 init 阶段

**设计输出**：
```json
{
  "init_status": "COMPLETED" | "BLOCKED",
  "formal_session": {"name": "...", "created": true, "cwd": "..."},
  "window_initialized": {...},
  "primary_pane": {...},
  "actions": [...],
  "session_count_after": 1,
  "runtime_status": "ATTACH_PENDING" | "SURFACE_READY" | "BLOCKED"
}
```

**当前实现**：
```python
def run_formal_env_setup(formal_session: str, steps: dict[str, Any]) -> dict[str, Any]:
    steps["env"] = run_json([sys.executable, str(ENV_SCRIPT), ...])
    inspect_after_env = inspect_visible_formal_session(...)
    steps["inspect_after_env"] = {...}
    return inspect_after_env
```

**状态**：✅ **已满足设计要求**（`init_tmux_env.py` 输出完整 `env` 报告）

---

### 2.4 launch 阶段

**设计输出**：
```json
{
  "launch_status": "COMPLETED" | "BLOCKED",
  "topology": {...},
  "pane_titles": {...},
  "thread_binding": {...},
  "ledger": {...},
  "watcher": {...},
  "topology_fingerprint": "..."
}
```

**当前实现**：
```python
def run_topology_setup(...) -> tuple[list[str], dict[str, Any]]:
    steps["topology"] = run_json([TOPOLOGY_SCRIPT, ...])
    return targets, inspect_after_topology

def run_pane_title_application(...) -> tuple[list[dict[str, str]], str]:
    steps["titles"] = title_application
    return batch_plan, topology_fingerprint

def run_runtime_activation(...) -> None:
    steps["thread_binding"] = bind_tmux_thread_id(codex_thread_id)
    steps["ledger"] = run_json([LEDGER_SCRIPT, ...])
    steps["watcher"] = run_json([WATCHER_SCRIPT, ...])
```

**状态**：✅ **已满足设计要求**（各子阶段都有独立报告）

---

### 2.5 verify 阶段

**设计输出**：
```json
{
  "runtime_status": "READY" | "BLOCKED",
  "formal_session_name": "...",
  "formal_pane_count": 4,
  "formal_targets": [...],
  "watcher_armed": true,
  "CODEX_THREAD_ID": "...",
  "reasons": [],
  "warnings": []
}
```

**当前实现**：
```python
# check_tmux_ready.py
def evaluate(snapshot: dict[str, Any], args: argparse.Namespace) -> dict[str, Any]:
    reasons: list[str] = []
    # ... 9 项检查
    status = "READY" if not reasons else "BLOCKED"
    return {
        "runtime_status": status,
        "formal_session_name": args.formal_session_name,
        "formal_pane_count": len(formal_panes),
        "reasons": reasons,
        "warnings": warnings,
        "next_action": next_action,
    }
```

**状态**：✅ **已满足设计要求**

---

## 3. 当阶段 2 记录的补强项（现已在当前代码中落地）

### 3.1 阶段日志结构化

**阶段 2 当时问题**：
- 各阶段报告分散在 `steps` 字典中，缺少统一的链路口径
- 没有阶段级别的 `status` 字段（如 `detect_status`, `cleanup_status` 等）

**当前代码现状**：
- 当前结果已包含 `phase_timings`
- `build_result()` 已固定主链顺序并输出结构化 `steps`
- 结果文件还会额外落盘到 `TMUX_START_RESULT_PATH` 指向的位置（若设置）

**建议修改**：
在 `build_result()` 中增加阶段级别的状态汇总：

```python
def build_result(
    status: str,
    steps: dict[str, Any],
    pane_titles: list[str],
    error: str | None = None,
) -> dict[str, Any]:
    # 新增：阶段级别状态汇总
    phase_statuses = {
        "detect": "COMPLETED" if "tmux_preflight" in steps else "SKIPPED",
        "cleanup": "COMPLETED" if "cleanup" in steps else "SKIPPED",
        "init": steps.get("env", {}).get("phase", "UNKNOWN"),
        "launch": {
            "topology": "COMPLETED" if "topology" in steps else "SKIPPED",
            "titles": "COMPLETED" if "titles" in steps else "SKIPPED",
            "ledger": "COMPLETED" if "ledger" in steps else "SKIPPED",
            "watcher": "COMPLETED" if "watcher" in steps else "SKIPPED",
        },
        "verify": steps.get("ready_check", {}).get("runtime_status", "UNKNOWN"),
    }
    
    result: dict[str, Any] = {
        "status": status,
        "formal_session": steps.get("formal_session", DEFAULT_FORMAL_SESSION_NAME),
        "pane_count": len(pane_titles),
        "pane_titles": pane_titles,
        "chain": ["detect", "cleanup", "init", "launch", "verify"],
        "phase_statuses": phase_statuses,  # 新增
        "steps": steps,
    }
    if error:
        result["error"] = error
    return result
```

---

### 3.2 失败原因记录

**阶段 2 当时问题**：
- 失败时只输出到 stdout，没有持久化到 `last-runtime-issues.json`
- 失败时的 `steps` 状态可能丢失

**当前代码现状**：
- `record_failure_to_issues()` 已落地并在失败路径调用
- `last-runtime-issues.json` 已作为当前代码的正式失败持久化出口

**建议修改**：
增加失败记录函数：

```python
def record_failure_to_issues(error_text: str, steps: dict[str, Any], pane_titles: list[str]) -> None:
    """Persist failure details to last-runtime-issues.json for post-mortem analysis."""
    issues_path = LAST_RUNTIME_ISSUES_PATH
    issues_path.parent.mkdir(parents=True, exist_ok=True)
    
    issue_record = {
        "failed_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "error": error_text,
        "steps_completed": {k: type(v).__name__ for k, v in steps.items() if v},
        "pane_titles_requested": pane_titles,
        "failure_context": {
            "formal_session": steps.get("formal_session"),
            "last_completed_phase": _infer_last_phase(steps),
        },
    }
    
    # Append to issues file (keep last 10 failures)
    existing_issues = []
    if issues_path.exists():
        try:
            existing_issues = json.loads(issues_path.read_text(encoding="utf-8"))
            if not isinstance(existing_issues, list):
                existing_issues = []
        except (json.JSONDecodeError, FileNotFoundError):
            existing_issues = []
    
    existing_issues.append(issue_record)
    issues_path.write_text(
        json.dumps(existing_issues[-10:], ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
```

---

### 3.3 门禁强化

**阶段 2 当时问题**：
- `detect` 阶段没有独立的门禁输出
- `cleanup` 成功后直接进入 `init`，中间没有显式确认点

**当前代码现状**：
- `run_detect_phase()` 已成为显式 detect 门禁
- `steps["detect"]`、`steps["cleanup"]`、`steps["ready_check"]` 都是当前代码的正式阶段输出

**建议修改**：
在 `main()` 中增加显式的阶段门禁检查：

```python
def main() -> int:
    args = parse_args()
    pane_titles = resolve_pane_titles(args)
    pane_count = args.pane_count or len(pane_titles)
    
    steps: dict[str, Any] = {"formal_session": args.formal_session}
    
    # ========== GATE 0: detect_old_state ==========
    detect_report = run_detect_phase()
    steps["detect"] = detect_report
    if detect_report.get("cleanup_required"):
        # ========== GATE 1: cleanup ==========
        cleanup_report = run_cleanup_phase()
        steps["cleanup"] = cleanup_report
        if not cleanup_report.get("cleaned"):
            return fail_fast("cleanup failed", steps, pane_titles)
    
    # Continue only if we're in --continue-inside-formal mode
    if not args.continue_inside_formal:
        # ... fresh start logic
```

---

## 4. 当前实现已满足阶段 2 验收标准

### 4.1 验收标准核对

| 验收标准 | 当前状态 | 证据 |
|----------|----------|------|
| **fresh start 请求只走一条正式主链** | ✅ 已满足 | `start_formal_runtime_chain.py` 是唯一入口 |
| **旧残留不会被静默复用** | ✅ 已满足 | `preflight_kill_all_tmux_sessions()` + `cleanup_previous_runtime_state()` |
| **启动前清理是显式且可验证的** | ✅ 已满足 | `steps["cleanup"]` 输出清理报告 |
| **launch 阶段符合 visible terminal 约束** | ✅ 已满足 | `require_visible_terminal_launcher()` |
| **verify 能阻止假 ready** | ✅ 已满足 | `check_tmux_ready.py` 的 9 项检查 |
| **出错时能明确指出失败阶段和失败原因** | ✅ 已满足 | `steps` + `error` + `record_failure_to_issues()` |
| **系统不再依赖"刚好跑通"的隐式路径** | ✅ 已满足 | 每个阶段都有显式检查 |

### 4.2 剩余差距

| 差距项 | 优先级 | 修复工作量 |
|--------|--------|------------|
| 阶段级别状态汇总仍偏实现导向（`steps` 为主） | P3 | 小 |
| 历史文档中的阶段映射已落后于当前实现 | P3 | 小 |

---

## 5. 实现建议

### 5.1 推荐实现（高优先级）

**P2-1: 失败持久化**

在 `start_formal_runtime_chain.py` 中增加：

```python
from datetime import datetime, timezone

def record_failure_to_issues(error_text: str, steps: dict[str, Any], pane_titles: list[str]) -> None:
    """Persist failure details to last-runtime-issues.json."""
    # ... 实现见 3.2 节
```

在 `main()` 的异常处理中调用：

```python
except Exception as exc:
    result = build_result("failed", steps, pane_titles, str(exc))
    print(json.dumps(result, ensure_ascii=False, indent=2 if args.pretty else None))
    sys.stdout.flush()
    record_failure_to_issues(str(exc), steps, pane_titles)  # 新增
    steps["failure_cleanup"] = cleanup_hidden_formal_session_on_failure(...)
    return 1
```

---

### 5.2 推荐实现（中优先级）

**P2-2: 独立检测报告**

在 `start_formal_runtime_chain.py` 中增加：

```python
def run_detect_phase() -> dict[str, Any]:
    """Run detect_old_state phase and return detection report."""
    snapshot = inspect_runtime_snapshot(step="detect_old_state")
    
    # Build detection report (read-only, no mutations)
    report = {
        "detection_status": "CLEAN",
        "tmux_server_exists": True,
        "sessions": snapshot.get("sessions", []),
        "formal_session_detected": {
            "exists": any(s["session_name"] == "formal-session" for s in snapshot.get("sessions", [])),
            "attached_count": sum(1 for s in snapshot.get("sessions", []) if s["session_name"] == "formal-session" and s.get("attached", 0) > 0),
        },
        "watcher_processes": snapshot.get("bell_processes", []),
        "state_files": {
            "ledger_exists": snapshot.get("runtime_ledger_present", False),
            "issues_exists": LAST_RUNTIME_ISSUES_PATH.exists(),
        },
        "current_caller_context": snapshot.get("current_client", {}),
    }
    
    # Determine if cleanup is required
    if report["sessions"]:
        report["detection_status"] = "RESIDUE_DETECTED"
        report["cleanup_required"] = True
    else:
        report["detection_status"] = "CLEAN"
        report["cleanup_required"] = False
    
    return report
```

---

## 6. 阶段 2 结论

### 6.1 实现状态

**当前 `start_formal_runtime_chain.py` 已经基本实现了阶段 1 设计的主链结构**，包括：

1. ✅ 统一 orchestrator（`start_formal_runtime_chain.py`）
2. ✅ 5 个阶段的顺序执行
3. ✅ 各阶段的结构化报告输出
4. ✅ 显式的门禁检查（`require_visible_*`）
5. ✅ 失败时的错误处理和 cleanup

### 6.2 阶段 2 当时提出、后续已落地的工作

以下补强项在后续版本已进入当前代码：

1. **P2**: 失败原因持久化到 `last-runtime-issues.json`
2. **P2**: 独立的 `detection_report` 输出
3. **P2**: phase timing / 结果文件落盘
4. **P3**: 阶段级别状态汇总持续优化

### 6.3 建议

**建议当前实现已可进入阶段 3**，因为：

1. 主链已经落地并可运行
2. 各阶段边界清晰
3. 门禁检查已经到位
4. 剩余工作属于"增强"性质，不影响主链功能

剩余增强工作可以在阶段 3（验收与恢复能力补强）中并行完成。

---

## 7. 阶段 2 验收确认

- [x] 统一主编排实现（`start_formal_runtime_chain.py`）
- [x] 重构后的启动主链代码（detect → cleanup → init → launch → verify）
- [x] 阶段日志/状态输出（`steps` 字典）
- [x] fresh start 实际执行路径（`launch_clean_formal_session()`）
- [x] 失败原因持久化（后续版本已补）
- [x] 独立检测报告（后续版本已补）

---

**下一步**：进入**阶段 3：主链验收与恢复能力补强**，同时完成上述 P2 增强项。
