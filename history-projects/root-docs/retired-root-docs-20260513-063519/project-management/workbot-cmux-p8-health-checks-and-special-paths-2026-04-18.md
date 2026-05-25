# [Phase 2] P8 Health checks and special paths

## 目标

稳定 `cmux_runtime_ctl.py` 的健康判定，使主链路与特殊路径在同一套机检规则下可判定：

- `pm-only` 路径可在有效条件下返回 `healthy=true`
- `5+1` 路径可在有效条件下返回 `healthy=true`
- `cmux-browser` board pane 与单工作区/选中工作区守卫进入硬门禁

## 实施内容

### 1) 运行时健康判定（全局脚本）

更新文件（仓库外全局 runtime 真相文件）：

- `/Users/busiji/.agents/skills/cmux/scripts/cmux_runtime_ctl.py`

核心改动：

- 新增 runtime 模式判定：`pm_only | five_plus_one | multi_bot | unknown`
- 新增 board guard：`runtime.board_surface_guard`
  - `five_plus_one/multi_bot`：要求且仅允许一个 `cmux-browser` 且类型为 `browser`
  - `pm_only`：guard 标记为 `required=false`，但若检测到残留 board 会判失败
- 新增 `5+1` 形状守卫：`runtime.five_plus_one_shape_guard`
  - `five_plus_one` 模式下要求五个 worker 标题齐全（`pm/dev/qa/doc/rea`）
- 将 `runtime.selected_workspace_matches_assignment` 纳入 `healthy` 强制条件
- 活跃绑定从“统一 terminal 检查”改为“worker=terminal、board=browser”的模式化检查
- watcher 改为按模式门禁：
  - `pm_only` 必须 `watcher.alive=true`
  - `five_plus_one` 仅记录 watcher 状态，不阻断 `healthy`
- 输出新增诊断字段：`runtime_mode`、`active_runtime_healthy`、`board_surfaces`

### 2) 回归测试（仓库内）

新增测试文件：

- `/Users/busiji/workbot/tests/test_cmux_runtime_ctl_p8_health_paths.py`

覆盖点：

- board slot 使用 `browser` 时活跃绑定健康
- `five_plus_one` 缺失 `cmux-browser` 时 board guard 失败
- `pm_only` 健康路径返回成功
- `five_plus_one` 健康路径在 watcher 不存活时仍可通过
- `pm_only` 在 watcher 不存活时失败
- selected workspace mismatch 失败
- single-workspace guard 失败
- `five_plus_one` board guard 失败会阻断整体健康
- `inspect_live_runtime` 真实计算路径被覆盖（非仅 print_status 聚合桩替换）：
  - `five_plus_one` 形状守卫与 board guard 的真实分支
  - `pm_only` 残留 board 的拒绝分支

### 3) 运行手册同步

更新：

- `/Users/busiji/workbot/docs/cmux-runtime-handbook.md`

`A5 健康检查` 条目新增：

- `selected_workspace_matches_assignment=true`
- `active_runtime_healthy=true`
- `board_surface_guard.healthy=true`（按 `pm-only/5+1` 语义区分）

## 验证

- `python3 -m py_compile /Users/busiji/.agents/skills/cmux/scripts/cmux_runtime_ctl.py /Users/busiji/workbot/tests/test_cmux_runtime_ctl_p8_health_paths.py`
- `pytest -q /Users/busiji/workbot/tests/test_cmux_runtime_ctl_p8_health_paths.py`
- `pytest -q /Users/busiji/workbot/tests/test_cmux_runtime_ctl_p8_health_paths.py /Users/busiji/workbot/tests/test_memory_hook_gateway_p7_mainline.py /Users/busiji/workbot/tests/test_cmux_hook_bridge.py /Users/busiji/workbot/tests/test_cmux_hook_materialization.py /Users/busiji/workbot/tests/test_memory_hook_gateway_m6_batch3_provider_switch.py`

当前复核结果（2026-04-18，实现子代理实跑）：

- `python3 -m pytest -q tests/test_cmux_runtime_ctl_p8_health_paths.py` → `10 passed in 0.04s`

## 交叉验证

> 本阶段要求：必须使用子代理完成并通过交叉验证后才能推进。

- 主审：`Helmholtz`（`019d9c7e-c6e5-79d0-8bcc-6a3f091b25d1`）→ **PASS**
  - 证据：`healthy` 公式已纳入模式化 watcher、board guard、single/selected workspace guard 与 `five_plus_one_shape_guard`。
  - 证据：确认 `pm_only` 与 `5+1` 分支语义与测试覆盖一致。
- 复审：`Bohr`（`019d9c7e-c785-73d2-994c-965452241313`）→ **PASS**
  - 证据：确认 `cmux-browser` guard 与模式守卫均进入最终健康门禁。
  - 证据：确认 P8 测试覆盖关键正反路径并通过（`10 passed`）。
- 结论：**通过**。在双路 PASS 后才执行阶段收口与后续推进。
