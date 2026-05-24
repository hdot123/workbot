# workbot cmux P1 交付: Control Packet Schema

日期: 2026-04-17

## 目标

`P1` 只定义 commander 正常读路径使用的最小控制包合同，不提前把 watcher / finish-cycle / cross-verify 的主消费链整体迁移到新合同。

## 当前证据

- 当前 `watcher` 正常路径仍以 pane screen / tail 文本为主:
  - `/Users/busiji/.agents/skills/cmux/scripts/watch_cmux_assignments.py`
  - `/Users/busiji/.agents/skills/cmux/scripts/cmux_finish_cycle.py`
- 仓库内已经存在短 marker + JSON 的机器可读先例:
  - `/Users/busiji/workbot/tools/cmux_cross_verify.py`
  - `/Users/busiji/workbot/artifacts/cmux-runtime/cross-verify-latest.json`
- 这说明 `P1` 的合理边界是先把 packet schema 固化，再由 `P6` / `P11-text` 迁移 transcript-heavy consumers。

## 本次落地

- 新增 schema/校验 CLI:
  - `/Users/busiji/workbot/tools/cmux_control_packet.py`
- 新增回归测试:
  - `/Users/busiji/workbot/tests/test_cmux_control_packet.py`

## v1 最小字段

`wb-cmux-control-packet-v1` 的最小字段如下:

1. `schema_version`
2. `state`
3. `result`
4. `marker`
5. `summary`
6. `artifact_path`

字段约束:

- `state` 只允许: `running`, `waiting_input`, `blocked`, `completed`, `failed`
- `result` 必须与 `state` 一一对应:
  - `running -> in_progress`
  - `waiting_input -> needs_input`
  - `blocked -> blocked`
  - `completed -> pass`
  - `failed -> fail`
- `marker` 必须是短 marker，且以 `:` 结尾；screen 中 marker 前缀和 JSON 内 `marker` 必须一致
- `artifact_path` 必须是绝对路径或 `null`
- `completed` / `failed` 的 `summary` 不能是 `done` / `completed` / `已完成` 之类占位词
- 如果 screen 里只有“已完成 / pass / failed”之类 prose 结论而没有 packet，校验器必须拒绝

## v1 兼容扩展字段

为了不把后续 `P6` / `P11-text` 的 consumer 迁移成本重新抬高，v1 允许携带以下兼容字段:

- `assignment_id`
- `logical_target`
- `task_id`
- `completed_at`
- `evidence_refs`

这些字段在 `P1` 里不是最小必填项，但已经纳入示例，用于给 `finish-cycle` / writeback / audit 路径预留稳定映射位。

## 向后兼容说明

当前仓库与运行面里已经存在 mixed-format 机器输出:

- marker + JSON: `/Users/busiji/workbot/tools/cmux_cross_verify.py`
- 聚合 JSON artifact: `/Users/busiji/workbot/artifacts/cmux-runtime/cross-verify-latest.json`
- assignment packet: `/Users/busiji/workbot/artifacts/cmux-runtime/cmux-assignment.json`
- key=value log lines: `/Users/busiji/workbot/artifacts/cmux-runtime/watch_cmux_assignments.log`

因此 `P1` 的严格校验只作用于 **新 control packet 正常路径**，不追溯性否定现有 legacy log / artifact。

## 状态示例

### running

```json
{
  "schema_version": "wb-cmux-control-packet-v1",
  "state": "running",
  "result": "in_progress",
  "marker": "XCp1run01:",
  "assignment_id": "dev-101",
  "logical_target": "dev-bot",
  "summary": "dev-bot is applying the approved patch set.",
  "artifact_path": null
}
```

### waiting_input

```json
{
  "schema_version": "wb-cmux-control-packet-v1",
  "state": "waiting_input",
  "result": "needs_input",
  "marker": "XCp1wait1:",
  "assignment_id": "qa-101",
  "logical_target": "qa-bot",
  "summary": "qa-bot is waiting for the commander to approve the next prompt.",
  "artifact_path": null
}
```

### blocked

```json
{
  "schema_version": "wb-cmux-control-packet-v1",
  "state": "blocked",
  "result": "blocked",
  "marker": "XCp1block:",
  "assignment_id": "pm-101",
  "logical_target": "pm-bot",
  "summary": "pm-bot is blocked by a missing validated upstream source.",
  "artifact_path": "/Users/busiji/workbot/artifacts/cmux-runtime/pm-bot-blocked.json",
  "evidence_refs": [
    "/Users/busiji/workbot/artifacts/cmux-runtime/pm-bot-blocked.json"
  ]
}
```

### completed

```json
{
  "schema_version": "wb-cmux-control-packet-v1",
  "state": "completed",
  "result": "pass",
  "marker": "XCp1done1:",
  "assignment_id": "doc-101",
  "logical_target": "doc-bot",
  "task_id": "DOC-101",
  "summary": "doc-bot finished the delivery note and recorded the evidence path.",
  "artifact_path": "/Users/busiji/workbot/artifacts/cmux-runtime/doc-bot-summary.json",
  "completed_at": "2026-04-17T22:30:00+0800",
  "evidence_refs": [
    "/Users/busiji/workbot/artifacts/cmux-runtime/doc-bot-summary.json"
  ]
}
```

### failed

```json
{
  "schema_version": "wb-cmux-control-packet-v1",
  "state": "failed",
  "result": "fail",
  "marker": "XCp1fail1:",
  "assignment_id": "rea-101",
  "logical_target": "rea-bot",
  "task_id": "REA-101",
  "summary": "rea-bot rejected the packet because the evidence artifact was missing.",
  "artifact_path": "/Users/busiji/workbot/artifacts/cmux-runtime/rea-bot-failure.json",
  "completed_at": "2026-04-17T22:31:00+0800",
  "evidence_refs": [
    "/Users/busiji/workbot/artifacts/cmux-runtime/rea-bot-failure.json"
  ]
}
```

## P1 / P6 边界

本次不声称已完成以下迁移，这些仍属于后续卡片:

- `watch_cmux_assignments.py` 默认消费 packet/summary: 属于 `P6`
- `cmux_finish_cycle.py` 摆脱 transcript tail 依赖: 属于 `P6` 与 `P11-text`
- `youzy_data_replica_hook.py` 摆脱 pane text 正常路径: 属于 `P11-text`

## 验证

```bash
python3 /Users/busiji/workbot/tests/test_cmux_control_packet.py
python3 /Users/busiji/workbot/tools/cmux_control_packet.py --print-examples --pretty
```
