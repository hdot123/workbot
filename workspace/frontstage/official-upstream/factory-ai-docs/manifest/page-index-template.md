# Factory AI 页面索引模板

> 用途：登记页面级原料，避免后续来源漂移。

| id | title | source_url | section | local_path | format | fetched_at | status | notes |
|---|---|---|---|---|---|---|---|---|
| factory-001 |  |  |  |  | md/html/pdf |  | todo |  |
| factory-002 |  |  |  |  | md/html/pdf |  | todo |  |

## 字段说明

- `id`：稳定编号，建议按项目前缀递增
- `title`：页面标题
- `source_url`：原始页面链接
- `section`：所属章节或栏目
- `local_path`：仓库内落盘路径
- `format`：原始格式，如 `md`、`html`、`pdf`
- `fetched_at`：抓取或导出时间
- `status`：`todo / seeded / fetched / parsed / reviewed / blocked`
- `notes`：备注，如重定向、登录限制、内容重复等
