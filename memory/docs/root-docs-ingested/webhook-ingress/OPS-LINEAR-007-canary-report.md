# OPS-LINEAR-007 production canary report

日期：2026-05-04

## 结论

PASS。Webhook Ingress 已从 n8n dry-run 进入受控 `production_canary`：公网入口不变，仍为 `POST https://webhook.exa.edu.kg/webhook/events`；旧 `/webhooks/linear` 继续 404；没有新增 Linear webhook；完整生产自动化仍未启用。production canary workflow 只执行低风险动作：n8n execution success + Supabase processing_logs `canary_forward`，不调用 GitLab、Slack、批量 Linear 更新、项目状态迁移或真实验收流程。

## 当前运行状态

| 项 | 状态 |
|----|------|
| 公网入口 | `POST /webhook/events` |
| 旧入口 | `POST /webhooks/linear` = 404 |
| ingress mode | `production_canary` |
| ingress DB | `WEBHOOK_DATABASE_URL` configured via root-only `.env.webhook-ingress` |
| `.env.webhook-ingress` 权限 | `600 root:root` |
| n8n canary workflow | `production-canary-events` active/published |
| dry-run workflow | `canonical-dryrun-events` still active for rollback |
| full production workflow | `standard provider webhooks` inactive |

Endpoint evidence:

```text
events_get=405 old_path=404 root=404 rest=404 health=200
```

## 持久化与 fail-closed

已修复容器重建后 DB URL 丢失问题：

- 新增 `/opt/n8n-linear/.env.webhook-ingress`，权限 `600 root:root`。
- `docker-compose.yml` 新增 compose-managed `webhook-ingress` 服务。
- `webhook-ingress` 使用 `env_file: [.env, .env.webhook-ingress]`。
- 使用 Supabase pooler IPv4 连接串；避免 node-22 direct host IPv6 不通问题。

代码层 fail-closed：

- `WEBHOOK_INGRESS_MODE in {canary_dryrun, production_canary, live}` 时，缺少 `WEBHOOK_DATABASE_URL` 会拒绝启动。
- `shadow` 仍允许本地 SQLite fallback。

本地测试：

```text
20 passed
```

## production canary workflow

Workflow：`production-canary-events`

- path：`/webhook/production-canary-events/webhook/canonical-production-canary`（Docker 内部）
- 模式：Webhook `onReceived`
- 动作：仅产生 n8n success execution，不执行外部 API / 通知 / 状态迁移。

最新 execution：

```text
109|production-canary-events|success|webhook|2026-05-04 16:58:48.01+08|2026-05-04 16:58:48.019+08
108|production-canary-events|success|webhook|2026-05-04 16:58:46.191+08|2026-05-04 16:58:46.209+08
107|production-canary-events|success|webhook|2026-05-04 16:58:34.044+08|2026-05-04 16:58:34.053+08
106|production-canary-events|success|webhook|2026-05-04 16:58:25.39+08|2026-05-04 16:58:25.4+08
105|production-canary-events|success|webhook|2026-05-04 16:58:18.506+08|2026-05-04 16:58:18.517+08
104|production-canary-events|success|webhook|2026-05-04 16:57:27.15+08|2026-05-04 16:57:27.186+08
```

Execution `103` 是初版 Code node 引号问题导致的历史 error，已通过改为 minimal onReceived workflow 修复。

## 真实 Linear 三类事件验收

临时 issue：

- Issue：`JTO-182`
- Issue ID：`c6d2463a-23f7-4212-a8fd-003ade83cf8a`
- URL：`https://linear.app/jtoom/issue/JTO-182/ops-linear-007-production-canary-validation-1777885094`
- 清理：已 archive

Supabase canonical evidence：

```text
evt_69ded3f1-8904-4a4a-9fa2-aa17a628fc11|Issue|create|issue|created|...|n8n_forwarded=1
evt_0f1aba63-e01c-4b4a-9755-cfca9e66da55|Issue|update|issue|updated|...|n8n_forwarded=1
evt_7d78b1d9-076f-4f5e-8481-45945f34dca1|Comment|create|comment|created|...|n8n_forwarded=1
```

附加清理事件：

```text
evt_0c7b7efe-d017-4b22-9ae9-89a6a1d3e32e|Issue|remove|issue|deleted|...|n8n_forwarded=1
```

Processing logs for issue rows：

```text
store|INFO|raw and canonical event stored|{}
canary_forward|INFO|canonical event forwarded successfully|{'status': 'success', 'route_mode': 'production_canary'}
```

## 幂等验收

合成 signed replay 使用同一 `Linear-Delivery`：

```text
try1 code=200 body={"ok":true,"status":"accepted",...}
try2 code=200 body={"ok":true,"status":"duplicate_accepted",...same event_id...}
```

结果：duplicate 不重复创建 canonical event，不重复执行 canary action，不重复 forward 到 n8n。

## 日志脱敏验收

扫描 ingress 最近日志：

```text
redaction_ok
```

未发现：

- DB URL / DB password
- Linear signing secret
- Authorization
- Linear-Signature 明文
- Linear API token

## 生产自动化隔离

当前 active workflows：

```text
canonical-dryrun-events|canonical dryrun events|t
production-canary-events|production canary events|t
std-provider-webhooks|standard provider webhooks|f
webhook events|t
```

说明：

- 公网 `/webhook/events` 先进入 ingress verifier，再转内部 `production-canary-events`。
- `production-canary-events` 只有 minimal Webhook onReceived，不含 HTTP Request node，不调用 Linear/GitLab/Slack。
- `standard provider webhooks` inactive。
- 本轮 Linear API 只由主线程用于创建/更新/评论/归档临时测试 issue；workflow 本身不调用外部 API。

## 回滚方案

一键回滚到 dry-run：

```bash
ssh node-22 'set -euo pipefail
cd /opt/n8n-linear
cp .env .env.bak-rollback-ops-linear-007-$(date +%Y%m%d-%H%M%S)
python3 - <<"PY"
from pathlib import Path
p=Path(".env")
lines=p.read_text().splitlines()
updates={
 "WEBHOOK_INGRESS_MODE":"canary_dryrun",
 "N8N_CANONICAL_WEBHOOK_URL":"http://n8n:5678/webhook/canonical-dryrun-events/webhook/canonical-events",
}
out=[]; seen=set()
for line in lines:
    key=line.split("=",1)[0] if "=" in line else None
    if key in updates:
        out.append(f"{key}={updates[key]}"); seen.add(key)
    else:
        out.append(line)
for k,v in updates.items():
    if k not in seen: out.append(f"{k}={v}")
p.write_text("\n".join(out)+"\n")
PY
docker compose up -d --force-recreate webhook-ingress
sleep 5
docker exec webhook-ingress-shadow python - <<"PY"
from workspace.tools.webhook_ingress.server import ServerConfig
c=ServerConfig.from_env()
assert c.ingress_mode == "canary_dryrun"
assert c.database_url
print("rollback_ok", c.ingress_mode, bool(c.database_url))
PY
'
```

可选增强回滚：如需停止 production canary workflow，可在 n8n 中将 `production-canary-events` active=false；但保留 active 也不会被公网触达，除非 ingress URL 指向它。

## 注意事项

- `docker compose up -d --force-recreate webhook-ingress` 在当前 compose 依赖设置下可能连带 recreate n8n/postgres；本轮验证服务已恢复 healthy。
- `WEBHOOK_DATABASE_URL` 目前只放在 `.env.webhook-ingress`，不要在命令输出中打印。
- 若后续要加 Linear comment canary action，应单独开 OPS-LINEAR-008，并默认关闭；本轮未启用。
