# OPS-LINEAR-009: Decouple Canary Comment Action from Webhook Ingress Core Handler

> **Goal**: Read-only design for extracting the controlled Linear canary comment action out of `WebhookIngress.handle()` into an explicit route/action/executor structure.
>
> **Date**: 2026-05-04
> **Status**: Design (READ-ONLY)
> **Parent**: OPS-LINEAR-008 (canary comment in ingress side)
> **Constraint**: READ-ONLY. No code modifications.

---

## 1. Problem Statement

OPS-008 implemented canary comment creation **inside** `WebhookIngress.handle()` via `_maybe_create_canary_comment()`. This piles business-side effects (Linear GraphQL API calls) into the webhook ingress core handler, which should remain focused on:

1. Signature verification
2. Canonical event normalization
3. Idempotency checks
4. Storage
5. Routing/forwarding to n8n

OPS-009 requires an explicit **route → action → executor** invocation chain, where the canary comment is a separate, independently invokable action rather than a side-effect buried in the ingress handler.

---

## 2. Current Architecture (OPS-008)

```
POST /webhooks/linear
  → WebhookIngress.handle()
    → verify signature
    → normalize to canonical event
    → idempotency check
    → save to store
    → forward to n8n (if not shadow)
    → _maybe_create_canary_comment()   ← ❌ business action inside core handler
      → Linear GraphQL API call
```

**Issues**:
- Canary comment is a side-effect in the hot path of every webhook
- Ingress handler knows about Linear GraphQL mutations
- No independent invocation or testing of canary comment logic
- Cannot be routed separately from the main n8n forwarding path
- `_make_linear_canary_commenter` lives in `server.py`, `_is_linear_test_issue_update` in `ingress.py` — scattered responsibilities

---

## 3. Target Architecture (OPS-009)

### 3.1 Layered Separation

```
┌─────────────────────────────────────────────────────────┐
│  routes.py                                               │
│  RouteDispatcher: maps canonical events → action names   │
└───────────────────────┬─────────────────────────────────┘
                        │ route_name
                        ▼
┌─────────────────────────────────────────────────────────┐
│  actions/                                                │
│  ActionRegistry: name → Action (guards + executor)       │
└───────────────────────┬─────────────────────────────────┘
                        │ action.execute(canonical_event)
                        ▼
┌─────────────────────────────────────────────────────────┐
│  executors/                                              │
│  LinearCanaryCommentExecutor: pure side-effect logic     │
└─────────────────────────────────────────────────────────┘
```

### 3.2 Invocation Flow

```
POST /webhooks/linear
  → WebhookIngress.handle()
    → verify, normalize, store, forward to n8n (unchanged)
    → route = RouteDispatcher.match(canonical_event)
    → if route: ActionRegistry.get(route).execute(canonical_event)
```

Key difference: `handle()` no longer contains any provider-specific side-effect logic. It delegates to a routing + action system.

---

## 4. Proposed Module Structure

### 4.1 New Files

```
workspace/tools/webhook_ingress/
├── __init__.py                    # existing, updated exports
├── ingress.py                     # simplified: remove _maybe_create_canary_comment
├── models.py                      # unchanged
├── adapter.py                     # unchanged
├── storage.py                     # unchanged
├── postgres_storage.py            # unchanged
├── server.py                      # updated: move canary_commenter factory to executors
├── routes.py                      # existing RouteMatcher, enhanced
├── routes.yaml                    # unchanged
│
├── actions/                       # NEW directory
│   ├── __init__.py
│   ├── base.py                    # Action base class + registry
│   └── canary_comment.py          # LinearCanaryCommentAction
│
├── executors/                     # NEW directory
│   ├── __init__.py
│   └── linear_canary_comment.py   # LinearCanaryCommentExecutor
│
└── logging/                       # NEW directory (optional, can inline)
    └── __init__.py                # structured log helpers
```

### 4.2 Alternative: Flat Module (Fewer Files)

If the team prefers fewer directories:

```
workspace/tools/webhook_ingress/
├── actions.py                     # Action base, registry, canary_comment action
├── executors.py                   # LinearCanaryCommentExecutor
├── ingress.py                     # simplified
├── server.py                      # updated
└── ... (rest unchanged)
```

**Recommendation**: Use the flat module approach for this minimal decoupling. The actions/executors are single-purpose right now; directories can be introduced when more actions exist.

---

## 5. Detailed Interface Design

### 5.1 `executors/linear_canary_comment.py` (or `executors.py`)

```python
from __future__ import annotations
from typing import Any, Protocol


class LinearCanaryCommentResult:
    """Result of a canary comment execution."""
    def __init__(self, *, success: bool, comment_id: str | None = None, error: str | None = None):
        self.success = success
        self.comment_id = comment_id
        self.error = error


class LinearCanaryCommentExecutor:
    """Pure executor: given a canonical event, post a canary comment to Linear.

    No routing, no gating, no store access. Only: build body → call API → return result.
    """

    def __init__(self, api_token: str, *, timeout: int = 10):
        self.api_token = api_token
        self.timeout = timeout
        self._client: httpx.Client | None = None

    def _get_client(self) -> httpx.Client:
        if self._client is None:
            import httpx
            self._client = httpx.Client(timeout=self.timeout)
        return self._client

    def __call__(self, canonical_event: dict[str, Any]) -> LinearCanaryCommentResult:
        """Execute the canary comment. Returns result, never raises (catches all)."""
        issue_id = canonical_event["source"]["resource_id"]
        body = self._build_comment_body(canonical_event)
        try:
            client = self._get_client()
            response = client.post(
                "https://api.linear.app/graphql",
                headers={"Authorization": self.api_token, "Content-Type": "application/json"},
                json={"query": self._GRAPHQL_MUTATION, "variables": {"issueId": issue_id, "body": body}},
            )
            response.raise_for_status()
            data = response.json()
            if data.get("errors"):
                return LinearCanaryCommentResult(success=False, error=str(data["errors"]))
            result = data.get("data", {}).get("commentCreate", {})
            if not result.get("success"):
                return LinearCanaryCommentResult(success=False, error="commentCreate not successful")
            comment = result.get("comment") or {}
            return LinearCanaryCommentResult(success=True, comment_id=comment.get("id"))
        except Exception as exc:
            return LinearCanaryCommentResult(success=False, error=f"{type(exc).__name__}: {exc}")

    @staticmethod
    def _build_comment_body(canonical_event: dict[str, Any]) -> str:
        payload = canonical_event.get("payload") or {}
        identifier = payload.get("identifier") or canonical_event["source"]["resource_id"]
        return (
            f"[webhook-ingress-canary] OPS-LINEAR-009 canonical event "
            f"{canonical_event['event_id']} accepted for {identifier}."
        )

    _GRAPHQL_MUTATION = """
        mutation CanaryComment($issueId: String!, $body: String!) {
          commentCreate(input: {issueId: $issueId, body: $body}) {
            success
            comment { id }
          }
        }
    """
```

### 5.2 `actions/base.py` (or `actions.py` top section)

```python
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Protocol


class ActionGuard(Protocol):
    """Returns True if the action should proceed for this event."""
    def __call__(self, canonical_event: dict[str, Any]) -> bool: ...


@dataclass(frozen=True)
class ActionResult:
    action_name: str
    success: bool
    details: dict[str, Any] | None = None
    error: str | None = None


class Action(Protocol):
    """An action has a name, guards, and an executor."""
    @property
    def name(self) -> str: ...
    def guards(self) -> list[ActionGuard]: ...
    def execute(self, canonical_event: dict[str, Any]) -> ActionResult: ...


class ActionRegistry:
    """Thread-safe registry of named actions."""

    def __init__(self):
        self._actions: dict[str, Action] = {}

    def register(self, action: Action) -> None:
        self._actions[action.name] = action

    def get(self, name: str) -> Action | None:
        return self._actions.get(name)

    def dispatch(self, route_name: str, canonical_event: dict[str, Any]) -> ActionResult | None:
        """Lookup action by route name and execute it. Returns None if no action registered."""
        action = self.get(route_name)
        if action is None:
            return None
        # Run all guards
        for guard in action.guards():
            if not guard(canonical_event):
                return ActionResult(action_name=action.name, success=False, details={"reason": "guard_rejected"})
        return action.execute(canonical_event)
```

### 5.3 `actions/canary_comment.py` (or `actions.py` continuation)

```python
from __future__ import annotations
from typing import Any

from .base import Action, ActionResult, ActionGuard


def _is_linear_test_issue_update(canonical_event: dict[str, Any]) -> bool:
    """Guard: only process Linear test issue updates."""
    if canonical_event.get("provider") != "linear":
        return False
    if canonical_event.get("canonical_type") != "issue" or canonical_event.get("canonical_action") != "updated":
        return False
    payload = canonical_event.get("payload") or {}
    title = str(payload.get("title") or "")
    if "[webhook-ingress-canary]" in title:
        return True
    identifier = str(payload.get("identifier") or "")
    metadata = payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {}
    allowed_identifiers = metadata.get("canary_allowed_identifiers")
    if isinstance(allowed_identifiers, list) and identifier in allowed_identifiers:
        return True
    labels = payload.get("labels") if isinstance(payload.get("labels"), list) else []
    return any(str(label).lower() == "webhook-ingress-canary" for label in labels)


def _is_production_canary_mode(route_mode: str) -> ActionGuard:
    """Guard factory: only run in production_canary mode."""
    def guard(canonical_event: dict[str, Any]) -> bool:
        return route_mode == "production_canary"
    return guard


def _is_enabled_flag(flag: bool) -> ActionGuard:
    """Guard factory: check enabled flag."""
    def guard(canonical_event: dict[str, Any]) -> bool:
        return flag
    return guard


class LinearCanaryCommentAction(Action):
    @property
    def name(self) -> str:
        return "linear.canary_comment"

    def __init__(
        self,
        executor,                     # LinearCanaryCommentExecutor
        *,
        route_mode: str,
        enabled: bool,
        store=None,                   # WebhookEventStore for logging
    ):
        self._executor = executor
        self._store = store
        self._guards: list[ActionGuard] = [
            _is_production_canary_mode(route_mode),
            _is_enabled_flag(enabled),
            _is_linear_test_issue_update,
        ]

    def guards(self) -> list[ActionGuard]:
        return self._guards

    def execute(self, canonical_event: dict[str, Any]) -> ActionResult:
        event_id = canonical_event.get("event_id", "unknown")
        provider = canonical_event.get("provider", "unknown")

        result = self._executor(canonical_event)

        if self._store:
            self._store.log(
                provider=provider,
                phase="canary_action",
                level="INFO" if result.success else "ERROR",
                message="linear canary comment created" if result.success else "linear canary comment failed",
                event_id=event_id,
                details={"comment_id": result.comment_id} if result.comment_id else {"error": result.error},
                route_name="linear.production_canary",
                target_type="linear_comment_canary",
                status="success" if result.success else "error",
                attempt=1,
                canonical_event_id=event_id,
            )

        return ActionResult(
            action_name=self.name,
            success=result.success,
            details={"comment_id": result.comment_id} if result.comment_id else None,
            error=result.error,
        )
```

### 5.4 `ingress.py` — Simplified `WebhookIngress`

```python
# REMOVE from __init__:
#   - canary_commenter: CanaryCommenter | None = None
#   - canary_comment_enabled: bool = False
# REMOVE entire method:
#   - _maybe_create_canary_comment()
# REMOVE function:
#   - _is_linear_test_issue_update()

# ADD to __init__:
#   - action_registry: ActionRegistry | None = None

# ADD at end of handle() (after forwarding log, before ack return):
#   self._dispatch_actions(canonical_event)

# ADD method:
def _dispatch_actions(self, canonical_event: dict | None) -> None:
    if not canonical_event or not self.action_registry:
        return
    # Derive route_name from route_mode + provider
    route_name = f"{self.adapters.keys().__iter__().__next__()}.production_canary" if self.route_mode == "production_canary" else None
    if route_name:
        self.action_registry.dispatch(route_name, canonical_event)
```

**Better**: Route name comes from `RouteMatcher` or from config, not computed ad-hoc. The `server.py` build step wires it.

### 5.5 `server.py` — Wiring Changes

```python
# REMOVE: _make_linear_canary_commenter() function
# REMOVE: _linear_comment_body() function
# The executor is now created from the executors module.

def _build_ingress(config: ServerConfig) -> WebhookIngress:
    # ... existing store, n8n_sender setup unchanged ...

    # NEW: build action registry
    from .actions import ActionRegistry
    from .actions.canary_comment import LinearCanaryCommentAction
    from .executors.linear_canary_comment import LinearCanaryCommentExecutor

    action_registry = ActionRegistry()

    if config.linear_canary_comment_enabled and config.linear_canary_api_token:
        executor = LinearCanaryCommentExecutor(config.linear_canary_api_token)
        canary_action = LinearCanaryCommentAction(
            executor,
            route_mode=config.ingress_mode,
            enabled=config.linear_canary_comment_enabled,
            store=store,
        )
        action_registry.register(canary_action)

    return WebhookIngress(
        linear_secret=config.linear_secret,
        store=store,
        n8n_sender=n8n_sender,
        route_mode=config.ingress_mode,
        action_registry=action_registry,   # NEW parameter
    )
```

### 5.6 `routes.py` Enhancement

```python
class RouteMatcher:
    # ... existing match() and ingress_path() unchanged ...

    def action_route_name(self, event: dict) -> str | None:
        """Derive an action route name from the canonical event.

        Returns e.g. 'linear.canary_comment' for production_canary mode events,
        or None if no action should be dispatched.
        """
        delivery_mode = event.get("delivery_mode")
        provider = event.get("provider", "linear")
        if delivery_mode == "production_canary":
            return f"{provider}.canary_comment"
        return None
```

---

## 6. Logging Strategy

### 6.1 Logging Remains in `WebhookEventStore.log()`

No changes to the logging interface. Actions use the same `store.log()` calls with the same fields:

| Field | Value |
|-------|-------|
| `phase` | `"canary_action"` |
| `route_name` | `"linear.production_canary"` |
| `target_type` | `"linear_comment_canary"` |
| `status` | `"success"`, `"error"`, `"skipped"` |
| `details` | `{"comment_id": "..."}` or `{"error": "..."}` |

### 6.2 Guard Rejection Logging

When a guard rejects, the action returns `ActionResult(success=False, details={"reason": "guard_rejected"})`. The caller (`_dispatch_actions`) can optionally log:

```python
def _dispatch_actions(self, canonical_event: dict | None) -> None:
    if not canonical_event or not self.action_registry:
        return
    route_name = self._resolve_action_route(canonical_event)
    if not route_name:
        return
    result = self.action_registry.dispatch(route_name, canonical_event)
    if result and not result.success:
        self.store.log(
            provider=canonical_event.get("provider", "unknown"),
            phase="canary_action",
            level="INFO",
            message="linear canary comment skipped",
            event_id=canonical_event.get("event_id"),
            details={"reason": result.details.get("reason") if result.details else "unknown"},
            route_name=route_name,
            target_type="linear_comment_canary",
            status="skipped",
            attempt=1,
            canonical_event_id=canonical_event.get("event_id"),
        )
```

---

## 7. Test Plan

### 7.1 Unit Tests (New File: `tests/test_actions.py`)

```python
# Test executor in isolation (no ingress, no store)
class TestLinearCanaryCommentExecutor:
    def test_success_returns_comment_id(self, mock_httpx):
        executor = LinearCanaryCommentExecutor("lin_api_test")
        result = executor(canonical_event_for_test_issue())
        assert result.success
        assert result.comment_id is not None

    def test_api_error_returns_failure(self, mock_httpx_error):
        executor = LinearCanaryCommentExecutor("lin_api_test")
        result = executor(canonical_event_for_test_issue())
        assert not result.success
        assert result.error is not None

    def test_comment_body_has_correct_prefix(self, mock_httpx):
        executor = LinearCanaryCommentExecutor("lin_api_test")
        # Intercept the request to verify body
        result = executor(canonical_event_for_test_issue())
        assert "[webhook-ingress-canary]" in captured_request_body


# Test action with guards
class TestLinearCanaryCommentAction:
    def test_runs_in_production_canary_mode(self):
        action = make_action(route_mode="production_canary", enabled=True)
        result = action.execute(canonical_event_for_test_issue())
        assert result.success

    def test_rejected_in_live_mode(self):
        action = make_action(route_mode="live", enabled=True)
        # Guard rejects before executor is called
        result = action.execute(canonical_event_for_test_issue())
        # Via dispatch, guard rejects
        assert ...

    def test_rejected_when_not_test_issue(self):
        action = make_action(route_mode="production_canary", enabled=True)
        result = action.execute(canonical_event_for_production_issue())
        # Guard _is_linear_test_issue_update rejects

    def test_rejected_when_disabled(self):
        action = make_action(route_mode="production_canary", enabled=False)
        # Guard rejects


# Test registry dispatch
class TestActionRegistry:
    def test_dispatch_calls_action(self):
        registry = ActionRegistry()
        registry.register(mock_action)
        result = registry.dispatch("linear.canary_comment", canonical_event)
        assert result is not None

    def test_dispatch_returns_none_for_unknown_route(self):
        registry = ActionRegistry()
        result = registry.dispatch("unknown.route", canonical_event)
        assert result is None
```

### 7.2 Integration Tests

```python
class TestIngressWithActionRegistry:
    def test_production_canary_dispatches_canary_comment(self, mock_executor, mock_store):
        registry = ActionRegistry()
        registry.register(LinearCanaryCommentAction(mock_executor, route_mode="production_canary", enabled=True, store=mock_store))
        ingress = WebhookIngress(linear_secret="test", store=mock_store, route_mode="production_canary", action_registry=registry)
        result = ingress.handle(make_webhook_request_for_test_issue())
        assert result.forwarded_to_n8n
        # Verify executor was called exactly once
        assert mock_executor.call_count == 1

    def test_live_mode_does_not_dispatch_canary_comment(self, mock_executor, mock_store):
        registry = ActionRegistry()
        registry.register(LinearCanaryCommentAction(mock_executor, route_mode="production_canary", enabled=True, store=mock_store))
        ingress = WebhookIngress(linear_secret="test", store=mock_store, route_mode="live", action_registry=registry)
        result = ingress.handle(make_webhook_request_for_test_issue())
        assert mock_executor.call_count == 0

    def test_shadow_mode_does_not_dispatch(self, mock_executor, mock_store):
        ...

    def test_duplicate_event_does_not_re_dispatch(self, mock_executor, mock_store):
        # First call: dispatched
        # Second call with same idempotency: duplicate_accepted, no dispatch
        ...
```

### 7.3 Test Fixtures

```python
def canonical_event_for_test_issue():
    return {
        "canonical_version": "v1",
        "event_id": "evt_test",
        "provider": "linear",
        "canonical_type": "issue",
        "canonical_action": "updated",
        "payload": {
            "id": "uuid-123",
            "identifier": "JTO-TEST",
            "title": "ops-linear-009-decoupling-test",
            "metadata": {},
        },
        "source": {"resource_id": "uuid-123"},
        "idempotency_key": "linear:test-delivery",
        "received_at": "2026-05-04T12:00:00Z",
        "timestamp": "2026-05-04T12:00:00Z",
        "provider_event_type": "Issue",
        "provider_action": "update",
    }

def canonical_event_for_production_issue():
    event = canonical_event_for_test_issue()
    event["payload"]["title"] = "Real production bug fix"
    return event
```

---

## 8. Patch Plan (File-by-File)

### Phase 1: New Files

| # | File | Purpose |
|---|------|---------|
| 1 | `workspace/tools/webhook_ingress/actions.py` | `Action`, `ActionGuard`, `ActionResult`, `ActionRegistry`, `LinearCanaryCommentAction` |
| 2 | `workspace/tools/webhook_ingress/executors.py` | `LinearCanaryCommentExecutor`, `LinearCanaryCommentResult` |
| 3 | `workspace/tools/webhook_ingress/tests/test_actions.py` | Unit tests for executor, action, registry |

### Phase 2: Modified Files

| # | File | Changes |
|---|------|---------|
| 4 | `ingress.py` | Remove `CanaryCommenter` protocol, `canary_commenter`/`canary_comment_enabled` params, `_maybe_create_canary_comment()` method, `_is_linear_test_issue_update()` function. Add `action_registry` param and `_dispatch_actions()` method. |
| 5 | `server.py` | Remove `_make_linear_canary_commenter()`, `_linear_comment_body()`. Import from `executors` + `actions`. Build `ActionRegistry` and pass to `WebhookIngress`. |
| 6 | `__init__.py` | Add exports for `ActionRegistry`, `ActionResult`, `LinearCanaryCommentExecutor`, `LinearCanaryCommentResult`. |

### Phase 3: Verification

| # | Action | Expected |
|---|--------|----------|
| 7 | Run existing tests | All pass (no regression) |
| 8 | Run new action tests | All pass |
| 9 | Manual: POST test issue webhook | Canary comment posted, logged |
| 10 | Manual: POST production issue webhook | No canary comment, no dispatch |
| 11 | Manual: shadow mode webhook | No dispatch |

---

## 9. Backward Compatibility

### 9.1 `CanaryCommenter` Protocol Removal

The `CanaryCommenter` Protocol in `ingress.py` is replaced by `LinearCanaryCommentExecutor.__call__`. The signature is identical: `def __call__(self, canonical_event: dict) -> str | None`. However, `Executor.__call__` returns `LinearCanaryCommentResult` instead of `str | None`. This is an internal API change; no external consumers exist.

### 9.2 `WebhookIngress.__init__` Signature Change

**Before**:
```python
def __init__(self, *, linear_secret, store=None, n8n_sender=None,
             route_mode="live", canary_commenter=None, canary_comment_enabled=False):
```

**After**:
```python
def __init__(self, *, linear_secret, store=None, n8n_sender=None,
             route_mode="live", action_registry=None):
```

Only `server.py` calls this constructor, so the change is localized.

### 9.3 Server Configuration (No Change)

Environment variables remain the same:
- `LINEAR_CANARY_COMMENT_ENABLED`
- `LINEAR_CANARY_API_TOKEN`
- `WEBHOOK_INGRESS_MODE`

---

## 10. Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Guard logic regression | Low | High | Full unit test coverage of each guard |
| Executor API behavior change | Low | Medium | Executor has same GraphQL mutation as before |
| Action registry dispatch missing events | Low | Medium | Integration test with real ingress flow |
| Logging format drift | Very Low | Low | Same `store.log()` call pattern reused |
| New test coverage gaps | Medium | Low | Test plan covers executor, action, registry, integration |

---

## 11. Implementation Notes

1. **Start with flat files** (`actions.py`, `executors.py`) rather than directories. Directories add overhead for single-file modules.
2. **Keep `_is_linear_test_issue_update` logic unchanged** — move it from `ingress.py` to `actions.py` as-is. No behavior change.
3. **The GraphQL mutation string** stays identical to OPS-008. Only the wrapper changes.
4. **`store.log()` calls** move from `_maybe_create_canary_comment` into `LinearCanaryCommentAction.execute()` and `_dispatch_actions()`.
5. **`server.py`** should import from the new modules, not contain executor construction logic.
6. **No new dependencies** — `httpx` is already used in `server.py`.

---

## 12. Future Extension Points

Once decoupled, the action/executor pattern supports:

- **Multiple actions per route**: e.g., `linear.canary_comment` + `linear.sync_to_supabase`
- **Async executors**: `AsyncLinearCanaryCommentExecutor` for non-blocking execution
- **Action chaining**: dispatch multiple actions sequentially
- **Per-provider action registries**: different action sets for GitHub, Linear, etc.
- **Action retry**: executor returns `should_retry=True` with backoff

None of these are in scope for OPS-009. The design supports them without modification.

---

**Document Status**: Design Complete  
**Next Step**: Create OPS-LINEAR-009 implementation task with this design as reference  
**Reviewer**: TBD
