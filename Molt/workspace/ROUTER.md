# ROUTER.md — Memory Write Rules (OPS, v2.1.2)

> ✅ CANONICAL: `workspace/memory/kb/global/memory-router-design.md`
> 本文件是 **执行接口/操作协议（OPS）**：定义"怎么分类→写到哪→怎么写→用什么快捷指令"。
> 若与 canonical 冲突：以 canonical 为准；本文件仅调整命令与模板，不重定义层级/索引口径。

---

## 绝对禁止行为（一旦违反=系统错误）

- ❌ 禁止 overwrite 任何 `workspace/memory/kb/**`（KB 只能 read-first-CRUD）
- ❌ 禁止删除任何 `workspace/memory/kb/**` 的旧内容（只能 `superseded` 或 `CONFLICT`）
- ❌ 禁止把长历史/长日志塞进 `workspace/MEMORY.md` 或 `workspace/memory/short-index.md`
- ❌ 禁止把 `archive-memory/**` 纳入索引或当作真相层
- ❌ 禁止自己发明新路径；写入必须走下方 Write Targets

---

## Write Targets（Routing）

| 标签 | 目标路径 | 写入方式 |
|------|---------|---------|
| [LOG] | `workspace/memory/log/YYYY-MM-DD.md` | append-only |
| [KB:DECISION] | `workspace/memory/kb/decisions/YYYY-MM-DD-<slug>.md` | new file |
| [KB:LESSON] | `workspace/memory/kb/lessons/<topic>.md` | append; read-first-CRUD |
| [KB:PEOPLE] | `workspace/memory/kb/people/<name>.md` | append; read-first-CRUD |
| [KB:PREF] | `workspace/memory/kb/preferences/user.md` | append; read-first-CRUD |
| [KB:PROJECT] | `workspace/memory/kb/projects/<project-or-node>.md` | append; read-first-CRUD |
| [KB:GLOBAL] | `workspace/memory/kb/global/<topic>.md` | append; read-first-CRUD |
| [ARTIFACT] | `workspace/projects/**` | normal files; add CANONICAL pointer |
| [ARCHIVE:RAW] | `/Users/busiji/passkills/archive-memory/raw/**` | write allowed; never index |
| [ARCHIVE:INVALID] | `/Users/busiji/passkills/archive-memory/invalid/INVALID-MEMORY.md` | append evidence; never index |
| [ACTION] | `workspace/memory/actions/inbox.md` | append-only |

> 注：[ACTION] 是任务收件箱（可选目录 actions），不承载知识正文；知识必须进 KB。

---

## Log Entry Format（append-only）

```md
### HH:MM — Title #tags

- what: …
- why: …
- result: …

keywords: 部署 回滚 需求 变更 支付 服务
```

> 中文关键词必须空格化

---

## KB 写入协议（Read-First-CRUD）

写入任何 `workspace/memory/kb/**` 前：

1. **Read** 目标文件（不存在则创建）
2. **Compare** → `NOOP / ADD / UPDATE / CONFLICT`
3. **UPDATE**：旧段落标记 `superseded`（禁止删除）
4. **CONFLICT**：保留两版并加冲突块，等待人工裁决

### Conflict Block Template

```md
> ⚠️ CONFLICT (YYYY-MM-DD)
> A: (older claim + source)
> B: (new claim + source)
> Needed: human decision (choose A / choose B / merge)
```

---



---

*Updated: 2026-03-01*

---

## 快捷指令（Short Commands）

> 默认规则：除非明确说"写 KB/写决策/更 NOW"，否则**只写 [LOG]**（append-only）。

### 读取类

* `读 NOW`：只读 `workspace/NOW.md` 后回答
* `读启动`：按顺序读 NOW → ROUTER(本文件) → short-index → 今日 log（必要片段）

### 记录类

* `记 log：<一句话>`：追加到 `workspace/memory/log/YYYY-MM-DD.md`（自动加时间戳与 keywords）
* `更 NOW：<一句话>`：覆写更新 `workspace/NOW.md`（Today/Next/Blockers/Health）

### 写入 KB（必须先读再写）

* `写偏好：<一句话>` → [KB:PREF]
* `写画像：<一句话>` → [KB:PEOPLE]（建议文件名 `user-profile.md` 或 `<name>.md` 以团队约定为准）
* `写项目：<一句话>` → [KB:PROJECT]
* `写决策：<一句话>` → [KB:DECISION]（新建 decisions；并在 short-index 仅挂短链接）
* `写经验：<topic>：<一句话>` → [KB:LESSON]
* `写全局：<topic>：<一句话>` → [KB:GLOBAL]

### 任务收件箱

* `TODO：<一句话>`：追加到 `workspace/memory/actions/inbox.md`（自动带日期与 #todo）；不自动改 NOW.md

---

## 默认启动策略（避免 compaction）

* 默认只执行 `读 NOW`
* 只有触发条件才 `读启动`：

  1. 断线/重启/换 run
  2. compact 后答非所问
  3. 高风险写入前（写决策/改规则/批量变更）
  4. 检测到截断/timeout
  5. 明确指令"读启动"

---

## ARTIFACT 桥接规则（必须）

当 `workspace/projects/**` 下存在长交付件/报告：

* 允许保留原文
* 但在文件顶部追加一行指针（不改正文）：

  * `> CANONICAL: workspace/memory/kb/projects/<...>.md`
* 未来检索/更新以 KB 为准（projects 仅产物）

---

*Updated: 2026-03-04*
*OPS version: v2.1.2*
