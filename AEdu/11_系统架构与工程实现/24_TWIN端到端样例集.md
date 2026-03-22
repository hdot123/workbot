# TWIN 端到端样例集

> 文档编号：ARCH-024  
> 版本：V1.0  
> 创建日期：2026-03-21  
> 最后更新：2026-03-21  
> 维护人：系统架构与工程实现负责人  
> 状态：已冻结（首轮骨架开发基线）  
> 用途：支撑 TWIN 首轮骨架开发  
> 变更方式：后续修改需通过新一轮准入评审

---

## 1. 文档目的

本文档用于给出 TWIN 首轮骨架开发的完整端到端样例，统一以下闭环口径：

`输入源 → 标准学习事件 → KB 引用 → TWIN 消费 → 状态更新 → 输出结果`

本文档重点验证：

1. 正常输入如何正常更新
2. 引用缺失时如何降级处理
3. 低置信度输入如何进入 `review_needed`

---

## 2. 样例适用范围

所有样例只适用于以下冻结范围：

| 维度 | 冻结值 |
|------|--------|
| 地区 | 安徽省 |
| 学段 | 高中 |
| 年级 | 高一 |
| 学科 | 物理 |
| 教材版本 | `PHY_PEP_G1_V1` |
| 输入源 | 家长文本、老师反馈文本、单页扫描/OCR |

样例中的学生对象统一采用：

- `student_id = STU_AH_G1_PHY_001`
- `twin_id = TWIN_AH_G1_PHY_001`

---

## 3. 样例一：正常输入，正常更新

### 3.1 背景

学生已完成基础绑定，当前 TWIN 状态为 `active`。老师在物理作业讲评后提交结构化反馈。

### 3.2 输入源

- 来源：老师反馈文本
- 来源类型：`teacher_feedback_text`

### 3.3 原始输入

> 高一 1 班李明今天物理作业《匀变速直线运动的速度与时间关系》已完成，订正后能说出公式，但在加速度方向判断上还是错了两次，课堂回答速度偏慢。

### 3.4 事件生成结果

```json
{
  "event_id": "EVT_TWIN_001",
  "student_id": "STU_SZ_G1_PHY_001",
  "event_type": "correction_followup_event",
  "source_type": "teacher_feedback_text",
  "event_time": "2026-03-21T10:20:00+08:00",
  "region_id": "GD_SZ",
  "stage_level": "高中",
  "grade_level": "高一",
  "subject": "物理",
  "curriculum_version_id": "PHY_PEP_G1_V1",
  "event_status": "success",
  "confidence_score": 0.91,
  "event_summary": "作业订正完成，但加速度方向判断仍有重复错误，课堂响应偏慢。",
  "chapter_refs": ["PHY_PEP_G1_V1_SEC_03_01"],
  "knowledge_refs": ["PHY_PEP_G1_KP_021"],
  "anchor_refs": ["PHY_ANCHOR_020"],
  "behavior_tags": ["correction_completed", "repeat_error", "slow_response"],
  "raw_input_ref": "RAW_EVT_TWIN_001",
  "trace_id": "TRACE_TWIN_001"
}
```

### 3.5 KB 引用情况

- `curriculum_version_id` 命中：`PHY_PEP_G1_V1`
- `chapter_refs` 命中：`PHY_PEP_G1_V1_SEC_03_01`
- `knowledge_refs` 命中：`PHY_PEP_G1_KP_021`
- `anchor_refs` 命中：`PHY_ANCHOR_020`

结论：知识引用完整，允许进入正常更新链。

### 3.6 TWIN 消费情况

TWIN 执行动作：

1. 校验学生绑定与冻结范围一致。
2. 进入事实层更新，刷新最近作业与当前关注点。
3. 进入行为层更新，刷新订正跟进与课堂响应摘要。
4. 基于现有历史窗口刷新基础演化层。
5. 刷新风险层为 `watch`，但不直接抬升为高风险。
6. 刷新数据质量层。

### 3.7 状态更新过程

| 层级 | 更新内容 |
|------|----------|
| 事实层 | `latest_homework_summary`、`current_focus_points` 更新 |
| 行为层 | `correction_followup_summary`、`feedback_response_summary` 更新 |
| 演化层 | `knowledge_trend_summary` 标记为“订正后仍有重复错误，需继续观察” |
| 风险层 | `current_risk_labels` 增加 `knowledge_mastery_watch` |
| 数据质量层 | `state_confidence_score` 上升，`recency_score` 刷新 |

### 3.8 输出结果

```json
{
  "twin_id": "TWIN_SZ_G1_PHY_001",
  "status": "active",
  "last_event_ref": "EVT_TWIN_001",
  "current_focus_points": ["PHY_PEP_G1_KP_021"],
  "current_risk_labels": ["knowledge_mastery_watch"],
  "review_needed": false,
  "trace_id": "TRACE_TWIN_001"
}
```

### 3.9 是否进入 `review_needed`

- 否

### 3.10 验收点

1. 正常事件被成功消费。
2. 知识引用完整，事实层与行为层都被正确更新。
3. 风险层没有因为单条事件被过度放大。
4. `last_event_ref` 与 `trace_id` 均可追溯。

### 3.11 结论

- 通过

---

## 4. 样例二：引用缺失，降级处理

### 4.1 背景

学生仍处于冻结范围内。家长提供了物理学习行为反馈，但无法稳定定位到具体知识点。

### 4.2 输入源

- 来源：家长文本
- 来源类型：`parent_text`

### 4.3 原始输入

> 孩子昨晚物理作业做到很晚，一直在改卷子，情绪有点烦躁，我只知道是物理，但没看出具体是哪一章。

### 4.4 事件生成结果

```json
{
  "event_id": "EVT_TWIN_002",
  "student_id": "STU_SZ_G1_PHY_001",
  "event_type": "parent_feedback_event",
  "source_type": "parent_text",
  "event_time": "2026-03-21T21:10:00+08:00",
  "region_id": "GD_SZ",
  "stage_level": "高中",
  "grade_level": "高一",
  "subject": "物理",
  "curriculum_version_id": "PHY_PEP_G1_V1",
  "event_status": "degraded",
  "confidence_score": 0.82,
  "event_summary": "作业持续时间长、存在重复订正和情绪波动，但未定位具体知识点。",
  "chapter_refs": [],
  "knowledge_refs": [],
  "anchor_refs": [],
  "behavior_tags": ["late_homework", "repeat_correction", "frustration"],
  "raw_input_ref": "RAW_EVT_TWIN_002",
  "trace_id": "TRACE_TWIN_002"
}
```

### 4.5 KB 引用情况

- `curriculum_version_id` 已锁定为 `PHY_PEP_G1_V1`
- `chapter_refs` 缺失
- `knowledge_refs` 缺失
- `anchor_refs` 缺失

结论：不能做知识层更新，但不构成直接拒绝。

### 4.6 TWIN 消费情况

TWIN 执行动作：

1. 校验冻结范围合法。
2. 因无稳定知识引用，不更新知识掌握快照。
3. 进入 `degraded` 路径，只更新行为层和数据质量层。
4. 在事实层仅保留“本次输入未形成知识定位”的记录。
5. 不直接修改 `mastery_gap` 或高风险状态。

### 4.7 状态更新过程

| 层级 | 更新内容 |
|------|----------|
| 事实层 | 仅记录“本次事件未形成知识引用”，不修改知识掌握状态 |
| 行为层 | `execution_rhythm_summary` 增加“作业持续时间偏长、重复订正” |
| 演化层 | 若近期已有类似事件，可刷新节奏趋势；若无，则保持原值 |
| 风险层 | 不直接抬升知识风险，可保留 `watch` 候选说明 |
| 数据质量层 | 记录一次“行为有效但知识引用缺失”的输入 |

### 4.8 输出结果

```json
{
  "twin_id": "TWIN_SZ_G1_PHY_001",
  "last_event_ref": "EVT_TWIN_002",
  "event_status": "degraded",
  "knowledge_state_changed": false,
  "behavior_state_changed": true,
  "review_needed": false,
  "trace_id": "TRACE_TWIN_002"
}
```

### 4.9 是否进入 `review_needed`

- 否

### 4.10 验收点

1. 引用缺失事件没有被误判为完整成功。
2. 行为层允许更新，知识层没有被伪造更新。
3. 事件被记录为 `degraded`，而不是直接失败。
4. 整个降级路径可以追溯。

### 4.11 结论

- 可降级通过

---

## 5. 样例三：低置信度输入，进入 `review_needed`

### 5.1 背景

学生收到一张单页扫描件，但图像模糊，OCR 抽取得到多个相互冲突的引用候选。

### 5.2 输入源

- 来源：单页扫描/OCR
- 来源类型：`scan_ocr`

### 5.3 原始输入

> 一张物理练习纸，图像模糊，题干中只能看出“速度”“加速度”等片段，无法稳定确认是章节 3 还是章节 4。

### 5.4 事件生成结果

```json
{
  "event_id": "EVT_TWIN_003",
  "student_id": "STU_SZ_G1_PHY_001",
  "event_type": "scan_ocr_result_event",
  "source_type": "scan_ocr",
  "event_time": "2026-03-21T19:40:00+08:00",
  "region_id": "GD_SZ",
  "stage_level": "高中",
  "grade_level": "高一",
  "subject": "物理",
  "curriculum_version_id": "PHY_PEP_G1_V1",
  "event_status": "review_needed",
  "confidence_score": 0.56,
  "event_summary": "OCR 文本片段不足，章节与知识点候选冲突。",
  "chapter_refs": ["PHY_PEP_G1_V1_SEC_03_01", "PHY_PEP_G1_V1_SEC_04_02"],
  "knowledge_refs": [],
  "anchor_refs": ["PHY_ANCHOR_044"],
  "raw_input_ref": "RAW_EVT_TWIN_003",
  "trace_id": "TRACE_TWIN_003",
  "review_ticket_ref": "REVIEW_TWIN_003"
}
```

### 5.5 KB 引用情况

- 教材版本命中：`PHY_PEP_G1_V1`
- `chapter_refs` 存在冲突候选
- `knowledge_refs` 未稳定命中
- `anchor_refs` 单独存在但无法支撑知识更新

结论：不能直接进入主更新链。

### 5.6 TWIN 消费情况

TWIN 执行动作：

1. 校验范围合法。
2. 因低置信度且引用冲突，事件直接进入 `review_needed`。
3. 不更新事实层、行为层、演化层和风险层关键内容。
4. 只保留审计追踪和复核引用。
5. 等待 `reviewed_learning_event` 回写后再决定是否更新状态。

### 5.7 状态更新过程

| 层级 | 更新内容 |
|------|----------|
| 事实层 | 不更新 |
| 行为层 | 不更新 |
| 演化层 | 不更新 |
| 风险层 | 不更新 |
| 数据质量层 | 不改当前质量分，只记录一条低置信复核事件日志 |

### 5.8 输出结果

```json
{
  "twin_id": "TWIN_SZ_G1_PHY_001",
  "event_status": "review_needed",
  "review_ticket_ref": "REVIEW_TWIN_003",
  "state_changed": false,
  "last_event_ref": "EVT_TWIN_003",
  "trace_id": "TRACE_TWIN_003"
}
```

### 5.9 是否进入 `review_needed`

- 是

### 5.10 验收点

1. 低置信度 OCR 输入没有直接改写学生状态。
2. 冲突引用被正确转入 `review_needed`。
3. 审计链完整，后续可等待人工复核回写。
4. TWIN 没有越权替代人工裁定。

### 5.11 结论

- 通过复核路径验收

---

## 6. 修订历史

| 版本 | 日期 | 变更内容 | 责任人 |
|------|------|----------|--------|
| V1.0 | 2026-03-21 | 首次冻结 TWIN 首轮端到端样例集，覆盖正常、降级、复核三条路径 | 系统架构与工程实现负责人 |
