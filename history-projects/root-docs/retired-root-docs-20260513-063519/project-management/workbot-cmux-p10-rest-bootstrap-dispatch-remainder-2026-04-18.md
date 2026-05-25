# workbot cmux P10-rest 交付: Bootstrap and dispatch remainder

日期: 2026-04-18

## 阶段硬门禁

> 本阶段要求：必须使用子代理完成任务，并且必须完成双路交叉验证；只有交叉验证结论为 **PASS** 后，才允许进入下一步。

## 目标

完成 `P10-rest` 剩余收口：

- 将 `runtime-launch-manifest` 与 per-bot `*-smoke-report` 纳入正式验收门禁。
- 收紧 dispatch contract 与 runtime truth 的前置一致性，避免“可启动但运行期才被 watcher 拒绝”的漂移。
- 补齐仓库侧回归测试和文档口径。

## 本次改动（仓库内）

### 1) Formal acceptance 门禁补齐

更新：

- `/Users/busiji/workbot/workspace/tools/cmux_phase_readiness.py`

新增能力：

- `expected_runtime_bot_names(...)`：从 `cmux-assignment.json / pm-bot-watch.json` 解析当前 active bot 集合。
- `collect_runtime_launch_manifest_problems(...)`：检查 `runtime-launch-manifest-*.json` 的存在性与关键字段有效性。
- `collect_startup_smoke_report_problems(...)`：检查 `*-smoke-report.json` 的存在性与状态约束（含 crawl4ai 场景必须 `passed`）。
- 上述问题集合已并入 `implemented/entry_ready` 判定，不再仅停留在文档口径。

### 2) 读路径合同补齐 smoke 语义

更新：

- `/Users/busiji/workbot/workspace/tools/cmux_read_contract.py`

新增规则：

- `startup_smoke`（`priority=85`，`normal_path_allowed=true`），将 `*-smoke-report.json` 提升为主线程默认可读的正式验收信号。

### 3) Dispatch contract 回归与手册口径同步

更新：

- `/Users/busiji/workbot/tests/test_cmux_dispatch_contract_p10_rest.py`（新增）
- `/Users/busiji/workbot/docs/cmux-runtime-handbook.md`

说明：

- 新增了对 dispatch drift 的仓库测试覆盖（`dispatch_owner/lane_identity/worker_role`）。
- 手册 A2 从“`allowed_tools=[\"Read\"]`”改为“按 bot 级 idle baseline”，与当前运行实现一致。

## 运行时真相位修改（仓库外）

以下改动发生在全局 cmux 运行脚本（不在仓库内）：

- `/Users/busiji/.agents/skills/cmux/scripts/generate_cmux_assignments.py`

`dispatch_blockers(...)` 新增前置一致性阻断：

- `dispatch_owner.not_codex`
- `lane_identity.bot_name_mismatch`
- `worker_role.bot_name_mismatch`

## 本地验证

```bash
python3 -m py_compile \
  /Users/busiji/workbot/workspace/tools/cmux_phase_readiness.py \
  /Users/busiji/workbot/workspace/tools/cmux_read_contract.py \
  /Users/busiji/workbot/tests/test_cmux_phase_readiness.py \
  /Users/busiji/workbot/tests/test_cmux_dispatch_contract_p10_rest.py \
  /Users/busiji/workbot/tests/test_cmux_read_contract.py

pytest -q \
  /Users/busiji/workbot/tests/test_cmux_phase_readiness.py \
  /Users/busiji/workbot/tests/test_cmux_dispatch_contract_p10_rest.py \
  /Users/busiji/workbot/tests/test_cmux_read_contract.py \
  /Users/busiji/workbot/tests/test_cmux_summary_artifact.py

pytest -q \
  /Users/busiji/workbot/tests/test_cmux_runtime_ctl_p8_health_paths.py \
  /Users/busiji/workbot/tests/test_cmux_packet_consumers.py
```

结果：

- 第一组：`29 passed`
- 第二组：`18 passed`

补充证据：

- `python3 /Users/busiji/workbot/workspace/tools/cmux_phase_readiness.py` 已能显式报告缺失的 per-bot smoke 报告，不再静默放过。
- 在补齐 non-crawl4ai bot 的 `*-smoke-report.json` 后，`phase2-preflight-latest.json` 中：
  - `runtime_launch_manifest_problems = {}`
  - `startup_smoke_report_problems = {}`

## 子代理交叉验证

交叉验证在本阶段是硬门禁；主线程只有在双路 PASS 后才可推进阶段收口。

- A 路：`Schrodinger`（formal acceptance / read-contract 侧）→ **PASS**
  - 证据：`cmux_phase_readiness.py` 已把 manifest/smoke 问题并入 `implemented` 判定。
  - 证据：`cmux_read_contract.py` 新增 `startup_smoke` 默认可读规则。
  - 证据：`test_cmux_phase_readiness.py` 与 `test_cmux_read_contract.py` 新增门禁覆盖并通过。
- B 路：`Planck`（dispatch contract / handbook 侧）→ **PASS**
  - 证据：`generate_cmux_assignments.py::dispatch_blockers()` 新增三类 pre-launch drift 拦截：
    - `dispatch_owner.not_codex`
    - `lane_identity.bot_name_mismatch`
    - `worker_role.bot_name_mismatch`
  - 证据：`test_cmux_dispatch_contract_p10_rest.py` 覆盖 valid 与三类 drift 分支并通过。
  - 证据：`cmux-runtime-handbook.md` A2 口径已与 bot 级 idle baseline 对齐。

结论：**交叉验证通过**。满足“必须使用子代理 + 交叉验证 PASS 才能推进下一步”的阶段门禁。
