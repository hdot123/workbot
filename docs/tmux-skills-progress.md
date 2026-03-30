# tmux-skills 开发进度

更新时间：2026-03-29（Asia/Shanghai）

## 当前口径

`tmux-skills` 的正式口径已经改为：

- Codex 提供 `pane_count`
- Codex 提供 `pane_titles`
- `tmux-skills` 在前台 tmux 中生成这些 pane
- `tmux-skills` 在 pane 停止时向 `CODEX_THREAD_ID` 绑定 thread 的 owner 窗口报告

它不再被定义为 runtime skill，也不再以任何旧接管校验作为完成标准。

## 当前完成情况

### 已完成

- `tmux-skills` 的输入权属于 Codex，pane 数量和标题由调用方提供
- `tmux-skills` 的执行目标是前台 attached 的 `formal-session`
- `tmux-skills` 的产出目标是 pane 数量到位、标题到位
- `tmux-skills` 的持续职责是 pane 状态监控与停止上报
- `CODEX_THREAD_ID` 仍然是上报目标的唯一正式线程入口，并且必须指向唯一的 Codex app thread id
- delivery 已收口到常驻 window IPC bridge，不再通过 `codex exec resume` 或本地 `session_index.jsonl` 解释目标线程
- 公开主链已切到 `cleanup -> env -> topology -> pane-labeling -> ledger -> watcher`
- 旧的接管相关公开入口已下线或改为兼容弃用提示
- watcher 已改成只上报 `pane_stopped` / `pane_unreachable` / `session_detached`
- 每次新的 pane 创建前都会先清理旧 watcher、旧 runtime ledger、旧 issues、旧 handoff 数据和旧 watcher 日志

## 当前状态

实现已经按最终口径落地完成：

1. 接收 Codex 提供的 `pane_count`
2. 接收 Codex 提供的 `pane_titles`
3. 在前台 tmux 中生成 pane 并设置标题
4. 在 pane 停止时把状态报告给 `CODEX_THREAD_ID` 绑定 thread 的 owner 窗口

## 当前阶段结论

**`tmux-skills` 已完成向“前台 tmux pane 生成 + 停止上报”口径的改造。**
