# Claude Code 页面到来源映射

> 用途：把“本地原料文件”与“上游官方来源”建立明确映射。
> 说明：当前为模板文件，可直接开始填写。

| page_id | title | local_path | source_url | source_seed_id | source_type | access | verification_status | remarks |
|---|---|---|---|---|---|---|---|---|
| claude-code-001 |  |  |  | claude-seed-001 | docs / homepage / console / changelog | public / auth-required | unverified-live / verified / blocked |  |
| claude-code-002 |  |  |  | claude-seed-002 | docs / homepage / console / changelog | public / auth-required | unverified-live / verified / blocked |  |

## 规则

- 一个 `source_url` 可以映射多个本地文件
- 一个本地文件必须至少能追溯到一个上游 `source_url`
- 如果页面存在跳转、迁移、镜像或导出版本差异，必须写入 `remarks`
- 若某页面来自登录态导出，也要显式记录 `access=auth-required`
