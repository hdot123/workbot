# 📊 数据库表结构文档

**项目**: 学生词汇学习管理系统 (Student Vocabulary Learning Management System)
**版本**: v5.0
**数据库**: PostgreSQL (Supabase)
**项目 ID**: `axtbgfmitrsflqiwudni`
**生成时间**: 2026-03-11

---

## 📋 目录

- [核心业务表](#核心业务表)
- [学习进度与记录](#学习进度与记录)
- [高考教育数据系统](#高考教育数据系统)
- [志愿服务系统](#志愿服务系统)
- [系统集成与监控](#系统集成与监控)
- [数据库视图](#数据库视图)
- [枚举常量定义](#枚举常量定义)

---

## 核心业务表

### 1. `users` - 用户表 (Supabase Auth)
Supabase 内置认证用户表

### 2. `user_profiles` - 用户画像表

| 列名 | 类型 | 说明 | 约束 |
|------|------|------|------|
| id | UUID | 主键 | PK, FK → users.id |
| full_name | VARCHAR | 全名 | |
| avatar_url | VARCHAR | 头像 URL | |
| school_id | UUID | 学校 ID | FK → schools.id |
| created_at | TIMESTAMP | 创建时间 | |
| updated_at | TIMESTAMP | 更新时间 | |

### 3. `schools` - 学校表

| 列名 | 类型 | 说明 | 约束 |
|------|------|------|------|
| id | UUID | 主键 | PK |
| name | VARCHAR | 学校名称 | NOT NULL |
| school_type | VARCHAR | 学校类型 | MIDDLE_SCHOOL / HIGH_SCHOOL / COMPLETE_SCHOOL |
| created_at | TIMESTAMP | 创建时间 | |
| updated_at | TIMESTAMP | 更新时间 | |

### 4. `classes` - 班级表

| 列名 | 类型 | 说明 | 约束 |
|------|------|------|------|
| id | UUID | 主键 | PK |
| name | VARCHAR | 班级名称 | NOT NULL |
| grade_level | INTEGER | 年级 (1-12) | NOT NULL |
| school_id | UUID | 学校 ID | FK → schools.id |
| teacher_id | UUID | 教师用户 ID | FK → users.id |
| created_at | TIMESTAMP | 创建时间 | |
| updated_at | TIMESTAMP | 更新时间 | |

### 5. `user_roles` - 用户角色表

| 列名 | 类型 | 说明 | 约束 |
|------|------|------|------|
| id | UUID | 主键 | PK |
| user_id | UUID | 用户 ID | FK → users.id, UNIQUE |
| role | VARCHAR | 角色 | student / teacher / admin |
| created_at | TIMESTAMP | 创建时间 | |

### 6. `class_join_requests` - 班级加入申请表

| 列名 | 类型 | 说明 | 约束 |
|------|------|------|------|
| id | UUID | 主键 | PK |
| student_id | UUID | 学生 ID | FK → users.id |
| class_id | UUID | 班级 ID | FK → classes.id |
| status | VARCHAR | 申请状态 | pending / approved / rejected |
| created_at | TIMESTAMP | 创建时间 | |
| updated_at | TIMESTAMP | 更新时间 | |

---

## 学习进度与记录

### 7. `textbooks` - 教材表

| 列名 | 类型 | 说明 | 约束 |
|------|------|------|------|
| id | UUID | 主键 | PK |
| name | VARCHAR | 教材名称 | NOT NULL |
| grade_level | INTEGER | 适用年级 | |
| publisher | VARCHAR | 出版社 | |
| created_at | TIMESTAMP | 创建时间 | |

### 8. `lessons` - 课程/单元表

| 列名 | 类型 | 说明 | 约束 |
|------|------|------|------|
| id | UUID | 主键 | PK |
| textbook_id | UUID | 教材 ID | FK → textbooks.id |
| lesson_number | INTEGER | 课次 | NOT NULL |
| title | VARCHAR | 标题 | NOT NULL |
| created_at | TIMESTAMP | 创建时间 | |

### 9. `words` - 词汇表

| 列名 | 类型 | 说明 | 约束 |
|------|------|------|------|
| id | UUID | 主键 | PK |
| lesson_id | UUID | 课程 ID | FK → lessons.id |
| word | VARCHAR | 单词/词语 | NOT NULL |
| pinyin | VARCHAR | 拼音 | |
| definition | TEXT | 释义 | |
| example | TEXT | 例句 | |
| created_at | TIMESTAMP | 创建时间 | |

### 10. `vocabulary_progress` - 词汇学习进度表

| 列名 | 类型 | 说明 | 约束 |
|------|------|------|------|
| id | UUID | 主键 | PK |
| user_id | UUID | 用户 ID | FK → users.id |
| word_id | UUID | 词汇 ID | FK → words.id |
| mastery_level | INTEGER | 掌握等级 (0-5) | DEFAULT 0 |
| review_count | INTEGER | 复习次数 | DEFAULT 0 |
| last_reviewed_at | TIMESTAMP | 最后复习时间 | |
| next_review_at | TIMESTAMP | 下次复习时间 | |
| created_at | TIMESTAMP | 创建时间 | |
| updated_at | TIMESTAMP | 更新时间 | |

### 11. `learning_logs` - 学习日志表

| 列名 | 类型 | 说明 | 约束 |
|------|------|------|------|
| id | UUID | 主键 | PK |
| user_id | UUID | 用户 ID | FK → users.id |
| word_id | UUID | 词汇 ID | FK → words.id |
| action_type | VARCHAR | 动作类型 | practice_correct / practice_wrong / review_correct / review_wrong / mastered / forgotten |
| created_at | TIMESTAMP | 创建时间 | |

### 12. `session_snapshots` - 学习会话快照表

| 列名 | 类型 | 说明 | 约束 |
|------|------|------|------|
| id | UUID | 主键 | PK |
| user_id | UUID | 用户 ID | FK → users.id |
| snapshot_data | JSONB | 快照数据 | |
| created_at | TIMESTAMP | 创建时间 | |

### 13. `growth_records` - 成长记录表

| 列名 | 类型 | 说明 | 约束 |
|------|------|------|------|
| id | UUID | 主键 | PK |
| user_id | UUID | 用户 ID | FK → users.id |
| type | VARCHAR | 记录类型 | homework / exam / practice |
| title | VARCHAR | 标题 | |
| description | TEXT | 描述 | |
| file_url | VARCHAR | 文件 URL | |
| status | VARCHAR | 处理状态 | uploading / processing / completed / failed |
| created_at | TIMESTAMP | 创建时间 | |
| updated_at | TIMESTAMP | 更新时间 | |

### 14. `learning_goals` - 学习目标表

| 列名 | 类型 | 说明 | 约束 |
|------|------|------|------|
| id | UUID | 主键 | PK |
| user_id | UUID | 用户 ID | FK → users.id |
| goal_type | VARCHAR | 目标类型 | word_count / accuracy / exam_score / knowledge_point |
| target_value | DECIMAL | 目标值 | |
| current_value | DECIMAL | 当前值 | |
| status | VARCHAR | 目标状态 | active / completed / paused / cancelled |
| priority | VARCHAR | 优先级 | high / medium / low |
| deadline | DATE | 截止日期 | |
| created_at | TIMESTAMP | 创建时间 | |
| updated_at | TIMESTAMP | 更新时间 | |

### 15. `knowledge_points` - 知识点表

| 列名 | 类型 | 说明 | 约束 |
|------|------|------|------|
| id | UUID | 主键 | PK |
| name | VARCHAR | 知识点名称 | NOT NULL |
| description | TEXT | 描述 | |
| parent_id | UUID | 父知识点 ID | FK → knowledge_points.id |
| created_at | TIMESTAMP | 创建时间 | |

### 16. `knowledge_point_progress` - 知识点进度表

| 列名 | 类型 | 说明 | 约束 |
|------|------|------|------|
| id | UUID | 主键 | PK |
| user_id | UUID | 用户 ID | FK → users.id |
| knowledge_point_id | UUID | 知识点 ID | FK → knowledge_points.id |
| mastery_status | VARCHAR | 掌握状态 | not_started / learning / mastered / reviewing |
| practice_count | INTEGER | 练习次数 | DEFAULT 0 |
| accuracy_rate | DECIMAL | 正确率 | |
| last_practiced_at | TIMESTAMP | 最后练习时间 | |
| created_at | TIMESTAMP | 创建时间 | |
| updated_at | TIMESTAMP | 更新时间 | |

### 17. `pdf_import_logs` - PDF 导入日志表

| 列名 | 类型 | 说明 | 约束 |
|------|------|------|------|
| id | UUID | 主键 | PK |
| user_id | UUID | 用户 ID | FK → users.id |
| file_name | VARCHAR | 文件名 | |
| import_type | VARCHAR | 导入类型 | textbook / homework |
| status | VARCHAR | 处理状态 | pending / processing / completed / failed |
| error_message | TEXT | 错误信息 | |
| created_at | TIMESTAMP | 创建时间 | |
| updated_at | TIMESTAMP | 更新时间 | |

---

## 高考教育数据系统

### 18. `high_schools` - 高中学校表

| 列名 | 类型 | 说明 | 约束 |
|------|------|------|------|
| id | UUID | 主键 | PK |
| name | VARCHAR | 学校名称 | NOT NULL |
| province | VARCHAR | 省份 | |
| city | VARCHAR | 城市 | |
| school_type | VARCHAR | 学校类型 | MIDDLE_SCHOOL / HIGH_SCHOOL / COMPLETE_SCHOOL |
| school_level | VARCHAR | 学校级别 | 省级重点 / 市级重点 / 区级重点 / 普通 |
| created_at | TIMESTAMP | 创建时间 | |

### 19. `middle_schools` - 初中学校表

| 列名 | 类型 | 说明 | 约束 |
|------|------|------|------|
| id | UUID | 主键 | PK |
| name | VARCHAR | 学校名称 | NOT NULL |
| province | VARCHAR | 省份 | |
| city | VARCHAR | 城市 | |
| school_type | VARCHAR | 学校类型 | MIDDLE_SCHOOL / HIGH_SCHOOL / COMPLETE_SCHOOL |
| created_at | TIMESTAMP | 创建时间 | |

### 20. `universities` - 大学表

| 列名 | 类型 | 说明 | 约束 |
|------|------|------|------|
| id | UUID | 主键 | PK |
| name | VARCHAR | 大学名称 | NOT NULL |
| province | VARCHAR | 省份 | |
| city | VARCHAR | 城市 | |
| university_level | VARCHAR | 大学层次 | 985 / 211 / 双一流 / 普通本科 / 高职专科 |
| university_type | VARCHAR | 大学类型 | 综合 / 理工 / 农林 / 医药 / 师范 / 财经 / 政法 / 语言 / 艺术 / 体育 |
| created_at | TIMESTAMP | 创建时间 | |

### 21. `majors` - 专业表

| 列名 | 类型 | 说明 | 约束 |
|------|------|------|------|
| id | UUID | 主键 | PK |
| name | VARCHAR | 专业名称 | NOT NULL |
| category | VARCHAR | 学科门类 | |
| degree_level | VARCHAR | 学历层次 | 本科 / 专科 |
| created_at | TIMESTAMP | 创建时间 | |

### 22. `university_majors` - 大学专业关联表

| 列名 | 类型 | 说明 | 约束 |
|------|------|------|------|
| id | UUID | 主键 | PK |
| university_id | UUID | 大学 ID | FK → universities.id |
| major_id | UUID | 专业 ID | FK → majors.id |
| created_at | TIMESTAMP | 创建时间 | |

### 23. `enrollment_plans` - 招生计划表

| 列名 | 类型 | 说明 | 约束 |
|------|------|------|------|
| id | UUID | 主键 | PK |
| university_id | UUID | 大学 ID | FK → universities.id |
| major_id | UUID | 专业 ID | FK → majors.id |
| province | VARCHAR | 招生省份 | |
| year | INTEGER | 年份 | |
| quota | INTEGER | 招生名额 | |
| created_at | TIMESTAMP | 创建时间 | |

### 24. `province_cutoff_scores` - 省控线表

| 列名 | 类型 | 说明 | 约束 |
|------|------|------|------|
| id | UUID | 主键 | PK |
| province | VARCHAR | 省份 | |
| year | INTEGER | 年份 | |
| subject_category | VARCHAR | 科目类别 | 理科 / 文科 / 综合改革 / 物理类 / 历史类 |
| batch | VARCHAR | 批次 | 一本 / 二本 / 专科 |
| cutoff_score | INTEGER | 省控线分数 | |
| created_at | TIMESTAMP | 创建时间 | |

### 25. `university_cutoff_scores` - 大学录取线表

| 列名 | 类型 | 说明 | 约束 |
|------|------|------|------|
| id | UUID | 主键 | PK |
| university_id | UUID | 大学 ID | FK → universities.id |
| province | VARCHAR | 省份 | |
| year | INTEGER | 年份 | |
| subject_category | VARCHAR | 科目类别 | |
| batch | VARCHAR | 批次 | |
| min_score | INTEGER | 最低录取分 | |
| avg_score | DECIMAL | 平均录取分 | |
| created_at | TIMESTAMP | 创建时间 | |

### 26. `major_cutoff_scores` - 专业录取线表

| 列名 | 类型 | 说明 | 约束 |
|------|------|------|------|
| id | UUID | 主键 | PK |
| university_major_id | UUID | 大学专业 ID | FK → university_majors.id |
| province | VARCHAR | 省份 | |
| year | INTEGER | 年份 | |
| min_score | INTEGER | 最低录取分 | |
| avg_score | DECIMAL | 平均录取分 | |
| created_at | TIMESTAMP | 创建时间 | |

### 27. `score_ranking_tables` - 一分一段表

| 列名 | 类型 | 说明 | 约束 |
|------|------|------|------|
| id | UUID | 主键 | PK |
| province | VARCHAR | 省份 | |
| year | INTEGER | 年份 | |
| subject_category | VARCHAR | 科目类别 | |
| score | INTEGER | 分数 | |
| ranking | INTEGER | 排名 | |
| same_score_count | INTEGER | 同分人数 | |
| created_at | TIMESTAMP | 创建时间 | |

### 28. `admission_predictions` - 录取预测表

| 列名 | 类型 | 说明 | 约束 |
|------|------|------|------|
| id | UUID | 主键 | PK |
| user_id | UUID | 用户 ID | FK → users.id |
| university_id | UUID | 大学 ID | FK → universities.id |
| major_id | UUID | 专业 ID | FK → majors.id |
| predicted_score | INTEGER | 预测分数 | |
| admission_probability | DECIMAL | 录取概率 (0-100) | |
| risk_level | VARCHAR | 风险等级 | 冲刺 / 稳妥 / 保守 / 困难 |
| created_at | TIMESTAMP | 创建时间 | |

### 29. `career_assessments` - 职业测评表

| 列名 | 类型 | 说明 | 约束 |
|------|------|------|------|
| id | UUID | 主键 | PK |
| user_id | UUID | 用户 ID | FK → users.id |
| assessment_type | VARCHAR | 测评类型 | holland / mbti / ability / personality |
| assessment_result | JSONB | 测评结果 | |
| created_at | TIMESTAMP | 创建时间 | |

### 30. `holland_major_mapping` - 霍兰德专业映射表

| 列名 | 类型 | 说明 | 约束 |
|------|------|------|------|
| id | UUID | 主键 | PK |
| holland_code | VARCHAR | 霍兰德代码 | |
| major_id | UUID | 专业 ID | FK → majors.id |
| compatibility_score | DECIMAL | 匹配度分数 | |
| created_at | TIMESTAMP | 创建时间 | |

---

## 志愿服务系统

### 31. `volunteer_opportunities` - 志愿服务机会表

| 列名 | 类型 | 说明 | 约束 |
|------|------|------|------|
| id | UUID | 主键 | PK |
| title | VARCHAR | 标题 | NOT NULL |
| description | TEXT | 描述 | |
| location | VARCHAR | 地点 | |
| start_time | TIMESTAMP | 开始时间 | |
| end_time | TIMESTAMP | 结束时间 | |
| max_participants | INTEGER | 最大参与人数 | |
| current_participants | INTEGER | 当前参与人数 | DEFAULT 0 |
| is_active | BOOLEAN | 是否激活 | DEFAULT true |
| created_at | TIMESTAMP | 创建时间 | |
| updated_at | TIMESTAMP | 更新时间 | |

### 32. `volunteer_applications` - 志愿服务申请表

| 列名 | 类型 | 说明 | 约束 |
|------|------|------|------|
| id | UUID | 主键 | PK |
| user_id | UUID | 用户 ID | FK → users.id |
| opportunity_id | UUID | 志愿机会 ID | FK → volunteer_opportunities.id |
| status | VARCHAR | 申请状态 | pending / approved / rejected / cancelled |
| applied_at | TIMESTAMP | 申请时间 | |
| reviewed_at | TIMESTAMP | 审核时间 | |
| created_at | TIMESTAMP | 创建时间 | |

---

## 系统集成与监控

### 33. `system_integrations` - 系统集成配置表

| 列名 | 类型 | 说明 | 约束 |
|------|------|------|------|
| id | UUID | 主键 | PK |
| service_type | VARCHAR | 服务类型 | ocr / ai / storage / email / payment |
| service_name | VARCHAR | 服务名称 | |
| api_endpoint | VARCHAR | API 端点 | |
| credentials | JSONB | 凭证信息（加密） | |
| is_active | BOOLEAN | 是否激活 | DEFAULT true |
| created_at | TIMESTAMP | 创建时间 | |
| updated_at | TIMESTAMP | 更新时间 | |

### 34. `performance_snapshots` - 性能快照表

| 列名 | 类型 | 说明 | 约束 |
|------|------|------|------|
| id | UUID | 主键 | PK |
| metric_name | VARCHAR | 指标名称 | |
| metric_value | DECIMAL | 指标值 | |
| metadata | JSONB | 元数据 | |
| created_at | TIMESTAMP | 创建时间 | |

---

## 数据库视图

### 视图 1: `mastery_risk_detection` - 掌握风险检测视图

**用途**: 焦虑引擎核心视图，识别"虚假掌握"（高分低能）学生

**核心算法**:
```sql
Gap = Homework_Accuracy - Exam_Accuracy
```

**风险判定**:
- `Gap > 30%` → **高风险** (焦虑等级: 高)
- `Gap > 15%` → **中风险** (焦虑等级: 中)
- `Gap < 5%` → **低风险** (焦虑等级: 低)

**关键字段**:
- student_id
- student_name
- assignment_accuracy (作业正确率)
- exam_accuracy (考试正确率)
- accuracy_delta (Δ 指标)
- anxiety_level (焦虑等级)
- student_model (学生模型分类)

### 视图 2: `user_learning_summary` - 用户学习汇总视图

**用途**: 汇总用户的学习进度、正确率、掌握程度等指标

### 视图 3: `weak_points_analysis` - 薄弱点分析视图

**用途**: 识别学生的薄弱知识点和高频错误词汇

### 视图 4: `learning_efficiency_analysis` - 学习效率分析视图

**用途**: 分析用户的学习效率、时间投入与成果对比

### 视图 5: `student_goal_progress_summary` - 学生目标进度汇总视图

**用途**: 追踪学生学习目标的完成进度

### 视图 6: `knowledge_mastery_dashboard` - 知识点掌握仪表盘

**用途**: 可视化展示学生的知识点掌握情况

---

## 枚举常量定义

所有枚举常量定义在 `src/utils/constants.js` 文件中：

### 用户角色 (USER_ROLES)
- `student` - 学生
- `teacher` - 教师
- `admin` - 管理员

### 班级加入申请状态 (JOIN_REQUEST_STATUS)
- `pending` - 待审核
- `approved` - 已通过
- `rejected` - 已拒绝

### 学习目标状态 (GOAL_STATUS)
- `active` - 激活中
- `completed` - 已完成
- `paused` - 已暂停
- `cancelled` - 已取消

### 学习目标类型 (GOAL_TYPES)
- `word_count` - 词汇数量目标
- `accuracy` - 正确率目标
- `exam_score` - 考试成绩目标
- `knowledge_point` - 知识点掌握目标

### 优先级 (PRIORITY_LEVELS)
- `high` - 高
- `medium` - 中
- `low` - 低

### 知识点掌握状态 (MASTERY_STATUS)
- `not_started` - 未开始
- `learning` - 学习中
- `mastered` - 已掌握
- `reviewing` - 复习中

### 成长记录类型 (GROWTH_RECORD_TYPES)
- `homework` - 作业
- `exam` - 考试
- `practice` - 练习

### 成长记录状态 (GROWTH_RECORD_STATUS)
- `uploading` - 上传中
- `processing` - 处理中
- `completed` - 已完成
- `failed` - 失败

### 学习日志动作类型 (LEARNING_ACTION_TYPES)
- `practice_correct` - 练习答对
- `practice_wrong` - 练习答错
- `review_correct` - 复习答对
- `review_wrong` - 复习答错
- `mastered` - 掌握
- `forgotten` - 遗忘

### PDF 导入类型 (PDF_IMPORT_TYPES)
- `textbook` - 教材导入
- `homework` - 作业导入

### PDF 导入状态 (PDF_IMPORT_STATUS)
- `pending` - 待处理
- `processing` - 处理中
- `completed` - 已完成
- `failed` - 失败

### 学校类型 (SCHOOL_TYPES)
- `MIDDLE_SCHOOL` - 初中
- `HIGH_SCHOOL` - 高中
- `COMPLETE_SCHOOL` - 完全中学

### 学校级别 (SCHOOL_LEVELS)
- `省级重点`
- `市级重点`
- `区级重点`
- `普通`

### 大学层次 (UNIVERSITY_LEVELS)
- `985`
- `211`
- `双一流`
- `普通本科`
- `高职专科`

### 大学类型 (UNIVERSITY_TYPES)
- `综合`
- `理工`
- `农林`
- `医药`
- `师范`
- `财经`
- `政法`
- `语言`
- `艺术`
- `体育`

### 学历层次 (DEGREE_LEVELS)
- `本科`
- `专科`

### 科目类别 (SUBJECT_CATEGORIES)
- `理科`
- `文科`
- `综合改革`
- `物理类`
- `历史类`

### 录取风险等级 (ADMISSION_RISK_LEVELS)
- `冲刺` - 录取概率较低
- `稳妥` - 录取概率适中
- `保守` - 录取概率较高
- `困难` - 录取概率很低

### 职业测评类型 (ASSESSMENT_TYPES)
- `holland` - 霍兰德兴趣测评
- `mbti` - MBTI 性格测试
- `ability` - 能力倾向测试
- `personality` - 性格测试

### 服务类型 (SERVICE_TYPES)
- `ocr` - OCR 服务
- `ai` - AI 服务
- `storage` - 存储服务
- `email` - 邮件服务
- `payment` - 支付服务

### 练习模式 (PRACTICE_MODES)
- `flashcard` - 卡片模式
- `spelling` - 拼写模式
- `quiz` - 选择题模式

### 通用处理状态 (PROCESS_STATUS)
- `pending` - 待处理
- `processing` - 处理中
- `completed` - 已完成
- `failed` - 失败

---

## 🔐 安全机制

### Row Level Security (RLS)

所有核心表均已启用 RLS 策略，确保：

1. **学生** 只能访问自己的数据
2. **教师** 可以访问其班级学生的数据
3. **管理员** 拥有完全访问权限

### 关键安全策略

- `users` 表：用户只能查看和更新自己的信息
- `vocabulary_progress` 表：学生只能操作自己的进度
- `classes` 表：教师只能管理自己创建的班级
- `growth_records` 表：学生只能查看自己的成长记录

---

## 📝 使用规范

### Service Layer 模式

**强制要求**: 所有数据库访问必须通过 Service 类

```javascript
// ✅ 正确：通过 Service 访问
import VocabularyService from '@/services/vocabularyService';
const progress = await VocabularyService.getUserProgress(userId);

// ❌ 错误：直接调用 Supabase
import { supabase } from '@/services/supabaseClient';
const { data } = await supabase.from('vocabulary_progress').select();
```

### BaseService 使用示例

```javascript
import BaseService from './BaseService';
import { TABLES } from './supabaseClient';

class VocabularyService extends BaseService {
  constructor() {
    super(TABLES.VOCABULARY_PROGRESS);
    if (import.meta.env.DEV) {
      window.vocabularyService = this;
    }
  }

  getUserProgress = async (userId) => {
    const { data, error } = await this.fromTable(TABLES.VOCABULARY_PROGRESS)
      .select('*, words(*)')
      .eq('user_id', userId);

    this.handleError(error, '获取用户进度失败');
    return data;
  }
}

export default new VocabularyService();
```

---

## 🎨 UI 主题配色

基于心理学设计的色彩系统：

```javascript
THEME_COLORS = {
  PAGE_BG: '#13111c',      // 深色背景
  CARD_BG: '#2a253a',      // 卡片背景
  SUCCESS: '#00e676',      // 真实掌握（绿色）
  PRIMARY: '#ff80ab',      // 焦虑触发（粉红）
  WARNING: '#fbbf24',      // 艾宾浩斯阈值（琥珀）
  DANGER: '#ef4444',       // 高风险（红色）
}
```

---

## 📚 相关文档

- [Migration 文件目录](file:///Users/busiji/MyProject/supabase/migrations/)
- [常量定义](file:///Users/busiji/MyProject/src/utils/constants.js)
- [BaseService 文档](file:///Users/busiji/MyProject/src/services/BaseService.js)
- [Supabase 客户端配置](file:///Users/busiji/MyProject/src/services/supabaseClient.js)

---

**生成工具**: Claude Code (Sonnet 4.6)
**文档版本**: v1.0
**最后更新**: 2026-03-11
