# workbot cmux P12-rest 交付: commander docs/truth mapping

日期: 2026-04-18  
范围: `P12-rest`

## 阶段硬门禁

> 本阶段要求：必须使用子代理完成任务，并且必须完成双路交叉验证；只有交叉验证结论为 **PASS** 后，才允许进入下一步。

## 目标

完成 commander 文档层 `P12-rest`：

- 将 `A1-A9` 语义映射到当前 `cmux 5+1` 实现链。
- 将 hook-contract / runtime chain 与当前脚本行为对齐。
- 清理并澄清历史漂移口径（`lookme/tmux`、`empty`、pane transcript normal-path 依赖等）。

## 本次文档改动

### 1) 更新 canonical truth 文档

文件：

- `/Users/busiji/workbot/docs/cmux-subagent-runtime-chain.md`

新增/调整：

- 新增 `A1-A9` 到 `cmux 5+1` 的逐阶段映射表（A1..A9 对应脚本与产物）。
- 新增 `P12-rest` 漂移口径澄清：
  - `cmux` assignment 真源路径收敛到 `workspace/artifacts/cmux-runtime/cmux-assignment.json`
  - `A7` normal path 回写改为结构化来源优先
  - `cmux-browser` 与 `empty` 的身份边界澄清

### 2) 更新 runtime 执行手册

文件：

- `/Users/busiji/workbot/docs/cmux-runtime-handbook.md`

新增/调整：

- 从 `A0-A6` 叙述改写为 `A1-A9` 全链路执行手册。
- 明确 hook 四事件与 `missing_hook_context` fail-close（返回码 `2`）合同。
- 明确 watcher/consumer-state/finish-cycle 的运行链路与产物。
- 明确 `A7` 回写 normal path 结构化真源优先，forensic 仅兜底。
- 明确 `A8` commander 生命周期职责边界。

## 关键口径（本次定稿）

1. `A1-A9` 是 commander 语义层；当前实现层映射以 `cmux` 脚本和 `5+1` 拓扑为准。  
2. Hook 合同是运行时硬门禁，不满足上下文就 fail-close，不允许静默成功。  
3. `A7` 本地回写 normal path 不再依赖 pane transcript/evidence line。  
4. `cmux-browser` 是 board pane，不是正式 bot 身份；`empty` 不是对外身份真相。  

## 交付证据

- 修改文件：
  - `/Users/busiji/workbot/docs/cmux-subagent-runtime-chain.md`
  - `/Users/busiji/workbot/docs/cmux-runtime-handbook.md`
  - `/Users/busiji/workbot/docs/project-management/workbot-cmux-p12-rest-commander-docs-truth-mapping-2026-04-18.md`
- 证据点：
  - 文档内新增 `A1-A9`→`cmux 5+1` 映射表
  - 文档内新增 hook-contract fail-close 条款
  - 文档内新增 normal-path 结构化回写条款

## 子代理与交叉验证状态

- 硬门禁文本已写入本交付文档。  
- 本阶段执行采用“实现子代理 + 独立审计子代理”双路模型，结论如下：
  - Route-1（实现与自检）：`Hooke` -> **PASS**
  - Route-2（独立复核）：`Mill` -> **PASS**
- 双路均为 **PASS**，允许进入后续阶段动作（卡片回写与 Git 交付）。

## 双路交叉验证证据（PASS）

### Route-1: Hooke（实现子代理）PASS

- 结论：完成 P12-rest 文档落地，且仅改动指定文档范围。
- 关键命中：
  - `cmux-subagent-runtime-chain.md` 新增 `A1-A9` 到 `cmux 5+1` 映射节（`L380+`）。
  - `cmux-runtime-handbook.md` 新增 `A1-A9` 执行映射、`missing_hook_context` fail-close、`A7/A8` 治理条款（`L22/L65/L103/L115+`）。
  - 本交付文档写入硬门禁文本与交付范围（`L1/L4/L6+`）。
- 自检命令（子代理已执行）：
  - `rg -n 'A1-A9 语义到 .*cmux 5\\+1.*实现映射|P12-rest 漂移口径澄清|normal path 证据来源' docs/cmux-subagent-runtime-chain.md`
  - `rg -n 'A1-A9 执行映射|missing_hook_context|A7 本地治理回写|A8 CE 生命周期同步|漂移口径澄清' docs/cmux-runtime-handbook.md`

### Route-2: Mill（独立审计子代理）PASS

- 结论：未发现剩余漂移 blocker，Cross-Verification Verdict = **PASS**。
- 关键命中：
  - `AGENTS.md` 的 `cmux 5+1`、主线程边界、legacy tmux residue 口径一致（`L78/L79/L87/L90/L91`）。
  - `cmux-runtime-handbook.md` 的 `A1-A9/A7/A8/A9` 与 normal-path 条款一致（`L22/L101/L110/L128/L131`）。
  - `cmux-subagent-runtime-chain.md` 的 assignment 真源与 A7/A8/A9 映射一致（`L380/L387/L392/L398/L399`）。
  - lookme/tmux 文档均有 Legacy 栅栏（`lookme-runtime-runbook.md#L3` 等）。
- 独立复核命令（子代理已执行）：
  - `rg -n 'cmux|formal-session|task thread|monitor thread|tmux-to|CODEX_THREAD_ID' AGENTS.md`
  - `rg -n 'A1-A9|A7|A8|A9|cmux-assignment.json|normal path' docs/cmux-runtime-handbook.md docs/cmux-subagent-runtime-chain.md docs/cmux-subagent-runtime-truth-table.md docs/a1-a9-session-protocol.md docs/a1-a9-session-brief.md`
  - `rg -n 'Legacy|historical|not current official path|lookme|formal-session|4-pane' docs/lookme-runtime-runbook.md docs/lookme-anchored-task-flow.md docs/lookme-runtime-cheatsheet.md docs/tmux-docs-index.md`
