---
name: tmux-skills
description: |
  Workbot 的统一 tmux runtime skill 集合。正式职责只包括 runtime / watcher / bell / verify。
  它不再负责 claude 启动、角色进入或 system prompt 注入。
---

# tmux-skills

## 目的

这个 skill 只做一件事：

**把 workbot 的 tmux 运行面、门铃和验收统一收口到同一个 runtime-only 域。**

正式链路固定为：

1. `env`
2. `topology`
3. `ledger`
4. `watcher`
5. `verify`

只有走完整条链并通过 `verify_tmux_runtime.py`，formal runtime 才算 `READY`。

## 冻结口径

- 正式 session 只承认一个 attached 的 `formal-session`
- 正式 pane 数固定为 `6`
- 正式白名单标题固定为 `dev-bot / qa-bot / doc-bot`
- `worker_ceiling = 3` 只是并发推进上限，不是 pane 数
- 对外交付只展示 `target = formal-session:window.pane`
- `pane_id` 只保留为内部 tmux 细节
- watcher / bell / delivery 统一走 `target`
- `runtime_blocked` 事件只进入恢复分支，不投递窗口 SOP 门铃

## 不再负责

`tmux-skills` 不再承担以下动作：

- `claude --agent`
- 角色切换
- system prompt 注入
- identity payload 注入
- 业务任务下发

这些动作都属于人类与 Codex 的职责。

## 文档真源

tmux 规则文档只允许保留：

- `/Users/busiji/workbot/skills/tmux-skills/SKILL.md`
- `/Users/busiji/workbot/docs/tmux-skills-design.md`
- `/Users/busiji/workbot/docs/tmux-skills-duty-boundary.md`
- `/Users/busiji/workbot/docs/tmux-skills-progress.md`

## 正式输出合同

门铃 payload 的正式字段为：

- `target`
- `pane_title`
- `state_class`
- `state_label`
- `session`
- `window`
- `current_command`
- `reachable`
- `deliverable`

固定门铃模板为：

```text
<pane标题> 呼叫：去 tmux <target> 窗口<状态名> SOP 状态
```

固定状态映射为：

- `sop_approval -> 审批`
- `pane_checkin -> 巡检`
- `runtime_blocked -> 恢复`

## 使用方式

### 1. 读取现场

```bash
python3 /Users/busiji/workbot/skills/tmux-skills/scripts/inspect_tmux_runtime.py --pretty
```

### 2. 做 ready-check

```bash
python3 /Users/busiji/workbot/skills/tmux-skills/scripts/check_tmux_ready.py \
  --pretty \
  --expected-pane-count 4 \
  --require-formal \
  --require-bell
```

### 3. 挂 watcher

```bash
python3 /Users/busiji/workbot/skills/tmux-skills/scripts/arm_tmux_handoff_watcher.py \
  --formal-session-name formal-session \
  --target formal-session:1.1 --target formal-session:1.2 --target formal-session:1.3 \
  --target formal-session:1.4 \
  --deliver
```

### 4. 构造单个 target 通知

```bash
python3 /Users/busiji/workbot/skills/tmux-skills/scripts/build_tmux_handoff_notification.py \
  --target formal-session:1.3
```

### 5. 观察 target

```bash
python3 /Users/busiji/workbot/skills/tmux-skills/scripts/watch_tmux_handoff.py \
  --target formal-session:1.3 --deliver
```

### 6. 构造 bundle 与投递

```bash
python3 /Users/busiji/workbot/skills/tmux-skills/scripts/build_tmux_handoff_bundle.py \
  --event-file /tmp/notification.json

python3 /Users/busiji/workbot/skills/tmux-skills/scripts/deliver_tmux_handoff_notification.py \
  --bundle-file /tmp/notification.json \
  --session-mode fixed
```

### 7. 写入 SQLite

```bash
python3 /Users/busiji/workbot/skills/tmux-skills/scripts/write_tmux_notifications_sqlite.py \
  --input-file /tmp/notification.jsonl
```

## 一句话职责

你的职责是：

**维护 workbot 的 tmux formal runtime，并把所有对外出口压缩成 target-based 的 runtime / bell 信号。**
