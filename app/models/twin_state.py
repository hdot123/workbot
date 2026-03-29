"""TWIN state entity models for student digital twin."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class KnowledgeState:
    """State of a single knowledge point for a student."""

    knowledge_id: str
    mastery_level: float  # 0.0 to 1.0
    last_updated: str
    last_assessed: str | None = None
    evidence_count: int = 0
    trend: str = "stable"  # "improving", "declining", "stable"
    flags: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not 0.0 <= self.mastery_level <= 1.0:
            raise ValueError("mastery_level must be between 0 and 1")
        if self.trend not in {"improving", "declining", "stable"}:
            raise ValueError(f"invalid trend: {self.trend}")

    def with_update(
        self,
        new_evidence_mastery: float,
        new_evidence_time: str,
        weight: float = 0.3,
    ) -> "KnowledgeState":
        """Update mastery with new evidence using exponential moving average."""
        old_mastery = self.mastery_level
        new_mastery = (1 - weight) * old_mastery + weight * new_evidence_mastery

        if new_mastery > old_mastery + 0.05:
            trend = "improving"
        elif new_mastery < old_mastery - 0.05:
            trend = "declining"
        else:
            trend = "stable"

        flags = list(self.flags)
        if new_mastery < 0.3:
            if "low_mastery" not in flags:
                flags.append("low_mastery")
        else:
            if "low_mastery" in flags:
                flags.remove("low_mastery")

        return KnowledgeState(
            knowledge_id=self.knowledge_id,
            mastery_level=round(new_mastery, 4),
            last_updated=new_evidence_time,
            last_assessed=new_evidence_time,
            evidence_count=self.evidence_count + 1,
            trend=trend,
            flags=tuple(flags),
        )


@dataclass(frozen=True)
class AbilityState:
    """State of a single ability for a student."""

    ability_id: str
    ability_level: float  # 0.0 to 1.0
    last_updated: str
    evidence_count: int = 0
    recent_performance: tuple[float, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not 0.0 <= self.ability_level <= 1.0:
            raise ValueError("ability_level must be between 0 and 1")

    def with_update(
        self,
        new_evidence_level: float,
        new_evidence_time: str,
        window_size: int = 5,
    ) -> "AbilityState":
        """Update ability with new evidence."""
        recent = list(self.recent_performance)[-window_size + 1 :] + [new_evidence_level]
        avg_level = sum(recent) / len(recent)

        return AbilityState(
            ability_id=self.ability_id,
            ability_level=round(avg_level, 4),
            last_updated=new_evidence_time,
            evidence_count=self.evidence_count + 1,
            recent_performance=tuple(recent),
        )


@dataclass(frozen=True)
class ChapterProgress:
    """Progress state for a chapter."""

    chapter_node_id: str
    coverage: float  # 0.0 to 1.0
    knowledge_mastery_avg: float
    last_studied: str
    time_spent_minutes: int = 0
    exercise_count: int = 0

    def __post_init__(self) -> None:
        if not 0.0 <= self.coverage <= 1.0:
            raise ValueError("coverage must be between 0 and 1")
        if not 0.0 <= self.knowledge_mastery_avg <= 1.0:
            raise ValueError("knowledge_mastery_avg must be between 0 and 1")


@dataclass(frozen=True)
class BehaviorRecord:
    """Single behavior observation record."""

    behavior_tag: str
    observed_at: str
    intensity: float  # 0.0 to 1.0
    context: str | None = None
    observer: str | None = None  # "teacher" or "parent"


@dataclass
class StudentTwinState:
    """
    Complete state container for a student's digital twin.

    This is the main state object that gets updated when learning events
    are consumed by the TWIN system.
    """

    student_id: str
    created_at: str
    updated_at: str

    knowledge_states: dict[str, KnowledgeState] = field(default_factory=dict)
    ability_states: dict[str, AbilityState] = field(default_factory=dict)
    chapter_progress: dict[str, ChapterProgress] = field(default_factory=dict)
    behavior_records: list[BehaviorRecord] = field(default_factory=list)

    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create_empty(cls, student_id: str, now: str | None = None) -> "StudentTwinState":
        """Create an empty twin state for a new student."""
        timestamp = now or datetime.now().isoformat()
        return StudentTwinState(
            student_id=student_id,
            created_at=timestamp,
            updated_at=timestamp,
        )

    def get_knowledge_state(self, knowledge_id: str) -> KnowledgeState | None:
        """Get current state for a knowledge point."""
        return self.knowledge_states.get(knowledge_id)

    def get_ability_state(self, ability_id: str) -> AbilityState | None:
        """Get current state for an ability."""
        return self.ability_states.get(ability_id)

    def get_chapter_progress(self, chapter_node_id: str) -> ChapterProgress | None:
        """Get progress for a chapter."""
        return self.chapter_progress.get(chapter_node_id)

    def get_behavior_history(self, behavior_tag: str | None = None) -> list[BehaviorRecord]:
        """Get behavior records, optionally filtered by tag."""
        if behavior_tag is None:
            return list(self.behavior_records)
        return [r for r in self.behavior_records if r.behavior_tag == behavior_tag]

    def compute_overall_metrics(self) -> dict[str, float]:
        """Compute aggregate metrics across all state dimensions."""
        metrics: dict[str, float] = {}

        if self.knowledge_states:
            mastery_values = [ks.mastery_level for ks in self.knowledge_states.values()]
            metrics["knowledge_avg_mastery"] = sum(mastery_values) / len(mastery_values)
            metrics["knowledge_count"] = float(len(self.knowledge_states))

            improving = sum(1 for ks in self.knowledge_states.values() if ks.trend == "improving")
            metrics["knowledge_improving_ratio"] = improving / len(self.knowledge_states)

        if self.ability_states:
            level_values = [abs.ability_level for abs in self.ability_states.values()]
            metrics["ability_avg_level"] = sum(level_values) / len(level_values)
            metrics["ability_count"] = float(len(self.ability_states))

        if self.chapter_progress:
            coverage_values = [cp.coverage for cp in self.chapter_progress.values()]
            metrics["chapter_avg_coverage"] = sum(coverage_values) / len(self.chapter_progress)

        metrics["behavior_record_count"] = float(len(self.behavior_records))

        return metrics

    def to_dict(self) -> dict[str, Any]:
        """Serialize twin state to dictionary."""
        return {
            "student_id": self.student_id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "knowledge_states": {
                kid: {
                    "knowledge_id": ks.knowledge_id,
                    "mastery_level": ks.mastery_level,
                    "last_updated": ks.last_updated,
                    "last_assessed": ks.last_assessed,
                    "evidence_count": ks.evidence_count,
                    "trend": ks.trend,
                    "flags": list(ks.flags),
                }
                for kid, ks in self.knowledge_states.items()
            },
            "ability_states": {
                aid: {
                    "ability_id": abs.ability_id,
                    "ability_level": abs.ability_level,
                    "last_updated": abs.last_updated,
                    "evidence_count": abs.evidence_count,
                    "recent_performance": list(abs.recent_performance),
                }
                for aid, abs in self.ability_states.items()
            },
            "chapter_progress": {
                cid: {
                    "chapter_node_id": cp.chapter_node_id,
                    "coverage": cp.coverage,
                    "knowledge_mastery_avg": cp.knowledge_mastery_avg,
                    "last_studied": cp.last_studied,
                    "time_spent_minutes": cp.time_spent_minutes,
                    "exercise_count": cp.exercise_count,
                }
                for cid, cp in self.chapter_progress.items()
            },
            "behavior_records": [
                {
                    "behavior_tag": br.behavior_tag,
                    "observed_at": br.observed_at,
                    "intensity": br.intensity,
                    "context": br.context,
                    "observer": br.observer,
                }
                for br in self.behavior_records
            ],
            "metadata": self.metadata,
        }
