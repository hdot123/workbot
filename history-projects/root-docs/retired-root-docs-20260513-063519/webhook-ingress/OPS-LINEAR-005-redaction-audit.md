# OPS-LINEAR-005 Log Redaction Audit

> **Audit Date**: 2026-05-04  
> **Scope**: webhook-ingress-shadow, nginx, docker inspect outputs  
> **Result**: FAIL  
> **Auditor**: bailian-worker

---

## Audit Result: **FAIL**

At least one **REDACTION_RISK** found with plaintext secret persistence in persistent storage.

---

## REDACTION_RISK Findings

### RISK-1: `raw_headers` stored PLAINTEXT in database (CRITICAL)

- **Location**: `workspace/tools/webhook_ingress/storage.py:85-100` and `postgres_storage.py:36-54`
- **Type**: DATABASE_PERSISTENCE
- **Secrets at risk**: `Linear-Signature`, `Authorization` (any header matching secret patterns)
- **Details**: Both `storage.py` (SQLite) and `postgres_storage.py` (Supabase/PostgreSQL) call `json.dumps(dict(request.headers))` and persist ALL request headers unredacted into the `webhook_raw_events.raw_headers` column. This includes `Linear-Signature` / `x-linear-signature` headers containing HMAC-SHA256 signatures.
- **Impact**: Every webhook payload results in the Linear webhook signing secret's HMAC signature being stored in plaintext in the database. While the signature alone is not the raw secret, it is a reusable credential for replay attacks and represents a credential exposure.
- **Safe grep to verify presence**:
  ```bash
  # Check if raw_headers column is being written without redaction
  grep -n 'json\.dumps(headers' workspace/tools/webhook_ingress/storage.py
  grep -n 'json\.dumps(headers' workspace/tools/webhook_ingress/postgres_storage.py
  ```

### RISK-2: `_AccessLogFilter` has no `return True` (HIGH)

- **Location**: `workspace/tools/webhook_ingress/server.py:139-148`
- **Type**: LOGGING_BUG
- **Details**: The `_AccessLogFilter.filter()` method does not contain a `return True` at the end. In Python's logging framework, a filter that returns `None` (implicit) is treated as falsy, meaning **all log records will be dropped**. This means the intended access log redaction filter is never functioning, and even if it were fixed, its regex-based approach would need strengthening.
- **Impact**: All uvicorn/starlette access logs are silently suppressed. If the filter were corrected, it would need to be tested to confirm secrets in URL query strings and request bodies are properly redacted.
- **Safe grep to verify**:
  ```bash
  grep -n 'return True' workspace/tools/webhook_ingress/server.py
  # Expected: should find at least one in _AccessLogFilter.filter()
  # Actual: none found in that method
  ```

### RISK-3: Application-level redaction only covers logger, not storage (MEDIUM)

- **Location**: `workspace/tools/webhook_ingress/server.py:199-204`
- **Type**: REDACTION_COVERAGE_GAP
- **Details**: The `redact_sensitive_headers()` function is called before the application `logger.info()` on line 203-204, so application log messages are correctly redacted. However, the same `headers` dict (unredacted) is passed to `WebhookRequest` and subsequently to `storage.save()`, where it is persisted as raw JSON.
- **Secrets at risk**: Any header containing "secret", "signature", "token", "password", "key", or "authorization" (per `_SECRET_PATTERNS`)
- **Safe grep to verify**:
  ```bash
  grep -n 'redact_sensitive_headers\|safe_headers\|raw_headers' workspace/tools/webhook_ingress/server.py
  ```

### RISK-4: Database URL in error messages (LOW)

- **Location**: `workspace/tools/webhook_ingress/postgres_storage.py:17`
- **Type**: EXCEPTION_LEAKAGE
- **Details**: If `psycopg2.connect()` fails, the exception message may include the full database URL (which contains credentials) in the traceback. The code does not catch and redact connection exceptions.
- **Safe grep to verify**:
  ```bash
  grep -n 'psycopg2.connect\|try:\|except' workspace/tools/webhook_ingress/postgres_storage.py
  ```

---

## Areas Verified CLEAN

| Area | Status | Notes |
|------|--------|-------|
| Application log output (`logger.info`) | PASS | `redact_sensitive_headers()` correctly applied before logging |
| `_SECRET_PATTERNS` coverage | PASS | Covers: secret, signature, token, password, key, authorization |
| `redact_sensitive_query()` function | PASS | Present but unused (no query string logging detected) |
| Local error.log (`workspace/memory/system/errors.log`) | PASS | No plaintext secrets found (9540 lines scanned) |
| Playwright console log | PASS | No secret patterns found |
| Environment variable usage in code | PASS | Secrets read from env vars, not hardcoded |

---

## Log Sources Examined

| Log Source | Available | Secrets Found |
|-----------|-----------|---------------|
| webhook-ingress-shadow application logs | N/A (no running containers) | N/A |
| nginx access/error logs | N/A (nginx not installed locally) | N/A |
| docker inspect outputs | N/A (no running containers) | N/A |
| workspace/memory/system/errors.log | Yes (9540 lines) | None |
| .playwright-cli logs | Yes | None |
| workspace/memory/tmp/*.log | No .log files found | N/A |

**Note**: Docker and nginx are not running on the local audit machine. The audit is based on code review only. Running the audit commands requires SSH access to node-22 (the deployment target).

---

## Safe Grep Commands for Remote Audit (node-22)

These commands can be run on node-22 to verify actual log content without printing secrets:

```bash
# 1. Check shadow container logs for any LINEAR_WEBHOOK_SECRET values
#    Returns COUNT only, not the actual secret
docker logs webhook-ingress-shadow 2>&1 \
  | grep -c 'LINEAR_WEBHOOK_SECRET'

# 2. Check shadow container logs for Linear-Signature header values
#    Returns COUNT of lines containing the header name
docker logs webhook-ingress-shadow 2>&1 \
  | grep -ciE 'linear-signature'

# 3. Check shadow container logs for Authorization headers
docker logs webhook-ingress-shadow 2>&1 \
  | grep -ciE 'authorization.*bearer|bearer.*[a-z0-9]'

# 4. Check shadow container logs for database URLs
docker logs webhook-ingress-shadow 2>&1 \
  | grep -ciE 'postgresql://.*:.*@|supabase.*url'

# 5. Check shadow container logs for password patterns
docker logs webhook-ingress-shadow 2>&1 \
  | grep -ciE 'password\s*[:=]'

# 6. Check nginx access logs for Linear-Signature header leakage
#    (nginx does not log headers by default, but verify custom log_format)
grep -c 'linear.signature\|linear-signature' /var/log/nginx/access.log 2>/dev/null || echo "no nginx logs or no match"

# 7. Check nginx error logs for any secret leakage
grep -ciE 'secret|password|authorization|token' /var/log/nginx/error.log 2>/dev/null || echo "no nginx error logs"

# 8. Check docker inspect for env var leakage
docker inspect webhook-ingress-shadow 2>&1 \
  | grep -c 'LINEAR_WEBHOOK_SECRET\|WEBHOOK_DATABASE_URL\|SUPABASE_DB_URL'

# 9. Query Supabase for raw_headers column containing Linear-Signature
#    (requires supabase CLI or curl with service key)
#    curl -sS "https://<project>.supabase.co/rest/v1/webhook_raw_events?select=raw_headers&limit=1" \
#      -H "apikey: <anon-key>" \
#      -H "Authorization: Bearer <service-key>" \
#      | grep -c 'linear-signature'
```

---

## Required Fixes

### Fix-1 (CRITICAL): Redact headers before database storage

In both `storage.py` and `postgres_storage.py`, redact sensitive headers before calling `json.dumps(headers)`:

```python
# In storage.py save() method, before json.dumps:
from .server import redact_sensitive_headers
safe_headers = redact_sensitive_headers(dict(request.headers))
# ... then store safe_headers instead of headers
```

Or define `redact_sensitive_headers` locally in the storage module to avoid circular imports.

### Fix-2 (HIGH): Add `return True` to `_AccessLogFilter`

```python
class _AccessLogFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        msg = record.getMessage()
        for pat in _SECRET_PATTERNS:
            if pat in msg.lower():
                record.msg = "[REDACTED]"
                record.args = ()
        return True  # <-- MUST add this
```

### Fix-3 (LOW): Wrap psycopg2.connect in try/except with redaction

```python
try:
    self.conn = psycopg2.connect(database_url)
except Exception as exc:
    raise RuntimeError("Failed to connect to database") from exc
```

---

## Summary

| Metric | Value |
|--------|-------|
| Total REDACTION_RISK findings | 4 |
| CRITICAL | 1 (raw_headers plaintext in DB) |
| HIGH | 1 (AccessLogFilter drops all logs) |
| MEDIUM | 1 (redaction coverage gap) |
| LOW | 1 (exception message leakage) |
| **Overall verdict** | **FAIL** |
| **Blocking for production** | **Yes — Fix-1 and Fix-2 must be resolved** |
