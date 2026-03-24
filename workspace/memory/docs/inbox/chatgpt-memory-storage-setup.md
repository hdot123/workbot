# ChatGPT 会话向量记忆存储 - 安装指南

> 文档编号：WORKBOT-DOC-001
> 创建日期：2026-03-22
> 维护人：工作空间管理员

---

## 1. 概述

本文档描述如何在 Supabase 中部署 ChatGPT 会话存储和向量记忆系统，用于：
- 存储 ChatGPT Web 的历史会话
- 向量化消息内容，支持语义检索
- 实现 AI 长期记忆功能

---

## 2. 前置条件

### 2.1 环境变量配置

在 `~/.zshrc` 中配置以下变量：

```bash
# ChatGPT Web 会话存储 - Supabase 配置
export SUPABASE_GPT_URL="https://yxhgzdflkuumjswpazcm.supabase.co"
export SUPABASE_GPT_KEY="sb_publishable_xxx"          # Publishable Key (anon)
export SUPABASE_GPT_SERVICE_KEY="sb_secret_xxx"       # Service Role Key
```

**刷新配置**：
```bash
source ~/.zshrc
```

**验证**：
```bash
echo $SUPABASE_GPT_URL
echo $SUPABASE_GPT_KEY
echo $SUPABASE_GPT_SERVICE_KEY
```

---

## 3. 获取 Supabase Keys

### 3.1 账户信息

| 项目 | 值 |
|------|------|
| **账户别名** | `gpt-memory` |
| **登录邮箱** | (待补充) |
| **项目 URL** | `https://yxhgzdflkuumjswpazcm.supabase.co` |

### 3.2 获取 API Keys

1. 左侧菜单 → **Settings** → **API**
2. 复制以下两个 Key：
   - **Publishable key** → `SUPABASE_GPT_KEY`
   - **service_role key** → `SUPABASE_GPT_SERVICE_KEY` ⚠️ 保密

---

## 4. 数据库表结构

### 4.1 表概览

| 表名 | 用途 |
|------|------|
| `chatgpt_sessions` | 会话元数据（会话 ID、标题、时间） |
| `chatgpt_messages` | 消息内容（角色、内容、向量） |
| `chatgpt_memories` | 向量化记忆（摘要、关键词、标签） |

### 4.2 字段说明

#### chatgpt_sessions

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | uuid | 主键 |
| `session_id` | text | ChatGPT Web 会话编号 (1-10) |
| `title` | text | 会话标题 |
| `created_at` | timestamptz | 创建时间 |
| `updated_at` | timestamptz | 更新时间 |

#### chatgpt_messages

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | uuid | 主键 |
| `session_id` | uuid | 关联会话 |
| `role` | text | `user` 或 `assistant` |
| `content` | text | 消息内容 |
| `embedding` | vector(1536) | OpenAI embedding 向量 |
| `created_at` | timestamptz | 创建时间 |

#### chatgpt_memories

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | uuid | 主键 |
| `message_id` | uuid | 关联消息 |
| `summary` | text | 内容摘要 |
| `keywords` | text[] | 关键词数组 |
| `embedding` | vector(1536) | 向量 |
| `tags` | text[] | 标签数组 |
| `created_at` | timestamptz | 创建时间 |

---

## 5. 部署 SQL 脚本

### 5.1 在 Supabase SQL Editor 执行

1. 左侧菜单 → **SQL Editor**
2. 点击 **New Query**
3. 粘贴下方全部 SQL
4. 点击 **Run**

```sql
-- ========== 1. 启用向量扩展 ==========
create extension if not exists vector;

-- ========== 2. 创建会话表 ==========
create table if not exists chatgpt_sessions (
  id uuid primary key default gen_random_uuid(),
  session_id text not null,
  title text,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

-- ========== 3. 创建消息表 ==========
create table if not exists chatgpt_messages (
  id uuid primary key default gen_random_uuid(),
  session_id uuid references chatgpt_sessions(id) on delete cascade,
  role text not null check (role in ('user', 'assistant')),
  content text not null,
  embedding vector(1536),
  created_at timestamptz default now()
);

-- ========== 4. 创建记忆表 ==========
create table if not exists chatgpt_memories (
  id uuid primary key default gen_random_uuid(),
  message_id uuid references chatgpt_messages(id) on delete cascade,
  summary text,
  keywords text[],
  embedding vector(1536),
  tags text[],
  created_at timestamptz default now()
);

-- ========== 5. 创建索引 ==========
create index idx_messages_session on chatgpt_messages(session_id);
create index idx_messages_embedding on chatgpt_messages using ivfflat (embedding vector_cosine_ops) with (lists = 100);
create index idx_memories_embedding on chatgpt_memories using ivfflat (embedding vector_cosine_ops) with (lists = 100);
create index idx_memories_tags on chatgpt_memories using gin (tags);

-- ========== 6. 启用 RLS 安全策略 ==========
alter table chatgpt_sessions enable row level security;
alter table chatgpt_messages enable row level security;
alter table chatgpt_memories enable row level security;

-- 开发阶段允许所有操作（生产环境需限制）
create policy "allow all" on chatgpt_sessions for all using (true);
create policy "allow all" on chatgpt_messages for all using (true);
create policy "allow all" on chatgpt_memories for all using (true);

-- ========== 7. 创建向量搜索函数 ==========
create or replace function search_similar_messages(
  query_embedding vector(1536),
  match_count int default 5
)
returns table (
  id uuid,
  content text,
  role text,
  similarity float
)
language plpgsql
as $$
begin
  return query
  select m.id, m.content, m.role, 1 - (m.embedding <=> query_embedding) as similarity
  from chatgpt_messages m
  order by m.embedding <=> query_embedding
  limit match_count;
end;
$$;
```

---

## 6. 验证部署

### 6.1 检查表是否创建成功

在 SQL Editor 执行：

```sql
-- 检查表是否存在
select table_name from information_schema.tables
where table_schema = 'public'
and table_name in ('chatgpt_sessions', 'chatgpt_messages', 'chatgpt_memories');

-- 检查向量扩展
select * from pg_extension where extname = 'vector';
```

### 6.2 测试插入数据

```sql
-- 插入测试会话
insert into chatgpt_sessions (session_id, title)
values ('1', '测试会话');

-- 插入测试消息
insert into chatgpt_messages (session_id, role, content)
values (
  (select id from chatgpt_sessions where session_id = '1'),
  'user',
  '你好，请介绍一下你自己'
);

-- 查询验证
select * from chatgpt_messages;
```

---

## 7. 使用流程

### 7.1 数据流

```
用户提问
    ↓
检索相似记忆 (向量检索)
    ↓
拼接上下文 (历史 + 当前)
    ↓
调用 ChatGPT (chatgpt-web ask)
    ↓
存储新会话 (存入 DB)
    ↓
向量化 (embedding 模型)
```

### 7.2 下一步

1. ✅ 完成本部署文档
2. ⬜ 编写存储脚本 (`save_chatgpt_session.sh`)
3. ⬜ 编写检索脚本 (`search_memories.sh`)
4. ⬜ 集成到 `gpt-web-teacher` skill

---

## 8. 故障排除

### 问题 1：vector 扩展创建失败

**错误**：`extension "vector" does not exist`

**解决**：
- Supabase 默认启用 pgvector，检查项目设置
- 或者联系 Supabase 支持

### 问题 2：权限不足

**错误**：`permission denied for schema public`

**解决**：
- 确保使用 `service_role key` 执行 SQL
- 检查 RLS 策略

### 问题 3：索引创建失败

**错误**：`could not create index`

**解决**：
- 检查表数据量，先插入少量测试数据
- 调整 `lists` 参数（默认 100）

---

## 9. 参考资源

- [Supabase pgvector 文档](https://supabase.com/docs/guides/database/pgvector)
- [Supabase SQL Editor](https://supabase.com/docs/guides/sql-editor)
- [向量相似度搜索](https://supabase.com/docs/guides/ai/vector-columns#querying-vectors)

---

**状态**：✅ 文档已创建
**下次更新**：完成存储/检索脚本后更新
