# Cloudflare Tunnel Path Control — Security Hardening Analysis

> **Date**: 2026-05-09
> **Scope**: cloudflared ingress path-level allowlist for `webhook.exa.edu.kg`
> **Node**: node-22 (43.167.177.86)
> **Risk Level**: Medium (defense-in-depth improvement, not a critical vulnerability)

---

## 1. Current Risk Assessment

### 1.1 Current Architecture (Verified from Evidence)

```
Internet → Cloudflare → cloudflared (node-22)
  → localhost:5678 (Docker port map to nginx:8080)
    → nginx (n8n-webhook-gateway container)
      → /healthz          → n8n:5678/healthz
      → /webhook/events   → webhook-ingress-shadow:8000/webhooks/linear
      → /* (catch-all)    → 404
```

### 1.2 Current cloudflared config.yml (Before)

```yaml
tunnel: <tunnel-id>
credentials-file: /root/.cloudflared/<tunnel-id>.json

ingress:
  - hostname: webhook.exa.edu.kg
    service: http://127.0.0.1:5678
  - service: http_status:404
```

### 1.3 Risk Analysis

| # | Risk | Severity | Current Mitigation | Residual Risk |
|---|------|----------|-------------------|---------------|
| R1 | **cloudflared forwards ALL paths** on the hostname to nginx | **Medium** | nginx catch-all returns 404 | If nginx is misconfigured or reloaded with errors, all paths may hit n8n directly |
| R2 | **nginx catch-all returns 404, not 403 or 444** | **Low** | 404 reveals server existence but not content | Attacker can enumerate paths and confirm server presence |
| R3 | **No path-level filtering at cloudflared layer** | **Medium** | nginx provides single layer of path control | Single point of failure; if nginx config breaks, all paths reach backend services |
| R4 | **n8n Web UI potentially accessible** if nginx fails open | **Medium** | nginx `/` returns 404; n8n bound to 127.0.0.1 | If nginx is bypassed or misconfigured, n8n admin UI is exposed to the internet |
| R5 | **No rate limiting at tunnel layer** | **Low** | None at cloudflared level | Abuse/spam of `/webhook/events` could overwhelm webhook-ingress |

**Key Finding**: The current architecture relies on a **single defense layer** (nginx) for path control. The cloudflared tunnel forwards everything to nginx without any pre-filtering. If nginx configuration has an error (failed reload, syntax error causing fallback), the catch-all `location /` might not protect as expected.

**Overall Risk**: **Medium** — not immediately exploitable due to nginx 404 catch-all, but violates defense-in-depth principle. Path-level control at cloudflared layer provides a second independent barrier.

---

## 2. Path-Level Allowlist Proposal

### 2.1 Active Public Routes (from routes.yaml + nginx config)

| Public Path | Method | Backend | Purpose |
|-------------|--------|---------|---------|
| `/healthz` | GET | n8n:5678/healthz | Health check |
| `/webhook/events` | POST | webhook-ingress-shadow:8000/webhooks/linear | Linear webhook (HMAC verified) |

### 2.2 Future/Planned Routes (from routes.yaml, enabled but no nginx route yet)

| Public Path | Backend | Status |
|-------------|---------|--------|
| `/webhooks/factory` | webhook-ingress:8000/webhooks/factory | Factory provider enabled in routes.yaml, no nginx location yet |

### 2.3 Disabled Routes (from routes.yaml, should NOT be accessible)

- `/webhooks/github` — disabled
- `/webhooks/slack` — disabled
- `/webhooks/posthog` — disabled
- `/webhooks/pagerduty` — disabled
- `/webhooks/uptime-kuma` — disabled

### 2.4 cloudflared config.yml — Before / After

#### Before (Current)

```yaml
tunnel: <tunnel-id>
credentials-file: /root/.cloudflared/<tunnel-id>.json

ingress:
  # All paths on webhook.exa.edu.kg → nginx (single path control layer)
  - hostname: webhook.exa.edu.kg
    service: http://127.0.0.1:5678
  # Non-matching hostnames → 404
  - service: http_status:404
```

#### After (Path-Level Allowlist)

```yaml
tunnel: <tunnel-id>
credentials-file: /root/.cloudflared/<tunnel-id>.json

ingress:
  # === Path-level allowlist: only explicitly permitted paths reach nginx ===

  # Health check (GET)
  - hostname: webhook.exa.edu.kg
    path: ^/healthz$
    service: http://127.0.0.1:5678

  # Linear webhook entry point (POST, HMAC verified by webhook-ingress)
  - hostname: webhook.exa.edu.kg
    path: ^/webhook/events$
    service: http://127.0.0.1:5678

  # Factory webhook entry point (POST, HMAC verified by webhook-ingress)
  # NOTE: Uncomment when Factory webhook is activated in nginx config
  # - hostname: webhook.exa.edu.kg
  #   path: ^/webhooks/factory$
  #   service: http://127.0.0.1:5678

  # === Deny all other paths ===
  # Any unmatched path on webhook.exa.edu.kg → 403 Forbidden
  - hostname: webhook.exa.edu.kg
    service: http_status:403

  # Any unmatched hostname → 404
  - service: http_status:404
```

**Key Changes**:
1. Only `/healthz` and `/webhook/events` reach nginx — all other paths are rejected at the tunnel layer with **403 Forbidden**
2. Factory webhook path is commented out (not yet active in nginx); uncomment when ready
3. Unmatched paths on `webhook.exa.edu.kg` return **403** (not 404) — explicitly signals "denied" rather than "not found"
4. The final catch-all `http_status:404` handles any other hostname reaching this tunnel

### 2.5 Security Improvement Summary

| Aspect | Before | After |
|--------|--------|-------|
| Path control layers | 1 (nginx only) | 2 (cloudflared + nginx) |
| Unauthorized paths | 404 (nginx) | 403 (cloudflared, never reaches nginx) |
| `/admin`, `/api`, etc. | Reaches nginx → 404 | Blocked at tunnel → 403 |
| n8n Web UI exposure risk | If nginx fails, exposed | cloudflared blocks non-allowlisted paths independently |
| Attack surface | Full hostname forwarded | Only 2 paths forwarded |

---

## 3. Backup Steps

```bash
# SSH to node-22
ssh root@43.167.177.86

# Step 1: Backup current cloudflared config
cp /etc/cloudflared/config.yml /etc/cloudflared/config.yml.bak.$(date +%Y%m%d-%H%M%S)
# Or if config is at a different path:
# cp /root/.cloudflared/config.yml /root/.cloudflared/config.yml.bak.$(date +%Y%m%d-%H%M%S)

# Step 2: Verify backup exists
ls -la /etc/cloudflared/config.yml*

# Step 3: Backup current nginx gateway config (defense-in-depth)
docker exec n8n-webhook-gateway cat /etc/nginx/conf.d/default.conf > /opt/n8n-linear/nginx/webhook-gateway.conf.bak.$(date +%Y%m%d-%H%M%S)

# Step 4: Record current cloudflared service status
systemctl status cloudflared > /tmp/cloudflared-status-before.txt 2>&1
```

---

## 4. Rollback Steps

```bash
# If the new config causes issues:

# Step 1: Restore cloudflared config from backup
cp /etc/cloudflared/config.yml.bak.YYYYMMDD-HHMMSS /etc/cloudflared/config.yml

# Step 2: Restart cloudflared service
systemctl restart cloudflared

# Step 3: Verify service is running
systemctl status cloudflared

# Step 4: Verify tunnel connectivity
cloudflared tunnel info <tunnel-name>

# Step 5: Verify webhook endpoint still works
curl -s -o /dev/null -w '%{http_code}' https://webhook.exa.edu.kg/healthz
# Expected: 200

# Step 6: If cloudflared fails to start, check config syntax
cloudflared tunnel ingress validate
```

---

## 5. Verification Steps

Execute in order after applying the new config and restarting cloudflared:

### 5.1 Allowed Paths (Should Succeed)

```bash
# Test 1: Health check — should return 200
curl -s -o /dev/null -w '%{http_code}\n' https://webhook.exa.edu.kg/healthz
# Expected: 200

# Test 2: Webhook endpoint — should return 401 (empty/invalid signature)
curl -s -o /dev/null -w '%{http_code}\n' -X POST https://webhook.exa.edu.kg/webhook/events \
  -H "Content-Type: application/json" \
  -d '{"test": true}'
# Expected: 401 (HMAC signature verification failure = ingress is working)
```

### 5.2 Denied Paths (Should Return 403)

```bash
# Test 3: Random path — should return 403 (blocked at cloudflared)
curl -s -o /dev/null -w '%{http_code}\n' https://webhook.exa.edu.kg/random-path
# Expected: 403

# Test 4: Admin path — should return 403
curl -s -o /dev/null -w '%{http_code}\n' https://webhook.exa.edu.kg/admin
# Expected: 403

# Test 5: API path — should return 403
curl -s -o /dev/null -w '%{http_code}\n' https://webhook.exa.edu.kg/api
# Expected: 403

# Test 6: n8n Web UI path — should return 403
curl -s -o /dev/null -w '%{http_code}\n' https://webhook.exa.edu.kg/
# Expected: 403

# Test 7: Disabled provider path — should return 403
curl -s -o /dev/null -w '%{http_code}\n' https://webhook.exa.edu.kg/webhooks/github
# Expected: 403

# Test 8: Path traversal attempt — should return 403
curl -s -o /dev/null -w '%{http_code}\n' https://webhook.exa.edu.kg/webhook/events/../../admin
# Expected: 403
```

### 5.3 Full Verification Script

```bash
#!/bin/bash
echo "=== Cloudflare Tunnel Path Control Verification ==="
echo ""

PASS=0
FAIL=0

check() {
  local desc="$1" url="$2" method="$3" expected="$4"
  local actual
  if [ "$method" = "POST" ]; then
    actual=$(curl -s -o /dev/null -w '%{http_code}' -X POST "$url" -H "Content-Type: application/json" -d '{}')
  else
    actual=$(curl -s -o /dev/null -w '%{http_code}' "$url")
  fi
  if [ "$actual" = "$expected" ]; then
    echo "  ✅ $desc: $actual (expected $expected)"
    PASS=$((PASS + 1))
  else
    echo "  ❌ $desc: $actual (expected $expected)"
    FAIL=$((FAIL + 1))
  fi
}

echo "--- Allowed Paths ---"
check "GET  /healthz"        "https://webhook.exa.edu.kg/healthz"        "GET"  "200"
check "POST /webhook/events" "https://webhook.exa.edu.kg/webhook/events" "POST" "401"

echo ""
echo "--- Denied Paths ---"
check "GET  /"                "https://webhook.exa.edu.kg/"                "GET" "403"
check "GET  /random-path"    "https://webhook.exa.edu.kg/random-path"    "GET" "403"
check "GET  /admin"          "https://webhook.exa.edu.kg/admin"          "GET" "403"
check "GET  /api"            "https://webhook.exa.edu.kg/api"            "GET" "403"
check "GET  /webhooks/github" "https://webhook.exa.edu.kg/webhooks/github" "GET" "403"
check "GET  /webhooks/slack"  "https://webhook.exa.edu.kg/webhooks/slack"  "GET" "403"

echo ""
echo "=== Results: $PASS passed, $FAIL failed ==="
```

---

## 6. nginx Layer Supplemental Control (Defense in Depth)

Even with cloudflared path filtering, harden the nginx gateway as a second independent barrier.

### 6.1 Current nginx Config (from audit evidence)

```nginx
server {
    listen 8080;
    server_name _;

    location = /healthz {
        proxy_pass http://n8n:5678/healthz;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto https;
    }

    location = /webhook/events {
        proxy_pass http://webhook-ingress-shadow:8000/webhooks/linear;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto https;
    }

    location / {
        return 404;
    }
}
```

### 6.2 Hardened nginx Config

```nginx
server {
    listen 8080;
    server_name _;

    # --- Security Headers ---
    server_tokens off;
    add_header X-Content-Type-Options "nosniff" always;

    # --- Allowed Paths ---

    # Health check (GET only)
    location = /healthz {
        limit_except GET {
            deny all;
        }
        proxy_pass http://n8n:5678/healthz;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto https;
    }

    # Linear webhook entry point (POST only)
    location = /webhook/events {
        limit_except POST {
            deny all;
        }
        proxy_pass http://webhook-ingress-shadow:8000/webhooks/linear;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto https;

        # Rate limiting (100 requests per minute per IP)
        # Requires: limit_req_zone $binary_remote_addr zone=webhook:10m rate=100r/m;
        # limit_req zone=webhook burst=20 nodelay;
    }

    # Factory webhook entry point (POST only) — uncomment when active
    # location = /webhooks/factory {
    #     limit_except POST {
    #         deny all;
    #     }
    #     proxy_pass http://webhook-ingress-shadow:8000/webhooks/factory;
    #     proxy_http_version 1.1;
    #     proxy_set_header Host $host;
    #     proxy_set_header X-Real-IP $remote_addr;
    #     proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    #     proxy_set_header X-Forwarded-Proto https;
    # }

    # --- Explicit Deny for Known Sensitive Paths ---
    # These return 444 (nginx silent drop — closes connection without response)

    location = /admin { return 444; }
    location = /login { return 444; }
    location = /setup { return 444; }
    location = /api { return 444; }
    location = /api/ { return 444; }
    location = /execution { return 444; }
    location = /workflow { return 444; }
    location = /credentials { return 444; }
    location = /variables { return 444; }
    location = /rest/ { return 444; }

    # --- Catch-All: Deny Everything Else ---
    # Return 444 (silent drop) for any unmatched path
    # This is stricter than 404 — reveals nothing about the server
    location / {
        return 444;
    }
}
```

### 6.3 Key Changes from Current nginx Config

| Change | Before | After | Rationale |
|--------|--------|-------|-----------|
| Catch-all response | `return 404` | `return 444` | 444 = silent connection drop, reveals no server info |
| HTTP method restriction | None | `limit_except GET/POST` | `/healthz` only accepts GET, `/webhook/events` only accepts POST |
| Sensitive path explicit deny | None | `return 444` for /admin, /api, etc. | n8n management paths silently dropped |
| Server tokens | Default (on) | `server_tokens off` | Hide nginx version |

### 6.4 Rate Limiting (Optional Enhancement)

Add to the nginx `http` block (or at container level):

```nginx
# In http {} context:
limit_req_zone $binary_remote_addr zone=webhook:10m rate=100r/m;

# Then in the /webhook/events location:
limit_req zone=webhook burst=20 nodelay;
```

---

## 7. Notes and Caveats

### 7.1 Service Restart Required

```bash
# After modifying cloudflared config.yml:
systemctl restart cloudflared

# After modifying nginx config (inside Docker container):
docker exec n8n-webhook-gateway nginx -t
docker exec n8n-webhook-gateway nginx -s reload
```

### 7.2 Path Regex Accuracy

| Path | Regex | Matches | Does NOT Match |
|------|-------|---------|----------------|
| `/healthz` | `^/healthz$` | `/healthz` | `/healthz/`, `/healthzfoo`, `/Healthz` |
| `/webhook/events` | `^/webhook/events$` | `/webhook/events` | `/webhook/events/`, `/webhook/events/123` |

**Note**: cloudflared `path` uses Go `regexp.Regexp` for matching. The `^` and `$` anchors are important to prevent partial matches.

### 7.3 Impact on HMAC Verification Chain

**No impact expected.** The change occurs at the cloudflared layer, which is transparent to the HTTP request. When cloudflared forwards an allowed path to nginx:

1. cloudflared passes through all HTTP headers (including `Linear-Delivery-Id`, `Linear-Signature`)
2. nginx passes through all headers to webhook-ingress via `proxy_set_header`
3. webhook-ingress reads `Linear-Signature` header and verifies HMAC

The path filtering at cloudflared only decides **whether** the request reaches nginx at all. It does not modify headers or body.

### 7.4 Docker Compose Port Binding Verification

Ensure n8n and webhook-ingress remain bound to localhost only:

```bash
# Verify n8n is not exposed to public internet
ss -tlnp | grep 5678
# Should show: 127.0.0.1:5678 (not 0.0.0.0:5678)

# Verify webhook-ingress port 8000 is not exposed publicly
ss -tlnp | grep 8000
# Should show: 127.0.0.1:8000 or no binding (Docker internal network only)
```

### 7.5 Cloudflared Config Syntax Validation

Before restarting cloudflared, validate the config:

```bash
# Validate ingress rules
cloudflared tunnel ingress validate

# Dry-run to check rule matching
cloudflared tunnel ingress rule <tunnel-name>
```

### 7.6 Monitoring Post-Change

After applying the change, monitor for 403 responses in cloudflared logs:

```bash
# Check cloudflared logs for rejected requests
journalctl -u cloudflared --since "1 hour ago" | grep -i "403\|forbidden\|blocked"

# Monitor nginx access logs for unexpected patterns
docker logs n8n-webhook-gateway --since "1 hour ago" | grep -v "healthz\|webhook/events"
```

---

## 8. Defense-in-Depth Summary

```
Layer 1: Cloudflare Edge (DDoS protection, WAF)
  ↓
Layer 2: cloudflared Tunnel (path allowlist — THIS CHANGE)
  ↓ Only /healthz and /webhook/events pass through
Layer 3: nginx Gateway (path allowlist + HTTP method restriction + 444 silent drop)
  ↓ Only allowed paths and methods reach backend
Layer 4: webhook-ingress (HMAC signature verification)
  ↓ Only validly-signed requests are processed
Layer 5: Application logic (action routing, dedup, forwarding)
```

**Before this change**: Layer 2 was absent — all paths went directly to Layer 3.
**After this change**: Layer 2 provides independent path filtering, so even if Layer 3 (nginx) fails, unauthorized paths never reach backend services.
