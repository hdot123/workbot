---
name: tmux-goto
description: |
  当 tmux-goto 收到某个 tmux pane 的通知时，先切到对应 pane 并查看最近输出，再基于真实上下文决定下一步。适用于 dev/qa/commander 多 pane 协作场景。

  触发条件：
  - 收到某个 tmux pane 的通知，需要判断如何选择或继续执行
  - 用户要求“去看某个 tmux pane”“查看 dev/qa 当前状态”“收到通知就过去看”
  - tmux-goto 收到 pane id、标题、提示摘要后，需要补齐上下文再决策

  不触发条件：
  - 只是普通 shell 命令执行，不涉及 tmux pane 上下文
  - 已经拿到了充分上下文且无需再回 tmux pane 核查
---

# tmux-goto

## 目的

这个技能只做一件事：收到 pane 通知后，先去看现场，再决定。

tmux-goto 只负责把 pane 消息交给你并要求你先看现场，再决定；不要在 skill 内写死“遇到某种提示就自动选 1”之类的逻辑。

## 核心原则

1. 收到通知后，先去对应 pane 看现场，再决定。
2. 优先使用 `pane_id`，不要只靠标题猜测目标 pane。
3. 如果通知只有摘要，没有足够上下文，就继续抓 pane 输出，不要直接判断。
4. 只有在用户已经明确授权“由你决定并执行”时，才发送 `tmux send-keys`。
5. 做完动作后，必须复查 pane，确认任务是否真的继续推进。

## tmux-goto 的职责

tmux-goto 在这里对外只做三件事：

1. 告诉你哪个 pane 需要关注
2. 把该 pane 的当前提示和最近输出带过来
3. 在你明确给出动作后，再去执行 `tmux send-keys`

不要把任何“关键词命中就自动选择”的逻辑写进 tmux-goto。

## 通知最小字段

通知至少应包含：

- `pane_id`
- `pane_title`
- `prompt`
- `recent_output`

如果还能提供这些字段会更稳：

- `session`
- `window`
- `cwd`
- `current_command`

## 最小通知示例

```json
{
  "pane_id": "%0",
  "pane_title": "dev",
  "prompt": "Do you want to proceed?\n1. Yes\n2. No",
  "recent_output": "最近 30-80 行 pane 输出"
}
```

复杂场景可以额外补：

```json
{
  "session": "0",
  "window": "0",
  "cwd": "/path/to/project",
  "current_command": "python3 -c ..."
}
```

## 生成通知

如果外部调度还没有自己的 payload 组装逻辑，优先直接用本 skill 自带脚本生成通知：

```bash
python3 /Users/busiji/.codex/skills/tmux-goto/scripts/build_tmux_notification.py --pane-id %0
```

这个脚本只负责：

- 读取 `pane_id`
- 抓取最近输出
- 补上 `session / window / pane_title / cwd / current_command`
- 给出一个很轻量的 `prompt` 摘要

它不会做任何自动判断，也不会发送按键。

## 收到通知后的默认动作

收到通知后，默认先做这三步：

1. 定位 pane
2. 抓取最近输出
3. 只汇报上下文和建议动作，不直接执行

只有在用户已经明确授权“你来决定并执行”时，才进入发送按键阶段。

## watcher 输出格式

`watch_tmux_notifications.py` 输出的是逐行 JSON，字段与单次通知脚本保持一致，并额外补：

- `event`: 固定为 `pane_attention`
- `detected_at`: ISO8601 时间
- `signature`: 当前提示块的稳定签名

## 对外 handoff bundle

如果需要把同一条 pane 通知同时交给 tmux-goto 和数据库，直接把通知事件送进：

```bash
python3 /Users/busiji/.codex/skills/tmux-goto/scripts/build_tmux_goto_bundle.py
```

这个脚本会输出一个总对象，公开字段只有两路：

- `tmux_goto`: 原始通知，推给 tmux-goto
- `db_write`: 数据库写入指令，推给数据库

输出里的 `fanout` 数组是内部实现细节，对外不推荐直接使用。

## 建议返回格式

如果还不该执行，优先返回：

```json
{
  "pane_id": "%0",
  "action": "hold",
  "reason": "已查看 pane，上下文已补齐，建议先由你确认是否执行"
}
```

如果可以执行，再返回：

```json
{
  "pane_id": "%0",
  "action": "send_keys",
  "keys": ["C-m"],
  "reason": "当前是一次性普通确认，允许继续"
}
```

## 工作流程

### 1. 定位 pane

优先直接使用通知里的 `pane_id`。

如果只有标题或 session/window 信息，再用：

```bash
tmux list-panes -a -F '#{session_name}:#{window_index}.#{pane_index}	#{pane_id}	#{pane_title}'
```

### 2. 查看最近输出

先看最近屏幕：

```bash
tmux capture-pane -p -t <pane_id>
```

如果不够，再看更长上下文：

```bash
tmux capture-pane -p -S -200 -t <pane_id>
```

### 3. 判断下一步

根据真实上下文决定：

- 只是汇报当前状态
- 给出建议，但不执行
- 发送一次确认键
- 中断当前命令
- 继续让该 pane 干活

不要把判断规则写死成关键词匹配。关键词只能帮助你发现“可能有提示”，不能替代上下文判断。

### 4. 必要时执行

只有在已经确认该动作合理时，才执行，例如：

```bash
tmux send-keys -t <pane_id> C-m
```

或：

```bash
tmux send-keys -t <pane_id> C-c
```

### 5. 执行后复查

执行后立刻重新抓一次 pane：

```bash
tmux capture-pane -p -t <pane_id>
```

确认：

- 提示是否消失
- 任务是否继续推进
- 是否进入新的确认框或报错

## 输出要求

优先用简短结构化汇报：

- `目标 pane`
- `看到的上下文`
- `采取的动作`
- `当前结果`

如果没有执行任何动作，也要明确说明原因，例如“上下文不足，先不选”。
