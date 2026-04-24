# Ingestion Registry Map

Status: rule-only, records-cleared
Created: 2026-04-12
Updated: 2026-04-24
Notes: `history-projects/**` 记录为正式历史证据根，不授予合法性。

## Rule
- Registry tracks non-legal inputs waiting for explicit decision.
- Registration does not grant legality.
- `incoming-raw` and `compatibility-only` scopes stay non-legal until absorbed.
- Status values include `absorbed` and `retired` for lifecycle tracking.
- Registry state changes 同次 `git commit` 提交后才生效.
- `history-projects/**` 是唯一正式历史证据根的登记范围；其登记只用于治理与追溯，不授予合法性。
- `workspace/projects/**` 是交付/运行目录，不是历史根。

## Current Registry
- Scope `history-projects/**` -> `retired`
- Scope `workspace/project-map/**` -> `incoming-raw`
- Scope `workspace/memory/kb/global/**` -> `compatibility-only`
- Scope `workspace/memory/kb/projects/**` -> `compatibility-only`
- Scope `workspace/memory/docs/**` -> `incoming-raw`
- Scope `workspace/memory/log/**` -> `incoming-raw`
- Scope `workspace/projects/**` -> `incoming-raw`
- Scope `workspace/tools/**` -> `compatibility-only`
- Scope `tests/**` -> `compatibility-only`
