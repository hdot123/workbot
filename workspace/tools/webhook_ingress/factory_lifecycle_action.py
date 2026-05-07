from __future__ import annotations
from typing import Any
from .lifecycle import FactoryLifecycleStateMachine, RunState, LifecycleTransitionError


class FactoryLifecycleAction:
    """Action that processes factory lifecycle events through the state machine."""

    name = "factory_lifecycle"

    def __init__(self, *, state_machine: FactoryLifecycleStateMachine, enabled: bool):
        self.state_machine = state_machine
        self.enabled = enabled

    def run(self, *, provider: str, route_mode: str, canonical_event: dict[str, Any], store: Any) -> None:
        event_id = canonical_event["event_id"]
        idempotency_key = canonical_event["idempotency_key"]
        payload = canonical_event.get("payload", {}) if isinstance(canonical_event.get("payload"), dict) else {}
        source = canonical_event.get("source", {}) if isinstance(canonical_event.get("source"), dict) else {}

        if not self.enabled:
            _log_factory_action(store, provider=provider, event_id=event_id,
                idempotency_key=idempotency_key, action_name=self.name,
                status="skipped", details={"reason": "disabled"})
            return

        if provider != "factory":
            _log_factory_action(store, provider=provider, event_id=event_id,
                idempotency_key=idempotency_key, action_name=self.name,
                status="skipped", details={"reason": "not_factory_provider"})
            return

        # Only process in production_canary mode for now
        if route_mode not in ("production_canary", "canary_dryrun"):
            _log_factory_action(store, provider=provider, event_id=event_id,
                idempotency_key=idempotency_key, action_name=self.name,
                status="skipped", details={"reason": f"route_mode={route_mode}"})
            return

        run_id = source.get("resource_id") or payload.get("run_id")
        event_type = canonical_event.get("provider_event_type", "")
        project_id = source.get("project_id")

        if not run_id:
            _log_factory_action(store, provider=provider, event_id=event_id,
                idempotency_key=idempotency_key, action_name=self.name,
                status="error", level="ERROR",
                message="missing run_id in factory lifecycle event",
                details={}, project_id=project_id)
            return

        try:
            new_state = self.state_machine.process_event(run_id, event_type)
            _log_factory_action(store, provider=provider, event_id=event_id,
                idempotency_key=idempotency_key, action_name=self.name,
                status="success",
                message=f"lifecycle transition: {event_type} → {new_state.value}",
                details={"run_id": run_id, "new_state": new_state.value, "event_type": event_type},
                project_id=project_id, target_type="factory_lifecycle")
        except LifecycleTransitionError as exc:
            current = self.state_machine.get_state(run_id)
            _log_factory_action(store, provider=provider, event_id=event_id,
                idempotency_key=idempotency_key, action_name=self.name,
                status="error", level="ERROR",
                message=str(exc),
                details={"run_id": run_id, "current_state": current.value if current else None, "event_type": event_type},
                project_id=project_id, target_type="factory_lifecycle")


def _log_factory_action(
    store: Any, *, provider: str, event_id: str, idempotency_key: str,
    action_name: str, status: str, level: str = "INFO",
    message: str | None = None, details: dict[str, Any] | None = None,
    project_id: str | None = None, target_type: str | None = None,
) -> None:
    """Log a factory lifecycle action to the store."""
    store.log(
        provider=provider,
        phase="factory_lifecycle",
        level=level,
        message=message or f"{action_name} {status}",
        event_id=event_id,
        details=details or {},
        route_name="factory.lifecycle",
        action_name=action_name,
        target_type=target_type or action_name,
        status=status,
        attempt=1,
        canonical_event_id=event_id,
        idempotency_key=idempotency_key,
        project_id=project_id,
    )
