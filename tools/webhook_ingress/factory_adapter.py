from __future__ import annotations

import hashlib
import hmac
import json
import uuid
from datetime import UTC, datetime
from typing import Any

from .models import WebhookRequest
from .adapter import AdapterError, SignatureInvalidError, NormalizeError, utc_now_iso, sha256_hex, _clean_none


class FactoryAdapter:
    provider = "factory"
    signature_headers = ("x-factory-signature",)
    delivery_headers = ("x-factory-delivery-id",)

    action_map = {
        "started": "created",
        "progress": "updated",
        "done": "updated",
        "blocked": "updated",
        "failed": "updated",
    }

    def __init__(self, secret: str | bytes):
        if isinstance(secret, str):
            secret = secret.encode("utf-8")
        self.secret = secret

    def verify(self, request: WebhookRequest) -> None:
        signature = None
        for header_name in self.signature_headers:
            signature = request.header(header_name)
            if signature:
                break
        if not signature:
            raise SignatureInvalidError("missing X-Factory-Signature header")
        signature = signature.strip()
        if signature.lower().startswith("sha256="):
            signature = signature.split("=", 1)[1]
        expected = hmac.new(self.secret, request.raw_body, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(signature, expected):
            raise SignatureInvalidError("invalid X-Factory-Signature")

    def delivery_id(self, request: WebhookRequest) -> str | None:
        for header_name in self.delivery_headers:
            value = request.header(header_name)
            if value:
                return value.strip()
        return None

    def normalize(self, request: WebhookRequest, *, event_id: str | None = None, received_at: str | None = None) -> dict[str, Any]:
        try:
            payload = json.loads(request.raw_body.decode("utf-8"))
        except Exception as exc:
            raise NormalizeError(f"invalid JSON payload: {exc}") from exc

        raw_hash = sha256_hex(request.raw_body)
        delivery_id = self.delivery_id(request)
        idempotency_key = f"factory:{delivery_id}" if delivery_id else f"factory:sha256:{raw_hash}"

        event_type = str(payload.get("event_type") or "unknown")
        run_id = payload.get("run_id")
        dispatch_id = payload.get("dispatch_id")
        issue_id = payload.get("issue_id")
        issue_key = payload.get("issue_key")
        project_id = payload.get("project_id")
        timestamp = payload.get("timestamp") or utc_now_iso()

        actor_data = payload.get("actor")
        if not isinstance(actor_data, dict):
            actor_data = {}

        event_payload = payload.get("payload")
        if not isinstance(event_payload, dict):
            event_payload = {}

        phase = event_payload.get("phase") or "unknown"
        canonical_action = self.action_map.get(phase.lower(), phase.replace(" ", "_").lower())

        canonical = {
            "canonical_version": "v1",
            "event_id": event_id or f"evt_{uuid.uuid4()}",
            "provider": "factory",
            "provider_event_type": event_type,
            "provider_action": self.action_map.get(phase, phase),
            "provider_delivery_id": delivery_id,
            "canonical_type": "factory_run",
            "canonical_action": canonical_action,
            "timestamp": timestamp,
            "received_at": received_at or utc_now_iso(),
            "source": {
                "provider": "factory",
                "instance_url": "https://factory.ai",
                "workspace_id": None,
                "resource_id": run_id,
                "resource_url": None,
                "project_id": project_id,
                "team_id": None,
            },
            "actor": {
                "id": actor_data.get("id") or "factory-agent",
                "display_name": actor_data.get("display_name") or "Factory Agent",
            },
            "payload": payload,
            "idempotency_key": idempotency_key,
            "raw_body_sha256": f"sha256:{raw_hash}",
        }
        return _clean_none(canonical)
