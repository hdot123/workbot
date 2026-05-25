from __future__ import annotations

from typing import Any, Protocol

from .executors import FactoryDispatchDryRunExecutor, LinearCanaryCommentExecutor

CANARY_LABEL_NAME = "webhook-ingress-canary"


class Action(Protocol):
    name: str

    def run(self, *, provider: str, route_mode: str, canonical_event: dict[str, Any], store: Any) -> None: ...


class ActionRegistry:
    def __init__(self, actions: list[Action] | None = None):
        self._actions = list(actions or [])

    def run(self, *, provider: str, route_mode: str, canonical_event: dict[str, Any], store: Any) -> None:
        for action in self._actions:
            action.run(provider=provider, route_mode=route_mode, canonical_event=canonical_event, store=store)


class FactoryDispatchDryRunAction:
    name = "factory_dispatch_dryrun"

    def __init__(
        self,
        *,
        executor: FactoryDispatchDryRunExecutor,
        enabled: bool,
        allowed_project_ids: set[str] | None = None,
        ready_state_names: set[str] | None = None,
    ):
        self.executor = executor
        self.enabled = enabled
        self.allowed_project_ids = {project_id for project_id in (allowed_project_ids or set()) if project_id}
        self.ready_state_names = {name.strip().lower() for name in (ready_state_names or {"Ready for Factory"}) if name.strip()}

    def run(self, *, provider: str, route_mode: str, canonical_event: dict[str, Any], store: Any) -> None:
        event_id = canonical_event["event_id"]
        idempotency_key = canonical_event["idempotency_key"]
        project_id = _project_id(canonical_event)
        if route_mode != "production_canary" or not self.enabled:
            _log_action(
                store,
                provider=provider,
                event_id=event_id,
                idempotency_key=idempotency_key,
                action_name=self.name,
                status="skipped",
                details={"reason": "disabled"},
                project_id=project_id,
            )
            return
        if not is_factory_ready_project_issue_transition(
            canonical_event,
            allowed_project_ids=self.allowed_project_ids,
            ready_state_names=self.ready_state_names,
        ):
            _log_action(
                store,
                provider=provider,
                event_id=event_id,
                idempotency_key=idempotency_key,
                action_name=self.name,
                status="skipped",
                details={"reason": "not_factory_ready_project_issue_transition"},
                project_id=project_id,
            )
            return
        result = self.executor.execute(canonical_event)
        _log_action(
            store,
            provider=provider,
            event_id=event_id,
            idempotency_key=idempotency_key,
            action_name=self.name,
            status="success",
            message="factory dispatch dry-run payload generated",
            details={"action_result_json": result.action_result_json},
            project_id=project_id,
            target_type="factory_dispatch_dryrun",
        )


class LinearCanaryCommentAction:
    name = "linear_canary_comment"

    def __init__(self, *, executor: LinearCanaryCommentExecutor, enabled: bool, allowed_project_ids: set[str] | None = None):
        self.executor = executor
        self.enabled = enabled
        self.allowed_project_ids = {project_id for project_id in (allowed_project_ids or set()) if project_id}

    def run(self, *, provider: str, route_mode: str, canonical_event: dict[str, Any], store: Any) -> None:
        event_id = canonical_event["event_id"]
        idempotency_key = canonical_event["idempotency_key"]
        project_id = _project_id(canonical_event)
        if route_mode != "production_canary" or not self.enabled:
            _log_action(
                store,
                provider=provider,
                event_id=event_id,
                idempotency_key=idempotency_key,
                action_name=self.name,
                status="skipped",
                details={"reason": "disabled"},
                project_id=project_id,
            )
            return
        if not is_project_scoped_linear_issue_update(canonical_event, allowed_project_ids=self.allowed_project_ids):
            _log_action(
                store,
                provider=provider,
                event_id=event_id,
                idempotency_key=idempotency_key,
                action_name=self.name,
                status="skipped",
                details={"reason": "not_project_scoped_issue_update"},
                project_id=project_id,
            )
            return
        try:
            result = self.executor.execute(canonical_event)
        except Exception as exc:
            _log_action(
                store,
                provider=provider,
                event_id=event_id,
                idempotency_key=idempotency_key,
                action_name=self.name,
                status="error",
                level="ERROR",
                message="linear canary comment failed",
                details={"error_type": type(exc).__name__},
                project_id=project_id,
                target_type="linear_comment_canary",
            )
            return
        _log_action(
            store,
            provider=provider,
            event_id=event_id,
            idempotency_key=idempotency_key,
            action_name=self.name,
            status="success",
            message="linear canary comment created",
            details={"comment_id": result.comment_id} if result.comment_id else {},
            project_id=project_id,
            target_type="linear_comment_canary",
        )


def is_factory_ready_project_issue_transition(
    canonical_event: dict[str, Any],
    *,
    allowed_project_ids: set[str] | None = None,
    ready_state_names: set[str] | None = None,
) -> bool:
    if canonical_event.get("provider") != "linear":
        return False
    if canonical_event.get("canonical_type") != "issue" or canonical_event.get("canonical_action") != "updated":
        return False
    project_id = _project_id(canonical_event)
    if allowed_project_ids and (not project_id or project_id not in allowed_project_ids):
        return False
    payload = canonical_event.get("payload") if isinstance(canonical_event.get("payload"), dict) else {}
    current_state = str(payload.get("state") or "").strip().lower()
    previous_state = payload.get("previous_state")
    previous_state_normalized = str(previous_state).strip().lower() if previous_state else None
    ready_names = {name.strip().lower() for name in (ready_state_names or {"Ready for Factory"}) if name.strip()}
    if current_state not in ready_names:
        return False
    if previous_state_normalized in ready_names:
        return False
    return True


def is_project_scoped_linear_issue_update(canonical_event: dict[str, Any], *, allowed_project_ids: set[str] | None = None) -> bool:
    if canonical_event.get("provider") != "linear":
        return False
    if canonical_event.get("canonical_type") != "issue" or canonical_event.get("canonical_action") != "updated":
        return False
    if not allowed_project_ids:
        return is_labelled_linear_issue_update(canonical_event)
    project_id = _project_id(canonical_event)
    return bool(project_id and project_id in allowed_project_ids)


def is_labelled_linear_issue_update(canonical_event: dict[str, Any]) -> bool:
    if canonical_event.get("provider") != "linear":
        return False
    if canonical_event.get("canonical_type") != "issue" or canonical_event.get("canonical_action") != "updated":
        return False
    return CANARY_LABEL_NAME in _label_names(canonical_event)


def _project_id(canonical_event: dict[str, Any]) -> str | None:
    source = canonical_event.get("source") if isinstance(canonical_event.get("source"), dict) else {}
    payload = canonical_event.get("payload") if isinstance(canonical_event.get("payload"), dict) else {}
    project_id = source.get("project_id") or payload.get("project_id")
    return str(project_id) if project_id else None


def _label_names(canonical_event: dict[str, Any]) -> set[str]:
    payload = canonical_event.get("payload") or {}
    labels = payload.get("labels") if isinstance(payload.get("labels"), list) else []
    names: set[str] = set()
    for label in labels:
        if isinstance(label, dict):
            name = label.get("name") or label.get("id")
        else:
            name = label
        if name:
            names.add(str(name).strip().lower())
    return names


def _log_action(
    store: Any,
    *,
    provider: str,
    event_id: str,
    idempotency_key: str,
    action_name: str,
    status: str,
    level: str = "INFO",
    message: str | None = None,
    details: dict[str, Any] | None = None,
    project_id: str | None = None,
    target_type: str | None = None,
) -> None:
    store.log(
        provider=provider,
        phase="canary_action",
        level=level,
        message=message or f"{action_name} {status}",
        event_id=event_id,
        details=details or {},
        route_name="linear.production_canary",
        action_name=action_name,
        target_type=target_type or action_name,
        status=status,
        attempt=1,
        canonical_event_id=event_id,
        idempotency_key=idempotency_key,
        project_id=project_id,
    )
