"""Retrieval Unit for assembling TWIN/GRAPH output into searchable context."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Protocol

from app.models.graph_models import GraphEdge, GraphNode, GraphSnapshot
from app.models.graph_writer import GraphWriter
from app.models.twin_state import StudentTwinState


class TwinStore(Protocol):
    """Protocol for accessing TWIN state."""

    def get_state(self, student_id: str) -> StudentTwinState | None:
        """Get current twin state for a student."""
        ...


class GraphStore(Protocol):
    """Protocol for accessing GRAPH data."""

    def get_latest_snapshot(self) -> GraphSnapshot | None:
        """Get the most recent graph snapshot."""
        ...

    def load_snapshot(self, snapshot_id: str) -> GraphSnapshot | None:
        """Load a specific graph snapshot."""
        ...


@dataclass(frozen=True)
class CurrentStateView:
    """View of student's current state for retrieval."""

    student_id: str
    knowledge_mastery_avg: float
    ability_level_avg: float
    chapter_coverage_avg: float
    last_updated: str
    status_flags: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "student_id": self.student_id,
            "knowledge_mastery_avg": self.knowledge_mastery_avg,
            "ability_level_avg": self.ability_level_avg,
            "chapter_coverage_avg": self.chapter_coverage_avg,
            "last_updated": self.last_updated,
            "status_flags": list(self.status_flags),
        }


@dataclass(frozen=True)
class KeyEventRecord:
    """Key event record for retrieval."""

    event_id: str
    event_type: str
    event_time: str
    event_summary: str
    knowledge_refs: list[str]
    ability_refs: list[str]
    event_status: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "event_time": self.event_time,
            "event_summary": self.event_summary,
            "knowledge_refs": self.knowledge_refs,
            "ability_refs": self.ability_refs,
            "event_status": self.event_status,
        }


@dataclass(frozen=True)
class StructuralReference:
    """Structural reference to curriculum knowledge."""

    chapter_node_id: str
    chapter_name: str
    knowledge_ids: list[str]
    ability_ids: list[str]
    anchor_ids: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "chapter_node_id": self.chapter_node_id,
            "chapter_name": self.chapter_name,
            "knowledge_ids": self.knowledge_ids,
            "ability_ids": self.ability_ids,
            "anchor_ids": self.anchor_ids,
        }


@dataclass
class RetrievalUnit:
    """
    Minimal retrieval unit combining current state, key events, and structural references.

    This is the main output of the Retrieval Unit assembly.
    """

    retrieval_id: str
    student_id: str
    assembled_at: str

    current_state: CurrentStateView | None = None
    key_events: list[KeyEventRecord] = field(default_factory=list)
    structural_refs: list[StructuralReference] = field(default_factory=list)

    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize retrieval unit to dictionary."""
        return {
            "retrieval_id": self.retrieval_id,
            "student_id": self.student_id,
            "assembled_at": self.assembled_at,
            "current_state": self.current_state.to_dict() if self.current_state else None,
            "key_events": [e.to_dict() for e in self.key_events],
            "structural_refs": [s.to_dict() for s in self.structural_refs],
            "metadata": self.metadata,
        }

    @classmethod
    def create_empty(cls, student_id: str) -> "RetrievalUnit":
        """Create an empty retrieval unit skeleton."""
        now = datetime.now().isoformat()
        return RetrievalUnit(
            retrieval_id=f"RET_{student_id}_{now.replace(':', '').replace('-', '')[:15]}",
            student_id=student_id,
            assembled_at=now,
        )


@dataclass
class RetrievalContext:
    """
    Assembled retrieval context for downstream consumption.

    This is the final output that can be used by OBS layer or external APIs.
    """

    retrieval_unit: RetrievalUnit
    graph_snapshot_id: str | None = None
    twin_state_snapshot_id: str | None = None
    is_complete: bool = False
    missing_components: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "retrieval_unit": self.retrieval_unit.to_dict(),
            "graph_snapshot_id": self.graph_snapshot_id,
            "twin_state_snapshot_id": self.twin_state_snapshot_id,
            "is_complete": self.is_complete,
            "missing_components": self.missing_components,
        }


class RetrievalUnitAssembler:
    """
    Assembles RetrievalUnit from TWIN and GRAPH data sources.

    This is the core component for F9-T1.
    """

    def __init__(
        self,
        twin_store: TwinStore,
        graph_store: GraphStore,
        chapter_names: dict[str, str] | None = None,
        knowledge_names: dict[str, str] | None = None,
        ability_names: dict[str, str] | None = None,
        chapter_knowledge_map: dict[str, list[str]] | None = None,
        knowledge_to_ability_map: dict[str, list[str]] | None = None,
    ):
        self.twin_store = twin_store
        self.graph_store = graph_store
        self.chapter_names = chapter_names or {}
        self.knowledge_names = knowledge_names or {}
        self.ability_names = ability_names or {}
        self.chapter_knowledge_map = chapter_knowledge_map or {}
        self.knowledge_to_ability_map = knowledge_to_ability_map or {}

    def assemble_current_state(self, twin_state: StudentTwinState) -> CurrentStateView:
        """Assemble current state view from twin state."""
        knowledge_mastery_avg = 0.0
        ability_level_avg = 0.0
        chapter_coverage_avg = 0.0

        status_flags: list[str] = []

        if twin_state.knowledge_states:
            mastery_values = [ks.mastery_level for ks in twin_state.knowledge_states.values()]
            knowledge_mastery_avg = sum(mastery_values) / len(mastery_values)

            low_mastery_count = sum(1 for m in mastery_values if m < 0.3)
            if low_mastery_count > 0:
                status_flags.append(f"low_mastery_count:{low_mastery_count}")

        if twin_state.ability_states:
            level_values = [abs.ability_level for abs in twin_state.ability_states.values()]
            ability_level_avg = sum(level_values) / len(level_values)

        if twin_state.chapter_progress:
            coverage_values = [cp.coverage for cp in twin_state.chapter_progress.values()]
            chapter_coverage_avg = sum(coverage_values) / len(coverage_values)

        declining_count = sum(
            1 for ks in twin_state.knowledge_states.values()
            if ks.trend == "declining"
        )
        if declining_count > 0:
            status_flags.append(f"declining_count:{declining_count}")

        return CurrentStateView(
            student_id=twin_state.student_id,
            knowledge_mastery_avg=round(knowledge_mastery_avg, 4),
            ability_level_avg=round(ability_level_avg, 4),
            chapter_coverage_avg=round(chapter_coverage_avg, 4),
            last_updated=twin_state.updated_at,
            status_flags=tuple(status_flags),
        )

    def assemble_key_events(
        self,
        twin_state: StudentTwinState,
        limit: int = 10,
    ) -> list[KeyEventRecord]:
        """Assemble key events from twin state behavior records."""
        events: list[KeyEventRecord] = []

        for behavior in twin_state.behavior_records[-limit:]:
            events.append(
                KeyEventRecord(
                    event_id=f"BEH_{behavior.behavior_tag}_{behavior.observed_at}",
                    event_type="behavior_observation",
                    event_time=behavior.observed_at,
                    event_summary=behavior.context or f"Behavior: {behavior.behavior_tag}",
                    knowledge_refs=[],
                    ability_refs=[],
                    event_status="success",
                )
            )

        return events

    def assemble_structural_refs(
        self,
        twin_state: StudentTwinState,
        graph_snapshot: GraphSnapshot | None = None,
    ) -> list[StructuralReference]:
        """Assemble structural references from twin state and graph.

        Args:
            twin_state: Current student twin state.
            graph_snapshot: Legacy parameter kept for backward compatibility; ignored.
        """
        refs: list[StructuralReference] = []

        chapter_node_ids = set(twin_state.chapter_progress.keys())

        for chapter_id in chapter_node_ids:
            knowledge_ids = list(self.chapter_knowledge_map.get(chapter_id, [])) if self.chapter_knowledge_map else []

            ability_ids: list[str] = []
            if self.knowledge_to_ability_map:
                ability_set: set[str] = set()
                for kid in knowledge_ids:
                    ability_set.update(self.knowledge_to_ability_map.get(kid, []))
                ability_ids = sorted(ability_set)

            refs.append(
                StructuralReference(
                    chapter_node_id=chapter_id,
                    chapter_name=self.chapter_names.get(chapter_id, chapter_id),
                    knowledge_ids=knowledge_ids,
                    ability_ids=ability_ids,
                    anchor_ids=[],
                )
            )

        return refs

    def assemble(
        self,
        student_id: str,
        include_events: bool = True,
        include_structural: bool = True,
    ) -> RetrievalContext:
        """
        Assemble a complete RetrievalContext for a student.

        Args:
            student_id: Student ID to assemble retrieval for
            include_events: Whether to include key events
            include_structural: Whether to include structural references

        Returns:
            RetrievalContext with assembled data
        """
        retrieval_unit = RetrievalUnit.create_empty(student_id)
        missing_components: list[str] = []

        twin_state = self.twin_store.get_state(student_id)
        twin_snapshot_id = None
        graph_snapshot_id = None

        if twin_state is None:
            missing_components.append("twin_state_missing")
        else:
            retrieval_unit.current_state = self.assemble_current_state(twin_state)
            twin_snapshot_id = twin_state.updated_at

            if include_events:
                retrieval_unit.key_events = self.assemble_key_events(twin_state)

            graph_snapshot = self.graph_store.get_latest_snapshot()
            graph_snapshot_id = graph_snapshot.snapshot_id if graph_snapshot else None

            if include_structural:
                retrieval_unit.structural_refs = self.assemble_structural_refs(
                    twin_state
                )

        is_complete = len(missing_components) == 0 and retrieval_unit.current_state is not None

        return RetrievalContext(
            retrieval_unit=retrieval_unit,
            graph_snapshot_id=graph_snapshot_id,
            twin_state_snapshot_id=twin_snapshot_id,
            is_complete=is_complete,
            missing_components=missing_components,
        )
