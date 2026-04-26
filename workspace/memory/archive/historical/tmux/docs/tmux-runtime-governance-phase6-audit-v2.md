# tmux Runtime 系统治理 - 第二次自审报告

> 当前文档角色：历史审计记录。
> 它反映的是当次审计结论，不单独作为当前实现的唯一真源。
> 后续实现和文档整理若继续演进，应以 `/Users/busiji/workbot/docs/tmux-docs-index.md` 和当前代码为准。
> 文中“已完成 / 已实现 / 已修复”等表述，均表示第二次自审当时的结论。

**审计日期**: 2026-03-31  
**审计范围**: 修复后对照原任务书逐项核验  
**审计原则**: 只认代码、文件、调用路径、真实执行机制

---

## 1. 审计总结

| 类别 | 数量 | 变更 |
|------|------|------|
| 已完成项 | 18 项 | +6 项 |
| 部分完成项 | 0 项 | -6 项 |
| 未完成项 | 0 项 | -4 项 |
| 与原任务书冲突的点 | 0 项 | -5 项（已全部修复） |

**整体结论**: `已完成`

---

## 2. 已完成项（新增/修复）

| # | 交付物 | 证据 | 判定 |
|---|--------|------|------|
| 2.1 | Phase 5 独立验收文档 | `docs/tmux-runtime-governance-phase5-implementation.md` 已创建 | ✅ 已完成 |
| 2.2 | 主链接入调度器 | `start_formal_runtime_chain.py` 使用 `tmux_scheduler.py` 调用各阶段脚本（7 处 `run_json_script` 调用） | ✅ 已完成 |
| 2.3 | internal_only 拦截 | `run_script.py` 和 `tmux_scheduler.py` 均实现 `is_internal_call()` 和检查逻辑 | ✅ 已完成 |
| 2.4 | hidden PTY 检测增强 | `is_hidden_pty()` 实现多指标检测（hidden_context 文件、tmux session 名称、TTY 验证） | ✅ 已完成 |
| 2.5 | clean state 检查增强 | `is_clean_state()` 检查 sessions、ledger、watcher 进程、bridge 进程、CODEX_THREAD_ID | ✅ 已完成 |
| 2.6 | Phase 6 文档修正 | 删除夸大表述，修正为实际实现状态，添加"曾冲突但已修复的问题"章节 | ✅ 已完成 |

---

## 3. 与原任务书对照核验

### 3.1 分阶段交付核验

| 阶段 | 独立交付物 | 验收材料 | 判定 |
|------|------------|----------|------|
| Phase 0 | ✅ `phase0-analysis.md` | ✅ 当前已同步为 23 个 `scripts/` 条目、主链直达入口 + 公开调度入口层级、5 类问题 | ✅ 通过 |
| Phase 1 | ✅ `phase1-design.md` | ✅ 5 阶段定义、输入输出、成功/失败条件 | ✅ 通过 |
| Phase 2 | ✅ `phase2-implementation.md` | ✅ 阶段映射表、差距分析 | ✅ 通过 |
| Phase 3 | ✅ `phase3-recovery.md` | ✅ 9 项检查清单、失败场景表、重试策略 | ✅ 通过 |
| Phase 4 | ✅ `phase4-registry-design.md` | ✅ 注册表结构、调度器设计、校验规则 | ✅ 通过 |
| Phase 5 | ✅ `phase5-implementation.md` | ✅ 注册表实现、调度器测试、迁移状态 | ✅ 通过 |
| Phase 6 | ✅ `phase6-final.md` | ✅ 完整验收、架构总结、冲突修复记录 | ✅ 通过 |

### 3.2 主链收敛核验

| 要求 | 实际实现 | 判定 |
|------|----------|------|
| detect → cleanup → init → launch → verify | ✅ `start_formal_runtime_chain.py` 顺序执行 | ✅ 通过 |
| detect 独立检测语义 | ✅ `run_detect_phase()` 返回 detection_report | ✅ 通过 |
| detect 独立检测产物 | ✅ `steps["detect"]` 存储检测报告 | ✅ 通过 |
| verify 完整 ready 验收 | ✅ `check_tmux_ready.py` 9 项检查 | ✅ 通过 |

### 3.3 注册制接管核验

| 要求 | 实际实现 | 判定 |
|------|----------|------|
| 正式脚本通过受控调用 | ✅ `start_formal_runtime_chain.py` 通过 `tmux_scheduler.py` 调用 | ✅ 通过 |
| 无路径直调 | ✅ 原 `subprocess.run([sys.executable, str(TOPOLOGY_SCRIPT), ...])` 已替换为 `run_json_script("build_tmux_topology.py", ...)` | ✅ 通过 |
| 注册制强制执行 | ✅ 主链导入并使用调度器模块 | ✅ 通过 |

### 3.4 调度器校验核验

| 校验项 | 实现状态 | 测试证据 |
|--------|----------|----------|
| 注册检查 | ✅ 已实现 | `run_script.py --script unknown.py` → 拒绝 |
| 状态检查 | ✅ 已实现 | `run_script.py --script deliver_*.py` → 警告 |
| orchestrator_only | ✅ 已实现 | 通过 `TMUX_ORCHESTRATOR_CONTEXT` 控制 |
| internal_only | ✅ 已实现 | `run_script.py --script runtime_ledger.py` → 拒绝 |
| hidden PTY | ✅ 已实现（增强） | 多指标检测 |
| visible terminal | ✅ 已实现 | TTY 验证 |
| clean state | ✅ 已实现（增强） | 检查 sessions/ledger/watcher/bridge |
| preconditions | ✅ 已实现 | 6 种前置条件检查 |

---

## 4. 关键修复验证

### 4.1 主链接入调度器

**修复前**:
```python
steps["topology"] = run_json(
    [sys.executable, str(TOPOLOGY_SCRIPT), "--formal-session", ...],
    step="topology",
)
```

**修复后**:
```python
from tmux_scheduler import run_json_script, set_orchestrator_context

def run_topology_setup(...):
    set_orchestrator_context()  # 设置 orchestrator 上下文
    steps["topology"] = run_json_script(
        "build_tmux_topology.py",  # 通过注册名调用
        ["--formal-session", formal_session, "--target-pane-count", str(pane_count)],
        step="topology",
    )
```

**验证**: `grep -c "run_json_script" start_formal_runtime_chain.py` → 7 处

---

### 4.2 internal_only 拦截

**修复前**: `validate_script()` 无 internal_only 检查

**修复后**:
```python
def is_internal_call() -> bool:
    internal_marker = os.environ.get("TMUX_INTERNAL_CALL", "")
    return internal_marker == "true"

# 在 validate_script() 中:
if visibility == "internal_only":
    if not is_internal_call():
        errors.append(f"Script '{script_name}' is for internal use only")
        return False, errors, warnings
```

**验证**: `python3 run_script.py --script runtime_ledger.py` → `ERROR: Script 'runtime_ledger.py' is for internal use only`

---

### 4.3 hidden PTY 检测增强

**修复前**:
```python
def is_hidden_pty() -> bool:
    codex_thread_id = os.environ.get("CODEX_THREAD_ID", "")
    if codex_thread_id:
        return True
    return False
```

**修复后**:
```python
def is_hidden_pty() -> bool:
    # 1. hidden_context 文件检查
    hidden_context_file = Path.home() / ".claude" / "hidden_context"
    if hidden_context_file.exists():
        return True

    # 2. tmux session 名称检查
    if "TMUX" in os.environ:
        session_name = subprocess.run(["tmux", "display-message", "-p", "#S"], ...).stdout.strip()
        if session_name.startswith("_") or session_name == "hidden":
            return True

    # 3. TTY 验证
    if codex_thread_id and not _verify_visible_terminal():
        return True

    return False
```

---

### 4.4 Phase 5 独立文档

**修复前**: 无 Phase 5 独立文档

**修复后**: `docs/tmux-runtime-governance-phase5-implementation.md` 包含：
- 阶段 5 目标与交付物
- 注册表结构（2.1-2.3 节）
- 调度器实现（3.1-3.2 节）
- 脚本迁移执行（4.1-4.2 节）
- 阶段 5 验收测试（5.1-5.2 节）
- 阶段 5 验收确认（6.1-6.2 节）

---

## 5. 文档口径核验

### 5.1 脚本数量

| 文档 | 声称数量 | 实际数量 | 判定 |
|------|----------|----------|------|
| Phase 6（修正前） | 23 个 | 22 个 | ❌ 不实 |
| Phase 6（修正后） | 22 个 | 22 个 | ✅ 一致 |

### 5.2 注册制接管表述

| 文档 | 原表述 | 修正后表述 | 判定 |
|------|--------|------------|------|
| Phase 6 | "脚本执行受注册制控制" | "主链通过 tmux_scheduler.py 调用各阶段脚本" | ✅ 准确 |
| Phase 6 | "正式脚本有且只有一种受控调用方式" | 删除该绝对化表述，改为"主链已接入调度器" | ✅ 准确 |

---

## 6. 最终核验清单

| 核验项 | 方法 | 结果 |
|--------|------|------|
| Phase 0-6 文档齐全 | `ls docs/tmux-runtime-governance-*.md` | ✅ 8 个文件 |
| SCRIPT_REGISTRY.json 有效 | `python3 -c "import json; json.load(open(...))"` | ✅ 有效 JSON |
| tmux_scheduler 模块可导入 | `python3 -c "import tmux_scheduler"` | ✅ 导入成功 |
| run_script.py 可执行 | `python3 run_script.py --list` | ✅ 正常输出 |
| internal_only 拦截有效 | `python3 run_script.py --script runtime_ledger.py` | ✅ 拒绝执行 |
| 主链使用调度器 | `grep -c "run_json_script" start_formal_runtime_chain.py` | ✅ 7 处调用 |

---

## 7. 审计结论

**整体判定**: `已完成`

**依据**:
1. 所有 7 个阶段均有独立交付文档
2. 主链已通过 `tmux_scheduler.py` 接入调度器
3. internal_only 拦截已实现并测试通过
4. hidden PTY 检测已增强
5. Phase 5 独立文档已创建
6. Phase 6 文档已修正夸大表述
7. 所有与原任务书冲突的点已修复

**无遗留未完成项**。

---

**审计报告结束**
