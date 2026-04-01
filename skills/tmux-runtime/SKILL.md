---
name: tmux-runtime
description: |
  Workbot 的统一 tmux runtime skill。
  按注册名单管理 tmux runtime 的正式入口、内部入口、watcher、验收和 window IPC delivery。
---

# tmux-runtime

## 用途

这个 skill 用于：

1. 创建或接管 `formal-session`
2. 按输入标题生成 pane
3. 绑定 `CODEX_THREAD_ID`
4. 挂载 watcher
5. 验收 runtime readiness
6. 把 watcher 事件送到目标 Codex app thread

## 使用时机

在这些场景使用这个 skill：

- 打开或重建 tmux pane
- 初始化 `formal-session`
- 给 pane 应用标题
- 挂 watcher
- 验收 runtime 是否 ready
- 排查 handoff delivery

## 注册分层

### stable / public

- `start_formal_runtime_chain.py`
- `check_tmux_ready.py`
- `arm_tmux_handoff_watcher.py`
- `tmux_handoff_app_bridge.py`

### stable / orchestrator_only

- `watch_tmux_handoff.py`
- `build_tmux_topology.py`
- `init_tmux_panes.py`
- `init_tmux_env.py`
- `init_runtime_ledger.py`

### stable / internal_only

- `runtime_ledger.py`
- `tmux_runtime_common.py`
- `build_tmux_handoff_bundle.py`

### testing / internal_only

- `tmux_runtime_ledger.py`

### deprecated / public

- `deliver_tmux_handoff_notification.py`
- `build_tmux_handoff_notification.py`
- `build_tmux_db_write_instruction.py`
- `write_tmux_notifications_sqlite.py`
- `tmux_notification_record.py`
- `load_local_identity.py`
- `verify_tmux_runtime.py`
- `verify_pane_identity.py`
- `inspect_tmux_runtime.py`

## 正式入口

正式创建或接管 pane，使用：

- `start_formal_runtime_chain.py`

当前主链输入：

- `--codex-thread-id`
- `--pane-title`（重复传入）
- `--formal-session`（默认 `formal-session`）

示例：

```bash
python3 start_formal_runtime_chain.py \
  --codex-thread-id "$CODEX_THREAD_ID" \
  --formal-session formal-session \
  --pane-title dev-bot \
  --pane-title dev-bot \
  --pane-title doc-bot \
  --pane-title doc-bot \
  --pretty
```

## 前置条件

- 必须从可见终端发起
- Hidden PTY 会被主链直接拒绝
- pane 数量和 pane 标题由调用方显式提供
- `CODEX_THREAD_ID` 是 handoff 目标 thread 的唯一真源

## 主链内部动作

当前主链内部执行：

- detect
- tmux preflight
- cleanup
- env
- topology
- titles
- ledger
- surface normalization
- watcher
- ready_check

调用方不需要在主链前重复做这些步骤。

## 公开验收和公开 watcher 入口

按当前注册名单，公开常用脚本是：

- `start_formal_runtime_chain.py`
- `check_tmux_ready.py`
- `arm_tmux_handoff_watcher.py`
- `tmux_handoff_app_bridge.py`

常用验收：

```bash
python3 run_script.py \
  --script check_tmux_ready.py \
  --args "--require-formal --require-watcher --pretty"
```

## 当前运行链

当前 watcher / delivery / bridge 运行链是：

- `watch_tmux_handoff.py`
- `deliver_tmux_handoff_notification.py`
- `tmux_handoff_app_bridge.py`

按当前代码：

- watcher 按轮扫描全部 targets
- watcher 抓 pane 内容并计算 hash
- watcher 按固定规则产出事件
- watcher 当前每轮最多向下游释放 `1` 条消息
- `deliver_tmux_handoff_notification.py` 确保 bridge 常驻
- `tmux_handoff_app_bridge.py` 顺序消费 queue，并通过 window IPC 投递到目标 thread

## 冲突处理

本文件只复述当前注册名单和当前实现。

如果本文件和当前注册名单或当前实现冲突，以当前注册名单和当前实现为准。

## 参考

只在需要看当前设计索引时再读：

- [/Users/busiji/workbot/docs/tmux-docs-index.md](/Users/busiji/workbot/docs/tmux-docs-index.md)
