# OpenCode 原始材料落盘约定

## 目的

保证原始材料进入仓库后，后续可追溯、可复核、可重建索引。

## 落盘建议

每份原始材料建议至少补齐以下信息：

- 来源链接
- 获取日期
- 获取方式
- 原始格式
- 是否需要登录

## 推荐文件头

```md
source_url: 
fetched_at: 
method: browser_export / crawler / api / manual_copy
format: md / html / pdf / txt
requires_auth: yes / no
```

## 注意事项

- 不要在 `raw/` 内改写原始语义
- 如需清洗文本，另存新文件，并保留原件
- 登录后内容与公开内容混用时，要在文件头明确标记
