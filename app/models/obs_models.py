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


@dataclass(frozen=True)
class ExplanationBlock:
    """
    Explanation block with observation-evidence-impact structure.

    Core explanation unit for parent reports following OBS-008 design.
    """

    block_id: str
    title: str
    observation: str  # 观察到的现象
    evidence: list[str]  # 主要依据列表
    impact: str | None = None  # 可能影响
    confidence_note: str | None = None  # 置信说明

    def to_dict(self) -> dict[str, Any]:
        return {
            "block_id": self.block_id,
            "title": self.title,
            "observation": self.observation,
            "evidence": self.evidence,
            "impact": self.impact,
            "confidence_note": self.confidence_note,
        }


@dataclass(frozen=True)
class ActionSuggestion:
    """
    Actionable suggestion for parents with effort level and role.

    Follows OBS-002 principle: 可行动 (actionable).
    """

    suggestion_id: str
    title: str
    action_text: str
    effort_level: str = "low"  # "low", "medium", "high"
    role: str = "parent"  # "parent", "student", "teacher"

    def to_dict(self) -> dict[str, Any]:
        return {
            "suggestion_id": self.suggestion_id,
            "title": self.title,
            "action_text": self.action_text,
            "effort_level": self.effort_level,
            "role": self.role,
        }


@dataclass(frozen=True)
class FeedbackEntry:
    """
    Feedback entry for parent report correction/supplement.

    Provides feedback mechanism as required by OBS-008.
    """

    entry_id: str
    report_id: str
    feedback_type: str  # "correction", "supplement", "execution", "general"
    submission_url: str | None = None
    deadline: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "entry_id": self.entry_id,
            "report_id": self.report_id,
            "feedback_type": self.feedback_type,
            "submission_url": self.submission_url,
            "deadline": self.deadline,
        }


@dataclass
class ParentWeeklyReport:
    """
    Weekly report for parents showing student's learning progress.

    This is the main output object for the parent view in OBS layer.
    Follows OBS-008 design: 本周摘要，本周变化，当前关注点，重点学科/知识点，家庭可配合事项，反馈入口
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

    # OBS-008: Explanation blocks with observation-evidence-impact structure
    weekly_highlights: list[ExplanationBlock] = field(default_factory=list)
    weekly_concerns: list[ExplanationBlock] = field(default_factory=list)

    # OBS-008: Structured action suggestions instead of plain strings
    suggested_actions: list[ActionSuggestion] = field(default_factory=list)

    # OBS-008: Feedback entry for correction/supplement
    feedback_entry: FeedbackEntry | None = None

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
            "weekly_highlights": [eb.to_dict() for eb in self.weekly_highlights],
            "weekly_concerns": [eb.to_dict() for eb in self.weekly_concerns],
            "suggested_actions": [sa.to_dict() for sa in self.suggested_actions],
            "feedback_entry": self.feedback_entry.to_dict() if self.feedback_entry else None,
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
class ParentMonthlyReport:
    """
    Monthly report for parents showing student's learning progress over a month.

    Follows OBS-008 design: 月度摘要，月度趋势，学科结构变化，重点问题与解释，阶段建议，干预回顾，反馈入口
    Extends weekly report with monthly aggregation and trend analysis.
    """

    report_id: str
    student_id: str
    student_name: str
    month_start: str
    month_end: str
    generated_at: str

    # Aggregated knowledge/ability/chapter data
    knowledge_summary: list[KnowledgeSummary] = field(default_factory=list)
    ability_summary: list[AbilitySummary] = field(default_factory=list)
    chapter_progress: list[ChapterSummary] = field(default_factory=list)
    behavior_summary: list[BehaviorSummary] = field(default_factory=list)

    # Monthly trend analysis
    monthly_highlights: list[ExplanationBlock] = field(default_factory=list)
    monthly_concerns: list[ExplanationBlock] = field(default_factory=list)
    knowledge_trend: str = "stable"  # "improving", "stable", "declining"
    ability_trend: str = "stable"

    # Subject structure changes
    subject_changes: list[dict[str, Any]] = field(default_factory=list)  # [{subject, change_type, delta}]

    # Stage suggestions and intervention review
    suggested_actions: list[ActionSuggestion] = field(default_factory=list)
    intervention_reviews: list[dict[str, Any]] = field(default_factory=list)  # [{action, result, insight}]

    # Feedback entry
    feedback_entry: FeedbackEntry | None = None

    overall_status: str = "normal"  # "normal", "attention", "concern"

    def to_dict(self) -> dict[str, Any]:
        """Serialize report to dictionary."""
        return {
            "report_id": self.report_id,
            "student_id": self.student_id,
            "student_name": self.student_name,
            "month_start": self.month_start,
            "month_end": self.month_end,
            "generated_at": self.generated_at,
            "knowledge_summary": [ks.to_dict() for ks in self.knowledge_summary],
            "ability_summary": [abs.to_dict() for abs in self.ability_summary],
            "chapter_progress": [cs.to_dict() for cs in self.chapter_progress],
            "behavior_summary": [bs.to_dict() for bs in self.behavior_summary],
            "monthly_highlights": [eb.to_dict() for eb in self.monthly_highlights],
            "monthly_concerns": [eb.to_dict() for eb in self.monthly_concerns],
            "knowledge_trend": self.knowledge_trend,
            "ability_trend": self.ability_trend,
            "subject_changes": self.subject_changes,
            "suggested_actions": [sa.to_dict() for sa in self.suggested_actions],
            "intervention_reviews": self.intervention_reviews,
            "feedback_entry": self.feedback_entry.to_dict() if self.feedback_entry else None,
            "overall_status": self.overall_status,
        }

    @classmethod
    def create_empty(
        cls,
        student_id: str,
        student_name: str,
        month_start: str,
        month_end: str,
    ) -> "ParentMonthlyReport":
        """Create an empty monthly report skeleton."""
        now = datetime.now().isoformat()
        return ParentMonthlyReport(
            report_id=f"MR_{month_start}_{student_id}",
            student_id=student_id,
            student_name=student_name,
            month_start=month_start,
            month_end=month_end,
            generated_at=now,
        )

    def compute_overall_status(self) -> str:
        """Compute overall status based on summary data."""
        if self.monthly_concerns:
            self.overall_status = "concern"
        elif self.monthly_highlights:
            self.overall_status = "attention"
        else:
            self.overall_status = "normal"
        return self.overall_status


@dataclass
class TeacherStudentDetail:
    """
    Detailed view for teachers showing individual student status.

    Provides more granular data than parent view for teacher decision-making.
    Follows OBS-003 design: 当前状态摘要，近期变化，知识点结构，题型与误区，关键事件依据，老师反馈区，家校协同提示
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

    # OBS-003: 当前状态摘要与关注点
    overall_status: str = "normal"  # "normal", "attention", "concern"
    focus_subject: str | None = None  # 当前重点学科
    focus_knowledge_points: list[str] = field(default_factory=list)  # 重点知识点
    focus_exercise_types: list[str] = field(default_factory=list)  # 重点题型
    focus_misconceptions: list[str] = field(default_factory=list)  # 重点误区

    # OBS-003: 风险提示
    risk_level: str = "low"  # "low", "medium", "high"
    recent_change: str | None = None  # 近期变化摘要

    # OBS-003: 老师反馈与跟进
    teacher_notes: str | None = None
    last_contact_date: str | None = None
    followed_up: bool = False  # 是否已跟进
    action_items: list[ActionSuggestion] = field(default_factory=list)  # 教学跟进事项

    # OBS-003: 反馈入口
    feedback_entry: FeedbackEntry | None = None

    # OBS-006: 报告周期（用于报告类输出）
    report_period: str | None = None  # "weekly", "monthly", "stage"

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
            "overall_status": self.overall_status,
            "focus_subject": self.focus_subject,
            "focus_knowledge_points": self.focus_knowledge_points,
            "focus_exercise_types": self.focus_exercise_types,
            "focus_misconceptions": self.focus_misconceptions,
            "risk_level": self.risk_level,
            "recent_change": self.recent_change,
            "teacher_notes": self.teacher_notes,
            "last_contact_date": self.last_contact_date,
            "followed_up": self.followed_up,
            "action_items": [ai.to_dict() for ai in self.action_items],
            "feedback_entry": self.feedback_entry.to_dict() if self.feedback_entry else None,
            "report_period": self.report_period,
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

    def compute_focus_areas(
        self,
        knowledge_names: dict[str, str] | None = None,
        exercise_types: list[str] | None = None,
        misconceptions: list[str] | None = None,
    ) -> None:
        """Compute focus areas based on knowledge states and patterns."""
        knowledge_names = knowledge_names or {}

        # Identify focus knowledge points (low mastery or declining)
        focus_kp = []
        for ks in self.knowledge_states:
            if ks.mastery_level < 0.6 or ks.trend == "declining":
                focus_kp.append(knowledge_names.get(ks.knowledge_id, ks.knowledge_id))
        self.focus_knowledge_points = focus_kp

        # Set focus subject based on most problematic knowledge
        if focus_kp and knowledge_names:
            # Simple heuristic: use first knowledge point's subject
            self.focus_subject = "物理"  # Placeholder, should be derived from knowledge mapping

        # Set exercise types and misconceptions
        self.focus_exercise_types = exercise_types or []
        self.focus_misconceptions = misconceptions or []

    def compute_risk_level(self) -> str:
        """Compute risk level based on knowledge states and alerts."""
        low_mastery_count = sum(1 for ks in self.knowledge_states if ks.mastery_level < 0.5)
        declining_count = sum(1 for ks in self.knowledge_states if ks.trend == "declining")

        if low_mastery_count >= 3 or declining_count >= 2:
            self.risk_level = "high"
        elif low_mastery_count >= 1 or declining_count >= 1:
            self.risk_level = "medium"
        else:
            self.risk_level = "low"

        return self.risk_level


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
    condition: str  # "no_knowledge_data", "no_ability_data", "low_confidence", "no_class_data", "low_coverage"
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
        elif self.condition == "no_class_data":
            return not data_available.get("class_data", False)
        elif self.condition == "low_coverage":
            return not data_available.get("coverage", False)
        return False

    def get_display_content(self) -> dict[str, Any]:
        """Get fallback display content."""
        return {
            "display_mode": self.display_mode,
            "message": self.message,
            "fallback": self.fallback_content,
        }


@dataclass(frozen=True)
class RiskDistribution:
    """Risk distribution for class/school aggregate view."""

    low_risk_count: int = 0
    medium_risk_count: int = 0
    high_risk_count: int = 0
    risk_trend: str = "stable"  # "rising", "stable", "falling"

    @property
    def total_students(self) -> int:
        return self.low_risk_count + self.medium_risk_count + self.high_risk_count

    @property
    def high_risk_rate(self) -> float:
        if self.total_students == 0:
            return 0.0
        return self.high_risk_count / self.total_students

    def to_dict(self) -> dict[str, Any]:
        return {
            "low_risk_count": self.low_risk_count,
            "medium_risk_count": self.medium_risk_count,
            "high_risk_count": self.high_risk_count,
            "risk_trend": self.risk_trend,
            "total_students": self.total_students,
            "high_risk_rate": self.high_risk_rate,
        }


@dataclass(frozen=True)
class SubjectIssue:
    """Subject-level issue aggregation for dashboard."""

    subject: str
    issue_type: str  # "knowledge_point", "question_type", "behavior"
    issue_name: str
    affected_students: int
    trend: str  # "rising", "stable", "falling"
    priority: str = "medium"  # "high", "medium", "low"

    def to_dict(self) -> dict[str, Any]:
        return {
            "subject": self.subject,
            "issue_type": self.issue_type,
            "issue_name": self.issue_name,
            "affected_students": self.affected_students,
            "trend": self.trend,
            "priority": self.priority,
        }


@dataclass
class ClassDashboardSummary:
    """
    Class-level aggregate view for school dashboard.

    Core output object for class view in OBS layer.
    """

    dashboard_id: str
    class_id: str
    class_name: str
    school_id: str
    grade_id: str
    generated_at: str

    # Core metrics
    total_students: int = 0
    active_students: int = 0
    data_coverage_rate: float = 0.0

    # Risk distribution
    risk_distribution: RiskDistribution = field(default_factory=RiskDistribution)

    # Subject issues (Top N)
    subject_issues: list[SubjectIssue] = field(default_factory=list)

    # Follow-up & feedback
    follow_up_rate: float = 0.0  # Focus student follow-up rate
    feedback_rate: float = 0.0   # Feedback coverage rate

    # Trend (last 7 days)
    trend_direction: str = "stable"  # "improving", "stable", "declining"

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "dashboard_id": self.dashboard_id,
            "class_id": self.class_id,
            "class_name": self.class_name,
            "school_id": self.school_id,
            "grade_id": self.grade_id,
            "generated_at": self.generated_at,
            "total_students": self.total_students,
            "active_students": self.active_students,
            "data_coverage_rate": self.data_coverage_rate,
            "risk_distribution": self.risk_distribution.to_dict(),
            "subject_issues": [si.to_dict() for si in self.subject_issues],
            "follow_up_rate": self.follow_up_rate,
            "feedback_rate": self.feedback_rate,
            "trend_direction": self.trend_direction,
        }

    @classmethod
    def create_empty(
        cls,
        class_id: str,
        class_name: str,
        school_id: str,
        grade_id: str,
    ) -> "ClassDashboardSummary":
        """Create an empty class dashboard skeleton."""
        now = datetime.now().isoformat()
        return ClassDashboardSummary(
            dashboard_id=f"CLS_DASH_{class_id}_{datetime.now().strftime('%Y%m%d')}",
            class_id=class_id,
            class_name=class_name,
            school_id=school_id,
            grade_id=grade_id,
            generated_at=now,
        )


@dataclass(frozen=True)
class GradeSummary:
    """Grade-level aggregate for school dashboard."""

    grade_id: str
    grade_name: str
    class_count: int
    student_count: int
    risk_distribution: RiskDistribution

    def to_dict(self) -> dict[str, Any]:
        return {
            "grade_id": self.grade_id,
            "grade_name": self.grade_name,
            "class_count": self.class_count,
            "student_count": self.student_count,
            "risk_distribution": self.risk_distribution.to_dict(),
        }


@dataclass(frozen=True)
class MajorIssue:
    """Major issue aggregation for school dashboard."""

    issue_category: str  # "subject", "knowledge", "behavior"
    issue_summary: str
    affected_grades: int
    affected_classes: int
    priority: str  # "high", "medium", "low"

    def to_dict(self) -> dict[str, Any]:
        return {
            "issue_category": self.issue_category,
            "issue_summary": self.issue_summary,
            "affected_grades": self.affected_grades,
            "affected_classes": self.affected_classes,
            "priority": self.priority,
        }


@dataclass(frozen=True)
class FollowUpStatus:
    """Follow-up status for school dashboard."""

    focus_student_followed_rate: float = 0.0
    teacher_feedback_rate: float = 0.0
    parent_feedback_rate: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "focus_student_followed_rate": self.focus_student_followed_rate,
            "teacher_feedback_rate": self.teacher_feedback_rate,
            "parent_feedback_rate": self.parent_feedback_rate,
        }


@dataclass
class SchoolDashboardSummary:
    """
    School-level aggregate view for school dashboard.

    Core output object for school view in OBS layer.
    """

    dashboard_id: str
    school_id: str
    school_name: str
    generated_at: str

    # Coverage & access
    total_classes: int = 0
    total_students: int = 0
    active_rate: float = 0.0

    # Grade summaries
    grade_summaries: list[GradeSummary] = field(default_factory=list)

    # Major issues
    major_issues: list[MajorIssue] = field(default_factory=list)

    # Follow-up status
    follow_up_status: FollowUpStatus = field(default_factory=FollowUpStatus)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "dashboard_id": self.dashboard_id,
            "school_id": self.school_id,
            "school_name": self.school_name,
            "generated_at": self.generated_at,
            "total_classes": self.total_classes,
            "total_students": self.total_students,
            "active_rate": self.active_rate,
            "grade_summaries": [gs.to_dict() for gs in self.grade_summaries],
            "major_issues": [mi.to_dict() for mi in self.major_issues],
            "follow_up_status": self.follow_up_status.to_dict(),
        }

    @classmethod
    def create_empty(
        cls,
        school_id: str,
        school_name: str,
    ) -> "SchoolDashboardSummary":
        """Create an empty school dashboard skeleton."""
        now = datetime.now().isoformat()
        return SchoolDashboardSummary(
            dashboard_id=f"SCH_DASH_{school_id}_{datetime.now().strftime('%Y%m%d')}",
            school_id=school_id,
            school_name=school_name,
            generated_at=now,
        )


class OBSDisplayBuilder:
    """
    Builder for OBS display objects with degraded display support.

    Handles:
    1. Building parent weekly reports
    2. Building teacher student details
    3. Building school/class dashboard summaries
    4. Applying degraded display rules when data is incomplete
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
            DegradedDisplayRule(
                rule_id="DDR_004",
                condition="no_class_data",
                display_mode="show_partial",
                message="班级聚合数据不足，请继续积累数据",
                fallback_content={"risk_distribution": None, "subject_issues": []},
            ),
            DegradedDisplayRule(
                rule_id="DDR_005",
                condition="low_coverage",
                display_mode="show_placeholder",
                message="数据覆盖率较低，当前结论仅供参考",
                fallback_content={"coverage_warning": True},
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
        exercise_types: list[str] | None = None,
        misconceptions: list[str] | None = None,
    ) -> TeacherStudentDetail:
        """
        Build a teacher student detail from twin state.

        Follows OBS-003 design with focus areas, risk level, and action items.
        """
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

        # Compute alert flags
        alert_flags: list[str] = []
        for ks in detail.knowledge_states:
            if ks.mastery_level < 0.3:
                alert_flags.append(f"low_mastery:{ks.knowledge_name}")
            if ks.trend == "declining":
                alert_flags.append(f"declining:{ks.knowledge_name}")
        detail.alert_flags = alert_flags

        # Compute focus areas (OBS-003)
        detail.compute_focus_areas(
            knowledge_names=knowledge_names,
            exercise_types=exercise_types,
            misconceptions=misconceptions,
        )

        # Compute risk level (OBS-003)
        detail.compute_risk_level()

        # Set recent change summary (OBS-003)
        if detail.risk_level == "high":
            detail.recent_change = "近 7 天问题上升，建议优先跟进"
        elif detail.risk_level == "medium":
            detail.recent_change = "近 14 天有波动，建议持续观察"
        else:
            detail.recent_change = "近期整体稳定"

        return detail

    def build_class_dashboard_summary(
        self,
        class_id: str,
        class_name: str,
        school_id: str,
        grade_id: str,
        aggregate_data: dict[str, Any],
    ) -> ClassDashboardSummary:
        """Build a class dashboard summary from aggregate data."""
        dashboard = ClassDashboardSummary.create_empty(
            class_id=class_id,
            class_name=class_name,
            school_id=school_id,
            grade_id=grade_id,
        )

        dashboard.total_students = aggregate_data.get("total_students", 0)
        dashboard.active_students = aggregate_data.get("active_students", 0)
        dashboard.data_coverage_rate = aggregate_data.get("data_coverage_rate", 0.0)

        risk_data = aggregate_data.get("risk_distribution", {})
        dashboard.risk_distribution = RiskDistribution(
            low_risk_count=risk_data.get("low_risk_count", 0),
            medium_risk_count=risk_data.get("medium_risk_count", 0),
            high_risk_count=risk_data.get("high_risk_count", 0),
            risk_trend=risk_data.get("risk_trend", "stable"),
        )

        subject_issues_data = aggregate_data.get("subject_issues", [])
        for issue_data in subject_issues_data:
            dashboard.subject_issues.append(SubjectIssue(
                subject=issue_data.get("subject", ""),
                issue_type=issue_data.get("issue_type", "knowledge_point"),
                issue_name=issue_data.get("issue_name", ""),
                affected_students=issue_data.get("affected_students", 0),
                trend=issue_data.get("trend", "stable"),
                priority=issue_data.get("priority", "medium"),
            ))

        dashboard.follow_up_rate = aggregate_data.get("follow_up_rate", 0.0)
        dashboard.feedback_rate = aggregate_data.get("feedback_rate", 0.0)
        dashboard.trend_direction = aggregate_data.get("trend_direction", "stable")

        return dashboard

    def build_school_dashboard_summary(
        self,
        school_id: str,
        school_name: str,
        aggregate_data: dict[str, Any],
    ) -> SchoolDashboardSummary:
        """Build a school dashboard summary from aggregate data."""
        dashboard = SchoolDashboardSummary.create_empty(
            school_id=school_id,
            school_name=school_name,
        )

        dashboard.total_classes = aggregate_data.get("total_classes", 0)
        dashboard.total_students = aggregate_data.get("total_students", 0)
        dashboard.active_rate = aggregate_data.get("active_rate", 0.0)

        grade_data_list = aggregate_data.get("grade_summaries", [])
        for grade_data in grade_data_list:
            risk_data = grade_data.get("risk_distribution", {})
            grade_summary = GradeSummary(
                grade_id=grade_data.get("grade_id", ""),
                grade_name=grade_data.get("grade_name", ""),
                class_count=grade_data.get("class_count", 0),
                student_count=grade_data.get("student_count", 0),
                risk_distribution=RiskDistribution(
                    low_risk_count=risk_data.get("low_risk_count", 0),
                    medium_risk_count=risk_data.get("medium_risk_count", 0),
                    high_risk_count=risk_data.get("high_risk_count", 0),
                    risk_trend=risk_data.get("risk_trend", "stable"),
                ),
            )
            dashboard.grade_summaries.append(grade_summary)

        major_issues_data = aggregate_data.get("major_issues", [])
        for issue_data in major_issues_data:
            dashboard.major_issues.append(MajorIssue(
                issue_category=issue_data.get("issue_category", ""),
                issue_summary=issue_data.get("issue_summary", ""),
                affected_grades=issue_data.get("affected_grades", 0),
                affected_classes=issue_data.get("affected_classes", 0),
                priority=issue_data.get("priority", "medium"),
            ))

        follow_up_data = aggregate_data.get("follow_up_status", {})
        dashboard.follow_up_status = FollowUpStatus(
            focus_student_followed_rate=follow_up_data.get("focus_student_followed_rate", 0.0),
            teacher_feedback_rate=follow_up_data.get("teacher_feedback_rate", 0.0),
            parent_feedback_rate=follow_up_data.get("parent_feedback_rate", 0.0),
        )

        return dashboard

    def apply_degraded_rules_to_dashboard(
        self,
        dashboard: ClassDashboardSummary | SchoolDashboardSummary,
        data_available: dict[str, bool],
    ) -> tuple[ClassDashboardSummary | SchoolDashboardSummary, list[str]]:
        """Apply degraded display rules to a dashboard summary."""
        applied_messages: list[str] = []

        for rule in self.degraded_rules:
            if rule.should_apply(data_available):
                applied_messages.append(rule.message)

        return dashboard, applied_messages

    def build_parent_monthly_report(
        self,
        student_id: str,
        student_name: str,
        month_start: str,
        month_end: str,
        twin_state: dict[str, Any],
        weekly_reports: list[ParentWeeklyReport] | None = None,
        knowledge_names: dict[str, str] | None = None,
        ability_names: dict[str, str] | None = None,
        chapter_names: dict[str, str] | None = None,
    ) -> ParentMonthlyReport:
        """
        Build a parent monthly report from twin state and weekly reports.

        Monthly report aggregates 4 weekly reports and adds trend analysis,
        subject structure changes, and intervention reviews.
        """
        report = ParentMonthlyReport.create_empty(
            student_id=student_id,
            student_name=student_name,
            month_start=month_start,
            month_end=month_end,
        )

        knowledge_names = knowledge_names or {}
        ability_names = ability_names or {}
        chapter_names = chapter_names or {}

        # Aggregate knowledge/ability/chapter from twin state
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

        # Compute trends from weekly reports
        if weekly_reports and len(weekly_reports) >= 2:
            # Simple trend computation: compare first week to last week
            first_week = weekly_reports[0]
            last_week = weekly_reports[-1]

            # Knowledge trend
            if first_week.knowledge_summary and last_week.knowledge_summary:
                first_avg = sum(k.mastery_level for k in first_week.knowledge_summary) / len(first_week.knowledge_summary)
                last_avg = sum(k.mastery_level for k in last_week.knowledge_summary) / len(last_week.knowledge_summary)
                if last_avg > first_avg + 0.1:
                    report.knowledge_trend = "improving"
                elif last_avg < first_avg - 0.1:
                    report.knowledge_trend = "declining"

            # Ability trend
            if first_week.ability_summary and last_week.ability_summary:
                first_avg = sum(a.ability_level for a in first_week.ability_summary) / len(first_week.ability_summary)
                last_avg = sum(a.ability_level for a in last_week.ability_summary) / len(last_week.ability_summary)
                if last_avg > first_avg + 0.1:
                    report.ability_trend = "improving"
                elif last_avg < first_avg - 0.1:
                    report.ability_trend = "declining"

            # Aggregate highlights/concerns from weekly reports
            for i, wr in enumerate(weekly_reports):
                for highlight in wr.weekly_highlights:
                    report.monthly_highlights.append(highlight)
                for concern in wr.weekly_concerns:
                    report.monthly_concerns.append(concern)

        report.compute_overall_status()
        return report
