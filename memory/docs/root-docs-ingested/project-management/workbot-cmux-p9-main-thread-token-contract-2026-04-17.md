# workbot cmux P9 交付: Main-Thread Token Contract

日期: 2026-04-17

## 目标

把 main-thread 的低 token 默认读路径写成可执行合同，而不是软约定。

## 本次落地

- 新增 commander read-contract helper:
  - `/Users/busiji/workbot/tools/cmux_read_contract.py`
- 新增回归测试:
  - `/Users/busiji/workbot/tests/test_cmux_read_contract.py`

## 默认允许的 commander 读源

- `*summary*.json`
- `*control-packet*.json`

## 默认禁止的 normal-path 读源

- `*.log`
- `*transcript*`
- `*screen*`
- `*tail*`

## 升级规则

- 详细 sidecar (`*latest*.json`, `*report*.json`, `*detail*.json`) 只能在 summary/control packet 明确指向时读取
- watcher log / pane transcript 需要显式 forensic 升级，不能作为 commander 默认读路径

## 验证

```bash
python3 /Users/busiji/workbot/tests/test_cmux_read_contract.py
```
