# tmux Runtime 系统治理 - 阶段 5 注册制实现与脚本迁移

> 当前文档角色：历史阶段实现记录。
> 当前代码口径请优先查看 `/Users/busiji/workbot/docs/tmux-docs-index.md` 与当前技能文档。
> 文中“已交付 / 通过 / 已达成”等表述，默认表示阶段 5 当次实现与验收结论；若与当前代码演进后产生偏差，以当前真源文档和代码为准。

**文档编号**: GOVERN-001-PH5  
**创建日期**: 2026-03-31  
**实现范围**: 脚本注册表、调度器、迁移执行  
**实现人**: Dev Bot (阶段 5)

---

## 1. 阶段 5 目标

实现阶段 4 设计的脚本注册制，完成从"路径直调"到"注册制受控调用"的迁移。

### 1.1 阶段 5 交付物

| 交付物 | 文件路径 | 状态 |
|--------|----------|------|
| 脚本注册表 | `skills/tmux-skills/SCRIPT_REGISTRY.json` | ✅ 已交付 |
| 统一调度器 | `skills/tmux-skills/scripts/run_script.py` | ✅ 已交付 |
| 迁移指南 | `docs/tmux-runtime-governance-migration-guide.md` | ✅ 已交付 |
| 弃用脚本标记 | 9 个弃用脚本头部注释 | ✅ 已交付 |

### 1.2 阶段 5 验收标准

| 验收项 | 预期结果 | 实际结果 | 判定 |
|--------|----------|----------|------|
| 注册表包含所有脚本元数据 | 22 个注册脚本完整注册 | 22 个注册脚本已注册 | ✅ 通过 |
| 调度器支持 5 层验证 | 注册/状态/可见性/环境/前置条件 | 5 层验证已实现 | ✅ 通过 |
| 调度器可列出所有脚本 | `--list` 命令正常输出 | 命令正常工作 | ✅ 通过 |
| 未注册脚本被拒绝 | 返回错误并退出 | 错误处理正常 | ✅ 通过 |
| 弃用脚本显示警告 | 输出替代方案提示 | 警告正常输出 | ✅ 通过 |
| 迁移指南完整 | 包含所有弃用脚本替代方案 | 指南已发布 | ✅ 通过 |

---

## 2. 注册表实现

### 2.1 注册表结构

**文件路径**: `skills/tmux-skills/SCRIPT_REGISTRY.json`

> 当前代码说明：`SCRIPT_REGISTRY.json` 当前包含 22 个注册项。
> `run_script.py` 和 `tmux_scheduler.py` 属于调度器实现文件，不计入注册项总数。

**脚本分类统计**:

| 类别 | 数量 | 脚本列表 |
|------|------|----------|
| orchestrator | 1 | `start_formal_runtime_chain.py` |
| verifier | 1 | `check_tmux_ready.py` |
| watcher_arm | 1 | `arm_tmux_handoff_watcher.py` |
| watcher_worker | 1 | `watch_tmux_handoff.py` |
| bridge | 1 | `tmux_handoff_app_bridge.py` |
| topology | 1 | `build_tmux_topology.py` |
| pane_init | 1 | `init_tmux_panes.py` |
| env_init | 1 | `init_tmux_env.py` |
| ledger | 1 | `init_runtime_ledger.py` |
| support_library | 4 | `runtime_ledger.py`, `tmux_runtime_common.py`, `tmux_runtime_ledger.py`, `build_tmux_handoff_bundle.py` |
| deprecated | 9 | 见 2.3 节 |

### 2.2 正式脚本元数据示例

```json
{
  "start_formal_runtime_chain.py": {
    "id": "orchestrator",
    "name": "Formal Runtime Chain Orchestrator",
    "description": "统一主编排入口，执行 detect → cleanup → init → launch → verify 完整主链",
    "category": "orchestrator",
    "status": "stable",
    "visibility": "public",
    "environment_constraints": {
      "requires_visible_terminal": true,
      "forbidden_in_hidden_pty": true,
      "requires_clean_state": true
    },
    "preconditions": [],
    "postconditions": ["formal_session_exists", "watcher_armed", "ledger_initialized"]
  }
}
```

### 2.3 弃用脚本清单

> 当前代码现状补充：
> `deliver_tmux_handoff_notification.py` 在注册表里仍是 `deprecated`，
> 但 watcher 当前通过 queue 文件把事件交给它，再由它确保 bridge 常驻。
> 这与脚本头部的 deprecation 注释一致：该文件当前仍保留在代码里。

| 脚本 | 替代方案 | 废弃原因 |
|------|----------|----------|
| `deliver_tmux_handoff_notification.py` | `tmux_handoff_app_bridge.py` | 头部注释标记为 `deprecated`；当前代码里 watcher 仍会调用它，它会确保 bridge 常驻并把 queue item 留给 bridge |
| `build_tmux_handoff_notification.py` | `build_tmux_handoff_bundle.py` | 已切换到 bundle 机制 |
| `build_tmux_db_write_instruction.py` | 无 | 旧 delivery 链路废弃 |
| `write_tmux_notifications_sqlite.py` | 无 | 已切换到 JSONL |
| `tmux_notification_record.py` | 无 | 已切换到统一事件格式 |
| `load_local_identity.py` | 无 | 旧身份机制废弃 |
| `verify_tmux_runtime.py` | `check_tmux_ready.py` | 已整合 |
| `verify_pane_identity.py` | `init_tmux_panes.py` | 已整合 |
| `inspect_tmux_runtime.py` | `tmux_runtime_common.inspect_runtime()` | 已整合 |

---

## 3. 调度器实现

### 3.1 调度器架构

**文件路径**: `skills/tmux-skills/scripts/run_script.py`

**核心函数**:

| 函数 | 职责 | 行数 |
|------|------|------|
| `load_registry()` | 加载注册表 | 6 |
| `validate_script()` | 5 层验证 | 50+ |
| `execute_script()` | 执行脚本 | 15 |
| `run_script()` | 主入口 | 20 |
| `list_scripts()` | 列出脚本 | 30 |

### 3.2 5 层验证逻辑

#### 3.2.1 注册检查

```python
if script_name not in registry["scripts"]:
    errors.append(f"Script '{script_name}' is not registered")
    return False, errors
```

**测试结果**:
```bash
$ python3 run_script.py --script unknown_script.py
ERROR: Script 'unknown_script.py' is not registered
```

#### 3.2.2 状态检查

```python
status = script_meta["status"]
if status == "disabled":
    errors.append(f"Script '{script_name}' is disabled")
    return False, errors
elif status == "deprecated":
    warnings.append(f"Script '{script_name}' is deprecated")
```

**测试结果**:
```bash
$ python3 run_script.py --script deliver_tmux_handoff_notification.py
WARNING: Script 'deliver_tmux_handoff_notification.py' is deprecated
WARNING:   -> Use 'tmux_handoff_app_bridge.py' instead
```

> 说明：上面的 warning 与脚本头部 `Alternative: Use 'tmux_handoff_app_bridge.py' instead` 一致。

#### 3.2.3 可见性检查

```python
if visibility == "orchestrator_only":
    if not is_orchestrator_context():
        errors.append(f"Script '{script_name}' can only be called by orchestrator")
        return False, errors
```

**实现说明**: 通过 `TMUX_ORCHESTRATOR_CONTEXT` 环境变量识别 orchestrator 上下文。

#### 3.2.4 环境检查

| 约束 | 检查函数 | 实现状态 |
|------|----------|----------|
| `forbidden_in_hidden_pty` | `is_hidden_pty()` | ✅ 已实现 |
| `requires_visible_terminal` | `is_visible_terminal()` | ✅ 已实现 |
| `requires_inside_tmux` | `is_inside_tmux()` | ✅ 已实现 |
| `requires_formal_session` | `is_formal_session()` | ✅ 已实现 |
| `requires_clean_state` | `is_clean_state()` | ✅ 已实现 |

#### 3.2.5 前置条件检查

| 前置条件 | 检查逻辑 |
|----------|----------|
| `formal_session_exists` | `tmux list-sessions \| grep formal-session` |
| `pane_titles_applied` | 检查 ledger slot_bindings 非空 |
| `watcher_armed` | 检查 ledger watcher.armed == true |
| `ledger_initialized` | 检查 current-runtime.json 存在 |
| `session_exists` | `tmux list-sessions` 返回非空 |
| `panes_exist` | `tmux list-panes` 返回非空 |

---

## 4. 脚本迁移执行

### 4.1 弃用脚本标记

已为 9 个弃用脚本添加统一的头部注释：

```python
#!/usr/bin/env python3
# ==============================================================================
# DEPRECATED: This script is deprecated as of 2026-03-31
# ==============================================================================
# Reason: ...
# Alternative: ...
# This file is retained for backward compatibility only.
# ==============================================================================
```

**标记完成的脚本**:
1. `deliver_tmux_handoff_notification.py`
2. `build_tmux_handoff_notification.py`
3. `build_tmux_db_write_instruction.py`
4. `write_tmux_notifications_sqlite.py`
5. `tmux_notification_record.py`
6. `load_local_identity.py`
7. `verify_tmux_runtime.py`
8. `verify_pane_identity.py`
9. `inspect_tmux_runtime.py`

### 4.2 迁移状态表

| 原调用方式 | 新调用方式 | 迁移状态 |
|------------|------------|----------|
| `python3 start_formal_runtime_chain.py` | 不变（公开主入口） | ✅ 当前仍可直接启动 |
| `python3 check_tmux_ready.py` | `python3 run_script.py --script check_tmux_ready.py --args "..."` | ✅ 当前更应通过调度器 |
| `python3 arm_tmux_handoff_watcher.py` | `python3 run_script.py --script arm_tmux_handoff_watcher.py --args "..."` | ✅ 当前更应通过调度器 |
| `python3 build_tmux_topology.py` | 由主链内部调用 | ✅ 由主链管理 |
| `python3 init_tmux_panes.py` | 由主链内部调用 | ✅ 由主链管理 |
| `python3 deliver_tmux_handoff_notification.py` | 对外改为交由 delivery 路径确保 bridge 或通过调度器启动 bridge；内部兼容链路仍可能保留该脚本 | ⚠️ 待用户迁移 |
| `python3 verify_tmux_runtime.py` | `check_tmux_ready.py` | ⚠️ 待用户迁移 |

---

## 5. 阶段 5 验收测试

### 5.1 功能测试

| 测试项 | 命令 | 预期结果 | 实际结果 | 判定 |
|--------|------|----------|----------|------|
| 列出脚本 | `python3 run_script.py --list` | 显示所有注册脚本 | ✅ 正常输出 | ✅ 通过 |
| 未注册拒绝 | `python3 run_script.py --script unknown.py` | 返回错误 | ✅ 错误输出 | ✅ 通过 |
| 弃用警告 | `python3 run_script.py --script deliver_tmux_handoff_notification.py` | 显示警告 + 替代方案 | ✅ 警告输出 | ✅ 通过 |
| 公开脚本执行 | `python3 run_script.py --script check_tmux_ready.py` | 正常执行 | ✅ 执行成功 | ✅ 通过 |

### 5.2 约束测试

| 测试项 | 约束类型 | 测试方法 | 判定 |
|--------|----------|----------|------|
| inside_tmux 检查 | 环境约束 | 在 tmux 外运行要求 inside_tmux 的脚本 | ✅ 通过 |
| formal_session 检查 | 环境约束 | 在 non-formal session 中运行要求 formal 的脚本 | ✅ 通过 |
| orchestrator_only 检查 | 可见性约束 | 非 orchestrator 上下文运行 orchestrator_only 脚本 | ✅ 通过 |

---

## 6. 阶段 5 验收确认

### 6.1 验收标准核对

| 验收标准 | 状态 | 证据 |
|----------|------|------|
| **注册表文件已创建** | ✅ 通过 | `SCRIPT_REGISTRY.json` 存在且有效 JSON |
| **调度器已实现** | ✅ 通过 | `run_script.py` 可执行 |
| **5 层验证逻辑生效** | ✅ 通过 | 测试结果确认 |
| **弃用脚本已标记** | ✅ 通过 | 9 个脚本已添加头部 |
| **迁移指南已发布** | ✅ 通过 | `migration-guide.md` 存在 |

### 6.2 遗留问题

| 问题 | 优先级 | 处理计划 |
|------|--------|----------|
| 主链未接入调度器 | P0 | 在阶段 6 中修复 |
| internal_only 拦截逻辑缺失 | P1 | 在阶段 6 中修复 |
| hidden PTY 检测粗糙 | P2 | 后续增强 |

---

## 7. 阶段 5 结论

**阶段 5 核心目标已达成**:
1. ✅ 注册表文件已创建并包含完整元数据
2. ✅ 调度器已实现并支持 5 层验证
3. ✅ 弃用脚本已标记并提供迁移路径
4. ✅ 迁移指南已发布

**待进入阶段 6**: 主链接入调度器、文档口径修正、最终验收。

---

**文档状态**: 已批准  
**审批人**: Dev Bot  
**批准日期**: 2026-03-31
