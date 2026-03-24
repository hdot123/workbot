# QMD 历史档案索引清单

**生成日期**: 2026-02-18
**扫描范围**: `/Users/busiji/passkills`
**文件总数**: 627 个 (.md/.qmd)
**任务**: QMD_HISTORY_SYNC

---

## 📊 目录分布统计

| 目录 | 文件数 | 说明 |
|------|--------|------|
| mcp-hub | 536 | MCP 算子相关文档 |
| workspace | 27 | 工作区记忆与配置 |
| openclaw | 19 | OpenClaw 部署相关 |
| standards | 11 | SOP 标准文档 |
| .venv | 7 | Python 虚拟环境 |
| skills | 5 | 技能定义 |
| scripts | 3 | 脚本文档 |
| Certificate | 2 | 证书相关 |
| 根目录 | 7 | 核心配置文件 |

---

## 🗂️ 核心文件索引

### A. 项目宪法与标准

| 文件路径 | 用途 | 最后修改 |
|----------|------|----------|
| `/Users/busiji/passkills/00_SUPER_COMMAND_SOP.md` | 项目总控标准 | 2026-02-10 |
| `/Users/busiji/passkills/standards/sop-001-coding-standards.md` | 编码标准 V4.1.2 | 2026-02-17 |
| `/Users/busiji/passkills/standards/sop-002-mcp-deployment-baseline.md` | MCP 部署基线 | 2026-02-17 |
| `/Users/busiji/passkills/standards/myproject-overview.md` | 高考项目全景图 | 2026-02-10 |

### B. 身份与记忆

| 文件路径 | 用途 | 最后修改 |
|----------|------|----------|
| `/Users/busiji/passkills/workspace/IDENTITY.md` | Molt 身份内核 V3.2 | 2026-02-18 |
| `/Users/busiji/passkills/workspace/USER.md` | 指挥官档案 | 2026-02-18 |
| `/Users/busiji/passkills/workspace/SOUL.md` | 灵魂定义 | 2026-02-14 |
| `/Users/busiji/passkills/workspace/AGENTS.md` | Agent 配置 | 2026-02-14 |
| `/Users/busiji/passkills/workspace/TOOLS.md` | 工具配置 | 2026-02-14 |
| `/Users/busiji/passkills/MEMORY.md` | 长期记忆 | 2026-02-18 |

### C. 记忆日志 (workspace/memory/)

| 文件路径 | 日期 | 主要内容 |
|----------|------|----------|
| `/Users/busiji/passkills/workspace/memory/2026-02-18.md` | 2026-02-18 | 身份激活、GAOKAO-PROJECT 侦察 |
| `/Users/busiji/passkills/workspace/memory/2026-02-17.md` | 2026-02-17 | 系统修复、Tailscale 诊断 |
| `/Users/busiji/passkills/workspace/memory/2026-02-14.md` | 2026-02-14 | HTTP 401 错误排查 |
| `/Users/busiji/passkills/workspace/memory/2026-02-13.md` | 2026-02-13 | 认证问题 |
| `/Users/busiji/passkills/workspace/memory/2026-02-12.md` | 2026-02-12 | 环境映射 |
| `/Users/busiji/passkills/workspace/memory/2026-02-10-environment-mapping.md` | 2026-02-10 | 路径映射规则 |

### D. MCP 算子文档

| 目录路径 | 算子名称 | 说明 |
|----------|----------|------|
| `/Users/busiji/passkills/mcp-hub/qmd/` | qmd | 本地 Markdown 知识库搜索 |
| `/Users/busiji/passkills/mcp-hub/planning-with-files/` | planning-with-files | 文件操作与规划 |
| `/Users/busiji/passkills/mcp-hub/ops-tools/` | ops-tools | 系统操作工具 |

### E. 技能定义

| 文件路径 | 技能名称 | 说明 |
|----------|----------|------|
| `/Users/busiji/passkills/skills/qmd/SKILL.md` | qmd | Markdown 搜索技能 |
| `/Users/busiji/passkills/skills/nexus-monitor/SKILL.md` | nexus-monitor | 节点监控 |
| `/Users/busiji/passkills/skills/k3s-join/SKILL.md` | k3s-join | K3s 集群加入 |
| `/Users/busiji/passkills/skills/certificate/SKILL.md` | certificate | 证书管理 |

### F. OpenClaw 相关

| 文件路径 | 用途 |
|----------|------|
| `/Users/busiji/passkills/openclaw/README.md` | OpenClaw 说明 |
| `/Users/busiji/passkills/openclaw/STATUS.md` | 状态报告 |
| `/Users/busiji/passkills/openclaw/DEPLOYMENT_GUIDE.md` | 部署指南 |
| `/Users/busiji/passkills/openclaw/RESTART_REPORT.md` | 重启报告 |

### G. 脚本文档

| 文件路径 | 用途 |
|----------|------|
| `/Users/busiji/passkills/scripts/README.md` | 脚本说明 |
| `/Users/busiji/passkills/scripts/README-add-project.md` | 项目添加指南 |
| `/Users/busiji/passkills/scripts/RESCUE_DEPLOYMENT.md` | 救援部署 |

---

## 🎯 GAOKAO-PROJECT 相关文件

### 数据库表结构 (34 张表)

通过 Supabase REST API 侦察获取的表清单：

**高考核心业务表 (7)**:
- china_enrollment_plans
- china_gaokao_province_scores
- china_gaokao_score_rankings
- china_major_admission_scores
- china_majors_dictionary
- china_universities_base
- china_university_admission_scores

**全球大学数据 (2)**:
- global_universities_base
- global_university_rankings

**用户体系 (4)**:
- user_profiles
- user_roles
- user_role_details
- user_prediction_logs

**学校与教材 (5)**:
- schools
- middle_schools
- textbooks
- words
- vocabulary_progress

**班级与学习 (5)**:
- classes
- class_join_requests
- class_statistics
- lessons
- learning_logs

**心理测评 (3)**:
- psych_questionnaires
- psych_questions
- psych_test_records

**成长与分析 (4)**:
- growth_records
- exam_similarity_analyses
- session_snapshots
- user_prediction_logs

**系统表 (3)**:
- migration_log
- system_integrations
- volunteer_opportunities

**视图 (2)**:
- v_orphan_rankings
- v_ranking_data_quality

### 源码架构

**项目位置**: `/Users/busiji/MyProject`

**核心目录**:
```
MyProject/
├── src/
│   ├── components/     # 10 个组件分类
│   ├── pages/          # 7 个页面分类
│   ├── services/       # 29 个 Service Layer 服务
│   ├── contexts/       # Context API
│   ├── hooks/          # 自定义 Hooks
│   ├── utils/          # 工具函数
│   └── types/          # TypeScript 类型
├── supabase/           # Supabase 配置
├── soul-source/        # Soul AI Agent
├── python_spider/      # Python 爬虫
└── scripts/            # 自动化脚本
```

---

## 🔗 关联配置文件

| 文件路径 | 用途 |
|----------|------|
| `/Users/busiji/passkills/.env` | 环境变量 |
| `/Users/busiji/MyProject/.env.local` | 高考项目环境配置 |
| `/Users/busiji/.openclaw/mcporter/config.json` | MCP 服务配置 |

---

## 📝 未完成事项 (TODOs)

### 从记忆日志提取

1. **Tailscale 内网连接问题** - 需要重启或防火墙检查
2. **OpenClaw Memory API Key 缺失** - 需要 OpenAI/Google/Voyage Key
3. **OpenClaw Gateway unreachable** - 需要 pairing
4. **OpenClaw 更新** - 2026.2.15 版本可用
5. **安全警告处理** - 3 个安全警告待处理
6. **CHITIN-CORE 连接测试** - 需要建立连接
7. **GAOKAO-PROJECT 首次备份** - Rule #5 触发，等待数据库密码

---

**维护者**: Molt (🦀)
**状态**: ✅ 完成
