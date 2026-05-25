# OPS-LINEAR-006 修复验收报告

日期：2026-05-04

## 结论

PASS。node-22 Linear 单入口 canary dry-run 已完成验收：公网仅保留 `POST https://webhook.exa.edu.kg/webhook/events`，旧 `/webhooks/linear` 已 404 且 Linear 侧旧 shadow webhook 已删除；真实 Linear Issue created / Issue updated / Comment created 均进入 ingress、写入 Supabase raw/canonical/logs，并 dry-run 转发到 n8n，n8n `canonical-dryrun-events` 最新执行为 `success`。本轮未启用生产业务动作。

## 当前入口与隔离状态

| 项 | 结果 |
|----|------|
| `GET /webhook/events` | 405，只接受 POST |
| `POST /webhooks/linear` | 404 |
| `GET /` | 404 |
| `GET /rest/settings` | 404 |
| `GET /healthz` | 200 |
| ingress mode | `canary_dryrun` |
| n8n dry-run workflow | `canonical-dryrun-events` active/published |
| 生产 provider workflow | 未启用；`standard provider webhooks` inactive |

## Linear webhook 状态

| Webhook | 状态 |
|---------|------|
| active webhook `3cafb372-3aa1-4697-9ff4-0b1d6aaa7ce4` | URL `https://webhook.exa.edu.kg/webhook/events`，enabled `true`，team `JTO` |
| old shadow webhook `9e1edca6-1d2c-4f42-9a7c-07ddb5654d0d` | 已删除/不存在 |

说明：当前 `/webhook/events` 使用 node-22 `WEBHOOK_SECRET_LINEAR` / `LINEAR_WEBHOOK_SECRET` 注入到 ingress verifier。真实 Linear 事件能通过 HMAC 并返回 200，证明该 secret 与当前 active Linear webhook 匹配。

## n8n dry-run 修复

修复点：

- 将 `canonical-dryrun-events` 简化为 dry-run-only workflow。
- Webhook 使用 `responseMode=onReceived`，避免 Respond node/发布版本差异导致 execution 长期 running。
- n8n 环境 `EXECUTIONS_DATA_SAVE_ON_SUCCESS=all`，保证 success execution 可用于验收。
- ingress 的 `N8N_CANONICAL_WEBHOOK_URL` 指向内部 dry-run URL：`http://n8n:5678/webhook/canonical-dryrun-events/webhook/canonical-events`。

最新 n8n execution 证据：

```text
102|canonical-dryrun-events|success|webhook|2026-05-04 16:31:07.071+08|2026-05-04 16:31:07.08+08
101|canonical-dryrun-events|success|webhook|2026-05-04 16:31:05.25+08|2026-05-04 16:31:05.258+08
100|canonical-dryrun-events|success|webhook|2026-05-04 16:30:54.036+08|2026-05-04 16:30:54.043+08
99|canonical-dryrun-events|success|webhook|2026-05-04 16:30:45.458+08|2026-05-04 16:30:45.465+08
98|canonical-dryrun-events|success|webhook|2026-05-04 16:30:38.82+08|2026-05-04 16:30:38.83+08
```

历史 `running/error` 记录是修复前遗留，不再代表当前 workflow 行为。

## 真实 Linear 三类事件验收

临时 issue：

- Issue：`JTO-181`
- Issue ID：`803da538-2512-4115-b9c7-36d0380c36c1`
- URL：`https://linear.app/jtoom/issue/JTO-181/ops-linear-006-final-dry-run-validation-1777883430`
- 清理：已 archive，`archivedAt=2026-05-04T08:31:02.602Z`

Supabase canonical evidence：

```text
evt_7a8c3d09-fa10-47d2-9228-a52d8ab82f1c|Issue|create|issue|created|...|n8n_forwarded=1
evt_50204df8-66b7-4566-b715-f836a6d76ea2|Issue|update|issue|updated|...|n8n_forwarded=1
evt_4ce72e1f-9fc5-4220-b678-1b81e0d5b3d7|Comment|create|comment|created|...|n8n_forwarded=1
```

附加清理事件也正常 dry-run：

```text
evt_80c6f167-6e78-4d72-bce0-4e03f3062647|Issue|remove|issue|deleted|...|n8n_forwarded=1
evt_5caf3d07-71bf-49a5-867a-33f1e5565371|Comment|remove|comment|deleted|...|n8n_forwarded=1
```

raw/canonical/logs：

- `raw_rows` for `JTO-181` issue create/update/remove：3；Comment create/remove 另有 canonical rows。
- processing logs for issue rows include `store` and `n8n_dryrun`.
- `n8n_dryrun` log details include `{'status': 'success', 'route_mode': 'canary_dryrun'}`.

## 幂等验收

合成 signed replay 使用同一 `Linear-Delivery`：

```text
try1 code=200 body={"ok":true,"status":"accepted",...}
try2 code=200 body={"ok":true,"status":"duplicate_accepted",...same event_id...}
```

结果：duplicate 不重复创建 canonical event，不重复 forward 到 n8n dry-run。

## 日志脱敏验收

扫描 ingress 最近日志：

```text
redaction_ok
```

未发现：

- Linear secret
- DB URL
- DB password
- Authorization
- Linear-Signature 明文

## 本轮生产动作隔离

- 未启用 `standard provider webhooks`。
- 未把 canonical events 切到生产 provider workflow。
- n8n active workflows 中 dry-run workflow active；旧 provider fan-out workflow inactive。
- 本轮外部 Linear API 仅用于用户授权的临时 issue create/update/comment/archive 与旧 webhook delete；dry-run workflow 本身不调用 Linear/GitLab/Slack/通知。

## 注意事项

- ingress 容器必须保留 `WEBHOOK_DATABASE_URL`（当前使用 Supabase pooler IPv4 连接串）。直接 `db.<project>.supabase.co` 在 node-22 上解析到 IPv6 不通。
- 早期因错误 pooler 用户/密码触发过 Supabase pooler 临时 auth block，已改为正确用户 `postgres.<project-ref>` 后恢复。
- 修复前的 n8n `running/error` execution 可作为历史记录保留；后续验收以 execution `98+` 的 success 记录为准。
