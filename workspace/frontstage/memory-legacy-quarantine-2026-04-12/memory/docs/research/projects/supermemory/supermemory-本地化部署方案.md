# Supermemory Self-Hosted 本地化部署方案

> 用途：AEdu 项目记忆层私有化部署
> 隐私保护：学生数据完全存储在自有基础设施
> 部署目标：Cloudflare Workers + 自有 PostgreSQL

---

## 一、为什么选择 Self-Hosted（隐私保护视角）

### 1.1 SaaS vs Self-Hosted 对比

| 维度 | SaaS API | Self-Hosted |
|------|---------|-------------|
| **数据存储位置** | supermemory 云端 | 自有 PostgreSQL |
| **数据出境风险** | 存在 | 无（完全可控） |
| **合规性** | 依赖供应商 | 自主控制 |
| **数据删除** | 依赖供应商配合 | 随时自主删除 |
| **访问日志** | 供应商掌握 | 自有日志系统 |
| **成本** | 按用量付费 | 固定基础设施成本 |

### 1.2 教育数据合规要求

根据《个人信息保护法》和教育数据管理相关规定：
- 学生个人信息属于**敏感个人信息**
- 原则上应当**本地存储**
- 确需向境外提供的，应当通过**安全评估**

**Self-Hosted 优势**：
- ✅ 数据存储在自有 VPC 内
- ✅ 不经过第三方 SaaS
- ✅ 符合教育数据合规要求

---

## 二、部署架构

```
┌─────────────────────────────────────────────────────────────┐
│                    你的基础设施                              │
│                                                             │
│  ┌─────────────┐     ┌─────────────┐     ┌─────────────┐   │
│  │  Cloudflare │     │  PostgreSQL │     │   你的应用   │   │
│  │   Workers   │────▶│  (pgvector) │◀────│   (AEdu)    │   │
│  │  (记忆引擎)  │     │  (数据存储)  │     │  (StudentTwin)│  │
│  └─────────────┘     └─────────────┘     └─────────────┘   │
│         │                    │                              │
│         └────────────────────┘                              │
│                    内部网络通信                              │
└─────────────────────────────────────────────────────────────┘
         │
         │ 仅 outbound 到 LLM Provider
         ▼
    ┌─────────────┐
    │ OpenAI/     │
    │ Anthropic   │  ← API 调用，不传输用户数据
    └─────────────┘
```

**数据流向**：
1. 学生学习数据 → 你的 AEdu 应用 → 自有 PostgreSQL
2. 记忆提取/检索 → Cloudflare Workers → 自有 PostgreSQL
3. LLM 调用 → 仅用于记忆提取，学生数据不落地

---

## 三、前置条件

### 3.1 必需资源

| 资源 | 用途 | 获取方式 |
|------|------|---------|
| Cloudflare 账号 | 部署 Workers | https://dash.cloudflare.com |
| PostgreSQL | 存储记忆数据 | 自建或云服务商 |
| LLM API Key | 记忆提取 | OpenAI/Anthropic 等 |

### 3.2 技术门槛

- **难度**：中等
- **时间**：2-4 小时（首次部署）
- **维护**：低（Cloudflare 托管，无需运维服务器）

---

## 四、部署步骤

### 4.1 创建 Cloudflare 账号

1. 访问 https://dash.cloudflare.com/sign-up
2. 注册账号
3. 获取 **Account ID**（URL 中的字符串）

### 4.2 创建 API Token

1. 访问 https://dash.cloudflare.com/?to=/:account/api-tokens
2. 点击 **"Create Token"** → 选择 **"Custom token"**
3. 配置权限：
   - `Account:AI Gateway:Edit`
   - `Account:Hyperdrive:Edit`
   - `Account:Workers KV Storage:Edit`
   - `Account:Workers R2 Storage:Edit`
4. 创建并保存 Token（只显示一次）

### 4.3 准备 PostgreSQL

**要求**：
- 支持 **pgvector 扩展**
- 支持 SSL 连接
- 可从 Cloudflare Workers 访问

**推荐方案**：
| 服务商 | 价格 | 说明 |
|--------|------|------|
| **Neon** | 免费 tier | Serverless PG，内置 pgvector |
| **Supabase** | 免费 tier | 托管 PG，内置 pgvector |
| **AWS RDS** | 按量 | 需手动安装 pgvector |

**Neon 快速创建**：
```bash
# 访问 https://neon.tech 创建
# 获取连接字符串格式：
postgresql://user:password@ep-xxx.ap-southeast-1.aws.neon.tech/dbname?sslmode=require
```

### 4.4 获取 LLM API Key

**最低要求**：OpenAI API Key

1. 访问 https://platform.openai.com
2. 创建账号 → API Keys → Create new secret key
3. 添加计费信息

**可选**：Anthropic、Gemini、Groq（用于多模型路由）

---

## 五、环境变量配置

创建 `.env` 文件：

```bash
# === 必需配置 ===

# 部署环境
NODE_ENV=production

# supermemory 团队分配的 Host ID（需申请企业版）
NEXT_PUBLIC_HOST_ID=your_host_id

# 认证密钥（运行 openssl rand -base64 32 生成）
BETTER_AUTH_SECRET="your_random_secret_here"

# 你的 API 域名
BETTER_AUTH_URL=https://api.yourdomain.com

# PostgreSQL 连接字符串
DATABASE_URL=postgresql://user:pass@host:5432/dbname?sslmode=require

# Cloudflare 凭证
CLOUDFLARE_ACCOUNT_ID=your_account_id
CLOUDFLARE_API_TOKEN=your_api_token

# LLM Provider
OPENAI_API_KEY=sk-xxx

# 邮件服务（可选，用于发送通知）
RESEND_API_KEY=re_xxx

# === 可选配置 ===

# 其他 LLM Provider
ANTHROPIC_API_KEY=
GEMINI_API_KEY=
GROQ_API_KEY=

# OAuth 登录（可选）
AUTH_GITHUB_ID=
AUTH_GITHUB_SECRET=
AUTH_GOOGLE_ID=
AUTH_GOOGLE_SECRET=

# Connectors（可选）
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
MICROSOFT_CLIENT_ID=
MICROSOFT_CLIENT_SECRET=
NOTION_CLIENT_ID=
NOTION_CLIENT_SECRET=
```

---

## 六、部署脚本

**前提**：需要联系 supermemory 团队获取企业部署包

```bash
# 1. 解压部署包
unzip supermemory-enterprise-deployment.zip
cd supermemory-deployment

# 2. 复制环境变量模板
cp packages/alchemy/env.example .env

# 3. 编辑 .env 文件
$EDITOR .env

# 4. 部署到 Cloudflare
bun ./deploy.ts
```

---

## 七、隐私保护措施

### 7.1 数据加密

| 环节 | 措施 |
|------|------|
| 传输中 | TLS 1.3（Cloudflare 强制 HTTPS） |
| 存储中 | PostgreSQL SSL + 磁盘加密 |
| 密钥管理 | 环境变量隔离，不入库 |

### 7.2 访问控制

| 层级 | 控制 |
|------|------|
| 网络层 | Cloudflare WAF + IP 白名单 |
| 应用层 | JWT 认证 + containerTag 隔离 |
| 数据层 | PG 行级权限（RLS） |

### 7.3 审计日志

```sql
-- 建议：在 PostgreSQL 中开启审计日志
CREATE EXTENSION IF NOT EXISTS pgaudit;

-- 记录所有对记忆数据的访问
ALTER SYSTEM SET pgaudit.log = 'READ,WRITE';
ALTER SYSTEM SET pgaudit.log_relation = 'on';
```

### 7.4 数据删除

```typescript
// 用户请求删除时的处理
await client.documents.delete(documentId, {
  deleteAssociatedMemories: true  // 级联删除
});

// 物理删除（PG 层面）
DELETE FROM memories WHERE container_tags @> ARRAY['student_123'];
```

---

## 八、成本估算

### 8.1 Cloudflare Workers

| 项目 | 免费额度 | 付费后 |
|------|---------|--------|
| 请求数 | 100,000/天 | $0.15/1M 请求 |
| CPU 时间 | 10ms/请求 | 按量计费 |
| KV 存储 | 1GB | $0.5/GB/月 |

**估算**：1 万学生，每人每天 10 次记忆操作
- 日请求：10 万（免费额度内）
- 月成本：$0

### 8.2 PostgreSQL

| 服务商 | 免费额度 | 付费后 |
|--------|---------|--------|
| Neon | 0.5GB 存储 | $0.000000494/GB-秒 |
| Supabase | 500MB 存储 | $25/月（Pro） |

**估算**：1 万学生，每学生 100 条记忆，每条 1KB
- 总存储：1GB
- 月成本：$0-25

### 8.3 LLM API

| Provider | 价格（输入） | 价格（输出） |
|----------|-------------|-------------|
| OpenAI GPT-4o | $5/1M tokens | $15/1M tokens |
| Anthropic Claude Haiku | $0.25/1M tokens | $1.25/1M tokens |

**估算**：每学生每天 1 次记忆提取，每次 500 tokens
- 月请求：30 万
- 月 tokens：1.5 亿
- 月成本（Haiku）：约 $37.5

### 8.4 总成本

| 规模 | 月成本估算 |
|------|-----------|
| 试点（100 学生） | $5-10 |
| 小规模（1 万学生） | $50-100 |
| 大规模（10 万学生） | $500-1000 |

---

## 九、下一步动作

| 序号 | 动作 | 状态 |
|------|------|------|
| 1 | 联系 supermemory 团队获取企业部署包 | ⬜ 待办 |
| 2 | 创建 Cloudflare 账号 + API Token | ⬜ 待办 |
| 3 | 创建 Neon/Supabase PostgreSQL | ⬜ 待办 |
| 4 | 获取 OpenAI API Key | ✅ 已有 |
| 5 | 配置环境变量 | ⬜ 待办 |
| 6 | 部署到 Cloudflare | ⬜ 待办 |
| 7 | 测试记忆存取 | ⬜ 待办 |
| 8 | 集成到 AEdu | ⬜ 待办 |

---

## 十、联系 supermemory 企业版

**邮箱**：需从官网获取
**网站**：https://supermemory.ai
**控制台**：https://console.supermemory.ai

**咨询内容**：
1. 企业 Self-Hosted 方案价格
2. 获取部署包（含 Workers 代码）
3. 获取 `NEXT_PUBLIC_HOST_ID`
4. SLA 和技术支持

---

**维护人**：AEdu 技术负责人
**版本**：V1.0
**最后更新**：2026-03-23
**隐私保护级别**：高（学生数据本地存储）
