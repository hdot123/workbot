"""Tests for the FastAPI shadow server webhook ingress endpoint."""
from __future__ import annotations

import hmac
import hashlib
import json
import sys
from pathlib import Path

import pytest

# Ensure repo root is on sys.path
repo_root = Path(__file__).resolve().parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SECRET = "test-server-secret"


def _linear_signature(body: bytes) -> str:
    return hmac.new(SECRET.encode("utf-8"), body, hashlib.sha256).hexdigest()


def _linear_payload() -> dict:
    return {
        "type": "Issue",
        "action": "update",
        "organizationId": "org-1",
        "data": {
            "id": "issue-srv-1",
            "identifier": "JTO-999",
            "title": "Server integration test",
            "description": "testing",
            "url": "https://linear.app/jtoom/issue/JTO-999/test",
            "createdAt": "2026-05-04T00:00:00.000Z",
            "updatedAt": "2026-05-04T00:01:00.000Z",
            "team": {"id": "team-1"},
            "state": {"name": "Backlog"},
            "user": {"id": "user-1", "name": "Test User", "email": "test@example.com"},
        },
    }


@pytest.fixture(autouse=True)
def _set_env(monkeypatch: pytest.MonkeyPatch):
    """Set the minimal required env for the server module."""
    monkeypatch.setenv("LINEAR_WEBHOOK_SECRET", SECRET)
    monkeypatch.setenv("WEBHOOK_INGRESS_MODE", "shadow")
    monkeypatch.delenv("WEBHOOK_DATABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_DB_URL", raising=False)
    monkeypatch.delenv("WEBHOOK_LOG_LEVEL", raising=False)


@pytest.fixture()
def client():
    """Return a TestClient opened within the FastAPI lifespan context.
    
    This ensures the lifespan startup runs before any request, properly
    initializing _ingress and _config.
    """
    from workspace.tools.webhook_ingress import server as server_mod

    # Create a fresh app each time so lifespan runs cleanly
    from fastapi import FastAPI
    from contextlib import asynccontextmanager
    from starlette.testclient import TestClient

    @asynccontextmanager
    async def test_lifespan(app: FastAPI):
        server_mod._config = server_mod.ServerConfig.from_env()
        server_mod.setup_logging(server_mod._config)
        server_mod._ingress = server_mod._build_ingress(server_mod._config)
        yield

    test_app = FastAPI(title="TestApp", version="test", lifespan=test_lifespan)

    # Copy the routes from server module
    test_app.get("/health")(server_mod.health)
    test_app.post("/webhooks/linear")(server_mod.webhook_linear)

    with TestClient(test_app) as c:
        yield c


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_health_endpoint(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["mode"] == "shadow"


def test_post_webhooks_linear_success(client):
    payload = _linear_payload()
    body = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    sig = _linear_signature(body)

    resp = client.post(
        "/webhooks/linear",
        content=body,
        headers={"Linear-Signature": sig, "Content-Type": "application/json"},
    )
    assert resp.status_code == 200


def test_post_webhooks_linear_bad_signature(client):
    payload = _linear_payload()
    body = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")

    resp = client.post(
        "/webhooks/linear",
        content=body,
        headers={"Linear-Signature": "bad-signature", "Content-Type": "application/json"},
    )
    assert resp.status_code == 401


def test_post_webhooks_linear_missing_signature(client):
    payload = _linear_payload()
    body = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")

    resp = client.post(
        "/webhooks/linear",
        content=body,
        headers={"Content-Type": "application/json"},
    )
    assert resp.status_code == 401


def test_post_webhooks_linear_empty_body(client):
    resp = client.post(
        "/webhooks/linear",
        content=b"",
        headers={"Linear-Signature": "anything"},
    )
    # Signature check runs first; empty body won't match the HMAC -> 401
    assert resp.status_code == 401


def test_shadow_mode_does_not_forward_to_n8n():
    """In shadow mode, the n8n_sender is None, so no forwarding occurs."""
    from workspace.tools.webhook_ingress import server as server_mod

    config = server_mod.ServerConfig(ingress_mode="shadow", linear_secret=SECRET)
    ingress = server_mod._build_ingress(config)
    assert ingress.n8n_sender is None, "Shadow mode must not forward to n8n"


def test_redact_sensitive_headers():
    from workspace.tools.webhook_ingress.server import redact_sensitive_headers

    headers = {
        "Linear-Signature": "secret-value",
        "Authorization": "Bearer token123",
        "Content-Type": "application/json",
        "X-Custom-Token": "my-token",
        "X-Request-Id": "req-123",
    }
    redacted = redact_sensitive_headers(headers)

    assert redacted["Linear-Signature"] == "[REDACTED]"
    assert redacted["Authorization"] == "[REDACTED]"
    assert redacted["X-Custom-Token"] == "[REDACTED]"
    assert redacted["Content-Type"] == "application/json"
    assert redacted["X-Request-Id"] == "req-123"


def test_redact_sensitive_query():
    from workspace.tools.webhook_ingress.server import redact_sensitive_query

    assert redact_sensitive_query("") == ""
    assert redact_sensitive_query("token=abc") == "[REDACTED]"
    assert redact_sensitive_query("id=123&name=test") == "id=123&name=test"


def test_canary_dryrun_requires_database_url(monkeypatch):
    monkeypatch.setenv("LINEAR_WEBHOOK_SECRET", SECRET)
    monkeypatch.setenv("WEBHOOK_INGRESS_MODE", "canary_dryrun")
    monkeypatch.delenv("WEBHOOK_DATABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_DB_URL", raising=False)

    from workspace.tools.webhook_ingress import server as server_mod
    config = server_mod.ServerConfig.from_env()
    with pytest.raises(RuntimeError, match="WEBHOOK_DATABASE_URL is required"):
        server_mod._build_ingress(config)


def test_canary_comment_enabled_requires_token(monkeypatch):
    monkeypatch.setenv("LINEAR_WEBHOOK_SECRET", SECRET)
    monkeypatch.setenv("WEBHOOK_INGRESS_MODE", "shadow")
    monkeypatch.setenv("LINEAR_CANARY_COMMENT_ENABLED", "true")
    monkeypatch.delenv("LINEAR_CANARY_API_TOKEN", raising=False)
    monkeypatch.delenv("LINEAR_API_TOKEN", raising=False)

    from workspace.tools.webhook_ingress import server as server_mod
    config = server_mod.ServerConfig.from_env()
    with pytest.raises(RuntimeError, match="LINEAR_CANARY_API_TOKEN is required"):
        server_mod._build_ingress(config)


def test_non_shadow_modes_require_database_url(monkeypatch):
    monkeypatch.setenv("LINEAR_WEBHOOK_SECRET", SECRET)
    monkeypatch.delenv("WEBHOOK_DATABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_DB_URL", raising=False)

    from workspace.tools.webhook_ingress import server as server_mod
    for mode in ("canary_dryrun", "production_canary", "live"):
        monkeypatch.setenv("WEBHOOK_INGRESS_MODE", mode)
        config = server_mod.ServerConfig.from_env()
        with pytest.raises(RuntimeError, match="WEBHOOK_DATABASE_URL is required"):
            server_mod._build_ingress(config)
