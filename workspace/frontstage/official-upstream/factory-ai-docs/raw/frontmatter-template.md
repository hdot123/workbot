# Factory AI 原始材料文件头模板

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
verification_status: user-provided-official / unverified-live / verified / redirected / archived / blocked
notes: 
```

## 最小要求

至少应补齐：

- `source_url`
- `fetched_at`
- `method`
- `format`
- `requires_auth`
