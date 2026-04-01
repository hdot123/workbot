---
type: [KB:DECISION]
title: "Workbot 项目级 Agents 与正式运行面规范"
created: 2026-03-25
updated: 2026-03-30
last_verified: 2026-03-30
source: Manual
confidence: high
tags: [workbot, claude, agents, runtime, runtime-surfaces, tmux-to, bailian, qwen3.5-plus]
related: [workbot, 2026-03-04-4-bot-workflow-planning, 2026-03-02-bailian-coding-plan-models]
version: v1.7
status: active
---

# Workbot 项目级 Agents 与正式运行面规范

## 结论

- `dev-bot` 与 `qa-bot` 的项目级 agent 真源固定在 `/Users/busiji/workbot/.claude/agents/`
- `doc-bot` 的项目级 agent 真源也固定在 `/Users/busiji/workbot/.claude/agents/`
- 当前项目不再把 `/Users/busiji/workbot/agents/` 作为 `dev-bot` / `qa-bot` / `doc-bot` 的运行真源
- `dev-bot`、`qa-bot` 与 `doc-bot` 当前主模型统一固定为 `qwen3.5-plus`
- 百炼连接参数放在项目本地 Claude settings 层，不放在 agent markdown 正文中
- tmux pane / window / slot 只是当前 attached session 内的临时工作分区或临时标签，不是项目级 bot 身份对象
- tmux 正式运行面必须收口为一个前台 attached 的 `formal-session`
- `task` / `monitor` / `runtime` 只表示同一个 `formal-session` 内的临时工作分区或临时 slot，不再各自拥有独立 formal session

## 真源定义

### 项目级 Agents

- `/Users/busiji/workbot/.claude/agents/dev-bot.md`
- `/Users/busiji/workbot/.claude/agents/qa-bot.md`
- `/Users/busiji/workbot/.claude/agents/doc-bot.md`

这两个文件是当前项目的 Claude project agents 真源，用于 Claude 会话直接加载。

### 共享角色库

- `/Users/busiji/workbot/agents/`

该目录仍然保留共享角色库职责，但不再承载 `dev-bot` / `qa-bot` 的当前项目运行真源。

## 模型规范

### 当前固定模型

- `dev-bot`：`qwen3.5-plus`
- `qa-bot`：`qwen3.5-plus`
- `doc-bot`：`qwen3.5-plus`

### 配置原则

- agent 文件中写什么模型，运行时就应当使用什么模型
- 不再依赖 `sonnet -> qwen3.5-plus` 这类额外映射来表达当前项目的主模型
- 百炼连接参数属于 settings/env 层，不属于 agent frontmatter 的职责

## Claude Settings 规范

- 当前项目的百炼连接参数放在 `/Users/busiji/workbot/.claude/settings.local.json`
- 该文件用于项目本地连接配置，不作为共享知识文件引用
- 记忆层只记录配置边界，不记录敏感 token 明文

## tmux 运行规范

### 命名规则

- 正式 runtime 只承认一个 formal session，默认名为 `formal-session`
- 接管或启动前，必须先获取当前 tmux 的 `session name`、`window id`、`window title`、`pane id` 与 `pane title`
- 当前 tmux 拓扑、pane id、pane title 与 slot 分配都只是当次 attached runtime 的临时元数据
- bot 绑定关系必须可见化，至少要能明确回答：当前 `window id` 是多少、当前 `window title` 是什么、当前 pane 当前承载了什么工作
- pane 标题只用于当前 runtime 的局部辨识，不得被文档固化为项目级身份名、稳定对象名或长期语义键
- 项目文档不得把 pane 标签与身份名拼接成长期存在的对象名
- `tmux-skills` 不再定义任何长期对象名；它只负责 tmux pane 生成、标题设置和 pane 停止上报

### 运行规则

- 项目级 agent 真源只在 `.claude/agents/`，不在 tmux pane 标题、pane 编号或 pane 拓扑中表达
- 某个 pane 是否承载某个项目级 agent，属于当前 runtime 的会话态事实，不得写成项目级长期命名对象
- 不允许把 shell pane、历史输出或旧拓扑标签误判为当前 runtime 已完成身份接管
- 不允许把临时 pane 标签文档化为稳定对象名
- 修改 `.claude/agents/` 或 `.claude/settings.local.json` 后，必须重启对应 Claude 会话或重新加载配置
- tmux 正式运行面必须在前台
- detached session、后台残留 session、无人可见的 tmux 会话不算有效运行面
- 若当前前台 tmux 已关闭，则当天 `formal-session` 视为未运行

### tmux-skills Pane 生成与监控流程

`tmux-skills` 的职责不再是处理任何会话身份接管，而是：

- 接收 Codex 提供的 `pane_count`
- 接收 Codex 提供的 `pane_titles`
- 在前台 `formal-session` 中生成对应 pane
- 设置 pane 标题
- 在后续监控 pane 状态
- pane 停止后通过 `CODEX_THREAD_ID` 报告给对应的 Codex app thread

#### 阶段 A：启动前清场（只执行一次）

- 收到 tmux pane 生成指令后，先确认当前工作目录是 `/Users/busiji/workbot`
- 先查询是否存在 tmux 会话
- 若发现后台运行的 tmux（`attached=0`），全部杀掉
- 若发现前台运行的 tmux（`attached>=1`），先接管该前台会话，不重复创建新会话
- `tbot` can be used as a bootstrap quick entry; before running it clear out existing sessions so that the single formal runtime session is not yet polluted.
- 只有在“无后台残留 + 前台可见”同时满足后，才进入下一阶段

#### 阶段 B：前台会话准备（必须在可见终端完成）

- 若没有任何 tmux 会话，则在普通可见终端创建前台会话（正式会话名固定为 `formal-session`）
- When `tbot` is used for bootstrapping, the goal state is temporarily having only the bootstrap pane with `attached=1`; once the single formal runtime session is available, shut down the `tbot` session and switch to `formal-session`.
- 已验证：在 `Terminal.app` 中通过 `do script` 重复裸执行 `tbot` 会让同一个 `tbot` session` 出现 `attached=2`，因此 bootstrap `tbot` 必须在 `formal-session` 就绪后关闭。
- 一旦 `attached>1`，视为污染，必须回到阶段 A 清场，不得继续。

#### 阶段 C：Codex 调用 tmux-skills 生成 pane

- Codex 显式传入：
  - `pane_count`
  - `pane_titles`
- `tmux-skills` 只负责：
  - 生成或收缩 pane 数量
  - 设置 pane 标题
  - 允许在 pane 内直接启动 `claude`
  - 当 pane 标题命中项目 `.claude/agents/<name>.md` 时，启动 `claude --agent <name>`
  - 输出 pane 的 `target` 与 `pane_title`
- `tmux-skills` 不负责：
  - 为不存在于项目 `.claude/agents/` 的名字启动 `claude --agent`
  - agent 定义生成或 prompt 编排
  - prompt 注入
  - scene 校验

#### 阶段 D：停止监控与上报

- pane 生成完成后，`tmux-skills` 只监控 pane 状态
- watcher 只能在 pane 创建、`claude` 启动准备、项目 agent 白名单匹配后的 `claude --agent` 启动准备完成后才开始扫描和放第一条消息
- 监控目标只包含当前 formal session 中由 Codex 要求生成的 pane
- 任一 pane 停止时，`tmux-skills` 必须把停止事件发送到 `CODEX_THREAD_ID`
- `CODEX_THREAD_ID` 在 tmux 门铃链路中的语义固定为 Codex app thread id，不再允许复用为本地 CLI session id
- 停止事件的 delivery 由常驻 window IPC bridge 执行；watcher 只负责观察、记录和落队列
- 停止事件不再通过 `codex exec resume` 投递
- 停止事件至少包含：
  - `target`
  - `pane_title`
  - `state`

## 每日任务与监控线程规范

### 启用门槛

- 任务线程与监控线程分离不是默认起点，而是完成前置准备后的正式运行模式
- 未完成前置准备前，不得把当天会话认定为正式的每日任务线程和每日监控线程
- 前置准备不足时，只允许临时排查或临时协作，不允许作为当日标准运行链路

### 任务线程

- 每天必须新建一个任务会话线程
- 当天所有任务下发、bot 协作、进度汇报、结果汇总都只走当天任务线程
- 任务线程是当天任务事实的唯一线程真源

### 监控线程

- 每天必须再新建一个监控会话线程
- 监控线程只监控当天任务线程
- 监控线程只承接异常、告警、监控状态，不承接任务本身
- 监控线程是当天监控事实的唯一线程真源
- tmux 门铃系统不再维护 monitor 专用 thread 变量；负责监控的临时工作 pane 或临时 slot 必须在启动时显式注入唯一的 `CODEX_THREAD_ID`
- 上述 `CODEX_THREAD_ID` 必须是 monitor 对应的 Codex app thread id

## 每日单 formal tmux 会话规范

### 正式运行面

- 每天最多承认一个正式 tmux 会话，默认名为 `formal-session`
- `formal-session` 只绑定当天正式 runtime，不再拆分为独立 task formal session 与 monitor formal session
- `task` / `monitor` 与其他工作 pane 只作为 `formal-session` 内的临时工作分区或临时 slot 存在
- Codex 调用 `tmux-skills` 生成的 pane 只在 `formal-session` 当前拓扑允许的 pane 中执行
- `formal-session` 必须是当前前台可见会话，不允许在后台长期运行
- detached session、bootstrap `tbot` 和其他临时会话都不算正式运行面

## tmux-to 分流规范

- `tmux-to` 正常任务流只允许发送到当天任务线程
- `tmux-to` 监控、异常、告警流只允许发送到当天监控线程
- 不允许把异常信息打回任务线程
- 不允许把任务执行结果打到监控线程
- 不允许一个线程同时承担任务流和监控流
- 对 tmux 门铃链路而言，线程分流通过 monitor 临时工作 pane 或临时 slot 启动时注入的 `CODEX_THREAD_ID` 实现，不再依赖多个候选环境变量回退
- 对 tmux handoff delivery 而言，消息进入监控线程时应当以 owner window 的成功响应作为接收确认

## 每日启动流程

### 前置准备清单

以下项目全部准备完成后，才允许启用任务/监控线程分流与单 formal-session 正式运行面：

1. 当天任务范围已经收口，并且唯一状态源已经明确
2. 当天任务面板已经写好，并明确 `dev-bot` / `qa-bot` 的分工
3. 当天任务线程 ID 已创建
4. 当天监控线程 ID 已创建
5. `tmux-to` 任务流与监控流的目标线程已经明确
6. 当天日报文件已经建立或已预留写入位置
7. 已确认不会继续沿用前一天或其他临时会话作为正式任务会话

只有以上 7 项完成，才进入下面的正式启动流程。

1. 新建当天任务线程
2. 新建当天监控线程
3. 创建或接管唯一的 `formal-session`
4. 由 Codex 调用 `tmux-skills`，传入当天需要的 `pane_count` 与 `pane_titles`
5. 由 `tmux-skills` 在 `formal-session` 内生成对应 pane 并设置标题
6. 在 monitor 临时工作 pane 或临时 slot 中启动对 `formal-session` 的监控，并注入当天监控线程的 `CODEX_THREAD_ID`
7. 后续所有 `tmux-to` 消息按任务流与监控流严格分流

## 每日收口流程

- 任务线程负责沉淀当天任务结果、bot 协作结论与最终汇总
- 监控线程负责沉淀当天异常、告警、人工介入与监控结论
- 每日日报必须引用当天任务线程和监控线程的事实结果，而不是引用固定会话名

## 原因

- 如果把 tmux 临时标签误写成长期对象名，后续执行和记忆层就容易再次把临时工作分区误读成身份对象
- 把项目级运行身份收口到 `.claude/agents/` 后，Claude 加载链最直接
- 把真实模型直接写入 agent frontmatter 后，排障时不需要再反查别名映射

## 后续约束

- 若未来切换品牌或模型，优先修改项目级 agent 与 settings 层，不新增第二真源
- 若新增新的项目级 bot，应复用同样规则：项目级 agent 真源固定，tmux 侧只表达当前会话期的临时工作分区与临时标签
- 若新增新的每日任务流，必须沿用“任务/监控线程分流 + 单 formal tmux 会话 + pane / slot 分层 + `tmux-to` 分流”模型，不得回退为多 formal session 混用

## 日报规则

- 从 2026-03-25 起，`dev-bot` 与 `qa-bot` 的每日任务进度必须强制写入 `workspace/memory/log/` 的对应日期日志
- 日报至少包含：
  - 当日 bot 身份
  - 已完成事项
  - 阻断项或风险项
  - 当日结论
  - 可追溯证据来源
- 日报属于事实层，只进入 `memory/log/`
- 若日报沉淀出长期规则或固定流程，再提炼进入 `memory/kb/**`
