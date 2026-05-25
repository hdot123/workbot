# cmux Runtime Truth Source Map 与事实表

本文是 `workbot` 当前 `cmux` 运行说明的 source map 与 supporting fact table。

## 文档定位

- 本文件不是主 canonical truth；主文是 `/Users/busiji/workbot/docs/cmux-subagent-runtime-chain.md`。
- 本文件负责回答“哪些文件是权威真相源、哪些文件只是辅助解释文档、发生冲突时以谁为准”。
- `/Users/busiji/workbot/docs/cmux-subagent-minimal-operating-guideline.md` 只负责最小操作口径，不负责定义真相源优先级。

## Truth Source Map

| 层级 | 文件 | 角色 | 冲突时处理 |
| --- | --- | --- | --- |
| global bot source | `/Users/busiji/.claude/agents/*.md` | 全局 bot body 定义层。 | bot body 冲突时先看这一层。 |
| repository identity source | `/Users/busiji/workbot/AGENTS.md` | 仓库级身份总表；定义仓库级身份范围、外部主线程边界和项目运行定位。 | 仓库级身份边界冲突时优先。 |
| project binding source | `/Users/busiji/workbot/.claude/agents/*.md` | 当前项目绑定层；声明 `workbot` 当前绑定/启用哪些全局 bots。 | 项目绑定集合冲突时优先于项目文档口径。 |
| runtime rule source | `/Users/busiji/.agents/skills/cmux/references/workbot/cmux-multi-pane-agent-runtime-requirements.md` | `cmux` 运行规则说明源。 | 与项目文档冲突时优先；与脚本冲突时按脚本实现修正文案。 |
| runtime rule source | `/Users/busiji/.agents/skills/cmux/SKILL.md` | `cmux` skill 层规则与默认合同说明。 | 与项目文档冲突时优先；与脚本冲突时按脚本实现修正文案。 |
| runtime implementation source | `/Users/busiji/.agents/skills/cmux/scripts/bootstrap_claude_runtime.py` | 启动、锁身份、校验的实现基线。 | 启动和锁身份行为冲突时优先。 |
| runtime implementation source | `/Users/busiji/.agents/skills/cmux/scripts/generate_cmux_assignments.py` | assignment 生成和 live 绑定回填的实现基线。 | live binding 与 title 角色冲突时优先。 |
| runtime implementation source | `/Users/busiji/.agents/skills/cmux/scripts/watch_cmux_assignments.py` | active flow 运行态约束与 watcher 校验基线。 | active-flow 约束冲突时优先。 |
| runtime implementation source | `/Users/busiji/.agents/skills/cmux/scripts/cmux_hook_state.py` | 运行态状态目录与默认 runtime artifact 路径实现基线。 | 状态路径或默认文件名冲突时优先。 |
| project canonical document | `/Users/busiji/workbot/docs/cmux-subagent-runtime-chain.md` | 当前项目面向使用者的 primary canonical truth document。 | 项目文档之间冲突时优先。 |
| project supporting map | 本文件 | truth source map 与 supporting fact table。 | 不单独压过 canonical 或底层真相源。 |
| project operating guide | `/Users/busiji/workbot/docs/cmux-subagent-minimal-operating-guideline.md` | minimal operating canonical。 | 使用口径冲突时回到 canonical 与 source map。 |

## Source-of-Truth Rule

按当前项目口径，发生冲突时按下面顺序处理：

1. `/Users/busiji/.claude/agents/*.md` 定义 global bot body。
2. `/Users/busiji/workbot/AGENTS.md` 与 `/Users/busiji/workbot/.claude/agents/*.md` 决定仓库级身份边界和 project binding 集合。
3. `cmux` 源头文档与 `cmux` 运行脚本共同决定 project runtime 规则边界。
4. `/Users/busiji/workbot/docs/cmux-subagent-runtime-chain.md` 负责把 global bot layer / project binding layer / project runtime layer 收成项目 canonical wording。
5. 本文件只做 source map 与 fact table。
6. `/Users/busiji/workbot/docs/cmux-subagent-minimal-operating-guideline.md` 只做最小操作口径。

## Fact Table

| 分类 | 主题 | 当前规则 | 来源文件 | documented | implemented | active now | 备注 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| identity-layer rule | Global bot layer | 全局 bot body 当前定义在 `~/.claude/agents/*.md`。 | `/Users/busiji/.claude/agents/pm-bot.md`<br>`/Users/busiji/.claude/agents/dev-bot.md`<br>`/Users/busiji/.claude/agents/qa-bot.md`<br>`/Users/busiji/.claude/agents/doc-bot.md`<br>`/Users/busiji/.claude/agents/rea-bot.md` | true | true | true | 这是 bot body 的全局层，不等于项目绑定层。 |
| identity-layer rule | Project binding layer | `workbot` 当前绑定全局 `pm-bot / dev-bot / qa-bot / doc-bot / rea-bot`。 | `/Users/busiji/workbot/.claude/agents/pm-bot.md`<br>`/Users/busiji/workbot/.claude/agents/dev-bot.md`<br>`/Users/busiji/workbot/.claude/agents/qa-bot.md`<br>`/Users/busiji/workbot/.claude/agents/doc-bot.md`<br>`/Users/busiji/workbot/.claude/agents/rea-bot.md` | true | true | true | 这是项目 binding 层，不等于 runtime lane 本身。 |
| repository-level rule | Current runtime carrier | `workbot` 当前唯一正式 runtime carrier 是 `cmux`。 | `/Users/busiji/workbot/AGENTS.md`<br>`/Users/busiji/.agents/skills/cmux/SKILL.md`<br>`/Users/busiji/.agents/skills/cmux/references/workbot/cmux-multi-pane-agent-runtime-requirements.md` | true | true | true | 旧 `tmux` 只剩历史残留含义。 |
| project-topology rule | Current project topology | `workbot` 当前项目内部正式运行拓扑固定为 `5+1`：五个绑定到全局 bots 的项目 runtime pane（`pm-bot`、`dev-bot`、`qa-bot`、`doc-bot`、`rea-bot`）以及 `1` 个 `cmux-browser` board pane。外部主线程不在这个 `5+1` 内。 | `/Users/busiji/workbot/docs/cmux-subagent-runtime-chain.md`<br>`/Users/busiji/workbot/docs/cmux-subagent-minimal-operating-guideline.md` | true | mixed | true | 项目文档层已完成三层模型收口；实现侧默认模板仍保留旧合同痕迹。 |
| repository-level rule | Board pane role | `cmux-browser` 只代表 board pane / board surface，不是正式 bot 身份，也不参与 agent 文件锁定。 | `/Users/busiji/workbot/AGENTS.md`<br>`/Users/busiji/.agents/skills/cmux/SKILL.md`<br>`/Users/busiji/.agents/skills/cmux/references/workbot/cmux-multi-pane-agent-runtime-requirements.md` | true | mixed | true | 当前全局实现侧仍可能通过 `empty` 占位槽承载 board surface。 |
| project-topology rule | Bound bot runtime panes | `workbot` 当前项目内部五个绑定 bot runtime pane 集合是 `pm-bot`、`dev-bot`、`qa-bot`、`doc-bot`、`rea-bot`。 | `/Users/busiji/workbot/docs/cmux-subagent-runtime-chain.md`<br>`/Users/busiji/workbot/docs/cmux-subagent-minimal-operating-guideline.md` | true | mixed | true | `pm-bot` 的 role body 已闭合；剩余只保留实现侧冲突说明。 |
| repository-level rule | Project-local agent file presence | 当前项目本地 `.claude/agents` 文件层已存在 `pm-bot`、`dev-bot`、`qa-bot`、`doc-bot`、`rea-bot`。 | `/Users/busiji/workbot/.claude/agents/pm-bot.md`<br>`/Users/busiji/workbot/.claude/agents/dev-bot.md`<br>`/Users/busiji/workbot/.claude/agents/qa-bot.md`<br>`/Users/busiji/workbot/.claude/agents/doc-bot.md`<br>`/Users/busiji/workbot/.claude/agents/rea-bot.md` | true | true | true | `pm-bot` 的 global body、project binding、project runtime 三层现已对齐；剩余是实现侧冲突，不是 role-contract 未决。 |
| project-topology rule | External main-thread role | 外部 `main-thread` 是项目外部的调度身份，不要求项目本地 agent 文件，也不应写成项目 `cmux` workspace 内的 pane。 | `/Users/busiji/workbot/docs/cmux-subagent-runtime-chain.md`<br>`/Users/busiji/workbot/docs/cmux-subagent-minimal-operating-guideline.md` | true | unknown | true | 这是项目文档层的边界口径。 |
| pm-bot role rule | `pm-bot` role body | 当前 canonical role body 是 产品分析 / 模仿产品 / 整理需求 / 采集网站内容 / benchmarking / imitation analysis。若出现 `clarification`，只应理解为产品侧需求梳理，不是主线程级裁定。 | `/Users/busiji/workbot/.claude/agents/pm-bot.md`<br>`/Users/busiji/workbot/docs/cmux-subagent-runtime-chain.md` | true | true | true | role body 不等于 tool policy，也不包含 task breakdown / scope convergence / acceptance framing / dispatch / closure / adjudication。 |
| pm-bot tool rule | `pm-bot` current tool truth | 当前工具真相跟随 active runtime/tool policy 和 implemented gates，而不是跟随 legacy collector 变体。 | `/Users/busiji/.claude/agents/pm-bot.md`<br>`/Users/busiji/.agents/skills/cmux/scripts/bootstrap_claude_runtime.py`<br>`/Users/busiji/.agents/skills/cmux/scripts/generate_cmux_assignments.py` | true | true | true | 当前实现仍把 Crawl4AI 主路径收紧到 `cj-bot`。 |
| historical residue | `pm-bot` legacy collector variant | legacy collector / Crawl4AI 长跑 / checkpoint 口径只作为 historical residue，不是当前 canonical capability contract。 | `/Users/busiji/workbot/frontstage/memory-legacy-quarantine-2026-04-12/memory/lessons/pm-bot-crawl4ai-runtime-path.md`<br>`/Users/busiji/workbot/frontstage/memory-legacy-quarantine-2026-04-12/memory/log/2026-04-08.md`<br>`/Users/busiji/workbot/frontstage/memory-legacy-quarantine-2026-04-12/memory/log/2026-04-10.md` | true | false | false | 这是历史残留，不再作为当前能力合同。 |
| runtime-level rule | Formal runtime unit | 正式运行单元是 `assignment + pane + primary terminal surface`。 | `/Users/busiji/.agents/skills/cmux/SKILL.md`<br>`/Users/busiji/.agents/skills/cmux/references/workbot/cmux-multi-pane-agent-runtime-requirements.md` | true | true | true | 不是单独 `pane`，也不是单独 `surface`。 |
| runtime-level rule | Assignment role | `assignment`、`task_text`、`continue_text` 是外部真源；`cmux` 只消费并绑定，不发明任务。 | `/Users/busiji/.agents/skills/cmux/SKILL.md`<br>`/Users/busiji/.agents/skills/cmux/scripts/bootstrap_claude_runtime.py`<br>`/Users/busiji/.agents/skills/cmux/scripts/generate_cmux_assignments.py` | true | true | true | active assignment 在启动前必须通过 `dispatch_ready` gate。 |
| runtime-level rule | Lane binding vs agent locking | `logical_target / bot_name` 承担 lane-binding 语义；`lane_identity` 承担 agent-locking 语义。 | `/Users/busiji/.agents/skills/cmux/references/workbot/cmux-multi-pane-agent-runtime-requirements.md`<br>`/Users/busiji/.agents/skills/cmux/scripts/bootstrap_claude_runtime.py`<br>`/Users/busiji/.agents/skills/cmux/scripts/generate_cmux_assignments.py` | true | true | true | 两层必须分开写。 |
| runtime-level rule | Active-flow identity constraint | 当前 active watcher 基线仍要求 `lane_identity == bot_name`。 | `/Users/busiji/.agents/skills/cmux/scripts/watch_cmux_assignments.py`<br>`/Users/busiji/.agents/skills/cmux/references/workbot/cmux-multi-pane-agent-runtime-requirements.md` | true | true | true | 这不否认分层，只是否认“自由分离”已成为常规流。 |
| runtime-level rule | Agent file resolution order | 身份锁定查找顺序是：项目 `.claude/agents/<lane_identity>.md`，然后 `~/.claude/agents/<lane_identity>.md`，找不到就报错。 | `/Users/busiji/.agents/skills/cmux/SKILL.md`<br>`/Users/busiji/.agents/skills/cmux/scripts/bootstrap_claude_runtime.py` | true | true | true | 当前实现没有第三层显式 caller-supplied agent fallback。 |
| runtime-level rule | Locked identity mechanism | 真正的身份锁定发生在启动命令 `claude --agent <lane_identity>`。 | `/Users/busiji/.agents/skills/cmux/SKILL.md`<br>`/Users/busiji/.agents/skills/cmux/scripts/bootstrap_claude_runtime.py` | true | true | true | 不是靠 title 自动生成，也不是靠会话内粘贴身份文本。 |
| runtime-level rule | Title role | `pane title` 与 `surface title` 都只是 runtime lookup aid。 | `/Users/busiji/.agents/skills/cmux/SKILL.md`<br>`/Users/busiji/.agents/skills/cmux/scripts/generate_cmux_assignments.py`<br>`/Users/busiji/.agents/skills/cmux/references/workbot/cmux-multi-pane-agent-runtime-requirements.md` | true | true | true | title 可参与 live lookup 和回填，但不生成身份真相。 |
| runtime-level rule | Launch chain | `bootstrap_claude_runtime.py` 会建拓扑、同步 assignment、校验 `dispatch_ready`、解析 identity file，再执行 `claude --agent <lane_identity>`。 | `/Users/busiji/.agents/skills/cmux/scripts/bootstrap_claude_runtime.py`<br>`/Users/busiji/.agents/skills/cmux/scripts/generate_cmux_assignments.py` | true | true | true | 当前正式路径是 startup-time locking。 |
| runtime-level rule | Launch verification chain | 启动后先等 Claude ready，再校验这是原生 Claude agent 会话，而且没有掉进临时身份流。 | `/Users/busiji/.agents/skills/cmux/SKILL.md`<br>`/Users/busiji/.agents/skills/cmux/scripts/bootstrap_claude_runtime.py` | true | true | true | 缺少原生会话头或出现临时身份提示时应失败。 |
| runtime-level rule | Runtime artifact directory | 当项目存在 `/artifacts` 时，默认运行时目录是 `/Users/busiji/workbot/artifacts/cmux-runtime/`。 | `/Users/busiji/.agents/skills/cmux/scripts/cmux_hook_state.py` | false | true | true | 这是脚本实现事实。 |
| control-chain rule | `pm-bot` assignment and dispatch | `pm-bot` 的 assignment 真源仍在外部，`dispatch_owner` 仍是 `codex`。 | `/Users/busiji/.agents/skills/cmux/SKILL.md`<br>`/Users/busiji/.agents/skills/cmux/scripts/generate_cmux_assignments.py`<br>`/Users/busiji/.agents/skills/cmux/scripts/watch_cmux_assignments.py` | true | true | true | `pm-bot` 不是独立 dispatch owner。 |
| control-chain rule | `pm-bot` watcher/reminder/continue/takeover model | 当前 active truth 是 `shared core + pm-specific special cases`。 | `/Users/busiji/.agents/skills/cmux/scripts/bootstrap_claude_runtime.py`<br>`/Users/busiji/.agents/skills/cmux/scripts/watch_cmux_assignments.py`<br>`/Users/busiji/workbot/docs/cmux-subagent-runtime-chain.md` | true | true | true | 不是完整独立控制链。 |
| control-chain rule | Shared runtime state files | shared state 仍走 `hook-state.json`、`watch_cmux_assignments.pid`、`watch_cmux_assignments.log` 和 shared `cmux notify`。 | `/Users/busiji/.agents/skills/cmux/scripts/cmux_hook_state.py`<br>`/Users/busiji/.agents/skills/cmux/scripts/bootstrap_claude_runtime.py`<br>`/Users/busiji/.agents/skills/cmux/scripts/watch_cmux_assignments.py` | true | true | true | 这是 shared core 的主体。 |
| control-chain rule | `pm-bot` special-case paths | `pm-bot` special cases 当前包括 `pm-bot-watch.json`、single-bot bootstrap support、pm-specific continue/correction 分支。 | `/Users/busiji/.agents/skills/cmux/scripts/cmux_hook_state.py`<br>`/Users/busiji/.agents/skills/cmux/scripts/bootstrap_claude_runtime.py`<br>`/Users/busiji/.agents/skills/cmux/scripts/watch_cmux_assignments.py` | true | true | true | 特判存在，但仍嵌在 shared core 上。 |
| governance rule | A7 local writeback | A7 本地回写由 `cmux_finish_cycle.py` 执行，必须写回 task-list / `ce-sync-plan`，并生成 finish receipt。 | `/Users/busiji/.agents/skills/cmux/scripts/cmux_finish_cycle.py`<br>`/Users/busiji/artifacts/cmux-runtime/cmux-finish-receipts.jsonl` | true | true | true | normal path 结构化回写优先，forensic 仅显式回退。 |
| governance rule | A8 commander-only CE sync | 正式 CE 生命周期评论仍由 commander 执行；自动收尾默认不替代 commander。 | `/Users/busiji/workbot/docs/a1-a9-session-protocol.md`<br>`/Users/busiji/.agents/skills/cmux/scripts/cmux_finish_cycle.py` | true | true | true | A7 完成不等于 A8 已完成。 |
| governance rule | A9 exit/next-session branching | A9 必须在 A7（必要时 A8）后执行，按“有下一会话任务/无下一会话任务”分支收口。 | `/Users/busiji/workbot/docs/a1-a9-session-protocol.md`<br>`/Users/busiji/workbot/docs/cmux-runtime-handbook.md` | true | true | true | 不允许跳过 A7 直接进入 A9。 |
| legacy reminder residue | `CODEX_THREAD_ID` / doorbell chain | 旧 `CODEX_THREAD_ID` / doorbell / monitor-thread 提醒链只属于 legacy residue，不是当前 active `cmux` reminder truth。 | `/Users/busiji/workbot/frontstage/memory-legacy-quarantine-2026-04-12/memory/log/2026-03-27.md` | true | false | false | 当前 active 提醒链是 shared `cmux notify`。 |
| implementation-tail note | `pm-bot` remaining implementation tail | watcher Crawl4AI residue 与 `continue_text` bookkeeping mismatch 已在本轮实现补尾中收掉；当前只需保留 memory hook 仍引用缺失 lesson，以及全局默认 materialization 的实现残留。 | `/Users/busiji/.agents/skills/cmux/scripts/bootstrap_claude_runtime.py`<br>`/Users/busiji/.agents/skills/cmux/scripts/generate_cmux_assignments.py`<br>`/Users/busiji/workbot/tools/memory_hook_gateway.py` | true | true | true | 不要再把已收掉的 watcher/continue 问题列为 remaining open conflict。 |
| documented-but-unimplemented | Caller-explicit fallback | caller-explicit agent fallback 不属于当前已实现能力。 | `/Users/busiji/.agents/skills/cmux/SKILL.md`<br>`/Users/busiji/.agents/skills/cmux/scripts/bootstrap_claude_runtime.py` | true | false | false | 当前文档只把它记为旧文案提及过的未实现能力。 |
| runtime-boundary note | Global default leakage | 全局 skill/bootstrap 默认模板仍可能露出 `pm-bot / dev-bot / qa-bot / doc-bot / rea-bot + empty`；对 `workbot` 而言，这只代表实现侧默认合同与 board placeholder 残留，不再构成把 `pm-bot` 降格为默认泄漏的依据。 | `/Users/busiji/.agents/skills/cmux/SKILL.md`<br>`/Users/busiji/.agents/skills/cmux/scripts/bootstrap_claude_runtime.py`<br>`/Users/busiji/workbot/docs/cmux-subagent-runtime-chain.md` | true | true | true | 当前项目 truth 是 `pm-bot / dev-bot / qa-bot / doc-bot / rea-bot + cmux-browser`，外部主线程在工作区外。 |
| project-boundary note | `pm-bot` role/tool/legacy boundary | `pm-bot` 的 role body 已闭合，tool policy 跟随 active runtime/tool policy，legacy collector variant 只属于历史残留。不要把这层定稿误写成“实现已经完全统一”。 | `/Users/busiji/workbot/docs/cmux-subagent-runtime-chain.md`<br>`/Users/busiji/.claude/agents/pm-bot.md` | true | mixed | true | 当前仍需单列的只是实现尾项：缺失的 memory lesson 引用，以及全局默认 materialization 的实现残留。 |
| historical residue | tmux status | 旧 `tmux` 规则不是当前 runtime truth，只能视为历史残留。 | `/Users/busiji/workbot/AGENTS.md` | true | true | true | `tmux` 不再作为当前 `workbot` 运行真相来源。 |

## 当前可直接复用的判断口径

- 先问身份范围：回到 `/Users/busiji/workbot/AGENTS.md` 与项目 `.claude/agents`。
- 再问运行规则：回到 `cmux` 源头文档和运行脚本。
- 再问用户侧定稿口径：回到 `/Users/busiji/workbot/docs/cmux-subagent-runtime-chain.md`。
- 只问最小怎么操作：回到 `/Users/busiji/workbot/docs/cmux-subagent-minimal-operating-guideline.md`。
