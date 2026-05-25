# workbot cmux P13 交付: Artifact Hygiene And Read Priority

日期: 2026-04-17

## 目标

防止 side artifact 把 transcript-heavy 读路径重新带回 commander 的默认路径。

## 本次落地

在 `/Users/busiji/workbot/tools/cmux_read_contract.py` 里增加了显式 artifact 分类:

- `commander_summary`
- `control_state`
- `detail_sidecar`
- `side_state_shadow`
- `overview_sidecar`
- `forensic_only`

## 显式优先级

1. `commander_summary`
2. `control_state`
3. 其余一律非默认读路径

显式降级对象:

- `hook-state.json`
- `pm-bot-watch.json`
- `*overview*`
- `*.log`
- `*transcript*`

## 验证

```bash
python3 /Users/busiji/workbot/tests/test_cmux_read_contract.py
```

## 结果

- `hook-state.json` 与 `pm-bot-watch.json` 被明确降级为 `side_state_shadow`
- overview 文件被明确降级为 `overview_sidecar`
- watcher log / transcript 继续保持 `forensic_only`
- 当 summary 与 control-state 同时存在时，summary 永远优先，control-state 只能做第二读源
