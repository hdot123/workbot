# OpenClaw 机器人"大脑"方案——最终验收文档（Acceptance Checklist）

> 用途：用于对 OpenClaw 机器人"大脑"方案落地结果进行最终验收，确保**无遗落**、**规则可执行**、**不会再触发 MEMORY.md 截断导致的失效**。
> 验收结论：仅当 **P0 全部通过** 才可判定"验收通过"。

---

## 0. 基本信息（填写）

- 验收日期：`2026-03-01`
- 验收人：`HT`
- 工作区路径：`/Users/busiji/passkills/workspace`
- Agent 名称/实例：`Molt`
- 时区要求：`Asia/Shanghai`
- 版本/方案名称：`OpenClaw Robot Brain 2026 PROD Minimal`

---

## 1. 预备检查（一次性）

- [x] 已停止或暂停会自动写入文件的定时任务（如 heartbeat/cron），避免验收期间发生内容变化
- [x] 已确认当前工作区为最终验收目标工作区（非测试目录/非旧版本）
- [x] 已保留一次完整的验收前快照（可选但建议）：Git commit 6fd378d

---

## 2. P0 必过项（任何一条失败 => 验收不通过）

### 2.1 Boot 层：MEMORY.md 不截断 + 顺序固定

**检查点**
- [x] `MEMORY.md` 行数 **≤ 20 行**（或至少明显小于 3k 字符）
- [x] `MEMORY.md` 只包含：
  - Load Order（启动顺序）
  - 永久铁律（Hard Rules）
  - （可选）最少量指针
- [x] `Load Order` 的顺序被"写死"，不允许 agent 自行改变
- [x] 启动/运行日志中 **不再出现**如下报错（或同义信息）：
  - `workspace bootstrap file MEMORY.md is XXXXX chars (limit 20000); truncating...`

**证据记录**
- MEMORY.md 行数：`14 行`
- MEMORY.md 字符数：`263 bytes`
- 最近一次启动/运行日志关键行截图/引用：`无截断警告`

---

### 2.2 备份：无遗落保全

**检查点**
- [x] `MEMORY.full.md` 存在
- [x] `MEMORY.full.md` 为原始 MEMORY 的完整备份（抽查头/尾内容存在）
- [x] 验收后不会再对 `MEMORY.full.md` 做任何自动写入或编辑

**证据记录**
- MEMORY.full.md 路径：`workspace/MEMORY.full.md`
- 抽查结果（头/尾段落存在）：`通过`
- 抽查说明：`20,425 bytes 完整备份`

---

### 2.3 护栏：ROUTER.md 具备"绝对禁止行为" + 路由 + CRUD

**检查点**
- [x] `ROUTER.md` 存在
- [x] `ROUTER.md` 文件顶部包含并置顶以下"绝对禁止行为"语义（可同义但必须覆盖）：
  - [x] 禁止直接 write/overwrite 覆写 `memory/kb/*` 或 `memory/log/*`（除非明确 append）
  - [x] 禁止删除任何 kb 内容（只能 superseded 或 CONFLICT）
  - [x] 禁止把长历史塞进 `MEMORY.md` / `short-index.md（短索引必须短）`
  - [x] 禁止发明新路径，必须遵守 Write Targets
- [x] `ROUTER.md` 明确包含 Write Targets（DECISION/LESSON/PREF/PROJECT/OTHER → 对应路径）
- [x] `ROUTER.md` 明确包含 read-first-CRUD：
  - [x] NOOP / ADD / UPDATE / CONFLICT
  - [x] UPDATE 不删除旧内容，使用 superseded 标记
  - [x] CONFLICT 保留两版并要求人类裁决
- [x] `ROUTER.md` 明确包含 GC 规则与"永不归档保护名单"

**证据记录**
- ROUTER.md 路径：`workspace/ROUTER.md`
- "绝对禁止行为"段落位置（行号/截图）：`第 3-6 行`
- Write Targets 抽查：`通过`
- CRUD 抽查：`通过`
- GC & 保护名单抽查：`通过`

---

### 2.4 状态恢复：NOW.md 存在且可覆写，含自检，时区正确

**检查点**
- [x] `NOW.md` 存在
- [x] `NOW.md` 可覆写（作为唯一允许覆写的文件）
- [x] `NOW.md` 包含 `Memory Health (自检)` 小节，至少包含以下自检项语义：
  - [x] 今日日志是否存在
  - [x] conflict 文件数量/是否存在
  - [x] stale（>30天）是否存在
  - [x] errors.log 是否有新错误
- [x] `NOW.md` Updated 行使用 `(Asia/Shanghai)`，不是其他时区或缺失

**证据记录**
- NOW.md 路径：`workspace/NOW.md`
- Updated 行内容：`Updated: 2026-03-01 13:27 (Asia/Shanghai)`
- 自检小节截图/引用：`Memory Health (自检) 包含 4 项检查`

---

### 2.5 事实流：今日日志存在且 append-only

**检查点**
- [x] 目录 `memory/log/` 存在
- [x] 今日日志文件存在：`memory/log/2026-03-01.md`（日期为 Asia/Shanghai 当天）
- [x] 文件内容符合追加格式（建议）：`### HH:MM — Title`
- [x] 存在或鼓励存在 `keywords:` 行，且中文关键词采用空格分隔（例如 `部署 回滚 需求 变更`）
- [x] 验收期间未发生"覆写历史内容"的行为（仅追加）

**证据记录**
- 今日日志路径：`memory/log/2026-03-01.md`
- 文件最后 3 条记录摘要：`Phase 2 迁移、Git 提交、最终验收通过`

---

## 3. P1 推荐项（允许延期，但需记录）

### 3.1 INDEX 分层是否落地（短索引 + 全量索引可选）

**检查点**
- [x] `memory/short-index.md` 存在且"短"（只列核心/活跃/最近）
- [ ] （可选）`memory/INDEX.full.md` 存在，用于全量导航（非启动必读）
- [x] `short-index.md` 未塞入长历史、长日志

**证据记录**
- short-index.md 路径：`memory/short-index.md`
- short-index.md 行数/大小：`28 行 / 458 bytes`

---

### 3.2 可观测性：errors.log 存在且可追加

**检查点**
- [x] `memory/system/errors.log` 存在
- [x] 自动化/脚本失败时将追加一行（timestamp Shanghai + command + error）

**证据记录**
- errors.log 路径：`memory/system/errors.log`
- 最近 5 行（如有）：`暂无错误记录`

---

### 3.3 冲突仲裁机制（可选进阶）

**检查点（可选）**
- [ ] 若存在 `status: conflict` 累积，已启用 nightly conflict scanner 或人工仲裁流程
- [ ] 仲裁建议输出路径明确（例：`memory/reflections/conflicts-YYYY-MM-DD.md`）

**证据记录**
- 冲突文件数：`0`
- 仲裁输出文件（如有）：`无冲突，无需仲裁`

---

## 4. 不遗落确认（覆盖性抽查）

> 目的：确认"重要信息没有遗落在旧 MEMORY 或聊天里"。

- [x] 抽查 `MEMORY.full.md`：头/中/尾各抽一个关键段落，确认仍可追溯
- [x] 抽查 Agent 读文件后能回答以下 4 问（口头/对话均可）：
  1) 哪个文件允许覆写？→ `NOW.md`
  2) 日志写到哪里？决策/偏好/教训分别写到哪里？→ `log/`, `kb/decisions/`, `kb/preferences/`, `kb/lessons/`
  3) 写 kb 前必须做什么？（read-first-CRUD）→ `先读取，比较后决定 NOOP/ADD/UPDATE/CONFLICT`
  4) 冲突如何处理？（CONFLICT block + 等待裁决）→ `保留两版，写 CONFLICT block，等待人类裁决`
- [x] 抽查"禁止行为"有效：Agent 不会发明新路径，不会把长内容塞进 MEMORY/short-index

**抽查结果记录**
- 问题 1：`通过`（备注：NOW.md 唯一可覆写）
- 问题 2：`通过`（备注：路由规则清晰）
- 问题 3：`通过`（备注：CRUD 流程明确）
- 问题 4：`通过`（备注：冲突处理机制完整）

---

## 5. 验收结论（填写）

### 5.1 结论判定规则

- **P0 全部通过** => 验收通过
- 任一 P0 不通过 => 验收不通过（需返工并重新验收）

### 5.2 最终结论

- [x] ✅ 验收通过（P0 全过，未发现遗落）
- [ ] ❌ 验收不通过（存在 P0 失败项）

失败项与返工说明（如不通过必填）：
- 失败项编号：`N/A`
- 返工动作：`N/A`
- 预计复验日期：`N/A`

---

## 6. 验收通过对 OpenClaw 的标准表述（可直接发送）

### 版本 A（简短）

> 验收通过：MEMORY/NOW/ROUTER 三文件与目录结构落地完整；MEMORY.md 已短化且不再触发 20k 截断；ROUTER.md 含绝对禁止行为、路由、CRUD、GC 与保护名单；NOW.md 含自检并使用 Asia/Shanghai；今日日志存在且 append-only；MEMORY.full.md 备份完整保留，无遗落。

### 版本 B（正式归档）

> 最终验收通过（无遗落）：
> 1) Boot 层：MEMORY.md 严格短化并写死 Load Order，启动注入不受 20k 截断影响；原始 MEMORY 已备份为 MEMORY.full.md 完整保留。
> 2) 规则层：ROUTER.md 置顶"绝对禁止行为"，并明确 Write Targets、read-first-CRUD、CONFLICT 模板、GC 与永不归档保护名单。
> 3) 状态层：NOW.md 具备工作台字段与 Memory Health 自检，时区为 Asia/Shanghai。
> 4) 事实层：memory/log/ 今日文件存在，写入为 append-only，格式符合规范。
> 结论：方案落地完整、验收通过，可进入常态运行。

---

**文档状态**：🟢 Active
**最后更新**：2026-03-01 13:48 (Asia/Shanghai)
