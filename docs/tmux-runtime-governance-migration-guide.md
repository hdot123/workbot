# tmux-skills 脚本注册制迁移指南

**文档编号**: GOVERN-001-MIGRATION  
**创建日期**: 2026-03-31  
**适用版本**: SCRIPT_REGISTRY.json v1.0  

---

## 1. 概述

tmux-skills 系统现已引入脚本注册制，通过 `SCRIPT_REGISTRY.json` 和 `run_script.py` 调度器实现受控的脚本执行。

### 1.1 迁移范围

| 类别 | 迁移要求 | 时间线 |
|------|----------|--------|
| **公开脚本** (public) | 无需迁移，保持原有调用方式 | 立即生效 |
| **Orchestrator 脚本** (orchestrator_only) | 建议通过调度器调用 | 建议迁移 |
| **弃用脚本** (deprecated) | 必须迁移到替代方案 | 尽快迁移 |
| **支持库** (support_library) | 作为模块导入，无需迁移 | N/A |

---

## 2. 调用方式对照表

### 2.1 公开脚本（Public Scripts）

公开脚本保持原有调用方式，无需更改：

| 脚本 | 原调用方式 | 新调用方式 | 状态 |
|------|------------|------------|------|
| `start_formal_runtime_chain.py` | `python3 start_formal_runtime_chain.py ...` | 不变 | 🟢 无需迁移 |
| `check_tmux_ready.py` | `python3 check_tmux_ready.py ...` | 不变 | 🟢 无需迁移 |
| `arm_tmux_handoff_watcher.py` | `python3 arm_tmux_handoff_watcher.py ...` | 不变 | 🟢 无需迁移 |
| `tmux_handoff_app_bridge.py` | `python3 tmux_handoff_app_bridge.py ...` | 不变 | 🟢 无需迁移 |

**示例**：
```bash
# Fresh start - 保持不变
python3 /Users/busiji/workbot/skills/tmux-skills/scripts/start_formal_runtime_chain.py \
  --codex-thread-id "thread_abc123" \
  --pane-count 4 \
  --pane-titles "task-1,task-2,notes,monitor"
```

---

### 2.2 Orchestrator 脚本（Orchestrator Only）

Orchestrator 脚本只能由 `start_formal_runtime_chain.py` 内部调用，不建议直接执行。

| 脚本 | 原调用方式 | 新调用方式 | 状态 |
|------|------------|------------|------|
| `build_tmux_topology.py` | `python3 build_tmux_topology.py ...` | 通过主链自动调用 | 🟡 由主链管理 |
| `init_tmux_panes.py` | `python3 init_tmux_panes.py ...` | 通过主链自动调用 | 🟡 由主链管理 |
| `init_tmux_env.py` | `python3 init_tmux_env.py ...` | 通过主链自动调用 | 🟡 由主链管理 |
| `init_runtime_ledger.py` | `python3 init_runtime_ledger.py ...` | 通过主链自动调用 | 🟡 由主链管理 |
| `watch_tmux_handoff.py` | `python3 watch_tmux_handoff.py ...` | 通过 watcher arm 调用 | 🟡 由主链管理 |

**如确需独立调用**（调试场景），可通过调度器：

```bash
# 通过调度器调用（设置 orchestrator 上下文）
export TMUX_ORCHESTRATOR_CONTEXT=true
python3 /Users/busiji/workbot/skills/tmux-skills/scripts/run_script.py \
  --script build_tmux_topology.py \
  --args "--session-name formal-session --pane-count 4"
```

---

### 2.3 弃用脚本（Deprecated Scripts）

**⚠️ 必须迁移** - 弃用脚本将在未来版本中移除。

| 弃用脚本 | 替代方案 | 迁移方式 |
|---------|----------|----------|
| `deliver_tmux_handoff_notification.py` | `tmux_handoff_app_bridge.py` | 使用 window IPC bridge |
| `build_tmux_handoff_notification.py` | `build_tmux_handoff_bundle.py` | 使用 bundle 机制 |
| `build_tmux_db_write_instruction.py` | 无（功能废弃） | 移除相关调用 |
| `write_tmux_notifications_sqlite.py` | 无（功能简化） | 使用 JSONL 日志 |
| `tmux_notification_record.py` | 无（功能整合） | 使用统一事件格式 |
| `load_local_identity.py` | 无（功能废弃） | 移除相关调用 |
| `verify_tmux_runtime.py` | `check_tmux_ready.py` | 使用新版验收脚本 |
| `verify_pane_identity.py` | `init_tmux_panes.py` | 使用 pane title 应用脚本 |
| `inspect_tmux_runtime.py` | `tmux_runtime_common.inspect_runtime()` | 导入公共模块 |

---

## 3. 弃用脚本迁移详解

### 3.1 Delivery 链路迁移

**旧方式**（已弃用）：
```bash
python3 deliver_tmux_handoff_notification.py --event-file event.json
```

**新方式**（推荐）：
```bash
# 启动常驻 bridge 进程
python3 tmux_handoff_app_bridge.py --queue-file handoff-queue.jsonl

# handoff 事件会自动通过 window IPC 交付
```

**迁移步骤**：
1. 停止使用 `deliver_tmux_handoff_notification.py`
2. 在 formal session 启动时运行 `tmux_handoff_app_bridge.py` 作为常驻进程
3. handoff 事件写入 `handoff-queue.jsonl`，bridge 会自动处理

---

### 3.2 Notification 构建迁移

**旧方式**（已弃用）：
```bash
python3 build_tmux_handoff_notification.py --target "formal-session:1.1"
```

**新方式**（推荐）：
```bash
# 在 Python 代码中导入 bundle 构建函数
from build_tmux_handoff_bundle import build_bundle

event = {"type": "pane_state_change", "target": "formal-session:1.1"}
bundle = build_bundle(event)
```

**迁移步骤**：
1. 将 `build_tmux_handoff_bundle.py` 作为模块导入
2. 调用 `build_bundle()` 函数替代旧脚本

---

### 3.3 Runtime 验证迁移

**旧方式**（已弃用）：
```bash
python3 verify_tmux_runtime.py --require-formal
```

**新方式**（推荐）：
```bash
python3 check_tmux_ready.py --require-formal --require-watcher
```

**迁移步骤**：
1. 将所有 `verify_tmux_runtime.py` 调用替换为 `check_tmux_ready.py`
2. `check_tmux_ready.py` 提供更完整的 9 项检查

---

### 3.4 Runtime 检查迁移

**旧方式**（已弃用）：
```bash
python3 inspect_tmux_runtime.py --pretty
```

**新方式**（推荐）：
```python
# 在 Python 代码中
from tmux_runtime_common import inspect_runtime

snapshot = inspect_runtime()
print(json.dumps(snapshot, indent=2))
```

**迁移步骤**：
1. 在代码中导入 `tmux_runtime_common` 模块
2. 调用 `inspect_runtime()` 函数

---

## 4. 调度器使用指南

### 4.1 基本用法

```bash
# 列出所有注册脚本
python3 run_script.py --list

# 运行脚本
python3 run_script.py --script <script_name> --args "<args>"
```

### 4.2 调度器验证

调度器会自动执行以下验证：

1. **注册检查** - 脚本必须在 `SCRIPT_REGISTRY.json` 中注册
2. **状态检查** - disabled 脚本禁止执行，deprecated 脚本显示警告
3. **可见性检查** - orchestrator_only 脚本检查调用上下文
4. **环境检查** - 验证环境约束（visible terminal, inside tmux, 等）
5. **前置条件检查** - 验证 preconditions 是否满足

### 4.3 错误示例

```bash
# ❌ 错误：脚本未注册
python3 run_script.py --script unknown_script.py
# ERROR: Script 'unknown_script.py' is not registered

# ❌ 错误：环境约束不满足（在 hidden PTY 中运行要求 visible terminal 的脚本）
python3 run_script.py --script start_formal_runtime_chain.py
# ERROR: Script 'start_formal_runtime_chain.py' requires visible terminal

# ❌ 错误：前置条件不满足
python3 run_script.py --script check_tmux_ready.py
# ERROR: Precondition 'formal_session_exists' not met
```

---

## 5. 迁移时间表

| 阶段 | 日期 | 事项 |
|------|------|------|
| **阶段 1** | 2026-03-31 | 注册表创建，调度器实现 |
| **阶段 2** | 2026-04-07 | 弃用脚本标记完成 |
| **阶段 3** | 2026-04-14 | 完成所有迁移 |
| **阶段 4** | 2026-04-21 | 移除弃用脚本 |

---

## 6. 常见问题

### Q1: 我的脚本是否受影响？

**检查方式**：
```bash
python3 run_script.py --list
```

查看脚本的状态标记：
- 🟢 stable - 可继续使用
- 🟡 testing - 可继续使用，但处于测试状态
- 🔴 deprecated - 需要迁移到替代方案
- ⚫ disabled - 禁止使用

### Q2: 如何知道弃用脚本的替代方案？

查看 `SCRIPT_REGISTRY.json` 中的 `deprecation.alternative` 字段：

```bash
jq '.scripts["deliver_tmux_handoff_notification.py"].deprecation.alternative' \
  /Users/busiji/workbot/skills/tmux-skills/SCRIPT_REGISTRY.json
```

### Q3: 调度器能否完全替代直接调用？

对于公开脚本（public），直接调用和通过调度器调用效果相同。

对于 orchestrator_only 脚本，建议通过调度器调用以便进行验证。

### Q4: 如何添加新脚本到注册表？

在 `SCRIPT_REGISTRY.json` 中添加新的脚本条目：

```json
{
  "scripts": {
    "my_new_script.py": {
      "id": "unique_id",
      "name": "My New Script",
      "description": "Description of what it does",
      "category": "utility",
      "status": "stable",
      "visibility": "public",
      "entry_point": "my_new_script.py",
      "environment_constraints": {},
      "spawns_background_process": false,
      "side_effects": [],
      "input_parameters": {},
      "output": {"type": "none", "fields": []},
      "preconditions": [],
      "postconditions": []
    }
  }
}
```

---

## 7. 联系与支持

如有迁移问题，请参考：
- `/Users/busiji/workbot/docs/tmux-runtime-governance-phase4-registry-design.md` - 注册制设计文档
- `/Users/busiji/workbot/skills/tmux-skills/SCRIPT_REGISTRY.json` - 注册表文件

---

**文档状态**: 初稿  
**维护人**: tmux-skills 工作组
