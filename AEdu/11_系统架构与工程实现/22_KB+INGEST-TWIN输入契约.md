# KB+INGEST-TWIN 输入契约

> 文档编号：ARCH-022  
> 版本：V1.0  
> 创建日期：2026-03-21  
> 最后更新：2026-03-21  
> 维护人：系统架构与工程实现负责人  
> 状态：已冻结（首轮骨架开发基线）  
> 用途：支撑 TWIN 首轮骨架开发  
> 变更方式：后续修改需通过新一轮准入评审

---

## 1. 文档目的与边界

本文档用于定义 KB + INGEST 向 TWIN 提供输入的最小稳定契约，回答以下问题：

1. TWIN 到底吃哪些事件
2. 哪些字段缺了还能继续
3. 哪些字段缺了必须拦住
4. 哪些情况进入 `review_needed`
5. KB 与 INGEST 对 TWIN 各自承担什么责任

本文档只定义模块契约级输入边界，不展开为：

- API 字段协议文档
- MQ 主题设计文档
- 数据库表结构文档
- 模型提示词文档

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
| 上游基线 | KB + INGEST 已冻结首轮骨架开发基线 |
| 下游消费方 | TWIN 首轮骨架开发 |

超出冻结范围的事件，不属于本契约允许消费范围。

---

## 3. 输入事件清单

TWIN 首轮只消费以下逻辑事件：

| 逻辑事件类型 | 来源 | 用途 | 是否允许直接进入状态更新 |
|--------------|------|------|----------------------------|
| `homework_result_event` | 老师反馈文本、扫描/OCR | 承接物理作业或纸面结果 | 条件允许 |
| `correction_followup_event` | 老师反馈文本、家长文本 | 承接订正、复做、跟进情况 | 允许 |
| `teacher_feedback_event` | 老师反馈文本 | 承接老师对学习表现的结构化观察 | 条件允许 |
| `parent_feedback_event` | 家长文本 | 承接家庭场景中的学习行为反馈 | 条件允许 |
| `scan_ocr_result_event` | 单页扫描/OCR | 承接纸面结果、题面定位、引用候选 | 条件允许 |
| `reviewed_learning_event` | 人工复核回写 | 用于修正 `review_needed` 事件 | 允许 |

说明：

- TWIN 不直接吃原始文本或原始 OCR 全文。
- TWIN 只消费上游已经标准化的事件对象。
- `reviewed_learning_event` 不是额外输入源，而是人工复核对上游事件的回写结果。

---

## 4. 必需字段清单

以下字段缺失时，TWIN 不允许进入主链路消费：

| 字段 | 作用 | 缺失处理 |
|------|------|----------|
| `event_id` | 事件唯一标识与幂等去重 | `reject` |
| `student_id` | 定位 StudentTwinAgent | `reject` |
| `event_type` | 决定消费和更新路径 | `reject` |
| `source_type` | 校验输入源是否在白名单中 | `reject` |
| `event_time` | 时间窗口与演化更新依据 | `reject` |
| `region_id` | 校验是否属于深圳范围 | `reject` |
| `stage_level` | 校验是否属于高中范围 | `reject` |
| `grade_level` | 校验是否属于高一范围 | `reject` |
| `subject` | 校验是否属于物理范围 | `reject` |
| `curriculum_version_id` | 校验是否属于 `PHY_PEP_G1_V1` | `reject` |
| `event_status` | 判断成功、降级、复核或拒绝 | `reject` |
| `confidence_score` | 判断是否进入 `review_needed` | `reject` |
| `event_summary` | 提供最小事件语义摘要 | `reject` |
| `raw_input_ref` | 追溯原始输入证据 | `reject` |
| `trace_id` | 审计与跨模块追踪 | `reject` |

---

## 5. 可选字段清单

以下字段不是所有事件都必须具备：

| 字段 | 用途 | 缺失时处理 |
|------|------|------------|
| `chapter_refs` | 章节级定位 | 可缺失，按规则降级 |
| `knowledge_refs` | 知识点级定位 | 可缺失，按规则降级 |
| `anchor_refs` | 教材锚点定位 | 可缺失 |
| `ability_refs` | 能力点关联 | 可缺失 |
| `score_payload` | 分数、正确率、完成度等结构化结果 | 可缺失 |
| `behavior_tags` | 行为标签摘要 | 可缺失 |
| `teacher_context_summary` | 老师场景摘要 | 可缺失 |
| `parent_context_summary` | 家长场景摘要 | 可缺失 |
| `review_ticket_ref` | 复核工单引用 | 仅在 `review_needed` 时需要 |
| `source_file_ref` | 扫描件或附件定位 | 非文本场景可填 |

可选字段缺失不等于自动拒绝，但是否允许进入主链路，要看具体事件类型和降级规则。

---

## 6. 字段合法性约束

### 6.1 范围合法性

以下条件必须同时成立：

- `region_id` 对应安徽
- `stage_level = 高中`
- `grade_level = 高一`
- `subject = 物理`
- `curriculum_version_id = PHY_PEP_G1_V1`

只要有任一条件不满足，即视为范围外输入，必须 `reject`。

### 6.2 来源合法性

`source_type` 只允许：

- `parent_text`
- `teacher_feedback_text`
- `scan_ocr`
- `reviewed_event`

其他来源类型均为非法来源，必须 `reject`。

### 6.3 状态合法性

`event_status` 只允许：

- `success`
- `degraded`
- `review_needed`
- `rejected`

其中：

- `success` 与 `degraded` 才能被 TWIN 尝试消费
- `review_needed` 只能进入人工复核路径
- `rejected` 不能进入 TWIN 状态更新

### 6.4 置信度合法性

`confidence_score` 必须满足：

- 值域在 `0 ~ 1`
- `scan_ocr` 事件低于 `0.70` 时，默认进入 `review_needed`
- 文本事件低于 `0.65` 时，默认进入 `review_needed`

### 6.5 引用一致性合法性

若事件带有 `chapter_refs / knowledge_refs / anchor_refs`，则必须满足：

- 都属于 `PHY_PEP_G1_V1`
- 不得跨教材版本混用
- `knowledge_refs` 与 `chapter_refs` 不得冲突
- `anchor_refs` 不得脱离章节或知识语义长期独立存在

---

## 7. `chapter_refs / knowledge_refs / anchor_refs` 的消费规则

### 7.1 `knowledge_refs` 消费规则

当 `knowledge_refs` 合法且稳定命中时：

- 允许更新知识掌握快照
- 允许更新当前关注点
- 允许参与风险与演化判断

当 `knowledge_refs` 缺失时：

- 不能直接更新知识掌握状态
- 不能直接更新 `mastery_gap`
- 只能根据其他条件决定降级、hold 或 `review_needed`

### 7.2 `chapter_refs` 消费规则

当 `chapter_refs` 合法但 `knowledge_refs` 缺失时：

- 允许更新章节级事实或进度摘要
- 不允许伪造知识点级状态
- 允许以 `degraded` 路径进入行为或事实层的有限更新

### 7.3 `anchor_refs` 消费规则

`anchor_refs` 主要用于：

- 扫描/OCR 输入定位
- 回贴教材位置
- 作为复核和追溯证据

单独存在 `anchor_refs` 时：

- 不允许直接更新知识掌握状态
- 不允许直接更新高风险结论
- 只能作为证据挂载，必要时进入 `review_needed`

---

## 8. 缺失引用时的降级策略

| 场景 | 是否允许继续 | 处理方式 |
|------|--------------|----------|
| `knowledge_refs` 缺失，但 `chapter_refs` 合法 | 允许 | `degraded`；只更新章节级事实或行为摘要 |
| `chapter_refs` 缺失，但 `knowledge_refs` 合法 | 允许 | 继续；章节可由 KB 反推，不构成阻断 |
| `anchor_refs` 缺失，但 `knowledge_refs` 合法 | 允许 | 继续；锚点不是首轮阻断字段 |
| `knowledge_refs` 与 `chapter_refs` 同时缺失，但事件属于行为观察 | 条件允许 | `degraded`；只更新行为层与数据质量层 |
| `knowledge_refs` 与 `chapter_refs` 同时缺失，且事件试图修改知识掌握状态 | 不允许 | `hold` 或 `review_needed`，不得直接更新 |
| `curriculum_version_id` 缺失 | 不允许 | `reject` |
| `student_id` 缺失 | 不允许 | `reject` |

---

## 9. `review_needed` 触发条件

出现以下任一情况时，事件必须进入 `review_needed`：

1. 置信度低于来源门槛。
2. `knowledge_refs` 与 `chapter_refs` 发生冲突。
3. 事件的地区、年级、学科与学生当前绑定冲突，但冲突原因无法自动判定。
4. OCR 事件只有候选引用，没有稳定命中。
5. 同一业务事实被两个事件给出明显冲突结果，且无法自动裁定。
6. 事件试图直接改写高风险状态，但缺乏足够事实支撑。
7. 事件结构虽然完整，但语义歧义过高，无法安全决定更新层级。

进入 `review_needed` 后：

- 不允许直接改写学生关键状态
- 必须生成 `review_ticket_ref`
- 必须保留 `raw_input_ref` 与 `trace_id`

---

## 10. 非法输入 / 不完整输入处理规则

### 10.1 `reject`

以下情况直接 `reject`：

- 关键必需字段缺失
- 范围外输入
- 来源非法
- `event_status = rejected`
- 幂等去重发现同一 `event_id` 已被成功消费

`reject` 后：

- 不更新 TWIN 任何状态
- 只保留错误日志和审计记录

### 10.2 `hold`

以下情况进入 `hold`：

- 输入合法，但知识引用不足以安全更新知识层
- 事件可用于后续补充，但当前不能直接改写关键状态
- 需要等待人工复核回写或上游补字段

`hold` 后：

- 允许保留待处理引用
- 不允许直接更新知识掌握与核心风险状态

### 10.3 `review_needed`

`review_needed` 适用于：

- 低置信度
- 强冲突
- 高风险更新争议
- OCR 语义不稳定

### 10.4 `success / degraded`

- `success`：满足直接更新条件，可进入 TWIN 状态主链路
- `degraded`：允许部分更新，但必须限制更新范围并明确降级原因

---

## 11. 与上游责任边界

| 模块 | 责任 | 不负责 |
|------|------|--------|
| KB | 提供教材版本、章节、知识点、锚点的权威引用体系 | 不负责原始输入解析、不负责学生状态更新 |
| INGEST | 解析原始输入、生成标准事件、给出质量判断和初始状态 | 不负责维护 TWIN 当前态、不负责长期状态演化 |
| TWIN | 消费合格标准事件，更新当前态并形成状态变化记录 | 不负责重做解析、不负责篡改 KB 主数据 |

结论是：

- KB 对“引用是否权威有效”负责
- INGEST 对“事件是否可被消费”负责
- TWIN 对“合格事件如何改变当前态”负责

---

## 12. 与 TWIN 状态更新的关系

本契约是 [TWIN 状态更新映射表](/Users/busiji/workbot/AEdu/05_学生数字孪生/14_TWIN状态更新映射表.md) 的前置门槛。

只有满足本契约的事件，TWIN 才能进入以下动作：

- 事实层更新
- 行为层更新
- 演化层刷新
- 风险层刷新
- 数据质量层刷新

不满足本契约的事件，不能绕过门槛直接改写 StudentTwinAgent。

---

## 13. 验收要点

本契约的最小验收要点如下：

1. TWIN 只消费冻结范围内的事件。
2. TWIN 不消费原始输入，只消费标准事件。
3. 缺少关键字段的事件必须被拦住。
4. 缺少部分知识引用但仍可形成行为摘要的事件，允许降级处理。
5. 低置信度或冲突事件必须进入 `review_needed`。
6. `chapter_refs / knowledge_refs / anchor_refs` 的消费规则必须可执行、可追溯。

---

## 14. 修订历史

| 版本 | 日期 | 变更内容 | 责任人 |
|------|------|----------|--------|
| V1.0 | 2026-03-21 | 首次冻结 KB + INGEST 到 TWIN 的首轮输入契约 | 系统架构与工程实现负责人 |
