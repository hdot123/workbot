---
type: [KB:GLOBAL]
title: "记忆分层路由总设计 v2.1.1"
created: 2026-03-03 03:49
source: Manual
confidence: high
tags: [memory, router, design, source-material, upstream]
version: v2.1.1
status: retired
last_verified: 2026-03-03
updated: 2026-03-08
related: []
---

# 记忆分层路由总设计 v2.1.1（融合优化版）

> RETIRED HISTORICAL VERSION
> 本文件是上游 `passkills` 体系的旧版本，只保留历史来源价值，不具备当前 `workbot` 本地默认解释权。
>
> 当前 `workbot` 的正式 global canonical 以 [memory/kb/global/INDEX.md](/Users/busiji/workbot/memory/kb/global/INDEX.md) 的 “Current Local Canonical” 为准。
>
> 适用对象：OpenClaw / Molt（主权工作区：`/Users/busiji/passkills`）
> 目标：让记忆写入与检索**永远可控、可追溯、可治理**；避免历史噪音污染；避免启动/读取过重导致 compaction 死循环。
> 范围：本文件只定义"路由规划/硬规则"，不包含行动流程（流程另文）。

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

**文件**：`MEMORY.md`

**职责**：只定义 Load Order + Hard Rules。

**硬约束**：
- 极短（<20 行），永不膨胀
- 不承载历史/知识/日志
- 允许保留一行人工核对版本号：`boot_version: v2.1.1`

> 备注：CRUD 规则属于 KB，不属于 Boot（避免 Boot 演化膨胀）。

---

### L1 State 层（工作台）

**文件**：`NOW.md`（**唯一允许覆写**的文件）

**职责**：当前状态 / 今日重点 / 下一步 / 阻塞 / Health。

**硬规则**：
- NOW.md 必须保持短（人类 30 秒可读完）
- 覆写更新（overwrite）只允许发生在 NOW.md

**强烈推荐：日切防膨胀（不强制自动化）**

目的：防止 NOW 长期堆积导致 bloat、触发 compaction 读取负担。

简易做法（每日首启/日终二选一执行即可）：
- 从昨日 NOW 提取 `Today / Blockers / Next 3 Actions` 各 1–3 行摘要
- 追加写入当日 `memory/log/YYYY-MM-DD.md`
- 将 NOW 覆写回模板（保留 Mission + 空白 Today/Next/Blockers/Health）

---

### L2 Fact 层（事实流水）

**文件**：`memory/log/YYYY-MM-DD.md`（append-only）

**职责**：记录"今天发生了什么"。

**原则**：
- 宁多勿少，但必须结构化
- 只追加，不覆写
- `keywords:` 行必须存在，且中文关键词空格分隔（提升召回）

---

### L3 Knowledge 层（知识库 / 可复用）

**目录**：`memory/kb/**`（read-first-CRUD）

**子目录分类**：
- `kb/projects/<project-or-node>.md` → 项目/节点持续手册（节点角色/IP/端口/账号/运行方式/验证方式/常用命令）
- `kb/lessons/<topic>.md` → 通用经验/排错套路（跨项目复用）
- `kb/decisions/YYYY-MM-DD-<slug>.md` → 重大决策（不可逆/影响面大）
- `kb/preferences/user.md` 与 `kb/people/*.md`
- `kb/global/**` → 跨项目共享知识（全局原则/通用规范/统一口径）

**职责**：记录"以后还会用到的结论/手册/经验/决策"。

**原则**：
- KB 是唯一真相层（canonical）
- log 仅为原始流水（非真相）
- KB 写入必须 read-first-CRUD：`NOOP / ADD / UPDATE / CONFLICT`
- UPDATE 禁止删除旧内容（只允许 `superseded` 标记）
- CONFLICT 必须显式保留两版并等待人类裁决

#### global 写入优先级规则（必须）

- **写入优先级**：
  1) 跨项目稳定原则/统一规范 → `kb/global/`
  2) 项目/节点专属细节/参数/流程 → `kb/projects/`
- **禁止重复**：项目细节禁止写入 global；global 禁止堆叠项目参数表。

---

### L4 Cold 层（冷存储，不索引）

**根目录**：`/Users/busiji/passkills/archive-memory/**`

**子分类**：
- `raw/**` → 旧日志、旧 MEMORY、过程 dump、临时导出、历史资料
- `invalid/INVALID-MEMORY.md` → 冲突/错误/废弃记忆（证据留存，永不删除）

**原则**：
- 越大越好，但**永远不进入任何索引范围**
- invalid 是"证据仓库"，不是 canonical；canonical 永远在 KB

---

## 二、唯一真相路由表（Write Targets）

> 所有写入必须首先被分类为以下之一；禁止"随便写到哪里"。

### 1) [LOG] 事实流水（中期）

- **落点**：`memory/log/YYYY-MM-DD.md`
- **适用**：执行过程摘要、结果、临时结论、短故障记录摘要
- **硬约束**：append-only；必须包含 `keywords:`（中文空格分隔）

---

### 2) [KB:*] 可复用知识（长期）

- **[KB:PROJECT]** → `memory/kb/projects/<project-or-node>.md`
- **[KB:LESSON]** → `memory/kb/lessons/<topic>.md`
- **[KB:DECISION]** → `memory/kb/decisions/YYYY-MM-DD-<slug>.md`
- **[KB:PREF]** → `memory/kb/preferences/user.md`
- **[KB:PEOPLE]** → `memory/kb/people/<name>.md`
- **[KB:GLOBAL]** → `memory/kb/global/<topic>.md`

**硬约束**：
- 先读再写（read-first-CRUD）
- 禁止覆盖写（overwrite）
- 禁止删除旧内容（只能 superseded 或 CONFLICT）

---

### 3) [ARTIFACT] 项目产物区（非记忆层）

- **落点**：`projects/**`
- **允许**：脚本、manifest、配置、README、运行命令清单、交付件
- **禁止**：把"最终 Runbook/部署手册/复盘/经验总结"当作唯一长期真相

**桥接规则（必须）**：
- 若 `projects/**` 中存在长文档（交付件/报告），允许保留
- 但必须在文件顶部加一行指针（不改正文）：
  - `> CANONICAL: memory/kb/projects/<...>.md`
- 未来检索以 KB 为准（projects 仅为原始产物/交付件）

---

### 4) [ARCHIVE:*] 冷存储（不索引）

- **[ARCHIVE:RAW]** → `/Users/busiji/passkills/archive-memory/raw/**`
- **[ARCHIVE:INVALID]** → `/Users/busiji/passkills/archive-memory/invalid/INVALID-MEMORY.md`

---

## 三、索引范围规划（Index Scope）

> 目标：官方标准 + 我们 KB，且不被历史/错误污染。

- ✅ **索引核心范围（必须）**：`memory/docs/**` + `memory/kb/**`
- 🟡 **允许附带（可选）**：`memory/log/**`、`memory/reflections/**`、`memory/system/**`、`memory/short-index.md`
- ❌ **禁止索引范围（硬禁）**：`archive-memory/**`、任何 `.archive/**`、`projects/**`

---

## 四、short-index 定义（必须明确，避免索引口径漂移）

**文件**：`memory/short-index.md`

**定位**：启动/快速导航用的"短索引"（**不是知识正文，不是历史摘要**）。

**允许内容**：
- Core：指向 `kb/preferences`、关键 `kb/projects`、关键 `kb/global`
- Active：当前活跃 lessons
- Latest：最近 N 个 decisions（建议 N=5）

**禁止内容**：
- 长历史、长复盘、长摘要、完整日志粘贴
- 把 short-index 当第二个 MEMORY/INDEX.full

**约束阈值（用于报警，不自动整理）**：
- `short-index.md` > 2KB **或** > 60 行 → 报警提示需要整理（不自动整理）

---

## 五、reflections / system 目录准入（仅当必要时引入）

> 符合原则："任何新目录必须有理由"。这两个目录允许存在，但只在必要时使用，避免变成杂物堆。

### reflections（可选）

**目录**：`memory/reflections/**`

**仅在以下场景使用**：
- 日终复盘（提炼 log → kb）
- 冲突仲裁建议（输出裁决草案）
- 索引/运行异常的复盘记录（用于后续改进）

### system（可选但推荐保留）

**目录**：`memory/system/**`

**仅用于可观测性**（建议只保留 `errors.log` 等）：
- 禁止把 system 当杂物目录
- 任何新增文件必须说明"为何属于可观测性"

---

## 六、冲突与错误记忆（不删，但不污染）

### 冲突处理统一策略

1. **canonical 永远在 KB**：冲突必须在 KB 文件中显式 CONFLICT（保留两版）
2. **错误/废弃版本进入 invalid**：将被判定为错/废弃的版本复制到 `INVALID-MEMORY.md`（证据留存）
3. **最终裁决后收敛**：KB canonical 只保留唯一一致口径（减少未来分叉）

> 重点：invalid 用来"找回证据"，不是用来"指导未来"。

---

## 七、读取策略规划（性能与半条命防线）

### 默认策略（常态）

- 默认读取：`读NOW`（轻量）
- 不自动全读 docs/log/kb

### 冷启动（新 run）策略

- 每个新 run 允许一次轻量"读启动"：
  - NOW → ROUTER → short-index → 今日 log（仅必要片段）
- 读启动时禁止复述读取清单，只输出一句"读启动完成"进入任务

### 异常策略

- 异常（timeout / Connection error / compacting）时不做重读
- 先恢复 run（重启/换 run），恢复后按"冷启动一次"读取

---

## 八、Frontmatter 规范（治理与不破坏 append-only）

### 强制（仅 KB）

`memory/kb/**` 必须包含 YAML frontmatter，用于治理与可信度：

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

*文档版本：v2.1.1*
*创建日期：2026-03-03*
*状态：active*
