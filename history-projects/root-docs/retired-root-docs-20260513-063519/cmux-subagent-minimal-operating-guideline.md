# cmux Runtime Minimal Operating Canonical

本文只回答当前 `workbot` 怎样最小合法地使用 `cmux` 子代理运行面。

## 文档定位

- 本文件是 minimal operating canonical。
- 主 canonical truth 在 `/Users/busiji/workbot/docs/cmux-subagent-runtime-chain.md`。
- truth source map 在 `/Users/busiji/workbot/docs/cmux-subagent-runtime-truth-table.md`。
- 如果本文件与上面两份文档冲突，以上面两份为准。

## 一句总口径

当前正式子代理不是“一个 pane”或“一个 title”，而是：

`assignment + pane + primary terminal surface`

身份不是从 UI 标签生成的，而是由可解析 agent 文件出发，通过 `claude --agent <lane_identity>` 在启动时锁定。

这里还必须同时记住 bot 三层模型：

- global bot layer：`~/.claude/agents/*.md`
- project binding layer：`/Users/busiji/workbot/.claude/agents/*.md`
- project runtime layer：`workbot` 把已绑定 bots 跑进 `cmux`

## 1. 如何发起正式子代理任务

1. 先准备外部 active assignment。不要把任务直接写成某个 pane 内的临时文本。
2. 先把外部主线程和项目 `cmux` workspace 分开记账：外部主线程负责调度、派发、汇总和裁定，它不在项目内部 `5+1` 里。
3. 再按项目内部 truth 记账：当前项目内部正式拓扑固定为 `5+1`：
   - `pm-bot`、`dev-bot`、`qa-bot`、`doc-bot`、`rea-bot` 五个绑定到全局 bots 的项目 runtime pane
   - `1` 个 `cmux-browser` board pane
4. `cmux-browser` 只是 board pane，不是正式 bot 身份。
5. 当前可用于项目内部 formal bot lane 的 bot 名只使用：
   - `pm-bot`
   - `dev-bot`
   - `qa-bot`
   - `doc-bot`
   - `rea-bot`
6. 用 `/Users/busiji/.agents/skills/cmux/scripts/bootstrap_claude_runtime.py` 建当前 `cmux` runtime carrier。

这六个点里要分层理解：

- `pm-bot / dev-bot / qa-bot / doc-bot / rea-bot` 先是 global bots
- 再由 `workbot/.claude/agents/*.md` 绑定进项目
- 最后才在项目 `cmux` workspace 里作为五个 bot pane 运行

## 2. 如何绑定 lane

当前只用这一套解释：

- `logical_target / bot_name` 负责 lane binding。
- `lane_identity` 负责 agent locking。
- 当前 active flow 仍要求 `lane_identity == bot_name`。

因此，最小合法 assignment 至少要满足：

- 能唯一绑定到一个 lane。
- active 项已经通过 `dispatch_ready` gate。
- 运行后能回填 `workspace_ref`、`pane_ref`、`surface_ref`、`runtime_identity`。

## 3. 如何锁 agent 身份

当前运行时只认这条锁定链：

1. 先查 `/Users/busiji/workbot/.claude/agents/<lane_identity>.md`
2. 项目里没有时，再查 `~/.claude/agents/<lane_identity>.md`
3. 仍找不到就报错

真正的锁定动作是：

```bash
claude --agent <lane_identity>
```

补充边界：

- caller-explicit agent fallback 当前未实现。
- 外部 `main-thread` 是调度身份，不是项目本地 agent 文件身份，也不在项目内部 `5+1` 里。
- `cmux-browser` 也不是项目本地 agent 文件身份。
- `pm-bot` 当前在项目文档层已经是一个绑定到全局 bot 的项目 runtime pane；role body 已闭合。
- `pm-bot` 当前 role body 应理解为 产品分析 / 模仿产品 / 整理需求 / 采集网站内容 / benchmarking / imitation analysis。
- 若文档里仍出现 `clarification`，只按产品侧需求梳理理解，不得外推成主线程级裁定。
- `pm-bot` 的工具边界要跟 active runtime/tool policy 走，不能直接拿 legacy collector 变体覆盖。

## 4. 如何确认当前 surface 合法

同时满足下面这些点，才算当前口径下的合法正式运行面：

1. 有合法 active assignment。
2. assignment 已绑定到唯一 lane。
3. 对应 lane 的 primary terminal surface 上实际跑的是原生 `claude --agent` 会话。
4. assignment 运行态已经回填：
   - `workspace_ref`
   - `pane_ref`
   - `surface_ref`
   - `runtime_identity`
5. 当前 active flow 没有违反 `lane_identity == bot_name` 基线。

最小检查动作可以用：

- `cmux ping`
- `cmux tree`
- 查看 `/Users/busiji/workbot/workspace/artifacts/cmux-runtime/` 下 assignment 运行态字段是否已回填

## 5. 如何避免把 title 当成身份真源

当前必须坚持下面这条线：

- `pane title` 只是 runtime lookup aid。
- `surface title` 只是 runtime lookup aid。
- title 可以参与 live lookup、surface 回填和可见标签表达。
- title 不生成身份真相。

所以不要做这几件事：

- 不要因为 title 看起来像 `dev-bot` 就认定它已经锁上 `dev-bot` 身份。
- 不要把 board surface 的 title 当成正式 bot 身份。
- 不要把 title 回填成功误写成“title 生成了身份”。

## 6. 如何理解 `5+1 + cmux-browser`

当前 `5+1` 的正确解释是：

- 外部主线程在项目 `cmux` workspace 外，不属于下面这个 `5+1`。
- `5` 指项目内部五个绑定 bot runtime pane：
  - `pm-bot`
  - `dev-bot`
  - `qa-bot`
  - `doc-bot`
  - `rea-bot`
- `+1` 指 `cmux-browser` board pane

这里必须分层理解：

- 外部 `main-thread` 是项目外部 scheduler/control context。
- `pm-bot` 是项目内部一个绑定到全局 bot 的 runtime pane，role body 已闭合。
- `dev-bot / qa-bot / doc-bot / rea-bot` 是其他绑定到全局 bots 的项目 runtime pane。
- `cmux-browser` 是看板运行面，不是正式 bot 身份。

对 `pm-bot` 还要再分三层：

- role body：产品分析 / 模仿产品 / 整理需求 / 采集网站内容 / benchmarking / imitation analysis
- tool truth：跟 active runtime/tool policy 和 implemented gates 走
- legacy collector variant：历史残留，不是当前 canonical capability contract

本轮实现补尾已经收掉 watcher Crawl4AI residue 和 `continue_text` bookkeeping mismatch，所以最小操作口径里不再把它们当作当前 reader-facing 冲突；如果还要继续追踪，只保留 memory lesson 缺失引用和全局默认 materialization 的实现残留。

## 7. 当前实现路径与项目真相的边界

当前某些显式四-bot 启动命令可以作为可用实现路径，但它们不是 canonical `5+1` 拓扑声明。

例如下面这条命令当前可用，但只应被当成实现路径，不应反向改写项目 truth：

```bash
python3 /Users/busiji/.agents/skills/cmux/scripts/bootstrap_claude_runtime.py \
  --project-dir /Users/busiji/workbot \
  --recreate \
  --bot-name dev-bot \
  --bot-name qa-bot \
  --bot-name doc-bot \
  --bot-name rea-bot
```

当前仍然必须按下面这套 truth 解释：

- `cmux` 是唯一正式 runtime carrier。
- 项目内部正式拓扑固定为 `5+1`：`pm-bot / dev-bot / qa-bot / doc-bot / rea-bot + cmux-browser`。
- 外部主线程在项目 `cmux` workspace 外。
- `cmux-browser` 不是正式 bot 身份。
- 全局默认里的 `empty` 仍只能按 board placeholder 或实现残留解释。
- `pm-bot` 不再按默认泄漏处理；它在项目文档层已经被写成一个绑定到全局 bot 的项目 runtime pane。
- `pm-bot` 的 role body 已闭合；当前仍需显式保留的是实现侧冲突，不是 role-contract 未决。

当前还必须补记 `pm-bot` 控制链的最小真相：

- assignment source 在外部
- `dispatch_owner = codex`
- watcher / reminder / continue / takeover 基线是 shared core
- `pm-bot` 只在 shared core 上叠加 special cases
- shared state 仍走 `hook-state.json`、shared watcher pid/log 和 shared `cmux notify`
- `pm-bot-watch.json` 只代表 `pm-bot` single-bot special case
- 旧 `CODEX_THREAD_ID` / doorbell / monitor-thread 只按 legacy residue 理解
- 当前实现侧冲突仍需显式保留，不能被文档假装抹平
