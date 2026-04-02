# 反馈闭环回流断言与边界说明

> 文档编号：OBS-010-APPENDIX-001  
> 版本：V1.0  
> 创建日期：2026-04-02  
> 维护人：DEV-A (反馈闭环负责人)

---

## 1. 文档目的

本文档为 OBS-010 的附录，用于固化反馈闭环的：
1. **回流断言**：代码层必须满足的不变量
2. **边界规则**：什么可以直接影响，什么不能直接改写
3. **MVP 范围**：当前实现的明确边界

本文档供 QA-008 执行回归测试时参考，并作为 DOC-012 验收口径的证据附件。

---

## 2. 回流断言（Code-Level Assertions）

### 2.1 路由断言

| 断言编号 | 断言内容 | 验证测试 | 状态 |
|----------|----------|----------|------|
| ASSERT-FB-001 | `feedback_type == "calibration"` → `routed_to == "review_queue"` | `test_feedback_routing()` | ✅ 已验证 |
| ASSERT-FB-002 | `feedback_type == "experience"` → `routed_to == "product_pool"` | `test_feedback_routing()` | ✅ 已验证 |
| ASSERT-FB-003 | `feedback_type == "operation"` → `routed_to == "operation_pool"` | `test_feedback_routing()` | ✅ 已验证 |
| ASSERT-FB-004 | `feedback_type == "exception"` → `routed_to == "tech_pool"` | `test_feedback_routing()` | ✅ 已验证 |

### 2.2 状态流转断言

| 断言编号 | 断言内容 | 验证测试 | 状态 |
|----------|----------|----------|------|
| ASSERT-FB-005 | 初建状态必为 `pending` | `test_feedback_lifecycle()` | ✅ 已验证 |
| ASSERT-FB-006 | 调用 `route()` 后状态变为 `routed` | `test_feedback_lifecycle()` | ✅ 已验证 |
| ASSERT-FB-007 | 调用 `mark_in_progress()` 后状态变为 `in_progress` | `test_feedback_lifecycle()` | ✅ 已验证 |
| ASSERT-FB-008 | 调用 `mark_resolved()` 后状态变为 `resolved` | `test_feedback_lifecycle()` | ✅ 已验证 |
| ASSERT-FB-009 | 状态流转不可逆序（无 `mark_pending()` 从 resolved 回退） | 代码审查 | ✅ 已验证 |

### 2.3 验证规则断言

| 断言编号 | 断言内容 | 验证测试 | 状态 |
|----------|----------|----------|------|
| ASSERT-FB-010 | `source_role` 不在 {parent, teacher, school, operation} → 验证失败 | `test_feedback_validation()` | ✅ 已验证 |
| ASSERT-FB-011 | `target_type` 不在 {parent_report, teacher_detail, class_dashboard, school_dashboard, home} → 验证失败 | `test_feedback_validation()` | ✅ 已验证 |
| ASSERT-FB-012 | `feedback_type` 不在 {calibration, experience, operation, exception} → 验证失败 | `test_feedback_validation()` | ✅ 已验证 |
| ASSERT-FB-013 | `rating` 不在 1-5 范围 → 验证失败 | `test_feedback_validation()` | ✅ 已验证 |
| ASSERT-FB-014 | `feedback_option_id` 与 `feedback_text` 同时为空 → 验证失败 | `test_feedback_validation()` | ✅ 已验证 |

---

## 3. 边界规则（OBS-010 第 26 节代码化）

### 3.1 可直接影响的内容（无需人工复核）

| 反馈类型 | 可直接影响 | 影响方式 |
|----------|------------|----------|
| experience | 产品优化池入队 | 自动进入 `product_pool` |
| operation | 运营动作池入队 | 自动进入 `operation_pool` |
| operation | 已跟进标记 | `mark_in_progress()` + `mark_resolved()` |
| calibration | 状态校准池入队 | 自动进入 `review_queue` |
| exception | 技术问题池入队 | 自动进入 `tech_pool` |

### 3.2 不可直接改写的内容（需人工复核）

| 内容类型 | 为什么不能直接改写 | 正确处理流程 |
|----------|-------------------|--------------|
| 学生风险等级 | 核心状态字段，轻反馈直接改写会导致系统真相层失控 | 进入 `review_queue` → 人工复核 → 确认后由 StudentTwinAgent 更新 |
| 知识点掌握度 | 需要多事件交叉验证，单条反馈不足以修正 | 进入 `review_queue` → 人工复核 → 触发图谱更新链 |
| 学科状态判断 | 需要教学观察佐证 | 进入 `review_queue` → 人工复核 → 老师确认 |
| 关键事实对象 | 如学生 ID、班级归属等 | 进入 `review_queue` → 运营确认 → 数据修正流程 |

### 3.3 边界规则代码体现

```python
# feedback_event.py 中无直接修改 StudentTwinAgent 状态的方法
# FeedbackEvent 只负责：
# 1. 创建反馈事件
# 2. 路由到对应池
# 3. 追踪处理状态（pending → routed → in_progress → resolved）
# 4. 不直接修改 TWIN/GRAPH 状态
```

---

## 4. MVP 范围固化

### 4.1 已实现的枚举值

**feedback_type（4 种）**：
- `calibration` - 状态校准类
- `experience` - 产品体验类
- `operation` - 实施推进类
- `exception` - 异常故障类

**route_destination（4 种）**：
- `review_queue` - 状态校准池
- `product_pool` - 产品优化池
- `operation_pool` - 运营动作池
- `tech_pool` - 技术问题池

**status（5 种）**：
- `pending` - 待处理
- `routed` - 已分流
- `in_progress` - 处理中
- `resolved` - 已解决
- `closed` - 已关闭

**source_role（4 种）**：
- `parent` - 家长
- `teacher` - 老师
- `school` - 学校
- `operation` - 运营

**target_type（5 种）**：
- `parent_report` - 家长报告
- `teacher_detail` - 老师学生详情
- `class_dashboard` - 班级看板
- `school_dashboard` - 学校总览
- `home` - 首页

### 4.2 预设选项（12 项）

**PARENT_REPORT_OPTIONS（4 项）**：
- `PR_ACCURATE` - 报告内容贴近实际 → experience
- `PR_INACCURATE` - 报告内容与实际不符 → calibration
- `PR_HELPFUL` - 报告对我有帮助 → experience
- `PR_SUPPLEMENT` - 我有情况要补充 → calibration

**TEACHER_DETAIL_OPTIONS（4 项）**：
- `TD_ACCURATE` - 判断贴近教学观察 → experience
- `TD_FOLLOWED` - 已跟进 → operation
- `TD_CONTINUE` - 需要继续关注 → operation
- `TD_ERROR` - 存在映射错误 → calibration

**DASHBOARD_OPTIONS（4 项）**：
- `DB_SMOOTH` - 推进顺畅 → experience
- `DB_BLOCKED` - 遇到卡点 → operation
- `DB_SUPPORT` - 需要支持 → operation
- `DB_ANOMALY` - 数据异常 → exception

### 4.3 MVP 未包含（Out of Scope）

| 未包含功能 | 说明 | 后续任务 |
|------------|------|----------|
| 后端持久化 | FeedbackEvent 仅内存对象，未接入数据库 | 需单独后端任务 |
| 处理池 API | review_queue 等池的检索、分配 API | 需单独后端任务 |
| 通知机制 | 反馈分配后通知责任人 | 需单独后端任务 |
| 前端反馈入口 | 家长端/老师端/学校端 UI | 需前端任务 |
| 反馈统计分析 | 反馈率、关闭率、聚类分析 | 需运营分析任务 |

---

## 5. 验收样例索引

12 个标准验收样例已固化至：
- `AEdu/08_观察层与产品层/qa_008_feedback_samples.json`

样例覆盖：
- FB-SAMPLE-001 ~ 006：6 个预设选项场景
- FB-SAMPLE-007 ~ 008：2 个自由文本场景
- FB-SAMPLE-009：1 个完整生命周期场景
- FB-SAMPLE-010 ~ 012：3 个边界验证场景

---

## 6. 与其他文档的关系

| 本文档 | 关联文档 | 关系说明 |
|--------|----------|----------|
| OBS-010-APPENDIX-001 | OBS-010 产品交互与反馈闭环 | 本文档是 OBS-010 的代码层附录 |
| OBS-010-APPENDIX-001 | qa_008_feedback_samples.json | 本文档断言由样例文件覆盖 |
| OBS-010-APPENDIX-001 | app/models/feedback_event.py | 本文档断言基于该实现 |
| OBS-010-APPENDIX-001 | tests/test_feedback_loop.py | 本文档断言由该测试验证 |

---

## 7. 维护说明

- **维护人**：DEV-A (反馈闭环负责人)
- **更新条件**：当 feedback_type、route_destination、status 枚举发生变化时更新
- **评审要求**：重大变更需 QA 复核

---

**文档状态**：已冻结（2026-04-02）  
**审批人**：DEV-A / QA / DOC 联审
