# Codex 原始材料文件头模板

> 用途：每份进入 `raw/` 的原始材料，建议在文件开头保留以下元信息。

```md
source_url: 
source_title: 
fetched_at: 
method: browser_export / crawler / api / manual_copy
format: md / html / pdf / txt
requires_auth: yes / no
source_seed_id: 
page_id: 
verification_status: unverified-live / verified / redirected / archived / blocked
notes: 
```

## 最小要求

至少应补齐：

- `source_url`
- `fetched_at`
- `method`
- `format`
- `requires_auth`

## 推荐要求

若该页面已经进入索引，还应补齐：

- `source_seed_id`
- `page_id`
- `verification_status`

## 原则

- `raw/` 保留原始语义，不在这里写下游结论
- 如需清洗版或提炼版，应另存，不覆盖原始文件
