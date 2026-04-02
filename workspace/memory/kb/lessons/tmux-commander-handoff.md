---
type: [KB:LESSON]
title: "Lesson: tmux Commander Handoff"
created: 2026-04-01
updated: 2026-04-02
last_verified: 2026-04-02
status: active
tags: [tmux, handoff, sop, commander]
confidence: high
source: Manual
version: v1.0
related: [workbot]
---

# Lesson: tmux Commander Handoff

keywords: tmux handoff 执行提醒 检查SOP状态 去pane窗口继续执行 去tmux窗口继续执行 approval_prompt approval_stuck accept_edits accept edits on Claude界面提示 非审批信号 lookme

## 核心口径

- 通知 = 谁停了
- 执行 = 我去那个窗口处理
- pane 消息 = 强执行信号，必须去对应窗口处理

## 当前通知模板

- 示例：`去formal-session:1.1检查 SOP 状态`
- 通用模板：`去{target}检查 SOP 状态`
- 若命中执行提醒：`去{target}继续执行当前任务`

## SOP 执行动作

1. 进对应窗口
2. 按当前高亮规则操作一次
3. 立刻复查
4. 没消失就继续

## 当前规则

- 默认高亮在 `1`
- 选 `1` 直接 `Enter`
- 选 `2` 下移一次再 `Enter`
- 选 `3` 下移两次再 `Enter`
- 处理口径是“方向键切换 + Enter”，不是直接打 `1/2/3`
- Claude Code 的 `Bash command` 审批框按 SOP 处理
- `accept edits on ...` 是 Claude 的界面提示，不是审批 SOP，不应触发审批动作
- 当 `lookme` 抓最近 5 行、连续两轮 hash 相同且仍停在 `accept edits on ...` 附近时，应转换为“去 pane 窗口继续执行当前任务”的执行提醒，而不是审批提醒
- 一旦出现“去 pane 窗口继续执行当前任务”的执行提醒，处理口径不是等待下一次提醒，而是立刻切到对应 pane 继续处理
- 不要直接打数字键，也不要假设单独 `Enter` 一定会生效；先用方向键确认当前高亮，再 `Enter`

## 一句话规则

`去formal-session:1.1检查 SOP 状态` = 进窗口、按当前高亮规则操作一次、立刻复查；没消失就继续，直到确认框消失或明确失败。
