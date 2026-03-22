# KB+INGEST 端到端样例集

> 文档编号：ARCH-021  
> 版本：V1.0  
> 创建日期：2026-03-21  
> 最后更新：2026-03-21  
> 维护人：系统架构与工程实现负责人  
> 状态：已冻结（首轮骨架开发基线）  
> 用途：支撑 KB + INGEST 首轮骨架开发  
> 变更方式：后续修改需通过新一轮准入评审

---

## 1. 文档目的

本文档用于为 KB + INGEST 首轮骨架开发提供可直接执行的端到端样例，统一“原始输入 → 清洗与解析 → 学习事件 → 知识引用 → 输出结果”的最小闭环口径。

本文档重点回答以下问题：

1. 首轮开发到底要跑通什么样的样例
2. 学习事件如何引用知识底座
3. 哪些输入可以直接进入主链路
4. 哪些输入必须进入人工复核
5. 如何用具体样例验证 KB 与 INGEST 的协同是否成立

---

## 2. 适用范围

本文样例仅用于 KB + INGEST 首轮骨架开发的开发、联调与验收。

适用范围包括：

- 高中阶段
- 高一
- 物理学科
- 人教版必修一
- 首轮试点输入源中的文本输入、扫描/OCR 输入
- 正常样例与低置信度样例

不适用范围包括：

- 全学科并行样例
- 多地区教材版本切换样例
- 学生状态更新后的 TWIN 深层计算样例
- GRAPH、OBS、SIM 的完整下游业务样例

---

## 3. 样例约束说明

### 3.1 首轮样例统一前提

| 维度 | 冻结值 |
|------|--------|
| 地区 | 安徽省 |
| 学段 | 高中 |
| 年级 | 高一 |
| 学科 | 物理 |
| 教材版本 | `PHY_PEP_G1_V1` |
| 首发教材对象 | `MAT-PHYS-001` 高中物理必修一知识树 |
| 首发主链路 | 输入 → 学习事件 → 知识引用 → 事件出库/复核出库 |

### 3.2 引用字段约定

| 字段 | 含义 |
|------|------|
| `chapter_refs` | 引用章节树节点 |
| `knowledge_refs` | 引用知识点节点 |
| `anchor_refs` | 引用教材锚点 |
| `ability_refs` | 引用能力点 |
| `curriculum_version_id` | 引用教材版本 |

### 3.3 样例判定原则

- 正常样例必须能进入标准学习事件主链路。
- OCR 样例允许存在一定噪声，但必须能给出可解释的结构化结果。
- 低置信度样例不得直接污染主链路，必须进入人工复核队列。
- 每个样例都必须能回溯到知识底座中的明确引用或明确的失败原因。

---

## 4. 端到端样例一：家长文本输入正常入链

### 4.1 输入

输入源：家长聊天窗口文本  
原始输入：

> 今天物理作业写完了，受力分析那页错了两题。

输入上下文：

| 字段 | 值 |
|------|----|
| tenant_id | `TENANT_SZ_PILOT_001` |
| student_id | `STU_GD_SZ_G10_001` |
| class_id | `CLS_GD_SZ_G10_01` |
| school_id | `SCH_GD_SZ_PILOT_001` |
| source_role | `parent` |
| source_channel | `wechat` |
| raw_input_id | `RAW_TXT_0001` |
| ingested_at | `2026-03-21T19:30:00+08:00` |

### 4.2 处理

#### 4.2.1 清洗

- 去除无关语气词和口语停顿
- 识别学科候选：物理
- 识别事件候选：作业完成 + 错题信息
- 将“那页”视为弱定位信息，不作为独立结构字段
- 时间未显式给出，使用录入日作为弱代理，并标注时间精度为 `day`

#### 4.2.2 结构化

- `event_type = homework`
- `event_subtype = after_school_homework`
- `event_action = finish`
- `summary = 完成物理作业，受力分析相关内容错 2 题`
- `detail_payload.wrong_count = 2`
- `detail_payload.completion_status = completed`
- `parsing_status = parsed`
- `validation_status = valid`
- `requires_manual_review = false`

#### 4.2.3 知识映射

- 从关键词“受力分析”匹配到首发知识树中的章节主题
- 建立章节、知识点、能力点、锚点候选
- 因文本未包含具体页码，锚点采用章节级默认锚点

### 4.3 知识引用

| 引用类型 | 引用值 | 说明 |
|----------|--------|------|
| `curriculum_version_id` | `PHY_PEP_G1_V1` | 首发教材版本 |
| `chapter_refs` | `["PHY_PEP_G1_V1_SEC_03_01"]` | 对应“受力分析”章节节点 |
| `knowledge_refs` | `["PHY_PEP_G1_KP_021"]` | 对应受力分析核心知识点 |
| `anchor_refs` | `["PHY_ANCHOR_020"]` | 对应章节级默认锚点 |
| `ability_refs` | `["PHY_AP_003"]` | 对应受力分析能力 |

### 4.4 输出

```json
{
  "event_id": "EVT_HW_0001",
  "raw_input_id": "RAW_TXT_0001",
  "tenant_id": "TENANT_SZ_PILOT_001",
  "student_id": "STU_GD_SZ_G10_001",
  "class_id": "CLS_GD_SZ_G10_01",
  "school_id": "SCH_GD_SZ_PILOT_001",
  "event_time": "2026-03-21T00:00:00+08:00",
  "event_time_precision": "day",
  "ingested_at": "2026-03-21T19:30:00+08:00",
  "source_type": "text_input",
  "source_channel": "wechat",
  "source_role": "parent",
  "event_type": "homework",
  "event_subtype": "after_school_homework",
  "event_action": "finish",
  "title": "物理作业完成",
  "summary": "完成受力分析相关作业，错 2 题",
  "detail_payload": {
    "completion_status": "completed",
    "wrong_count": 2
  },
  "subject": "physics",
  "chapter_refs": ["PHY_PEP_G1_V1_SEC_03_01"],
  "knowledge_refs": ["PHY_PEP_G1_KP_021"],
  "anchor_refs": ["PHY_ANCHOR_020"],
  "ability_refs": ["PHY_AP_003"],
  "curriculum_version_id": "PHY_PEP_G1_V1",
  "confidence_score": 0.91,
  "completeness_score": 0.86,
  "parsing_status": "parsed",
  "validation_status": "valid",
  "requires_manual_review": false
}
```

### 4.5 验收点

- [ ] 能正确识别为物理作业事件，而不是泛化为普通反馈
- [ ] 能引用到“受力分析”相关章节和知识点
- [ ] 缺少具体页码时，允许引用章节级锚点而不阻断主链路
- [ ] 事件可直接进入标准学习事件库，不进入人工复核
- [ ] 全链路保留原始输入与结构化结果的可追溯关系

---

## 5. 端到端样例二：扫描件 / OCR 输入正常入链

### 5.1 输入

输入源：作业照片 OCR  
原始输入：

- 一张物理练习册拍照图片
- OCR 识别文本摘要：

> 受力分析练习 1  
> 第 3 题错误  
> 第 5 题错误  
> 共 10 题  
> 得分 80 分

输入上下文：

| 字段 | 值 |
|------|----|
| tenant_id | `TENANT_SZ_PILOT_001` |
| student_id | `STU_GD_SZ_G10_002` |
| class_id | `CLS_GD_SZ_G10_01` |
| school_id | `SCH_GD_SZ_PILOT_001` |
| source_role | `teacher` |
| source_channel | `scanner` |
| source_file_ref | `FILE_IMG_0008` |
| raw_input_id | `RAW_IMG_0008` |
| ingested_at | `2026-03-22T08:45:00+08:00` |

### 5.2 处理

#### 5.2.1 清洗

- 图片质量检测通过，未触发 `ocr_bad`
- OCR 文本去除多余换行与噪点
- 提取题量、错误题数、得分信息
- 从标题“受力分析练习 1”抽取章节/知识点候选

#### 5.2.2 结构化

- `event_type = homework`
- `event_subtype = workbook_scan`
- `event_action = score_recorded`
- `detail_payload.question_count = 10`
- `detail_payload.wrong_count = 2`
- `metric_payload.accuracy_rate = 0.8`
- `parsing_status = parsed`
- `validation_status = valid`
- `requires_manual_review = false`

#### 5.2.3 知识映射

- 优先按练习标题匹配知识点
- 若标题与章节树命中，则回贴对应教材锚点
- 因为是练习场景，锚点类型记为 `exercise`

### 5.3 知识引用

| 引用类型 | 引用值 | 说明 |
|----------|--------|------|
| `curriculum_version_id` | `PHY_PEP_G1_V1` | 首发教材版本 |
| `chapter_refs` | `["PHY_PEP_G1_V1_SEC_03_01"]` | “受力分析”章节节点 |
| `knowledge_refs` | `["PHY_PEP_G1_KP_021"]` | 受力分析知识点 |
| `anchor_refs` | `["PHY_ANCHOR_021"]` | 对应练习题锚点 |
| `ability_refs` | `["PHY_AP_003", "PHY_AP_007"]` | 受力分析与建模能力 |

### 5.4 输出

```json
{
  "event_id": "EVT_HW_0008",
  "raw_input_id": "RAW_IMG_0008",
  "tenant_id": "TENANT_SZ_PILOT_001",
  "student_id": "STU_GD_SZ_G10_002",
  "class_id": "CLS_GD_SZ_G10_01",
  "school_id": "SCH_GD_SZ_PILOT_001",
  "event_time": "2026-03-22T08:45:00+08:00",
  "event_time_precision": "minute",
  "ingested_at": "2026-03-22T08:45:00+08:00",
  "processed_at": "2026-03-22T08:45:04+08:00",
  "source_type": "image_scan",
  "source_channel": "scanner",
  "source_role": "teacher",
  "source_file_ref": "FILE_IMG_0008",
  "event_type": "homework",
  "event_subtype": "workbook_scan",
  "event_action": "score_recorded",
  "title": "受力分析练习结果入库",
  "summary": "共 10 题，错 2 题，正确率 80%",
  "detail_payload": {
    "homework_name": "受力分析练习 1",
    "question_count": 10,
    "wrong_count": 2,
    "score": 80,
    "full_score": 100
  },
  "metric_payload": {
    "accuracy_rate": 0.8
  },
  "subject": "physics",
  "chapter_refs": ["PHY_PEP_G1_V1_SEC_03_01"],
  "knowledge_refs": ["PHY_PEP_G1_KP_021"],
  "anchor_refs": ["PHY_ANCHOR_021"],
  "ability_refs": ["PHY_AP_003", "PHY_AP_007"],
  "curriculum_version_id": "PHY_PEP_G1_V1",
  "confidence_score": 0.88,
  "completeness_score": 0.93,
  "parsing_status": "parsed",
  "validation_status": "valid",
  "requires_manual_review": false
}
```

### 5.5 验收点

- [ ] OCR 输入能正确清洗并提取题量、错题数、分数
- [ ] OCR 结果能稳定映射到“受力分析”章节，而不是泛化到“力与运动”
- [ ] 练习类输入的锚点类型应为 `exercise`
- [ ] 输出事件字段完整，可直接供后续模块消费
- [ ] 原图、OCR 文本、结构化结果、知识引用可全链路追溯

---

## 6. 端到端样例三：低置信度输入进入人工复核

### 6.1 输入

输入源：家长上传照片 + 短文本  
原始输入：

> 孩子今天这张物理卷子状态不太对，力学那块又不行了。

附件情况：

- 上传一张模糊试卷照片
- OCR 识别结果片段化，包含多个不可读字符
- 试卷上未明确出现学生姓名
- 文本中“力学那块”无法稳定定位到单一章节或知识点

输入上下文：

| 字段 | 值 |
|------|----|
| tenant_id | `TENANT_SZ_PILOT_001` |
| student_id | `STU_GD_SZ_G10_003` |
| class_id | `CLS_GD_SZ_G10_01` |
| school_id | `SCH_GD_SZ_PILOT_001` |
| source_role | `parent` |
| source_channel | `wechat` |
| source_file_ref | `FILE_IMG_0015` |
| raw_input_id | `RAW_MIX_0015` |
| ingested_at | `2026-03-22T21:10:00+08:00` |

### 6.2 处理

#### 6.2.1 清洗

- 文本去噪后保留关键信号：物理、卷子、力学那块、状态不太对
- 图像质量检测不通过，触发 `ocr_bad`
- OCR 文本乱码占比过高，不进入自动知识映射
- 虽然学生上下文存在，但知识引用对象不明确

#### 6.2.2 结构化

- 可初步识别为 `exam` / `parent_feedback` 候选之一，但无法稳定落类
- `parsing_status = partially_parsed`
- `validation_status = weak_valid`
- `requires_manual_review = true`
- `ambiguity_flags` 至少包含：
  - `content_noisy`
  - `ocr_bad`
  - `knowledge_mapping_uncertain`

#### 6.2.3 复核路由

- 不生成正式学习事件入主链路
- 生成一条人工复核任务
- 待人工确认后，才能补齐事件类型、知识引用和锚点引用

### 6.3 知识引用

| 引用类型 | 引用值 | 说明 |
|----------|--------|------|
| `curriculum_version_id` | `PHY_PEP_G1_V1` | 可继承学生已绑定教材版本 |
| `chapter_refs` | `[]` | 暂不允许猜测 |
| `knowledge_refs` | `[]` | 暂不允许猜测 |
| `anchor_refs` | `[]` | 图片质量不足，不能稳定锚定 |
| `ability_refs` | `[]` | 暂不允许猜测 |

### 6.4 输出

```json
{
  "review_task_id": "RVW_0015",
  "raw_input_id": "RAW_MIX_0015",
  "tenant_id": "TENANT_SZ_PILOT_001",
  "student_id": "STU_GD_SZ_G10_003",
  "class_id": "CLS_GD_SZ_G10_01",
  "school_id": "SCH_GD_SZ_PILOT_001",
  "ingested_at": "2026-03-22T21:10:00+08:00",
  "source_type": "image_scan",
  "source_channel": "wechat",
  "source_role": "parent",
  "source_file_ref": "FILE_IMG_0015",
  "candidate_event_types": ["exam", "parent_feedback"],
  "subject_candidate": "physics",
  "curriculum_version_id": "PHY_PEP_G1_V1",
  "chapter_refs": [],
  "knowledge_refs": [],
  "anchor_refs": [],
  "ability_refs": [],
  "confidence_score": 0.42,
  "completeness_score": 0.51,
  "parsing_status": "partially_parsed",
  "validation_status": "weak_valid",
  "ambiguity_flags": [
    "content_noisy",
    "ocr_bad",
    "knowledge_mapping_uncertain"
  ],
  "requires_manual_review": true,
  "review_reason": "无法稳定确认事件类型与知识引用，且 OCR 质量不足",
  "next_action": "route_to_manual_review_queue"
}
```

### 6.5 验收点

- [ ] 低置信度输入不会被错误写成正式学习事件
- [ ] 系统能明确说明为什么进入人工复核，而不是只给出“失败”
- [ ] 学生上下文允许继承教材版本，但不允许据此硬猜章节和知识点
- [ ] 人工复核任务中必须保留原始文本、原图、OCR 结果和异常标记
- [ ] 复核任务可回流到主链路，但回流前不得污染 KB 引用关系

---

## 7. 样例使用说明

### 7.1 用于开发联调
三组样例应作为 KB + INGEST 首轮骨架开发的固定样例集，开发、测试、联调都使用同一份口径。

### 7.2 用于验收校准
若实现结果与本文样例集的结构化结果、知识引用结果或异常路由结果不一致，应视为未通过首轮准入验收。

### 7.3 用于规则迭代
第三组低置信度样例不要求首轮自动解决，但必须保证：

- 能识别异常
- 能进入复核
- 能保留引用上下文
- 能为后续规则优化提供回流依据

---

## 8. 结论

对于 KB + INGEST 首轮骨架开发，以上三组样例已足以覆盖：

- 正常文本输入主链路
- OCR/扫描输入主链路
- 低置信度输入人工复核链路

若实现无法稳定通过这三组样例，则不应进入全量实现或全量联调。
