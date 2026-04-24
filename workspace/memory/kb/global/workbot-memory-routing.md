# Workbot Memory Routing Rules

Status: rule-only, records-cleared
Created: 2026-04-12
Updated: 2026-04-24
Notes: 历史材料统一路由到仓库根 `history-projects/`，不再以 `frontstage quarantine` 作为正式历史根。

## Routing Rules
- Rule layer is read-first for policy decisions.
- Historical materials route to `/Users/busiji/workbot/history-projects/` as the sole formal history root, not canonical memory.
- `workspace/frontstage/` and its quarantine trees are legacy residue staging only, not a formal history root.
- Locked project domains are read-only unless owner authorizes change.

## Truth Basis

### Source Refs
- `/Users/busiji/workbot/workspace/INDEX.md`
- `/Users/busiji/workbot/history-projects/INDEX.md`
- `/Users/busiji/workbot/workspace/memory/docs/INDEX.md`

### Authority Refs
- `/Users/busiji/workbot/workspace/project-map/legal-core-map.md`
- `/Users/busiji/workbot/workspace/memory/kb/global/workbot-truth-model.md`

### Evidence Refs
- `/Users/busiji/workbot/workspace/tools/memory_hook_gateway.py`
- `/Users/busiji/workbot/workspace/tools/validate_memory_system.py`

### Conflict Status
- `resolved`
