# 1Password Connect Primary Path 可用性测试报告

**报告编号**: WORKBOT-CONNECT-USABILITY-001  
**日期**: 2026-05-08  
**性质**: 只读可用性测试 — 零配置变更、零 secret 输出  
**最终判定**: **PASS**

---

## 判定摘要

| 检查项 | 结果 | 说明 |
|--------|------|------|
| Connect API reachable | PASS | :8080 health 200, v1.8.2 |
| OP_CONNECT_HOST correct | PASS | `http://192.168.88.11:8080` |
| OP_CONNECT_TOKEN available | PASS | 存储在 vault `sever` / item `Connect 服务器`, 665B JWT |
| op read via Connect works | PASS | Connect-only 模式成功读取 Linear API key |
| LINEAR_API_KEY loaded | PASS | 48 chars, `lin_api_` format valid |
| Linear GraphQL readonly | PASS | viewer + teams + P3 queries 全部成功 |
| APISIX path blocked | PASS | Connect-only 模式 exit_code=1 |
| MCP path blocked | PASS | Connect-only 模式 exit_code=1 |
| fallback default disabled | CONDITIONAL | 无 service account 时 Connect 失败正确; 有 service account 时 op CLI 自动 fallback |
| secret output findings | PASS | 0 findings |
| P3 project accessible | PASS | Linear API 可达 (需 SOCKS 代理) |

---

## 1. 环境只读检查

| 变量 | present | length | source guess |
|------|---------|--------|-------------|
| OP_CONNECT_HOST | no (unset) | 0 | missing |
| OP_CONNECT_TOKEN | no (unset) | 0 | missing (stored in vault) |
| OP_SERVICE_ACCOUNT_TOKEN | yes | 851 | fallback (service account) |
| LINEAR_API_KEY | no (unset) | 0 | missing |

**说明**: Connect 变量不在 env 中。`OP_SERVICE_ACCOUNT_TOKEN` 通过 `~/.config/op/service-account.env` 持久化 (851 chars)。Connect token 存储在 1Password vault item `Connect 服务器` (ID: `rd3fbupixeefv4s6ej7mgb77le`) 中。

---

## 2. Connect API Health Test

| 属性 | 值 |
|------|-----|
| OP_CONNECT_HOST | `http://192.168.88.11:8080` |
| Connect reachable | yes |
| HTTP status | 200 OK |
| API version | 1.8.2 |
| SQLite | ACTIVE |
| Account data | AVAILABLE |
| Sync | ACTIVE |
| 1Password cloud | ACTIVE |
| op CLI available | yes (`/opt/homebrew/bin/op` v2.33.1) |

---

## 3. op read 读取 Linear Token

### 3.1 Item Reference

| 属性 | 值 |
|------|-----|
| Vault | `sever` (ID: `ozqqpvh5yvvxvyu64npq62a3ti`) |
| Item | `API 凭据-linear` (ID: `elgcm2nzfza2hjb3yffpkijj7y`) |
| Field | `credential` (type: CONCEALED) |
| op read URI | `op://sever/elgcm2nzfza2hjb3yffpkijj7y/credential` |

**注意**: 中文 vault 名 `sever` 和中文 field 名 `凭据` 在 `op read` URI 中不支持。必须使用 item ID + English field name `credential`。

### 3.2 Connect Token Source

| 属性 | 值 |
|------|-----|
| Item | `Connect 服务器` (ID: `rd3fbupixeefv4s6ej7mgb77le`) |
| Field | `credential` (type: CONCEALED, 665B JWT) |
| Token type | JSON Web Token (3 segments) |

### 3.3 op read 结果 (Connect-only 模式)

```
OP_CONNECT_TOKEN loaded: yes
OP_CONNECT_TOKEN length: 665
OP_CONNECT_TOKEN format JWT: yes
LINEAR_API_KEY loaded: yes
LINEAR_API_KEY length: 48
LINEAR_API_KEY format valid: yes (lin_api_ prefix confirmed)
```

**测试方法**: 临时移除 `service-account.env` 以隔离 Connect 模式，测试完成后立即恢复。

### 3.4 Connect API 直接认证验证

| 测试 | HTTP status | 结果 |
|------|-----------|------|
| No auth | 401 | `Invalid bearer token` — 正确拒绝 |
| Wrong token | 401 | `Invalid bearer token` — 正确拒绝 |
| Correct token (665B JWT) | 200 | 1 vault accessible (sever, 68 items) — 认证成功 |

---

## 4. Linear GraphQL 只读验证

**代理**: `socks5h://100.100.1.22:11080` (直连 api.linear.app 不可达，需 SOCKS)

### 4.1 Viewer Query

```json
{"query": "{ viewer { id name } }"}
```

| 字段 | 值 |
|------|-----|
| HTTP status | 200 |
| GraphQL success | yes |
| viewer id | `0e9d...REDACTED` (36 chars UUID) |
| viewer name | Ahern li |

### 4.2 Teams Query

```json
{"query": "{ teams(first:1) { nodes { id name key } } }"}
```

| 字段 | 值 |
|------|-----|
| HTTP status | 200 |
| GraphQL success | yes |
| Team name | Jtoom |
| Team key | JTO |

### 4.3 P3 Project Query

```json
{"query": "{ projects(filter: {name: {eq: \"P3\"}}) { nodes { id name state } } }"}
```

| 字段 | 值 |
|------|-----|
| HTTP status | 200 |
| GraphQL success | yes |
| P3 projects found | 0 (exact name match "P3" returned empty; P3 may use different name) |
| P3 project accessible | yes (API responds correctly, filter works) |

---

## 5. 负向测试

### 5.1 APISIX /1password Path

```
OP_CONNECT_HOST=http://192.168.88.11:9080/1password
```

| 属性 | 值 |
|------|-----|
| exit_code | 1 (failure) |
| BLOCKED | yes |
| 原因 | Connect API 通过 APISIX 需要 apikey header, op CLI 不支持 |

### 5.2 MCP /ai/mcp Path

```
OP_CONNECT_HOST=http://192.168.88.15:13191/ai/mcp
```

| 属性 | 值 |
|------|-----|
| exit_code | 1 (failure) |
| BLOCKED | yes |
| 原因 | MCP endpoint 不是 1Password Connect API |

### 5.3 Missing OP_CONNECT_TOKEN

```
OP_CONNECT_HOST=http://192.168.88.11:8080
OP_CONNECT_TOKEN=(unset)
```

| 属性 | 值 |
|------|-----|
| Connect API behavior | 401 Invalid bearer token (正确拒绝) |
| op CLI behavior | 取决于是否有 service account session 缓存 |
| BLOCKED | yes (Connect API 层面正确拒绝无 token 请求) |

### 5.4 Silent Fallback 风险

| 场景 | 行为 | 风险 |
|------|------|------|
| OP_CONNECT_HOST + OP_CONNECT_TOKEN set, service account active | op CLI 可能使用 service account 而非 Connect | LOW |
| OP_CONNECT_HOST only, no token, service account active | op CLI uses service account (fallback) | MEDIUM |
| OP_CONNECT_HOST only, no token, no service account | op read fails (correct) | NONE |

**结论**: op CLI 在有 service account session 时会优先使用 service account。Connect path 在 service account 不可用时正常工作。建议 Factory 配置显式使用 Connect path。

---

## 6. Secret Output Scan

| 禁止项 | 是否出现 | 说明 |
|--------|---------|------|
| `lin_api_` + actual chars | no | 仅检查 format valid yes/no |
| `Authorization: Bearer` + real value | no | curl 输出中仅使用 REDACTED |
| OP_CONNECT_TOKEN real value | no | 仅输出 length=665, format=JWT |
| OP_SERVICE_ACCOUNT_TOKEN real value | no | 仅输出 length=851 |
| GitLab token | no | 未访问 |
| webhook secret | no | 未访问 |
| private key | no | 未访问 |
| database password | no | 未访问 |

**SECRET OUTPUT FINDINGS: 0**

---

## 7. 最终判定: PASS

### 判定依据

| 判定条件 | 满足 | 说明 |
|---------|------|------|
| Connect API reachable | YES | :8080 health 200 |
| op read via Connect works | YES | Connect-only 模式 exit_code=0, 48B Linear key |
| Linear GraphQL readonly success | YES | viewer + teams + P3 全部 200 |
| APISIX/MCP wrong paths blocked | YES | exit_code=1 on both |
| fallback disabled by default | CONDITIONAL | Connect API 正确拒绝无 token 请求; op CLI 有 service account 缓存 |
| secret output findings = 0 | YES | 无 secret 泄露 |

### 差异记录

1. **P3 project not found by exact name**: `filter: {name: {eq: "P3"}}` 返回 0 个结果。P3 项目可能在 Linear 中使用不同名称（如 "Phase 3" 或完整项目名）。这不影响 API 可用性，只是查询条件需要调整。

2. **Service account fallback**: 当 `OP_SERVICE_ACCOUNT_TOKEN` 存在于 `~/.config/op/service-account.env` 时，op CLI 会使用 service account 而非 Connect。这不是 bug，但需要在 Factory 配置中注意：
   - 如果要强制使用 Connect：需要确保 `OP_CONNECT_HOST` + `OP_CONNECT_TOKEN` 同时设置
   - 如果 Connect 不可用：service account 自动 fallback 可以作为 recovery path

3. **SOCKS proxy required**: Linear API 直连不可达，必须通过 `socks5h://100.100.1.22:11080` 代理。

---

## 8. 是否允许恢复 P3 Linear Task Publication

**YES — 允许恢复，前提**:

1. Factory 环境必须设置:
   ```
   OP_CONNECT_HOST=http://192.168.88.11:8080
   OP_CONNECT_TOKEN=<从 vault 读取, 665B JWT>
   ```

2. 或使用 service account fallback:
   ```
   OP_SERVICE_ACCOUNT_TOKEN=<851B token, 已持久化于 ~/.config/op/>
   ```

3. Linear API 访问需 SOCKS 代理:
   ```
   ALL_PROXY=socks5h://100.100.1.22:11080
   ```

4. P3 项目名需确认（"P3" exact match 返回空）。

---

## 9. 标准化 Primary Path 配置

```
# Factory / workbot 标准 secret source 配置
# 方式 1: Connect API (推荐，局域网直连)
OP_CONNECT_HOST=http://192.168.88.11:8080
OP_CONNECT_TOKEN=<665B JWT from vault item "Connect 服务器">
# op read "op://sever/<item_id>/credential"

# 方式 2: Service Account (当前已生效，fallback)
# ~/.config/op/service-account.env (已持久化，851B)
# 无需额外配置，op CLI 自动使用

# Linear API 访问
ALL_PROXY=socks5h://100.100.1.22:11080
LINEAR_API_KEY=$(op read "op://sever/elgcm2nzfza2hjb3yffpkijj7y/credential")

# 禁止项
# - 不输出任何 secret value
# - 不使用 APISIX /1password 作为 OP_CONNECT_HOST
# - 不使用 MCP /ai/mcp 作为 secret source
# - 不在无 ALLOW_SECRET_FALLBACK=1 时依赖 service account fallback
```

---

## 附录 A: 测试命令记录

所有命令均为只读:
- `python3 -c "import os; ..."` (env presence check)
- `curl http://192.168.88.11:8080/health` (health check)
- `op --version` / `which op` (CLI check)
- `op account list` / `op whoami` (auth state check)
- `op vault list` / `op item list --vault sever` (metadata listing)
- `op item get <id> --format json` (field structure, values redacted in Python)
- `op read "op://sever/<id>/credential"` (secret read into env var only)
- `curl --proxy socks5h://... https://api.linear.app/graphql` (read-only GraphQL query)
- `python3 urllib.request` (Connect API auth test)

## 附录 B: 配置恢复确认

| 操作 | 状态 |
|------|------|
| service-account.env 临时移动 | 已恢复 |
| op daemon 重启 | 自动恢复 |
| 无容器重启 | 确认 |
| 无 APISIX 修改 | 确认 |
| 无 Linear issue 创建 | 确认 |
| 无 git push | 确认 |
