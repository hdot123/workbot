# Persistent Audit Upgrade Path

**文档编号**: P2-AUDIT-007
**版本**: V1.0
**日期**: 2026-05-08
**关联 Linear Issue**: JTO-203
**P2 Project**: P2 — Long-task dry-run + GitLab CI feedback loop
**状态**: 设计稿（dry-run only, no production migration）

---

## 1. 概述

本文档设计从 P1C file-based SQLite audit 到 PostgreSQL/Supabase production_canary 的审计存储升级方案。

**核心原则**：设计阶段不执行迁移，不修改生产数据库。

---

## 2. 当前状态（P1C）

| 属性 | 值 |
|------|-----|
| 存储 | SQLite file (`WEBHOOK_SQLITE_PATH`) |
| 表 | `raw_events`, `canonical_events`, `processing_logs` |
| 限制 | 单文件，并发差，无高可用，查询慢 |
| 位置 | `/Users/busiji/workbot/app/webhook.db` |

---

## 3. 目标状态（P2/Supabase）

| 属性 | 值 |
|------|-----|
| 存储 | PostgreSQL (Supabase production_canary) |
| 表 | `raw_events`, `canonical_events`, `processing_logs`, `action_result_json` |
| 优势 | 高并发，HA，索引优化，扩展性强 |
| 位置 | Supabase project (canary) |

---

## 4. DB Schema

### 4.1 raw_events

| Column | Type | Constraints | 说明 |
|--------|------|-------------|------|
| `id` | UUID | PK, default gen_random_uuid() | 主键 |
| `delivery_id` | UUID | UNIQUE, NOT NULL | 递送唯一标识 |
| `provider` | VARCHAR(32) | NOT NULL | "gitlab", "linear" |
| `raw_body` | JSONB | NOT NULL | 原始 webhook body |
| `raw_body_sha256` | VARCHAR(64) | NOT NULL | SHA256 校验 |
| `content_length` | INT | | Body 大小 |
| `source_ip` | INET | | 来源 IP |
| `headers` | JSONB | | 请求头摘要 |
| `received_at` | TIMESTAMPTZ | NOT NULL, default now() | 接收时间 |
| `created_at` | TIMESTAMPTZ | NOT NULL, default now() | 创建时间 |

```sql
CREATE TABLE raw_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    delivery_id UUID UNIQUE NOT NULL,
    provider VARCHAR(32) NOT NULL,
    raw_body JSONB NOT NULL,
    raw_body_sha256 VARCHAR(64) NOT NULL,
    content_length INT,
    source_ip INET,
    headers JSONB,
    received_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_raw_events_delivery_id ON raw_events(delivery_id);
CREATE INDEX idx_raw_events_provider ON raw_events(provider);
CREATE INDEX idx_raw_events_received_at ON raw_events(received_at);
```

### 4.2 canonical_events

| Column | Type | Constraints | 说明 |
|--------|------|-------------|------|
| `id` | UUID | PK, default gen_random_uuid() | 主键 |
| `event_id` | VARCHAR(64) | UNIQUE, NOT NULL | 事件全局唯一标识 |
| `delivery_id` | UUID | NOT NULL, FK → raw_events | 关联 raw event |
| `idempotency_key` | VARCHAR(64) | UNIQUE, NOT NULL | 去重键 |
| `canonical_type` | VARCHAR(64) | NOT NULL | 事件类型 |
| `payload` | JSONB | NOT NULL | 规范化 payload |
| `metadata` | JSONB | | 元数据 |
| `created_at` | TIMESTAMPTZ | NOT NULL, default now() | 创建时间 |

```sql
CREATE TABLE canonical_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_id VARCHAR(64) UNIQUE NOT NULL,
    delivery_id UUID NOT NULL REFERENCES raw_events(delivery_id),
    idempotency_key VARCHAR(64) UNIQUE NOT NULL,
    canonical_type VARCHAR(64) NOT NULL,
    payload JSONB NOT NULL,
    metadata JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_canonical_events_event_id ON canonical_events(event_id);
CREATE INDEX idx_canonical_events_delivery_id ON canonical_events(delivery_id);
CREATE INDEX idx_canonical_events_type ON canonical_events(canonical_type);
CREATE INDEX idx_canonical_events_idempotency ON canonical_events(idempotency_key);
```

### 4.3 processing_logs

| Column | Type | Constraints | 说明 |
|--------|------|-------------|------|
| `id` | UUID | PK, default gen_random_uuid() | 主键 |
| `event_id` | VARCHAR(64) | NOT NULL, FK → canonical_events | 关联 canonical event |
| `action` | VARCHAR(64) | NOT NULL | 操作类型 |
| `action_result_json` | JSONB | | 操作结果 |
| `status` | VARCHAR(16) | NOT NULL | "success" / "failed" / "pending" |
| `error_message` | TEXT | | 错误信息 |
| `created_at` | TIMESTAMPTZ | NOT NULL, default now() | 创建时间 |

```sql
CREATE TABLE processing_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_id VARCHAR(64) NOT NULL REFERENCES canonical_events(event_id),
    action VARCHAR(64) NOT NULL,
    action_result_json JSONB,
    status VARCHAR(16) NOT NULL,
    error_message TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_processing_logs_event_id ON processing_logs(event_id);
CREATE INDEX idx_processing_logs_action ON processing_logs(action);
CREATE INDEX idx_processing_logs_status ON processing_logs(status);
```

### 4.4 action_result_json 结构

```json
{
  "action": "linear_comment_dry_run",
  "result": {
    "comment_id": "linear_comment_id",
    "issue_key": "JTO-XXX",
    "status": "success",
    "timestamp": "2026-05-08T10:30:00Z"
  },
  "error": null,
  "duration_ms": 450,
  "retry_count": 0
}
```

---

## 5. 查询接口

### 5.1 Query by delivery_id

```sql
SELECT r.*, c.*, p.*
FROM raw_events r
LEFT JOIN canonical_events c ON c.delivery_id = r.delivery_id
LEFT JOIN processing_logs p ON p.event_id = c.event_id
WHERE r.delivery_id = '<delivery_id>';
```

用途：追踪单次 webhook 递送的完整处理链。

### 5.2 Query by event_id

```sql
SELECT c.*, p.*
FROM canonical_events c
LEFT JOIN processing_logs p ON p.event_id = c.event_id
WHERE c.event_id = '<event_id>';
```

用途：查询特定事件的完整处理历史。

### 5.3 Query by issue_id

```sql
SELECT c.*, p.*
FROM canonical_events c
LEFT JOIN processing_logs p ON p.event_id = c.event_id
WHERE c.payload->>'issue_id' = '<issue_id>'
ORDER BY c.created_at DESC;
```

用途：查询特定 Linear issue 相关的所有事件。

### 5.4 Query by pipeline_id

```sql
SELECT c.*, p.*
FROM canonical_events c
LEFT JOIN processing_logs p ON p.event_id = c.event_id
WHERE c.payload->>'pipeline_id' = '<pipeline_id>'
ORDER BY c.created_at DESC;
```

用途：查询特定 GitLab pipeline 的所有相关事件。

### 5.5 Query by run_id

```sql
SELECT c.*, p.*
FROM canonical_events c
LEFT JOIN processing_logs p ON p.event_id = c.event_id
WHERE c.payload->>'run_id' = '<run_id>'
ORDER BY c.created_at DESC;
```

用途：查询特定 Factory run 的所有相关事件。

---

## 6. Retention Policy

| 数据类型 | 保留期 | 清理策略 |
|---------|--------|---------|
| raw_events | 90 天 | 自动删除过期记录 |
| canonical_events | 365 天 | 保留关键事件 |
| processing_logs | 365 天 | 与 canonical_events 同步 |
| action_result_json | 365 天 | 作为 processing_logs 一部分 |

### 6.1 清理 SQL（未来参考）

```sql
-- 清理 90 天前的 raw_events
DELETE FROM raw_events WHERE received_at < now() - interval '90 days';

-- 清理 365 天前的 canonical_events 及其关联的 processing_logs
DELETE FROM processing_logs
WHERE event_id IN (
    SELECT event_id FROM canonical_events
    WHERE created_at < now() - interval '365 days'
);
DELETE FROM canonical_events WHERE created_at < now() - interval '365 days';
```

---

## 7. Duplicate Event Strategy

| 策略 | 实现 |
|------|------|
| Idempotency key | UNIQUE constraint on `canonical_events.idempotency_key` |
| Duplicate detection | INSERT ... ON CONFLICT (idempotency_key) DO NOTHING |
| Audit duplicate | 记录到 processing_logs status="duplicate_skipped" |

```sql
INSERT INTO canonical_events (event_id, delivery_id, idempotency_key, canonical_type, payload)
VALUES ('<event_id>', '<delivery_id>', '<idempotency_key>', '<type>', '<payload>'::jsonb)
ON CONFLICT (idempotency_key) DO NOTHING;
```

---

## 8. Migration Plan

### 8.1 阶段 1: Schema 验证（P2 dry-run）

1. 在 Supabase canary project 创建 schema
2. 插入模拟数据验证
3. 运行查询验证
4. **不迁移真实数据**

### 8.2 阶段 2: 数据导出（未来）

```bash
# 导出 SQLite 数据
sqlite3 webhook.db ".dump raw_events" > raw_events.sql
sqlite3 webhook.db ".dump canonical_events" > canonical_events.sql
sqlite3 webhook.db ".dump processing_logs" > processing_logs.sql
```

### 8.3 阶段 3: 数据导入（未来）

1. 转换 SQL 方言（SQLite → PostgreSQL）
2. 导入到 canary project
3. 验证数据完整性（count check, SHA256 check）
4. 运行查询验证

### 8.4 阶段 4: 切换（未来）

1. 停止 SQLite 写入
2. 切换到 PostgreSQL 连接
3. 验证新连接
4. 保留 SQLite 备份

### 8.5 阶段 5: 清理（未来）

1. 确认新系统稳定运行 7 天
2. 删除 SQLite 文件
3. 更新文档

---

## 9. Rollback Plan

如果迁移出现问题：

1. 立即停止 PostgreSQL 写入
2. 切换回 SQLite 连接
3. 验证 SQLite 数据完整性
4. 通知相关人员
5. 审计回滚操作
6. 修复问题后重新尝试

**P2 当前：不执行迁移，无需回滚。**

---

## 10. Schema Gap Analysis（SQLite → PostgreSQL）

| 特性 | SQLite | PostgreSQL | Gap |
|------|--------|------------|-----|
| JSON | TEXT (手动解析) | JSONB (原生) | ✅ 改进 |
| UUID | TEXT | UUID 类型 | ✅ 改进 |
| INET | TEXT | INET 类型 | ✅ 改进 |
| 并发写入 | 单文件锁 | 高并发 | ✅ 改进 |
| 索引 | 基础 B-tree | 多种索引 | ✅ 改进 |
| 外键 | 可选 | 强制 | ✅ 改进 |
| 时区 | 无 | TIMESTAMPTZ | ✅ 改进 |

---

## 11. 不包含 Secret 声明

本文档不包含任何 API key、token、password、secret、private key、database URL 或其他敏感信息。

所有示例均为结构定义和 schema 描述。

---

**文档结束**
**P2-07 交付物 — Persistent Audit Upgrade Path V1.0**
