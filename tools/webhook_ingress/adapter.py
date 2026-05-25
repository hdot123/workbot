from __future__ import annotations

import hashlib
import hmac
import json
import uuid
from datetime import UTC, datetime
from typing import Any

from .models import WebhookRequest


class AdapterError(Exception):
    code = "ADAPTER_ERROR"


class SignatureInvalidError(AdapterError):
    code = "SIGNATURE_INVALID"


class NormalizeError(AdapterError):
    code = "NORMALIZE_FAILED"


def utc_now_iso() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def sha256_hex(raw_body: bytes) -> str:
    return hashlib.sha256(raw_body).hexdigest()


def _clean_none(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: _clean_none(v) for k, v in value.items() if v is not None}
    if isinstance(value, list):
        return [_clean_none(v) for v in value]
    return value


def _linear_label_names(data: dict[str, Any]) -> list[str] | None:
    labels = data.get("labels")
    if not isinstance(labels, list):
        return None
    names: list[str] = []
    for label in labels:
        if isinstance(label, dict):
            name = label.get("name") or label.get("id")
        else:
            name = label
        if name:
            names.append(str(name))
    return names or None


class LinearAdapter:
    provider = "linear"
    signature_headers = ("linear-signature", "x-linear-signature")
    delivery_headers = ("linear-delivery", "linear-delivery-id", "x-linear-delivery-id")

    type_map = {
        "Issue": "issue",
        "Comment": "comment",
        "Customer": "customer",
        "Document": "document",
        "InitiativeUpdate": "initiative_update",
        "IssueLabel": "issue_label",
        "ProjectUpdate": "project_update",
        "Release": "release",
        "CustomerNeed": "customer_request",
        "Cycle": "cycle",
        "Reaction": "emoji_reaction",
        "Initiative": "initiative",
        "Attachment": "issue_attachment",
        "ProjectLabel": "project_label",
        "Project": "project",
        "User": "user",
        "IssueSLA": "issue_sla",
    }
    action_map = {
        "create": "created",
        "update": "updated",
        "remove": "deleted",
        "delete": "deleted",
        "archive": "closed",
        "unarchive": "reopened",
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
            raise SignatureInvalidError("missing Linear-Signature header")
        signature = signature.strip()
        if signature.lower().startswith("sha256="):
            signature = signature.split("=", 1)[1]
        expected = hmac.new(self.secret, request.raw_body, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(signature, expected):
            raise SignatureInvalidError("invalid Linear-Signature")

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
        idempotency_key = f"linear:{delivery_id}" if delivery_id else f"linear:sha256:{raw_hash}"
        event_type = str(payload.get("type") or "unknown")
        action = str(payload.get("action") or "unknown")
        data = payload.get("data") if isinstance(payload.get("data"), dict) else {}
        actor_data = payload.get("actor") or payload.get("user") or data.get("user")
        if not isinstance(actor_data, dict):
            actor_data = {}

        canonical_type = self.type_map.get(event_type, event_type.replace(" ", "_").lower())
        canonical_action = self.action_map.get(action.lower(), action.replace(" ", "_").lower())
        labels = _linear_label_names(data)
        label_ids = data.get("labelIds") if isinstance(data.get("labelIds"), list) else None
        project = data.get("project") if isinstance(data.get("project"), dict) else {}
        project_id = data.get("projectId") or project.get("id")
        project_name = project.get("name")
        project_url = project.get("url")
        team_id = data.get("teamId") or data.get("team", {}).get("id") if isinstance(data.get("team"), dict) else data.get("teamId")
        state_data = data.get("state")
        state_name = state_data.get("name") if isinstance(state_data, dict) else state_data
        state_id = state_data.get("id") if isinstance(state_data, dict) else None
        updated_from = payload.get("updatedFrom") if isinstance(payload.get("updatedFrom"), dict) else {}
        previous_state_data = updated_from.get("state") if isinstance(updated_from.get("state"), dict) else None
        previous_state = previous_state_data.get("name") if previous_state_data else None
        previous_state_id = updated_from.get("stateId") or previous_state_data.get("id") if previous_state_data else updated_from.get("stateId")
        resource_id = data.get("id") or payload.get("id") or delivery_id or raw_hash
        event_timestamp = (
            data.get("updatedAt")
            or data.get("createdAt")
            or payload.get("createdAt")
            or payload.get("timestamp")
            or received_at
            or utc_now_iso()
        )

        canonical = {
            "canonical_version": "v1",
            "event_id": event_id or f"evt_{uuid.uuid4()}",
            "provider": "linear",
            "provider_event_type": event_type,
            "provider_action": action,
            "provider_delivery_id": delivery_id,
            "canonical_type": canonical_type,
            "canonical_action": canonical_action,
            "timestamp": event_timestamp,
            "received_at": received_at or utc_now_iso(),
            "source": {
                "provider": "linear",
                "instance_url": "https://linear.app",
                "workspace_id": payload.get("organizationId") or team_id,
                "resource_id": str(resource_id),
                "resource_url": data.get("url"),
                "project_id": project_id,
                "team_id": team_id,
            },
            "actor": {
                "id": actor_data.get("id"),
                "display_name": actor_data.get("name") or actor_data.get("displayName"),
                "email": actor_data.get("email"),
            },
            "payload": {
                "id": data.get("id"),
                "identifier": data.get("identifier"),
                "title": data.get("title") or data.get("name"),
                "description": data.get("description"),
                "state": state_name,
                "state_id": state_id,
                "previous_state": previous_state,
                "previous_state_id": previous_state_id,
                "url": data.get("url"),
                "labels": labels,
                "label_ids": label_ids,
                "project_id": project_id,
                "project_name": project_name,
                "project_url": project_url,
                "metadata": {
                    "linear_id": data.get("id"),
                    "linear_identifier": data.get("identifier"),
                    "raw_type": event_type,
                    "raw_action": action,
                },
            },
            "idempotency_key": idempotency_key,
            "raw_body_sha256": f"sha256:{raw_hash}",
        }
        return _clean_none(canonical)
