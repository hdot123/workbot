# tmux 文档索引（Legacy）

**更新时间**: 2026-03-31  
**适用范围**: `/Users/busiji/workbot/skills/tmux-skills/` 当前代码实现

---

## 1. 历史口径入口（非当前正式执行口径）

以下文档仅用于追溯历史 `tmux` 实现，不再作为 `workbot` 当前正式运行口径：

1. `/Users/busiji/workbot/skills/tmux-skills/SKILL.md`
2. `/Users/busiji/workbot/docs/tmux-skills-design.md`
3. `/Users/busiji/workbot/docs/tmux-skills-duty-boundary.md`

`workbot` 当前正式执行口径请改用：

1. `/Users/busiji/workbot/AGENTS.md`
2. `/Users/busiji/workbot/docs/cmux-runtime-handbook.md`
3. `/Users/busiji/workbot/docs/cmux-subagent-runtime-chain.md`

---

## 2. 文档分层

### 2.1 当前有效文档

这些文档用于描述**当前代码正在执行的逻辑**：

- `skills/tmux-skills/SKILL.md`
- `docs/tmux-skills-design.md`
- `docs/tmux-skills-duty-boundary.md`
- `docs/tmux-skills-progress.md`

### 2.2 历史阶段文档

这些文档用于保留治理过程、阶段设计、验收记录和历史决策，不再作为当前实现的单一真源：

- `docs/tmux-runtime-governance-phase0-analysis.md`
- `docs/tmux-runtime-governance-phase1-design.md`
- `docs/tmux-runtime-governance-phase2-implementation.md`
- `docs/tmux-runtime-governance-phase3-recovery.md`
- `docs/tmux-runtime-governance-phase4-registry-design.md`
- `docs/tmux-runtime-governance-phase5-implementation.md`
- `docs/tmux-runtime-governance-phase6-audit-v2.md`
- `docs/tmux-runtime-governance-phase6-final.md`
- `docs/tmux-runtime-governance-migration-guide.md`

这些文档允许保留“当时的阶段目标 / 审计结果 / 设计假设”，但如果与当前代码冲突，必须额外注明“当前代码现状”。

---

## 3. 当前核心实现口径

### 3.1 历史 tmux 残留处理

当前代码实现的 fresh start 主链，会先：

- 检测当前 tmux sessions
- 杀掉已有 tmux sessions
- 验证 tmux session 已清空
- 清理 watcher、ledger、issues、handoff/delivery 队列与日志
- unset tmux 环境里的 `CODEX_THREAD_ID`

bridge 当前不在 cleanup 中显式 kill；现状由 PID 文件检查与单实例锁避免重复实例。

### 3.2 watcher / delivery / bridge 口径

- `start_formal_runtime_chain.py` 是当前主链直达入口
- `run_script.py` 是当前公开调度入口
- 注册表中的 `public` 条目是否能直接 `python3 script.py`，当前代码还取决于各脚本顶部的 runtime enforcement
- tmux 原生命令只提供 pane 原始状态与可抓取屏幕内容
- watcher 不发明规则，只执行固定规则
- `round` 表示对全部 watcher targets 的一次完整扫描
- `pane_stopped` 固定规则：
  - `pane_dead > 0`
  - 或首次采样建立 baseline 且观察到有效输出变化后，同一个 pane 连续 `3` 轮最近 `5` 行输出 hash 不变
- watcher 不边扫边放；必须先完成整轮扫描，再决定这一轮如何下放
- 同一时刻最多只允许向下游放 `1` 条消息
- `deliver_tmux_handoff_notification.py` 只负责确保 bridge 常驻；如果输入事件尚未落到 queue，会先写入 queue
- `tmux_handoff_app_bridge.py` 按顺序处理 queue 文件，并通过 window IPC 投递

---

## 4. 维护规则

- 修改当前实现时，优先更新：
  - `SKILL.md`
  - `tmux-skills-design.md`
  - `tmux-skills-duty-boundary.md`
- 如果治理阶段文档与当前代码出现偏差：
  - 不要直接假装历史文档当时就是现在这样
  - 应补充“当前代码现状”说明
  - 或明确标注为历史参考

---

## 5. 一句话结论

`tmux-skills` 当前的正式真源是技能文档和当前设计文档；治理阶段文档保留历史价值，但不再单独决定当前代码口径。
