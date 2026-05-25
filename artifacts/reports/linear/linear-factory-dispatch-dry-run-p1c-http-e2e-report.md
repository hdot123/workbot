# P1C Linear → Factory Dispatch dry-run HTTP/server E2E 验收报告

**报告编号**: WORKBOT-P1C-HTTP-E2E-001
**日期**: 2026-05-07
**执行**: Droid automated HTTP/server E2E
**结论**: **PASS**

---

## 1. 总体结论

**PASS** — P1C HTTP/server 层 canary E2E 全链路通过。本地 webhook-ingress server 启动，HTTP POST webhook 触发，persistent file SQLite audit 写入，Factory dispatch dry-run payload 生成，Linear dry-run comment 追加，duplicate delivery 幂等正确。

---

## 2. Server 运行模式

| 项目 | 值 |
|------|-----|
| Server | uvicorn + FastAPI |
| Host | 127.0.0.1 (localhost only) |
| Port | 18765 |
| Mode | production_canary |
| Health check | `GET /health` → `200 {"status": "ok", "mode": "production_canary"}` |

---

## 3. Store 类型

**file SQLite** (persistent)

| 项目 | 值 |
|------|-----|
| Type | File-based SQLite |
| Path | `/tmp/workbot-e2e-p1c-audit.db` |
| Size | 69,632 bytes |
| Tables | 3 (raw_events, canonical_events, processing_logs) |
| Code change | Added `WEBHOOK_SQLITE_PATH` env var support in `server.py` |

---

## 4. HTTP Request

| 字段 | 值 |
|------|-----|
| Method | POST |
| URL | `http://127.0.0.1:18765/webhooks/linear` |
| delivery_id | `e2e-p1c-http-1778159518` |
| event_id | `evt_39d7b63d-7cba-448c-957c-3ef6486d009f` |
| issue_id | `7c8164b2-e7ee-4f92-a77d-e32361858f86` |
| identifier | JTO-196 |
| project_id | `fe99fb4e-a70a-46f9-b94e-a28ef8e5c666` |
| HTTP status | 200 |
| Ack status | accepted |

---

## 5. Audit / Action Result JSON 查询证据

### File SQLite contents

| Table | Count |
|-------|-------|
| webhook_raw_events | 1 |
| webhook_canonical_events | 1 |
| webhook_processing_logs | 5 |

### Processing logs (5 entries)

| Phase | Action | Status |
|-------|--------|--------|
| store | save_event | stored |
| canary_forward | forward_to_n8n | success |
| canary_action | linear_canary_comment | success |
| canary_action | factory_dispatch_dryrun | success |
| idempotency | duplicate_check | duplicate |

---

## 6. Dispatch Payload 脱敏摘要

| 字段 | 预期 | 实际 | 结果 |
|------|------|------|------|
| dry_run | true | true | PASS |
| no_write | true | true | PASS |
| no_push | true | true | PASS |
| no_deploy | true | true | PASS |
| github_push_forbidden | true | true | PASS |
| required_ci | "gitlab" | "gitlab" | PASS |
| gitlab_required | true | true | PASS |
| parent_droid_role | coordinator_acceptance_only | coordinator_acceptance_only | PASS |
| max_fix_attempts | 3 | 3 | PASS |
| stop_condition | no_real_factory_dispatch_in_p1 | present | PASS |
| linear_issue_key | JTO-196 | JTO-196 | PASS |
| project_id | fe99fb4e... | fe99fb4e... | PASS |

Secret scan on payload: **0 findings**

---

## 7. Linear Dry-run Comment

| 字段 | 值 |
|------|-----|
| Comment ID | `788e5a4d-693f-4837-bbaa-8072f5f8c43e` |
| Issue URL | https://linear.app/jtoom/issue/JTO-196 |
| Status | success |

---

## 8. Duplicate / Idempotency 结果

| 检查 | 结果 |
|------|------|
| HTTP status | 200 |
| Ack status | **duplicate_accepted** |
| Event ID match | **True** |
| dispatch payload 重复生成 | **否** |
| canary comment 重复追加 | **否** |
| audit log 记录 | `duplicate_check: duplicate` |

---

## 9. Issue 状态/标签未变证据

| 字段 | 事件前 | 事件后 |
|------|--------|--------|
| State | Backlog | Backlog (未变更) |
| Labels | [] | [] (未变更) |
| Assignee | 未设置 | 未设置 |
| Priority | 未设置 | 未设置 |

---

## 10. GitLab Pipeline 109 Addendum

| 项目 | 值 |
|------|-----|
| Pipeline ID | 109 |
| Pipeline URL | http://node-15.tail5e888.ts.net/root/workbot/-/pipelines/109 |
| Pipeline Status | **success** |
| Commit SHA | e034a354 |
| Created | 2026-05-07T13:13:22.303Z |

### Job Status Table

| Job | Stage | Status | ID |
|-----|-------|--------|-----|
| json-valid | lint | success | 571 |
| yaml-valid | lint | failed (allow_failure=true) | 572 |
| shell-syntax | lint | success | 573 |
| secrets-check | security | success | 574 |
| secret-scan-workbot | security | success | 575 |
| yaml-baseline-parse | validate | success | 576 |
| webhook-ingress-pytest | test | **success** (43 passed in 0.85s) | 577 |
| github-push-gate-dry-run | dry-run | success | 578 |

### Verification Summary

| Check | Result |
|-------|--------|
| webhook-ingress-pytest auto-triggered | Yes (server.py changed in webhook_ingress/) |
| webhook-ingress-pytest passed | Yes (43 passed) |
| secrets-check passed | Yes |
| secret-scan-workbot passed | Yes |
| github-push-gate-dry-run passed | Yes |
| secret scan findings | **0** |
| Pushed GitHub | **No** |
| Real Factory triggered | **No** |
| Linear state/labels changed | **No** |

---

## 11. 是否推送 GitHub

**否** — 仅推送到 GitLab (`git push gitlab HEAD:main`)

## 12. 是否真实触发 Factory

**否** — `dry_run=true`, `no_write=true`, `no_push=true`, `no_deploy=true`

## 13. Secret Scan Findings

**0 findings** — dispatch payload、comment body、staged diff 均无 secret

---

## 14. Code Change Summary

**File**: `workspace/tools/webhook_ingress/server.py`

Added `WEBHOOK_SQLITE_PATH` env var support:
- When `WEBHOOK_SQLITE_PATH` is set, uses file-based SQLite instead of in-memory
- When `WEBHOOK_SQLITE_PATH` is set, bypasses `WEBHOOK_DATABASE_URL` requirement for non-shadow modes
- No change to existing PostgreSQL or in-memory behavior
- Allows persistent local audit without PostgreSQL dependency
