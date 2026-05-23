from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Callable

from .actions import ActionRegistry
from .adapter import AdapterError, LinearAdapter, SignatureInvalidError, sha256_hex, utc_now_iso
from .factory_adapter import FactoryAdapter
from .models import AckResponse, WebhookRequest
from .schema import validate_canonical_event
from .storage import WebhookEventStore


@dataclass(frozen=True)
class IngressResult:
    http_status: int
    ack: AckResponse
    canonical_event: dict | None = None
    forwarded_to_n8n: bool = False


class WebhookIngress:
    def __init__(
        self,
        *,
        linear_secret: str | bytes,
        factory_secret: str | bytes | None = None,
        store: WebhookEventStore | None = None,
        n8n_sender: Callable[[dict], None] | None = None,
        route_mode: str = "live",
        action_registry: ActionRegistry | None = None,
    ):
        self.adapters = {"linear": LinearAdapter(linear_secret)}
        if factory_secret:
            self.adapters["factory"] = FactoryAdapter(factory_secret)
        self.store = store or WebhookEventStore()
        self.n8n_sender = n8n_sender
        self.route_mode = route_mode
        self.action_registry = action_registry or ActionRegistry()

    def handle(self, request: WebhookRequest) -> IngressResult:
        request_id = f"req_{uuid.uuid4()}"
        adapter = self.adapters.get(request.provider)
        if not adapter:
            ack = AckResponse(False, "PROVIDER_NOT_CONFIGURED", request_id, None, request.provider, "PROVIDER_NOT_CONFIGURED")
            return IngressResult(404, ack)

        try:
            adapter.verify(request)
        except SignatureInvalidError as exc:
            self.store.log(provider=request.provider, phase="signature", level="WARN", message=str(exc))
            ack = AckResponse(False, "SIGNATURE_INVALID", request_id, None, request.provider, "SIGNATURE_INVALID")
            return IngressResult(401, ack)

        received_at = utc_now_iso()
        event_id = f"evt_{uuid.uuid4()}"
        try:
            canonical_event = adapter.normalize(request, event_id=event_id, received_at=received_at)
            validate_canonical_event(canonical_event)
        except AdapterError as exc:
            self.store.log(provider=request.provider, phase="normalize", level="ERROR", message=str(exc))
            ack = AckResponse(False, exc.code, request_id, None, request.provider, exc.code)
            return IngressResult(400, ack)
        except Exception as exc:
            self.store.log(provider=request.provider, phase="normalize", level="ERROR", message=str(exc))
            ack = AckResponse(False, "CANONICAL_SCHEMA_INVALID", request_id, None, request.provider, "CANONICAL_SCHEMA_INVALID")
            return IngressResult(400, ack)

        existing = self.store.find_event_by_idempotency_key(canonical_event["idempotency_key"])
        if existing:
            self.store.log(
                provider=request.provider,
                phase="idempotency",
                level="INFO",
                message="duplicate accepted",
                event_id=existing["event_id"],
                details={"idempotency_key": canonical_event["idempotency_key"]},
                action_name="duplicate_check",
                status="duplicate",
                attempt=1,
                canonical_event_id=existing["event_id"],
                idempotency_key=canonical_event["idempotency_key"],
            )
            ack = AckResponse(True, "duplicate_accepted", request_id, existing["event_id"], request.provider)
            return IngressResult(200, ack, canonical_event=None, forwarded_to_n8n=False)

        self.store.save(request=request, canonical_event=canonical_event)
        self.store.log(
            provider=request.provider,
            phase="store",
            level="INFO",
            message="raw and canonical event stored",
            event_id=event_id,
            action_name="save_event",
            status="stored",
            attempt=1,
            canonical_event_id=event_id,
            idempotency_key=canonical_event["idempotency_key"],
        )

        forwarded = False
        if self.n8n_sender and self.route_mode != "shadow":
            event_for_route = dict(canonical_event)
            if self.route_mode in {"canary_dryrun", "production_canary"}:
                event_for_route["delivery_mode"] = self.route_mode
            self.n8n_sender(event_for_route)
            forwarded = True
            if hasattr(self.store, "mark_forwarded"):
                self.store.mark_forwarded(event_id)
            phase = "n8n_dryrun" if self.route_mode == "canary_dryrun" else "canary_forward" if self.route_mode == "production_canary" else "route"
            route_name = "linear.production_canary" if self.route_mode == "production_canary" else "linear.canary_dryrun" if self.route_mode == "canary_dryrun" else "linear.live"
            self.store.log(
                provider=request.provider,
                phase=phase,
                level="INFO",
                message="canonical event forwarded successfully",
                event_id=event_id,
                details={"route_mode": self.route_mode},
                route_name=route_name,
                action_name="forward_to_n8n",
                target_type="n8n_canary" if self.route_mode in {"canary_dryrun", "production_canary"} else "n8n_live",
                status="success",
                attempt=1,
                canonical_event_id=event_id,
                idempotency_key=canonical_event["idempotency_key"],
            )
        else:
            self.store.log(
                provider=request.provider,
                phase="route",
                level="INFO",
                message="n8n forwarding skipped",
                event_id=event_id,
                details={"route_mode": self.route_mode, "reason": "shadow mode or no n8n sender configured"},
                action_name="skip_forward",
                status="skipped",
                attempt=1,
                canonical_event_id=event_id,
                idempotency_key=canonical_event["idempotency_key"],
            )

        self.action_registry.run(provider=request.provider, route_mode=self.route_mode, canonical_event=canonical_event, store=self.store)

        ack = AckResponse(True, "accepted", request_id, event_id, request.provider)
        return IngressResult(200, ack, canonical_event=canonical_event, forwarded_to_n8n=forwarded)

def idempotency_key_for_request(provider: str, delivery_id: str | None, raw_body: bytes) -> str:
    return f"{provider}:{delivery_id}" if delivery_id else f"{provider}:sha256:{sha256_hex(raw_body)}"
