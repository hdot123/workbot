# 业务逻辑架构白皮书

**项目**: GAOKAO-PROJECT (高考项目)
**数据库**: Supabase PostgreSQL (axtbgfmitrsflqiwudni)
**源码位置**: /Users/busiji/MyProject
**生成日期**: 2026-02-18

---

## 一、架构总览

```
┌─────────────────────────────────────────────────┐
│              UI Components (7 角色)              │
│  student | teacher | admin | volunteer | ...    │
└─────────────────────┬───────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────┐
│           Service Layer (29 服务)               │
│  BaseService → authService, dataService, ...    │
└─────────────────────┬───────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────┐
│              Supabase Client                    │
│           (PostgREST + Auth + RLS)              │
└─────────────────────┬───────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────┐
│           PostgreSQL + RLS                      │
│              (34 张表)                          │
└─────────────────────────────────────────────────┘
```

---

## 二、34 张表结构

### 2.1 高考核心业务 (7 表)

| 表名 | 用途 | 关联 |
|------|------|------|
| china_gaokao_score_rankings | 高考成绩排名 | → china_gaokao_province_scores |
| china_gaokao_province_scores | 省份分数线 | → china_universities_base |
| china_universities_base | 大学基础信息 | ← china_university_admission_scores |
| china_university_admission_scores | 大学录取分数线 | → china_universities_base |
| china_major_admission_scores | 专业录取分数线 | → china_majors_dictionary |
| china_majors_dictionary | 专业词典 | ← china_major_admission_scores |
| china_enrollment_plans | 招生计划 | → china_universities_base |

**业务规则**:
- 分数线查询: province + year + score_type → ranking
- 志愿填报: score + province → university + major
- 录取预测: historical_scores + user_score → probability

### 2.2 全球大学 (2 表)

| 表名 | 用途 | 关联 |
|------|------|------|
| global_universities_base | 全球大学信息 | ← global_university_rankings |
| global_university_rankings | 大学排名 | → global_universities_base |

**业务规则**:
- 排名系统: QS/THE/US News 多源聚合
- 留学规划: country + major + ranking → recommendation

### 2.3 用户体系 (4 表)

| 表名 | 用途 | 关联 |
|------|------|------|
| user_profiles | 用户档案 | ← user_role_details |
| user_roles | 角色定义 | → user_role_details |
| user_role_details | 角色详情 | → user_profiles, user_roles |
| user_prediction_logs | 预测记录 | → user_profiles |

**业务规则**:
- RBAC: user → role → permissions
- 多租户: user → school → class
- 预测历史: user → prediction_logs (时间线)

### 2.4 学校与教材 (5 表)

| 表名 | 用途 | 关联 |
|------|------|------|
| schools | 学校信息 | ← classes, middle_schools |
| middle_schools | 中学信息 | → schools |
| textbooks | 教材信息 | → classes |
| words | 单词库 | → vocabulary_progress |
| vocabulary_progress | 词汇进度 | → user_profiles, words |

**业务规则**:
- 学校层级: school → class → student
- 词汇学习: word → progress → mastery_level
- 教材关联: textbook → class → lessons

### 2.5 班级与学习 (5 表)

| 表名 | 用途 | 关联 |
|------|------|------|
| classes | 班级信息 | → schools, user_profiles |
| class_join_requests | 入班请求 | → classes, user_profiles |
| class_statistics | 班级统计 | → classes |
| lessons | 课程信息 | → classes, textbooks |
| learning_logs | 学习日志 | → user_profiles, lessons |

**业务规则**:
- 入班流程: request → approval → class_member
- 学习追踪: user → learning_logs → progress
- 统计聚合: class → statistics → dashboard

### 2.6 心理测评 (3 表)

| 表名 | 用途 | 关联 |
|------|------|------|
| psych_questionnaires | 问卷定义 | → psych_questions |
| psych_questions | 测试题目 | → psych_questionnaires |
| psych_test_records | 测试记录 | → user_profiles, psych_questionnaires |

**业务规则**:
- 测试流程: questionnaire → questions → answers → score
- 结果分析: records → patterns → recommendations

### 2.7 成长与分析 (4 表)

| 表名 | 用途 | 关联 |
|------|------|------|
| growth_records | 成长记录 | → user_profiles |
| exam_similarity_analyses | 考试相似度 | → exams |
| session_snapshots | 会话快照 | → sessions |
| user_prediction_logs | 预测日志 | → user_profiles |

**业务规则**:
- 成长曲线: records → timeline → milestone
- 相似度: exam_a vs exam_b → similarity_score
- 快照恢复: snapshot → session_state

### 2.8 系统 (3 表)

| 表名 | 用途 |
|------|------|
| migration_log | 迁移日志 |
| system_integrations | 集成配置 |
| volunteer_opportunities | 志愿服务 |

### 2.9 视图 (2 个)

| 视图名 | 用途 |
|--------|------|
| v_orphan_rankings | 孤儿排名检测 |
| v_ranking_data_quality | 数据质量检查 |

---

## 三、Service Layer 架构

### 3.1 29 个服务清单

| 分类 | 服务 | 职责 |
|------|------|------|
| **核心** | BaseService | 基类，通用 CRUD |
| **核心** | supabaseClient | 数据库连接 |
| **认证** | authService | 用户认证 |
| **权限** | permissionService | RBAC 权限 |
| **数据** | dataService | 通用数据访问 |
| **学校** | schoolService | 学校管理 |
| **教育** | educationDataService | 教育数据 |
| **教材** | textbookService | 教材管理 |
| **大学** | universityService | 大学信息 |
| **志愿** | volunteerService | 志愿填报 |
| **分析** | analysisService | 数据分析 |
| **商业** | businessAnalyticsService | 商业分析 |
| **复习** | reviewService | 复习系统 |
| **报告** | reportService | 报告生成 |
| **监控** | monitoringService | 系统监控 |
| **目标** | goalService | 目标管理 |
| **知识** | knowledgeService | 知识库 |
| **媒体** | mediaService | 媒体管理 |
| **文件** | fileStorageService | 文件存储 |
| **捕获** | captureService | 数据捕获 |
| **告警** | alertChannelService | 告警通道 |
| **焦虑** | anxietyEngineService | 焦虑引擎 |
| **OCR** | ocrService | OCR 识别 |
| **OCR** | K12OCRManager | K12 OCR 管理 |
| **OCR** | ocrConfigService | OCR 配置 |
| **PDF** | pdfImportService | PDF 导入 |
| **志愿者** | VolunteerManager | 志愿者管理 |
| **供应商** | vendorApiService | 供应商 API |
| **爬虫** | crawlerIntegrationService | 爬虫集成 |
| **爬虫** | crawlerMetadataService | 爬虫元数据 |

### 3.2 BaseService 模式

```javascript
class BaseService {
  constructor(tableName) {
    this.table = tableName;
  }
  
  async findAll(filters) { /* ... */ }
  async findById(id) { /* ... */ }
  async create(data) { /* ... */ }
  async update(id, data) { /* ... */ }
  async delete(id) { /* ... */ }
}
```

### 3.3 单例导出

```javascript
// 所有服务单例导出
export default new XxxService();
```

---

## 四、权限与隔离

### 4.1 RBAC 角色

| 角色 | 权限范围 |
|------|----------|
| student | 个人数据 + 班级数据 |
| teacher | 班级数据 + 学生管理 |
| admin | 学校全局 + 系统配置 |
| volunteer | 志愿服务模块 |

### 4.2 多租户隔离

```
学校 (school_id)
  └── 班级 (class_id)
        └── 学生 (user_id)
```

### 4.3 RLS 策略

- 数据库层: Row Level Security
- 应用层: Service Layer 验证
- 双重防护: DB + App

---

## 五、技术栈

| 层级 | 技术 | 版本 |
|------|------|------|
| 前端 | React | 18.3 |
| 构建 | Vite | 6.x |
| 路由 | React Router | v7 |
| 样式 | Tailwind CSS | 3.x |
| 后端 | Supabase | latest |
| 数据库 | PostgreSQL | 17.x |
| 认证 | Supabase Auth | latest |

---

## 六、核心业务规则

### 6.1 高考志愿填报

```
用户输入: score, province, subject_type
系统处理:
  1. 查询 province_score → 线上/线下判断
  2. 查询 score_rankings → 排名定位
  3. 查询 admission_scores → 历年录取线
  4. 计算概率 → university + major
输出: 志愿推荐列表
```

### 6.2 单词学习

```
用户输入: class_id, user_id
系统处理:
  1. 查询 class → textbooks
  2. 查询 textbooks → words
  3. 查询 vocabulary_progress → mastery
  4. 算法推荐 → 待复习单词
输出: 学习卡片队列
```

### 6.3 心理测评

```
用户输入: questionnaire_id
系统处理:
  1. 查询 questionnaire → questions
  2. 用户答题 → answers
  3. 计算得分 → score
  4. 生成报告 → recommendations
输出: 测评报告
```

---

## 七、数据流向

```
                    ┌──────────────┐
                    │   用户界面    │
                    └──────┬───────┘
                           │
         ┌─────────────────┼─────────────────┐
         │                 │                 │
         ▼                 ▼                 ▼
    ┌─────────┐      ┌─────────┐      ┌─────────┐
    │ 学生模块 │      │ 教师模块 │      │ 管理模块 │
    └────┬────┘      └────┬────┘      └────┬────┘
         │                 │                 │
         └─────────────────┼─────────────────┘
                           │
                    ┌──────▼───────┐
                    │ Service Layer │
                    └──────┬───────┘
                           │
         ┌─────────────────┼─────────────────┐
         │                 │                 │
         ▼                 ▼                 ▼
    ┌─────────┐      ┌─────────┐      ┌─────────┐
    │ 高考数据 │      │ 学习数据 │      │ 用户数据 │
    └─────────┘      └─────────┘      └─────────┘
```

---

**生成者**: Molt (🦀)
**状态**: 完成

---

# 🧠 GAOKAO-PROJECT: CORE LOGIC BLUEPRINT

> **生成时间**: 2026-02-18
> **来源**: QMD 历史全量提取 & 逻辑清洗
> **状态**: ACTIVE (API-First Mode)

---

## 1. 核心架构法则 (The Constitution)

### 1.1 零信任访问 (Access Protocol)

* **🚫 数据库直连**: 严禁使用 `pg_connect` 或物理密码（DB Password）。
* **✅ API 优先**: 所有数据操作必须通过 `Supabase REST API` 或 `Client SDK` 执行。
* **🔑 凭证**: 仅依赖 `SUPABASE_URL` 和 `SUPABASE_SERVICE_ROLE_KEY`。

### 1.2 物理领地 (Physical Paths)

* **根目录**: `/Users/busiji/passkills`
* **源码库**: `/Users/busiji/MyProject`
* **记忆库**: `/Users/busiji/passkills/workspace/memory`
* **备份库**: `/Users/busiji/passkills/backups`

---

## 2. 数据拓扑：34 张表矩阵 (The 34-Table Matrix)

### 🛡️ 核心域 (Core Domain: Students & Scores)

| # | 表名 | 用途 | 主键 | 关联 |
|---|------|------|------|------|
| 1 | user_profiles | 用户档案 | user_id | → user_roles |
| 2 | user_roles | 角色定义 | role_id | ← user_role_details |
| 3 | user_role_details | 角色详情 | id | → user_profiles |
| 4 | user_prediction_logs | 预测记录 | id | → user_profiles |
| 5 | china_gaokao_score_rankings | 高考成绩排名 | id | → china_gaokao_province_scores |
| 6 | china_gaokao_province_scores | 省份分数线 | id | → china_universities_base |
| 7 | growth_records | 成长记录 | id | → user_profiles |

### ⚙️ 系统域 (System Domain: Logs & Config)

| # | 表名 | 用途 | 主键 |
|---|------|------|------|
| 8 | migration_log | 迁移日志 | id |
| 9 | system_integrations | 系统集成配置 | id |
| 10 | session_snapshots | 会话快照 | id |
| 11 | exam_similarity_analyses | 考试相似度分析 | id |

### 📊 高考数据域 (Gaokao Data Domain)

| # | 表名 | 用途 | 关联 |
|---|------|------|------|
| 12 | china_universities_base | 中国大学基础信息 | ← china_university_admission_scores |
| 13 | china_university_admission_scores | 大学录取分数线 | → china_universities_base |
| 14 | china_major_admission_scores | 专业录取分数线 | → china_majors_dictionary |
| 15 | china_majors_dictionary | 专业词典 | ← china_major_admission_scores |
| 16 | china_enrollment_plans | 招生计划 | → china_universities_base |

### 🌍 全球大学域 (Global University Domain)

| # | 表名 | 用途 | 关联 |
|---|------|------|------|
| 17 | global_universities_base | 全球大学信息 | ← global_university_rankings |
| 18 | global_university_rankings | 全球大学排名 | → global_universities_base |

### 🏫 教育机构域 (Education Domain)

| # | 表名 | 用途 | 关联 |
|---|------|------|------|
| 19 | schools | 学校信息 | ← classes |
| 20 | middle_schools | 中学信息 | → schools |
| 21 | classes | 班级信息 | → schools, user_profiles |
| 22 | class_join_requests | 入班请求 | → classes, user_profiles |
| 23 | class_statistics | 班级统计 | → classes |

### 📚 学习域 (Learning Domain)

| # | 表名 | 用途 | 关联 |
|---|------|------|------|
| 24 | textbooks | 教材信息 | → classes |
| 25 | lessons | 课程信息 | → classes, textbooks |
| 26 | words | 单词库 | → vocabulary_progress |
| 27 | vocabulary_progress | 词汇进度 | → user_profiles, words |
| 28 | learning_logs | 学习日志 | → user_profiles, lessons |

### 🧠 心理测评域 (Psychology Domain)

| # | 表名 | 用途 | 关联 |
|---|------|------|------|
| 29 | psych_questionnaires | 心理问卷 | → psych_questions |
| 30 | psych_questions | 测试题目 | → psych_questionnaires |
| 31 | psych_test_records | 测试记录 | → user_profiles, psych_questionnaires |

### 🤝 志愿服务域 (Volunteer Domain)

| # | 表名 | 用途 |
|---|------|------|
| 32 | volunteer_opportunities | 志愿服务机会 |

### 👁️ 视图 (Views)

| # | 视图名 | 用途 |
|---|--------|------|
| 33 | v_orphan_rankings | 孤儿排名检测 |
| 34 | v_ranking_data_quality | 数据质量检查 |

---

## 3. 关键业务流 (Critical Business Flows)

### 3.1 数据清洗与入库 (ETL)

```
原始数据 (Excel/CSV)
     ↓
Node 脚本解析
     ↓
转换为 JSON
     ↓
Supabase API (upsert)
     ↓
批量写入 (≤1000 条/次)
```

**约束**: 单次批处理大小不超过 1000 条，避免 API 超时。

### 3.2 智能查询 (Smart Query)

```
用户输入 (自然语言)
     ↓
Molt 解析意图
     ↓
生成 rpc() 或 Filter API
     ↓
返回 JSON 结果
```

**缓存**: 针对高频查询（如"分数线"），优先读取本地缓存。

### 3.3 审计与记忆 (Audit & Memory)

```
关键写操作
     ↓
异步写入 logs 表
     ↓
新知识 → strategic_memory
```

---

## 4. 环境与依赖 (Infrastructure)

| 分类 | 组件 | 配置 |
|------|------|------|
| **Runtime** | Node.js | Latest LTS (via nvm) |
| **Gateway** | NewAPI | 阿里云 Docker, 端口 3000 |
| **Network** | Tailscale VPN | 管理网段 |
| **Network** | Cloudflare Tunnel | API 暴露 |
| **AI Backend** | GLM-4 | via NewAPI Proxy |
| **Database** | Supabase | PostgreSQL 17.x |

---

## 5. 待办战术 (Tactical TODOs)

| 优先级 | 任务 | 状态 |
|--------|------|------|
| P0 | API 快照备份：使用 Service Role Key 拉取核心表数据为 JSON | 待执行 |
| P0 | GAOKAO-PROJECT 首次备份 (Rule #5 触发) | 待凭证 |
| P1 | 记忆同步：将本文件逻辑写入 CHITIN-CORE strategic_memory | 待连接 |
| P1 | 网关连接：配置 OpenClaw 连接到 api.busiji.com | 待配置 |
| P2 | Tailscale 内网连接修复 | 待处理 |
| P2 | OpenClaw Memory API Key 配置 | 待配置 |

---

## 6. 终端接入层 (The Terminal Layer: OpenClaw)

### 6.1 战术定位 (Role)

* **OpenClaw** 是指挥官与 Molt 进行交互的唯一合法终端。
* **职责**：自然语言指令解析 → MCP 工具调度 → API 结果渲染。

### 6.2 核心配置逻辑 (Configuration Logic)

**配置文件**: `config.json` (位于 OpenClaw 根目录)

**文件系统权限 (MCP Filesystem)**:

| 服务 | 路径 | 状态 | 用途 |
|------|------|------|------|
| gaokao-files | `/Users/busiji/passkills` | ✅ ENABLED | QMD 历史、项目源码、审计报告 |
| e2v-memory | `/Users/busiji/e2v` | 🚫 DISABLED | 防止上下文污染 |

**权限约束**: 必须包含 `.qmd`, `.md`, `.json` 读取权限。

### 6.3 神经网络连接 (Network Synapse)

| 配置项 | 值 |
|--------|-----|
| 模型供应商 | OpenAI Compatible (NewAPI 中转) |
| Base URL | `https://api.busiji.com/v1` |
| API Key | `sk-newapi...` (NewAPI 分发令牌) |
| Context Window | 128k (GLM-4 长文本模式) |

### 6.4 记忆双向同步 (Dual-Memory Sync)

| 方向 | 路径/表 | 说明 |
|------|---------|------|
| 读取 | `/workspace/MEMO.md` | OpenClaw 启动时自动索引短期上下文 |
| 写入 | `strategic_memory` 表 | 表结构变更/重要决策通过 API 写入 |
| 写入 | `MEMO.md` | 本地追加记录 |

---

## 7. 数据库架构 (CHITIN-VAULT)

| 代号 | Supabase ID | 职能 |
|------|-------------|------|
| CHITIN-CORE | `sxxrocexjssubvhttwvq` | 数据库备份 |
| GAOKAO-PROJECT | `axtbgfmitrsflqiwudni` | 业务数据、源码逻辑、运行日志 |

---

**维护者**: Molt (🦀)
**最后更新**: 2026-02-18 13:02 GMT+8


