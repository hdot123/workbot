# Lookme Runtime Cheatsheet

> Legacy Notice (P12-rest, 2026-04-18):
> 本文档是历史 `lookme/tmux` 速查表，不再代表当前正式运行口径。
> 当前正式执行入口请改用 `/Users/busiji/workbot/docs/cmux-runtime-handbook.md`。
> 下文所有 `4-pane/formal-session/lookme` 命令仅用于历史追溯，不用于当前正式运行。

## 1. 你发什么

```text
启动今天的 AEdu 4-pane runtime
```

或者：

```text
按 task list 整理今天 4 个 pane 的任务，然后启动 lookme
```

默认拓扑：`1 dev + 1 rea + 1 qa + 1 doc`
若当前会话没有独立审计位需求，才允许临时切回 `2 dev + 1 qa + 1 doc`

## 2. 我必须做什么

1. 先做任务系统唤醒：看 task list + CE plan，汇报整体情况
2. 更新 assignment 文件
3. 等你手动把 4 个 pane 就位
4. 启动 supervisor
5. 验活 supervisor + watcher
6. 确认 assignment 不是空壳，并看目标 pane 是否真的吃到任务

## 3. 任务真源

- [dev-task-list.md](/Users/busiji/workbot/projects/AEdu/dev-task-list.md)
- [qa-task-list.md](/Users/busiji/workbot/projects/AEdu/qa-task-list.md)
- [doc-task-list.md](/Users/busiji/workbot/projects/AEdu/doc-task-list.md)
- [rea-task-list.md](/Users/busiji/workbot/projects/AEdu/rea-task-list.md)
- [ce-sync-plan.md](/Users/busiji/workbot/projects/AEdu/ce-sync-plan.md)

## 4. assignment 文件

- [lookme-assignment.json](/Users/busiji/workbot/artifacts/tmux-skills/lookme/lookme-assignment.json)

## 5. 启动命令

```bash
python3 /Users/busiji/workbot/artifacts/tmux-skills/lookme/lookme_ctl.py start \
  --assignment-file /Users/busiji/workbot/artifacts/tmux-skills/lookme/lookme-assignment.json \
  --no-auto-approve
```

补充：

- 如果 assignment 文件为空，或者 active assignment 还是“待分配任务”占位项，`start` 会直接失败

## 6. 验活命令

```bash
python3 /Users/busiji/workbot/artifacts/tmux-skills/lookme/lookme_ctl.py status \
  --assignment-file /Users/busiji/workbot/artifacts/tmux-skills/lookme/lookme-assignment.json
```

正确结果：

- 一条 `lookme_supervisor.py`
- 一条 `lookme.py`
- `assignment.ready == true`

补充：

- `status` 在 supervisor / child / assignment 三者任一不健康时会返回非 `0`
- 所以“进程还在”但 assignment 是空的，不再算真的在监控

## 7. 看日志

```bash
tail -n 80 /Users/busiji/workbot/artifacts/tmux-skills/lookme/lookme-runtime.log
tail -n 40 /Users/busiji/workbot/artifacts/tmux-skills/lookme/lookme-supervisor.log
```

## 8. 看 4 个 pane

固定角色：

- `formal-session:1.1` -> `dev-bot`
- `formal-session:1.2` -> `rea-bot`
- `formal-session:1.3` -> `qa-bot`
- `formal-session:1.4` -> `doc-bot`

```bash
for t in formal-session:1.1 formal-session:1.2 formal-session:1.3 formal-session:1.4; do
  echo "=== $t ==="
  tmux display-message -p -t "$t" 'pane_id=#{pane_id} title=#{pane_title} cmd=#{pane_current_command} active=#{pane_active} dead=#{pane_dead} in_mode=#{pane_in_mode}'
  tmux capture-pane -t "$t" -p -S -20 | tail -n 20
  echo
done
```

## 9. pane 停住时怎么处理

### 审批卡住

特征：

- `This command requires approval`
- `Do you want to proceed?`

命令：

```bash
tmux send-keys -t formal-session:1.1 Enter
```

把 target 换成实际 pane。

### queued messages 卡住

特征：

- `Press up to edit queued messages`

处理原则：

- 先 `C-c`
- 再只发一条短消息

示例：

```bash
python3 - <<'PY'
from watch_pane import dispatch_task
dispatch_task(
    'formal-session:1.1',
    '继续当前任务，直接输出正式交付。不要反问。',
    cancel_first=True,
)
PY
```

工作目录：

```text
/Users/busiji/workbot/artifacts/tmux-skills/lookme
```

## 10. 当前会话收口后做什么

1. 再看一遍 4 个 pane
2. 回写 task list（含 `rea-task-list.md`）
3. 判断是否存在下一会话真实任务
4. 如果存在，更新 assignment 文件，并确认 watcher 已经把下一会话任务发进去
5. 如果不存在，直接停掉 `lookme`，不要让空 assignment 留在“监控中”状态

## 11. 什么叫真正跑起来

必须同时满足：

1. assignment 已更新
2. supervisor + watcher 进程都在
3. `assignment.ready == true`
4. 目标 pane 都已经收到当前任务

少一条都不算。
