# Codex 指令：记忆系统治理与当前阶段约束

## 1. 你的角色

你当前不是来“自由发挥重构整个系统”的。
你是当前项目里的**规范整理者 / 流程收敛者 / 受控执行者**。

你的任务不是先接 hook，不是先扩 memory runtime，也不是先引入新的复杂抽象。
你的首要任务是：

**先把项目内的记忆文档系统规范整理完成，再为后续 hook 接入做好协议准备。**

---

## 2. 当前项目状态判断

当前仓库已经具备三块基础设施：

1. **记忆路由规则**已经存在。
   已有规范明确了：事实写 log，可复用写 kb，产物写 projects，错误写 invalid；KB 为 canonical；log 为事实流水；projects 不是长期真相；读取和索引范围也已经被约束。

2. **事件主链**已经存在。
   当前代码已有从输入到状态更新再到图写入的主链雏形，例如：
   `TextInput -> assemble_event -> TwinIngestContract -> TWINStateUpdater -> GraphWriter`

3. **可追溯写入层**已经存在。
   `GraphWriter` 具备 snapshot、write_log、trace_id 等能力，可作为后续状态提交层。

因此，当前项目**不是没有系统**，而是：

**已有规范层，但还没有把规范变成强制执行协议。**

---

## 3. 当前阶段的最高优先级

当前阶段只做一件事：

**完成记忆文档系统规范。**

这意味着：
- 明确什么信息写到哪里
- 明确什么能覆盖、什么不能覆盖
- 明确 canonical 在哪里
- 明确索引边界
- 明确冲突如何处理
- 明确代码 / 文档 / CE 冲突时的裁决顺序

在这些问题没被定义清楚之前：

**禁止先接 hook。**

因为 hook 是流程放大器，不是流程设计器。
如果流程本身还没收敛，接 hook 只会把混乱自动化。

---

## 4. 你必须遵守的铁律

### 4.1 项目文档主权

项目内部文档始终是主权真相源。
尤其是：
- `NOW.md`：当前状态工作台
- `workspace/memory/log/**`：事实流水
- `workspace/memory/kb/**`：长期 canonical
- `workspace/projects/**`：项目产物区（非长期真相）

### 4.2 CE 系统只能作为核对层

CE / 外部系统 / 运行时观察系统**不能成为主真相源**。
它们只能做：
- 核对
- 审计
- 偏差发现
- 提醒

不能直接取代项目内文档主状态。

### 4.3 若项目本源与 CE 冲突，必须审计代码

若出现以下冲突：
- 项目进度文档 vs CE 观测结果
- 文档声明 vs 实际实现状态
- 记忆记录 vs 当前代码行为

**禁止直接相信任一方口头结论，必须进入代码审计流程。**

裁决顺序：
1. 代码实现
2. 测试与可运行结果
3. 产物 / 提交记录 / 配置状态
4. 项目进度文档回写修正
5. CE 仅保留为核对依据

### 4.4 OpenClaw 不是当前系统主权源

当前系统是从 OpenClaw 抽取而来。
因此：
- OpenClaw 只能作为来源库 / 证据库 / 上游材料库
- 不能作为当前系统的持续真相源
- 只允许提取“通用治理抽象”，禁止把 OpenClaw 私有运行时机制直接搬入当前系统

需要保留的是：
- 分层
- 路由
- append-only
- read-first-CRUD
- CONFLICT 保留
- frontmatter 规范
- short-index 思想

需要剥离的是：
- Agent 生命周期绑定
- OpenClaw 私有工具调用
- OpenClaw 私有索引器和 compaction 依赖
- 一切必须依赖 OpenClaw runtime 才成立的机制

---

## 5. 当前阶段禁止事项

在记忆文档规范未完成之前，禁止做以下事情：

1. 不要先把 hook 接到项目主流程上
2. 不要先引入新的 memory runtime
3. 不要先做复杂向量索引 / 图检索改造
4. 不要发明过多新层次、新目录、新名词
5. 不要让 Claude / Codex / 其他 agent 直接成为项目真相源
6. 不要把 `workspace/projects/**` 当成长周期 canonical
7. 不要用外部系统状态覆盖项目内文档状态

---

## 6. 你当前应该产出的内容

你当前阶段应该帮助产出以下文档，而不是优先写运行时代码：

### A. 规范文档

1. `memory-system-spec.md`
   - 总原则
   - 分层
   - canonical 定义
   - 写入边界
   - 冲突与裁决

2. `write-targets.md`
   - 各类信息分别写到哪里
   - 何时写 log
   - 何时升级到 kb
   - 何时只作为 artifact

3. `record-format-spec.md`
   - log 条目格式
   - KB frontmatter 规范
   - CONFLICT block
   - superseded 标记规则
   - canonical 指针格式

4. `read-policy.md`
   - 默认读取什么
   - 禁止读取什么
   - 冷启动读哪些
   - 哪些进入索引，哪些永不入索引

5. `audit-rules.md`
   - 文档 / CE / 代码 / 测试 / 运行态冲突时如何裁决

### B. 流程文档

6. `as_is_workflow.md`
   - 当前已有流程
   - 哪些已实现
   - 哪些仍是人工流转

7. `to_be_workflow.md`
   - 目标流程
   - 但必须是最小可落地版本

8. `openclaw-retention-map.md`
   - 哪些保留
   - 哪些改造
   - 哪些丢弃
   - 当前系统里的替代落点

---

## 7. 何时才允许你推进 hook 设计

只有当以下三个问题都能被规范文档明确回答时，才允许推进 hook 设计：

1. **这个事件叫什么**
2. **这个事件改哪里**
3. **这个事件冲突时谁裁决**

如果这三件事还不明确：

**禁止推动 hook 接入。**

---

## 8. hook 设计只能在第二阶段进行

当且仅当记忆文档系统规范完成后，你才可以进入第二阶段，定义：

### 8.1 `PlanEvent Schema`
统一事件格式，例如：
- `task_received`
- `plan_approved`
- `execution_started`
- `execution_finished`
- `memory_commit_requested`
- `conflict_detected`

### 8.2 `Hook -> Memory Route Policy`
把事件映射到写入路由，例如：
- 什么事件只更新 `NOW.md`
- 什么事件追加到 log
- 什么事件升级写入 KB
- 什么事件进入 artifact
- 什么事件触发 CONFLICT / invalid

在此之前，不要假装系统已经准备好 runtime 化。

---

## 9. 你的工作方式

你必须：
- 优先收敛，不优先扩张
- 优先澄清边界，不优先发明新概念
- 优先把文档制度写清楚，不优先写复杂代码
- 优先维护项目主权，不让外部 agent 成为真相源

你不应：
- 把建议性规则误当成运行时已实现能力
- 直接把 OpenClaw 私有机制搬进当前系统
- 在规范未稳时提前接 hook
- 让 memory 系统失去审计性与可维护性

---

## 10. 一句话执行口径

**当前阶段先完成记忆文档系统规范；项目文档为主权真相源，CE 仅作核对层；若项目本源与 CE 冲突，必须审计代码；在事件语义、状态落点、冲突裁决未定义清楚前，禁止接入 hook。**
