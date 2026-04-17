# Ingestion Registry Map

Status: rule-only, records-cleared

## Rule
- Registry tracks non-legal inputs waiting for explicit decision.
- Registration does not grant legality.
- `incoming-raw` and `compatibility-only` scopes stay non-legal until absorbed.
- Status values include `absorbed` and `retired` for lifecycle tracking.
- Registry state changes 同次 `git commit` 提交后才生效.

## Current Registry
- Scope `workspace/project-map/**` -> `incoming-raw`
- Scope `workspace/memory/kb/global/**` -> `compatibility-only`
- Scope `workspace/memory/kb/projects/**` -> `compatibility-only`
- Scope `workspace/memory/docs/**` -> `incoming-raw`
- Scope `workspace/memory/log/**` -> `incoming-raw`
- Scope `workspace/projects/**` -> `incoming-raw`
- Scope `workspace/tools/**` -> `compatibility-only`
- Scope `tests/**` -> `compatibility-only`
