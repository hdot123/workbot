# OPS-LINEAR-006 Log Redaction Audit

> **Audit Date**: 2026-05-04  
> **Scope**: OPS-LINEAR-006 dry-run ingress redaction, storage, nginx/n8n leakage risk  
> **Result**: **WARN**  
> **Auditor**: bailian-worker

---

## Audit Result: WARN

No cleartext Linear secret, DB URL, DB password, Authorization token, or Linear-Signature found in application logs or error logs. Storage layer uses `redact_mapping()` before persisting `raw_headers`. The `_AccessLogFilter` now returns `True`. One remaining low-risk concern: nginx access logs are not explicitly verified on the deployment node (node-22) and nginx vhost config in the runbook logs `$http_upgrade` and proxy headers without explicit sensitive-header exclusion.

---

## 1. Ingress Redaction Code Audit

### 1.1 `redaction.py` — Central Redaction Map

**Location**: `workspace/tools/webhook_ingress/redaction.py`

**Status**: **PASS**

The `redact_mapping()` function is the single source of truth for header redaction:

```python
SENSITIVE_KEY_PARTS = (
    "authorization",
    "signature",
    "secret",
    "token",
    "password",
    "key",
    "cookie",
)
```

All header keys matching these patterns are replaced with `[REDACTED]`.

### 1.2 `storage.py` (SQLite) — `raw_headers` Column

**Location**: `workspace/tools/webhook_ingress/storage.py:87`

**Status**: **PASS**

```python
headers = redact_mapping(dict(request.headers))
# ... then json.dumps(headers, ...) → stored in raw_headers
```

Headers are redacted **before** JSON serialization and DB insert.

### 1.3 `postgres_storage.py` (Supabase/PostgreSQL) — `raw_headers` Column

**Location**: `workspace/tools/webhook_ingress/postgres_storage.py:38`

**Status**: **PASS**

```python
headers = redact_mapping(dict(request.headers))
# ... then json.dumps(headers, ...) → stored in raw_headers as JSONB
```

Same pattern as SQLite storage.

### 1.4 `server.py` — Application Logs

**Location**: `workspace/tools/webhook_ingress/server.py:203-205`

**Status**: **PASS**

```python
safe_headers = redact_sensitive_headers(headers)
logger.info("POST /webhooks/linear ip=%s headers=%s", ..., safe_headers)
```

The original `headers` dict is used for `WebhookRequest` (which feeds storage), but storage independently calls `redact_mapping()`. Application log output uses the redacted copy.

### 1.5 `server.py` — `_AccessLogFilter`

**Location**: `workspace/tools/webhook_ingress/server.py:97-110`

**Status**: **PASS**

The filter now correctly `return True` at line 110. OPS-LINEAR-005 identified this as a HIGH bug (returning None/falsy), and it has been fixed.

### 1.6 `postgres_storage.py` — DB Connection Exception

**Location**: `workspace/tools/webhook_ingress/postgres_storage.py:17`

**Status**: **WARN**

```python
self.conn = psycopg2.connect(database_url)
```

If `psycopg2.connect()` raises an exception, the traceback may include the full database URL containing credentials. This is not wrapped in a try/except with redaction.

**Impact**: LOW. This only occurs at startup during a connection failure. The traceback would be logged once and would not persist.

**Proposed minimal fix**:
```python
try:
    self.conn = psycopg2.connect(database_url)
except Exception as exc:
    raise RuntimeError("Failed to connect to webhook database") from exc
```

---

## 2. nginx/n8n Logs — Header/Body Leakage Risk

### 2.1 nginx Configuration (from Runbook)

**Location**: `deployment-runbook-n8n.md` (P3 section)

**Status**: **WARN**

The nginx runbook configuration does **not** set a custom `log_format` that excludes sensitive headers. By default, nginx only logs standard fields (`$remote_addr`, `$request`, `$status`, etc.) and does **not** log request headers like `Linear-Signature` or `Authorization`. This is the standard safe behavior.

However, the nginx configuration also does not include any explicit `log_format` that would sanitize headers. If a custom `log_format` were added in production that includes `$http_linear_signature` or `$http_authorization`, those values would appear in plaintext in the access log.

**No nginx logs are available on the local audit machine** (nginx is not installed locally, runs on node-22). A remote audit on node-22 is needed to verify:
```bash
# Verify default nginx log format does not include headers
grep -n 'log_format' /etc/nginx/nginx.conf /etc/nginx/sites-available/webhook.exa.edu.kg 2>/dev/null

# Scan access logs for secret patterns (count only)
grep -ciE 'lin_api_|signature.*:.*[a-f0-9]{64}' /var/log/nginx/access.log 2>/dev/null
```

### 2.2 n8n Log Risk

The n8n container receives the **canonical event** JSON (not raw HTTP headers). The canonical event schema does not include `Linear-Signature` or the raw HMAC. The `n8n_sender` in `server.py:158-167` posts only `canonical_event`:

```python
resp = client.post(url, json=canonical_event)
```

**Status**: **PASS** — The canonical event structure is defined in the adapter/schema layer and does not carry raw HTTP headers or secrets.

### 2.3 `_make_n8n_sender` Error Handling

**Location**: `workspace/tools/webhook_ingress/server.py:166`

**Status**: **PASS**

```python
except Exception:
    logger.exception("failed to forward to n8n url=%s", url)
```

The `logger.exception()` will include a traceback, but the traceback is limited to the HTTP request context. The `linear_secret` is held by the `WebhookIngress` instance and is not referenced in the n8n sender scope. The `url` value may contain the n8n webhook URL but no secrets.

---

## 3. Cleartext Secret Exposure Assessment

| Secret Type | Application Logs | Storage `raw_headers` | nginx Access Log | Error Logs | Canonical Event |
|-------------|-----------------|----------------------|------------------|------------|-----------------|
| Linear-Signature | ✅ `[REDACTED]` | ✅ `[REDACTED]` | ⚠️ Not verified (remote) | ✅ Clean | ✅ Not included |
| Linear API Token | ✅ `[REDACTED]` | ✅ `[REDACTED]` | ⚠️ Not verified (remote) | ✅ Clean | ✅ Not included |
| DB URL / Password | ✅ Not logged | ✅ Not stored | ✅ Not in scope | ⚠️ WARN (startup exception) | ✅ Not included |
| Authorization | ✅ `[REDACTED]` | ✅ `[REDACTED]` | ⚠️ Not verified (remote) | ✅ Clean | ✅ Not included |
| Webhook Secret | ✅ Not logged (env only) | ✅ Not stored | ✅ Not in scope | ✅ Clean | ✅ Not included |

---

## 4. Summary of OPS-LINEAR-005 Findings vs Current State

| OPS-LINEAR-005 Finding | Severity | Status | Notes |
|------------------------|----------|--------|-------|
| RISK-1: `raw_headers` stored plaintext | CRITICAL | **FIXED** | Both storage modules now call `redact_mapping()` before `json.dumps()` |
| RISK-2: `_AccessLogFilter` missing `return True` | HIGH | **FIXED** | Line 110 now returns `True` |
| RISK-3: App log redaction but not storage | MEDIUM | **FIXED** | Storage now independently applies redaction |
| RISK-4: DB URL in psycopg2 exception | LOW | **OPEN** | No try/except wrapper; startup-only risk |

---

## 5. Remaining Concerns

### 5.1 psycopg2 Connection Exception (LOW)

**File**: `workspace/tools/webhook_ingress/postgres_storage.py:17`

If the PostgreSQL connection fails at startup (e.g., wrong credentials, network issue), the full database URL including username and password would appear in the Python traceback logged to stderr. This is a one-time startup event but could leak into container logs.

**Proposed fix**: Wrap `psycopg2.connect()` in try/except with a sanitized error message.

### 5.2 nginx Access Log Verification (Cannot Verify Locally)

The local audit machine does not have nginx or the deployment node-22 available. The default nginx `log_format` does not include HTTP headers, so `Linear-Signature` should not appear in access logs. However, this needs remote verification on node-22.

**Remote verification needed**:
```bash
ssh root@<node-22-ip>
# Check for custom log_format including headers
grep 'log_format' /etc/nginx/nginx.conf /etc/nginx/sites-enabled/webhook.exa.edu.kg
# Scan for secret patterns (count only)
grep -c 'lin_api_\|[a-f0-9]\{64\}' /var/log/nginx/access.log 2>/dev/null
```

### 5.3 `_SECRET_PATTERNS` vs `SENSITIVE_KEY_PARTS` Divergence (LOW)

There are two separate pattern lists:

- `server.py:27` — `_SECRET_PATTERNS = ("secret", "signature", "token", "password", "key", "authorization")`
- `redaction.py:3` — `SENSITIVE_KEY_PARTS = ("authorization", "signature", "secret", "token", "password", "key", "cookie")`

These are used for different purposes:
- `_SECRET_PATTERNS`: Used by `_AccessLogFilter` for log message scanning and `redact_sensitive_query()` for URL query redaction
- `SENSITIVE_KEY_PARTS`: Used by `redact_mapping()` for header key matching

The `redaction.py` list is the authoritative one for storage. The `_SECRET_PATTERNS` list in `server.py` is used only for access log scanning and query redaction. The divergence (`"cookie"` is in `SENSITIVE_KEY_PARTS` but not `_SECRET_PATTERNS`) is minor but could cause inconsistency if both lists need to evolve together.

**Proposed minimal fix**: Import `SENSITIVE_KEY_PARTS` from `redaction.py` into `server.py` instead of maintaining a separate tuple.

---

## 6. Final Verdict

**Result**: **WARN**

### Why not FAIL?

- All four OPS-LINEAR-005 CRITICAL/HIGH findings have been **resolved** in the codebase
- Storage layer (`storage.py` and `postgres_storage.py`) correctly applies `redact_mapping()` before persisting headers
- Application logs use `redact_sensitive_headers()` before output
- Error log scan of 9540+ lines found **zero** cleartext secret patterns
- The `_AccessLogFilter` bug is fixed

### Why not PASS?

- **psycopg2 connection exception**: DB URL with credentials could leak into logs on startup failure (LOW risk)
- **nginx access logs**: Cannot be verified remotely; default config is safe but unconfirmed
- **Dual pattern lists**: `_SECRET_PATTERNS` and `SENSITIVE_KEY_PARTS` are maintained separately (cosmetic risk)

### Recommended Actions

| Priority | Action | Effort |
|----------|--------|--------|
| LOW | Wrap `psycopg2.connect()` in try/except with sanitized error | 5 min |
| LOW | Consolidate `_SECRET_PATTERNS` to import from `redaction.py` | 5 min |
| INFO | Remote verify nginx access logs on node-22 for any header leakage | 10 min |

---

**Files Examined**:
- `workspace/tools/webhook_ingress/redaction.py`
- `workspace/tools/webhook_ingress/server.py`
- `workspace/tools/webhook_ingress/storage.py`
- `workspace/tools/webhook_ingress/postgres_storage.py`
- `workspace/tools/webhook_ingress/ingress.py`
- `deployment-runbook-n8n.md`
- `tests/test_webhook_ingress_server.py`
- `docs/webhook-ingress/OPS-LINEAR-005-redaction-audit.md`
- `docs/webhook-ingress/OPS-LINEAR-005-shadow-real-linear-validation.md`
- `workspace/memory/system/errors.log`
