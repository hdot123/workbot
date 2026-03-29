# tmux-skills 开发进度

更新时间：2026-03-29（Asia/Shanghai）

## 当前判断

`tmux-skills` 已从“身份注入”阶段彻底切换到 runtime-only formal session。当前正式链路固定为 `env -> topology -> ledger -> watcher -> verify`，只有链路全部通过、4 个 target 处于已知 Claude 现场、watcher 把门铃事件交给固定记忆模板后才能宣告 `READY`。

## 文档与入口收口

本轮新增完成：

- 外部 `scripts/tmux-look.sh`、`tmux-fmd` 等旧入口已退役
- 完整链路与 watcher 事件统一写语义化文档，`pane_id` 仅保留内部使用
- `formal-session` 当前被定义为 4 个白名单 target（`2 dev-bot + 1 qa-bot + 1 doc-bot`），`worker_ceiling=3`
- `tmux-skills` 文档、设计、进度三角形已根据 runtime-only contract 收敛
- legacy FMD 模拟器仅供测试用，门铃模板已对齐 `<pane_title> 呼叫：去 tmux <target> 窗口<状态名> SOP 状态`

当前唯一允许保留的 tmux active 文档为：

- `/Users/busiji/workbot/skills/tmux-skills/SKILL.md`
- `/Users/busiji/workbot/docs/tmux-skills-design.md`
- `/Users/busiji/workbot/docs/tmux-skills-duty-boundary.md`
- `/Users/busiji/workbot/docs/tmux-skills-progress.md`

## 四阶段进度总览

### 阶段 1：创建 tmux 环境

状态：正式 env executor 已接入 4-pane `formal-session`、`CODEX_THREAD_ID` 由启动器注入，链路第一步跑通。

已完成：

- `init_tmux_env.py` 能初始化或接管 single formal session 并设置 `destroy-unattached=on`
- `start_formal_runtime_chain.py` 在 env 阶段后即检查 formal session 是否已 attached
- `start-day.sh` 明确把 “human must prepare existing Claude scenes” 定义为前置条件

未完成：

- 让 env 检查在 4-pane ready 之前不会继续链下步
- 更强的 watcher 状态记录以防止重复 attach/dual session

### 阶段 2：数量触发数量

状态：topology executor 支持 4-pane target generation，不再硬绑 3 pane ceiling。

已完成：

- `build_tmux_topology.py` 生成 4 个 target 列表并确保 final `pane_count == 4`
- topology 输出包含 target 列表，可直接 feed 给 watcher / ledger
- 约定 `pane_count` 与 `worker_ceiling` 分离：后者仍是 3，前者就是 4

未完成：

- 自动从 topology 直接触发 ledger slot binding（当前需要手动 chain）
- 文档中列出的 `slot_bindings` plan 需继续和 watcher targets 明确同步

### 阶段 3：pane 级验证

状态：`init_tmux_panes.py` 不是注入器，而是贴标签 + 验证既有 scene。

已完成：

- `init_tmux_panes.py` 验证每个 target 的 `pane_title` 和 `node/claude` 运行态，并写 slot binding
- `verify_pane_identity.py` 只验证 whitelist 标题 + Claude 运行 + 可见角色 marker，不再依赖 `identity_injected`
- slot binding 更新进入 ledger 后，watcher 和 ready-check 能通过 `slot_bindings.monitor.target` 确定 monitor pane

未完成：

- 自动处理一旦 scene 失效就回退 `BLOCKED` 并提示 human 重置
- 更完善的 `slot_bindings` 可视化以便快速对齐 `target` vs `role`

### 阶段 4：全局收口验证

状态：`check_tmux_ready.py`/`verify_tmux_runtime.py` 只看 runtime facts，并依赖 watcher targets。

已完成：

- READY gate 检查唯一 attached formal session、`pane_count=4`、全部 target 在 Claude 状态、watcher armed、ledger topology 一致
- watcher 事件只输出 `target`/`pane_title`/`state_class`，`runtime_blocked` 事件不发 Codex
- 门铃模板固定 `state_class -> state_label` 映射，`pane_id` 仅出现在内部记录

未完成：

- 自动触发 verify 失败时的 recovery narrative 和 doorbell fallback
- 4-pane happy path 目前还是手动 trigger watchers，需要进一步脚本化

## 当前已完成的基础设施

### 1. Runtime ledger

- `/Users/busiji/workbot/skills/tmux-skills/scripts/runtime_ledger.py`
- `/Users/busiji/workbot/skills/tmux-skills/scripts/init_runtime_ledger.py`
- `/Users/busiji/workbot/skills/tmux-skills/scripts/tmux_runtime_ledger.py`

### 2. Topology / ready check / watcher

- `/Users/busiji/workbot/skills/tmux-skills/scripts/build_tmux_topology.py`
- `/Users/busiji/workbot/skills/tmux-skills/scripts/check_tmux_ready.py`
- `/Users/busiji/workbot/skills/tmux-skills/scripts/watch_tmux_handoff.py`
- `/Users/busiji/workbot/skills/tmux-skills/scripts/arm_tmux_handoff_watcher.py`

### 3. Notification pipeline

- `/Users/busiji/workbot/skills/tmux-skills/scripts/build_tmux_handoff_notification.py`
- `/Users/busiji/workbot/skills/tmux-skills/scripts/build_tmux_handoff_bundle.py`
- `/Users/busiji/workbot/skills/tmux-skills/scripts/deliver_tmux_handoff_notification.py`
- `/Users/busiji/workbot/skills/tmux-skills/scripts/write_tmux_notifications_sqlite.py`

### 4. Legacy fallbacks (testing only)

- `/Users/busiji/workbot/skills/tmux-skills/scripts/legacy_tmux_fmd_compat.py`

## 当前未完成的关键缺口

1. 把 `start_formal_runtime_chain.py` 直接和 `watcher`/`verify` 编排成一条一键链，在 Env 失败时就不进入下一步
2. 用 `tmux-skills/scripts/verify_tmux_runtime.py` 记录每次 `runtime_blocked` 事件并触发人类通知
3. 让 watcher 的 proactive bundling 强化 4-pane target contract（target list + deliverable flag）
4. 更新所有运维文档（design/SKILL/progress）与新链保持一致

## 当前阶段结论

当前阶段的真实输出是：

- 基础底座已经由 environment/topology/ledger 覆盖
- pane validation 只负责既有 Claude scene，不再注入身份
- watcher + doorbell pipelines 只交 target + state_class

**下一步是把链路文档、验证，以及 4-pane happy path 回归全覆盖。**
