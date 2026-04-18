# workbot cmux P11-text 交付: Special pane-text consumers

日期: 2026-04-18

## 阶段硬门禁

> 本阶段要求：必须使用子代理完成任务，并且必须完成双路交叉验证；只有交叉验证结论为 **PASS** 后，才允许进入下一步。

## 目标

将 `P6` 未覆盖的特殊 pane-text consumer（尤其是 `youzy` 路径）迁移到 control-packet / artifact 优先读取模型，阻断“默认读 pane transcript”的隐式路径。

## 运行时真相位修改（全局 cmux 脚本）

以下文件位于全局运行时目录（仓库外），属于当前正式 runtime 真相代码：

- `/Users/busiji/.agents/skills/cmux/scripts/watch_cmux_assignments.py`
- `/Users/busiji/.agents/skills/cmux/scripts/cmux_finish_cycle.py`
- `/Users/busiji/.agents/skills/cmux/scripts/youzy_data_replica_hook.py`

本次关键修改：

1. watcher 新增 consumer-state sidecar 产物  
   `watch_cmux_assignments.py` 新增 `cmux-consumer-state-latest.json` 写入逻辑，记录：
   - `schema_version=wb-cmux-consumer-state-v1`
   - 每个 assignment 的 `state/state_source/completed`
   - `control_packet` 与 `control_packet_error`

2. finish-cycle 正常路径改为 consumer-state/control-packet first  
   `cmux_finish_cycle.py` 的 `collect_outcome(...)` 新增显式消费 `consumer_entry`：
   - 正常路径只吃 `consumer_state -> control_packet`
   - 缺失 packet 时默认 fail-fast
   - 仅在 `--forensic-read-pane` 显式开启时允许 pane transcript 回退

3. youzy 特殊 consumer 改为 artifact-first  
   `youzy_data_replica_hook.py`：
   - 新增 `--control-packet-artifact`、`--consumer-state-file`
   - 正常路径必须提供 `control-packet artifact`，否则 fail-fast
   - `validate_control_artifact_with_consumer_state(...)` 强制校验 artifact 与 consumer-state 的引用关系
   - pane/screen 读取仅在 `--forensic-read-pane` 显式开启时允许

## 仓库内交付物

- 更新：`/Users/busiji/workbot/tests/test_cmux_packet_consumers.py`
- 新增：`/Users/busiji/workbot/tests/test_youzy_data_replica_hook_p11.py`

覆盖重点：

- finish-cycle 在 packet-first 路径下不触发 `read_screen`
- 缺失 packet 且未开启 forensic 时硬失败
- youzy hook 在正常路径只接受 artifact 输入
- consumer-state artifact 引用校验覆盖路径规范化场景

## 本地验证

```bash
python3 -m py_compile \
  /Users/busiji/.agents/skills/cmux/scripts/watch_cmux_assignments.py \
  /Users/busiji/.agents/skills/cmux/scripts/cmux_finish_cycle.py \
  /Users/busiji/.agents/skills/cmux/scripts/youzy_data_replica_hook.py \
  /Users/busiji/workbot/tests/test_cmux_packet_consumers.py \
  /Users/busiji/workbot/tests/test_youzy_data_replica_hook_p11.py

pytest -q \
  /Users/busiji/workbot/tests/test_cmux_packet_consumers.py \
  /Users/busiji/workbot/tests/test_youzy_data_replica_hook_p11.py

pytest -q \
  /Users/busiji/workbot/tests/test_cmux_control_packet.py \
  /Users/busiji/workbot/tests/test_cmux_summary_artifact.py
```

当前结果：

- `test_cmux_packet_consumers.py + test_youzy_data_replica_hook_p11.py`: `17 passed`
- `test_cmux_control_packet.py + test_cmux_summary_artifact.py`: `10 passed`

## 子代理交叉验证

交叉验证在本阶段是硬门禁；主线程只有在双路 PASS 后才可推进阶段收口。

- A 路：`Cicero`（watcher / finish-cycle 侧）→ **PASS**
  - 证据：`watch_cmux_assignments.py` 在无 control packet 且未开 forensic 时强制 `completed=False`，并写入 `state_source=control_packet_missing`。
  - 证据：`watch_cmux_assignments.py` 导入降级已收敛到 `except ModuleNotFoundError`，移除宽捕获 `except Exception`。
  - 证据：`watch_cmux_assignments.py` 与 `cmux_finish_cycle.py` 在 `wb-cmux-consumer-state-v1` schema 与 `assignments[logical_target]` 对齐上保持一致。
  - 证据：`tests/test_cmux_packet_consumers.py` 新增两条门禁测试，覆盖 forensic 关闭阻断与 forensic 开启放行。
- B 路：`Nietzsche`（youzy special consumer 侧）→ **PASS**
  - 证据：`youzy_data_replica_hook.py` 正常路径强制 `--control-packet-artifact`，缺失时 fail-fast。
  - 证据：`youzy_data_replica_hook.py` 的 pane/screen 读取仅在 `--forensic-read-pane` 显式开启时允许。
  - 证据：`validate_control_artifact_with_consumer_state(...)` 对 artifact 路径执行规范化比对（`resolve(strict=False)`）。
  - 证据：`tests/test_youzy_data_replica_hook_p11.py` 明确阻断旧的默认 pane-text 消费路径。
- 双路最小验证命令结果：
  - `pytest -q /Users/busiji/workbot/tests/test_cmux_packet_consumers.py` → `14 passed`
  - `pytest -q /Users/busiji/workbot/tests/test_youzy_data_replica_hook_p11.py` → `3 passed`

结论：**交叉验证通过**。满足“必须使用子代理 + 交叉验证 PASS 才能推进下一步”的阶段门禁。
