# workbot cmux P11-rest 交付: Governance writeback migration

日期: 2026-04-18

## 阶段硬门禁

> 本阶段要求：必须使用子代理完成任务，并且必须完成双路交叉验证；只有交叉验证结论为 **PASS** 后，才允许进入下一步。

## 目标

完成 `P11-rest` 治理回写迁移：

- task-list 与 CE sync writeback 只依赖结构化结果（control packet / consumer-state），不再把 pane transcript 作为 normal-path 依据。
- 保留 `note_id` 与 finish receipt 机制。
- 保持“CE 正式生命周期评论仍由 commander 复核执行”的职责边界不变。

## 本次改动

### 1) 运行时真相位（仓库外）

更新：

- `/Users/busiji/.agents/skills/cmux/scripts/cmux_finish_cycle.py`

关键行为：

- normal path task-id 推断新增结构化链：
  - `control_packet.task_id`
  - `consumer_entry.runtime_task_id`
  - `control_packet.summary / consumer_entry.runtime_summary / consumer_entry.summary` 中的 `PREFIX-###`
- normal path summary 回写新增结构化来源优先：
  - `control_packet.summary`
  - `consumer_entry.runtime_summary`
  - `consumer_entry.summary`
  - 最后才是结构化默认文案
- forensic path 保留 `extract_evidence_line(tail)`，并显式标记 `summary_source=forensic_tail.evidence_line`。
- 修复 youzy hook 子进程调用阻断：补齐 `import subprocess`，保证 `run_youzy_data_replica_hook(...)` 可执行。

### 2) 仓库内测试回归补齐

更新：

- `/Users/busiji/workbot/tests/test_cmux_packet_consumers.py`

新增覆盖：

- control-path summary 来源断言（`summary_source`）。
- control-path 禁止触发 `extract_evidence_line`。
- forensic-tail 回退路径仍可工作且来源标记正确。
- youzy hook 子进程调用参数链路测试。
- `main()` 治理回写主链测试：
  - task-list 行状态/证据回写
  - `ce-sync-plan` 的 `cmux_auto_finish` 记录
  - receipt 产出与 assignment 置 idle
- receipt 幂等：同 `cycle_id` 命中 skip，不重复写回。

## 本地验证

```bash
python3 -m py_compile \
  /Users/busiji/.agents/skills/cmux/scripts/cmux_finish_cycle.py \
  /Users/busiji/workbot/tests/test_cmux_packet_consumers.py \
  /Users/busiji/workbot/tests/test_youzy_data_replica_hook_p11.py

pytest -q \
  /Users/busiji/workbot/tests/test_cmux_packet_consumers.py

pytest -q \
  /Users/busiji/workbot/tests/test_youzy_data_replica_hook_p11.py \
  /Users/busiji/workbot/tests/test_cmux_control_packet.py \
  /Users/busiji/workbot/tests/test_cmux_summary_artifact.py
```

当前结果：

- `test_cmux_packet_consumers.py`: `14 passed`
- `test_youzy_data_replica_hook_p11.py + test_cmux_control_packet.py + test_cmux_summary_artifact.py`: `13 passed`

## 子代理交叉验证

交叉验证在本阶段是硬门禁；主线程只有在双路 PASS 后才可推进阶段收口。

- A 路：`Hooke`（实现侧）→ **PASS**
  - 证据：`cmux_finish_cycle.py` 已将 normal-path summary/task-id 推断迁移为结构化来源优先。
  - 证据：`cmux_finish_cycle.py` 已补 `subprocess` 导入并修复 youzy hook 调用阻断。
  - 证据：`test_cmux_packet_consumers.py` 已补治理回写主链与 receipt 幂等测试并通过。
- B 路：`Mill`（独立审计侧）→ **PASS**
  - 复跑命令：`pytest -q test_cmux_packet_consumers.py test_youzy_data_replica_hook_p11.py test_cmux_control_packet.py test_cmux_summary_artifact.py`
  - 结果：`27 passed in 0.83s`
  - 证据：`subprocess` 导入阻断已消失，control-path/forensic/youzy/writeback-chain 覆盖项全部通过。

## 结论

**交叉验证通过**。满足“必须使用子代理 + 双路交叉验证 PASS 后才可推进下一步”的阶段门禁。
