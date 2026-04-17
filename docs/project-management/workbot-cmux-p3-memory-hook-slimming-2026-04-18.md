# workbot cmux P3 交付: Memory-hook Slimming

日期: 2026-04-18

## 目标

在不改变 `build_context_package()` 运行语义的前提下，缩减 `memory-hook` 每次事件落盘时重复写入的大块上下文，把高重复字段转成共享 artifact 引用，同时保留调试和 truth tracing 所需的信息。

## 本次修改

- 在 `/Users/busiji/workbot/workspace/tools/memory_hook_impls.py` 的 `ArtifactSinkImpl` 内新增 shared-payload 写入逻辑。
- 将高重复字段收敛为一份按内容摘要寻址的共享 artifact:
  - `system_context`
  - `project_context`
  - `allowed_reads`
  - `allowed_writes`
  - `evidence_refs`
- snapshot / latest / `events.jsonl` 不再重复内联完整重字段，只保留:
  - `artifact_refs.shared_payload`
  - 轻量 `system_context` 摘要
  - 轻量 `project_context` 摘要
  - `allowed_reads` / `allowed_writes` / `evidence_refs` 摘要
  - `compaction` 元信息

## 结果

- 重复事件在 heavy payload 不变时会复用同一个 shared artifact，而不是每次都重写。
- 真实完整样本的事件行体积明显下降。
- fail-close / degraded 相关顶层状态字段仍保留在事件输出中。

## 体积测量

- 构造回归样本:
  - raw package: `2765`
  - compact event line: `2356`
  - delta: `409`
- 真实完整样本基线:
  - 样本来源: `/Users/busiji/workbot/workspace/artifacts/memory-hook/contexts/latest-codex-stop.json`
  - raw package: `3790`
  - compact event line: `1765`
  - delta: `2025`

## 子代理交叉验证

- `Volta` 复核了 GitHub Project 8 的未完成 phase 卡范围，并确认 9 张未完成卡已统一写入强制门槛:
  - 必须使用子代理协作完成
  - 交叉验证必须明确记录为“通过”后，才允许进入下一步
- `Hilbert` 对 persisted artifact 消费者做了只读审计，结论是没有发现依赖旧 inline 重字段结构的外部运行时消费者。
- `Dewey` 补充了 P3 回归测试文件:
  - `/Users/busiji/workbot/tests/test_memory_hook_shared_payload_artifacts.py`

## 验证

```bash
pytest /Users/busiji/workbot/tests/test_memory_hook_shared_payload_artifacts.py
python3 -m py_compile /Users/busiji/workbot/workspace/tools/memory_hook_impls.py /Users/busiji/workbot/tests/test_memory_hook_shared_payload_artifacts.py
```
