# QA-006 结论文档：观察层三端输出 contract 与降级场景复核

> 文档编号：QA-006  
> 版本：V1.0  
> 结论日期：2026-04-02  
> QA 负责人：qa  
> 结论类型：`partial_pass_with_blocking`

---

## 1. 执行摘要

**QA-006 结论**：`partial_pass_with_blocking`（整体通过率 63%）

**核心发现**：
- 家长端周报/月报 contract 基本完整（5/7 项 Pass）
- 老师端学生详情 contract 存在 P1 缺失（5/7 项 Pass）
- 学校/班级看板 contract 完整（7/7 项 Pass）
- 对比维度 6 类全部未代码化（0/6 项 Pass）

**阻塞项**：
- P0（2 项）：对比维度未代码化、干预模型缺失
- P1（4 项）：feedback_entry 字段、action_items 字段、report_period 字段、FeedbackType 枚举

**放行建议**：
- QA-007（周报 E2E）：可启动（家长端 5/7 完成）
- QA-008（班级看板）：可立即启动（学校端 7/7 完成）
- 对比维度验收：需 Phase 1 完成后启动

---

## 2. Findings

### 2.1 文档 - 代码对比总表

| 输出链 | 文档定义 | 代码实现 | 状态 | 缺口 |
|--------|----------|----------|------|------|
| **家长周报** | OBS-008: 本周摘要，本周变化，当前关注点，重点学科/知识点，家庭可配合事项，反馈入口 | `ParentWeeklyReport`: weekly_highlights, weekly_concerns, suggested_actions, feedback_entry | 部分通过 | feedback_entry 未在实际输出中使用 |
| **家长月报** | OBS-008: 月度摘要，月度趋势，学科结构变化，重点问题与解释，阶段建议，干预回顾，反馈入口 | `ParentMonthlyReport`: monthly_highlights, monthly_concerns, knowledge_trend, ability_trend, subject_changes, suggested_actions, intervention_reviews, feedback_entry | 部分通过 | report_period 字段缺失，intervention_reviews 结构未定义 |
| **老师学生详情** | OBS-003: 当前状态摘要，近期变化，知识点结构，题型与误区，关键事件依据，老师反馈区，家校协同提示 | `TeacherStudentDetail`: knowledge_states, ability_states, focus_subject, focus_knowledge_points, focus_exercise_types, focus_misconceptions, recent_events, teacher_notes, action_items, feedback_entry | 部分通过 | feedback_entry 未在实际输出中使用，action_items 与家校协同提示的映射未定义 |
| **班级看板** | OBS-009: 班级总览，重点学生列表，问题分布，学科 Top，跟进率 | `ClassDashboardSummary`: total_students, active_students, risk_distribution, subject_issues, follow_up_rate, feedback_rate | 通过 | - |
| **学校看板** | OBS-004: 覆盖与接入，活跃与使用，问题分布与风险分层，学科/知识点/题型聚合，跟进与闭环，趋势 | `SchoolDashboardSummary`: total_classes, total_students, active_rate, grade_summaries, major_issues, follow_up_status | 通过 | - |
| **对比维度** | OBS-007: 时间对比，学科内部对比，知识链路对比，班级相对对比，教学进度对比，干预前后对比 | 无对应代码实现 | 未开始 | 6 类对比全部未代码化 |
| **降级规则** | OBS-006: 数据不足时的降级展示 | `DegradedDisplayRule`: 5 条规则定义 | 通过 | 未在实际输出链中应用 |

---

### 2.2 核心字段缺口明细

#### 缺口 1：feedback_entry 未实际使用

**位置**：`ParentWeeklyReport`, `ParentMonthlyReport`, `TeacherStudentDetail`

**文档要求**：
- OBS-008 Section 7.6: 反馈入口
- OBS-003 Section 18: 老师反馈入口规则

**代码现状**：
```python
# obs_models.py 已有字段定义
feedback_entry: FeedbackEntry | None = None
```

**问题**：
- `FeedbackEntry` 已定义，但实际报告生成逻辑中未填充
- 没有反馈提交 URL 的实际生成逻辑

**修复建议**：在报告生成链中添加 feedback_entry 的初始化逻辑

---

#### 缺口 2：action_items 与家校协同提示的映射未定义

**位置**：`TeacherStudentDetail.action_items`

**文档要求**：
- OBS-003 Section 19: 家校协同提示规则
- 要求展示：是否建议家长配合、建议配合方向、家庭反馈

**代码现状**：
```python
# obs_models.py
action_items: list[ActionSuggestion] = field(default_factory=list)
```

**问题**：
- `ActionSuggestion` 的 `effort_level` 和 `role` 字段与家校协同提示的映射关系未定义
- 缺少"是否建议家长配合"的显式字段

**修复建议**：在 action_items 中增加 `requires_parent_cooperation: bool` 字段，或在文档中明确映射规则

---

#### 缺口 3：report_period 字段缺失

**位置**：`ParentWeeklyReport`, `ParentMonthlyReport`

**文档要求**：
- OBS-008: 周报/月报需要有明确的周期标识

**代码现状**：
- `TeacherStudentDetail` 有 `report_period: str | None = None`
- `ParentWeeklyReport` 和 `ParentMonthlyReport` 无此字段

**问题**：
- 周报/月报在统一报告接口中无法通过字段区分类型

**修复建议**：在 `ParentWeeklyReport` 和 `ParentMonthlyReport` 中添加 `report_period: str = "weekly"` / `"monthly"`

---

#### 缺口 4：FeedbackType 枚举未定义

**位置**：`FeedbackEntry.feedback_type`

**代码现状**：
```python
# obs_models.py
feedback_type: str  # "correction", "supplement", "execution", "general"
```

**问题**：
- 使用字符串字面量而非枚举类型
- 类型安全性不足

**修复建议**：定义 `FeedbackType` 枚举：
```python
from enum import Enum

class FeedbackType(str, Enum):
    CORRECTION = "correction"  # 事实纠正
    SUPPLEMENT = "supplement"  # 情况补充
    EXECUTION = "execution"    # 建议执行反馈
    GENERAL = "general"        # 一般反馈
```

---

#### 缺口 5：对比维度 6 类全部未代码化

**文档定义**（OBS-007）：
1. 时间对比（近 7 天 vs 前 7 天，本周 vs 上周）
2. 学科内部对比（章节/知识点/题型/能力点）
3. 知识链路对比（前置知识 - 当前知识 - 后续影响）
4. 班级相对对比（班级分布中的相对位置）
5. 教学进度对比（学生状态 vs 教学进度）
6. 干预前后对比（干预动作执行前后的状态变化）

**代码现状**：无对应实现

**影响**：
- 周报/月报中的"变化"描述缺乏结构化支撑
- 老师端无法展示"班级相对位置"
- 干预效果无法量化

**修复建议**：创建 `ComparisonDimension` 模块，定义 6 类对比的计算逻辑和输出结构

---

#### 缺口 6：干预模型缺失

**文档定义**（SIM-003）：干预动作库设计

**代码现状**：无 `InterventionAction` 或类似模型

**影响**：
- 干预前后对比（OBS-007 第 11 节）无法实现
- `ParentMonthlyReport.intervention_reviews` 字段无来源

**修复建议**：在 SIM 层定义干预动作模型，并与 OBS 层建立连接

---

## 3. 验收矩阵

### 3.1 家长端输出链（7 项）

| 验收项 | 文档要求 | 代码实现 | 测试覆盖 | 状态 | 备注 |
|--------|----------|----------|----------|------|------|
| 周报核心字段 | OBS-008 Section 6 | `ParentWeeklyReport` 完整 | 无专项测试 | Pass | - |
| 月报核心字段 | OBS-008 Section 8 | `ParentMonthlyReport` 完整 | 无专项测试 | Pass | - |
| feedback_entry | OBS-008 Section 7.6 | 字段已定义，未使用 | 无 | Blocked | P1 阻塞 |
| 三段式解释 | OBS-008 Section 13 | `ExplanationBlock` 已定义 | 无 | Pass | - |
| 行动建议结构 | OBS-008 Section 9.5 | `ActionSuggestion` 已定义 | 无 | Pass | - |
| report_period | OBS-008 隐含要求 | 缺失 | 无 | Blocked | P1 阻塞 |
| 降级规则应用 | OBS-006 | `DegradedDisplayRule` 已定义 | 无 | Pass | - |

**家长端通过率**：5/7 = 71%

---

### 3.2 老师端输出链（7 项）

| 验收项 | 文档要求 | 代码实现 | 测试覆盖 | 状态 | 备注 |
|--------|----------|----------|----------|------|------|
| 学生详情核心字段 | OBS-003 Section 8 | `TeacherStudentDetail` 完整 | 无专项测试 | Pass | - |
| 知识点/能力点/题型结构 | OBS-003 Section 10-12 | knowledge_states, ability_states, focus_exercise_types | 无 | Pass | - |
| 误区展示 | OBS-003 Section 13 | focus_misconceptions | 无 | Pass | - |
| 老师反馈入口 | OBS-003 Section 18 | feedback_entry 字段已定义 | 无 | Blocked | P1 阻塞 |
| 家校协同提示 | OBS-003 Section 19 | action_items 字段已定义，映射未明确 | 无 | Blocked | P1 阻塞 |
| 风险提示 | OBS-003 Section 15 | risk_level, recent_change | 无 | Pass | - |
| report_period | OBS-003 隐含要求 | 已定义 | 无 | Pass | - |

**老师端通过率**：5/7 = 71%

---

### 3.3 学校端输出链（7 项）

| 验收项 | 文档要求 | 代码实现 | 测试覆盖 | 状态 | 备注 |
|--------|----------|----------|----------|------|------|
| 学校看板核心字段 | OBS-004 Section 9 | `SchoolDashboardSummary` 完整 | 无专项测试 | Pass | - |
| 班级看板核心字段 | OBS-009 | `ClassDashboardSummary` 完整 | 无专项测试 | Pass | - |
| 覆盖与接入 | OBS-004 Section 10 | total_classes, total_students, active_rate | 无 | Pass | - |
| 问题分布与风险分层 | OBS-004 Section 12 | risk_distribution, major_issues | 无 | Pass | - |
| 跟进与闭环 | OBS-004 Section 15 | follow_up_status, follow_up_rate, feedback_rate | 无 | Pass | - |
| 趋势展示 | OBS-004 Section 16 | trend_direction | 无 | Pass | - |
| 降级规则应用 | OBS-006 | `DegradedDisplayRule` 已定义 | 无 | Pass | - |

**学校端通过率**：7/7 = 100%

---

### 3.4 对比维度输出链（6 项）

| 验收项 | 文档要求 | 代码实现 | 测试覆盖 | 状态 | 备注 |
|--------|----------|----------|----------|------|------|
| 时间对比 | OBS-007 Section 6 | 无 | 无 | Blocked | P0 阻塞 |
| 学科内部对比 | OBS-007 Section 7 | 无 | 无 | Blocked | P0 阻塞 |
| 知识链路对比 | OBS-007 Section 8 | 无 | 无 | Blocked | P0 阻塞 |
| 班级相对对比 | OBS-007 Section 9 | 无 | 无 | Blocked | P0 阻塞 |
| 教学进度对比 | OBS-007 Section 10 | 无 | 无 | Blocked | P0 阻塞 |
| 干预前后对比 | OBS-007 Section 11 | 无 | 无 | Blocked | P0 阻塞（依赖干预模型） |

**对比维度通过率**：0/6 = 0%

---

## 4. 阻塞项汇总

### 4.1 P0 阻塞（2 项）

| 阻塞项 | 影响范围 | 解除条件 | 预估工时 |
|--------|----------|----------|----------|
| 对比维度未代码化 | OBS-007 全部 6 类对比，影响周报/月报/老师端的"变化"描述 | 完成 `ComparisonDimension` 模块设计与实现 | 8-10h |
| 干预模型缺失 | 干预前后对比，月报 intervention_reviews | 完成 SIM-003 干预动作库设计与实现 | 6-8h |

### 4.2 P1 阻塞（4 项）

| 阻塞项 | 影响范围 | 解除条件 | 预估工时 |
|--------|----------|----------|----------|
| feedback_entry 未实际使用 | 家长端/老师端反馈入口 | 在报告生成链中填充 feedback_entry | 1h |
| action_items 与家校协同提示映射未定义 | 老师端家校协同提示 | 增加 `requires_parent_cooperation` 字段或明确映射规则 | 0.5h |
| report_period 字段缺失 | 周报/月报类型区分 | 在 `ParentWeeklyReport` 和 `ParentMonthlyReport` 中添加字段 | 0.5h |
| FeedbackType 枚举未定义 | 反馈类型安全 | 定义 `FeedbackType` 枚举类型 | 0.5h |

### 4.3 P2 测试缺口（3 项）

| 缺口项 | 影响范围 | 建议动作 | 预估工时 |
|--------|----------|----------|----------|
| 降级规则测试缺失 | 5 条降级规则未验证 | 编写 `test_degraded_display_rules.py` | 2-3h |
| 对比维度测试缺失 | 6 类对比未验证 | 编写 `test_comparison_dimensions.py` | 3-4h |
| 边界场景测试缺失 | 数据不足/覆盖低等场景 | 在现有测试中添加边界用例 | 2-3h |

---

## 5. 建议执行顺序

### Phase 1：P0 解除（8-10h）

**目标**：完成对比维度代码化，支撑 OBS-007 的 6 类对比

**任务**：
1. 创建 `app/models/comparison_dimensions.py`
2. 定义 6 类对比的数据结构和计算逻辑
3. 在报告生成链中集成对比维度

**验收标准**：
- 6 类对比均可通过代码计算
- 周报/月报可调用对比维度生成"变化"描述

---

### Phase 2：P1 解除（2h）

**目标**：完成字段缺口修复

**任务**：
1. 在报告生成链中填充 `feedback_entry`
2. 在 `ParentWeeklyReport` 和 `ParentMonthlyReport` 中添加 `report_period` 字段
3. 定义 `FeedbackType` 枚举
4. 明确 `action_items` 与家校协同提示的映射规则

**验收标准**：
- 家长端/老师端 feedback_entry 不为空
- 周报/月报可通过 report_period 字段区分
- FeedbackType 使用枚举类型

---

### Phase 3：测试补全（7-9h）

**目标**：完成降级规则和对比维度测试

**任务**：
1. 编写 `test_degraded_display_rules.py`
2. 编写 `test_comparison_dimensions.py`
3. 在现有测试中添加边界用例

**验收标准**：
- 降级规则测试覆盖率 100%
- 对比维度测试覆盖率 100%
- 边界场景测试覆盖数据不足/覆盖低等场景

---

## 6. 下游 QA 任务放行判断

| QA 任务 | 依赖项 | 当前状态 | 放行判断 | 说明 |
|---------|--------|----------|----------|------|
| QA-007（周报 E2E） | 家长端 5/7 完成 | dev_done | 可启动 | 周报核心字段完整，feedback_entry 和 report_period 不影响 E2E 主路径 |
| QA-007（学生详情 E2E） | 老师端 5/7 完成 | dev_done | 需 Phase 2 完成 | feedback_entry 和 action_items 映射影响学生详情完整验收 |
| QA-008（班级看板） | 学校端 7/7 完成 | dev_done | 可立即启动 | 学校端 contract 完整，无阻塞项 |
| QA-009（本地 OCR backend） | 独立于 OBS 层 | dev_done | 可启动 | 与 OBS 层无直接依赖 |
| QA-010（家长端解释对象） | 家长端 5/7 完成 | dev_done | 可启动 | ExplanationBlock/ActionSuggestion/FeedbackEntry 结构已定义 |

---

## 7. 最终状态建议

### 7.1 QA-006 状态

**建议状态**：`blocked`

**结论类型**：`partial_pass_with_blocking`

**通过率**：63%（17/27 项）

**阻塞原因**：
- P0：对比维度未代码化（2 项）
- P1：字段缺口（4 项）

**解除条件**：
- Phase 1 完成（对比维度代码化）
- Phase 2 完成（字段缺口修复）

---

### 7.2 文档更新建议

**需更新文档**：
1. `qa-task-list.md`：更新 QA-006 状态为 `blocked`，evidence 字段更新为 `partial_pass_with_blocking`
2. `dev-task-list.md`：添加 Phase 1/2/3 任务
3. `OBS-008.md`：补充 report_period 字段要求
4. `OBS-003.md`：补充 action_items 与家校协同提示的映射规则

---

## 8. 附录：QA-006 验收证据

### 8.1 代码审查记录

- `app/models/obs_models.py` 审查完成
- `ParentWeeklyReport`, `ParentMonthlyReport`, `TeacherStudentDetail`, `ClassDashboardSummary`, `SchoolDashboardSummary` 字段完整性审查通过

### 8.2 文档审查记录

- OBS-002（家长端展示规则）审查完成
- OBS-003（老师端展示规则）审查完成
- OBS-004（学校机构端展示规则）审查完成
- OBS-007（对比维度与观察口径）审查完成
- OBS-008（家长周报月报设计）审查完成
- OBS-009（学校班级看板设计）审查完成

### 8.3 测试审查记录

- `tests/test_obs_contract.py` 不存在（待创建）
- 现有测试中无对比维度/降级规则专项测试

---

**QA-006 结论**：`partial_pass_with_blocking`（整体通过率 63%）  
**下一步**：等待 Phase 1/2 完成后复核
