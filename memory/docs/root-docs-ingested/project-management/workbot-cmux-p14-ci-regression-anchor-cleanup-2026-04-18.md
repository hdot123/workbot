# Workbot CMUX P14 CI, Regression, and Anchor Cleanup (2026-04-18)

## Card 与硬门禁

- Phase 4 卡片：`[P14] CI, regression, and anchor cleanup`
- 硬门禁：`必须完成子代理交叉验证并得到 PASS，方可进入交付结论`

## 本次改动范围

### A) Workflow 回归扩展

已更新：

- `/Users/busiji/workbot/.github/workflows/memory-hook-external-core-only.yml`
- `/Users/busiji/workbot/.github/workflows/memory-core-auto-sync-deploy.yml`

两条 workflow 均纳入必跑：

- `tests/test_cmux_runtime_ctl_p8_health_paths.py`
- `tests/test_cmux_packet_consumers.py`
- `tests/test_youzy_data_replica_hook_p11.py`
- `tests/test_cmux_phase_readiness.py`
- 并保留原 M9 套件回归项

### B) Control-plane smoke（delegate-on）

- 保留现有 `--no-delegate` fail-closed smoke。
- 新增 delegate-on CLI smoke（`host=codex`，`event=session-start`，不带 `--no-delegate`）：
  - 通过临时 `cmux` stub 注入 `PATH`，让 CI 上的 delegate 分支可稳定触发且具备明确成败语义。
  - 该 smoke 与 fail-closed smoke 互补，覆盖“配置异常时关闭”与“真实委派路径可执行”两类门禁。

### C) 文档证据更新（最小改动）

已更新：

- `/Users/busiji/workbot/docs/project-management/workbot-cmux-p14-ci-regression-anchor-cleanup-2026-04-18.md`
- `/Users/busiji/workbot/docs/project-management/workbot-cmux-p8-health-checks-and-special-paths-2026-04-18.md`
- `/Users/busiji/workbot/docs/project-management/workbot-cmux-p11-text-special-pane-consumers-2026-04-18.md`

原则：

- 不重写历史结论，只修补 P14 本卡必需证据与 P8/P11 的过期测试通过数。
- 明确区分“本地一次性验证结果”和“CI 持续门禁结果”，避免语义混叠。

### D) Readiness 锚点常量对齐

已更新：

- `/Users/busiji/workbot/tools/cmux_phase_readiness.py`

调整点：

- `CURRENT_TASK_TITLE` 更新为：`[Phase 4] P14 CI, regression, and anchor cleanup`
- `REQUIRED_DONE_TITLES` 扩展到当前项目基线（Phase 0~3 已完成卡片）
- `CURRENT_TASK_FILES` 对齐到本卡交付文件集合
- `DELIVERY_DOCS` 从固定旧列表改为 `workbot-cmux-*.md` 动态收集，避免 phase 文档新增后的常量漂移

## 可复核命令与结果

本地一次性验证（当前工作树）：

```bash
python3 -m pytest -q \
  tests/test_cmux_runtime_ctl_p8_health_paths.py \
  tests/test_cmux_packet_consumers.py \
  tests/test_youzy_data_replica_hook_p11.py \
  tests/test_cmux_phase_readiness.py \
  tests/test_memory_hook_gateway_m6_batch3_provider_switch.py \
  tests/test_memory_hook_impls_policy_conflict.py \
  tests/test_memory_hook_provider_rollback.py \
  tests/test_memory_hook_gateway.py \
  tests/test_memory_hook_gateway_p7_mainline.py \
  tests/test_cmux_hook_bridge.py \
  tests/test_f8_rollback.py
```

```bash
set +e
printf '{"cwd":"%s","session_id":"ci-fail-closed"}\n' "/Users/busiji/workbot" | \
  MEMORY_HOOK_CORE_PROVIDER=external-core \
  MEMORY_HOOK_EXTERNAL_CORE_MODULE=does.not.exist.module \
  python3 /Users/busiji/workbot/tools/memory_hook_gateway.py \
    --host codex \
    --event session-start \
    --no-delegate
rc=$?
set -e
echo "exit_code=$rc"
```

```bash
tmpdir="$(mktemp -d)"
cat >"$tmpdir/cmux" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
if [ "${1:-}" = "codex-hook" ]; then
  echo '{}'
  exit 0
fi
if [ "${1:-}" = "identify" ]; then
  echo '{"caller":{"workspace_ref":"workspace:ci","surface_ref":"surface:ci"}}'
  exit 0
fi
exit 1
EOF
chmod +x "$tmpdir/cmux"
printf '{"cwd":"%s","session_id":"ci-real-control-plane"}\n' "/Users/busiji/workbot" | \
  PATH="$tmpdir:$PATH" \
  CMUX_SURFACE_ID="surface:ci" \
  python3 /Users/busiji/workbot/tools/memory_hook_gateway.py \
    --host codex \
    --event session-start
rm -rf "$tmpdir"
```

CI 持续门禁（workflow）：

- 两条 workflow 已包含 P14 必跑回归项（本次复核命中行）：
  - `/Users/busiji/workbot/.github/workflows/memory-hook-external-core-only.yml`：39-42 行
  - `/Users/busiji/workbot/.github/workflows/memory-core-auto-sync-deploy.yml`：108-111 行
- 本次实现子代理实跑结果（2026-04-18）：
  - 首次在根目录直接执行 3 条 pytest：均为 `Exit code 4`（`tests/...` 路径不存在，cwd=`/`）
  - `cd /Users/busiji/workbot && python3 -m pytest -q tests/test_cmux_runtime_ctl_p8_health_paths.py` → `10 passed in 0.04s`
  - `cd /Users/busiji/workbot && python3 -m pytest -q tests/test_cmux_packet_consumers.py` → `14 passed in 0.06s`
  - `cd /Users/busiji/workbot && python3 -m pytest -q tests/test_youzy_data_replica_hook_p11.py` → `3 passed in 1.56s`
- 持续门禁语义保持不变：交付判定仍以 CI 绿灯为准，本地结果仅作本次阻塞修复可追溯证据。

## 子代理交叉验证

- A 路（测试执行与结果核验）：
  - Verdict：`PASS`
  - 结论摘要：按要求实跑 3 条 pytest，并记录“根目录误跑失败 + 仓库目录复跑通过”完整证据链。
  - 证据：上述 3 条命令对应输出（`10 passed`、`14 passed`、`3 passed`）。
- B 路（文档一致性与锚点清理核验）：
  - Verdict：`PASS`
  - 结论摘要：P8/P11 已按本次实跑结果回填；P14 的占位模板已清理并替换为当前状态文本；workflow 关键测试项已复核存在。
  - 证据：本文件与 P8/P11 文档的更新内容，以及 workflow 命中行（39-42、108-111）。
- Cross-Verification Verdict：`PASS`
- 门禁结论：双路均为 `PASS`，允许进入交付结论。

## 交付回填位

- Commit SHA（已回填）：`8fdd8c5`、`409e5ca`、`fa986a5`
- Projects 卡证据（已回填）：`[Phase 4] P14 CI, regression, and anchor cleanup` 已在 Project 8 写入交付摘要并切换 `Status=Done`（2026-04-18）。
