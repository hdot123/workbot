# 学生 Agent 字段设计

> 文档编号：TWIN-002
> 版本：V1.0
> 创建日期：2024
> 最后更新：待定
> 维护人：学生数字孪生负责人

---

## 1. 文档目的

本文档用于定义 StudentTwinAgent 的字段体系、字段分层、字段类型、更新方式与设计边界。

本文档重点回答以下问题：

1. StudentTwinAgent 需要存哪些字段
2. 字段应该如何分层组织
3. 哪些字段由事实直接写入，哪些字段由规则或模型计算得到
4. 哪些字段适合保存在 Agent 当前态中，哪些应进入事件流或图谱记忆
5. MVP 阶段最小字段集是什么

---

## 2. 字段设计原则

### 2.1 当前态优先

StudentTwinAgent 主要承载“当前可用状态”和“关键引用”，不直接保存全部历史明细。

### 2.2 事实与推断分离

字段必须明确区分：

- 事实字段
- 派生字段
- 推断字段
- 审计字段

### 2.3 轻对象、重引用

原始输入、长文本、扫描件、完整事件链和图谱关系应放在事件系统、文件系统或图谱中；Agent 内仅保留摘要和引用。

### 2.4 面向更新

字段设计必须支持事件驱动更新，避免每次改一个局部状态都重写整份对象。

### 2.5 面向输出

字段必须服务于家长端、老师端、学校端、后台推演和审计追踪。

---

## 3. 字段分层

建议按以下层次组织字段：

1. 基础身份字段
2. 当前事实字段
3. 行为执行字段
4. 时间演化字段
5. 关系上下文字段
6. 推演准备字段
7. 审计与治理字段

---

## 4. 基础身份字段

建议至少包含：

- student_id
- twin_id
- region_id
- school_id
- class_id
- grade_level
- curriculum_version_id
- subject_list
- created_at
- updated_at

这些字段稳定性高，是所有状态对象的主锚点。

---

## 5. 当前事实字段

建议至少包含：

- current_learning_status
- current_subject_statuses
- current_knowledge_snapshots
- latest_exam_summary
- latest_homework_summary
- current_focus_points
- current_risk_labels

这些字段主要用于当前态展示和下游消费。

---

## 6. 行为执行字段

建议以对象数组或引用形式承载：

- behavior_summaries
- execution_rhythm_summary
- correction_followup_summary
- feedback_response_summary

不建议把全部行为明细直接塞入主对象。

---

## 7. 时间演化字段

建议至少包含：

- subject_trend_summary
- knowledge_trend_summary
- rhythm_trend_summary
- risk_trend_summary
- intervention_change_summary

这些字段用于表达“最近怎么变了”。

---

## 8. 关系上下文字段

建议至少包含：

- parent_context_summary
- teacher_context_summary
- class_context_summary
- school_context_summary
- teaching_stage_context
- home_school_coordination_summary

这些字段应保持中性表达，不直接输出价值判断。

---

## 9. 推演准备字段

建议至少包含：

- simulation_readiness_status
- simulation_readiness_score
- key_risk_factors
- weak_links
- candidate_action_refs
- boundary_notes

这些字段用于后台推演输入，不应直接等同于前台输出。

---

## 10. 审计与治理字段

建议至少包含：

- version_no
- last_event_ref
- last_updated_by
- audit_trace_ref
- data_completeness_score
- state_confidence_score

---

## 11. mastery_gap 相关字段

为了支撑 False Mastery 判断，建议在 Agent 中显式定义：

- homework_accuracy
- exam_accuracy
- mastery_gap
- mastery_gap_status
- mastery_gap_updated_at

其中：

- `mastery_gap = homework_accuracy - exam_accuracy`
- 当 `mastery_gap > 0.15` 时，必须进入风险解释范围
- 当 gap 持续扩大时，应同步写入时间演化层与推演准备层

---

## 12. 字段类型建议

### 事实字段

用于承载已确认、可直接追溯的客观结果。

### 派生字段

由规则、窗口汇总或统计计算得到。

### 推断字段

由模型或推理链得出，必须附带置信边界。

### 审计字段

用于记录对象演变过程与更新来源。

---

## 13. 不建议放入主对象的内容

以下内容不建议直接塞进 StudentTwinAgent 主对象：

- 原始 OCR 文本
- 完整聊天记录
- 全量事件明细
- 全量图谱关系
- 完整长报告正文
- 高不确定性推断链全文

---

## 14. MVP 最小字段集

MVP 阶段建议最少保留：

- 基础身份字段
- 当前事实字段
- 核心行为摘要
- 基础趋势摘要
- 关键关系摘要
- simulation_readiness_score
- homework_accuracy / exam_accuracy / mastery_gap
- 审计字段

---

## 15. 推荐样例

```json
{
  "student_id": "STU_000123",
  "twin_id": "TWIN_000123",
  "school_id": "SCH_001",
  "class_id": "CLS_G1_03",
  "curriculum_version_id": "PHY_PEP_G1",
  "current_learning_status": "unstable",
  "current_focus_points": [
    "受力分析步骤不稳定",
    "作业节奏有波动"
  ],
  "homework_accuracy": 0.86,
  "exam_accuracy": 0.64,
  "mastery_gap": 0.22,
  "mastery_gap_status": "risk",
  "simulation_readiness_score": 0.71,
  "data_completeness_score": 0.76,
  "version_no": 18,
  "last_event_ref": "LE_20240420_003"
}
```

---

## 16. 与其他文档的关系

| 本文档 | 关联文档 | 关系说明 |
|------|------|------|
| TWIN-002 字段设计 | TWIN-001 总体设计 | 总体设计提供字段分层框架 |
| TWIN-002 字段设计 | TWIN-003 学生状态模型 | 状态模型决定字段语义 |
| TWIN-002 字段设计 | TWIN-004 至 TWIN-007 | 各层文档决定字段归属 |

---

## 17. 结论

字段设计的核心目标，不是把 StudentTwinAgent 做成一个越来越胖的对象，而是让它成为一个可更新、可解释、可追溯、可服务多角色输出的当前态容器。

字段越多，越要守住边界；字段越关键，越要清楚它来自事实、规则还是推断。

## 与其他文档的关系

| 文档 | 关联文档 | 关系说明 |
|------|----------|----------|
| TWIN-002 学生 Agent 字段设计 | TWIN-001 StudentTwinAgent 总体设计 | 本文档是总体设计的字段层展开 |
| TWIN-002 学生 Agent 字段设计 | TWIN-003 学生状态模型 | 字段设计支撑状态模型的表达 |
| TWIN-002 学生 Agent 字段设计 | INGEST-007 学习事件生成标准 | 事件字段映射到 Agent 字段空间 |
