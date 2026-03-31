# tmux Runtime 系统治理 - 阶段 4 脚本注册制设计

**文档编号**: GOVERN-001-PH4  
**创建日期**: 2026-03-31  
**设计范围**: 脚本注册表、调度入口、校验规则  
**设计人**: Dev Bot (阶段 4)

---

## 1. 阶段 4 目标

设计正式脚本注册制，把"按路径直接调用脚本"升级为"按规则调用受控能力"。

### 1.1 需要回答的问题

- [x] 哪些脚本是正式脚本
- [x] 哪些脚本允许外部直接调用
- [x] 哪些脚本只能由 orchestrator 调用
- [x] 哪些脚本要求 clean environment
- [x] 哪些脚本禁止在 hidden PTY 运行
- [x] 哪些脚本会启动后台进程
- [x] 哪些脚本处于 stable / testing / deprecated / disabled 状态

---

## 2. 脚本分类清单

### 2.1 正式脚本（Formal Scripts）

**定义**：构成主链必要环节的脚本，必须通过注册校验才能执行。

| 脚本名 | 类别 | 调用权限 | 环境约束 | 后台进程 | 状态 |
|--------|------|----------|----------|----------|------|
| `start_formal_runtime_chain.py` | orchestrator | 公开 | visible_terminal | 否 | 🟢 stable |
| `check_tmux_ready.py` | verifier | 公开 | inside_tmux | 否 | 🟢 stable |
| `arm_tmux_handoff_watcher.py` | watcher_arm | 公开 | inside_tmux, formal_session | 是 (worker) | 🟢 stable |
| `watch_tmux_handoff.py` | watcher_worker | orchestrator_only | inside_tmux | 是 (自身) | 🟢 stable |
| `tmux_handoff_app_bridge.py` | bridge | 公开 | 无 | 是 (常驻) | 🟢 stable |
| `build_tmux_topology.py` | topology | orchestrator_only | inside_tmux, formal_session | 否 | 🟢 stable |
| `init_tmux_panes.py` | pane_init | orchestrator_only | inside_tmux, formal_session | 否 | 🟢 stable |
| `init_tmux_env.py` | env_init | orchestrator_only | visible_terminal | 否 | 🟢 stable |
| `init_runtime_ledger.py` | ledger | orchestrator_only | inside_tmux, formal_session | 否 | 🟢 stable |

---

### 2.2 支撑库脚本（Support Libraries）

**定义**：被其他脚本导入的模块，不直接执行。

| 脚本名 | 用途 | 状态 |
|--------|------|------|
| `runtime_ledger.py` | Ledger 读写 API | 🟢 stable |
| `tmux_runtime_common.py` | Runtime inspection 公共函数 | 🟢 stable |
| `tmux_runtime_ledger.py` | Ledger 辅助函数 | 🟡 testing |
| `build_tmux_handoff_bundle.py` | Handoff 事件打包 | 🟢 stable |

---

### 2.3 弃用/历史脚本（Deprecated/Legacy）

**定义**：不再推荐使用的脚本，应逐步移除。

| 脚本名 | 原用途 | 废弃原因 | 替代方案 | 状态 |
|--------|--------|----------|----------|------|
| `deliver_tmux_handoff_notification.py` | 旧 delivery runner | 已切换到 window IPC bridge | `tmux_handoff_app_bridge.py` | 🔴 deprecated |
| `build_tmux_handoff_notification.py` | 旧通知构建 | 已切换到 bundle 机制 | `build_tmux_handoff_bundle.py` | 🔴 deprecated |
| `build_tmux_db_write_instruction.py` | DB 写指令 | 旧 delivery 链路 | 无（功能已废弃） | 🔴 deprecated |
| `write_tmux_notifications_sqlite.py` | SQLite 持久化 | 已切换到 JSONL | 无（功能已简化） | 🔴 deprecated |
| `tmux_notification_record.py` | 通知记录 | 已切换到统一事件格式 | 无（功能已整合） | 🔴 deprecated |
| `load_local_identity.py` | 本地身份加载 | 旧身份机制 | 无（功能已废弃） | 🔴 deprecated |
| `verify_tmux_runtime.py` | Runtime 验证 | 已整合到 `check_tmux_ready.py` | `check_tmux_ready.py` | 🔴 deprecated |
| `verify_pane_identity.py` | Pane 身份验证 | 已整合到 `init_tmux_panes.py` | `init_tmux_panes.py` | 🔴 deprecated |
| `inspect_tmux_runtime.py` | Runtime 检查 | 已整合到 `tmux_runtime_common.py` | `tmux_runtime_common.inspect_runtime()` | 🔴 deprecated |

---

### 2.4 辅助工具脚本（Utilities）

**定义**：用于特定场景的工具脚本，不进入主链。

| 脚本名 | 用途 | 调用权限 | 状态 |
|--------|------|----------|------|
| `tmux_handoff_app_bridge.py` | Window IPC bridge 常驻 | 公开（可独立启动） | 🟢 stable |

---

## 3. 注册表结构设计

### 3.1 注册表文件格式

**注册表路径**：`/Users/busiji/workbot/skills/tmux-skills/SCRIPT_REGISTRY.json`

**结构**：
```json
{
  "version": "1.0",
  "updated_at": "2026-03-31T00:00:00Z",
  "scripts": {
    "start_formal_runtime_chain.py": {
      "id": "orchestrator",
      "name": "Formal Runtime Chain Orchestrator",
      "description": "统一主编排入口，执行 detect → cleanup → init → launch → verify 完整主链",
      "category": "orchestrator",
      "status": "stable",
      "visibility": "public",
      "entry_point": "start_formal_runtime_chain.py",
      "environment_constraints": {
        "requires_visible_terminal": true,
        "requires_inside_tmux": false,
        "requires_formal_session": false,
        "requires_clean_state": true,
        "forbidden_in_hidden_pty": true
      },
      "spawns_background_process": false,
      "side_effects": ["kills_all_tmux_sessions", "clears_runtime_state", "creates_formal_session"],
      "input_parameters": {
        "codex_thread_id": {"type": "string", "required": true},
        "pane_titles": {"type": "array<string>", "required": true},
        "formal_session": {"type": "string", "required": false, "default": "formal-session"},
        "task_id": {"type": "string", "required": false, "default": "tmux-skills-public-run"}
      },
      "output": {
        "type": "json",
        "fields": ["status", "formal_session", "pane_count", "pane_titles", "steps", "chain"]
      },
      "preconditions": [],
      "postconditions": ["formal_session_exists", "watcher_armed", "ledger_initialized"]
    },
    "check_tmux_ready.py": {
      "id": "verifier",
      "name": "Runtime Readiness Verifier",
      "description": "验收脚本，审计 pane count、titles、CODEX_THREAD_ID binding、watcher arming",
      "category": "verifier",
      "status": "stable",
      "visibility": "public",
      "entry_point": "check_tmux_ready.py",
      "environment_constraints": {
        "requires_visible_terminal": false,
        "requires_inside_tmux": true,
        "requires_formal_session": true,
        "requires_clean_state": false,
        "forbidden_in_hidden_pty": false
      },
      "spawns_background_process": false,
      "side_effects": [],
      "input_parameters": {
        "formal_session_name": {"type": "string", "required": false, "default": "formal-session"},
        "expected_pane_count": {"type": "int", "required": false},
        "require_formal": {"type": "bool", "required": false, "default": false},
        "require_watcher": {"type": "bool", "required": false, "default": false}
      },
      "output": {
        "type": "json",
        "fields": ["runtime_status", "formal_session_name", "formal_pane_count", "reasons", "warnings", "next_action"]
      },
      "preconditions": ["formal_session_exists"],
      "postconditions": []
    },
    "arm_tmux_handoff_watcher.py": {
      "id": "watcher_arm",
      "name": "Watcher Arm",
      "description": "启动/管理 stopped-pane watcher 进程",
      "category": "watcher_arm",
      "status": "stable",
      "visibility": "public",
      "entry_point": "arm_tmux_handoff_watcher.py",
      "environment_constraints": {
        "requires_visible_terminal": false,
        "requires_inside_tmux": true,
        "requires_formal_session": true,
        "requires_clean_state": false,
        "forbidden_in_hidden_pty": false
      },
      "spawns_background_process": true,
      "side_effects": ["spawns_watcher_process", "updates_ledger"],
      "input_parameters": {
        "formal_session_name": {"type": "string", "required": false, "default": "formal-session"},
        "targets": {"type": "array<string>", "required": false},
        "interval": {"type": "float", "required": false, "default": 10.0}
      },
      "output": {
        "type": "json",
        "fields": ["status", "targets", "watcher_pid", "deliver_enabled"]
      },
      "preconditions": ["formal_session_exists", "pane_titles_applied"],
      "postconditions": ["watcher_armed", "watcher_process_running"]
    }
  }
}
```

---

### 3.2 脚本元数据字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | string | 脚本唯一标识符（用于日志和审计） |
| `name` | string | 人类可读的名称 |
| `description` | string | 脚本职责描述 |
| `category` | enum | 脚本类别（orchestrator / verifier / watcher_arm / topology / pane_init / env_init / ledger / bridge / utility） |
| `status` | enum | 脚本状态（stable / testing / deprecated / disabled） |
| `visibility` | enum | 可见性（public / orchestrator_only / internal_only） |
| `entry_point` | string | 入口脚本文件名 |
| `environment_constraints` | object | 环境约束（见下节） |
| `spawns_background_process` | bool | 是否会启动后台进程 |
| `side_effects` | array | 副作用列表 |
| `input_parameters` | object | 输入参数定义 |
| `output` | object | 输出格式定义 |
| `preconditions` | array | 前置条件列表 |
| `postconditions` | array | 后置条件列表 |

---

### 3.3 环境约束字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `requires_visible_terminal` | bool | 是否要求从可见终端启动 |
| `requires_inside_tmux` | bool | 是否要求在 tmux 内部运行 |
| `requires_formal_session` | bool | 是否要求 formal-session 已存在 |
| `requires_clean_state` | bool | 是否要求干净状态（无旧 session/ledger/watcher） |
| `forbidden_in_hidden_pty` | bool | 是否禁止在 hidden PTY 运行 |

---

## 4. 调度入口设计

### 4.1 统一调度器

**调度器路径**：`/Users/busiji/workbot/skills/tmux-skills/scripts/run_script.py`

**职责**：
1. 加载注册表
2. 校验请求的脚本是否已注册
3. 校验环境约束是否满足
4. 校验前置条件是否满足
5. 执行脚本
6. 记录审计日志

**调用方式**：
```bash
python3 run_script.py --script start_formal_runtime_chain.py --args "..."
```

---

### 4.2 调度器伪代码

```python
def run_script(script_name: str, args: list[str]) -> int:
    # Step 1: Load registry
    registry = load_registry()
    
    # Step 2: Check if script is registered
    if script_name not in registry["scripts"]:
        print(f"ERROR: Script '{script_name}' is not registered")
        return 1
    
    script_meta = registry["scripts"][script_name]
    
    # Step 3: Check status
    if script_meta["status"] == "disabled":
        print(f"ERROR: Script '{script_name}' is disabled")
        return 1
    elif script_meta["status"] == "deprecated":
        print(f"WARNING: Script '{script_name}' is deprecated")
    
    # Step 4: Check visibility
    if script_meta["visibility"] == "orchestrator_only":
        if not is_called_by_orchestrator():
            print(f"ERROR: Script '{script_name}' can only be called by orchestrator")
            return 1
    
    # Step 5: Check environment constraints
    env_constraints = script_meta["environment_constraints"]
    if env_constraints.get("forbidden_in_hidden_pty") and is_hidden_pty():
        print(f"ERROR: Script '{script_name}' cannot run in hidden PTY")
        return 1
    if env_constraints.get("requires_visible_terminal") and not is_visible_terminal():
        print(f"ERROR: Script '{script_name}' requires visible terminal")
        return 1
    if env_constraints.get("requires_inside_tmux") and not inside_tmux():
        print(f"ERROR: Script '{script_name}' requires running inside tmux")
        return 1
    if env_constraints.get("requires_clean_state") and not is_clean_state():
        print(f"ERROR: Script '{script_name}' requires clean state")
        return 1
    
    # Step 6: Check preconditions
    for precondition in script_meta.get("preconditions", []):
        if not check_precondition(precondition):
            print(f"ERROR: Precondition '{precondition}' not met")
            return 1
    
    # Step 7: Execute script
    return execute_script(script_meta["entry_point"], args)
```

---

## 5. 校验规则设计

### 5.1 注册校验（Registration Check）

**规则**：未注册脚本不得进入正式链路。

```python
def check_registration(script_name: str) -> tuple[bool, str]:
    registry = load_registry()
    if script_name not in registry["scripts"]:
        return False, f"Script '{script_name}' is not registered"
    return True, ""
```

---

### 5.2 状态校验（Status Check）

**规则**：disabled 脚本不得执行；deprecated 脚本执行前需警告。

```python
def check_status(script_name: str) -> tuple[bool, str]:
    registry = load_registry()
    status = registry["scripts"][script_name]["status"]
    if status == "disabled":
        return False, f"Script '{script_name}' is disabled"
    if status == "deprecated":
        return True, f"WARNING: Script '{script_name}' is deprecated"
    return True, ""
```

---

### 5.3 可见性校验（Visibility Check）

**规则**：orchestrator_only 脚本只能由 orchestrator 调用。

```python
def check_visibility(script_name: str) -> tuple[bool, str]:
    registry = load_registry()
    visibility = registry["scripts"][script_name]["visibility"]
    if visibility == "orchestrator_only":
        if not is_orchestrator_context():
            return False, f"Script '{script_name}' can only be called by orchestrator"
    return True, ""
```

---

### 5.4 环境约束校验（Environment Check）

**规则**：环境约束不满足时拒绝执行。

```python
def check_environment(script_name: str) -> tuple[bool, list[str]]:
    registry = load_registry()
    constraints = registry["scripts"][script_name]["environment_constraints"]
    errors = []
    
    if constraints.get("forbidden_in_hidden_pty") and is_hidden_pty():
        errors.append("Cannot run in hidden PTY")
    if constraints.get("requires_visible_terminal") and not is_visible_terminal():
        errors.append("Requires visible terminal")
    if constraints.get("requires_inside_tmux") and not inside_tmux():
        errors.append("Requires running inside tmux")
    if constraints.get("requires_clean_state") and not is_clean_state():
        errors.append("Requires clean state")
    
    return len(errors) == 0, errors
```

---

### 5.5 前置条件校验（Precondition Check）

**规则**：前置条件不满足时拒绝执行。

| 前置条件 | 检查方式 |
|----------|----------|
| `formal_session_exists` | `tmux list-sessions \| grep formal-session` |
| `pane_titles_applied` | 检查 ledger slot_bindings 非空 |
| `watcher_armed` | 检查 ledger watcher.armed == true |
| `ledger_initialized` | 检查 current-runtime.json 存在 |

---

## 6. 与现有脚本迁移的映射方案

### 6.1 迁移策略

**阶段式迁移**：
1. **阶段 1**：创建注册表，标记所有脚本的当前状态
2. **阶段 2**：实现调度器，对公开脚本启用注册校验
3. **阶段 3**：将 orchestrator_only 脚本纳入注册体系
4. **阶段 4**：标记 deprecated 脚本，提供迁移指南
5. **阶段 5**：移除 deprecated 脚本（等待用户完成迁移后）

---

### 6.2 映射表

| 原调用方式 | 新调用方式 | 迁移状态 |
|------------|------------|----------|
| `python3 start_formal_runtime_chain.py ...` | 不变（公开入口） | 🟢 无需迁移 |
| `python3 check_tmux_ready.py ...` | 不变（公开入口） | 🟢 无需迁移 |
| `python3 build_tmux_topology.py ...` | `python3 run_script.py --script build_tmux_topology.py ...` | 🟡 建议迁移 |
| `python3 init_tmux_panes.py ...` | `python3 run_script.py --script init_tmux_panes.py ...` | 🟡 建议迁移 |
| `python3 init_tmux_env.py ...` | `python3 run_script.py --script init_tmux_env.py ...` | 🟡 建议迁移 |
| `python3 deliver_tmux_handoff_notification.py ...` | `python3 tmux_handoff_app_bridge.py` | 🔴 必须迁移 |

---

## 7. 阶段 4 验收确认

### 7.1 验收标准核对

| 验收标准 | 当前状态 | 证据 |
|----------|----------|------|
| **注册制不是简单白名单，而是执行治理机制** | ✅ 已满足 | 注册表包含环境约束、可见性、前置条件等治理规则 |
| **可以表达脚本职责、入口权限、执行环境约束、状态** | ✅ 已满足 | 元数据字段完整（category / visibility / constraints / status） |
| **可以阻止错环境执行、跳步骤执行、未注册执行** | ✅ 已满足 | 调度器包含环境校验、前置条件校验、注册校验 |
| **可以支持后续渐进迁移，而不是一刀切替换** | ✅ 已满足 | 迁移策略分 5 个阶段，公开入口保持不变 |

---

## 8. 下一步建议

建议进入**阶段 5：注册制实现与脚本迁移**，按以下顺序实现：

1. 创建 `SCRIPT_REGISTRY.json` 注册表文件
2. 实现 `run_script.py` 调度器
3. 实现校验规则函数
4. 迁移公开脚本到注册体系
5. 标记 deprecated 脚本
6. 编写迁移指南
