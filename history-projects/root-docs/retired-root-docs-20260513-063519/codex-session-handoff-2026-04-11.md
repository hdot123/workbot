# Codex 会话交接：2026-04-11

## 1. 这份文档的用途

这不是普通设计文档。
这是给 Codex 的**会话交接摘要**，用于承接当前关于“记忆系统 / 文档主权 / hook 接入顺序”的讨论结果。

Codex 在继续工作前，应先阅读：

1. `docs/codex-memory-governance-instructions.md`
2. 本文档 `docs/codex-session-handoff-2026-04-11.md`
3. `workspace/memory/kb/global/memory-router-design-v2.1.1.md`

---

## 2. 本次会话已经达成的核心结论

### 2.1 当前项目不是没有系统，而是“规范层已存在，触发层未建立”

当前仓库已经具备：
- 记忆路由规则
- 事件主链
- GraphWriter 可追溯写入层

但仍缺：
- 把“规则”变成“强制执行协议”的运行时闸门

所以当前问题不是继续堆 memory 文档，而是：

**文档规范已经有了，但尚未 runtime 化。**

---

### 2.2 当前 `workspace/memory/**` 更像文档型记忆系统，而不是事件驱动 runtime

现状特征：
- 有规则
- 有 kb
- 有 log
- 有 inbox
- 有人工收件箱与手工流转痕迹

说明它目前更像：
- 文档治理系统
- 记忆路由规范系统

而不是：
- 事件驱动 memory runtime

---

### 2.3 “先规划、再执行、再沉淀”以后可以通过 hook 强制化，但现在不能先接 hook

原则已经明确：
- Claude / Codex / OpenCode 这类工具以后可以通过 hook 实现“强制规划路线”
- 但当前项目阶段还没到可以安全接 hook 的程度

原因：
- 事件语义还没统一完
- 状态落点还没完全制度化
- 冲突裁决顺序还需要在文档中固化

因此：

**当前阶段禁止先接 hook。**

---

### 2.4 当前第一优先级不是写 runtime，而是完成记忆文档系统规范

已经明确：

**第一步 = 把记忆文档系统规范完成。**

不是先做：
- hook
- memory runtime
- 向量索引扩展
- 新的复杂抽象

而是先把以下问题写清楚：
- 什么信息写到哪
- 什么可以覆写，什么必须 append-only
- canonical 在哪里
- projects 与 kb 的关系
- 冲突时如何裁决
- 代码 / 文档 / CE 冲突时谁说了算

---

### 2.5 项目内置进度文档必须永远是主权真相源

已确认：
- 项目内部进度文档应当为主
- CE 系统只能作为核对层、审计层、提醒层
- 外部系统不能成为主状态源

因此：

**项目文档 > CE 系统**

但这不是说文档永远无条件正确。

---

### 2.6 若项目本源与 CE 冲突，必须审计代码

本次会话已明确：

若以下内容冲突：
- 项目进度文档
- CE 观测结果
- 记忆记录
- 实际运行行为

则：

**禁止直接相信任一方结论，必须审计代码。**

裁决顺序：
1. 代码实现
2. 测试与可运行结果
3. 产物 / 配置 / 提交记录
4. 项目进度文档回写修正
5. CE 保留为核对依据

也就是说：

**最终裁决权不在文档，不在 CE，而在可验证实现事实。**

---

### 2.7 当前系统是从 OpenClaw 抽出来的，但 OpenClaw 不能继续作为当前系统真相源

OpenClaw 的角色已经明确：
- 来源库
- 证据库
- 上游材料库

不是：
- 当前系统主权运行地
- 当前系统真相源

从 OpenClaw 只能提取：
- 分层治理抽象
- 路由原则
- append-only / read-first-CRUD / CONFLICT / frontmatter 等方法论

不能继续直接搬入：
- 私有 runtime 机制
- 生命周期绑定
- 私有索引 / flush / memory_search / memory_get 依赖

---

## 3. 已经形成的阶段判断

### 阶段 1（当前阶段）

**完成记忆文档系统规范**

目标：
- 先把文档制度写清楚
- 先把真相边界固定下来
- 先把写入规则和读取规则固定下来
- 先把冲突裁决规则固定下来

### 阶段 2（下一阶段）

在文档规范稳定后，才允许推进：
- `PlanEvent Schema`
- `Hook -> Memory Route Policy`

### 阶段 3（更后阶段）

在前两者稳定后，才允许接入：
- 强制规划 hook
- memory commit hook
- orchestration policy layer

---

## 4. Codex 当前不应做的事情

当前阶段，Codex **不要**：

1. 不要先把 hook 接上主流程
2. 不要先发明新的复杂 memory runtime
3. 不要继续扩张目录与概念层级
4. 不要让外部系统替代项目真相源
5. 不要把 OpenClaw 私有机制直接搬进当前系统
6. 不要把 `workspace/projects/**` 当成长周期 canonical
7. 不要跳过规范，直接写 orchestration 代码

---

## 5. Codex 当前应该做的事情

当前阶段，Codex **应该**：

1. 整理并收敛记忆文档系统规范
2. 明确各类信息的 write targets
3. 明确 log / kb / artifact / invalid / raw 的边界
4. 明确 NOW / short-index / docs / kb / log 的读取规则
5. 明确 CE / 文档 / 代码 / 测试 / 运行态冲突时的裁决顺序
6. 形成 OpenClaw 保留 / 改造 / 丢弃映射
7. 整理当前流程（as-is）与目标流程（to-be），但目标流程必须保持最小可落地

---

## 6. Codex 当前建议优先产出的文档

建议优先产出：

1. `memory-system-spec.md`
2. `write-targets.md`
3. `record-format-spec.md`
4. `read-policy.md`
5. `audit-rules.md`
6. `as_is_workflow.md`
7. `to_be_workflow.md`
8. `openclaw-retention-map.md`

说明：
这些文档优先级高于 hook 代码。

---

## 7. 什么时候才允许 Codex 推动 hook 设计

只有当下面三个问题在文档里都有明确答案时，才允许进入 hook 设计：

1. 这个事件叫什么
2. 这个事件改哪里
3. 这个事件冲突时谁裁决

只要这三个问题仍有任意一个不明确：

**禁止 Codex 推动 hook 接入。**

---

## 8. 一句话交接口径

**当前项目的首要任务不是接 hook，而是先完成记忆文档系统规范；项目文档为主权真相源，CE 仅作核对层；若项目本源与 CE 冲突，必须审计代码；OpenClaw 只作为来源库；在事件语义、状态落点、冲突裁决未定清楚前，禁止推进 hook。**
