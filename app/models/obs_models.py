"""OBS minimal output models for parent weekly report and teacher/student details."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class KnowledgeSummary:
    """Summary of knowledge state for display."""

    knowledge_id: str
    knowledge_name: str
    mastery_level: float
    trend: str  # "improving", "declining", "stable"
    last_updated: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "knowledge_id": self.knowledge_id,
            "knowledge_name": self.knowledge_name,
            "mastery_level": self.mastery_level,
            "trend": self.trend,
            "last_updated": self.last_updated,
        }


@dataclass(frozen=True)
class AbilitySummary:
    """Summary of ability state for display."""

    ability_id: str
    ability_name: str
    ability_level: float
    evidence_count: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "ability_id": self.ability_id,
            "ability_name": self.ability_name,
            "ability_level": self.ability_level,
            "evidence_count": self.evidence_count,
        }


@dataclass(frozen=True)
class ChapterSummary:
    """Summary of chapter progress for display."""

    chapter_node_id: str
    chapter_name: str
    coverage: float
    knowledge_mastery_avg: float
    last_studied: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "chapter_node_id": self.chapter_node_id,
            "chapter_name": self.chapter_name,
            "coverage": self.coverage,
            "knowledge_mastery_avg": self.knowledge_mastery_avg,
            "last_studied": self.last_studied,
        }


@dataclass(frozen=True)
class BehaviorSummary:
    """Summary of behavior observations for display."""

    behavior_tag: str
    behavior_name: str
    observation_count: int
    recent_intensity_avg: float
    last_observed: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "behavior_tag": self.behavior_tag,
            "behavior_name": self.behavior_name,
            "observation_count": self.observation_count,
            "recent_intensity_avg": self.recent_intensity_avg,
            "last_observed": self.last_observed,
        }


@dataclass
class ParentWeeklyReport:
    """
    Weekly report for parents showing student's learning progress.

    This is the main output object for the parent view in OBS layer.
    """

    report_id: str
    student_id: str
    student_name: str
    week_start: str
    week_end: str
    generated_at: str

    knowledge_summary: list[KnowledgeSummary] = field(default_factory=list)
    ability_summary: list[AbilitySummary] = field(default_factory=list)
    chapter_progress: list[ChapterSummary] = field(default_factory=list)
    behavior_summary: list[BehaviorSummary] = field(default_factory=list)

    weekly_highlights: list[str] = field(default_factory=list)
    weekly_concerns: list[str] = field(default_factory=list)
    suggested_actions: list[str] = field(default_factory=list)

    overall_status: str = "normal"  # "normal", "attention", "concern"

    def to_dict(self) -> dict[str, Any]:
        """Serialize report to dictionary."""
        return {
            "report_id": self.report_id,
            "student_id": self.student_id,
            "student_name": self.student_name,
            "week_start": self.week_start,
            "week_end": self.week_end,
            "generated_at": self.generated_at,
            "knowledge_summary": [ks.to_dict() for ks in self.knowledge_summary],
            "ability_summary": [abs.to_dict() for abs in self.ability_summary],
            "chapter_progress": [cs.to_dict() for cs in self.chapter_progress],
            "behavior_summary": [bs.to_dict() for bs in self.behavior_summary],
            "weekly_highlights": self.weekly_highlights,
            "weekly_concerns": self.weekly_concerns,
            "suggested_actions": self.suggested_actions,
            "overall_status": self.overall_status,
        }

    @classmethod
    def create_empty(
        cls,
        student_id: str,
        student_name: str,
        week_start: str,
        week_end: str,
    ) -> "ParentWeeklyReport":
        """Create an empty weekly report skeleton."""
        now = datetime.now().isoformat()
        return ParentWeeklyReport(
            report_id=f"WKR_{week_start}_{student_id}",
            student_id=student_id,
            student_name=student_name,
            week_start=week_start,
            week_end=week_end,
            generated_at=now,
        )

    def compute_overall_status(self) -> str:
        """Compute overall status based on summary data."""
        if self.weekly_concerns:
            self.overall_status = "concern"
        elif self.weekly_highlights:
            self.overall_status = "attention"
        else:
            self.overall_status = "normal"
        return self.overall_status


@dataclass
class TeacherStudentDetail:
    """
    Detailed view for teachers showing individual student status.

    Provides more granular data than parent view for teacher decision-making.
    """

    detail_id: str
    student_id: str
    student_name: str
    class_name: str
    generated_at: str

    knowledge_states: list[KnowledgeSummary] = field(default_factory=list)
    ability_states: list[AbilitySummary] = field(default_factory=list)
    chapter_progress: list[ChapterSummary] = field(default_factory=list)
    behavior_records: list[BehaviorSummary] = field(default_factory=list)

    recent_events: list[dict[str, Any]] = field(default_factory=list)
    alert_flags: list[str] = field(default_factory=list)

    teacher_notes: str | None = None
    last_contact_date: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize detail to dictionary."""
        return {
            "detail_id": self.detail_id,
            "student_id": self.student_id,
            "student_name": self.student_name,
            "class_name": self.class_name,
            "generated_at": self.generated_at,
            "knowledge_states": [ks.to_dict() for ks in self.knowledge_states],
            "ability_states": [abs.to_dict() for abs in self.ability_states],
            "chapter_progress": [cs.to_dict() for cs in self.chapter_progress],
            "behavior_records": [bs.to_dict() for bs in self.behavior_records],
            "recent_events": self.recent_events,
            "alert_flags": self.alert_flags,
            "teacher_notes": self.teacher_notes,
            "last_contact_date": self.last_contact_date,
        }

    @classmethod
    def create_empty(
        cls,
        student_id: str,
        student_name: str,
        class_name: str,
    ) -> "TeacherStudentDetail":
        """Create an empty student detail skeleton."""
        now = datetime.now().isoformat()
        return TeacherStudentDetail(
            detail_id=f"TSD_{student_id}_{datetime.now().strftime('%Y%m%d')}",
            student_id=student_id,
            student_name=student_name,
            class_name=class_name,
            generated_at=now,
        )


@dataclass
class StudentSelfView:
    """
    Simplified view for students showing their own progress.

    Age-appropriate presentation focusing on encouragement and growth.
    """

    view_id: str
    student_id: str
    student_name: str
    generated_at: str

    mastered_knowledge: list[KnowledgeSummary] = field(default_factory=list)
    learning_knowledge: list[KnowledgeSummary] = field(default_factory=list)
    ability_growth: list[AbilitySummary] = field(default_factory=list)

    encouragement_messages: list[str] = field(default_factory=list)
    next_goals: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Serialize self view to dictionary."""
        return {
            "view_id": self.view_id,
            "student_id": self.student_id,
            "student_name": self.student_name,
            "generated_at": self.generated_at,
            "mastered_knowledge": [ks.to_dict() for ks in self.mastered_knowledge],
            "learning_knowledge": [ks.to_dict() for ks in self.learning_knowledge],
            "ability_growth": [abs.to_dict() for abs in self.ability_growth],
            "encouragement_messages": self.encouragement_messages,
            "next_goals": self.next_goals,
        }


@dataclass
class DegradedDisplayRule:
    """
    Rule for degrading display when data is incomplete.

    Used when twin state has insufficient data for full display.
    """

    rule_id: str
    condition: str  # "no_knowledge_data", "no_ability_data", "low_confidence"
    display_mode: str  # "hide", "show_partial", "show_placeholder"
    message: str
    fallback_content: dict[str, Any] = field(default_factory=dict)

    def should_apply(self, data_available: dict[str, bool]) -> bool:
        """Check if this rule should apply given available data."""
        if self.condition == "no_knowledge_data":
            return not data_available.get("knowledge", False)
        elif self.condition == "no_ability_data":
            return not data_available.get("ability", False)
        elif self.condition == "low_confidence":
            return not data_available.get("confidence", False)
        return False

    def get_display_content(self) -> dict[str, Any]:
        """Get fallback display content."""
        return {
            "display_mode": self.display_mode,
            "message": self.message,
            "fallback": self.fallback_content,
        }


class OBSDisplayBuilder:
    """
    Builder for OBS display objects with degraded display support.

    Handles:
    1. Building parent weekly reports
    2. Building teacher student details
    3. Applying degraded display rules when data is incomplete
    """

    def __init__(self):
        self.degraded_rules: list[DegradedDisplayRule] = []
        self._setup_default_rules()

    def _setup_default_rules(self) -> None:
        """Setup default degraded display rules."""
        self.degraded_rules = [
            DegradedDisplayRule(
                rule_id="DDR_001",
                condition="no_knowledge_data",
                display_mode="show_partial",
                message="知识掌握数据不足，请继续使用系统积累数据",
                fallback_content={"knowledge_summary": []},
            ),
            DegradedDisplayRule(
                rule_id="DDR_002",
                condition="no_ability_data",
                display_mode="show_partial",
                message="能力发展数据不足，请继续关注学生学习",
                fallback_content={"ability_summary": []},
            ),
            DegradedDisplayRule(
                rule_id="DDR_003",
                condition="low_confidence",
                display_mode="show_placeholder",
                message="数据可信度较低，仅供参考",
                fallback_content={"confidence_warning": True},
            ),
        ]

    def build_parent_weekly_report(
        self,
        student_id: str,
        student_name: str,
        week_start: str,
        week_end: str,
        twin_state: dict[str, Any],
        knowledge_names: dict[str, str] | None = None,
        ability_names: dict[str, str] | None = None,
        chapter_names: dict[str, str] | None = None,
    ) -> ParentWeeklyReport:
        """Build a parent weekly report from twin state."""
        report = ParentWeeklyReport.create_empty(
            student_id=student_id,
            student_name=student_name,
            week_start=week_start,
            week_end=week_end,
        )

        knowledge_names = knowledge_names or {}
        ability_names = ability_names or {}
        chapter_names = chapter_names or {}

        knowledge_states = twin_state.get("knowledge_states", {})
        for kid, kstate in knowledge_states.items():
            report.knowledge_summary.append(
                KnowledgeSummary(
                    knowledge_id=kid,
                    knowledge_name=knowledge_names.get(kid, kid),
                    mastery_level=kstate.get("mastery_level", 0),
                    trend=kstate.get("trend", "stable"),
                    last_updated=kstate.get("last_updated", ""),
                )
            )

        ability_states = twin_state.get("ability_states", {})
        for aid, astate in ability_states.items():
            report.ability_summary.append(
                AbilitySummary(
                    ability_id=aid,
                    ability_name=ability_names.get(aid, aid),
                    ability_level=astate.get("ability_level", 0),
                    evidence_count=astate.get("evidence_count", 0),
                )
            )

        chapter_progress = twin_state.get("chapter_progress", {})
        for cid, cstate in chapter_progress.items():
            report.chapter_progress.append(
                ChapterSummary(
                    chapter_node_id=cid,
                    chapter_name=chapter_names.get(cid, cid),
                    coverage=cstate.get("coverage", 0),
                    knowledge_mastery_avg=cstate.get("knowledge_mastery_avg", 0),
                    last_studied=cstate.get("last_studied", ""),
                )
            )

        behavior_records = twin_state.get("behavior_records", [])
        for behavior in behavior_records:
            tag = behavior.get("behavior_tag", "")
            report.behavior_summary.append(
                BehaviorSummary(
                    behavior_tag=tag,
                    behavior_name=tag,
                    observation_count=1,
                    recent_intensity_avg=behavior.get("intensity", 0),
                    last_observed=behavior.get("observed_at", ""),
                )
            )

        report.compute_overall_status()
        return report

    def apply_degraded_rules(
        self,
        report: ParentWeeklyReport,
        data_available: dict[str, bool],
    ) -> tuple[ParentWeeklyReport, list[str]]:
        """Apply degraded display rules to a report."""
        applied_messages: list[str] = []

        for rule in self.degraded_rules:
            if rule.should_apply(data_available):
                applied_messages.append(rule.message)

        if applied_messages:
            report.weekly_concerns.extend(applied_messages)

        return report, applied_messages

    def build_teacher_student_detail(
        self,
        student_id: str,
        student_name: str,
        class_name: str,
        twin_state: dict[str, Any],
        knowledge_names: dict[str, str] | None = None,
        ability_names: dict[str, str] | None = None,
        chapter_names: dict[str, str] | None = None,
    ) -> TeacherStudentDetail:
        """Build a teacher student detail from twin state."""
        detail = TeacherStudentDetail.create_empty(
            student_id=student_id,
            student_name=student_name,
            class_name=class_name,
        )

        knowledge_names = knowledge_names or {}
        ability_names = ability_names or {}
        chapter_names = chapter_names or {}

        knowledge_states = twin_state.get("knowledge_states", {})
        for kid, kstate in knowledge_states.items():
            detail.knowledge_states.append(
                KnowledgeSummary(
                    knowledge_id=kid,
                    knowledge_name=knowledge_names.get(kid, kid),
                    mastery_level=kstate.get("mastery_level", 0),
                    trend=kstate.get("trend", "stable"),
                    last_updated=kstate.get("last_updated", ""),
                )
            )

        ability_states = twin_state.get("ability_states", {})
        for aid, astate in ability_states.items():
            detail.ability_states.append(
                AbilitySummary(
                    ability_id=aid,
                    ability_name=ability_names.get(aid, aid),
                    ability_level=astate.get("ability_level", 0),
                    evidence_count=astate.get("evidence_count", 0),
                )
            )

        alert_flags: list[str] = []
        for ks in detail.knowledge_states:
            if ks.mastery_level < 0.3:
                alert_flags.append(f"low_mastery:{ks.knowledge_name}")
            if ks.trend == "declining":
                alert_flags.append(f"declining:{ks.knowledge_name}")

        detail.alert_flags = alert_flags

        return detail
