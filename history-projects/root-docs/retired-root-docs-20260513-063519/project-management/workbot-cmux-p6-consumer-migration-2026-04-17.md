# workbot cmux P6 交付: Migrate Direct cmux Consumers

日期: 2026-04-17

## 目标

把 watcher、finish-cycle、cross-verify 的正常读路径从 transcript/tail heuristics 迁移到 `P1` control packet 与 `P2` summary/sidecar 合同。

## 运行时真相位变更

以下文件位于全局 `cmux` 运行时目录，不在 `workbot` 仓库内，但它们是当前正式 runtime 的真实消费链:

- `/Users/busiji/.agents/skills/cmux/scripts/watch_cmux_assignments.py`
- `/Users/busiji/.agents/skills/cmux/scripts/cmux_finish_cycle.py`

本次在这两个文件中增加了 packet-first 路径:

- 优先从 pane screen 中提取 `wb-cmux-control-packet-v1`
- 当 screen 只给出 prose-only completion 时，明确阻塞，不再把它当正常完成
- 仅在没有 packet 且不存在 prose-only completion 误导时，才保留旧的 transcript fallback

## 仓库内交付物

- `cross_verify` 改为消费 control packet:
  - `/Users/busiji/workbot/workspace/tools/cmux_cross_verify.py`
- 新增对外部 runtime truth 的回归测试:
  - `/Users/busiji/workbot/tests/test_cmux_packet_consumers.py`

## 核心证据

### cross_verify

- 现在通过 `extract_latest_control_packet()` 等待和解析结果
- bot prompt 现在直接要求输出 `wb-cmux-control-packet-v1`
- 成功判定基于 `state/result/status_code`，不再依赖 `ok/code` 混合格式

### watcher

- `try_extract_control_packet()` 优先解析 control packet
- `classify_control_packet_state()` 直接把 packet 映射到 runtime state
- prose-only completion 会被提升为 blocker，而不是被当作完成信号

### finish-cycle

- `collect_outcome()` 先走 control packet 路径
- `task_id/summary` 优先从 packet 读取
- prose-only completion 会直接报错阻塞收尾

## 验证

```bash
python3 /Users/busiji/workbot/tests/test_cmux_control_packet.py
python3 /Users/busiji/workbot/tests/test_cmux_summary_artifact.py
python3 /Users/busiji/workbot/tests/test_cmux_packet_consumers.py
```

## 边界

本次不声称已完成:

- `youzy` 等特殊 pane-text consumer 的彻底迁移: 这是 `P11-text`
- artifact 默认读优先级的系统性收口: `P13`
