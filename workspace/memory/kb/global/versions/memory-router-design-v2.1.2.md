---
type: [KB:GLOBAL]
title: "记忆分层路由总设计 v2.1.2"
created: 2026-03-03 03:49
updated: 2026-03-04 12:00
source: Manual
confidence: high
tags: [memory, router, design, canonical]
version: v2.1.2
status: active
last_verified: 2026-03-04
related: []
---

# 记忆分层路由总设计 v2.1.2（Canonical）

> ⚠️ **唯一真相声明**
> 本文档为记忆分层路由的最高规范。若与其他文档冲突，**以此为准**。

> 适用对象：OpenClaw / Molt（主权工作区：`/Users/busiji/passkills`）
> 目标：让记忆写入与检索**永远可控、可追溯、可治理**；避免历史噪音污染；避免启动/读取过重导致 compaction 死循环。
> 范围：本文件只定义"路由规划/硬规则/索引治理"，不包含执行话术；执行接口见 `ROUTER.md (OPS)`。

---

## 设计目标（铁律）

1. 任何可复用内容必须落到**唯一 canonical**（不再散写）。
2. 历史噪音与错误记忆**永不污染索引**。
3. 默认读取永远轻量（避免 compaction / 启动过重死循环）。
4. 每一次写入必须**可追溯来源与落点**（可审计）。

一句话执行铁律（建议写在 `ROUTER.md` 最顶部）：

> **事实写 log，可复用写 kb，产物写 projects，错误写 invalid，历史写 raw；索引核心看 docs+kb，archive-memory 永不入库。**

---

## 一、记忆层级与职责（五层，永不混用）

### L0 Boot 层（启动器）
**文件**：`workspace/MEMORY.md`
**职责**：只定义 Load Order + Hard Rules。
**硬约束**：
- 极短（<20 行），永不膨胀
- 不承载历史/知识/日志
- 允许保留版本行：`boot_version: v2.1.2`

> 注：CRUD / 冲突模板属于 KB（L3），不要塞进 Boot。

---

### L1 State 层（工作台）
**文件**：`workspace/NOW.md`（**唯一允许覆写**的文件）
**职责**：当前状态 / 今日重点 / 下一步 / 阻塞 / Health。
**硬规则**：
- NOW.md 必须保持短（人类 30 秒可读完）
- 覆写更新（overwrite）只允许发生在 NOW.md

---

### L2 Fact 层（事实流水）
**文件**：`workspace/memory/log/YYYY-MM-DD.md`（append-only）
**职责**：记录"今天发生了什么"。
**原则**：
- 宁多勿少，但必须结构化
- 只追加，不覆写
- `keywords:` 行必须存在，且中文关键词空格分隔（提升召回）

---

### L3 Knowledge 层（知识库 / 可复用 / Canonical）
**目录**：`workspace/memory/kb/**`（read-first-CRUD）
**子目录分类**：
- `kb/projects/<project-or-node>.md`
- `kb/lessons/<topic>.md`
- `kb/decisions/YYYY-MM-DD-<slug>.md`
- `kb/preferences/user.md` 与 `kb/people/*.md`
- `kb/global/<topic>.md`（跨项目共享规范/口径/原则）

**原则**：
- KB 是唯一真相层（canonical）
- log 仅为原始流水（非真相）
- KB 写入必须 read-first-CRUD：`NOOP / ADD / UPDATE / CONFLICT`
- UPDATE 禁止删除旧内容（只允许 `superseded` 标记）
- CONFLICT 必须显式保留两版并等待人类裁决

#### global 写入优先级规则（必须）
- 跨项目稳定原则/统一规范 → `kb/global/`
- 项目/节点专属细节/参数/流程 → `kb/projects/`
- 禁止重复：项目细节禁止写入 global；global 禁止堆叠项目参数表。

---

### L4 Cold 层（冷存储，不索引）
**根目录**：`/Users/busiji/passkills/archive-memory/**`
**子分类**：
- `raw/**` → 旧日志、旧 MEMORY、过程 dump、临时导出、历史资料
- `invalid/INVALID-MEMORY.md` → 冲突/错误/废弃记忆（证据留存，永不删除）

**原则**：
- 越大越好，但**永远不进入任何索引范围**
- invalid 是证据仓库，不是 canonical；canonical 永远在 KB

---

## 二、唯一真相路由表（Write Targets）

### [LOG] 事实流水（中期）
- 落点：`workspace/memory/log/YYYY-MM-DD.md`
- 约束：append-only；必须包含 `keywords:`（中文空格分隔）

### [KB:*] 可复用知识（长期）
- [KB:PROJECT] → `workspace/memory/kb/projects/<project-or-node>.md`
- [KB:LESSON] → `workspace/memory/kb/lessons/<topic>.md`
- [KB:DECISION] → `workspace/memory/kb/decisions/YYYY-MM-DD-<slug>.md`
- [KB:PREF] → `workspace/memory/kb/preferences/user.md`
- [KB:PEOPLE] → `workspace/memory/kb/people/<name>.md`
- [KB:GLOBAL] → `workspace/memory/kb/global/<topic>.md`

约束：先读再写（read-first-CRUD）；禁止覆盖写；禁止删除旧内容（只能 superseded 或 CONFLICT）

### [ARTIFACT] 项目产物区（非记忆层）
- 落点：`workspace/projects/**`
- 桥接：长交付文档顶部加指针
  `> CANONICAL: workspace/memory/kb/projects/<...>.md`

### [ARCHIVE:*] 冷存储（不索引）
- [ARCHIVE:RAW] → `/Users/busiji/passkills/archive-memory/raw/**`
- [ARCHIVE:INVALID] → `/Users/busiji/passkills/archive-memory/invalid/INVALID-MEMORY.md`

---

## 三、索引范围规划（Index Scope）
- ✅ 必须：`workspace/memory/docs/**` + `workspace/memory/kb/**`
- 🟡 可选：`workspace/memory/log/**`、`workspace/memory/reflections/**`、`workspace/memory/system/**`、`workspace/memory/short-index.md`、`workspace/memory/actions/**`
- ❌ 禁止：`archive-memory/**`、任何 `.archive/**`、`workspace/projects/**`

---

## 四、short-index 定义（必须）
**文件**：`workspace/memory/short-index.md`
**定位**：启动/快速导航用短索引（不是知识正文，不是历史摘要）。
**阈值报警**：>2KB 或 >60 行 → 提示整理（不自动整理）

---

## 五、可选目录准入（仅当必要时引入）

### reflections（可选）
`workspace/memory/reflections/**`：日终复盘、冲突仲裁草案、运行异常复盘。

### system（可选但推荐）
`workspace/memory/system/**`：可观测性（例如 errors.log）；禁止当杂物目录。

### actions（可选但允许；用于任务收件箱）
`workspace/memory/actions/**`：
- 仅允许"任务收件箱/行动条目"，**不承载知识正文**
- 默认 append-only（避免与 NOW 覆写冲突）
- 任务完成不要求回写删除（可在条目中标记 done）

---

## 六、冲突与错误记忆（不删，但不污染）
- canonical 永远在 KB：冲突必须在 KB 文件中显式 CONFLICT（保留两版）
- 错误/废弃版本进入 invalid：复制到 `INVALID-MEMORY.md` 证据留存
- 裁决后收敛：KB 只保留唯一一致口径（减少分叉）

---

## 七、读取策略（性能与半条命防线）
- 常态默认：只读 `NOW`（轻量）
- 新 run 允许一次"读启动"：NOW → ROUTER(OPS) → short-index → 今日 log（必要片段）
- 异常（timeout/compacting）：先恢复 run，再按冷启动一次读取

---

## 八、Frontmatter 规范（仅 KB 强制）
`workspace/memory/kb/**` 必须包含 YAML frontmatter：

```yaml
---
title: "..."
created: YYYY-MM-DD HH:MM
updated: YYYY-MM-DD HH:MM
source: [ROUTER|Agent|Manual|link]
confidence: high|medium|low
tags: [..]
related: [..]
version: v1.0
status: active|superseded|conflict
last_verified: YYYY-MM-DD
---
```

---

*文档版本：v2.1.2*
*更新日期：2026-03-04*
*状态：active*
