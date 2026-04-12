# OpenCode 证据链模板

> 用途：把“来源入口 → 页面原文 → 索引记录 → 人工判断”串成可追溯链路。

| claim_id | claim_summary | ref_id | source_url | page_id | raw_file | manifest_record | notes_record | promotion_ready | remarks |
|---|---|---|---|---|---|---|---|---|---|
| claim-001 |  | opencode-ref-001 |  | opencode-001 |  |  |  | no |  |
| claim-002 |  | opencode-ref-002 |  | opencode-002 |  |  |  | no |  |

## 字段说明

- `claim_summary`：要被吸收到下游的简短命题
- `ref_id`：对应 `refs/` 中的来源编号
- `source_url`：对应的官方来源 URL
- `page_id`：对应页面索引编号
- `raw_file`：原始落盘文件路径
- `manifest_record`：页面索引或站点地图中的对应记录
- `notes_record`：人工核对或冲突处理记录
- `promotion_ready`：是否达到 promotion 前条件

## 原则

- 没有 `ref_id` 的命题，不应进入下游知识层
- 没有 `raw_file` 的命题，不应被视为完成证据闭环
- 存在冲突但未处理完的命题，`promotion_ready` 必须保持 `no`
