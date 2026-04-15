---
name: tmux-runtime
description: |
  已退役。workbot 仅允许 cmux 运行时，禁止继续使用 tmux-runtime。
---

# tmux-runtime（Retired）

`tmux` 在 `workbot` 已正式退役。  
从现在开始只允许 `cmux` 运行时。

## 替代入口

请使用：

`/Users/busiji/.agents/skills/cmux/scripts/bootstrap_claude_runtime.py`

## 当前策略

- 保留 `tmux-runtime` 目录仅用于历史追溯。
- 任何 `tmux` 启动入口默认应阻断执行。
- 需要应急回放时，必须显式使用 legacy 开关并由人工确认。
