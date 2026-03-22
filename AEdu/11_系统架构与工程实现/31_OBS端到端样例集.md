# OBS 端到端样例集

> 文档编号：ARCH-031
> 版本：V1.0
> 创建日期：2026-03-21
> 最后更新：2026-03-21
> 维护人：系统架构与工程实现负责人
> 状态：已冻结（首轮骨架开发基线）
> 用途：支撑 OBS 首轮骨架开发
> 变更方式：后续修改需通过新一轮准入评审

---

## 1. 文档目的

本文档用于定义 OBS（观察层与产品层）模块在首轮骨架开发阶段的端到端样例集，确保模块进入正式开发前有可验证、可追溯、可复现的测试基准。

本文档重点回答以下问题：

1. OBS 首轮骨架开发需要跑通哪些端到端链路
2. 每个样例的输入是什么、输出是什么
3. 如何判断样例是否通过
4. 样例如何覆盖正常/降级/异常场景

---

## 2. 适用范围

### 2.1 适用模块

- OBS 模块（观察层与产品层）

### 2.2 适用阶段

- 首轮骨架开发阶段
- MVP 功能验收阶段

### 2.3 覆盖场景

| 场景 | 样例编号 | 优先级 |
|------|----------|--------|
| 家长查看周报完整流程 | E2E-001 | P0 |
| 老师查看学生详情完整流程 | E2E-002 | P0 |
| 状态校准反馈完整流程 | E2E-003 | P0 |
| 低置信度状态降级展示 | E2E-004 | P1 |
| 上游缺失降级展示 | E2E-005 | P1 |

---

## 3. 样例 E2E-001：家长查看周报完整流程

### 3.1 样例描述

家长用户在微信小程序中查看学生本周周报，验证从 TWIN 状态读取 → GRAPH 上下文装配 → 周报展示的完整链路。

### 3.2 前置条件

- TWIN 状态已更新（`data_quality_score >= 0.70`）
- GRAPH 检索结果已生成
- 家长用户已绑定学生

### 3.3 输入

```json
{
  "student_id": "stu_001",
  "user_role": "parent",
  "week_start": "2026-03-15",
  "week_end": "2026-03-21"
}
```

### 3.4 预期输出

```json
{
  "report_type": "weekly",
  "student_id": "stu_001",
  "report_period": {
    "start": "2026-03-15",
    "end": "2026-03-21"
  },
  "sections": [
    {
      "section_type": "event_summary",
      "title": "本周发生了什么",
      "content": "本周完成了 3 次物理作业，参与 1 次课堂测验",
      "confidence": 0.92
    },
    {
      "section_type": "change_summary",
      "title": "学习状态变化",
      "content": "力学章节掌握度从 0.68 提升至 0.75，整体掌握度稳定",
      "confidence": 0.88
    },
    {
      "section_type": "focus_points",
      "title": "需要关注",
      "content": "运动学章节存在 2 个薄弱知识点，建议加强练习",
      "confidence": 0.85
    },
    {
      "section_type": "suggestions",
      "title": "家庭可配合",
      "content": "建议关注孩子的作业订正情况，巩固薄弱知识点",
      "confidence": 0.80
    }
  ],
  "data_quality_score": 0.85,
  "twin_version": "v1.2.3",
  "graph_version": "v1.1.0",
  "generated_at": "2026-03-21T10:00:00Z",
  "trace_id": "trace_weekly_001"
}
```

### 3.5 验收标准

| 检查项 | 预期结果 |
|--------|----------|
| 周报生成成功 | `report_type = weekly` |
| 包含 4 个核心板块 | `sections.length = 4` |
| 置信度标注清晰 | 每个 section 包含 `confidence` |
| 版本追溯完整 | 包含 `twin_version`、`graph_version`、`trace_id` |
| 页面渲染正确 | 前端页面展示与预期输出一致 |

---

## 4. 样例 E2E-002：老师查看学生详情完整流程

### 4.1 样例描述

老师用户在微信小程序中查看学生详情页，验证从 TWIN 状态读取 → 知识结构展示 → 行为观察展示的完整链路。

### 4.2 前置条件

- TWIN 状态已更新
- 老师用户已绑定班级
- 学生属于该班级

### 4.3 输入

```json
{
  "student_id": "stu_001",
  "user_role": "teacher",
  "class_id": "class_101"
}
```

### 4.4 预期输出

```json
{
  "student_id": "stu_001",
  "basic_info": {
    "student_name": "张三",
    "class_name": "高一(1)班",
    "region": "安徽省"
  },
  "status_overview": {
    "overall_mastery_level": 0.75,
    "risk_level": "medium",
    "mastery_gap": 0.08,
    "mastery_gap_status": "轻微偏高"
  },
  "knowledge_structure": {
    "subject": "物理",
    "chapters": [
      {
        "chapter_name": "运动的描述",
        "mastery_level": 0.82,
        "knowledge_points": [
          {"name": "位移", "mastery": 0.90},
          {"name": "速度", "mastery": 0.85},
          {"name": "加速度", "mastery": 0.70}
        ]
      },
      {
        "chapter_name": "匀变速直线运动",
        "mastery_level": 0.68,
        "knowledge_points": [
          {"name": "匀变速运动规律", "mastery": 0.65},
          {"name": "自由落体运动", "mastery": 0.72}
        ]
      }
    ]
  },
  "behavior_observation": {
    "recent_tags": ["作业完成及时", "课堂参与积极"],
    "homework_accuracy_trend": [0.75, 0.78, 0.80],
    "exam_accuracy_trend": [0.70, 0.72, 0.75]
  },
  "data_quality_score": 0.88,
  "twin_version": "v1.2.3",
  "updated_at": "2026-03-21T09:00:00Z",
  "trace_id": "trace_detail_001"
}
```

### 4.5 验收标准

| 检查项 | 预期结果 |
|--------|----------|
| 学生信息正确 | `student_name`、`class_name` 与实际一致 |
| 状态概览完整 | 包含 `overall_mastery_level`、`risk_level`、`mastery_gap` |
| 知识结构展示正确 | 章节和知识点层级清晰 |
| 行为观察展示正确 | 包含行为标签和趋势数据 |
| 页面渲染正确 | 前端页面展示与预期输出一致 |

---

## 5. 样例 E2E-003：状态校准反馈完整流程

### 5.1 样例描述

家长用户提交状态校准反馈，验证反馈提交 → 分流 → 处理 → TWIN 状态更新的完整链路。

### 5.2 前置条件

- 家长用户已绑定学生
- TWIN 状态已更新
- 存在可校准的状态字段

### 5.3 输入

```json
{
  "student_id": "stu_001",
  "user_role": "parent",
  "feedback_type": "status_calibration",
  "feedback_content": {
    "target_field": "knowledge_mastery_snapshot.力学.牛顿第二定律",
    "current_value": 0.65,
    "calibrated_value": 0.80,
    "calibration_reason": "孩子已经掌握了这个知识点，只是考试时粗心",
    "evidence": "家庭作业正确率 95%"
  }
}
```

### 5.4 预期输出

```json
{
  "feedback_id": "fb_001",
  "feedback_type": "status_calibration",
  "status": "submitted",
  "student_id": "stu_001",
  "submitted_at": "2026-03-21T10:30:00Z",
  "processing_status": {
    "current_stage": "review_queue",
    "estimated_processing_time": "24h"
  },
  "trace_id": "trace_feedback_001"
}
```

### 5.5 后续处理（异步）

```json
{
  "feedback_id": "fb_001",
  "processing_result": {
    "status": "accepted",
    "calibration_applied": true,
    "new_field_value": 0.78,
    "twin_version": "v1.2.4",
    "processed_at": "2026-03-22T09:00:00Z"
  }
}
```

### 5.6 验收标准

| 检查项 | 预期结果 |
|--------|----------|
| 反馈提交成功 | 返回 `feedback_id` 和 `status = submitted` |
| 分流正确 | `processing_status.current_stage = review_queue` |
| 处理状态可追踪 | 可通过 `feedback_id` 查询处理进度 |
| TWIN 状态更新 | 处理完成后 TWIN 状态已更新 |

---

## 6. 样例 E2E-004：低置信度状态降级展示

### 6.1 样例描述

当 TWIN 状态 `data_quality_score < 0.50` 时，OBS 降级展示，验证降级逻辑是否正确。

### 6.2 前置条件

- TWIN 状态 `data_quality_score = 0.45`

### 6.3 输入

```json
{
  "student_id": "stu_002",
  "user_role": "parent"
}
```

### 6.4 预期输出

```json
{
  "student_id": "stu_002",
  "display_mode": "degraded",
  "degraded_reason": "data_quality_insufficient",
  "data_quality_score": 0.45,
  "display_content": {
    "status_summary": "数据收集中，暂无法给出可靠判断",
    "data_collection_progress": {
      "events_collected": 5,
      "events_required": 10,
      "estimated_completion": "预计还需 5 个学习事件"
    },
    "available_actions": [
      "补充作业完成情况",
      "补充考试/测验结果",
      "等待老师反馈"
    ]
  },
  "hidden_content": ["风险预警", "掌握度评价", "对比结论"]
}
```

### 6.5 验收标准

| 检查项 | 预期结果 |
|--------|----------|
| 降级模式正确 | `display_mode = degraded` |
| 不展示高风险结论 | `hidden_content` 包含风险预警 |
| 展示数据收集状态 | 包含 `data_collection_progress` |
| 引导用户补充输入 | 包含 `available_actions` |

---

## 7. 样例 E2E-005：上游缺失降级展示

### 7.1 样例描述

当 GRAPH 检索失败时，OBS 仅展示 TWIN 状态，验证降级逻辑是否正确。

### 7.2 前置条件

- TWIN 状态正常
- GRAPH 检索失败或返回 `low_relevance`

### 7.3 输入

```json
{
  "student_id": "stu_003",
  "user_role": "parent"
}
```

### 7.4 预期输出

```json
{
  "student_id": "stu_003",
  "display_mode": "twin_only",
  "degraded_reason": "graph_unavailable",
  "display_content": {
    "status_summary": "当前物理学科整体掌握度为 0.75",
    "change_summary": "近 7 天掌握度稳定",
    "focus_points": ["运动学章节需关注"]
  },
  "hidden_content": ["图谱分析结论", "知识关联解释"],
  "twin_version": "v1.2.3",
  "graph_status": "unavailable"
}
```

### 7.5 验收标准

| 检查项 | 预期结果 |
|--------|----------|
| 降级模式正确 | `display_mode = twin_only` |
| 仅展示 TWIN 状态 | `display_content` 不包含图谱分析结论 |
| 不展示图谱依据 | `hidden_content` 包含图谱相关内容 |
| 不提示系统异常 | 用户界面不显示错误信息 |

---

## 8. 样例执行记录模板

每次执行样例时，需记录以下信息：

| 字段 | 说明 |
|------|------|
| 执行时间 | YYYY-MM-DD HH:mm:ss |
| 执行人 | 执行人员姓名 |
| 样例编号 | E2E-001 ~ E2E-005 |
| 执行环境 | 开发环境/测试环境/预发布环境 |
| 输入数据 | 实际使用的输入数据 |
| 实际输出 | 系统实际返回的输出 |
| 验收结果 | 通过/失败 |
| 差异说明 | 如有差异，说明原因 |
| 截图/日志 | 相关截图或日志附件 |

---

## 9. 结论

OBS 的端到端样例集，是首轮骨架开发验收的核心依据。

所有 P0 样例（E2E-001 ~ E2E-003）必须全部通过，才能判定 OBS 首轮骨架开发完成。

P1 样例（E2E-004 ~ E2E-005）可在后续迭代中补充验证，但降级逻辑必须在首轮骨架开发中实现。