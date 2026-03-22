# GRAPH 对象写入与更新映射表

> 文档编号：GRAPH-012  
> 版本：V1.0  
> 创建日期：2026-03-21  
> 最后更新：2026-03-21  
> 维护人：记忆与图谱引擎负责人  
> 状态：已冻结（首轮骨架开发基线）  
> 用途：支撑 GRAPH 首轮骨架开发准入复核  
> 变更方式：后续修改需通过新一轮准入评审

---

## 1. 文档目的

本文档用于定义 GRAPH 首轮骨架开发中，对象如何写入、更新、回滚和追溯，回答以下问题：

1. 什么对象进入图谱
2. 什么对象进入时序记忆
3. 什么对象只做索引
4. 哪些写入失败必须阻断，哪些允许降级

---

## 2. 写入总原则

1. 先事件，后事实，再关系，最后快照与检索单元。
2. 只写冻结范围内的结构化对象，不写原始长文本。
3. 当前态可替代，历史链不可抹掉。
4. 低置信或关系不稳时，优先降级到时序记忆，不强行建边。
5. 所有写入都必须留 `trace_id`、来源对象和版本信息。

---

## 3. 对象类型总表

| 对象类型 | 主要来源 | 首轮是否纳入 |
|----------|----------|--------------|
| Fact | TWIN 当前态事实、风险与质量摘要 | 是 |
| Relation | KB 稳定知识关系、TWIN 输出的稳定结构关系 | 是 |
| Event | INGEST 标准事件、TWIN 状态更新事件 | 是 |
| Snapshot | TWIN 当前态快照、阶段快照 | 是 |
| Index / Retrieval Unit | GRAPH 为 GraphRAG 准备的最小检索单元 | 是 |

---

## 4. 对象类型 → 写入位置映射表

| 对象类型 | 写入位置 | 写入动作 | 失败策略 |
|----------|----------|----------|----------|
| Fact | 图谱事实层 | `create / supersede / invalidate` | 关键事实失败则阻断 |
| Relation | 图谱关系层 | `create / upsert / invalidate` | 稳定关系失败则阻断，弱关系失败可降级 |
| Event | 时序记忆层 + 事件对象层 | `append / invalidate` | Event 写入失败则阻断 |
| Snapshot | 状态快照层 | `create / supersede` | Snapshot 失败则阻断当前批次 |
| Index / Retrieval Unit | 检索索引层 | `upsert / invalidate` | 可降级，不阻断主写入 |

---

## 5. Event 写入规则

### 5.1 触发条件

- 收到合法标准学习事件
- 收到 TWIN 合法状态更新事件
- 收到人工复核回写事件

### 5.2 输入对象

- `learning_event_ref`
- `state_update_event`
- `reviewed_learning_event`

### 5.3 写入结果

- 形成可追溯 Event
- 进入学生时间线
- 为 Fact / Relation / Snapshot 提供来源

### 5.4 不允许写入的情况

- 范围外事件
- 缺失 `event_id / event_time / trace_id / raw_input_ref`
- 原始全文直接冒充 Event

### 5.5 结论

Event 是主链入口，写入失败必须阻断后续 Fact / Relation / Snapshot 写入。

---

## 6. Fact 写入规则

### 6.1 触发条件

- TWIN 已确认当前态事实
- 事实可追到 Event 或 Snapshot
- 事实属于冻结范围内的学生、物理学科和 `PHY_PEP_G1_V1`

### 6.2 输入对象

- `current_state_fact_set`
- `risk_signal_set`
- `quality_signal_set`

### 6.3 写入结果

- 生成或替换当前有效 Fact
- 旧版本标记 `superseded`
- 形成当前事实链

### 6.4 不允许写入的情况

- 仅凭单条低置信事件直接生成高确定性事实
- 缺失关键追溯链
- 事实内容超出冻结范围

### 6.5 写入失败处理

- 当前关键事实失败：阻断
- 衍生辅助事实失败：可降级记录错误并继续

---

## 7. Relation 写入规则

### 7.1 触发条件

- KB 已提供稳定知识关系
- TWIN 输出了稳定结构关系
- Fact / Event 已经成功写入

### 7.2 输入对象

- `knowledge_refs`
- `chapter_refs`
- `curriculum_version_id`
- 稳定状态关系映射

### 7.3 写入结果

- 生成最小稳定关系边
- 为 GraphRAG 提供结构骨架

### 7.4 不允许写入的情况

- 仅基于低置信 OCR 候选直接写强关系
- `knowledge_refs` 不稳定或与 `chapter_refs` 冲突
- 把前台解释逻辑当结构关系入图

### 7.5 写入失败处理

- 核心知识关系失败：若影响主链解释，阻断
- 弱关系或增强关系失败：可降级，仅保留 Event / Snapshot

---

## 8. Snapshot 写入规则

### 8.1 触发条件

- TWIN 当前态成功刷新
- 关键状态变化完成
- 需要固化某时点状态

### 8.2 输入对象

- `state_snapshot_ref`
- 当前有效 Fact 集
- 关键 Event 引用集合

### 8.3 写入结果

- 形成可回溯的状态快照
- 作为检索和恢复入口

### 8.4 不允许写入的情况

- 当前态本身未稳定
- `review_needed` 中间状态未经复核就固化
- 快照缺少时间和来源

### 8.5 写入失败处理

- 快照失败则阻断该批次的“当前态可用”结论

---

## 9. Index / Retrieval Unit 写入规则

### 9.1 触发条件

- Event / Fact / Relation / Snapshot 已成功写入
- 需要为单学生最小检索闭环准备上下文

### 9.2 输入对象

- 当前有效 Fact
- 关键 Relation
- 近窗口关键 Event
- 有效 Snapshot

### 9.3 写入结果

- 形成 GraphRAG 最小检索单元
- 支撑当前态解释召回

### 9.4 不允许写入的情况

- 试图直接把原始全文灌成 Retrieval Unit
- 上游对象尚未成功落位

### 9.5 写入失败处理

- 可降级，不阻断图谱主写入
- 但必须标记“检索未就绪”

---

## 10. 不允许写入的情况总表

| 场景 | 处理 |
|------|------|
| 范围外输入 | `reject` |
| 缺失 `student_id / trace_id / raw_input_ref` | `reject` |
| 低置信 OCR 直接建强知识关系 | `review_needed` 或降级 |
| `review_needed` 中间状态直接固化 | `reject` |
| 原始长文本直接入图 | `reject` |
| 下游解释文案、建议结论、推演结果提前入图 | `reject` |

---

## 11. review_needed / hold / reject 的区分

| 状态 | 含义 | GRAPH 处理 |
|------|------|------------|
| `review_needed` | 语义冲突或低置信，需要人工裁定 | 不固化关键 Fact / Relation，可保留待复核 Event |
| `hold` | 输入合法但暂不足以安全更新 | 保留 Event，不写强 Fact / Relation |
| `reject` | 输入非法或关键链路缺失 | 不进入主写入链 |

---

## 12. 状态流转边界

标准对象流转边界如下：

`Event 成功`  
→ `Fact 可确认则写入 / 替换`  
→ `Relation 稳定则写入`  
→ `Snapshot 固化`  
→ `Index / Retrieval Unit 刷新`

若在任一环节发生阻断：

- Event 阶段失败：后续全部终止
- Fact / Snapshot 阶段失败：当前批次终止
- Relation 阶段部分失败：允许降级，但不得伪造结构完整
- Index 阶段失败：允许主链成功，但标记检索未就绪

---

## 13. 回滚与版本控制要求

1. Event 采用 append + invalidate，不物理删除。
2. Fact 采用 supersede，保留版本链。
3. Relation 采用 activate / invalidate，保留失效痕迹。
4. Snapshot 采用新建版本，不覆盖旧快照。
5. Retrieval Unit 可 upsert，但必须保留来源版本引用。

---

## 14. 审计与追溯要求

所有成功写入对象至少保留：

- `trace_id`
- `raw_input_ref`
- `source_event_ref`
- `object_version_id`
- `previous_version_id`（如适用）
- `created_at / updated_at`

所有失败或回滚动作至少保留：

- 失败类型
- 失败对象
- 失败原因
- 是否触发补偿或回滚

---

## 15. 修订历史

| 版本 | 日期 | 变更内容 | 责任人 |
|------|------|----------|--------|
| V1.0 | 2026-03-21 | 首次补齐 GRAPH 对象写入与更新映射表，作为 GRAPH 首轮准入支撑文档 | 记忆与图谱引擎负责人 |
