# tmux-skills 设计文档

## 1. 定位

`tmux-skills` 不是业务调度器，不是角色注入器，也不是人格生成器。

它的唯一定位是：

**作为 workbot 的 tmux runtime 基础设施层，负责搭 runtime、验 runtime、守 runtime，并把对外出口收口为固定门铃事件。**

一句话定义：

**`tmux-skills = env + topology + ledger + watcher + verify`**

## 2. 冻结边界

`tmux-skills` 只负责：

- 创建或接管唯一 attached 的 `formal-session`
- 构造正式 pane 拓扑
- 给 pane 贴白名单标题
- 记录 runtime facts 到 ledger
- 观察“可达但停止推进”的 pane
- 发送固定格式门铃
- 做 ready-check / verify

`tmux-skills` 不再负责：

- `claude --agent`
- 角色切换
- system prompt 注入
- 身份 payload 注入
- 业务任务分发
- “等待身份进入成功”的内部判定

## 3. 正式模型

### 3.1 Formal Session

正式 runtime 只承认一个 attached 的 `formal-session`。

正式 pane 数冻结为 `4`：

- `formal-session:1.1 dev-bot`
- `formal-session:1.2 dev-bot`
- `formal-session:1.3 qa-bot`
- `formal-session:1.4 doc-bot`

`3` 不再表示 pane 数，而是：

- `worker_ceiling = 3`

它只代表并发推进上限。

### 3.2 对外主地址

对外交付和门铃主展示统一使用：

- `target = formal-session:window.pane`
- `pane_title = dev-bot / qa-bot / doc-bot`

`pane_id` 只保留为内部 tmux 实现与兼容诊断细节，不再进入主展示、门铃模板和正式 CLI 主入口。

### 3.3 Formal Chain

正式链路冻结为：

`env -> topology -> ledger -> watcher -> verify`

其中 `init_tmux_panes.py` 只作为内部 helper，负责：

- pane 标题写入
- target 校验
- slot binding 写回
- 既有现场验证

它不再是正式链条中的独立“角色拉起阶段”。

## 4. Runtime Contract

### 4.1 Ready Gate

READY 只验证 runtime facts：

- 唯一 attached 的 `formal-session`
- `pane_count = 4`
- 所有 formal target 标题属于白名单
- 所有 formal target 已进入 Claude 运行态
- `CODEX_THREAD_ID` 已绑定
- watcher 已 armed
- ledger 与 topology 一致
- `slot_bindings.monitor.target` 存在且和 watcher 绑定一致

不再把以下内容作为 READY 前提：

- `identity_catalog_present`
- `identity_injected`
- `launch_agent`
- `planned_roles`
- `active_roles`
- `queued_roles`

### 4.2 Ledger

runtime ledger 冻结为 runtime-only facts 结构，至少包含：

- `formal_session_name`
- `pane_count`
- `topology_fingerprint`
- `slot_bindings`
- `watcher`
- `codex_thread_bound`
- `worker_ceiling`
- `runtime_status`

其中 `slot_bindings.monitor` 必须是带 target 的具体绑定：

```json
{
  "role": "qa-bot",
  "target": "formal-session:1.3"
}
```

不再接受只有 role 没有 target 的 monitor 绑定。

## 5. Watcher And Bell

### 5.1 事件字段

watcher 对外事件冻结字段为：

- `target`
- `pane_title`
- `state_class`
- `state_label`
- `session`
- `window`
- `current_command`
- `reachable`
- `deliverable`

可选内部字段允许保留：

- `pane_id`
- `recent_output`
- `prompt`

### 5.2 固定门铃模板

门铃文案冻结为：

```text
<pane标题> 呼叫：去 tmux <target> 窗口<状态名> SOP 状态
```

状态映射冻结为：

- `sop_approval -> 审批`
- `pane_checkin -> 巡检`
- `runtime_blocked -> 恢复`

### 5.3 触发规则

只有在以下条件同时满足时，watcher 才会发出可投递门铃：

- pane 活着
- target 可达
- pane 停止推进
- Codex 仍可进入继续处理

这时才属于窗口 SOP 事件。

如果出现以下情况：

- pane 已死
- session detached
- target 不可达

则只进入 `runtime_blocked` 恢复分支，不投递窗口 SOP 门铃。

## 6. 角色分工

### 6.1 人类负责

- 进入 `claude`
- 决定哪个 pane 放什么身份内容
- 让 pane 进入既有白名单 Claude 现场
- 注入或确认 system prompt

### 6.2 Codex 负责

- 接收固定门铃
- 命中固定记忆
- 进入目标 `formal-session:window.pane`
- 执行窗口 SOP
- 复查并汇报
- 投递业务任务内容

### 6.3 tmux-skills 负责

- 维护 runtime
- 维护 ledger
- 维护 watcher
- 输出门铃
- 执行 verify

## 7. 操作入口

读取现场：

```bash
python3 /Users/busiji/workbot/skills/tmux-skills/scripts/inspect_tmux_runtime.py --pretty
```

做 ready-check：

```bash
python3 /Users/busiji/workbot/skills/tmux-skills/scripts/check_tmux_ready.py \
  --pretty \
  --expected-pane-count 4 \
  --require-formal \
  --require-bell
```

挂 watcher：

```bash
python3 /Users/busiji/workbot/skills/tmux-skills/scripts/arm_tmux_handoff_watcher.py \
  --formal-session-name formal-session \
  --target formal-session:1.1 --target formal-session:1.2 --target formal-session:1.3 \
  --target formal-session:1.4
```

构造单 target 通知：

```bash
python3 /Users/busiji/workbot/skills/tmux-skills/scripts/build_tmux_handoff_notification.py \
  --target formal-session:1.3
```

持续观察 target：

```bash
python3 /Users/busiji/workbot/skills/tmux-skills/scripts/watch_tmux_handoff.py \
  --target formal-session:1.3 --deliver
```

## 8. 结论

`tmux-skills` 的正式完成标准不再是“已经成功注入角色”，而是：

- runtime facts 正确
- formal topology 正确
- watcher 正确
- verify 返回 `READY`

所有后续实现、测试和文档都必须围绕这套 runtime-only contract 演进。
