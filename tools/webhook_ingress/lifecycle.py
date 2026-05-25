from __future__ import annotations

from enum import Enum


class RunState(str, Enum):
    STARTED = "started"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    BLOCKED = "blocked"
    FAILED = "failed"


class LifecycleTransitionError(Exception):
    pass


class FactoryLifecycleStateMachine:
    def __init__(self) -> None:
        self._runs: dict[str, RunState] = {}

    def start(self, run_id: str) -> RunState:
        """Start a new run. Raises if already exists."""
        if run_id in self._runs:
            raise LifecycleTransitionError(f"run {run_id} already exists")
        self._runs[run_id] = RunState.STARTED
        return RunState.STARTED

    def transition(self, run_id: str, target: RunState) -> RunState:
        """Transition to a new state. Validates the transition is legal."""
        if run_id not in self._runs:
            raise LifecycleTransitionError(f"run {run_id} not found")
        current = self._runs[run_id]
        if not self._is_valid_transition(current, target):
            raise LifecycleTransitionError(
                f"invalid transition: {current.value} → {target.value} for run {run_id}"
            )
        self._runs[run_id] = target
        return target

    def get_state(self, run_id: str) -> RunState | None:
        return self._runs.get(run_id)

    @staticmethod
    def _is_valid_transition(current: RunState, target: RunState) -> bool:
        valid = {
            RunState.STARTED: {RunState.IN_PROGRESS, RunState.FAILED},
            RunState.IN_PROGRESS: {RunState.IN_PROGRESS, RunState.DONE, RunState.BLOCKED, RunState.FAILED},
            RunState.BLOCKED: {RunState.IN_PROGRESS, RunState.FAILED},
            RunState.DONE: set(),
            RunState.FAILED: set(),
        }
        return target in valid.get(current, set())

    def is_terminal(self, run_id: str) -> bool:
        state = self._runs.get(run_id)
        return state in (RunState.DONE, RunState.FAILED)

    def event_type_to_state(self, event_type: str) -> RunState:
        """Map factory event_type string to RunState."""
        mapping = {
            "factory_run_started": RunState.STARTED,
            "factory_run_progress": RunState.IN_PROGRESS,
            "factory_run_done": RunState.DONE,
            "factory_run_blocked": RunState.BLOCKED,
            "factory_run_failed": RunState.FAILED,
        }
        if event_type not in mapping:
            raise LifecycleTransitionError(f"unknown event_type: {event_type}")
        return mapping[event_type]

    def process_event(self, run_id: str, event_type: str) -> RunState:
        """Process a factory lifecycle event: start or transition."""
        target = self.event_type_to_state(event_type)
        if run_id not in self._runs:
            if target != RunState.STARTED:
                raise LifecycleTransitionError(
                    f"first event for run {run_id} must be STARTED, got {target.value}"
                )
            return self.start(run_id)
        return self.transition(run_id, target)


def event_type_to_canonical_action(event_type: str) -> str:
    mapping = {
        "factory_run_started": "created",
        "factory_run_progress": "updated",
        "factory_run_done": "updated",
        "factory_run_blocked": "updated",
        "factory_run_failed": "updated",
    }
    return mapping.get(event_type, "unknown")
