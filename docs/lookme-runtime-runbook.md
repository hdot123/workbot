# Lookme Runtime Runbook

> Legacy Notice (P12-rest, 2026-04-18):
> 本文档保留为历史 `lookme/tmux` 运行记录，不再是当前正式执行入口。
> 当前正式入口与真相文档请使用：
> - `/Users/busiji/workbot/docs/cmux-runtime-handbook.md`
> - `/Users/busiji/workbot/docs/cmux-subagent-runtime-chain.md`
> - `/Users/busiji/workbot/AGENTS.md`

## 目的

这份文档定义一套固定流程：

- 你发一句启动指令
- 我整理当前会话任务分配
- 你手动就位 `formal-session` 里的固定 4 个 pane
- 我把任务发进这 4 个 pane
- 我启动并验活 `lookme` 常驻守护
- pane 停住时我去处理
- 当前会话进入收口后我回写状态，并决定进入下一会话还是转 idle

Obsidian 导航入口：[[会话运行文档导航]]

这份文档只保留历史链路说明（非当前正式执行链）：

- tmux 正式运行面：`formal-session`
- 任务分配文件：
  [`lookme-assignment.json`](/Users/busiji/workbot/workspace/artifacts/tmux-skills/lookme/lookme-assignment.json)
- watcher 入口：
  [`lookme.py`](/Users/busiji/workbot/workspace/artifacts/tmux-skills/lookme/lookme.py)
- 常驻守护入口：
  [`lookme_supervisor.py`](/Users/busiji/workbot/workspace/artifacts/tmux-skills/lookme/lookme_supervisor.py)

正式规则真源：

- [A1-A9 Session Protocol](/Users/busiji/workbot/docs/a1-a9-session-protocol.md)
- [A1-A9 Session Brief](/Users/busiji/workbot/docs/a1-a9-session-brief.md)

强制要求：

- 每次正式会话开始前，必须先读一遍 Session Brief
- 本 runbook 只解释操作，不替代 Session Protocol

## 你怎么发第一句

推荐直接发这种：

```text
启动今天的 AEdu 4-pane runtime
```

或者更明确一点：

```text
按 task list 整理今天 4 个 pane 的任务，然后启动 lookme
```

如果你已经知道今天的重点，也可以直接说：

```text
今天主线是 AEdu 阶段三，按 dev / rea / qa / doc 四个 pane 开工并启动 lookme
```

固定拓扑始终是：

- `1` 个 `dev-bot`
- `1` 个 `rea-bot`
- `1` 个 `qa-bot`
- `1` 个 `doc-bot`

## 我必须做的事

收到启动指令后，我必须按这个顺序做，不能跳步：

1. 先做“任务系统唤醒”：
   - 读取当天任务真源
   - 读取 CE 计划
   - 给出整体项目情况
   - 说明 CE 已完成多少、未完成多少
   - 说明哪些项符合要求、哪些项需要整改
2. 检查 `formal-session` 是否存在，并确认 pane 拓扑可用。
   固定要求是：
   - `formal-session:1.1` -> `dev-bot`
   - `formal-session:1.2` -> `rea-bot`
   - `formal-session:1.3` -> `qa-bot`
   - `formal-session:1.4` -> `doc-bot`
3. 读取当天任务真源：
   - [`dev-task-list.md`](/Users/busiji/workbot/workspace/projects/AEdu/dev-task-list.md)
   - [`rea-task-list.md`](/Users/busiji/workbot/workspace/projects/AEdu/rea-task-list.md)
   - [`qa-task-list.md`](/Users/busiji/workbot/workspace/projects/AEdu/qa-task-list.md)
   - [`doc-task-list.md`](/Users/busiji/workbot/workspace/projects/AEdu/doc-task-list.md)
   - [`ce-sync-plan.md`](/Users/busiji/workbot/workspace/projects/AEdu/ce-sync-plan.md)
4. 生成或更新
   [`lookme-assignment.json`](/Users/busiji/workbot/workspace/artifacts/tmux-skills/lookme/lookme-assignment.json)。
5. 等你手动把这 4 个 pane 就位。
6. 把任务发进 4 个 pane。
7. 启动 `lookme_supervisor.py`。
8. **验活**：
   - supervisor 进程存在
   - child watcher 进程存在
   - assignment 文件里至少有 1 个真实 active assignment，不能是空 `panes`，也不能是“待分配任务”占位项
   - 目标 pane 已收到当前会话任务
9. 只有验活完成后，我才可以说“已经启动”。

## 启动命令

### 1. 启动或保持 `lookme` 常驻守护

```bash
python3 /Users/busiji/workbot/workspace/artifacts/tmux-skills/lookme/lookme_ctl.py start \
  --assignment-file /Users/busiji/workbot/workspace/artifacts/tmux-skills/lookme/lookme-assignment.json \
  --no-auto-approve
```

说明：

- 默认用 `--no-auto-approve`
- 这条链路必须通过 supervisor 起，不要只裸跑 `lookme.py`
- 如果 assignment 文件为空，或者 active assignment 还是占位任务，`start` 会直接失败

### 2. 验活命令

```bash
python3 /Users/busiji/workbot/workspace/artifacts/tmux-skills/lookme/lookme_ctl.py status \
  --assignment-file /Users/busiji/workbot/workspace/artifacts/tmux-skills/lookme/lookme-assignment.json
```

期望结果：

- 一条 supervisor
- 一条 child watcher
- `assignment.ready == true`

补充：

- `status` 在 supervisor / child / assignment 三者任一不健康时会返回非 `0`
- 所以“进程在”但 assignment 是空的，不再算启动成功

### 3. 看运行日志

```bash
tail -n 80 /Users/busiji/workbot/workspace/artifacts/tmux-skills/lookme/lookme-runtime.log
tail -n 40 /Users/busiji/workbot/workspace/artifacts/tmux-skills/lookme/lookme-supervisor.log
```

## 任务分配文件规则

`lookme` 不猜任务。

没有有效任务分配时，`lookme` 不应该被视为“成功启动”。

没有 active assignment，或者 active assignment 仍是“待分配任务”占位项时，
`lookme_ctl.py start` 必须失败，不能硬说“已经在监控”。

唯一正式输入文件是：

[`lookme-assignment.json`](/Users/busiji/workbot/workspace/artifacts/tmux-skills/lookme/lookme-assignment.json)

每个 pane 至少要有这些字段：

- `assignment_id`
- `target`
- `bot_name`
- `role`
- `title`
- `goal`
- `display_name`
- `task_text`
- `continue_text`
- `status`

主键规则：

- pane 实例真源：`target`
- 当前任务真源：`assignment_id`
- `bot_name` 只是角色牌子，不是长期身份

固定角色规则：

- `formal-session:1.1` 永远承载 `dev-bot`
- `formal-session:1.2` 永远承载 `rea-bot`
- `formal-session:1.3` 永远承载 `qa-bot`
- `formal-session:1.4` 永远承载 `doc-bot`
- 变化的是 assignment，不是 pane target

## 启动后的现场检查

任务发完以后，我必须立即检查 4 个 pane：

```bash
for t in formal-session:1.1 formal-session:1.2 formal-session:1.3 formal-session:1.4; do
  echo "=== $t ==="
  tmux display-message -p -t "$t" 'pane_id=#{pane_id} title=#{pane_title} cmd=#{pane_current_command} active=#{pane_active} dead=#{pane_dead} in_mode=#{pane_in_mode}'
  tmux capture-pane -t "$t" -p -S -20 | tail -n 20
  echo
done
```

启动成功的最低标准不是“进程在”，而是：

- assignment 文件里存在真实 active assignment
- 对应 pane 已收到当前 assignment 的任务文本
- 至少有 `running` / `thinking` / `reading` / `执行中` 等推进迹象

## pane 停住时怎么处理

原则只有一句：

**pane 消息 = 强执行信号，必须去处理。**

发现 pane 停住时，优先分成三类：

### 1. 命令审批

特征：

- `This command requires approval`
- `Do you want to proceed?`

处理：

- 直接去对应 pane
- 先过审批
- 再复查是否恢复执行

### 2. Claude queued message

特征：

- `Press up to edit queued messages`
- pane 停在 prompt，但消息没有继续消费

处理：

- 不要继续往里叠很多消息
- 先 `C-c`
- 再只发一条最短、唯一、明确的继续指令

### 3. 已完成停在结果页

特征：

- pane 已给出完整交付结论
- 已经回到 prompt

处理：

- 不再催当前任务
- 先回写 task list / assignment
- 再决定进入下一会话还是转 idle
- 如果当前会话没有下一会话真实任务，直接停掉 `lookme`，并把 assignment 清回空闲态；不允许让空 assignment 继续伪装成“在监控”

## 会话收口时的动作

当当前会话的 active assignment 都完成时，我必须做这些动作：

1. 重新看 4 个 pane，确认不是“看起来像完成”，而是真的有交付结论。
2. 回写：
   - [`dev-task-list.md`](/Users/busiji/workbot/workspace/projects/AEdu/dev-task-list.md)
   - [`rea-task-list.md`](/Users/busiji/workbot/workspace/projects/AEdu/rea-task-list.md)
   - [`qa-task-list.md`](/Users/busiji/workbot/workspace/projects/AEdu/qa-task-list.md)
   - [`doc-task-list.md`](/Users/busiji/workbot/workspace/projects/AEdu/doc-task-list.md)
3. 判断是否存在下一会话真实任务。
4. 若存在，则更新
   [`lookme-assignment.json`](/Users/busiji/workbot/workspace/artifacts/tmux-skills/lookme/lookme-assignment.json)
   为下一会话任务，并确认 watcher 已经重新读取 assignment。
5. 若不存在，则停掉 `lookme` 并把 assignment 清回 idle。

## 我不该再犯的错误

### 1. 不能只说“脚本已经启动”

必须先验活，再说启动成功。

而且“验活”现在必须同时看：

- supervisor
- child watcher
- assignment.ready

### 2. 不能把 pane 停住只当提醒

看到了就必须去处理。

### 3. 不能在 Claude queued message 状态下连续灌很多消息

那会让 pane 更乱。

### 4. 不能把 bot 名称当实例身份

必须按 `target + assignment_id` 管理。

## 每天的最短操作模板

### 用户一句话

```text
启动今天的 AEdu 4-pane runtime
```

### 我应执行的固定流程

1. 看 task list，整理今天 4 条任务。
2. 更新
   [`lookme-assignment.json`](/Users/busiji/workbot/workspace/artifacts/tmux-skills/lookme/lookme-assignment.json)。
3. 启动或保持
   [`lookme_supervisor.py`](/Users/busiji/workbot/workspace/artifacts/tmux-skills/lookme/lookme_supervisor.py)。
4. 验活 supervisor + watcher + `assignment.ready`。
5. 看目标 pane 是否已吃到当前会话任务。
6. 任务中途 pane 一停住，立刻处理。
7. 当前会话收口后，先回写 task list，再决定进入下一会话还是转 idle。

## 当前结论

以后“开始运行”不再是口头状态，必须同时满足这 4 条：

- assignment 已更新
- supervisor + watcher 已验活
- `assignment.ready == true`
- 目标 pane 已吃到当前任务

少任何一条，都不算真正跑起来。
