"""TWIN state updater for processing learning events and updating student state."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Protocol

from app.models.twin_ingest_contract import TwinIngestContract, TwinIngestDecision
from app.models.twin_state import (
    AbilityState,
    BehaviorRecord,
    KnowledgeState,
    StudentTwinState,
)


class StateStore(Protocol):
    """Protocol for state persistence layer."""

    def get_state(self, student_id: str) -> StudentTwinState | None:
        """Get current state for a student."""
        ...

    def save_state(self, state: StudentTwinState) -> None:
        """Save updated state for a student."""
        ...


@dataclass(frozen=True)
class StateUpdateResult:
    """Result of a state update operation."""

    success: bool
    student_id: str
    event_id: str
    updated_at: str

    knowledge_updates: list[str] = field(default_factory=list)
    ability_updates: list[str] = field(default_factory=list)
    behavior_updates: list[str] = field(default_factory=list)

    error: str | None = None
    skipped_reason: str | None = None

    @property
    def was_skipped(self) -> bool:
        """Check if update was skipped (not an error, just no state change)."""
        return self.skipped_reason is not None


@dataclass
class AuditEntry:
    """Single audit log entry for state changes."""

    audit_id: str
    student_id: str
    event_id: str
    updated_at: str
    update_type: str  # "knowledge", "ability", "behavior", "chapter"
    before_state: dict[str, Any] | None
    after_state: dict[str, Any] | None
    change_summary: str
    trace_id: str


@dataclass
class AuditTrail:
    """Audit trail for a student's state changes."""

    student_id: str
    entries: list[AuditEntry] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def add_entry(self, entry: AuditEntry) -> None:
        """Add an audit entry."""
        self.entries.append(entry)
        self.updated_at = datetime.now().isoformat()

    def get_entries(self, limit: int = 50) -> list[AuditEntry]:
        """Get recent audit entries."""
        return self.entries[-limit:]

    def to_dict(self) -> dict[str, Any]:
        """Serialize audit trail to dictionary."""
        return {
            "student_id": self.student_id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "entries": [
                {
                    "audit_id": e.audit_id,
                    "student_id": e.student_id,
                    "event_id": e.event_id,
                    "updated_at": e.updated_at,
                    "update_type": e.update_type,
                    "change_summary": e.change_summary,
                    "trace_id": e.trace_id,
                }
                for e in self.entries
            ],
        }


@dataclass
class StateBroadcast:
    """Broadcast message for state changes."""

    broadcast_id: str
    student_id: str
    event_id: str
    broadcast_time: str
    update_summary: dict[str, Any]
    recipients: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Serialize broadcast to dictionary."""
        return {
            "broadcast_id": self.broadcast_id,
            "student_id": self.student_id,
            "event_id": self.event_id,
            "broadcast_time": self.broadcast_time,
            "update_summary": self.update_summary,
            "recipients": self.recipients,
        }


def _extract_mastery_from_event(contract: TwinIngestContract) -> float:
    """Extract inferred mastery level from event data."""
    if contract.event_status == "success":
        base_mastery = 0.8
    elif contract.event_status == "degraded":
        base_mastery = 0.5
    else:
        base_mastery = 0.3

    confidence_bonus = contract.confidence_score * 0.2
    return min(base_mastery + confidence_bonus, 1.0)


def _extract_ability_evidence(
    contract: TwinIngestContract,
    ability_refs: list[str],
) -> dict[str, float]:
    """Extract ability evidence levels from event."""
    mastery = _extract_mastery_from_event(contract)
    return {ability_id: mastery for ability_id in ability_refs}


class TWINStateUpdater:
    """
    State updater for processing learning events and updating student twin state.

    This is the core component that:
    1. Validates incoming events against TWIN contract
    2. Updates knowledge states based on event references
    3. Updates ability states based on mappings
    4. Records behavior observations
    5. Maintains audit trail
    6. Generates broadcast messages
    """

    def __init__(
        self,
        store: StateStore,
        knowledge_to_ability_map: dict[str, list[str]] | None = None,
    ):
        self.store = store
        self.knowledge_to_ability_map = knowledge_to_ability_map or {}
        self.audit_trails: dict[str, AuditTrail] = {}

    def _get_or_create_trail(self, student_id: str) -> AuditTrail:
        """Get or create audit trail for a student."""
        if student_id not in self.audit_trails:
            self.audit_trails[student_id] = AuditTrail(student_id=student_id)
        return self.audit_trails[student_id]

    def _create_audit_entry(
        self,
        student_id: str,
        event_id: str,
        update_type: str,
        before_state: dict[str, Any] | None,
        after_state: dict[str, Any] | None,
        change_summary: str,
        trace_id: str,
    ) -> AuditEntry:
        """Create an audit entry."""
        import uuid
        return AuditEntry(
            audit_id=f"AUD_{uuid.uuid4().hex[:12].upper()}",
            student_id=student_id,
            event_id=event_id,
            updated_at=datetime.now().isoformat(),
            update_type=update_type,
            before_state=before_state,
            after_state=after_state,
            change_summary=change_summary,
            trace_id=trace_id,
        )

    def process_event(
        self,
        contract: TwinIngestContract,
    ) -> StateUpdateResult:
        """
        Process a learning event and update student state.

        Args:
            contract: Validated TWIN ingest contract

        Returns:
            StateUpdateResult with update details
        """
        now = datetime.now().isoformat()
        student_id = contract.student_id
        event_id = contract.event_id

        decision = contract.validate()
        if not decision.accepted:
            # review_needed 事件是预期行为，不是错误
            if decision.review_needed:
                return StateUpdateResult(
                    success=True,
                    student_id=student_id,
                    event_id=event_id,
                    updated_at=now,
                    skipped_reason=decision.reason,
                )
            # 真正的 rejection（如范围不匹配、校验失败）
            return StateUpdateResult(
                success=False,
                student_id=student_id,
                event_id=event_id,
                updated_at=now,
                error=decision.reason,
            )

        if not decision.should_consume:
            return StateUpdateResult(
                success=True,
                student_id=student_id,
                event_id=event_id,
                updated_at=now,
                skipped_reason="event_requires_review_first",
            )

        state = self.store.get_state(student_id)
        if state is None:
            state = StudentTwinState.create_empty(student_id, now)

        before_dict = state.to_dict()

        knowledge_updates: list[str] = []
        ability_updates: list[str] = []
        behavior_updates: list[str] = []

        if decision.knowledge_state_allowed and contract.knowledge_refs:
            mastery = _extract_mastery_from_event(contract)
            for knowledge_id in contract.knowledge_refs:
                old_state = state.knowledge_states.get(knowledge_id)
                if old_state is None:
                    state.knowledge_states[knowledge_id] = KnowledgeState(
                        knowledge_id=knowledge_id,
                        mastery_level=mastery,
                        last_updated=now,
                        evidence_count=1,
                    )
                else:
                    state.knowledge_states[knowledge_id] = old_state.with_update(
                        mastery, now
                    )
                knowledge_updates.append(knowledge_id)

            for ability_id in contract.ability_refs:
                old_ability = state.ability_states.get(ability_id)
                if old_ability is None:
                    state.ability_states[ability_id] = AbilityState(
                        ability_id=ability_id,
                        ability_level=mastery,
                        last_updated=now,
                        evidence_count=1,
                    )
                else:
                    state.ability_states[ability_id] = old_ability.with_update(
                        mastery, now
                    )
                ability_updates.append(ability_id)

        if contract.behavior_tags:
            for behavior_tag in contract.behavior_tags:
                record = BehaviorRecord(
                    behavior_tag=behavior_tag,
                    observed_at=contract.event_time,
                    intensity=0.5,
                    context=contract.event_summary,
                    observer="teacher" if contract.source_type == "teacher_feedback_text" else "parent",
                )
                state.behavior_records.append(record)
                behavior_updates.append(behavior_tag)

        state.updated_at = now
        self.store.save_state(state)

        after_dict = state.to_dict()

        if knowledge_updates or ability_updates or behavior_updates:
            trail = self._get_or_create_trail(student_id)
            trail.add_entry(
                self._create_audit_entry(
                    student_id=student_id,
                    event_id=event_id,
                    update_type="combined",
                    before_state=before_dict,
                    after_state=after_dict,
                    change_summary=f"knowledge:{len(knowledge_updates)}, ability:{len(ability_updates)}, behavior:{len(behavior_updates)}",
                    trace_id=contract.trace_id,
                )
            )

        return StateUpdateResult(
            success=True,
            student_id=student_id,
            event_id=event_id,
            updated_at=now,
            knowledge_updates=knowledge_updates,
            ability_updates=ability_updates,
            behavior_updates=behavior_updates,
        )

    def create_broadcast(
        self,
        result: StateUpdateResult,
        recipients: list[str] | None = None,
    ) -> StateBroadcast | None:
        """Create a broadcast message for state updates."""
        if result.was_skipped or not result.success:
            return None

        import uuid
        update_summary = {
            "knowledge_updated": result.knowledge_updates,
            "ability_updated": result.ability_updates,
            "behavior_updated": result.behavior_updates,
        }

        return StateBroadcast(
            broadcast_id=f"BRC_{uuid.uuid4().hex[:12].upper()}",
            student_id=result.student_id,
            event_id=result.event_id,
            broadcast_time=datetime.now().isoformat(),
            update_summary=update_summary,
            recipients=recipients or ["parent", "teacher"],
        )
