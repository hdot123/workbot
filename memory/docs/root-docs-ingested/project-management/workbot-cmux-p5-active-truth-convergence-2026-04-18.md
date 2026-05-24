# Workbot CMUX P5 Active Truth Convergence (2026-04-18)

## 范围与门禁

- Phase 3 卡片：`[P5] Active truth convergence`
- 硬门禁：`子代理执行 + 交叉验证 PASS 才可推进`
- 本轮记录：先接收审计子代理 `Hubble` 的 baseline 结论（`FAIL`），再按 blocker 逐项修复并复核。

## 首轮审计结论（FAIL）

`Hubble` 返回 4 个 blocker：

1. quarantine lesson `pm-bot-crawl4ai-runtime-path.md` 仍是 `status: active`，与当前 truth 冲突。
2. quarantine logs `2026-04-08.md` / `2026-04-10.md` 缺少历史横幅，且存在“当前唯一入口”口径误导。
3. quarantine project `memory/projects/workbot.md` 仍为 `status: active` 且包含过时结构叙述。
4. active runtime profile 仍引用 quarantine lesson，未指向 active replacement lesson。

## 修复落地

### Blocker 1

文件：

- `/Users/busiji/workbot/frontstage/memory-legacy-quarantine-2026-04-12/memory/lessons/pm-bot-crawl4ai-runtime-path.md`

修复：

- `status: active` -> `status: superseded`
- 增加 quarantine 历史残留声明
- 增加 active replacement lesson 跳转：
  `/Users/busiji/workbot/memory/kb/lessons/pm-bot-global-binding-and-legacy-fence.md`

### Blocker 2

文件：

- `/Users/busiji/workbot/frontstage/memory-legacy-quarantine-2026-04-12/memory/log/2026-04-08.md`
- `/Users/busiji/workbot/frontstage/memory-legacy-quarantine-2026-04-12/memory/log/2026-04-10.md`

修复：

- 文档首段新增 quarantine 历史横幅，明确“非 active truth”
- 将“唯一入口”类表述改为“当日历史口径（已废止）”

### Blocker 3

文件：

- `/Users/busiji/workbot/frontstage/memory-legacy-quarantine-2026-04-12/memory/projects/workbot.md`

修复：

- 重写为 superseded stub（`status: superseded`）
- 删除 active 结构叙述，仅保留跳转到当前真源：
  - `/Users/busiji/workbot/AGENTS.md`
  - `/Users/busiji/workbot/docs/cmux-subagent-runtime-chain.md`
  - `/Users/busiji/workbot/docs/cmux-subagent-runtime-truth-table.md`
  - `/Users/busiji/workbot/memory/kb/projects/workbot.md`
  - `/Users/busiji/workbot/memory/kb/decisions/2026-03-25-workbot-project-agents-and-runtime-surfaces.md`

### Blocker 4

文件：

- `/Users/busiji/workbot/tools/memory_hook_adapters/workbot_runtime_profile.py`

修复：

- `PROJECT_LESSON_REFS["workbot"]` 从 quarantine lesson：
  `pm-bot-crawl4ai-runtime-path.md`
  迁移到 active replacement lesson：
  `pm-bot-global-binding-and-legacy-fence.md`

## 复核命令与结果

已执行：

1. lesson superseded 与 replacement 跳转检查（Grep）
2. 两份 quarantine log 横幅与“当日历史口径，已废止”检查（Grep）
3. quarantine project stub 状态与 active truth 跳转检查（Grep）
4. runtime profile lesson 引用检查（Grep）
5. runtime profile Python 语法检查（`python3 -m py_compile`）

结果：

- 所有检查命中预期
- `pm-bot-crawl4ai-runtime-path.md` 在 runtime profile 内命中计数为 `0`
- `py_compile` 成功（无 stderr）

## 结论

- baseline：`FAIL`
- 修复后复核：`PASS`
- P5 blockers 已闭环（`FAIL -> Fix -> PASS`）
