# tmux-skills 开发进度

> 当前文档角色：现行进度摘要。
> 当前实现细节请结合 `/Users/busiji/workbot/docs/tmux-docs-index.md`、`SKILL.md` 和 `tmux-skills-design.md` 一起阅读。

更新时间：2026-03-31（Asia/Shanghai）

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
- delivery 当前由 `deliver_tmux_handoff_notification.py` 确保 `tmux_handoff_app_bridge.py` 常驻，再由 bridge 通过 window IPC 投递；不再通过 `codex exec resume` 或本地 `session_index.jsonl` 解释目标线程
- 公开主链已切到 `cleanup -> env -> topology -> pane-labeling -> ledger -> watcher`
- `start_formal_runtime_chain.py` 是主链直达入口，`run_script.py` 是公开调度入口
- 注册表中的 `public` 条目是否能直接 `python3 script.py`，当前代码还取决于各脚本顶部的 runtime enforcement
- 旧的接管相关公开入口已下线或改为兼容弃用提示
- watcher 已改成只上报 `pane_stopped` / `pane_unreachable` / `session_detached`
- 每次新的 pane 创建前都会先清理旧 watcher、旧 runtime ledger、旧 issues、旧 handoff/delivery 数据与日志，并 unset tmux 环境中的 `CODEX_THREAD_ID`
- watcher 当前采用整轮扫描后再下放消息的方式；同一时刻最多只向下游放 `1` 条消息
- bridge 当前不在 cleanup 中显式 kill；现状由 PID 文件检查和单实例锁避免重复实例

## 当前状态

实现已经按最终口径落地完成：

1. 接收 Codex 提供的 `pane_count`
2. 接收 Codex 提供的 `pane_titles`
3. 在前台 tmux 中生成 pane 并设置标题
4. 在 pane 停止时把状态报告给 `CODEX_THREAD_ID` 绑定 thread 的 owner 窗口

当前真源文档为：

- `skills/tmux-skills/SKILL.md`
- `docs/tmux-skills-design.md`
- `docs/tmux-skills-duty-boundary.md`
- `docs/tmux-docs-index.md`

## 当前阶段结论

**`tmux-skills` 已完成向“前台 tmux pane 生成 + 停止上报”口径的改造。**
