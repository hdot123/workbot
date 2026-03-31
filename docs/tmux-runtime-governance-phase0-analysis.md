# tmux Runtime 系统治理 - 阶段 0 现状盘点与问题建模

> 当前文档角色：历史阶段分析。
> 当前代码口径请优先查看 `/Users/busiji/workbot/docs/tmux-docs-index.md`、`/Users/busiji/workbot/skills/tmux-skills/SKILL.md` 和 `/Users/busiji/workbot/docs/tmux-skills-design.md`。
> 本文中的“正式入口/当前实际使用”反映的是阶段 0 分析当时的入口盘点；当前代码里，`public` 条目是否还能直接 `python3 script.py`，还取决于各脚本顶部的 runtime enforcement。

**文档编号**: GOVERN-001-PH0  
**创建日期**: 2026-03-31  
**盘点范围**: `/Users/busiji/workbot/skills/tmux-skills/` 及相关运行面  
**盘点人**: Dev Bot (阶段 0)

---

## 1. 当前脚本与职责清单

### 1.1 核心脚本列表（当前 `scripts/` 目录共 23 个 Python 脚本）

> 下表已按当前仓库代码同步；它保留“阶段 0 盘点”结构，但脚本数量、行数和入口说明已更新到当前实现。

| 脚本名 | 行数 | 职责 | 状态 |
|--------|------|------|------|
| `start_formal_runtime_chain.py` | 1168 | **主编排入口**：cleanup -> env -> topology -> pane labeling -> surface normalization -> ledger -> watcher -> ready_check | 🟡 主链直达入口 |
| `run_script.py` | 313 | **公开调度入口**：注册校验、scheduler marker 注入、公开调度脚本 CLI | 🟡 正式入口 |
| `check_tmux_ready.py` | 262 | **验收脚本**：审计 pane count、titles、CODEX_THREAD_ID binding、watcher arming；当前代码中通常通过 scheduler 执行 | 🟡 正式验收 |
| `arm_tmux_handoff_watcher.py` | 349 | **Watcher 挂载**：启动/管理 stopped-pane watcher 进程；当前代码中通常通过 scheduler 执行 | 🟡 正式 |
| `watch_tmux_handoff.py` | 622 | **Watcher Worker**：按轮扫描 pane 状态，满足固定规则后最多一次向下游放 1 条事件 | 🟡 正式 |
| `tmux_handoff_app_bridge.py` | 708 | **Window IPC Bridge**：常驻进程，通过 Codex window IPC 投递 handoff 事件；当前代码中通常由 delivery 路径确保或通过 scheduler 执行 | 🟡 正式 |
| `deliver_tmux_handoff_notification.py` | 358 | **Delivery Runner**：确保 bridge 常驻；如果输入事件尚未落到 queue，会先写入 queue | 🟡 正式 |
| `build_tmux_topology.py` | 287 | **拓扑构建**：创建/收缩 pane 数量，应用 tiling layout | 🟡 正式 |
| `init_tmux_panes.py` | 425 | **Pane 标题应用**：批量设置 pane titles，更新 slot bindings | 🟡 正式 |
| `init_tmux_env.py` | 281 | **环境初始化**：创建 detached formal session，初始化窗口/ pane 标题 | 🟡 正式 |
| `init_runtime_ledger.py` | 154 | **Ledger 初始化**：创建 runtime ledger 元数据 | 🟡 正式 |
| `runtime_ledger.py` | 360 | **Ledger 模块**：读写 current-runtime.json，slot bindings 管理 | 🟢 支撑库 |
| `tmux_runtime_ledger.py` | 143 | **Ledger 辅助** | 🟡 支撑库 |
| `tmux_runtime_common.py` | 684 | **公共模块**：runtime inspection、session/client/pane 枚举、可见性判断 | 🟢 支撑库 |
| `build_tmux_handoff_bundle.py` | 119 | **Bundle 构建**：handoff 事件打包 | 🟡 支撑库 |
| `build_tmux_handoff_notification.py` | 118 | **通知构建** | 🟡 支撑库 |
| `write_tmux_notifications_sqlite.py` | 329 | **SQLite 持久化** | 🟡 支撑库 |
| `tmux_notification_record.py` | 148 | **通知记录** | 🟡 支撑库 |
| `build_tmux_db_write_instruction.py` | 84 | **DB 写指令** | 🔴 历史/弃用 |
| `inspect_tmux_runtime.py` | 47 | **Runtime 检查** | 🟡 辅助 |
| `verify_tmux_runtime.py` | 63 | **Runtime 验证** | 🟡 辅助 |
| `verify_pane_identity.py` | 33 | **Pane 身份验证** | 🟡 辅助 |
| `load_local_identity.py` | 33 | **本地身份加载** | 🔴 历史/弃用 |

### 1.2 支撑模块

| 模块 | 职责 |
|------|------|
| `runtime_ledger.py` | 运行时账本管理：`current-runtime.json` 读写、slot bindings、watcher 状态 |
| `tmux_runtime_common.py` | 通用 inspection：`inspect_runtime()`、可见性判断、session/client/pane 枚举 |

---

## 2. 当前入口识别

### 2.1 正式入口（当前实际使用）

**当前代码现状补充**：
- `start_formal_runtime_chain.py` 仍是主链直达入口
- `run_script.py` 是公开调度入口
- `check_tmux_ready.py`、`arm_tmux_handoff_watcher.py`、`tmux_handoff_app_bridge.py` 在注册表中属于 `public`；当前代码里，是否能直接 `python3 script.py` 还取决于各脚本顶部的 runtime enforcement

| 入口 | 调用方式 | 说明 |
|------|----------|------|
| `start_formal_runtime_chain.py` | `python3 start_formal_runtime_chain.py --codex-thread-id XXX --pane-title A --pane-title B ...` | **唯一对外主链入口**，负责 fresh start 全流程 |
| `run_script.py` | `python3 run_script.py --script <script_name> --args "..."` | **公开调度入口**，负责注册校验与 scheduler marker 注入 |
| `check_tmux_ready.py` | `python3 run_script.py --script check_tmux_ready.py --args "--require-formal --require-watcher"` | 验收/审计命令 |
| `arm_tmux_handoff_watcher.py` | `python3 run_script.py --script arm_tmux_handoff_watcher.py --args "--formal-session-name formal-session --target XXX"` | Watcher 挂载 |
| `tmux_handoff_app_bridge.py` | 通过 delivery 路径按需确保，或 `python3 run_script.py --script tmux_handoff_app_bridge.py --args "..."` | Window IPC bridge 常驻进程 |

### 2.2 辅助/历史/测试入口

| 入口 | 状态 | 说明 |
|------|------|------|
| `agents/tmux-runtime-bot.md` | 🔴 已弃用 | 文档明确说明"不再承担旧的四阶段 runtime / handoff / verify 编排职责" |
| `tbot` bootstrap session | 🟡 临时入口 | 可作为快速引导，但必须在 formal-session 就绪后关闭 |
| 各独立脚本直调 | 🟡 历史兼容口径 | 当前仅少数未受 enforcement 保护的脚本仍保留路径直调；公开能力应优先经 `run_script.py` 或 delivery 路径进入 |

---

## 3. 角色与职责映射

### 3.1 Hidden PTY vs Visible Terminal

| 角色 | 当前职责 | 边界 |
|------|----------|------|
| **Hidden PTY** (Codex hidden context) | 调用 `start_formal_runtime_chain.py` 发起 fresh start | ❌ **不能**直接承担 formal runtime 的正式启动职责 |
| **Visible Terminal** (Ghostty/iTerm2/Terminal.app) | 实际被 attach 的 tmux client，`session_attached > 0` 的必要条件 | ✅ **必须**是 formal runtime 的启动和运行载体 |

**当前问题**：
- `start_formal_runtime_chain.py` 明确要求 `require_visible_terminal_launcher()` —— 必须在真实可见终端启动
- 但调用链可能从 hidden PTY 发起，导致"启动脚本在 hidden 上下文，实际 tmux client 在可见终端"的分裂状态

### 3.2 Formal Runtime、Watcher、Delivery Runner

| 组件 | 职责 | 运行方式 |
|------|------|----------|
| **Formal Runtime** (`formal-session`) | 前台 attached 的 tmux session，承载所有工作 pane | 必须有且仅有一个 visible client attached |
| **Watcher** (`watch_tmux_handoff.py`) | 轮询 pane 状态，完成整轮扫描后按固定规则决定是否释放 `pane_stopped` / `pane_unreachable` 事件 | 后台进程，PID 记录于 ledger |
| **Delivery Runner** (`deliver_tmux_handoff_notification.py`) | 确保 bridge 常驻；如果输入事件尚未落到 queue，会先写入 queue | 后台进程 |
| **Window IPC Bridge** (`tmux_handoff_app_bridge.py`) | 通过 Codex window IPC 投递到 owner window | 常驻进程，PID 记录于 `.pid` 文件 |

### 3.3 Metadata / Snapshot / Lock / PID 文件

| 文件 | 路径 | 用途 |
|------|------|------|
| `current-runtime.json` | `/workspace/artifacts/tmux-runtime/` | **Runtime Ledger**：pane_count、slot_bindings、watcher 状态、codex_thread_bound |
| `last-runtime-issues.json` | 同上 | 历史问题记录 |
| `handoff-notifications.jsonl` | `/workspace/artifacts/tmux-skills/` | Watcher 输出日志 |
| `handoff-notifications.sqlite3` | 同上 | SQLite 持久化 |
| `window-ipc-delivery-receipts.jsonl` | 同上 | Delivery receipts |
| `tmux-handoff-window-ipc-bridge.pid` | 同上 | Bridge PID |
| `delivery-queue/*.json` | 同上 | 待投递事件队列 |

---

## 4. 当前运行链路图

### 4.1 Fresh Start 主链 (当前实际流程)

```
┌─────────────────────────────────────────────────────────────────────────┐
│  start_formal_runtime_chain.py (唯一对外主链入口)                        │
│  输入：--codex-thread-id, --pane-title[], --formal-session              │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  Phase 0: Preflight & Cleanup                                           │
│  ├── require_visible_terminal_launcher()  ← 必须在可见终端启动           │
│  ├── preflight_kill_all_tmux_sessions()  ← 杀掉所有旧 tmux              │
│  ├── verify_tmux_cleared()  ← 确认 tmux 已清空                          │
│  └── cleanup_previous_runtime_state()  ← 清理 ledger/issues/logs/queue │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  Phase 1: Launch Clean Formal Session                                   │
│  ├── tmux new-session -s formal-session (detached)                      │
│  └── 通过 --continue-inside-formal 继续内部流程                          │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  Phase 2: Env Setup (init_tmux_env.py)                                  │
│  ├── 创建 detached formal session                                       │
│  ├── 设置窗口标题                                                       │
│  └── 设置 primary pane 标题                                             │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  Phase 3: Topology (build_tmux_topology.py)                             │
│  ├── 按 target-pane-count 分裂/收缩 pane                                │
│  ├── 应用 tiled layout (2x2 / 3x2 / grid)                               │
│  └── 输出 pane_targets[]                                                │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  Phase 4: Pane Titles (init_tmux_panes.py)                              │
│  ├── 批量应用 pane titles                                               │
│  ├── 更新 slot_bindings                                                 │
│  └── 输出 topology_fingerprint                                          │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  Phase 4.5: Surface Normalization                                       │
│  ├── 收敛 pane 初始表面                                                 │
│  └── 避免 watcher 挂载后再被 respawn 覆盖                               │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  Phase 5: Runtime Activation & Verify                                   │
│  ├── bind_tmux_thread_id()  ← 设置 CODEX_THREAD_ID                     │
│  ├── init_runtime_ledger()  ← 写 ledger                                │
│  ├── arm_tmux_handoff_watcher()  ← 启动 watcher                        │
│  └── check_tmux_ready.py --require-formal --require-watcher  ← 验收    │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
                          ┌─────────────────┐
                          │  READY / BLOCKED │
                          └─────────────────┘
```

### 4.2 运行态链路

```
┌─────────────────────┐     ┌─────────────────────┐     ┌─────────────────────┐
│  formal-session     │     │  watch_tmux_handoff │     │  delivery-queue/    │
│  (前台 attached)    │────▶│  (整轮扫描 pane 状态) │────▶│  (待发送事件)       │
└─────────────────────┘     └─────────────────────┘     └─────────────────────┘
                                                             │
                                                             ▼
                                                   ┌─────────────────────┐
                                                   │  deliver_tmux_      │
                                                   │  handoff_notification│
                                                   │  (确保 bridge 常驻) │
                                                   └─────────────────────┘
                                                             │
                                                             ▼
                                                   ┌─────────────────────┐
                                                   │  tmux_handoff_app_  │
                                                   │  bridge.py          │
                                                   │  (常驻 Window IPC)  │
                                                   └─────────────────────┘
                                                             │
                                                             ▼
                                                   ┌─────────────────────┐
                                                   │  Codex Owner Window │
                                                   │  (thread-follower-  │
                                                   │   start-turn)       │
                                                   └─────────────────────┘
```

---

## 5. 当前状态文件/残留物清单

### 5.1 运行时状态文件

| 文件 | 路径 | 清理时机 | 未清理风险 |
|------|------|----------|------------|
| `current-runtime.json` | `workspace/artifacts/tmux-runtime/` | fresh start 时 | 旧 slot bindings 污染新拓扑 |
| `last-runtime-issues.json` | 同上 | fresh start 时 | 历史问题干扰新诊断 |
| `handoff-notifications.jsonl` | `workspace/artifacts/tmux-skills/` | fresh start 时 | 日志膨胀，但不影响功能 |
| `handoff-notifications.sqlite3` | 同上 | fresh start 时 | 同上 |
| `watch-tmux-handoff.stdout.log` | 同上 | fresh start 时 | 同上 |
| `deliver-tmux-handoff.stdout.log` | 同上 | fresh start 时 | 同上 |
| `delivery-queue/*.json` | 同上 | fresh start 时 | 旧事件可能重复投递 |
| `tmux-handoff-window-ipc-bridge.pid` | 同上 | fresh start 时 | 可能导致 bridge 重复启动 |
| `window-ipc-delivery-receipts.jsonl` | 同上 | fresh start 时 | 不影响功能 |

### 5.2 后台进程残留

| 进程 | 识别方式 | 清理方式 |
|------|----------|----------|
| Watcher (`watch_tmux_handoff.py`) | `ps ax -o pid=,command=` 中含脚本名 | `stop_conflicting_watchers()` |
| Bridge (`tmux_handoff_app_bridge.py`) | PID 文件 + `ps` 检查 | 当前不在 cleanup 中显式 kill，主要依赖 `ensure_bridge_running()` / `acquire_lock()` 保持单实例 |

---

## 6. 现有问题清单

### 6.1 多入口问题

| 问题 | 风险等级 | 说明 |
|------|----------|------|
| **隐藏的多入口** | 🔴 高 | `start_formal_runtime_chain.py` 是唯一对外入口，但内部支持 `--continue-inside-formal` 续期模式，可能被绕过 |
| **Bootstrap 入口** | 🟡 中 | `tbot` 可作为快速引导，但文档建议"在 formal-session 就绪后关闭"，实际可能长期并存 |
| **独立脚本直调** | 🟡 中 | 仍有少量脚本保留路径直调或兼容参数；若绕过 scheduler / delivery 入口，可能跳过 cleanup/preflight 阶段 |

### 6.2 多状态问题

| 问题 | 风险等级 | 说明 |
|------|----------|------|
| **Ledger 状态漂移** | 🔴 高 | `current-runtime.json` 可能与实际 tmux 状态不一致（如 watcher 进程已退出但 ledger 仍标记为 armed） |
| **Attached 状态判断** | 🔴 高 | 依赖 `session_attached > 0`，但可能存在 `attached=2` 污染（如文档提到的 tbot 重复执行问题） |
| **CODEX_THREAD_ID 绑定** | 🟡 中 | 可能 tmux env 中绑定了，但 ledger 中 `codex_thread_bound` 未同步 |

### 6.3 多残留问题

| 问题 | 风险等级 | 说明 |
|------|----------|------|
| **旧 session 残留** | 🔴 高 | 虽然 `preflight_kill_all_tmux_sessions()` 会杀掉所有旧 session，但如果当前调用者本身在 tmux 内，会跳过清理 |
| **旧 watcher 残留** | 🟡 中 | `stop_conflicting_watchers()` 只停 target 重叠的 watcher，可能有无关 watcher 继续运行 |
| **旧 queue 残留** | 🟡 中 | `clear_directory(DELIVERY_QUEUE_DIR)` 会清空队列，但未投递事件可能丢失 |

### 6.4 多上下文混用问题

| 问题 | 风险等级 | 说明 |
|------|----------|------|
| **Hidden PTY vs Visible Terminal** | 🔴 高 | 调用脚本可能从 hidden PTY 发起，但 tmux client 必须在 visible terminal —— 导致"启动上下文"与"运行上下文"分裂 |
| **Formal Session vs Bootstrap Session** | 🟡 中 | `tbot` 与 `formal-session` 可能并存，文档建议"tbot 就绪后关闭"，但实际可能长期占用资源 |

### 6.5 职责混杂问题

| 脚本 | 混杂职责 | 风险 |
|------|----------|------|
| `start_formal_runtime_chain.py` | 编排 + cleanup + launch + env + topology + titles + surface normalization + ledger + watcher + verify | 单脚本 1168 行，职责过多，难以单独测试或替换某阶段 |
| `tmux_runtime_common.py` | session 枚举 + client 枚举 + pane 枚举 + 可见性判断 + 进程检查 + ledger 读取 | 684 行工具库，耦合度过高 |
| `arm_tmux_handoff_watcher.py` | watcher 启动 + 旧 watcher 清理 + ledger 更新 | 职责可拆分 |

---

## 7. 风险分级

| 风险项 | 等级 | 可能后果 | 缓解措施 |
|--------|------|----------|----------|
| **Hidden PTY 启动** | 🔴 高 | "tmux 起起来了"但 actual visible client 不存在，导致假 ready | `require_visible_terminal_launcher()` 已实现，但需确保调用路径遵守 |
| **Attached=2 污染** | 🔴 高 | 旧 session 未完全清理，新 session 已创建，导致双 session 并存 | `preflight_kill_all_tmux_sessions()` 已实现，但需确保调用 |
| **Ledger 漂移** | 🔴 高 | ledger 记录与 tmux 实际状态不一致，导致误判 ready | `check_tmux_ready.py` 可做审计，但非强制门禁 |
| **旧 watcher 残留** | 🟡 中 | 多个 watcher 同时上报同一 pane，导致重复投递 | `stop_conflicting_watchers()` 已实现 |
| **Queue 残留** | 🟡 中 | 旧事件可能被重复投递 | `clear_directory()` 已实现 |
| **Bootstrap 污染** | 🟡 中 | `tbot` 与 `formal-session` 并存，资源占用 + 状态混淆 | 文档建议"tbot 就绪后关闭"，但无强制机制 |

---

## 8. 需要保留、收口、废弃的入口建议

### 8.1 保留（正式入口）

| 入口 | 保留理由 |
|------|----------|
| `start_formal_runtime_chain.py` | 唯一对外主链入口，已实现完整的 cleanup -> launch -> verify 流程 |
| `run_script.py` | 当前公开调度入口，负责注册校验与 scheduler marker 注入 |
| `check_tmux_ready.py` | 当前更准确属于公开调度子入口，可用于运行态审计 |
| `arm_tmux_handoff_watcher.py` | 当前更准确属于公开调度子入口，支持独立 re-arm |
| `tmux_handoff_app_bridge.py` | 当前更准确属于 delivery / scheduler 管理下的 bridge 常驻进程 |

### 8.2 收口（限制调用场景）

| 入口 | 收口建议 |
|------|----------|
| `build_tmux_topology.py` | 只能由 orchestrator 调用，不得独立直调 |
| `init_tmux_panes.py` | 只能由 orchestrator 调用，不得独立直调 |
| `init_tmux_env.py` | 只能由 orchestrator 调用，不得独立直调 |
| `init_runtime_ledger.py` | 只能由 orchestrator 调用，不得独立直调 |

### 8.3 废弃（建议移除或降级）

| 入口 | 废弃理由 | 替代方案 |
|------|----------|----------|
| `agents/tmux-runtime-bot.md` | 文档已明确"已弃用" | 直接使用 `start_formal_runtime_chain.py` |
| `tbot` bootstrap | 可能导致双 session 污染 | 直接使用 `formal-session` fresh start |
| `build_tmux_db_write_instruction.py` | 旧 delivery 链路，已切换到 window IPC | `tmux_handoff_app_bridge.py` |
| `load_local_identity.py` | 旧身份加载机制 | 不再需要 |

---

## 9. 阶段 0 结论

### 9.1 当前正式 Runtime 如何被启动

**答案**：
1. 调用者从**可见终端**（非 hidden PTY）执行：
   ```bash
   python3 start_formal_runtime_chain.py \
     --codex-thread-id "$CODEX_THREAD_ID" \
     --pane-title task-1 \
     --pane-title task-2 \
     --pane-title notes \
     --pane-title monitor \
     --pretty
   ```
2. 脚本执行 `preflight_kill_all_tmux_sessions()` 清理所有旧 session
3. 脚本执行 `verify_tmux_cleared()` 确认 tmux 已清空
4. 脚本执行 `cleanup_previous_runtime_state()` 清理 ledger/issues/logs/queue
5. 脚本通过 `tmux new-session -d -s formal-session` 创建 detached session
6. 脚本通过 `--continue-inside-formal` 继续内部流程
7. 依次执行 env -> topology -> pane titles -> surface normalization -> ledger -> watcher -> ready_check
8. `check_tmux_ready.py` 返回 READY 后，视为启动完成

### 9.2 哪些入口是正式入口，哪些只是辅助/历史/测试入口

**正式入口**：
- `start_formal_runtime_chain.py`（唯一对外主链）
- `run_script.py`（公开调度入口）

**正式子入口 / 运行子入口**：
- `check_tmux_ready.py`（经 scheduler 调用的验收/审计）
- `arm_tmux_handoff_watcher.py`（经 scheduler 调用的 watcher 挂载）
- `tmux_handoff_app_bridge.py`（由 delivery 路径确保或经 scheduler 调用的 bridge 常驻）

**辅助/历史/测试入口**：
- `agents/tmux-runtime-bot.md`（已弃用文档）
- `tbot`（bootstrap 快速引导，建议废弃）
- 各独立脚本直调（历史兼容口径，建议继续收口）

### 9.3 当前"Fresh Start"为什么不可靠

**不可靠因素**：
1. **调用上下文可能不满足要求**：`require_visible_terminal_launcher()` 要求从可见终端启动，但实际调用可能从 hidden PTY 发起
2. **Attached=2 污染风险**：如果旧 session 未完全清理，新 session 已创建，可能导致 `attached=2`（文档提到的 tbot 重复执行问题）
3. **Ledger 漂移**：ledger 记录可能与 tmux 实际状态不一致
4. **后台进程残留**：旧 watcher/bridge 可能继续运行，导致重复上报

### 9.4 旧状态残留会污染哪些阶段

| 残留类型 | 污染阶段 | 污染后果 |
|----------|----------|----------|
| 旧 session | Preflight | 可能导致 `attached=2` 污染，或跳过清理 |
| 旧 ledger | Ledger 初始化 | 旧 slot bindings 可能干扰新拓扑 |
| 旧 watcher | Watcher 挂载 | 多个 watcher 同时上报同一 pane |
| 旧 queue | Delivery | 旧事件可能被重复投递 |
| 旧 CODEX_THREAD_ID | Runtime Activation | 可能投递到错误线程 |

### 9.5 结构化问题清单

| 问题分类 | 问题描述 | 影响范围 | 优先级 |
|----------|----------|----------|--------|
| **入口收敛** | 存在多个可独立调用的脚本，可能跳过 cleanup/preflight | 全链路 | P0 |
| **上下文约束** | Hidden PTY 调用可能导致"启动上下文"与"运行上下文"分裂 | 启动阶段 | P0 |
| **状态一致性** | Ledger 记录可能与 tmux 实际状态不一致 | 运行态 | P0 |
| **残留清理** | 旧 session/watcher/queue 可能残留 | 启动/运行态 | P1 |
| **职责耦合** | `start_formal_runtime_chain.py` 职责过多，难以单独测试 | 维护性 | P2 |
| **Bootstrap 污染** | `tbot` 与 `formal-session` 可能并存 | 启动阶段 | P2 |

---

## 10. 阶段 0 验收确认

- [x] 能清楚说明当前正式 runtime 是如何被启动的
- [x] 能清楚说明哪些入口是正式入口，哪些只是辅助/历史/测试入口
- [x] 能清楚说明当前"fresh start"为什么不可靠
- [x] 能清楚说明旧状态残留会污染哪些阶段
- [x] 能给出一份足够指导后续重构的结构化问题清单

---

## 11. 下一步建议

建议进入**阶段 1：主链方案设计**，设计一条固定的主链：

```
detect_old_state -> cleanup -> init -> launch -> verify
```

并明确每一阶段的输入、输出、成功条件、失败条件、状态文件。
