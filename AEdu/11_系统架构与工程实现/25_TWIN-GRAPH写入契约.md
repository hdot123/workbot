# TWIN-GRAPH 写入契约

> 文档编号：ARCH-025  
> 版本：V1.0  
> 创建日期：2026-03-21  
> 最后更新：2026-03-21  
> 维护人：系统架构与工程实现负责人  
> 状态：已冻结（首轮骨架开发基线）  
> 用途：支撑 GRAPH 首轮骨架开发准入复核  
> 变更方式：后续修改需通过新一轮准入评审

---

## 1. 文档目的与边界

本文档用于定义 TWIN 向 GRAPH 提供写入对象的最小稳定契约，回答以下问题：

1. Fact / Relation / Event / Snapshot 的来源分别是什么
2. 哪些内容能直接写图谱
3. 哪些内容只能进入时序记忆或索引
4. 缺字段时如何处理
5. TWIN 与 GRAPH 在写入环节各自承担什么责任

本文档只定义模块契约级边界，不展开为：

- API 字段协议文档
- 图数据库 Schema 文档
- MQ 主题设计文档
- 检索 Prompt 文档

---

## 2. 契约适用范围

本契约只适用于以下冻结范围：

| 维度 | 冻结值 |
|------|--------|
| 地区 | 安徽省 |
| 学段 | 高中 |
| 年级 | 高一 |
| 学科 | 物理 |
| 教材版本 | `PHY_PEP_G1_V1` |
| 输入源 | 家长文本、老师反馈文本、单页扫描/OCR |
| 上游基线 | KB + INGEST + TWIN 已冻结基线 |
| 下游消费方 | GRAPH 首轮骨架开发 |

超出冻结范围的对象，不属于本契约允许写入范围。

---

## 3. TWIN 向 GRAPH 提供的对象清单

TWIN 首轮只向 GRAPH 提供以下对象：

| 对象 | 来源 | 说明 |
|------|------|------|
| `state_update_event` | TWIN 状态更新结果 | 描述某次状态更新发生了什么 |
| `learning_event_ref` | 上游标准学习事件引用 | 作为 GRAPH Event 的来源依据 |
| `current_state_fact_set` | TWIN 当前态事实快照 | 供 GRAPH 形成 Fact 写入 |
| `risk_signal_set` | TWIN 风险层结果 | 供 GRAPH 形成风险相关 Fact / Relation |
| `quality_signal_set` | TWIN 数据质量层结果 | 供 GRAPH 形成质量相关 Fact |
| `state_snapshot_ref` | TWIN 某时点状态快照 | 供 GRAPH 形成 Snapshot |
| `graph_write_refs` | 合法的 `chapter_refs / knowledge_refs / anchor_refs` | 用于落图和检索挂载 |

TWIN 不向 GRAPH 直接提供原始文本、原始 OCR 全文或面向前台的解释文案。

---

## 4. 哪些对象写入图谱

### 4.1 直接写入 Fact

满足以下条件时，允许写入 Fact：

- 当前态事实已被 TWIN 确认
- `student_id`、`curriculum_version_id`、`trace_id` 完整
- 事实有明确来源事件或快照

典型对象：

- 当前风险等级
- 当前重点知识点
- 当前学科状态摘要
- 数据质量评分

### 4.2 直接写入 Relation

满足以下条件时，允许写入 Relation：

- 关系具有稳定结构意义
- 关系两端对象均可识别
- 关系不依赖单条低置信事件才能成立

典型关系：

- `Student uses CurriculumVersion`
- `Chapter contains KnowledgePoint`
- `Student has_state StateSnapshot`
- `Student has_risk_signal RiskSignal`

### 4.3 直接写入 Event

满足以下条件时，允许写入 Event：

- 对应标准学习事件或 TWIN 状态更新事件
- `event_id / event_type / event_time / trace_id` 完整
- 事件状态为 `success`、`degraded` 或人工复核后的合法回写

### 4.4 直接写入 Snapshot

满足以下条件时，允许写入 Snapshot：

- 来自 TWIN 当前态或阶段快照
- 快照具有明确时点
- 快照可以回溯到事实集合与来源事件集合

---

## 5. 哪些对象仅保留在 TWIN

以下对象本轮只保留在 TWIN，不直接写入 GRAPH 主图：

| 对象 | 原因 |
|------|------|
| `review_needed` 中间裁定状态 | 仍处复核中，不适合固化为长期图谱结论 |
| `hold` 中间状态 | 只是临时等待，不是长期记忆对象 |
| 仅供当前态计算的临时中间变量 | 无长期解释价值 |
| 前台口径摘要文案 | 属于 OBS 责任，不属于 GRAPH 对象 |
| 推演准备中间变量 | 属于 SIM 责任，不属于首轮 GRAPH |

---

## 6. 哪些对象进入时序记忆

以下对象优先进入时序记忆：

| 对象 | 条件 | 是否直接建关系图 |
|------|------|------------------|
| 标准学习事件 | 事件合法、可追溯 | 是，作为 Event 写入，并进入时间线 |
| 状态变化记录 | 有明确前后差异 | 是，作为 Event + Snapshot 组合进入 |
| 行为摘要变化 | 有时间窗口和趋势意义 | 进入时序记忆，可不扩建复杂关系 |
| 风险变化记录 | 有清晰来源和时间 | 进入时序记忆，并写入最小风险关系 |
| 降级事件 | 结构不完整但可保留演化信息 | 进入时序记忆，限制关系写入 |

---

## 7. 必需字段

以下字段缺失时，GRAPH 不允许进入主写入链：

| 字段 | 作用 | 缺失处理 |
|------|------|----------|
| `student_id` | 定位学生子图 | `reject` |
| `trace_id` | 审计追踪 | `reject` |
| `curriculum_version_id` | 范围校验与知识挂载 | `reject` |
| `event_id` 或 `snapshot_id` | 写入主标识 | `reject` |
| `event_time` 或 `snapshot_time` | 时间轴定位 | `reject` |
| `source_status` | 判断 success / degraded / review / reject | `reject` |
| `raw_input_ref` | 回溯原始证据 | `reject` |

---

## 8. 可选字段

以下字段缺失不必然阻断主写入链：

| 字段 | 用途 | 缺失处理 |
|------|------|----------|
| `chapter_refs` | 章节级落位 | 可降级 |
| `knowledge_refs` | 知识点级落位 | 可降级，但限制 Fact / Relation |
| `anchor_refs` | 教材锚点回贴 | 可缺失 |
| `behavior_tags` | 行为语义补充 | 可缺失 |
| `quality_signal_set` | 质量层扩展 | 可缺失 |
| `risk_signal_set` | 风险层扩展 | 条件缺失可不写风险关系 |

---

## 9. 缺失字段的处理规则

| 场景 | 是否允许继续 | 处理方式 |
|------|--------------|----------|
| `knowledge_refs` 缺失，但 `chapter_refs` 合法 | 允许 | 只写 Chapter 级 Event / Snapshot，不写 KnowledgePoint 级强关系 |
| `chapter_refs` 缺失，但 `knowledge_refs` 合法 | 允许 | 继续，Chapter 可由 KB 反查 |
| `knowledge_refs` 与 `chapter_refs` 同时缺失，但事件仍可表达行为变化 | 允许 | 进入时序记忆，限制图谱关系写入 |
| `trace_id` 缺失 | 不允许 | `reject` |
| `student_id` 缺失 | 不允许 | `reject` |
| `raw_input_ref` 缺失 | 不允许 | `reject` |

---

## 10. 非法输入处理规则

以下情况直接视为非法输入：

1. 范围外地区、学段、年级、学科、教材版本。
2. 来源不在三类冻结输入源白名单内。
3. `review_needed` 未经人工复核直接伪装成成功对象。
4. 事件或快照缺少最小追溯链路。
5. 试图将原始长文本、自由推断、前台文案直接写图谱。

非法输入处理：

- 不进入 GRAPH 主写入链
- 只记录拒绝日志
- 不生成 Fact / Relation / Snapshot / Retrieval Unit

---

## 11. 降级策略

### 11.1 可降级写入

以下情况允许降级：

- 只有 Chapter 级定位，没有稳定 KnowledgePoint
- 行为层有明确变化，但知识层无法安全落位
- OCR 结果可形成事件与快照，但知识引用仍偏弱

降级后的规则：

- 可以写 Event
- 可以写 Snapshot
- 可以写有限 Fact
- 不得写强 KnowledgePoint 关系
- 不得直接生成高确定性风险结论

### 11.2 不可降级写入

以下情况不得用“降级”掩盖：

- 缺失 `student_id`
- 缺失 `trace_id`
- 缺失 `raw_input_ref`
- 事件状态本身已是 `rejected`

---

## 12. 责任边界

| 模块 | 负责 | 不负责 |
|------|------|--------|
| KB | 提供知识底座主数据和引用有效性 | 学生状态更新、图谱对象裁定 |
| INGEST | 解析原始输入并生成标准事件 | 长期图谱写入 |
| TWIN | 形成当前态、状态变化、风险和质量摘要 | 长期图谱主存储和回滚 |
| GRAPH | 根据契约落图、建版本链、做最小检索准备 | 回改上游判断、产出前台解释文案 |

---

## 13. 验收要点

本契约的最小验收要点如下：

1. GRAPH 只消费冻结范围内的 TWIN 输出对象。
2. GRAPH 不直接消费原始输入。
3. 关键必需字段缺失的对象必须被拦住。
4. `knowledge_refs` 缺失时，只允许有限降级，不允许伪造知识图谱关系。
5. `review_needed` 中间状态不得直接固化进长期图谱结论。
6. 所有成功写入对象都能追溯到 `trace_id / raw_input_ref / source_event_ref`。

---

## 14. 修订历史

| 版本 | 日期 | 变更内容 | 责任人 |
|------|------|----------|--------|
| V1.0 | 2026-03-21 | 首次补齐 TWIN-GRAPH 写入契约，作为 GRAPH 首轮准入支撑文档 | 系统架构与工程实现负责人 |
