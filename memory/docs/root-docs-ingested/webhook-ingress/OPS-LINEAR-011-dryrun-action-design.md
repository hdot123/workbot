# OPS-LINEAR-011: FactoryDispatchDryRunAction/Executor Design

> **Goal**: Read-only design for a DryRun action preserving ActionRegistry/Executor architecture.  
> **Date**: 2026-05-04  
> **Status**: Design (READ-ONLY)  
> **Parent**: OPS-LINEAR-010 (canary label scope refinement)  
> **Constraint**: READ-ONLY. No code modifications. Writes to processing log only. No external network calls.

---

## 1. Problem Statement

The webhook ingress system needs a **dry-run dispatch action** that:

1. Evaluates whether a canonical event **would** trigger downstream processing, without actually doing it
2. Is **independent** from the ingress handler — follows the same Action → Executor pattern as `LinearCanaryCommentAction`
3. Is **project scoped** — only evaluates events for configured project IDs
4. Is **Ready state scoped** — only evaluates events whose payload state maps to a Ready-equivalent state
5. **Writes only to the processing log** — no n8n forwarding, no Linear API calls, no external network calls
6. Provides an auditable trail of "what would happen" for each qualifying event

This action enables pre-flight validation before enabling real `production_canary` dispatch.

---

## 2. Existing Architecture Reference

### 2.1 Current Action/Executor Pattern

```
WebhookIngress.handle()
  → verify → normalize → store → forward to n8n
  → action_registry.run(provider=..., route_mode=..., canonical_event=..., store=...)
     → Action.run()
        → guards check (route_mode, enabled, project_id, etc.)
        → executor.execute(canonical_event)  ← may call external APIs
        → store.log(result)
```

### 2.2 Key Modules

| Module | Role |
|--------|------|
| `actions.py` | `Action` Protocol, `ActionRegistry`, `LinearCanaryCommentAction` |
| `executors.py` | `LinearCanaryCommentExecutor` — pure side-effect logic |
| `ingress.py` | `WebhookIngress.handle()` — orchestrates flow |
| `storage.py` | `WebhookEventStore.log()` — structured logging |
| `postgres_storage.py` | PostgreSQL implementation of `log()` |

### 2.3 Existing Log Fields

The `store.log()` method accepts these fields:
- `provider`, `phase`, `level`, `message`, `event_id`
- `details` (JSON dict with arbitrary keys)
- `route_name`, `target_type`, `status`, `attempt`
- `canonical_event_id`, `action_name`, `idempotency_key`, `project_id`

---

## 3. Target Architecture

### 3.1 Design Principles

| Principle | Rationale |
|-----------|-----------|
| **Independent from ingress handler** | DryRun action is not embedded in `handle()`; it's a registered action in `ActionRegistry` like any other |
| **Project scoped** | Only evaluates events whose `project_id` is in `DRYRUN_ALLOWED_PROJECT_IDS` |
| **Ready state scoped** | Only evaluates events whose payload state is in `DRYRUN_READY_STATES` |
| **Write-only to processing log** | No `httpx` calls, no n8n forwarding, no Linear GraphQL — only `store.log()` |
| **No external network calls** | Executor is pure computation: read event → evaluate → return result dict |

### 3.2 Invocation Flow

```
POST /webhooks/linear
  → WebhookIngress.handle()
    → verify, normalize, store, forward to n8n (unchanged)
    → action_registry.run(...)
       → LinearCanaryCommentAction (existing, in production_canary mode only)
       → FactoryDispatchDryRunAction (NEW, always runs regardless of route_mode)
          → guards: project_id ∈ allowed, state ∈ ready_states
          → executor.evaluate(canonical_event)  ← pure computation
          → store.log("dry_run_evaluated", details={would_dispatch, reasons, ...})
```

### 3.3 Why Always-Run (Not Mode-Gated)

The dry-run action is an **observability** action, not a side-effect action. It should evaluate every qualifying event to build a complete audit trail of "what would dispatch", regardless of the current `route_mode`. This is fundamentally different from `LinearCanaryCommentAction` which is mode-gated to `production_canary` only.

---

## 4. Proposed Classes and Interfaces

### 4.1 `FactoryDispatchDryRunResult`

```python
from __future__ import annotations
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class FactoryDispatchDryRunResult:
    """Result of a dry-run dispatch evaluation.

    No external side effects. Pure computation result.
    """
    event_id: str
    would_dispatch: bool
    reasons: list[str]              # Why dispatch would / would-not happen
    project_id: str | None
    state: str | None
    canonical_type: str
    canonical_action: str
    metadata: dict[str, Any]        # Extensible: extra evaluation details
```

### 4.2 `FactoryDispatchDryRunExecutor`

```python
from __future__ import annotations
from typing import Any


class FactoryDispatchDryRunExecutor:
    """Pure computation executor: evaluates a canonical event for dispatch eligibility.

    Zero external network calls. Reads event → applies rules → returns result.
    """

    def __init__(
        self,
        *,
        allowed_project_ids: set[str] | None = None,
        ready_states: set[str] | None = None,
    ):
        self.allowed_project_ids = allowed_project_ids or set()
        self.ready_states = {s.lower().strip() for s in (ready_states or set())}

    def evaluate(self, canonical_event: dict[str, Any]) -> FactoryDispatchDryRunResult:
        """Evaluate dispatch eligibility. Never raises; never calls external systems."""
        event_id = canonical_event.get("event_id", "unknown")
        project_id = _extract_project_id(canonical_event)
        state = _extract_state(canonical_event)
        canonical_type = canonical_event.get("canonical_type", "unknown")
        canonical_action = canonical_event.get("canonical_action", "unknown")

        reasons: list[str] = []
        would_dispatch = True

        # Guard 1: project scope
        if self.allowed_project_ids:
            if not project_id or project_id not in self.allowed_project_ids:
                would_dispatch = False
                reasons.append(f"project_id '{project_id}' not in allowed set")
            else:
                reasons.append(f"project_id '{project_id}' is allowed")
        else:
            reasons.append("no project_id filter configured")

        # Guard 2: ready state scope
        if self.ready_states:
            state_lower = (state or "").lower().strip()
            if state_lower not in self.ready_states:
                would_dispatch = False
                reasons.append(f"state '{state}' not in ready states {self.ready_states}")
            else:
                reasons.append(f"state '{state}' is a ready state")
        else:
            reasons.append("no ready state filter configured")

        # Guard 3: must be an issue update
        if canonical_type != "issue" or canonical_action != "updated":
            would_dispatch = False
            reasons.append(f"canonical_type={canonical_type}, canonical_action={canonical_action} — not issue.updated")
        else:
            reasons.append("is issue.updated event")

        return FactoryDispatchDryRunResult(
            event_id=event_id,
            would_dispatch=would_dispatch,
            reasons=reasons,
            project_id=project_id,
            state=state,
            canonical_type=canonical_type,
            canonical_action=canonical_action,
            metadata={
                "provider": canonical_event.get("provider"),
                "idempotency_key": canonical_event.get("idempotency_key"),
                "resource_id": canonical_event.get("source", {}).get("resource_id"),
            },
        )
```

### 4.3 `FactoryDispatchDryRunAction`

```python
from __future__ import annotations
from typing import Any


class FactoryDispatchDryRunAction:
    """Action that evaluates dispatch eligibility and logs the result.

    Always runs (not mode-gated). Independent from ingress handler.
    Writes only to processing log. No external network calls.
    """
    name = "factory_dispatch_dryrun"

    def __init__(
        self,
        *,
        executor: FactoryDispatchDryRunExecutor,
        enabled: bool = True,
    ):
        self.executor = executor
        self.enabled = enabled

    def run(
        self,
        *,
        provider: str,
        route_mode: str,
        canonical_event: dict[str, Any],
        store: Any,
    ) -> None:
        if not self.enabled:
            _log_dryrun(
                store,
                provider=provider,
                canonical_event=canonical_event,
                status="skipped",
                message="dry-run action disabled",
                details={"reason": "disabled"},
            )
            return

        try:
            result = self.executor.evaluate(canonical_event)
        except Exception as exc:
            _log_dryrun(
                store,
                provider=provider,
                canonical_event=canonical_event,
                status="error",
                level="ERROR",
                message="dry-run evaluation failed",
                details={"error_type": type(exc).__name__, "error": str(exc)},
            )
            return

        _log_dryrun(
            store,
            provider=provider,
            canonical_event=canonical_event,
            status="evaluated",
            message=f"dry-run: would_dispatch={result.would_dispatch}",
            details={
                "would_dispatch": result.would_dispatch,
                "reasons": result.reasons,
                "project_id": result.project_id,
                "state": result.state,
            },
        )
```

### 4.4 Log Helper

```python
def _log_dryrun(
    store: Any,
    *,
    provider: str,
    canonical_event: dict[str, Any],
    status: str,
    message: str,
    level: str = "INFO",
    details: dict[str, Any] | None = None,
) -> None:
    event_id = canonical_event.get("event_id")
    idempotency_key = canonical_event.get("idempotency_key")
    project_id = canonical_event.get("source", {}).get("project_id")

    store.log(
        provider=provider,
        phase="dryrun_dispatch_eval",
        level=level,
        message=message,
        event_id=event_id,
        details=details or {},
        route_name="factory.dispatch_dryrun",
        target_type="dispatch_evaluator",
        status=status,
        attempt=1,
        canonical_event_id=event_id,
        idempotency_key=idempotency_key,
        project_id=str(project_id) if project_id else None,
    )
```

### 4.5 Project ID and State Extractors

```python
def _extract_project_id(canonical_event: dict[str, Any]) -> str | None:
    source = canonical_event.get("source") if isinstance(canonical_event.get("source"), dict) else {}
    payload = canonical_event.get("payload") if isinstance(canonical_event.get("payload"), dict) else {}
    project_id = source.get("project_id") or payload.get("project_id") or payload.get("team", {}).get("id")
    return str(project_id) if project_id else None


def _extract_state(canonical_event: dict[str, Any]) -> str | None:
    payload = canonical_event.get("payload") or {}
    state = payload.get("state")
    if isinstance(state, dict):
        return state.get("name") or state.get("id")
    return str(state) if state else None
```

---

## 5. Environment Variables

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `FACTORY_DRYRUN_ENABLED` | bool | `true` | Enable/disable the dry-run action |
| `FACTORY_DRYRUN_ALLOWED_PROJECT_IDS` | CSV | _(empty)_ | Comma-separated project IDs to evaluate; empty = no filter |
| `FACTORY_DRYRUN_READY_STATES` | CSV | `"ready,in_progress"` | Comma-separated state names considered "ready" for dispatch |

### 5.1 ServerConfig Extension

```python
# In server.py ServerConfig:

@dataclass
class ServerConfig:
    # ... existing fields unchanged ...
    factory_dryrun_enabled: bool = True
    factory_dryrun_allowed_project_ids: set[str] | None = None
    factory_dryrun_ready_states: set[str] | None = None

    @classmethod
    def from_env(cls) -> "ServerConfig":
        return cls(
            # ... existing fields unchanged ...
            factory_dryrun_enabled=os.environ.get("FACTORY_DRYRUN_ENABLED", "true").lower() in {"1", "true", "yes"},
            factory_dryrun_allowed_project_ids=_parse_csv_set(os.environ.get("FACTORY_DRYRUN_ALLOWED_PROJECT_IDS")),
            factory_dryrun_ready_states=_parse_csv_set(os.environ.get("FACTORY_DRYRUN_READY_STATES")),
        )
```

### 5.2 Wiring in `_build_ingress()`

```python
# In server.py _build_ingress():

from .actions import ActionRegistry, LinearCanaryCommentAction, FactoryDispatchDryRunAction
from .executors import LinearCanaryCommentExecutor, FactoryDispatchDryRunExecutor

actions: list = []

# Existing canary action (unchanged)
if config.linear_canary_comment_enabled and config.linear_canary_api_token:
    actions.append(LinearCanaryCommentAction(
        executor=LinearCanaryCommentExecutor(api_token=config.linear_canary_api_token),
        enabled=True,
        allowed_project_ids=config.linear_canary_allowed_project_ids,
    ))

# NEW: dry-run dispatch action
actions.append(FactoryDispatchDryRunAction(
    executor=FactoryDispatchDryRunExecutor(
        allowed_project_ids=config.factory_dryrun_allowed_project_ids,
        ready_states=config.factory_dryrun_ready_states,
    ),
    enabled=config.factory_dryrun_enabled,
))

action_registry = ActionRegistry(actions)
```

---

## 6. Processing Log Fields

Each dry-run evaluation produces one `webhook_processing_logs` row:

| Column | Value |
|--------|-------|
| `event_id` | `canonical_event["event_id"]` |
| `provider` | e.g. `"linear"` |
| `phase` | `"dryrun_dispatch_eval"` |
| `level` | `"INFO"` (or `"ERROR"` on failure) |
| `message` | `"dry-run: would_dispatch=true"` or `"dry-run: would_dispatch=false"` |
| `details` (JSON) | See below |

### 6.1 `details` JSON Structure

```json
{
  "would_dispatch": true,
  "reasons": [
    "project_id 'abc-123' is allowed",
    "state 'Ready' is a ready state",
    "is issue.updated event"
  ],
  "project_id": "abc-123",
  "state": "Ready",
  "action_name": "factory_dispatch_dryrun",
  "route_name": "factory.dispatch_dryrun",
  "target_type": "dispatch_evaluator",
  "status": "evaluated"
}
```

**Status values**:
- `"evaluated"` — evaluation completed successfully
- `"skipped"` — action disabled
- `"error"` — evaluation raised an exception

---

## 7. Integration with ActionRegistry

### 7.1 No Changes to ActionRegistry

The existing `ActionRegistry.run()` method already supports multiple actions:

```python
class ActionRegistry:
    def __init__(self, actions: list[Action] | None = None):
        self._actions = list(actions or [])

    def run(self, *, provider, route_mode, canonical_event, store):
        for action in self._actions:
            action.run(provider=provider, route_mode=route_mode, canonical_event=canonical_event, store=store)
```

`FactoryDispatchDryRunAction` implements the same `Action` Protocol (`name` + `run(...)`), so it slots in as a new list element. No `ActionRegistry` changes needed.

### 7.2 Execution Order

Actions run in registration order. Recommended order:

1. `LinearCanaryCommentAction` (if enabled) — side-effect action
2. `FactoryDispatchDryRunAction` — observability action

The dry-run action runs **after** any side-effect actions, so it can log the complete picture including whether a canary comment was also triggered.

---

## 8. Module Placement

### 8.1 Recommended: Flat File Approach

Consistent with existing architecture, append to existing files:

| File | Additions |
|------|-----------|
| `tools/webhook_ingress/executors.py` | `FactoryDispatchDryRunResult`, `FactoryDispatchDryRunExecutor` |
| `tools/webhook_ingress/actions.py` | `FactoryDispatchDryRunAction`, `_extract_project_id`, `_extract_state`, `_log_dryrun` |
| `tools/webhook_ingress/server.py` | Config fields, wiring in `_build_ingress()` |
| `tools/webhook_ingress/__init__.py` | Export new classes |

### 8.2 Alternative: Separate Files

If team prefers separation:

| File | Purpose |
|------|---------|
| `tools/webhook_ingress/executors.py` | Keep existing `LinearCanaryComment*` |
| `tools/webhook_ingress/executors/dryrun.py` | `FactoryDispatchDryRunResult`, `FactoryDispatchDryRunExecutor` |
| `tools/webhook_ingress/actions.py` | Keep existing `LinearCanaryCommentAction` |
| `tools/webhook_ingress/actions/dryrun.py` | `FactoryDispatchDryRunAction` |

**Recommendation**: Flat file approach (8.1) — the dry-run action is a single cohesive addition, and the codebase already uses flat files for the canary action.

---

## 9. Guard Logic Detail

### 9.1 Project Scope Guard

```
if allowed_project_ids is configured:
    event must have project_id ∈ allowed_project_ids
else:
    pass (no filtering)
```

Project ID extraction priority:
1. `canonical_event["source"]["project_id"]`
2. `canonical_event["payload"]["project_id"]`
3. `canonical_event["payload"]["team"]["id"]` (Linear convention)

### 9.2 Ready State Guard

```
if ready_states is configured:
    event state name (lowercased) must ∈ ready_states
else:
    pass (no filtering)
```

State name extraction:
- `canonical_event["payload"]["state"]["name"]` (Linear dict form)
- `canonical_event["payload"]["state"]["id"]` (fallback)
- `canonical_event["payload"]["state"]` (string form, fallback)

### 9.3 Canonical Type Guard (Implicit)

The dry-run action implicitly evaluates only `issue.updated` events, because that's the only canonical event type that would trigger downstream factory dispatch. Other event types log `would_dispatch=false` with reason.

---

## 10. What This Action Does NOT Do

| Exclusion | Rationale |
|-----------|-----------|
| No n8n forwarding | That's the ingress handler's `n8n_sender`, not an action concern |
| No Linear API calls | This is dry-run — zero external network calls by design |
| No state mutation | Does not update `webhook_canonical_events` or any other table |
| No dependency on route_mode | Runs in all modes (shadow, canary_dryrun, production_canary, live) |
| No dependency on ingress handler | Independent Action in ActionRegistry |
| No blocking of other actions | Never raises; other actions continue normally |

---

## 11. Code Boundary Summary

```
┌─────────────────────────────────────────────────────────────┐
│  executors.py                                                │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  FactoryDispatchDryRunResult (dataclass)              │    │
│  │    - event_id, would_dispatch, reasons,               │    │
│  │      project_id, state, canonical_type,               │    │
│  │      canonical_action, metadata                       │    │
│  │                                                       │    │
│  │  FactoryDispatchDryRunExecutor                         │    │
│  │    - __init__(allowed_project_ids, ready_states)       │    │
│  │    - evaluate(canonical_event) → Result                │    │
│  │      Guards: project scope, ready state, type/action    │    │
│  └─────────────────────────────────────────────────────┘    │
├─────────────────────────────────────────────────────────────┤
│  actions.py                                                  │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  FactoryDispatchDryRunAction                          │    │
│  │    - name = "factory_dispatch_dryrun"                 │    │
│  │    - __init__(executor, enabled)                      │    │
│  │    - run(provider, route_mode, canonical_event, store) │    │
│  │      → executor.evaluate()                            │    │
│  │      → store.log(phase="dryrun_dispatch_eval")         │    │
│  │                                                       │    │
│  │  _extract_project_id(canonical_event) → str | None     │    │
│  │  _extract_state(canonical_event) → str | None          │    │
│  │  _log_dryrun(store, ...) → None                        │    │
│  └─────────────────────────────────────────────────────┘    │
├─────────────────────────────────────────────────────────────┤
│  server.py                                                   │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  ServerConfig:                                       │    │
│  │    - factory_dryrun_enabled                          │    │
│  │    - factory_dryrun_allowed_project_ids              │    │
│  │    - factory_dryrun_ready_states                     │    │
│  │                                                       │    │
│  │  _build_ingress():                                   │    │
│  │    - Create FactoryDispatchDryRunAction               │    │
│  │    - Add to ActionRegistry actions list               │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

---

## 12. Test Strategy

### 12.1 Executor Unit Tests

```python
class TestFactoryDispatchDryRunExecutor:
    def test_allowed_project_ready_state_would_dispatch(self):
        executor = FactoryDispatchDryRunExecutor(
            allowed_project_ids={"proj-1"},
            ready_states={"ready", "in_progress"},
        )
        result = executor.evaluate(event_for_project_ready("proj-1", "Ready"))
        assert result.would_dispatch is True
        assert len(result.reasons) == 3  # project + state + type

    def test_wrong_project_would_not_dispatch(self):
        executor = FactoryDispatchDryRunExecutor(
            allowed_project_ids={"proj-1"},
            ready_states={"ready"},
        )
        result = executor.evaluate(event_for_project_ready("proj-2", "Ready"))
        assert result.would_dispatch is False
        assert any("not in allowed set" in r for r in result.reasons)

    def test_wrong_state_would_not_dispatch(self):
        executor = FactoryDispatchDryRunExecutor(
            allowed_project_ids={"proj-1"},
            ready_states={"ready"},
        )
        result = executor.evaluate(event_for_project_ready("proj-1", "Done"))
        assert result.would_dispatch is False
        assert any("not in ready states" in r for r in result.reasons)

    def test_no_filters_passes_through(self):
        executor = FactoryDispatchDryRunExecutor()
        result = executor.evaluate(event_for_project_ready("proj-1", "Done"))
        assert result.would_dispatch is True  # only type guard remains

    def test_non_issue_update_would_not_dispatch(self):
        executor = FactoryDispatchDryRunExecutor()
        result = executor.evaluate(event_for_type_action("issue", "created"))
        assert result.would_dispatch is False
        assert any("not issue.updated" in r for r in result.reasons)

    def test_never_raises_on_malformed_event(self):
        executor = FactoryDispatchDryRunExecutor(
            allowed_project_ids={"proj-1"},
            ready_states={"ready"},
        )
        result = executor.evaluate({})  # empty dict
        assert result.would_dispatch is False
```

### 12.2 Action Integration Tests

```python
class TestFactoryDispatchDryRunAction:
    def test_logs_evaluated_result(self, memory_store):
        action = FactoryDispatchDryRunAction(
            executor=FactoryDispatchDryRunExecutor(
                allowed_project_ids={"proj-1"},
                ready_states={"ready"},
            ),
            enabled=True,
        )
        action.run(
            provider="linear",
            route_mode="shadow",
            canonical_event=event_for_project_ready("proj-1", "Ready"),
            store=memory_store,
        )
        logs = memory_store.conn.execute(
            "SELECT * FROM webhook_processing_logs WHERE phase='dryrun_dispatch_eval'"
        ).fetchall()
        assert len(logs) == 1
        details = json.loads(logs[0]["details"])
        assert details["would_dispatch"] is True

    def test_disabled_skips_evaluation(self, memory_store):
        action = FactoryDispatchDryRunAction(
            executor=FactoryDispatchDryRunExecutor(),
            enabled=False,
        )
        action.run(
            provider="linear",
            route_mode="shadow",
            canonical_event=event_for_project_ready("proj-1", "Ready"),
            store=memory_store,
        )
        logs = memory_store.conn.execute(
            "SELECT * FROM webhook_processing_logs WHERE status='skipped'"
        ).fetchall()
        assert len(logs) == 1

    def test_runs_in_all_route_modes(self, memory_store):
        for mode in ("shadow", "canary_dryrun", "production_canary", "live"):
            action = FactoryDispatchDryRunAction(
                executor=FactoryDispatchDryRunExecutor(),
                enabled=True,
            )
            action.run(
                provider="linear",
                route_mode=mode,
                canonical_event=event_for_project_ready("proj-1", "Ready"),
                store=memory_store,
            )
        logs = memory_store.conn.execute(
            "SELECT count(*) FROM webhook_processing_logs WHERE phase='dryrun_dispatch_eval'"
        ).fetchone()[0]
        assert logs == 4
```

---

## 13. Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Log volume in live mode | Medium | Low | Action is lightweight; can be disabled via `FACTORY_DRYRUN_ENABLED=false` |
| Project ID extraction mismatch | Low | Medium | Three-tier extraction (source → payload.project_id → payload.team.id) |
| State name casing issues | Low | Low | Lowercase normalization in executor |
| Executor throws on malformed event | Very Low | Low | Top-level try/except in Action.run() catches and logs error |

---

## 14. Future Extension Points

| Extension | Description |
|-----------|-------------|
| **Dry-run to real dispatch** | Once dry-run validates rules, swap `would_dispatch=true` for actual n8n forward |
| **Metrics aggregation** | Query `webhook_processing_logs` WHERE `phase='dryrun_dispatch_eval'` for dashboards |
| **Per-provider executors** | Different project/state extraction for GitHub, Jira, etc. |
| **Configurable guard rules** | YAML-based guard definitions instead of hardcoded Python |
| **Rate limiting** | Skip dry-run logging for high-frequency events |

None of these are in scope for this design.

---

**Document Status**: Design Complete  
**Next Step**: Implementation task with this design as reference  
**Reviewer**: TBD
