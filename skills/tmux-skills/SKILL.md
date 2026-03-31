---
name: tmux-skills
description: |
  Workbot 的 tmux pane 生成与监控技能。
  Codex 提供 pane 数量和 pane 标题，tmux-skills 负责在前台 tmux 中生成这些 pane，并在 pane 停止时通过 Codex 本地 window IPC 向专用 monitor thread 的 `CODEX_THREAD_ID` 对应当前窗口 thread 报告。
---

# tmux-skills

## 目的

这个 skill 只负责两件事：

1. 根据 Codex 提供的 `pane_count` / `pane_titles` 在前台 tmux 中生成 pane
2. 在 pane 停止、失联或不可达时，把事件投递到 monitor thread 的 `CODEX_THREAD_ID`

## 冻结口径

- `tmux-skills` 只管 tmux 运行面，不负责 Claude/agent/scene/prompt
- pane 数量和 pane 标题必须由调用方显式传入，skill 不自行决定
- 正式运行面只承认一个前台 attached 的 `formal-session`
- detached tmux session 不算正式运行面
- `CODEX_THREAD_ID` 是唯一门铃投递目标真源；未设置时必须 fail fast
- pane 标题只是当天 attached runtime 的临时标签，不是项目级身份定义
- 每次新建 pane 前必须先清理上一轮 watcher、ledger、issues、handoff 日志
- 禁止用伪造前台的方式启动 tmux；hidden PTY 必须转到真实可见终端

## 先看哪个入口

- 判断这次启动会不会转 `Terminal.app`：
  `/Users/busiji/workbot/skills/tmux-skills/scripts/start_formal_runtime_chain.py --explain-launch-path`
- 正式启动 / 接管 `formal-session`：
  `/Users/busiji/workbot/skills/tmux-skills/scripts/start_formal_runtime_chain.py`
- 看当前运行面是否 READY：
  `/Users/busiji/workbot/skills/tmux-skills/scripts/check_tmux_ready.py --summary`
- 需要完整审计结果时：
  `/Users/busiji/workbot/skills/tmux-skills/scripts/check_tmux_ready.py`
- 只处理布局：
  `/Users/busiji/workbot/skills/tmux-skills/scripts/build_tmux_topology.py`
- 只挂 watcher：
  `/Users/busiji/workbot/skills/tmux-skills/scripts/arm_tmux_handoff_watcher.py`
- window IPC bridge：
  `/Users/busiji/workbot/skills/tmux-skills/scripts/tmux_handoff_app_bridge.py`

## 默认工作流

1. 先跑 `start_formal_runtime_chain.py --explain-launch-path`
2. 再跑 `check_tmux_ready.py --summary`
3. 只有摘要不足时，再局部阅读源码
4. 不要默认整段读取 `start_formal_runtime_chain.py`、`check_tmux_ready.py` 或长篇决策记录

## 最小调用示例

```bash
python3 /Users/busiji/workbot/skills/tmux-skills/scripts/start_formal_runtime_chain.py \
  --codex-thread-id "$CODEX_THREAD_ID" \
  --formal-session formal-session \
  --pane-title task-1 \
  --pane-title task-2 \
  --pane-title notes \
  --pane-title monitor \
  --pretty
```

## 结果口径

- 启动主链负责：预清理、formal-session 接管或创建、pane 布局、标题设置、ledger、watcher、ready check
- watcher 只负责“看”和落队列
- delivery runner 只负责“送”的编排，真正投递由 window IPC bridge 完成
- 报告内容至少包含：
  `target`、`pane_title`、`state_class`

## 一句话职责

**根据 Codex 提供的数量和标题，在前台 tmux 中生成 pane，并在 pane 停止后通过 window IPC bridge 向 `CODEX_THREAD_ID` 对应的 monitor 当前窗口 thread 报告。**
