# Rollback Plan: safe-1password-mcp Deployment on ce-01

> **Document ID**: OPS-SAFE1PW-ROLLBACK-001  
> **Created**: 2026-05-08  
> **Server**: ce-01 (192.168.88.15)  
> **Status**: Active  
> **Risk Level**: Low (no local data storage, both containers coexist)

---

## 1. Architecture Summary

### Old Server (1password-connect)

| Property | Value |
|----------|-------|
| Container | `1password-connect` |
| Port | `8000` |
| SSE Path | `/1password-connect` |
| SSE URL | `https://192.168.88.15:8000/1password-connect` (or `http` depending on proxy) |
| Image | `supercorp/supergateway:latest` |
| MCP Entry | `/opt/mcp-servers/1password-connect/index.js` |
| Compose | `/opt/1panel/mcp/1password-connect/docker-compose.yml` |
| Env File | `/opt/1panel/mcp/1password-connect/.env` |
| Network | `1panel-network` |
| Tools | `op_list_items` (full JSON), `op_get_item` (full secrets) |

### New Server (safe-1password-mcp)

| Property | Value |
|----------|-------|
| Container | `safe-1password-mcp` |
| Port | `8001` |
| SSE Path | `/mcp/1password` |
| SSE URL | `https://192.168.88.15:8001/mcp/1password` (or `http` depending on proxy) |
| Image | `node:20-alpine` (bundled code) |
| MCP Entry | `/opt/mcp-servers/safe-1password-mcp/dist/index.js` |
| Compose | `/opt/mcp-servers/safe-1password-mcp/docker-compose.yml` |
| Env File | `/opt/mcp-servers/safe-1password-mcp/.env` |
| Network | `1panel-network` |
| Health | `GET http://127.0.0.1:8001/health` (30s interval) |
| Tools | `op_list_vaults`, `op_search_items`, `op_get_item`, `op_read_secret` |

---

## 2. Rollback Trigger Conditions

Initiate rollback if **any** of the following occur after cutover:

| # | Condition | Severity |
|---|-----------|----------|
| 1 | New server health check fails (`GET /health` returns non-200 or times out) | P0 |
| 2 | Factory cannot connect to new MCP endpoint (`https://192.168.88.15:8001/mcp/1password`) | P0 |
| 3 | MCP tool calls return errors (500, timeout, connection refused) consistently | P1 |
| 4 | Security vulnerability discovered in new server code | P0 |
| 5 | New server exposes secret data that should be redacted | P0 |
| 6 | 1Password Connect API upstream (`192.168.88.11:9080`) becomes unreachable (affects both servers — see Emergency Recovery) | P2 |
| 7 | Container crashes repeatedly (OOM, segfault) | P1 |

---

## 3. Rollback Steps (New → Old)

**Goal**: Restore Factory to use the old `1password-connect` server.

**Estimated Time**: < 2 minutes

### Step 3.1 — Verify old server is available

```bash
# SSH to ce-01 and check if old container exists and can start
ssh ce-01 'docker ps -a --filter name=1password-connect --format "{{.Names}} {{.Status}}"'
```

If the old container was stopped (not removed), proceed. If removed, see Section 6.

### Step 3.2 — Stop the new server

```bash
ssh ce-01 'cd /opt/mcp-servers/safe-1password-mcp && docker compose down'
```

Verify it stopped:

```bash
ssh ce-01 'docker ps --filter name=safe-1password-mcp --format "{{.Names}} {{.Status}}"'
# Should return empty
```

### Step 3.3 — Start the old server

```bash
ssh ce-01 'cd /opt/1panel/mcp/1password-connect && docker compose up -d'
```

Wait for it to be ready:

```bash
ssh ce-01 'docker ps --filter name=1password-connect --format "{{.Names}} {{.Status}}"'
# Should show "Up"
```

### Step 3.4 — Verify old server responds

```bash
# Health / connectivity check on old SSE endpoint
ssh ce-01 'curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8000/1password-connect'
# Expected: 200 or appropriate SSE handshake response
```

### Step 3.5 — Restore Factory MCP configuration

Update Factory MCP config to point back to the old endpoint:

| Field | Rollback Value |
|-------|---------------|
| URL | `https://192.168.88.15:8000/1password-connect/sse` (or the original configured URL) |

This is done in the Factory application settings (MCP integrations). No server-side change needed.

### Step 3.6 — Verify Factory connection

In Factory, invoke any 1Password tool (e.g., `op_list_items` on old server) and confirm it returns data.

### Step 3.7 — Log the rollback

```bash
# Record rollback event
ssh ce-01 'echo "[$(date -Iseconds)] ROLLBACK: safe-1password-mcp → 1password-connect executed" >> /opt/mcp-servers/safe-1password-mcp/rollback.log'
```

---

## 4. Forward Migration Steps (Old → New)

**Goal**: Cutover Factory from old `1password-connect` to new `safe-1password-mcp`.

**Estimated Time**: < 5 minutes

### Step 4.1 — Pre-flight: Verify new server is running and healthy

```bash
# Check container is up
ssh ce-01 'docker ps --filter name=safe-1password-mcp --format "{{.Names}} {{.Status}}"'

# Check health endpoint
ssh ce-01 'curl -sf http://127.0.0.1:8001/health'
# Expected: 200 OK with JSON status

# Test SSE endpoint responds
ssh ce-01 'curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8001/mcp/1password'
# Expected: 200 or appropriate SSE handshake response
```

### Step 4.2 — Pre-flight: Functional test of new server tools

Use a direct MCP client (or curl SSE handshake) to verify the new tools work:

```bash
# Verify tool list is available via MCP protocol
# (This requires an MCP client; if using Factory, test via a temporary MCP config)
```

Confirm these tools are exposed:
- `op_list_vaults`
- `op_search_items`
- `op_get_item`
- `op_read_secret`

### Step 4.3 — Update Factory MCP URL

In Factory application settings → MCP integrations, update:

| Field | New Value |
|-------|-----------|
| URL | `https://192.168.88.15:8001/mcp/1password/sse` |

Save the configuration.

### Step 4.4 — Verify Factory connection to new server

In Factory, invoke each new tool and confirm responses:
1. `op_list_vaults` → returns vault list
2. `op_search_items` → returns search results (metadata only)
3. `op_get_item` → returns item metadata (no full secret dump)
4. `op_read_secret` → returns single requested field

### Step 4.5 — Stop old server (keep configured for rollback)

```bash
ssh ce-01 'cd /opt/1panel/mcp/1password-connect && docker compose stop'
```

**Do NOT** `docker compose down` or remove the old container. Keep it stopped but ready for instant restart if rollback is needed.

Verify it's stopped (not removed):

```bash
ssh ce-01 'docker ps -a --filter name=1password-connect --format "{{.Names}} {{.Status}}"'
# Should show "Exited" — NOT absent
```

### Step 4.6 — Final verification

```bash
# New server is still healthy
ssh ce-01 'curl -sf http://127.0.0.1:8001/health'

# Old server is stopped but present
ssh ce-01 'docker ps -a --filter name=1password-connect --format "{{.Names}} {{.Status}}"'
```

In Factory, run one more tool invocation to confirm end-to-end functionality.

### Step 4.7 — Log the migration

```bash
ssh ce-01 'echo "[$(date -Iseconds)] MIGRATION: 1password-connect → safe-1password-mcp completed successfully" >> /opt/mcp-servers/safe-1password-mcp/migration.log'
```

---

## 5. Emergency Recovery

### Scenario A: Both servers are down

```bash
# Check status of both containers
ssh ce-01 'docker ps -a --filter name=1password-connect --filter name=safe-1password-mcp --format "{{.Names}} {{.Status}}"'
```

**Recovery priority**: Start whichever container can start first.

```bash
# Try old server first (simpler, proven)
ssh ce-01 'cd /opt/1panel/mcp/1password-connect && docker compose up -d'

# If old server fails, try new server
ssh ce-01 'cd /opt/mcp-servers/safe-1password-mcp && docker compose up -d'
```

### Scenario B: 1Password Connect API upstream is down (192.168.88.11:9080)

Both MCP servers depend on the same upstream. If it's down, **neither server can serve requests**.

```bash
# Verify upstream reachability from ce-01
ssh ce-01 'curl -sf -o /dev/null -w "%{http_code}" http://192.168.88.11:9080/1password/v1/vaults -H "Authorization: Bearer $OP_API_KEY"'
```

**Action**: This is an infrastructure issue, not a deployment issue. Escalate to the 1Password Connect host administrator. Both MCP servers will recover automatically when the upstream returns.

### Scenario C: Docker daemon is down on ce-01

```bash
ssh ce-01 'sudo systemctl start docker'
# Then restart whichever MCP server is the active one
```

### Scenario D: Port conflict

If port 8000 or 8001 is occupied by another process:

```bash
# Find what's using the port
ssh ce-01 'ss -tlnp | grep -E "800[01]"'

# Stop the conflicting container or process, then restart the MCP server
```

---

## 6. Data Safety Statement

**There is zero risk of data loss during rollback or migration.**

- The MCP servers are **stateless proxies** — they relay requests to the 1Password Connect API at `192.168.88.11:9080`.
- No 1Password vault data, secrets, or credentials are stored on ce-01.
- The `.env` files contain only the `OP_API_KEY` (a Connect API token) and the `OP_CONNECT_HOST` URL — no vault data.
- Rolling back simply changes which proxy container handles requests. The upstream data source (1Password Connect on 192.168.88.11) is untouched.
- The only "state" is the container runtime configuration (env vars, compose files), all of which are preserved on disk regardless of container state.

---

## 7. Quick Reference: Verification Commands

### Check which server is active

```bash
# One-liner status check
ssh ce-01 'echo "=== Old (1password-connect) ===" && docker ps -a --filter name=1password-connect --format "{{.Names}} {{.Status}}" && echo "=== New (safe-1password-mcp) ===" && docker ps -a --filter name=safe-1password-mcp --format "{{.Names}} {{.Status}}"'
```

### Health checks

```bash
# Old server health (SSE endpoint)
ssh ce-01 'curl -s -o /dev/null -w "HTTP %{http_code}\n" http://127.0.0.1:8000/1password-connect'

# New server health (dedicated endpoint)
ssh ce-01 'curl -sf http://127.0.0.1:8001/health && echo "OK" || echo "FAIL"'
```

### Connectivity from Factory (run locally)

```bash
# Test old endpoint
curl -s -o /dev/null -w "HTTP %{http_code}\n" http://192.168.88.15:8000/1password-connect

# Test new endpoint
curl -s -o /dev/null -w "HTTP %{http_code}\n" http://192.168.88.15:8001/mcp/1password
```

### Container logs (for debugging)

```bash
# Old server logs
ssh ce-01 'docker logs 1password-connect --tail 50'

# New server logs
ssh ce-01 'docker logs safe-1password-mcp --tail 50'
```

### Quick rollback (copy-paste)

```bash
# Full rollback in one sequence:
ssh ce-01 'cd /opt/mcp-servers/safe-1password-mcp && docker compose down && cd /opt/1panel/mcp/1password-connect && docker compose up -d && sleep 2 && curl -s -o /dev/null -w "Old server status: HTTP %{http_code}\n" http://127.0.0.1:8000/1password-connect'
# Then update Factory MCP URL to old endpoint
```

---

## 8. Key File Locations

| File | Path on ce-01 |
|------|---------------|
| Old compose file | `/opt/1panel/mcp/1password-connect/docker-compose.yml` |
| Old env file | `/opt/1panel/mcp/1password-connect/.env` |
| Old MCP code | `/opt/mcp-servers/1password-connect/index.js` |
| New compose file | `/opt/mcp-servers/safe-1password-mcp/docker-compose.yml` |
| New env file | `/opt/mcp-servers/safe-1password-mcp/.env` |
| New MCP code | `/opt/mcp-servers/safe-1password-mcp/dist/index.js` |
| Backup (local) | `/Users/busiji/workbot/artifacts/1password-connect-docker-compose.yml.bak` |

---

## 9. Rollback Decision Checklist

Before initiating rollback, confirm:

- [ ] New server has confirmed issues (not a transient network blip)
- [ ] Issue is not caused by 1Password Connect upstream being down (check `http://192.168.88.11:9080`)
- [ ] Old container still exists on disk (`docker ps -a | grep 1password-connect`)
- [ ] You have access to Factory MCP settings to update the URL
- [ ] You have SSH access to ce-01 (192.168.88.15)

If all checked, proceed with Section 3.
