# OPS-LINEAR-011 Rollback Plan

> 文档编号：OPS-LINEAR-011  
> 版本：V1.0  
> 创建日期：2026-05-04  
> 维护人：bailian-worker  
> 状态：草稿中  
> 用途：OPS-LINEAR-010（Project canary comment）回滚到 OPS-LINEAR-009（label-scope canary）+ 紧急 dry-run 降级

---

## 一、目标

OPS-LINEAR-010 将 Linear canary comment 的识别范围从 label 扩展到 Project membership。如果 Project canary comment 运行异常（误触发、不触发、外部 API 副作用），本预案提供：

1. **一键回滚**：移除 `LINEAR_CANARY_ALLOWED_PROJECT_IDS` 环境变量，恢复 OPS-LINEAR-009 label-scope 行为
2. **紧急 dry-run 降级**：将 ingress 模式切换至 `canary_dryrun`，完全关闭 canary comment action

---

## 二、一键回滚（OPS-010 → OPS-009）

### 2.1 命令

```bash
ssh root@node-22 'set -euo pipefail
cd /opt/n8n-linear

# 0. 备份当前 env
TS=$(date +%Y%m%d-%H%M%S)
cp .env.webhook-ingress ".env.webhook-ingress.bak-ops10-to-ops9-${TS}"

# 1. 移除 Project whitelist，恢复 OPS-009 label-scope 行为
python3 -c "
from pathlib import Path
path = Path('.env.webhook-ingress')
lines = [l for l in path.read_text().splitlines()
         if not l.startswith('LINEAR_CANARY_ALLOWED_PROJECT_IDS=')]
# 确保 canary comment 仍开启
if not any(l.startswith('LINEAR_CANARY_COMMENT_ENABLED=') for l in lines):
    lines.append('LINEAR_CANARY_COMMENT_ENABLED=true')
path.write_text('\n'.join(lines) + '\n')
"

chmod 600 .env.webhook-ingress

# 2. 重启 webhook-ingress
docker compose up -d --force-recreate webhook-ingress
sleep 5

# 3. 验证
echo "=== ROLLBACK COMPLETE: OPS-LINEAR-010 Project scope removed ==="
echo "Current mode: production_canary"
echo "Scope: OPS-LINEAR-009 label-based (project whitelist removed)"
docker compose ps webhook-ingress
'
```

### 2.2 效果

| 项目 | 回滚前 (OPS-010) | 回滚后 (OPS-009) |
|------|-------------------|-------------------|
| `WEBHOOK_INGRESS_MODE` | `production_canary` | `production_canary`（不变）|
| `LINEAR_CANARY_COMMENT_ENABLED` | `true` | `true`（不变）|
| `LINEAR_CANARY_ALLOWED_PROJECT_IDS` | `fe99fb4e-a70a-46f9-b94e-a28ef8e5c666` | **已移除** |
| Canary 识别方式 | Project membership | Label / title guard |

### 2.3 验证

```bash
# 确认 ingress mode 仍是 production_canary
curl -s https://webhook.exa.edu.kg/health

# 确认 env 中无 Project whitelist
ssh root@node-22 'grep LINEAR_CANARY_ALLOWED_PROJECT_IDS /opt/n8n-linear/.env.webhook-ingress || echo "CONFIRMED: project whitelist removed"'

# 确认 canary comment 仍可用（label-scope）
ssh root@node-22 'grep LINEAR_CANARY_COMMENT_ENABLED /opt/n8n-linear/.env.webhook-ingress'
```

---

## 三、紧急 dry-run 降级

当一键回滚不足以消除异常，或 canary comment action 本身存在严重问题时，执行全量 dry-run 降级。

### 3.1 命令

```bash
ssh root@node-22 'set -euo pipefail
cd /opt/n8n-linear

# 0. 备份
TS=$(date +%Y%m%d-%H%M%S)
cp .env ".env.bak-ops11-dryrun-${TS}"
cp .env.webhook-ingress ".env.webhook-ingress.bak-ops11-dryrun-${TS}"

# 1. 切换 .env 至 canary_dryrun
python3 -c "
from pathlib import Path
for path in (Path('.env'), Path('.env.webhook-ingress')):
    if not path.exists():
        continue
    lines = []
    for line in path.read_text().splitlines():
        if line.startswith('WEBHOOK_INGRESS_MODE='):
            lines.append('WEBHOOK_INGRESS_MODE=canary_dryrun')
        elif line.startswith('N8N_CANONICAL_WEBHOOK_URL='):
            lines.append('N8N_CANONICAL_WEBHOOK_URL=http://n8n:5678/webhook/canonical-dryrun-events/webhook/canonical-events')
        elif line.startswith('LINEAR_CANARY_COMMENT_ENABLED='):
            lines.append('LINEAR_CANARY_COMMENT_ENABLED=false')
        elif line.startswith('LINEAR_CANARY_API_TOKEN=') or line.startswith('LINEAR_CANARY_ALLOWED_PROJECT_IDS='):
            continue  # 移除敏感 token 和 project whitelist
        else:
            lines.append(line)
    path.write_text('\n'.join(lines) + '\n')
"

chmod 600 .env.webhook-ingress

# 2. 重启
docker compose up -d --force-recreate webhook-ingress
sleep 5

# 3. 验证
echo "=== EMERGENCY DRY-RUN COMPLETE ==="
echo "Ingress mode: canary_dryrun"
echo "Canary comment: DISABLED"
echo "n8n target: canonical-dryrun-events"
docker compose ps webhook-ingress
'
```

### 3.2 效果

| 变量 | 降级前 | 降级后 |
|------|--------|--------|
| `WEBHOOK_INGRESS_MODE` | `production_canary` | `canary_dryrun` |
| `N8N_CANONICAL_WEBHOOK_URL` | 生产 n8n URL | dry-run n8n URL |
| `LINEAR_CANARY_COMMENT_ENABLED` | `true` | `false` |
| `LINEAR_CANARY_API_TOKEN` | 存在 | **已移除** |
| `LINEAR_CANARY_ALLOWED_PROJECT_IDS` | 存在 | **已移除** |

### 3.3 验证

```bash
# 确认 mode 已切换
curl -s https://webhook.exa.edu.kg/health
# 预期: {"status":"ok","mode":"canary_dryrun"}

# 确认 canary comment 已关闭
ssh root@node-22 'grep LINEAR_CANARY_COMMENT_ENABLED /opt/n8n-linear/.env.webhook-ingress'
# 预期: LINEAR_CANARY_COMMENT_ENABLED=false

# 确认 dry-run n8n workflow 接收事件
ssh root@node-22 'docker exec n8n sqlite3 /home/node/.n8n/database.sqlite \
  "SELECT id, startedAt, status FROM execution_entity \
   WHERE workflowId = (SELECT id FROM workflow_entity WHERE name = '\''canonical-dryrun-events'\'' LIMIT 1) \
   ORDER BY startedAt DESC LIMIT 3;"'
```

---

## 四、决策矩阵

| 场景 | 动作 | 严重级别 |
|------|------|----------|
| Project canary 误触发到非 canary project | 2.1 一键回滚 | Medium |
| Project canary 不触发（projectId 缺失或格式异常）| 2.1 一键回滚 | Medium |
| Canary comment 产生错误评论或 API 异常 | 2.1 + 可选关闭 comment action | High |
| Canary comment 导致 n8n crash 或数据异常 | 3.1 紧急 dry-run | Critical |
| Linear API token 泄露或权限异常 | 3.1 紧急 dry-run（移除 token）| Critical |
| 误报，后续需重新测试 | 2.1 可逆，重新执行 010 部署 | Low |

---

## 五、回滚后检查清单

- [ ] 一键回滚验证通过（2.3 全部命令确认）
- [ ] 或紧急 dry-run 验证通过（3.3 全部命令确认）
- [ ] 回滚原因、时间戳、证据已记录
- [ ] 检查 Supabase 是否有异常 canary comment 记录
- [ ] 确认 `production-canary-events` n8n workflow 无新执行（dry-run 场景）
- [ ] 确认 `canonical-dryrun-events` n8n workflow 正常接收事件（dry-run 场景）
- [ ] 通知团队

---

## 六、关键文件参考

| 资源 | 位置 | 用途 |
|------|------|------|
| 部署目录 | `/opt/n8n-linear/` | docker-compose.yml, .env 文件 |
| Ingress env | `/opt/n8n-linear/.env` | `WEBHOOK_INGRESS_MODE`, `N8N_CANONICAL_WEBHOOK_URL` |
| Webhook env | `/opt/n8n-linear/.env.webhook-ingress` | `WEBHOOK_DATABASE_URL`, `LINEAR_CANARY_*` 变量 |
| n8n SQLite | `/opt/n8n/data/database.sqlite` | workflow + execution 数据 |
| webhook-ingress 容器 | `webhook-ingress` | Docker 容器 |
| n8n 容器 | `n8n` | Docker 容器 |
| Health 端点 | `https://webhook.exa.edu.kg/health` | 模式验证 |

---

## 七、与其他文档的关系

| 本文档 | 关联文档 | 关系说明 |
|--------|----------|----------|
| OPS-LINEAR-011 回滚预案 | OPS-LINEAR-010 验收报告 | 回滚 010 的 Project scope |
| OPS-LINEAR-011 回滚预案 | OPS-LINEAR-009 验收报告 | 回滚目标为 009 label-scope 基线 |
| OPS-LINEAR-011 回滚预案 | OPS-LINEAR-008 回滚预案 | 复用 dry-run 降级模式 |
| OPS-LINEAR-011 回滚预案 | OPS-LINEAR-006 dry-run 回滚 | 复用 canary_dryrun 切换逻辑 |

---

**文档状态**：草稿中  
**审批人**：待定
