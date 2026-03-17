# MEMO.md - 高考项目业务逻辑演进摘要

**生成日期**: 2026-02-18
**任务**: QMD_HISTORY_SYNC 阶段 2
**数据来源**: passkills 历史档案 + Supabase 侦察

---

## 📋 项目概况

**项目名称**: MyProject (高考项目)
**项目 ID**: MP-001
**源码位置**: `/Users/busiji/MyProject`
**数据库**: GAOKAO-PROJECT (`axtbgfmitrsflqiwudni`)

---

## 🏗️ 架构演进

### V1.0 - 基础架构
- React + Supabase 基础集成
- 基本的学生词语学习功能

### V2.0 - 多角色系统
- 引入 RBAC 权限控制
- 学生/教师/管理员三种角色

### V3.0 - 多租户隔离
- 学校 → 班级两级数据隔离
- RLS (Row Level Security) 数据库层权限

### V4.0 - Service Layer
- 29 个服务统一数据访问
- BaseService 基类继承
- 单例模式导出

### V5.0 - 当前版本
- 高考志愿填报功能
- 心理测评系统
- 成长记录追踪
- OCR 成绩识别

---

## 📊 34 张表业务逻辑

### 核心业务域

#### 1. 高考数据 (7 张表)
| 表名 | 业务逻辑 |
|------|----------|
| china_gaokao_score_rankings | 高考成绩排名数据，用于省份排名查询 |
| china_gaokao_province_scores | 各省份高考分数线（一本/二本/专科） |
| china_universities_base | 中国大学基础信息库 |
| china_university_admission_scores | 大学历年录取分数线 |
| china_major_admission_scores | 专业录取分数线 |
| china_majors_dictionary | 专业词典，专业代码与名称映射 |
| china_enrollment_plans | 招生计划数据 |

**业务场景**: 志愿填报、录取预测、分数线查询

#### 2. 全球大学 (2 张表)
| 表名 | 业务逻辑 |
|------|----------|
| global_universities_base | 全球大学基础信息 |
| global_university_rankings | 全球大学排名（QS/THE/US News） |

**业务场景**: 留学规划、大学对比

#### 3. 用户体系 (4 张表)
| 表名 | 业务逻辑 |
|------|----------|
| user_profiles | 用户档案，包含学生/教师信息 |
| user_roles | 用户角色定义 |
| user_role_details | 角色详情与权限 |
| user_prediction_logs | 用户预测记录，用于志愿填报历史 |

**业务场景**: 认证授权、角色管理

#### 4. 学校与教材 (5 张表)
| 表名 | 业务逻辑 |
|------|----------|
| schools | 学校信息 |
| middle_schools | 中学信息 |
| textbooks | 教材信息 |
| words | 单词库 |
| vocabulary_progress | 词汇学习进度 |

**业务场景**: 学校管理、单词学习

#### 5. 班级与学习 (5 张表)
| 表名 | 业务逻辑 |
|------|----------|
| classes | 班级信息 |
| class_join_requests | 班级加入请求 |
| class_statistics | 班级统计数据 |
| lessons | 课程信息 |
| learning_logs | 学习日志 |

**业务场景**: 班级管理、学习追踪

#### 6. 心理测评 (3 张表)
| 表名 | 业务逻辑 |
|------|----------|
| psych_questionnaires | 心理问卷定义 |
| psych_questions | 测试题目 |
| psych_test_records | 测试记录与结果 |

**业务场景**: 心理健康评估

#### 7. 成长与分析 (4 张表)
| 表名 | 业务逻辑 |
|------|----------|
| growth_records | 成长记录，追踪学生能力成长轨迹 |
| exam_similarity_analyses | 考试相似度分析 |
| session_snapshots | 会话快照 |
| user_prediction_logs | 预测日志 |

**业务场景**: 成长追踪、数据分析

#### 8. 系统 (3 张表)
| 表名 | 业务逻辑 |
|------|----------|
| migration_log | 迁移日志 |
| system_integrations | 系统集成配置 |
| volunteer_opportunities | 志愿服务机会 |

**业务场景**: 系统运维

---

## 🔧 Service Layer 架构

### 29 个服务清单

| 服务名称 | 职责 |
|----------|------|
| BaseService | 基类，提供通用 CRUD 方法 |
| supabaseClient | Supabase 客户端封装 |
| authService | 认证服务 |
| schoolService | 学校服务 |
| dataService | 数据服务 |
| permissionService | 权限服务 |
| ocrService | OCR 服务 |
| pdfImportService | PDF 导入 |
| volunteerService | 志愿者服务 |
| analysisService | 分析服务 |
| reviewService | 复习服务 |
| reportService | 报告服务 |
| monitoringService | 监控服务 |
| goalService | 目标服务 |
| knowledgeService | 知识服务 |
| educationDataService | 教育数据 |
| textbookService | 教材服务 |
| universityService | 大学服务 |
| mediaService | 媒体服务 |
| fileStorageService | 文件存储 |
| captureService | 捕获服务 |
| alertChannelService | 告警通道 |
| anxietyEngineService | 焦虑引擎 |
| businessAnalyticsService | 商业分析 |
| K12OCRManager | K12 OCR 管理 |
| VolunteerManager | 志愿者管理 |
| ocrConfigService | OCR 配置 |
| vendorApiService | 供应商 API |
| crawlerIntegrationService | 爬虫集成 |
| crawlerMetadataService | 爬虫元数据 |

---

## 🌐 环境配置习惯

### 本地开发环境
- 主机 IP: 192.168.88.235
- Dashboard: 18501
- Browserless: 13000
- PostgreSQL: 15432
- Redis: 16379

### Supabase 配置
- CHITIN-CORE: `sxxrocexjssubvhttwvq` (长期记忆)
- GAOKAO-PROJECT: `axtbgfmitrsflqiwudni` (生产战区)
- 区域: ap-southeast-1

### 路径规范
- Mac 宿主机路径: `/Users/busiji/...`
- 容器环境路径: `/root/...`
- 自动映射规则

---

## 🚀 技术栈

| 分类 | 技术 | 版本 |
|------|------|------|
| 前端 | React | 18.3 |
| 构建 | Vite | 6.x |
| 路由 | React Router | v7 |
| 样式 | Tailwind CSS | 3.x |
| 后端 | Supabase | latest |
| 数据库 | PostgreSQL | 17.x |

---

## 📝 待办事项

1. **Tailscale 内网连接修复**
2. **OpenClaw Memory API Key 配置**
3. **CHITIN-CORE 连接测试**
4. **GAOKAO-PROJECT 首次备份执行**

---

**维护者**: Molt (🦀)
**状态**: ✅ 完成
