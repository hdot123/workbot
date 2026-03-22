# TWIN 状态更新映射表

> 文档编号：TWIN-014  
> 版本：V1.0  
> 创建日期：2026-03-21  
> 最后更新：2026-03-21  
> 维护人：学生数字孪生负责人  
> 状态：已冻结（首轮骨架开发基线）  
> 用途：支撑 TWIN 首轮骨架开发  
> 变更方式：后续修改需通过新一轮准入评审

---

## 1. 文档目的

本文档用于定义 TWIN 在首轮骨架开发中的状态更新映射规则，回答以下问题：

1. 什么事件更新什么层
2. 哪些更新可以直接落库
3. 哪些更新只能标记待复核
4. 哪些事件不能直接改学生状态
5. `review_needed / hold / reject` 如何区分

---

## 2. 状态更新总原则

TWIN 状态更新必须遵循以下原则：

1. 先校验输入契约，再进入状态更新。
2. 先更新直接事实，再刷新派生状态。
3. 先更新当前态，再记录长期引用或下游广播。
4. 风险层不能脱离事实层单独漂浮更新。
5. 范围外、低置信、冲突事件不得直接改写学生关键状态。

在首轮骨架开发中，可直接落库的主要是：

- 基础绑定引用
- 事实层结果
- 行为层摘要
- 数据质量层摘要
- 状态变化记录与审计引用

只能在事实稳定后派生刷新的主要是：

- 演化层摘要
- 风险层摘要

---

## 3. 事件类型总表

| 事件类型 | 典型来源 | 默认结果 | 是否允许直接更新 |
|----------|----------|----------|------------------|
| `homework_result_event` | 老师反馈、扫描/OCR | `success / degraded` | 条件允许 |
| `correction_followup_event` | 老师反馈、家长文本 | `success / degraded` | 允许 |
| `teacher_feedback_event` | 老师反馈 | `success / degraded / review_needed` | 条件允许 |
| `parent_feedback_event` | 家长文本 | `degraded / review_needed` | 条件允许 |
| `scan_ocr_result_event` | 单页扫描/OCR | `success / degraded / review_needed` | 条件允许 |
| `reviewed_learning_event` | 人工复核回写 | `success` | 允许 |

说明：

- `success` 允许进入完整更新链。
- `degraded` 允许进入受限更新链。
- `review_needed` 不进入主状态链，只进入复核链。
- `reject` 不属于消费后的事件类型，而是输入门禁阶段的直接结论。

---

## 4. 事件类型 → 更新层级映射表

| 事件类型 | 事实层 | 行为层 | 演化层 | 风险层 | 数据质量层 | 默认处理 |
|----------|--------|--------|--------|--------|------------|----------|
| `homework_result_event` | 直接 | 条件 | 条件 | 条件 | 直接 | `success` |
| `correction_followup_event` | 条件 | 直接 | 条件 | 条件 | 直接 | `success / degraded` |
| `teacher_feedback_event` | 条件 | 直接 | 条件 | 条件 | 直接 | `success / degraded / review_needed` |
| `parent_feedback_event` | 否 | 直接 | 条件 | 条件 | 直接 | `degraded / review_needed` |
| `scan_ocr_result_event` | 条件 | 否 | 条件 | 否 | 直接 | `success / degraded / review_needed` |
| `reviewed_learning_event` | 直接 | 直接 | 条件 | 条件 | 直接 | `success` |

解释：

- “直接”表示符合输入契约即可写入本层。
- “条件”表示需要满足引用完整性、事实充足性或置信度门槛。
- “否”表示本轮不得直接由该类事件改写本层。

---

## 5. 五层更新体系

### 5.1 事实层

| 项目 | 内容 |
|------|------|
| 触发条件 | 事件为 `success` 或允许的 `degraded`，且关键上下文合法 |
| 输入对象 | `event_summary`、`score_payload`、`chapter_refs`、`knowledge_refs`、`curriculum_version_id` |
| 变更结果 | `latest_homework_summary`、`latest_exam_summary`、`current_focus_points`、`current_knowledge_snapshots` 更新 |
| 是否直接落库 | 是 |

事实层允许直接写入的前提是：

- 事件不在 `review_needed`
- 事件不在 `reject`
- 事件满足冻结范围

### 5.2 行为层

| 项目 | 内容 |
|------|------|
| 触发条件 | 事件包含行为线索，例如订正、拖延、响应、复做、完成节奏 |
| 输入对象 | `behavior_tags`、`event_summary`、老师或家长观察摘要 |
| 变更结果 | `execution_rhythm_summary`、`correction_followup_summary`、`feedback_response_summary` 更新 |
| 是否直接落库 | 是 |

行为层允许在 `degraded` 路径下更新，但必须满足：

- 输入语义足够清楚
- 该更新不冒充知识掌握结论

### 5.3 演化层

| 项目 | 内容 |
|------|------|
| 触发条件 | 事实层或行为层发生有效变化，且存在时间窗口可比较 |
| 输入对象 | 当前事件、最近事件窗口、现有状态快照 |
| 变更结果 | `subject_trend_summary`、`knowledge_trend_summary`、`rhythm_trend_summary` 更新 |
| 是否直接落库 | 条件落库 |

演化层不是原始输入直写层，必须在事实层或行为层稳定后再刷新。

### 5.4 风险层

| 项目 | 内容 |
|------|------|
| 触发条件 | 事实层与行为层已有足够支撑，或 `reviewed_learning_event` 明确确认风险 |
| 输入对象 | 结果数据、行为摘要、演化摘要、`mastery_gap` 相关数据 |
| 变更结果 | `current_risk_labels`、`mastery_gap_status`、`risk_trend_summary` 更新 |
| 是否直接落库 | 条件落库 |

风险层更新的强约束：

- 单条低置信事件不能直接抬升高风险状态
- 没有知识事实支撑时，不能直接改写知识掌握风险
- 没有结果型数据时，不能直接改写 `mastery_gap`

### 5.5 数据质量层

| 项目 | 内容 |
|------|------|
| 触发条件 | 任何被 TWIN 接触到的事件都会刷新质量判断 |
| 输入对象 | 置信度、字段完整度、来源质量、事件密度、时效性 |
| 变更结果 | `data_completeness_score`、`recency_score`、`event_density_score`、`state_confidence_score` 更新 |
| 是否直接落库 | 是 |

数据质量层可由 `success / degraded / review_needed` 事件驱动，但：

- `reject` 事件只写错误日志，不刷新学生当前态质量分

---

## 6. 每类更新的触发条件、输入对象与结果

| 更新类型 | 触发条件 | 输入对象 | 变更结果 |
|----------|----------|----------|----------|
| 事实层更新 | 事件合法、范围合法、关键引用或结构化结果可用 | 结构化事件结果、KB 引用 | 当前事实快照变化 |
| 行为层更新 | 行为线索明确且不需冒充知识结论 | 行为标签、文本摘要 | 节奏与跟进摘要变化 |
| 演化层更新 | 存在最近窗口与可比较历史 | 当前事件 + 历史状态 | 趋势摘要变化 |
| 风险层更新 | 风险有事实支撑且不依赖纯猜测 | 结果数据、行为摘要、演化摘要 | 风险标签与风险趋势变化 |
| 数据质量层更新 | 事件进入 TWIN 处理路径 | 置信度、完整度、时效性 | 质量分变化 |

---

## 7. 不允许更新的情况

以下情况不允许直接更新 StudentTwinAgent 核心状态：

1. 原始家长文本或老师原文未经 INGEST 标准化。
2. 只有 `anchor_refs`，没有稳定章节或知识语义。
3. 事件低置信且无人工复核回写。
4. 事件范围超出深圳 / 高中 / 高一 / 物理 / `PHY_PEP_G1_V1`。
5. 事件试图直接给出高风险决策性判断，但无事实证据支撑。
6. 同一业务事实与现有状态发生严重冲突且未复核。
7. 事件已被标为 `reject`。

---

## 8. `review_needed / hold / reject` 的区分

| 状态 | 含义 | 是否更新当前态 | 典型场景 |
|------|------|----------------|----------|
| `review_needed` | 需要人工裁定后才能决定是否更新 | 否 | 低置信、引用冲突、语义歧义、高风险争议 |
| `hold` | 事件合法但当前证据不足，暂缓关键更新 | 部分允许 | 缺知识引用但可保留行为线索 |
| `reject` | 输入非法或范围不合法，直接丢弃 | 否 | 关键字段缺失、来源非法、范围外事件 |

进一步说明：

- `review_needed` 是“需要人工判断”
- `hold` 是“先不改关键状态，但保留待处理上下文”
- `reject` 是“无权进入 TWIN”

---

## 9. 状态流转边界

首轮骨架开发只要求以下状态边界可执行：

| 状态流转 | 触发条件 |
|----------|----------|
| `pending_binding -> cold_start` | 学生基础绑定完成 |
| `cold_start -> active` | 首个合法事件被消费 |
| `active -> stable` | 已有连续合法事件支撑基础趋势 |
| `active -> review_needed` | 出现严重冲突或连续低置信事件 |
| `stable -> review_needed` | 稳定对象出现关键绑定或引用冲突 |
| `review_needed -> active` | 人工复核完成且问题解除 |
| `review_needed -> stable` | 人工复核完成且恢复为稳定态 |

本轮不把以下状态作为准入目标：

- `simulation_ready`
- `archived`

它们可以保留在总体设计中，但不作为首轮骨架开发的必须完成项。

---

## 10. 审计与追溯要求

每次进入状态更新链的事件，至少要保留：

- `last_event_ref`
- `trace_id`
- `raw_input_ref`
- 更新前后状态差异摘要
- 更新结果状态（`success / degraded / review_needed / hold / reject`）

当事件进入 `review_needed` 或 `hold` 时，还必须保留：

- `review_ticket_ref` 或待处理引用
- 降级或复核原因

---

## 11. 修订历史

| 版本 | 日期 | 变更内容 | 责任人 |
|------|------|----------|--------|
| V1.0 | 2026-03-21 | 首次冻结 TWIN 首轮状态更新映射规则 | 学生数字孪生负责人 |
