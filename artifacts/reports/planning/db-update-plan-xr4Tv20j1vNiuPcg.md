# n8n DB Update Plan - workflow_entity id `xr4Tv20j1vNiuPcg`

> **目标**: 在 node-22 上安全更新 n8n workflow `xr4Tv20j1vNiuPcg` 的 nodes/connections/settings
> **n8n 版本**: 2.18.5
> **数据库**: SQLite (非 PostgreSQL)
> **状态**: 规划阶段 - 只读研究，尚未执行任何修改

---

## 1. Schema Findings

### 数据库类型
- **SQLite** (非 PostgreSQL)
- 数据库文件路径: `/opt/n8n/data/database.sqlite` (宿主机) / `/home/node/.n8n/database.sqlite` (容器内)

### workflow_entity 表结构

基于 n8n 2.18.5 源码分析：

| Column | Type | Notes |
|--------|------|-------|
| `id` | varchar(36) PRIMARY KEY | 工作流 UUID |
| `name` | varchar(128) | 工作流名称 |
| `active` | boolean DEFAULT 0 | 是否激活 |
| `nodes` | text | JSON 字符串，存储所有节点定义 |
| `connections` | text | JSON 字符串，存储节点间连接 |
| `settings` | text | JSON 字符串，存储工作流设置 |
| `staticData` | text | JSON 字符串，静态数据 |
| `pinData` | text | JSON 字符串，测试数据 |
| `versionId` | varchar(36) | 版本 UUID |
| `triggerCount` | integer | 触发器数量 |
| `createdAt` | datetime | 创建时间 |
| `updatedAt` | datetime | 更新时间 |

### 关键发现

1. **nodes 存储格式**: `text` (JSON 字符串)
   - SQLite 没有原生 JSON 类型，n8n 使用 text 列存储 JSON
   - 格式: `[{"parameters":{...},"type":"n8n-nodes-base.webhook","name":"Webhook","typeVersion":2,"position":[x,y],"id":"<node-id>","webhookId":"<uuid>"}]`

2. **connections 存储格式**: `text` (JSON 字符串)
   - 格式: `{"main":[[{"node":"Code node","type":"main","index":0}]]}`

3. **settings 存储格式**: `text` (JSON 字符串)
   - 格式: `{"executionOrder":"v1","saveManualExecutions":true}`

---

## 2. 目标 Workflow 当前状态查询

### 第一步：备份当前数据

```bash
# SSH 到 node-22
ssh root@<node-22-ip>

# 备份数据库
cp /opt/n8n/data/database.sqlite /opt/n8n/backups/database.sqlite.backup.$(date +%Y%m%d_%H%M%S)

# 导出当前 workflow 数据（不打印敏感信息）
docker exec n8n sqlite3 /home/node/.n8n/database.sqlite <<'SQL'
.mode json
SELECT id, name, active, versionId, 
       length(nodes) as nodes_len,
       length(connections) as connections_len,
       length(settings) as settings_len
FROM workflow_entity 
WHERE id = 'xr4Tv20j1vNiuPcg';
SQL
```

### 第二步：查看当前节点结构（不打印完整 JSON）

```bash
docker exec n8n sqlite3 /home/node/.n8n/database.sqlite <<'SQL'
SELECT 
    id,
    name,
    active,
    json_extract(nodes, '$[0].name') as first_node_name,
    json_array_length(nodes) as node_count
FROM workflow_entity 
WHERE id = 'xr4Tv20j1vNiuPcg';
SQL
```

---

## 3. 目标 Workflow 设计

### 节点列表

| # | Node Name | Type | Key Parameters |
|---|-----------|------|----------------|
| 1 | Webhook | n8n-nodes-base.webhook | httpMethod=POST, path=events, responseMode=responseNode, options.rawBody=true |
| 2 | Verify Linear Signature | n8n-nodes-base.code | 验证 X-Linear-Signature (HMAC-SHA256) |
| 3 | Respond to Webhook | n8n-nodes-base.respondToWebhook | responseCode/body 动态响应 |

### 连接拓扑

```
Webhook (main output) -> Verify Linear Signature (main input)
Verify Linear Signature (main output) -> Respond to Webhook (main input)
```

### Settings

```json
{
  "executionOrder": "v1",
  "saveManualExecutions": true
}
```

---

## 4. 安全更新模板

### 方式一：使用 JSON 文件（推荐）

#### 步骤 1: 在宿主机创建 nodes.json

```json
// /opt/n8n/nodes-update.json
[
  {
    "parameters": {
      "httpMethod": "POST",
      "path": "events",
      "responseMode": "responseNode",
      "options": {
        "rawBody": true
      }
    },
    "type": "n8n-nodes-base.webhook",
    "typeVersion": 2,
    "position": [250, 300],
    "id": "webhook-node-id",
    "name": "Webhook",
    "webhookId": "<generate-uuid>"
  },
  {
    "parameters": {
      "jsCode": "// Verify Linear Signature\nconst crypto = require('crypto');\nconst headers = $input.first().json.headers;\nconst body = $input.first().json.body;\nconst signature = headers['x-linear-signature'];\nconst secret = process.env.LINEAR_WEBHOOK_SECRET;\nconst hmac = crypto.createHmac('sha256', secret);\nhmac.update(JSON.stringify(body));\nconst expected = hmac.digest('hex');\nif (signature !== expected) {\n  throw new Error('Invalid signature');\n}\nreturn [{ json: body }];"
    },
    "type": "n8n-nodes-base.code",
    "typeVersion": 2,
    "position": [500, 300],
    "id": "code-node-id",
    "name": "Verify Linear Signature"
  },
  {
    "parameters": {
      "respondWith": "json",
      "responseCode": "={{$json.statusCode || 200}}",
      "responseBody": "={{$json.body || {success: true}}}",
      "options": {}
    },
    "type": "n8n-nodes-base.respondToWebhook",
    "typeVersion": 1,
    "position": [750, 300],
    "id": "respond-node-id",
    "name": "Respond to Webhook"
  }
]
```

#### 步骤 2: 创建 connections.json

```json
// /opt/n8n/connections-update.json
{
  "webhook-node-id": {
    "main": [
      [
        {
          "node": "Verify Linear Signature",
          "type": "main",
          "index": 0
        }
      ]
    ]
  },
  "code-node-id": {
    "main": [
      [
        {
          "node": "Respond to Webhook",
          "type": "main",
          "index": 0
        }
      ]
    ]
  }
}
```

#### 步骤 3: 创建 settings.json

```json
// /opt/n8n/settings-update.json
{
  "executionOrder": "v1",
  "saveManualExecutions": true
}
```

#### 步骤 4: 执行安全更新

```bash
# SSH 到 node-22
ssh root@<node-22-ip>

# 确保有备份
cp /opt/n8n/data/database.sqlite /opt/n8n/backups/database.sqlite.backup.$(date +%Y%m%d_%H%M%S)

# 使用 sqlite3 和 JSON 文件执行更新
docker exec n8n sh -c 'sqlite3 /home/node/.n8n/database.sqlite' <<'SQL'
-- 验证 workflow 存在且记录当前状态
BEGIN TRANSACTION;

-- 保存当前版本 ID 用于回滚
SELECT id, name, active, versionId FROM workflow_entity WHERE id = 'xr4Tv20j1vNiuPcg';

-- 更新 nodes（从 JSON 文件读取）
UPDATE workflow_entity 
SET nodes = readfile('/home/node/nodes-update.json')
WHERE id = 'xr4Tv20j1vNiuPcg';

-- 更新 connections
UPDATE workflow_entity 
SET connections = readfile('/home/node/connections-update.json')
WHERE id = 'xr4Tv20j1vNiuPcg';

-- 更新 settings
UPDATE workflow_entity 
SET settings = readfile('/home/node/settings-update.json')
WHERE id = 'xr4Tv20j1vNiuPcg';

-- 更新时间戳
UPDATE workflow_entity 
SET updatedAt = datetime('now')
WHERE id = 'xr4Tv20j1vNiuPcg';

-- 验证更新结果
SELECT id, name, active, length(nodes) as nodes_len, length(connections) as connections_len, length(settings) as settings_len
FROM workflow_entity 
WHERE id = 'xr4Tv20j1vNiuPcg';

COMMIT;
SQL
```

### 方式二：使用 Python 脚本（更安全，可验证 JSON）

```python
#!/usr/bin/env python3
"""
n8n Workflow Entity Updater
安全更新 workflow_entity 表中的 nodes/connections/settings
"""
import sqlite3
import json
import sys
import os
from datetime import datetime

DB_PATH = '/opt/n8n/data/database.sqlite'
WORKFLOW_ID = 'xr4Tv20j1vNiuPcg'

def backup_db(db_path):
    """备份数据库"""
    backup_path = f"{db_path}.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    import shutil
    shutil.copy2(db_path, backup_path)
    return backup_path

def validate_json_file(file_path):
    """验证 JSON 文件格式"""
    with open(file_path, 'r') as f:
        data = json.load(f)
    return json.dumps(data, ensure_ascii=False)

def update_workflow(db_path, workflow_id, nodes_json, connections_json, settings_json):
    """更新 workflow"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # 开始事务
        cursor.execute("BEGIN TRANSACTION")
        
        # 验证 workflow 存在
        cursor.execute("SELECT id, name, active FROM workflow_entity WHERE id = ?", (workflow_id,))
        row = cursor.fetchone()
        if not row:
            raise ValueError(f"Workflow {workflow_id} not found")
        
        print(f"Found workflow: id={row[0]}, name={row[1]}, active={row[2]}")
        
        # 更新 nodes
        cursor.execute(
            "UPDATE workflow_entity SET nodes = ? WHERE id = ?",
            (nodes_json, workflow_id)
        )
        
        # 更新 connections
        cursor.execute(
            "UPDATE workflow_entity SET connections = ? WHERE id = ?",
            (connections_json, workflow_id)
        )
        
        # 更新 settings
        cursor.execute(
            "UPDATE workflow_entity SET settings = ? WHERE id = ?",
            (settings_json, workflow_id)
        )
        
        # 更新时间戳
        cursor.execute(
            "UPDATE workflow_entity SET updatedAt = datetime('now') WHERE id = ?",
            (workflow_id,)
        )
        
        # 提交事务
        cursor.execute("COMMIT")
        
        # 验证更新
        cursor.execute(
            "SELECT id, name, active, length(nodes), length(connections), length(settings) FROM workflow_entity WHERE id = ?",
            (workflow_id,)
        )
        result = cursor.fetchone()
        print(f"Updated workflow: id={result[0]}, name={result[1]}, active={result[2]}, nodes_len={result[3]}, connections_len={result[4]}, settings_len={result[5]}")
        
        return True
        
    except Exception as e:
        cursor.execute("ROLLBACK")
        print(f"Error: {e}", file=sys.stderr)
        return False
    finally:
        conn.close()

if __name__ == '__main__':
    # 验证文件存在
    nodes_file = '/opt/n8n/nodes-update.json'
    connections_file = '/opt/n8n/connections-update.json'
    settings_file = '/opt/n8n/settings-update.json'
    
    for f in [nodes_file, connections_file, settings_file]:
        if not os.path.exists(f):
            print(f"Error: {f} not found", file=sys.stderr)
            sys.exit(1)
    
    # 备份数据库
    backup_path = backup_db(DB_PATH)
    print(f"Database backed up to: {backup_path}")
    
    # 验证 JSON
    nodes_json = validate_json_file(nodes_file)
    connections_json = validate_json_file(connections_file)
    settings_json = validate_json_file(settings_file)
    
    # 执行更新
    success = update_workflow(DB_PATH, WORKFLOW_ID, nodes_json, connections_json, settings_json)
    sys.exit(0 if success else 1)
```

### 方式三：纯 SQL 模板（直接嵌入 JSON）

```sql
-- 安全更新模板（直接嵌入 JSON）
-- 注意：先备份数据库！

BEGIN TRANSACTION;

UPDATE workflow_entity 
SET 
    nodes = '[{"parameters":{"httpMethod":"POST","path":"events","responseMode":"responseNode","options":{"rawBody":true}},"type":"n8n-nodes-base.webhook","typeVersion":2,"position":[250,300],"id":"<webhook-node-id>","name":"Webhook","webhookId":"<uuid>"},{"parameters":{"jsCode":"// Verify Linear Signature..."},"type":"n8n-nodes-base.code","typeVersion":2,"position":[500,300],"id":"<code-node-id>","name":"Verify Linear Signature"},{"parameters":{"respondWith":"json","responseCode":"={{$json.statusCode || 200}}","responseBody":"={{$json.body || {success: true}}}"},"type":"n8n-nodes-base.respondToWebhook","typeVersion":1,"position":[750,300],"id":"<respond-node-id>","name":"Respond to Webhook"}]',
    connections = '{"<webhook-node-id>":{"main":[[{"node":"Verify Linear Signature","type":"main","index":0}]]},"<code-node-id>":{"main":[[{"node":"Respond to Webhook","type":"main","index":0}]]}}',
    settings = '{"executionOrder":"v1","saveManualExecutions":true}',
    updatedAt = datetime('now')
WHERE id = 'xr4Tv20j1vNiuPcg';

-- 验证更新
SELECT id, name, active, length(nodes) as nodes_len, length(connections) as connections_len, length(settings) as settings_len
FROM workflow_entity 
WHERE id = 'xr4Tv20j1vNiuPcg';

COMMIT;
```

---

## 5. 验证与回滚

### 验证命令

```bash
# 验证更新后的 JSON 格式
docker exec n8n sqlite3 /home/node/.n8n/database.sqlite <<'SQL'
SELECT 
    id,
    name,
    active,
    json_valid(nodes) as nodes_valid,
    json_valid(connections) as connections_valid,
    json_valid(settings) as settings_valid,
    json_array_length(nodes) as node_count
FROM workflow_entity 
WHERE id = 'xr4Tv20j1vNiuPcg';
SQL

# 检查节点名称（不打印完整 JSON）
docker exec n8n sqlite3 /home/node/.n8n/database.sqlite <<'SQL'
SELECT 
    json_extract(value, '$.name') as node_name,
    json_extract(value, '$.type') as node_type
FROM workflow_entity, json_each(nodes)
WHERE id = 'xr4Tv20j1vNiuPcg';
SQL

# 重启 n8n 使更改生效
docker compose -f /opt/n8n/docker-compose.yml restart

# 检查健康状态
docker compose -f /opt/n8n/docker-compose.yml ps
curl -s https://webhook.exa.edu.kg/healthz
```

### 回滚命令

```bash
# 回滚到备份
docker compose -f /opt/n8n/docker-compose.yml down
cp /opt/n8n/backups/database.sqlite.backup.<timestamp> /opt/n8n/data/database.sqlite
docker compose -f /opt/n8n/docker-compose.yml up -d

# 验证回滚
curl -s https://webhook.exa.edu.kg/healthz
```

---

## 6. 安全注意事项

1. **不要打印 secrets**: 所有包含 API keys、webhook secrets 的值使用环境变量引用（如 `$env.LINEAR_WEBHOOK_SECRET`）
2. **备份优先**: 任何更新前必须备份数据库
3. **事务保护**: 使用 BEGIN TRANSACTION / COMMIT 确保原子性
4. **验证 JSON**: 更新前验证 JSON 格式正确
5. **测试环境**: 先在测试环境验证更新脚本
6. **ID 一致性**: 确保 nodes 中的 id 与 connections 中的引用一致

---

## 7. 执行检查清单

- [ ] 备份数据库到 `/opt/n8n/backups/`
- [ ] 创建 nodes-update.json 并验证 JSON 格式
- [ ] 创建 connections-update.json 并验证 JSON 格式
- [ ] 创建 settings-update.json 并验证 JSON 格式
- [ ] 复制 JSON 文件到容器内 `/home/node/`
- [ ] 执行更新（事务保护）
- [ ] 验证 JSON 有效性（json_valid）
- [ ] 验证节点数量（json_array_length）
- [ ] 重启 n8n 容器
- [ ] 验证健康状态
- [ ] 测试 Webhook 端点
- [ ] 保留备份文件至少 7 天

---

**文档版本**: V1.0  
**创建日期**: 2026-05-04  
**状态**: 规划完成 - 等待执行批准
