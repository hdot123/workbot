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

- `tmux-skills` 负责 tmux 运行面；允许在 pane 里直接启动 `claude`
- `tmux-skills` 的官方 Python 运行时只认项目 `/Users/busiji/workbot/.venv/bin/python`
- 若 pane 标题命中项目 `.claude/agents/<name>.md`，先在对应 pane 内启动纯 `claude`，再把该身份文件内容粘贴注入到 Claude 窗口
- 不允许把不存在于项目 `.claude/agents/` 的名字映射成项目身份注入
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
2. 再跑 `start_formal_runtime_chain.py`
3. 需要 watcher 时，再显式跑 `arm_tmux_handoff_watcher.py`
4. 需要审计当前运行面时，再跑 `check_tmux_ready.py --summary`
5. 只有摘要不足时，再局部阅读源码

## 最小调用示例

```bash
/Users/busiji/workbot/.venv/bin/python /Users/busiji/workbot/skills/tmux-skills/scripts/start_formal_runtime_chain.py \
  --codex-thread-id "$CODEX_THREAD_ID" \
  --formal-session formal-session \
  --pane-title task-1 \
  --pane-title task-2 \
  --pane-title notes \
  --pane-title monitor \
  --pretty
```

## 结果口径

- 启动主链负责：预清理、formal-session 接管或创建、pane 布局、标题设置、项目 agent 白名单匹配后的纯 `claude` 启动、身份文件粘贴注入、ledger
- watcher 不属于默认启动链；只有显式执行 `arm_tmux_handoff_watcher.py` 后才开始扫描和放第一条消息
- watcher 只负责“看”和落队列
- delivery runner 只负责“送”的编排，真正投递由 window IPC bridge 完成
- 报告内容至少包含：
  `target`、`pane_title`、`state_class`

## 一句话职责

**根据 Codex 提供的数量和标题，在前台 tmux 中生成 pane，并在 pane 停止后通过 window IPC bridge 向 `CODEX_THREAD_ID` 对应的 monitor 当前窗口 thread 报告。**
