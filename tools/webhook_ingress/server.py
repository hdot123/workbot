"""Minimal FastAPI shadow server for webhook ingress on node-22.

Usage:
    WEBHOOK_INGRESS_MODE=shadow \
    LINEAR_WEBHOOK_SECRET=your-secret \
    uvicorn workspace.tools.webhook_ingress.server:app --host 0.0.0.0 --port 8080

Environment variables:
    WEBHOOK_INGRESS_MODE    - "shadow", "canary_dryrun", "production_canary", or "live"
    LINEAR_WEBHOOK_SECRET   - HMAC secret for Linear webhook signature verification
    WEBHOOK_DATABASE_URL    - PostgreSQL connection URL (required for canary_dryrun/production_canary/live)
    SUPABASE_DB_URL         - Alias for WEBHOOK_DATABASE_URL
    WEBHOOK_LOG_LEVEL       - Python log level (default: INFO)
    LINEAR_CANARY_COMMENT_ENABLED - true to enable guarded canary commentCreate in production_canary
    LINEAR_CANARY_API_TOKEN - Linear API token for guarded canary commentCreate only
"""

from __future__ import annotations

import logging
import os
import re
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from .actions import ActionRegistry, FactoryDispatchDryRunAction, LinearCanaryCommentAction
from .dispatch_payload import FactoryDispatchPayloadBuilder
from .executors import FactoryDispatchDryRunExecutor, LinearCanaryCommentExecutor
from .factory_lifecycle_action import FactoryLifecycleAction
from .ingress import IngressResult, WebhookIngress
from .lifecycle import FactoryLifecycleStateMachine
from .models import WebhookRequest
from .redaction import redact_mapping
from .storage import WebhookEventStore

logger = logging.getLogger("webhook_ingress.server")

_REQUIRED_DATABASE_MODES = {"canary_dryrun", "production_canary", "live"}

# ---------------------------------------------------------------------------
# Configuration (read lazily at startup, not at import time)
# ---------------------------------------------------------------------------

_REDACTED = "[REDACTED]"
_SECRET_PATTERNS = ("secret", "signature", "token", "password", "key", "authorization")


@dataclass
class ServerConfig:
    ingress_mode: str = "shadow"
    linear_secret: str = field(default="", repr=False)
    database_url: str | None = field(default=None, repr=False)
    log_level: str = "INFO"
    n8n_webhook_url: str | None = None
    linear_canary_comment_enabled: bool = False
    linear_canary_api_token: str | None = field(default=None, repr=False)
    linear_canary_allowed_project_ids: set[str] | None = None
    factory_dispatch_dryrun_enabled: bool = False
    factory_dispatch_allowed_project_ids: set[str] | None = None
    factory_dispatch_ready_state_names: set[str] | None = None
    factory_dispatch_repo: str = "busiji/workbot"
    factory_dispatch_target_branch: str = "branch-2"
    factory_secret: str = field(default="", repr=False)
    factory_lifecycle_enabled: bool = False

    @classmethod
    def from_env(cls) -> "ServerConfig":
        return cls(
            ingress_mode=os.environ.get("WEBHOOK_INGRESS_MODE", "shadow"),
            linear_secret=os.environ.get("LINEAR_WEBHOOK_SECRET", ""),
            database_url=os.environ.get("WEBHOOK_DATABASE_URL")
            or os.environ.get("SUPABASE_DB_URL"),
            log_level=os.environ.get("WEBHOOK_LOG_LEVEL", "INFO").upper(),
            n8n_webhook_url=os.environ.get("N8N_CANONICAL_WEBHOOK_URL")
            or os.environ.get("N8N_WEBHOOK_URL"),
            linear_canary_comment_enabled=os.environ.get("LINEAR_CANARY_COMMENT_ENABLED", "").lower() in {"1", "true", "yes"},
            linear_canary_api_token=os.environ.get("LINEAR_CANARY_API_TOKEN") or os.environ.get("LINEAR_API_TOKEN"),
            linear_canary_allowed_project_ids=_parse_csv_set(os.environ.get("LINEAR_CANARY_ALLOWED_PROJECT_IDS")),
            factory_dispatch_dryrun_enabled=os.environ.get("FACTORY_DISPATCH_DRYRUN_ENABLED", "").lower() in {"1", "true", "yes"},
            factory_dispatch_allowed_project_ids=_parse_csv_set(os.environ.get("FACTORY_DISPATCH_ALLOWED_PROJECT_IDS")),
            factory_dispatch_ready_state_names=_parse_csv_set(os.environ.get("FACTORY_DISPATCH_READY_STATE_NAMES")) or {"Ready for Factory"},
            factory_dispatch_repo=os.environ.get("FACTORY_DISPATCH_REPO", "busiji/workbot"),
            factory_dispatch_target_branch=os.environ.get("FACTORY_DISPATCH_TARGET_BRANCH", "branch-2"),
            factory_secret=os.environ.get("WEBHOOK_SECRET_FACTORY", ""),
            factory_lifecycle_enabled=os.environ.get("FACTORY_LIFECYCLE_ENABLED", "").lower() in {"1", "true", "yes"},
        )


# ---------------------------------------------------------------------------
# Secret redaction helper
# ---------------------------------------------------------------------------

def _parse_csv_set(value: str | None) -> set[str] | None:
    if not value:
        return None
    parsed = {part.strip() for part in value.split(",") if part.strip()}
    return parsed or None


def redact_sensitive_headers(headers: dict[str, str]) -> dict[str, str]:
    """Return a copy of headers with any secret-like values redacted."""
    return {key: str(value) for key, value in redact_mapping(headers).items()}


def redact_sensitive_query(query: str) -> str:
    """Redact query strings that may contain secrets."""
    if not query:
        return query
    for pat in _SECRET_PATTERNS:
        if pat in query.lower():
            return "[REDACTED]"
    return query


# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------

def setup_logging(config: ServerConfig) -> None:
    level = getattr(logging, config.log_level, logging.INFO)
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
    root = logging.getLogger("webhook_ingress")
    root.setLevel(level)
    root.addHandler(handler)
    for name in ("uvicorn.access", "starlette"):
        l = logging.getLogger(name)
        l.addFilter(_AccessLogFilter())


class _AccessLogFilter(logging.Filter):
    """Remove any request header or query value that looks secret from log messages."""

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(getattr(record, "getMessage", None), str):
            pass
        msg = record.getMessage()
        for pat in _SECRET_PATTERNS:
            # Redact any value following a secret-like header name
            if pat in msg.lower():
                record.msg = "[REDACTED]"
                record.args = ()
        return True


# ---------------------------------------------------------------------------
# Application lifecycle
# ---------------------------------------------------------------------------

_ingress: WebhookIngress | None = None
_config: ServerConfig | None = None


def _build_ingress(config: ServerConfig) -> WebhookIngress:
    """Construct the WebhookIngress instance based on given config."""
    if not config.linear_secret:
        raise RuntimeError("LINEAR_WEBHOOK_SECRET is not set")
    if config.ingress_mode in _REQUIRED_DATABASE_MODES and not config.database_url and not os.environ.get("WEBHOOK_SQLITE_PATH"):
        raise RuntimeError(f"WEBHOOK_DATABASE_URL is required for ingress mode {config.ingress_mode}")

    if config.database_url:
        from .postgres_storage import PostgresWebhookEventStore
        store = PostgresWebhookEventStore(config.database_url)
    else:
        sqlite_path = os.environ.get("WEBHOOK_SQLITE_PATH")
        store = WebhookEventStore(db_path=sqlite_path) if sqlite_path else WebhookEventStore()

    n8n_sender = None if config.ingress_mode == "shadow" else _make_n8n_sender(config.n8n_webhook_url)
    actions = []
    if config.linear_canary_comment_enabled:
        if not config.linear_canary_api_token:
            raise RuntimeError("LINEAR_CANARY_API_TOKEN is required when LINEAR_CANARY_COMMENT_ENABLED=true")
        actions.append(
            LinearCanaryCommentAction(
                executor=LinearCanaryCommentExecutor(api_token=config.linear_canary_api_token),
                enabled=True,
                allowed_project_ids=config.linear_canary_allowed_project_ids,
            )
        )
    if config.factory_dispatch_dryrun_enabled:
        actions.append(
            FactoryDispatchDryRunAction(
                executor=FactoryDispatchDryRunExecutor(
                    payload_builder=FactoryDispatchPayloadBuilder(
                        repo=config.factory_dispatch_repo,
                        target_branch=config.factory_dispatch_target_branch,
                    )
                ),
                enabled=True,
                allowed_project_ids=config.factory_dispatch_allowed_project_ids,
                ready_state_names=config.factory_dispatch_ready_state_names,
            )
        )
    # Shared lifecycle state machine for factory events
    lifecycle_machine = FactoryLifecycleStateMachine()
    if config.factory_lifecycle_enabled:
        actions.append(
            FactoryLifecycleAction(
                state_machine=lifecycle_machine,
                enabled=True,
            )
        )

    action_registry = ActionRegistry(actions)

    return WebhookIngress(
        linear_secret=config.linear_secret,
        factory_secret=config.factory_secret or None,
        store=store,
        n8n_sender=n8n_sender,
        route_mode=config.ingress_mode,
        action_registry=action_registry,
    )


def _mask_url(url: str) -> str:
    return re.sub(r"//([^:@/]+):([^@/]+)@", r"//\1:[REDACTED]@", url)


def _make_n8n_sender(default_url: str | None = None):
    """Create a sender callable that forwards canonical events to n8n."""
    import httpx

    from .routes import RouteMatcher

    matcher = RouteMatcher()
    client = httpx.Client(timeout=10)

    def sender(canonical_event: dict[str, Any]) -> None:
        url = default_url or matcher.match(canonical_event)
        if not url:
            logger.warning("no n8n route for event type=%s action=%s",
                           canonical_event.get("canonical_type"),
                           canonical_event.get("canonical_action"))
            return
        try:
            resp = client.post(url, json=canonical_event)
            resp.raise_for_status()
            logger.info("forwarded to n8n url=%s status=%s", _mask_url(url), resp.status_code)
        except Exception:
            logger.exception("failed to forward to n8n url=%s", _mask_url(url))

    return sender


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _ingress, _config
    _config = ServerConfig.from_env()
    setup_logging(_config)
    logger.info("webhook_ingress starting mode=%s", _config.ingress_mode)
    _ingress = _build_ingress(_config)
    logger.info("webhook_ingress ready")
    yield
    logger.info("webhook_ingress shutting down")


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------

app = FastAPI(title="Webhook Ingress Shadow", version="0.1.0", lifespan=lifespan)


@app.get("/health")
async def health() -> dict[str, str]:
    mode = _config.ingress_mode if _config else "unknown"
    return {"status": "ok", "mode": mode}


@app.post("/webhooks/linear")
async def webhook_linear(request: Request) -> JSONResponse:
    """Accept Linear webhook POSTs, verify signature, store, optionally forward to n8n."""
    global _ingress
    if _ingress is None:
        return JSONResponse(status_code=503, content={"ok": False, "status": "SERVICE_NOT_READY"})

    raw_body = await request.body()
    headers = dict(request.headers)

    # Log with redacted sensitive info
    safe_headers = redact_sensitive_headers(headers)
    logger.info("POST /webhooks/linear ip=%s headers=%s", request.client.host if request.client else "?", safe_headers)

    webhook_request = WebhookRequest(
        provider="linear",
        raw_body=raw_body,
        headers=headers,
        path=request.url.path,
        source_ip=request.client.host if request.client else None,
    )

    result: IngressResult = _ingress.handle(webhook_request)
    ack_dict = result.ack.to_dict()
    mode = _config.ingress_mode if _config else "?"
    logger.info("webhook result status=%s event_id=%s mode=%s",
                result.http_status, ack_dict.get("event_id"), mode)

    return JSONResponse(
        status_code=result.http_status,
        content=ack_dict,
    )


@app.post("/webhooks/factory")
async def webhook_factory(request: Request) -> JSONResponse:
    """Accept Factory lifecycle webhook POSTs, verify signature, store, drive lifecycle."""
    global _ingress
    if _ingress is None:
        return JSONResponse(status_code=503, content={"ok": False, "status": "SERVICE_NOT_READY"})

    raw_body = await request.body()
    headers = dict(request.headers)

    safe_headers = redact_sensitive_headers(headers)
    logger.info("POST /webhooks/factory ip=%s headers=%s", request.client.host if request.client else "?", safe_headers)

    webhook_request = WebhookRequest(
        provider="factory",
        raw_body=raw_body,
        headers=headers,
        path=request.url.path,
        source_ip=request.client.host if request.client else None,
    )

    if "factory" not in (_ingress.adapters if _ingress else {}):
        return JSONResponse(status_code=404, content={"ok": False, "status": "PROVIDER_NOT_CONFIGURED", "provider": "factory"})

    result: IngressResult = _ingress.handle(webhook_request)
    ack_dict = result.ack.to_dict()
    mode = _config.ingress_mode if _config else "?"
    logger.info("factory webhook result status=%s event_id=%s mode=%s",
                result.http_status, ack_dict.get("event_id"), mode)

    return JSONResponse(
        status_code=result.http_status,
        content=ack_dict,
    )
