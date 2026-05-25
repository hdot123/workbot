# workbot cmux P2 交付: Summary And Sidecar Split

日期: 2026-04-17

## 目标

把 commander 默认读路径收敛到短摘要 artifact，把长日志、详细检查结果和原始 JSON 明确降级为 sidecar。

## 当前证据

- `cross_verify` 现有详细产物会携带完整 `checks/result/screen_tail` 细节:
  - `/Users/busiji/workbot/workspace/tools/cmux_cross_verify.py`
  - `/Users/busiji/workbot/workspace/artifacts/cmux-runtime/cross-verify-latest.json`
- `P1` 已经定义 control packet，但还没有把“短摘要 vs 重 sidecar”拆开:
  - `/Users/busiji/workbot/workspace/tools/cmux_control_packet.py`

## 本次落地

- 新增 commander summary schema/helper:
  - `/Users/busiji/workbot/workspace/tools/cmux_summary_artifact.py`
- 更新 `cross_verify` 输出双轨 artifact:
  - 短摘要: `/Users/busiji/workbot/workspace/artifacts/cmux-runtime/cross-verify-summary-latest.json`
  - 详细 sidecar: `/Users/busiji/workbot/workspace/artifacts/cmux-runtime/cross-verify-latest.json`
- 新增测试:
  - `/Users/busiji/workbot/tests/test_cmux_summary_artifact.py`

## `wb-cmux-summary-v1` 形状

必填字段:

1. `schema_version`
2. `artifact_type`
3. `source`
4. `generated_at`
5. `title`
6. `status`
7. `summary_lines`
8. `primary_sidecar_path`
9. `sidecar_paths`

约束:

- `summary_lines` 最多 3 行，每行最多 160 字符
- `primary_sidecar_path` 与 `sidecar_paths` 只能是绝对路径或空
- sidecar 缺失时允许 `null` / `[]`，但不得因此回退到 pane transcript 作为默认读路径
- 原始 `checks/result/screen_tail` 等重内容必须保留在 sidecar，不进入 summary artifact

## 范围边界

`P2` 只定义摘要 artifact 并先接到 repo-local `cross_verify`。

本次不声称已完成:

- `watcher` 默认读 summary/control artifact: 这是 `P6`
- `finish-cycle` 摘要/sidecar 切分: 这是 `P6`
- `youzy` 文本消费者切分: 这是 `P11-text`

## 验证

```bash
python3 /Users/busiji/workbot/tests/test_cmux_summary_artifact.py
```
