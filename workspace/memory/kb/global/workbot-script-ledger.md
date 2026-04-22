---
type: [KB:GLOBAL]
title: "Workbot Script Ledger"
shortname: WB-SCRIPT-LEDGER
status: active
created: 2026-04-23
updated: 2026-04-23
source: local-canonical
confidence: high
tags: [scripts, ledger, runtime, cmux, memory, tooling]
related: [workbot-hook-contract, workbot-memory-system, workbot-truth-model]
---

# Workbot Script Ledger

> 本文件是 `workbot` 当前有效脚本面的正式台账。
> 它登记仓库内脚本、仓库顶层 `scripts/` 工具脚本，以及当前实际依赖但不在仓库 git 历史中的 repo-external runtime 入口。
> 它不登记 run artifact、临时日志、历史 residue 或 retired `tmux` 材料。

## 1. 适用范围

- 当前仓库真相内的核心脚本面是 `workspace/tools/`。
- 仓库顶层 `scripts/` 属于辅助工具面，保留在台账内，但不等同于正式 runtime 主体。
- 当前 `workbot` 仍实际依赖的 repo-external runtime 入口，必须登记为 external dependency。
- `workspace/artifacts/`、`workspace/log/`、`workspace/memory/tmp/` 下的运行物不是脚本台账成员。
- `.DS_Store` 之类本地 residue 不计入台账。

## 2. 统计快照

截至 `2026-04-23`：

- `workspace/tools/` Python 模块：`16`
- 仓库顶层 `scripts/` 活跃脚本：`6`
- repo-external runtime 入口：`3`
- 当前有效脚本总面：`25`

按子系统拆分：

- `cmux` 仓内模块：`6`
- `memory-hook / memory runtime` 仓内模块：`9`
- `task-source / general binding` 仓内模块：`1`
- 顶层工具脚本：`6`
- repo-external `cmux` runtime：`3`

## 3. 控制口径

- 当前项目的正式任务类型只有两类：`mainline` 与 `cmux`。
- 因此核心脚本面不应无限增殖；优先在既有脚本中收束职责，必要时再新增模块。
- 以当前两类任务模型计，`workspace/tools/` 的健康控制目标是约 `12-16` 个核心模块。
- 当前 `16` 个核心模块仍在可控边界内，但已接近上限；后续新增日志或 runtime 能力时，应优先避免继续膨胀脚本总数。

## 4. 分类规则

- `core`：正式 runtime、合同、门禁、状态机或写回实现。
- `utility`：样本、OCR、启动辅助或一次性工具脚本。
- `external-runtime`：仓库外但当前执行面实际依赖的正式 runtime 入口。
- `active`：当前有效并应被维护。
- `active-external`：当前有效但不在本仓库 git 历史内。
- `formal-core`：当前两类正式任务模型直接依赖的核心脚本。
- `supporting-core`：当前正式脚本面中的辅助实现、适配器或校验支撑脚本。
- `utility-runtime`：当前仍保留的辅助工具脚本，不构成正式 runtime 主干。
- `keep`：当前维持原位，不要求额外治理动作。
- `watch-size`：当前保留，但应监控继续膨胀。
- `split-target`：当前保留，但已进入优先拆薄候选。
- `ownership-clarify`：当前保留，但后续维护前应先澄清是否为兼容变体、重复入口或临时遗留。

## 5. Ledger

### 5.1 Repo Core: `workspace/tools/`

| Path | Subsystem | Kind | Lines | Status | Lifecycle | Next Action | Role |
| --- | --- | --- | ---: | --- | --- | --- | --- |
| `workspace/tools/cmux_control_packet.py` | cmux | core | 537 | active | formal-core | keep | `cmux` control packet schema、校验与消费约束 |
| `workspace/tools/cmux_cross_verify.py` | cmux | core | 286 | active | supporting-core | keep | `cmux` 读屏/状态交叉验证辅助 |
| `workspace/tools/cmux_phase_readiness.py` | cmux | core | 653 | active | formal-core | watch-size | `cmux` phase readiness 门禁与状态判断 |
| `workspace/tools/cmux_read_contract.py` | cmux | core | 335 | active | supporting-core | keep | `cmux` 读取合同与输入面裁决 |
| `workspace/tools/cmux_run_lifecycle.py` | cmux | core | 538 | active | formal-core | watch-size | `cmux` run/task-source 生命周期绑定 |
| `workspace/tools/cmux_summary_artifact.py` | cmux | core | 116 | active | supporting-core | keep | `cmux` summary artifact 组装 |
| `workspace/tools/current_task_source.py` | task-source | core | 263 | active | formal-core | keep | `mainline/cmux` 共用 task source schema 与 gate |
| `workspace/tools/memory_hook_core.py` | memory-hook | core | 271 | active | formal-core | keep | memory hook 主流程核心逻辑 |
| `workspace/tools/memory_hook_gateway.py` | memory-hook | core | 995 | active | formal-core | split-target | `Codex/Claude` 共享 hook gateway 入口 |
| `workspace/tools/memory_hook_impls.py` | memory-hook | core | 1162 | active | formal-core | split-target | memory hook 主要实现与路由落盘逻辑 |
| `workspace/tools/memory_hook_interfaces.py` | memory-hook | core | 226 | active | formal-core | keep | memory hook 合同接口与对象边界 |
| `workspace/tools/memory_hook_provider_rollback.py` | memory-hook | core | 60 | active | supporting-core | keep | provider rollback 保护入口 |
| `workspace/tools/memory_hook_adapters/neutral_policy.py` | memory-hook | core | 22 | active | supporting-core | keep | neutral host policy adapter |
| `workspace/tools/memory_hook_adapters/workbot_policy.py` | memory-hook | core | 24 | active | supporting-core | keep | workbot host policy adapter |
| `workspace/tools/memory_hook_adapters/workbot_runtime_profile.py` | memory-hook | core | 253 | active | supporting-core | keep | workbot runtime profile 适配 |
| `workspace/tools/validate_memory_system.py` | memory-hook | core | 43 | active | supporting-core | keep | memory system 基础校验工具 |

### 5.2 Repo Utility: `scripts/`

| Path | Subsystem | Kind | Lines | Status | Lifecycle | Next Action | Role |
| --- | --- | --- | ---: | --- | --- | --- | --- |
| `scripts/bailian_vision_8_samples.py` | OCR | utility | 272 | active | utility-runtime | keep | 百炼视觉样本跑批 |
| `scripts/ocr-textbook-baidu.py` | OCR | utility | 226 | active | utility-runtime | keep | 百度 OCR 课本处理脚本 |
| `scripts/ocr-textbook.py` | OCR | utility | 195 | active | utility-runtime | ownership-clarify | OCR 课本处理脚本 |
| `scripts/ocr_8_samples.py` | OCR | utility | 244 | active | utility-runtime | keep | OCR 八样本批处理 |
| `scripts/ocr_textbook.py` | OCR | utility | 142 | active | utility-runtime | ownership-clarify | OCR 课本脚本的兼容变体 |
| `scripts/start-day.sh` | startup | utility | 10 | active | utility-runtime | keep | 日常启动辅助脚本 |

### 5.3 Repo-External Runtime Dependencies

| Path | Subsystem | Kind | Lines | Status | Lifecycle | Next Action | Role |
| --- | --- | --- | ---: | --- | --- | --- | --- |
| `/Users/busiji/.agents/skills/cmux/scripts/watch_cmux_assignments.py` | cmux | external-runtime | 2830 | active-external | external-runtime | split-target | `cmux` watcher、dispatch、lane 推进主入口 |
| `/Users/busiji/.agents/skills/cmux/scripts/cmux_finish_cycle.py` | cmux | external-runtime | 1242 | active-external | external-runtime | split-target | `A7` writeback 与 `finish-cycle` closeout 主入口 |
| `/Users/busiji/.agents/skills/cmux/scripts/cmux_runtime_ctl.py` | cmux | external-runtime | 1044 | active-external | external-runtime | split-target | runtime inspect、health、status 分类主入口 |

## 6. 生命周期视图

截至当前台账：

- `formal-core`：`8`
- `supporting-core`：`8`
- `utility-runtime`：`6`
- `external-runtime`：`3`

维护解释：

- `formal-core` 必须随仓库真相长期维护，新增或退役都必须同步更新本台账。
- `supporting-core` 仍属于正式脚本面，但不应反向演变成新的事实中心。
- `utility-runtime` 可以继续保留，但不应在没有明确理由的情况下侵入正式 runtime。
- `external-runtime` 必须在 repo 内有对应合同或测试约束，避免形成不可审计黑箱。

## 7. 当前热点文件

以下文件不是错误，但已明显偏重，应优先控制继续膨胀：

- `workspace/tools/memory_hook_impls.py`：`1162` 行
- `workspace/tools/memory_hook_gateway.py`：`995` 行
- `workspace/tools/cmux_phase_readiness.py`：`653` 行
- `/Users/busiji/.agents/skills/cmux/scripts/watch_cmux_assignments.py`：`2830` 行
- `/Users/busiji/.agents/skills/cmux/scripts/cmux_finish_cycle.py`：`1242` 行
- `/Users/busiji/.agents/skills/cmux/scripts/cmux_runtime_ctl.py`：`1044` 行

当前判断：

- 问题主轴不是“脚本数量失控”，而是少数脚本职责过重。
- 如果后续要补任务日志体系，应优先复用现有边界，避免再无上限新增脚本。

## 8. 当前需澄清对象

以下脚本当前保留，但后续如要收敛脚本面，应先澄清归属和去留：

- `scripts/ocr-textbook.py`
- `scripts/ocr_textbook.py`

当前判断：

- 它们都仍是 active utility，而不是立即删除对象。
- 但两者命名高度接近，后续如要整理 OCR 工具层，必须先明确谁是当前主路径、谁是历史/兼容变体。
- 当前已验收 OCR 证据链实际引用的是 `scripts/ocr_textbook.py`；因此它不能再被简单表述为“纯兼容变体”。

## 9. 不计入台账的对象

以下对象与执行面有关，但不属于正式脚本台账：

- `workspace/log/**`：本地日志与 hook 运行残留
- `workspace/artifacts/**`：run artifact 与审计证据
- `workspace/memory/tmp/**`：临时写回与任务残留
- retired `tmux` 目录与历史迁移材料

## 10. 后续维护规则

- 新增正式脚本时，必须同步更新本台账。
- 删除或退役脚本时，必须同步更新本台账。
- 如果某个 repo-external runtime 入口不再被当前 `workbot` 正式依赖，应从本台账移除。
- 如果某个脚本只是临时调试用且不属于长期真相，不应登记到本台账。

## 11. Governance Matrix

> 本节不是再次罗列脚本清单，而是给出“谁能改、何时必须走 `branch-2`、何时必须做 acceptance、至少要跑哪些 focused tests”的执行矩阵。

| Scope | Covered Paths | Owner | Branch-2 Required | Acceptance Required | Repo External | Minimum Test Gate | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `cmux` repo contracts and lifecycle core | `workspace/tools/cmux_*.py`, `workspace/tools/current_task_source.py` | `cmux` runtime governance | yes | yes | no | `tests/test_cmux_control_packet.py`, `tests/test_cmux_phase_readiness.py`, `tests/test_cmux_run_lifecycle.py` | 触碰 formal chain、task-source、control packet、phase gate 时，必须按正式任务收口 |
| `memory-hook` formal core | `workspace/tools/memory_hook_*.py`, `workspace/tools/memory_hook_adapters/*.py`, `workspace/tools/validate_memory_system.py` | memory runtime governance | yes | yes, if contract/log path/truth path changes | no | `tests/test_memory_hook_shared_payload_artifacts.py` plus directly mapped focused tests | 触碰 `workspace/memory`、`workspace/log`、hook contract 或 host policy 时，不能只做本地试跑 |
| shared binding and task-source boundary | `workspace/tools/current_task_source.py` | mainline/cmux boundary governance | yes | yes | no | `tests/test_cmux_run_lifecycle.py`, `tests/test_cmux_control_packet.py` | 这是 `mainline` 与 `cmux` 的共用边界；任何改动都按高风险入口处理 |
| repo utility scripts | `scripts/*.py`, `scripts/*.sh` | local tooling / OCR governance | yes, for tracked repo changes | conditional | no | script-specific focused verification | 不直接构成正式 runtime；如影响正式工作流、样本结论或 canonical docs，则 acceptance 升级为必需 |
| repo-external `cmux` runtime | `/Users/busiji/.agents/skills/cmux/scripts/watch_cmux_assignments.py`, `/Users/busiji/.agents/skills/cmux/scripts/cmux_finish_cycle.py`, `/Users/busiji/.agents/skills/cmux/scripts/cmux_runtime_ctl.py` | `cmux` runtime operator | yes, if paired repo change exists | yes | yes | `tests/test_cmux_runtime_ctl_p8_health_paths.py`, `tests/test_cmux_phase_readiness.py`, `tests/test_cmux_packet_consumers.py` | 不在 git 历史中；每次变更都必须在最终汇报里单独列明“repo-external synced” |

## 12. Gate Rules

- 正式任务模型只有两类：`mainline` 与 `cmux`；正式脚本治理也只允许围绕这两类展开。
- 任何触碰 repo-tracked 脚本的改动，都不得直接落在 `branch-1`；必须先进入一次性的 `branch-2`。
- 任何触碰 `cmux` formal chain、task-source boundary、control packet、finish-cycle 或 runtime status 分类的改动，都必须带 focused tests，且默认要求 acceptance。
- 任何触碰 `workspace/log`、`workspace/memory`、hook contract 或 log path 的 `memory-hook` 改动，都必须把日志路径和 Git ignore 规则一起复核，避免把运行日志重新带回 repo truth。
- repo-external runtime 不是“自由改”的灰区；它虽然不进入当前仓库 git 历史，但必须与 repo 内测试或合同约束联动汇报。
- `workspace/log/**`、`workspace/artifacts/**`、`workspace/memory/tmp/**` 继续视为运行物与证据区，不得登记为正式脚本，也不得冒充任务日志真相。

## 13. Per-Script Governance Detail

> 本节把治理矩阵压到逐脚本粒度。`Change Gate` 表示最小变更门禁；`Test Gate` 表示至少要跑的 focused verification。

### 13.1 Repo Core: `workspace/tools/`

| Path | Owner | Change Gate | Test Gate | Notes |
| --- | --- | --- | --- | --- |
| `workspace/tools/cmux_control_packet.py` | `cmux` runtime governance | `branch-2 + acceptance` | `tests/test_cmux_control_packet.py`, `tests/test_cmux_packet_consumers.py` | control packet schema 与消费约束，属 formal chain 核心 |
| `workspace/tools/cmux_cross_verify.py` | `cmux` runtime governance | `branch-2 + focused tests` | `tests/test_cmux_phase_readiness.py`, `tests/test_cmux_summary_artifact.py` | 交叉验证辅助，不单独升格为事实中心 |
| `workspace/tools/cmux_phase_readiness.py` | `cmux` runtime governance | `branch-2 + acceptance` | `tests/test_cmux_phase_readiness.py`, `tests/test_cmux_runtime_ctl_p8_health_paths.py` | phase gate 与 readiness 裁决，高风险入口 |
| `workspace/tools/cmux_read_contract.py` | `cmux` runtime governance | `branch-2 + focused tests` | `tests/test_cmux_read_contract.py`, `tests/test_cmux_dispatch_contract_p10_rest.py` | 读取合同与输入约束，影响 dispatch 判定 |
| `workspace/tools/cmux_run_lifecycle.py` | `cmux` runtime governance | `branch-2 + acceptance` | `tests/test_cmux_run_lifecycle.py`, `tests/test_cmux_control_packet.py` | run/task-source 生命周期绑定，影响 `mainline/cmux` 边界 |
| `workspace/tools/cmux_summary_artifact.py` | `cmux` runtime governance | `branch-2 + focused tests` | `tests/test_cmux_summary_artifact.py`, `tests/test_cmux_packet_consumers.py` | summary artifact 组装，依赖 control packet 结果 |
| `workspace/tools/current_task_source.py` | mainline/cmux boundary governance | `branch-2 + acceptance` | `tests/test_cmux_run_lifecycle.py`, `tests/test_cmux_control_packet.py` | 共用 task-source boundary；任何改动都按高风险边界处理 |
| `workspace/tools/memory_hook_core.py` | memory runtime governance | `branch-2 + focused tests` | `tests/test_memory_hook_gateway.py`, `tests/test_memory_hook_shared_payload_artifacts.py` | memory hook 主流程核心，不直接决定 host policy |
| `workspace/tools/memory_hook_gateway.py` | memory runtime governance | `branch-2 + acceptance` | `tests/test_memory_hook_gateway.py`, `tests/test_memory_hook_gateway_p7_mainline.py`, `tests/test_memory_hook_gateway_m6_batch3_provider_switch.py`, `tests/test_memory_hook_shared_payload_artifacts.py` | 共享 gateway 主入口；触碰 log path/contract/truth path 时必须 acceptance |
| `workspace/tools/memory_hook_impls.py` | memory runtime governance | `branch-2 + acceptance` | `tests/test_memory_hook_impls_policy_conflict.py`, `tests/test_memory_hook_gateway.py`, `tests/test_memory_hook_shared_payload_artifacts.py` | 实现体量大，后续仍是 `split-target` |
| `workspace/tools/memory_hook_interfaces.py` | memory runtime governance | `branch-2 + focused tests` | `tests/test_memory_hook_gateway.py`, `tests/test_memory_hook_shared_payload_artifacts.py` | 合同接口层；改动必须保持 gateway 契约稳定 |
| `workspace/tools/memory_hook_provider_rollback.py` | memory runtime governance | `branch-2 + focused tests` | `tests/test_memory_hook_provider_rollback.py` | provider rollback 专用守卫，改动必须保留 fail-safe |
| `workspace/tools/memory_hook_adapters/neutral_policy.py` | memory runtime governance | `branch-2 + focused tests` | `tests/test_memory_hook_gateway.py`, `tests/test_memory_hook_impls_policy_conflict.py` | host policy adapter；不允许绕开 policy 冲突检测 |
| `workspace/tools/memory_hook_adapters/workbot_policy.py` | memory runtime governance | `branch-2 + focused tests` | `tests/test_memory_hook_gateway.py`, `tests/test_memory_hook_impls_policy_conflict.py` | workbot host policy adapter；触碰 truth/log path 时 acceptance 升级为必需 |
| `workspace/tools/memory_hook_adapters/workbot_runtime_profile.py` | memory runtime governance | `branch-2 + focused tests` | `tests/test_memory_hook_gateway_p7_mainline.py`, `tests/test_memory_hook_shared_payload_artifacts.py` | runtime profile 适配层，变更要与 gateway 行为同步验证 |
| `workspace/tools/validate_memory_system.py` | memory runtime governance | `branch-2 + focused verification` | `tests/test_memory_hook_gateway.py`, `tests/test_memory_hook_shared_payload_artifacts.py` | 校验工具入口；没有独立高风险 acceptance 需求，但不能无验证改动 |

### 13.2 Repo Utility: `scripts/`

| Path | Owner | Change Gate | Test Gate | Notes |
| --- | --- | --- | --- | --- |
| `scripts/bailian_vision_8_samples.py` | OCR/runtime tooling governance | `branch-2 + script-specific verification` | `tests/test_ocr_interface.py`, `tests/test_ocr_integration.py` | 样本脚本，不属于 formal runtime 主干 |
| `scripts/ocr-textbook-baidu.py` | OCR/runtime tooling governance | `branch-2 + script-specific verification` | `tests/test_ocr_interface.py`, `tests/test_ocr_integration.py`, `tests/test_ocr_event_bridge.py` | 百度 OCR 入口；改动如影响正式输出格式，acceptance 升级为必需 |
| `scripts/ocr-textbook.py` | OCR/runtime tooling governance | `branch-2 + ownership clarify + verification` | `tests/test_ocr_interface.py`, `tests/test_ocr_integration.py` | 与 `ocr_textbook.py` 并存；当前更像历史/并行变体，先澄清主入口再做扩大改动 |
| `scripts/ocr_8_samples.py` | OCR/runtime tooling governance | `branch-2 + script-specific verification` | `tests/test_ocr_interface.py`, `tests/test_ocr_integration.py` | 样本批处理脚本，保留 utility 角色 |
| `scripts/ocr_textbook.py` | OCR/runtime tooling governance | `branch-2 + ownership clarify + verification` | `tests/test_ocr_interface.py`, `tests/test_ocr_integration.py` | 当前已被已验收 OCR 证据链实际引用；但与 `ocr-textbook.py` 的主从关系仍需正式澄清 |
| `scripts/start-day.sh` | local startup governance | `branch-2 + manual smoke` | manual startup smoke only | 启动辅助，不直接触发 repo-wide acceptance |

### 13.3 Repo-External Runtime

| Path | Owner | Change Gate | Test Gate | Notes |
| --- | --- | --- | --- | --- |
| `/Users/busiji/.agents/skills/cmux/scripts/watch_cmux_assignments.py` | `cmux` runtime operator | `branch-2 + acceptance + repo-external sync note` | `tests/test_cmux_packet_consumers.py`, `tests/test_cmux_bootstrap_watcher_takeover.py`, `tests/test_cmux_watcher_self_reap.py`, `tests/test_cmux_hook_bridge.py` | watcher/dispatch 主入口；不在 git 中，但必须与 repo 内合同联动汇报 |
| `/Users/busiji/.agents/skills/cmux/scripts/cmux_finish_cycle.py` | `cmux` runtime operator | `branch-2 + acceptance + repo-external sync note` | `tests/test_cmux_packet_consumers.py`, `tests/test_cmux_phase_readiness.py`, `tests/test_cmux_runtime_ctl_p8_health_paths.py` | `A7` closeout 主入口；任何改动都要验证 receipt、writeback、idle reset |
| `/Users/busiji/.agents/skills/cmux/scripts/cmux_runtime_ctl.py` | `cmux` runtime operator | `branch-2 + acceptance + repo-external sync note` | `tests/test_cmux_runtime_ctl_p8_health_paths.py`, `tests/test_cmux_phase_readiness.py`, `tests/test_cmux_packet_consumers.py` | runtime inspect/health/status 分类主入口；原生执行 drift 规则必须稳定 |
