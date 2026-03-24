# ROUTER.md — Workbot Memory Write Rules

> CANONICAL: `memory/kb/global/memory-router-design.md`
> 本文件是根级 `workspace/` 的执行接口，只负责分类、落点和写入协议。
> 若与 canonical 冲突，以 canonical 为准。

## Root Scope
- 当前总控工作区：`/Users/busiji/workbot/workspace`
- `agents/molt/workspace/` 是来源工作区，不是默认写入目标

## 绝对禁止行为
- 禁止 overwrite 任何 `memory/kb/**`
- 禁止删除 `memory/kb/**` 的旧内容，只能 `superseded` 或 `CONFLICT`
- 禁止把长历史塞进 `MEMORY.md` 或 `memory/short-index.md`
- 禁止把 `../archive-memory/**` 当真相层或索引层
- 禁止继续把总项目知识写回 `agents/molt/workspace/`

## Write Targets

| 标签 | 目标路径 | 写入方式 |
|------|---------|---------|
| [LOG] | `memory/log/YYYY-MM-DD.md` | append-only |
| [KB:DECISION] | `memory/kb/decisions/YYYY-MM-DD-<slug>.md` | new file |
| [KB:LESSON] | `memory/kb/lessons/<topic>.md` | read-first-CRUD |
| [KB:PEOPLE] | `memory/kb/people/<name>.md` | read-first-CRUD |
| [KB:PREF] | `memory/kb/preferences/user.md` | read-first-CRUD |
| [KB:PROJECT] | `memory/kb/projects/<project>.md` | read-first-CRUD |
| [KB:PROJECT-SUB] | `memory/kb/projects/<project>/*.md` | read-first-CRUD |
| [KB:GLOBAL] | `memory/kb/global/<topic>.md` | read-first-CRUD |
| [KB:LONGTERM] | `memory/kb/longterm/**` | read-first-CRUD |
| [ARTIFACT] | `projects/**` | normal files; add canonical pointer when needed |
| [ARCHIVE:RAW] | `../archive-memory/raw/**` | write allowed; never index |
| [ARCHIVE:INVALID] | `../archive-memory/invalid/INVALID-MEMORY.md` | append evidence; never index |
| [ACTION] | `memory/actions/inbox.md` | append-only |

## Routing Principles
- 项目真相优先写 `memory/kb/projects/`
- 跨项目稳定规则优先写 `memory/kb/global/`
- 长期稳定记忆优先写 `memory/kb/longterm/`
- 研究与外部参考资料写 `memory/docs/`
- 交付件、报告、实施材料写 `projects/`

## KB 写入协议
1. 先读目标文件
2. 判断 `NOOP / ADD / UPDATE / CONFLICT`
3. `UPDATE` 仅允许追加 `superseded` 标记，禁止删除旧内容
4. `CONFLICT` 必须显式保留两版并等待人工裁决

## Conflict Block

```md
> ⚠️ CONFLICT (YYYY-MM-DD)
> A: older claim + source
> B: new claim + source
> Needed: human decision
```

## 启动策略
- 默认只读 `NOW.md`
- 需要重建上下文时再按 `MEMORY.md` 的顺序读启动链
- 高风险写入前先读 `ROUTER.md` + 目标 canonical

## Artifact Bridge
- `projects/**` 下的长文档可以保留
- 若存在对应 canonical，应在顶部加：
  - `> CANONICAL: memory/kb/projects/<...>.md`

---
Updated: 2026-03-24
OPS version: v3.0-workbot
