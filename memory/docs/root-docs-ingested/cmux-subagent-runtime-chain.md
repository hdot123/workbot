# cmux Runtime Canonical Truth

本文是 `workbot` 当前 `cmux` 运行真相的主文。

## 文档定位

- 本文件是当前项目面向使用者的 primary canonical truth document。
- `/Users/busiji/workbot/docs/cmux-subagent-runtime-truth-table.md` 负责 truth source map 与 supporting fact table。
- `/Users/busiji/workbot/docs/cmux-subagent-minimal-operating-guideline.md` 负责 minimal operating canonical。

项目文档之间如果冲突，以本文件为准。  
本文件如果与底层真相源冲突，按下面顺序处理：

1. `/Users/busiji/workbot/AGENTS.md` 与 `/Users/busiji/workbot/.claude/agents/*.md` 决定仓库级身份范围。
2. `/Users/busiji/.agents/skills/cmux/references/workbot/cmux-multi-pane-agent-runtime-requirements.md`、`/Users/busiji/.agents/skills/cmux/SKILL.md` 与当前 `cmux` 脚本实现共同决定 runtime 规则边界。
3. 本文件负责把上面两层整理成当前 `workbot` 可复用的 canonical wording。

本文只写当前已经清理并审定的实现链条和项目口径，不补写理想架构，不把历史残留写成当前真相。

## 定稿口径

- 当前唯一正式 runtime carrier 是 `cmux`。
- 外部 `main-thread` 是项目外部的调度/裁定上下文；它不在项目 `cmux` workspace 内，也不是项目内部 `5+1` 里的 pane。
- 当前项目内部正式运行拓扑固定为 `5+1`：
  - `pm-bot`、`dev-bot`、`qa-bot`、`doc-bot`、`rea-bot` 五个绑定到全局 bots 的项目 runtime pane
  - `1` 个 `cmux-browser` board pane
- `cmux-browser` 是看板运行面，不是正式 bot 身份。
- 当前项目内部五个绑定 bot runtime pane 是：
  - `pm-bot`
  - `dev-bot`
  - `qa-bot`
  - `doc-bot`
  - `rea-bot`
- `pm-bot` 的 role body 已闭合；tool policy 单独跟随 active runtime/tool policy 和 implemented gates；legacy collector variant 只按 historical residue 理解。
- `dev-bot`、`qa-bot`、`doc-bot`、`rea-bot` 是其他绑定到全局 bots 的项目 runtime pane。
- 外部 `main-thread` 仍是调度身份，不要求项目本地 agent 文件。
- `logical_target / bot_name` 承担 lane-binding 语义。
- `lane_identity` 承担 agent-locking 语义。
- 当前 active flow 仍要求 `lane_identity == bot_name`。
- `pane title` / `surface title` 只是 runtime lookup aid，不是 identity truth。
- caller-explicit agent fallback 不属于当前已实现能力；当前口径以 `bootstrap` 实现为准。

## 真相源分层

当前 `workbot` 的 `cmux` 运行真相要按两组分层一起理解：

### A. Bot 三层模型

1. global bot layer  
   文件：
   - `/Users/busiji/.claude/agents/*.md`

   这一层定义全局 bot body。对当前项目而言，`workbot` 当前使用的全局 bot 集合是：
   - `pm-bot`
   - `dev-bot`
   - `qa-bot`
   - `doc-bot`
   - `rea-bot`

2. project binding layer  
   文件：
   - `/Users/busiji/workbot/.claude/agents/*.md`

   这一层不重新发明 bot 类别，而是声明 `workbot` 当前绑定/启用哪些全局 bot。当前 `workbot` 绑定的是全局 `pm-bot / dev-bot / qa-bot / doc-bot / rea-bot`。

3. project runtime layer  
   文件：
   - `/Users/busiji/.agents/skills/cmux/references/workbot/cmux-multi-pane-agent-runtime-requirements.md`
   - `/Users/busiji/.agents/skills/cmux/SKILL.md`
   - `/Users/busiji/.agents/skills/cmux/scripts/bootstrap_claude_runtime.py`
   - `/Users/busiji/.agents/skills/cmux/scripts/generate_cmux_assignments.py`
   - `/Users/busiji/.agents/skills/cmux/scripts/watch_cmux_assignments.py`
   - `/Users/busiji/.agents/skills/cmux/scripts/cmux_hook_state.py`

   这一层回答“`workbot` 怎样把已绑定 bot 跑进 `cmux`”。

### B. 项目文档层

1. 仓库级边界层  
   文件：
   - `/Users/busiji/workbot/AGENTS.md`

   这一层回答仓库级身份边界、外部主线程边界和项目运行定位。

2. 项目解释层  
   文件：
   - 本文件：canonical truth
   - `cmux-subagent-runtime-truth-table.md`：truth source map
   - `cmux-subagent-minimal-operating-guideline.md`：minimal operating canonical

   这一层回答“当前使用者应该怎样理解和使用这套 truth”。

## 子代理怎么生成

### 1. `cmux` 不生成任务真相

当前实现里，`assignment`、`task_text`、`continue_text` 都是外部真源。`cmux` 负责消费、绑定和启动，不负责自己发明任务。

这句话的实际含义是：

1. 先有外部 assignment。
2. 再由 `cmux` 把 assignment 绑定到 lane、pane、surface。
3. 最后在对应的 primary terminal surface 上启动 Claude agent。

没有合法 assignment，就没有合法正式子代理任务。

### 2. 正式运行单元是什么

当前正式运行单元不是单独 `pane`，也不是单独 `surface`，而是：

`assignment + pane + primary terminal surface`

这条定义排除了三种常见误读：

- 不是只有 `pane` 就算一个正式子代理。
- 不是只有 `surface` 就算一个正式子代理。
- 不是 `title` 一改名就生成了正式身份。

### 3. 哪些 assignment 字段参与生成链

已审定的实现链条里，下面这些字段直接参与运行生成：

- `assignment_id`
- `logical_target`
- `bot_name`
- `lane_identity`
- `task_text`
- `continue_text`
- `status`
- `dispatch_ready`
- 运行后回填的 `workspace_ref`
- 运行后回填的 `pane_ref`
- 运行后回填的 `surface_ref`
- 运行后记录的 `runtime_identity`

当前应这样理解：

- `logical_target / bot_name` 决定 assignment 绑定到哪个 lane。
- `lane_identity` 决定真正锁到哪个 agent 文件和哪个 `claude --agent`。

这两层不能混写。

## 身份怎么锁定

### 1. 仓库级身份真源是什么

对 `workbot` 而言，仓库级身份真源是：

- `/Users/busiji/workbot/AGENTS.md`
- `/Users/busiji/workbot/.claude/agents/*.md`

当前项目文档层的五个绑定 bot runtime pane 有五个：

- `pm-bot`
- `dev-bot`
- `qa-bot`
- `doc-bot`
- `rea-bot`

这里必须分开三层：

- global bot layer：`/Users/busiji/.claude/agents/*.md` 定义全局 bot body。
- project binding layer：`/Users/busiji/workbot/.claude/agents/*.md` 声明 `workbot` 当前绑定哪些全局 bot。
- project runtime layer：`workbot` 再把这些已绑定 bot 跑进项目 `cmux` workspace。

对 `pm-bot` 来说：

- global body 已存在。
- project binding file 已存在。
- project runtime pane 已纳入当前项目内部 `5+1`。

因此 `pm-bot` 的 global body / project binding / project runtime 三层现在是对齐的。  
`pm-bot` 的 role body 也已经闭合；剩余需要单列的是实现侧冲突，不是 role-contract 未决。

外部 `main-thread` 只是调度身份，不是项目内部 pane，也不是项目本地 agent 文件身份。  
`cmux-browser` 只是 board pane，也不是项目本地 agent 文件身份。

### 2. 运行时真实锁定靠什么

当前真实锁定动作发生在启动命令层：

```bash
claude --agent <lane_identity>
```

这意味着：

- 能不能锁上正式身份，取决于 `<lane_identity>` 能不能解析到真实 agent 文件。
- 锁定发生在启动命令层，不在 UI 标签层。
- `pane title` 和 `surface title` 都不生成身份真相。

### 3. agent 文件解析顺序

当前审定的实现顺序是：

1. `/Users/busiji/workbot/.claude/agents/<lane_identity>.md`
2. `~/.claude/agents/<lane_identity>.md`
3. 找不到就报错

这里需要明确记录当前边界：

- 旧文案提过 caller-explicit fallback。
- 当前 `bootstrap_claude_runtime.py` 没有对应参数，也没有这层实现。

所以当前可复用的正式口径只有两层解析，没有第三层显式 fallback。

### 4. `logical_target`、`bot_name`、`lane_identity` 的关系

当前最终口径如下：

- `logical_target / bot_name` 负责 lane binding。
- `lane_identity` 负责 agent locking。
- 当前 active flow 仍要求 `lane_identity == bot_name`。

这三者在概念上必须分层，但不能把“长期偏离的 `lane_identity`”写成当前常规稳定流，因为 watcher 侧仍把 `lane_identity == bot_name` 当作 active runtime 基线约束。

## 运行时怎么承载和校验

### 1. 正式拓扑为什么是 `5+1`

当前 `workbot` 的项目内部正式运行拓扑是：

- `pm-bot` pane
- `dev-bot` execution pane
- `qa-bot` execution pane
- `doc-bot` execution pane
- `rea-bot` execution pane
- `cmux-browser` board pane

这里的 `5` 指项目 `cmux` workspace 内的五个命名 bot pane：

- `1` 个 `pm-bot` pane
- `4` 个其他 formal execution pane

`+1` 是 `cmux-browser` board pane。它负责看板或辅助浏览运行面，不参与正式 agent 身份锁定，所以不是正式 bot 身份。

外部 `main-thread` 不属于这个项目内部 `5+1`。它负责调度、派发、汇总与裁定，但不记成项目 `cmux` workspace 内的 pane。

## `pm-bot` 角色、工具与 legacy 变体

当前项目文档对 `pm-bot` 必须按三轴拆开写，不能再混成一句话：

### 1. role body

`pm-bot` 当前 canonical role body 是：

- 产品分析
- 模仿产品
- 整理需求
- 采集网站内容
- benchmarking
- imitation analysis

如果文档里仍出现 `clarification`，只应理解为产品侧需求梳理，不应扩展为主线程级任务裁定、范围裁定或验收裁定。
`pm-bot` 不负责 task breakdown、scope convergence、acceptance framing、dispatch、closure 或 adjudication。

这部分来自当前 active bot body，不等于工具权限，也不等于 runtime 特判。

### 2. tool truth

`pm-bot` 的当前工具真相必须单独看 active runtime/tool policy：

- 工具权限来自 active assignment、tool profile 和当前实现 gate。
- 当前 runtime 实现仍把网页事实采集 owner 和 `mcp__crawl4ai__*` 主路径收紧到 `cj-bot`，而不是把它写成 `pm-bot` 的当前 canonical capability contract。
- 因此不能把 `pm-bot` 当前 role body 直接推成网页事实采集 owner 身份。

### 3. legacy collector variant

旧记忆和隔离 lesson/log 中出现过 `pm-bot` 的 collector variant：

- 这类 collector / Crawl4AI 长跑 / checkpoint 口径现在只作为 historical residue 保留。
- 它不是当前项目文档里的 canonical capability contract。
- 当前若需判断工具边界，应回到 active runtime/tool policy 和已实现 gate，而不是直接用 legacy collector 变体覆盖当前口径。

## `pm-bot` 控制链、提醒链与续跑链

当前项目文档对 `pm-bot` 的控制链结论也必须拆开写：

### 1. assignment 与 dispatch

- `assignment` 真源仍在外部，不在 `cmux` 内部生成。
- `dispatch_owner` 当前仍是 `codex`。
- `pm-bot` 没有独立 dispatch owner，也不是外部主线程。

### 2. 当前 active 控制链

当前 active truth 是：

- watcher / reminder / continue / takeover 基线是 shared core。
- `pm-bot` 只在 shared core 上叠加 pm-specific special cases。

这意味着：

- 共享的 assignment/runtime 事实仍走 `cmux-assignment.json`、shared watcher 主循环和 shared runtime gate。
- 共享的 hook 状态仍走 `hook-state.json`。
- 共享的 watcher pid/log 仍走 `watch_cmux_assignments.pid` 和 `watch_cmux_assignments.log`。
- 共享的提醒链当前仍是 `cmux notify` native notify。

### 3. `pm-bot` special cases

当前文档只承认这些 `pm-bot` special cases 已存在：

- single-bot `pm-bot` bootstrap 会使用 `pm-bot-watch.json`
- bootstrap 对 `pm-bot` 有单独 session 启动处理
- watcher 对 `pm-bot` 有专门 continue/correction 分支

因此当前正确口径不是“`pm-bot` 有完整独立控制链”，而是“shared core + pm-specific special cases”。

### 4. legacy reminder / doorbell residue

旧 `CODEX_THREAD_ID` / doorbell / monitor-thread 语义仍只属于 legacy residue：

- 它们来自旧 tmux / monitor-thread / handoff 文档与记忆
- 不是当前 active `cmux` reminder chain
- 当前 active 文档不应再把它们写成 `pm-bot` 的正式提醒目标

### 5. 当前仍保留的实现侧尾项

本轮实现补尾已经收掉 watcher Crawl4AI residue 和 `continue_text` bookkeeping mismatch，所以它们不再属于 remaining open conflict。

当前仍需要保留、但只按实现侧尾项理解的内容是：

- active runtime tool gate 仍把 Crawl4AI 主路径收紧到 `cj-bot`；这属于当前 truth，不是冲突
- active memory hook 仍引用缺失的 `pm-bot-crawl4ai-runtime-path` lesson，而对应 lesson 只在 quarantine 中保留
- 全局默认 materialization 仍可能露出 `pm-bot / dev-bot / qa-bot / doc-bot / rea-bot + empty`，但这只代表实现默认与 board placeholder 残留，不是 reader-facing truth conflict

### 2. `pane`、primary terminal surface、board surface 的关系

当前应这样理解：

- `pane` 是槽位与可见承载位。
- primary terminal surface 是正式执行面。
- board surface 是 `cmux-browser` 所在的看板运行面。

因此：

- `pane title` 不是身份真源。
- `surface title` 不是身份真源。
- terminal surface title 可以参与 live lookup 和 assignment 回填。
- board surface 不能被当成正式 agent surface。

### 3. 启动链条

当前实现链条可压缩成下面几步：

1. `bootstrap_claude_runtime.py` 建 workspace 和运行拓扑。
2. 同步或生成 prelaunch assignment map。
3. 校验 active assignment 的 `dispatch_ready`。
4. 为每个 lane 解析并准备 agent 文件。
5. 以 `claude --agent <lane_identity>` 启动对应 primary terminal surface。
6. 等待 Claude ready。
7. 验证这是原生 Claude agent 会话，而且没有漂移到临时身份流。

当前正式路径是 startup-time locking，不是 session-time identity injection。

### 4. 启动后怎么判定合法

当前口径下，一个正式运行中的子代理至少同时满足：

- 有合法 active assignment。
- assignment 已绑定到唯一 lane。
- 对应 lane 的 primary terminal surface 上实际跑的是原生 `claude --agent`。
- assignment 运行态已回填 `workspace_ref`、`pane_ref`、`surface_ref`、`runtime_identity`。
- 当前 active flow 没有违反 `lane_identity == bot_name` 基线。

## 最小 canonical usage

当前面向使用者的 canonical usage 只有这套解释：

1. 任务由项目 `cmux` workspace 外的外部 assignment 发起和维护。
2. 外部 `main-thread` 负责调度、派发、汇总和裁定，但不记成项目内部 pane。
3. 项目内部 lane 用 `logical_target / bot_name` 绑定到 `pm-bot`、`dev-bot`、`qa-bot`、`doc-bot`、`rea-bot` 之一。
4. agent 用 `lane_identity` 锁定。
5. 正式执行发生在项目内部 bot pane 的 primary terminal surface。
6. `cmux-browser` 只承担 board pane。
7. title 只做 lookup aid，不参与身份真相判定。

当前某些显式四-bot 启动命令可以作为临时实现路径使用，但它们不能反向改写项目 truth，也不能替代 `5+1` 的正式拓扑声明。

## A1-A9 语义到 `cmux 5+1` 实现映射（P12-rest）

> 本节用于把 commander 语义层的 `A1-A9` 明确映射到当前仓库可验证的 `cmux` 实现链，避免把历史 `lookme/tmux` 术语直接当作当前运行真相。

| 会话阶段 | 语义（commander） | 当前 `cmux 5+1` 实现链 | 主脚本 / 产物 |
| --- | --- | --- | --- |
| `A1` | 建立本轮会话拓扑与 lane 角色 | 以 `bootstrap` 建立单 workspace，并物化 `pm/dev/qa/doc/rea + cmux-browser` | `bootstrap_claude_runtime.py` |
| `A2` | assignment 落盘并过启动门禁 | 生成/同步 `cmux-assignment.json`，active assignment 必须 `dispatch_ready=true` 才允许启动 | `generate_cmux_assignments.py`；`artifacts/cmux-runtime/cmux-assignment.json` |
| `A3` | 启动并派发到各 lane | 每个 active lane 通过 `claude --agent <lane_identity>` 启动，且 `lane_identity` 与 `bot_name` 基线一致 | `bootstrap_claude_runtime.py`；`runtime-launch-manifest-*.json` |
| `A4` | 运行态 hook 合同生效 | Hook 统一走 `cmux_claude_hook_bridge.py`；缺 `surface/state_file` 必须 `missing_hook_context` fail-close（退出码 `2`） | `cmux_claude_hook_bridge.py`；`cmux_hook_state.py`；`.claude/settings.local.json` 四事件 |
| `A5` | 监控与解卡 | watcher 轮询 + hook 状态桥接；维持单 workspace guard；写出 consumer sidecar | `watch_cmux_assignments.py`；`cmux-consumer-state-latest.json` |
| `A6` | 收口判定 | 完成判定以 control packet 状态为主（`completed/pass`）；非取证模式下缺 packet 不可判完成 | `watch_cmux_assignments.py`；`cmux_finish_cycle.py` |
| `A7` | 本地治理回写 | finish-cycle 把结果回写 task-list 与 `ce-sync-plan`；normal path 采用结构化来源（control packet / consumer-state） | `cmux_finish_cycle.py`；`*-task-list.md`；`ce-sync-plan.md` |
| `A8` | CE 生命周期同步 | 正式生命周期评论仍由 commander 复核执行；自动收尾默认仅做本地回写 | commander 流程；`cmux_finish_cycle.py --post-gitlab`（可选） |
| `A9` | 下一轮或 idle 出口 | 无下一轮时将 active assignment 置 `IDLE`，并保留 receipt 防重复收口 | `cmux_finish_cycle.py`；`cmux-finish-receipts.jsonl` |

## P12-rest 漂移口径澄清

- `A1-A9` 的语义层仍有效，但 `cmux` 实现链的 assignment 真源路径是 `artifacts/cmux-runtime/cmux-assignment.json`；历史 `lookme-assignment.json` 仅可作为旧术语，不是当前 runtime 真源路径。
- `A7` normal path 证据来源已迁移为结构化来源优先，不再依赖 pane transcript/evidence line；`forensic` 只作为显式兜底路径。
- `cmux-browser` 是 board pane，不是正式 bot 身份，也不是外部 `main-thread` 的替身。
- `empty` 仍可能作为脚本内部 placeholder token 出现，但对外可见运行真相仍是 `cmux-browser`，不得反写为项目身份真源。

## 当前必须遵守的原则

### 仓库级原则

- `AGENTS.md` 负责声明当前仓库正式身份范围。
- `/Users/busiji/workbot/.claude/agents/` 是当前 `workbot` 唯一保留的项目本地 binding / activation agent 文件层；它和项目内部 formal role 集合不是同一层。
- `cmux` 是当前唯一正式 runtime carrier。
- 项目内部正式拓扑是 `5+1`：`pm-bot / dev-bot / qa-bot / doc-bot / rea-bot + cmux-browser`。
- `cmux-browser` 是 board pane，不是正式 bot 身份。
- 外部 `main-thread` 是运行时调度身份，不在项目 `cmux` workspace 内，也不需要项目本地 agent 文件。
- `/Users/busiji/workbot/agents/` 已退出当前仓库布局，不是当前 `cmux` 身份锁定链的一部分。
- `/Users/busiji/workbot/.codex/agents/` 已删除，不是当前 `cmux` 身份锁定链的一部分，也不是并行身份层。

### runtime 级原则

- 身份不由 `pane title` 或 `surface title` 生成。
- 正式身份必须能落到真实 agent 文件。
- 真源决定身份，运行面只承载身份。
- 正式运行单元是 `assignment + pane + primary terminal surface`。
- `cmux` 不发明任务，只消费 assignment。
- 正式启动链是 `claude --agent <lane_identity>`。
- 当前 active flow 仍以 `lane_identity == bot_name` 作为 watcher 基线约束。

### 当前必须保留的实现边界

- 外部主线程不在项目 `cmux` workspace 内；不要把调度上下文写成项目 pane。
- 全局 skill/bootstrap 默认仍可能露出 `pm-bot + empty` 或其他旧合同；对 `workbot` 而言，这不再构成把 `pm-bot` 降格为默认泄漏的理由。
- 当前项目文档只把 `empty` 视为实现侧 board placeholder 残留；项目真相里的 board pane 名是 `cmux-browser`。
- `pm-bot` 的 role body 已定，tool policy 也已按 active runtime/tool gates 分层写清；当前仍需保留的是实现侧冲突，不要把文档写成“实现已经完全统一”。
- caller-explicit agent fallback 旧文案提过，但当前 `bootstrap` 没实现。
- title 参与 live lookup，不等于 title 生成身份。

## 常见误解与纠正

### 误解 1：pane title 或 surface title 就是身份

纠正：

- 不是。
- title 只是 runtime lookup aid。
- 当前正式身份必须能解析到真实 agent 文件，并通过 `claude --agent` 锁定。

### 误解 2：`cmux` 会自动生成任务和身份

纠正：

- 不是。
- assignment 是外部真源。
- `cmux` 只负责消费 assignment、绑定 lane、启动 surface、校验会话。

### 误解 3：`logical_target`、`bot_name`、`lane_identity` 是同一个字段

纠正：

- 不是。
- `logical_target / bot_name` 负责 lane binding。
- `lane_identity` 负责 agent locking。
- 当前 active flow 仍要求 `lane_identity == bot_name`。

### 误解 4：`cmux-browser` 是正式 bot

纠正：

- 不是。
- `cmux-browser` 只代表 board pane 或 board surface。
- 它不参与正式 agent 文件锁定。

### 误解 5：外部 `main-thread` 是项目 `cmux` workspace 内的一个 pane

纠正：

- 不是。
- 外部 `main-thread` 是项目外部的调度/裁定上下文。
- 项目内部 `5+1` 只包含五个 bot pane 和一个 `cmux-browser` board pane。

### 误解 6：`pm-bot` 只是全局默认或实现泄漏，不属于 `workbot` 项目真相

纠正：

- 不是。
- 当前项目文档层已经把 `pm-bot` 写成一个绑定到全局 bot 的项目 runtime pane。
- `pm-bot` 在项目内部 `5+1` 里占一个正式 bot pane。
- `pm-bot` 的 role body 已闭合；剩余问题只属于实现侧尾项。

### 误解 7：`pm-bot` 一旦被提升为项目正式角色，它的 capability conflict 就一起解决了

纠正：

- 不是。
- `pm-bot` 的 role body、tool policy、legacy residue 已经分层定稿。
- 当前剩余问题不是 role-contract 未决，而是实现侧仍有少量尾项需要保留说明。
- 这些尾项主要是缺失的 memory lesson 引用，以及全局默认 materialization 的实现残留。

### 误解 8：caller-explicit agent fallback 已经是当前可用能力

纠正：

- 不是。
- 当前 `bootstrap` 实现只有项目 `.claude/agents` 和用户级 `~/.claude/agents` 两层解析。
- 缺文件时会直接报错。
