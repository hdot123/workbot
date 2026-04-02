"""Feedback event models for OBS-010 feedback loop.

This module defines the feedback event structure that captures user feedback
from parents, teachers, and school administrators, and routes it to appropriate
processing pools.

Follows OBS-010 design:
- feedback_type: 状态校准类，产品体验类，实施推进类，异常故障类
- target_type: 报告，学生详情，班级看板，学校总览
- status: pending, routed, in_progress, resolved, closed
- routed_to: review_queue, product_pool, operation_pool, tech_pool
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


# Feedback type enumeration (OBS-010 Section 20)
FEEDBACK_TYPE_CALIBRATION = "calibration"  # 状态校准类
FEEDBACK_TYPE_EXPERIENCE = "experience"    # 产品体验类
FEEDBACK_TYPE_OPERATION = "operation"      # 实施推进类
FEEDBACK_TYPE_EXCEPTION = "exception"      # 异常故障类

FEEDBACK_TYPES = frozenset({
    FEEDBACK_TYPE_CALIBRATION,
    FEEDBACK_TYPE_EXPERIENCE,
    FEEDBACK_TYPE_OPERATION,
    FEEDBACK_TYPE_EXCEPTION,
})

# Feedback status enumeration
FEEDBACK_STATUS_PENDING = "pending"
FEEDBACK_STATUS_ROUTED = "routed"
FEEDBACK_STATUS_IN_PROGRESS = "in_progress"
FEEDBACK_STATUS_RESOLVED = "resolved"
FEEDBACK_STATUS_CLOSED = "closed"

FEEDBACK_STATUSES = frozenset({
    FEEDBACK_STATUS_PENDING,
    FEEDBACK_STATUS_ROUTED,
    FEEDBACK_STATUS_IN_PROGRESS,
    FEEDBACK_STATUS_RESOLVED,
    FEEDBACK_STATUS_CLOSED,
})

# Target type enumeration (where feedback comes from)
FEEDBACK_TARGET_PARENT_REPORT = "parent_report"
FEEDBACK_TARGET_TEACHER_DETAIL = "teacher_detail"
FEEDBACK_TARGET_CLASS_DASHBOARD = "class_dashboard"
FEEDBACK_TARGET_SCHOOL_DASHBOARD = "school_dashboard"
FEEDBACK_TARGET_HOME = "home"

FEEDBACK_TARGETS = frozenset({
    FEEDBACK_TARGET_PARENT_REPORT,
    FEEDBACK_TARGET_TEACHER_DETAIL,
    FEEDBACK_TARGET_CLASS_DASHBOARD,
    FEEDBACK_TARGET_SCHOOL_DASHBOARD,
    FEEDBACK_TARGET_HOME,
})

# Source role enumeration
FEEDBACK_ROLE_PARENT = "parent"
FEEDBACK_ROLE_TEACHER = "teacher"
FEEDBACK_ROLE_SCHOOL = "school"
FEEDBACK_ROLE_OPERATION = "operation"

FEEDBACK_ROLES = frozenset({
    FEEDBACK_ROLE_PARENT,
    FEEDBACK_ROLE_TEACHER,
    FEEDBACK_ROLE_SCHOOL,
    FEEDBACK_ROLE_OPERATION,
})

# Routing destinations (OBS-010 Section 20-24)
ROUTE_REVIEW_QUEUE = "review_queue"       # 状态校准 -> 人工校准池
ROUTE_PRODUCT_POOL = "product_pool"       # 产品体验 -> 产品优化池
ROUTE_OPERATION_POOL = "operation_pool"   # 实施推进 -> 运营动作池
ROUTE_TECH_POOL = "tech_pool"             # 异常故障 -> 技术问题池

ROUTE_DESTINATIONS = frozenset({
    ROUTE_REVIEW_QUEUE,
    ROUTE_PRODUCT_POOL,
    ROUTE_OPERATION_POOL,
    ROUTE_TECH_POOL,
})


PROBLEM_SEVERITY_P0 = "P0"
PROBLEM_SEVERITY_P1 = "P1"
PROBLEM_SEVERITY_P2 = "P2"

PROBLEM_SEVERITIES = frozenset({
    PROBLEM_SEVERITY_P0,
    PROBLEM_SEVERITY_P1,
    PROBLEM_SEVERITY_P2,
})

PROBLEM_STATUS_PENDING_ANALYSIS = "pending_analysis"
PROBLEM_STATUS_IN_PROGRESS = "in_progress"
PROBLEM_STATUS_PENDING_VERIFICATION = "pending_verification"
PROBLEM_STATUS_CLOSED = "closed"

PROBLEM_STATUSES = frozenset({
    PROBLEM_STATUS_PENDING_ANALYSIS,
    PROBLEM_STATUS_IN_PROGRESS,
    PROBLEM_STATUS_PENDING_VERIFICATION,
    PROBLEM_STATUS_CLOSED,
})


@dataclass(frozen=True)
class FeedbackOption:
    """
    Predefined feedback option for quick selection.

    Used in light-touch feedback scenarios (OBS-010 Section 10, 17, 18).
    """

    option_id: str
    label: str  # Display text
    feedback_type: str  # Maps to FEEDBACK_TYPE_*
    value: str | None = None  # Optional payload


@dataclass
class PilotProblem:
    """Pilot issue record for OPS-006/007/008 traceability."""

    problem_id: str
    source: str
    problem_type: str
    title: str
    description: str
    scope: str
    severity: str
    status: str
    owner: str
    created_at: str
    closed_at: str | None = None
    root_cause: str | None = None
    solution: str | None = None
    related_docs: list[str] = field(default_factory=list)
    related_feedback_ids: list[str] = field(default_factory=list)
    resolution_notes: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "problem_id": self.problem_id,
            "source": self.source,
            "problem_type": self.problem_type,
            "title": self.title,
            "description": self.description,
            "scope": self.scope,
            "severity": self.severity,
            "status": self.status,
            "owner": self.owner,
            "created_at": self.created_at,
            "closed_at": self.closed_at,
            "root_cause": self.root_cause,
            "solution": self.solution,
            "related_docs": self.related_docs,
            "related_feedback_ids": self.related_feedback_ids,
            "resolution_notes": self.resolution_notes,
        }

    def validate(self) -> tuple[bool, list[str]]:
        errors: list[str] = []

        if not self.problem_id:
            errors.append("problem_id is required")
        if not self.problem_type:
            errors.append("problem_type is required")
        if not self.title:
            errors.append("title is required")
        if not self.scope:
            errors.append("scope is required")
        if self.severity not in PROBLEM_SEVERITIES:
            errors.append(f"invalid severity: {self.severity}")
        if self.status not in PROBLEM_STATUSES:
            errors.append(f"invalid status: {self.status}")
        if self.status == PROBLEM_STATUS_CLOSED and not self.closed_at:
            errors.append("closed_at is required when status is closed")

        return (len(errors) == 0, errors)

    def mark_in_progress(self, owner: str | None = None) -> None:
        self.status = PROBLEM_STATUS_IN_PROGRESS
        if owner:
            self.owner = owner

    def mark_pending_verification(self) -> None:
        self.status = PROBLEM_STATUS_PENDING_VERIFICATION

    def close(
        self,
        resolution_notes: str,
        solution: str | None = None,
        root_cause: str | None = None,
    ) -> None:
        self.status = PROBLEM_STATUS_CLOSED
        self.closed_at = datetime.now().isoformat()
        self.resolution_notes = resolution_notes
        if solution:
            self.solution = solution
        if root_cause:
            self.root_cause = root_cause

    def reopen(self, resolution_notes: str | None = None) -> None:
        self.status = PROBLEM_STATUS_IN_PROGRESS
        self.closed_at = None
        if resolution_notes:
            self.resolution_notes = resolution_notes


@dataclass(frozen=True)
class FeedbackTraceabilitySnapshot:
    """Aggregate feedback and pilot-issue metrics for OPS-007 review."""

    generated_at: str
    total_feedback: int
    parent_feedback_count: int
    teacher_feedback_count: int
    school_feedback_count: int
    operation_feedback_count: int
    resolved_feedback_count: int
    total_problems: int
    closed_problem_count: int
    parent_feedback_submit_rate: float
    teacher_feedback_submit_rate: float
    resolved_feedback_rate: float
    closed_problem_rate: float
    intervention_fill_rate: float
    feedback_by_type: dict[str, int]
    problem_by_type: dict[str, int]
    open_problem_count: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "generated_at": self.generated_at,
            "total_feedback": self.total_feedback,
            "parent_feedback_count": self.parent_feedback_count,
            "teacher_feedback_count": self.teacher_feedback_count,
            "school_feedback_count": self.school_feedback_count,
            "operation_feedback_count": self.operation_feedback_count,
            "resolved_feedback_count": self.resolved_feedback_count,
            "total_problems": self.total_problems,
            "closed_problem_count": self.closed_problem_count,
            "parent_feedback_submit_rate": self.parent_feedback_submit_rate,
            "teacher_feedback_submit_rate": self.teacher_feedback_submit_rate,
            "resolved_feedback_rate": self.resolved_feedback_rate,
            "closed_problem_rate": self.closed_problem_rate,
            "intervention_fill_rate": self.intervention_fill_rate,
            "feedback_by_type": self.feedback_by_type,
            "problem_by_type": self.problem_by_type,
            "open_problem_count": self.open_problem_count,
        }


class FeedbackTraceabilityBuilder:
    """Build OPS-007 metrics and OPS-008 review summaries from feedback objects."""

    def build_snapshot(
        self,
        feedback_events: list["FeedbackEvent"],
        pilot_problems: list[PilotProblem],
        *,
        active_parent_users: int = 0,
        active_teacher_users: int = 0,
        executed_interventions: int = 0,
    ) -> FeedbackTraceabilitySnapshot:
        feedback_by_type = {feedback_type: 0 for feedback_type in FEEDBACK_TYPES}
        problem_by_type: dict[str, int] = {}

        parent_feedback_count = 0
        teacher_feedback_count = 0
        school_feedback_count = 0
        operation_feedback_count = 0
        resolved_feedback_count = 0

        for feedback in feedback_events:
            feedback_by_type[feedback.feedback_type] = feedback_by_type.get(feedback.feedback_type, 0) + 1

            if feedback.source_role == FEEDBACK_ROLE_PARENT:
                parent_feedback_count += 1
            elif feedback.source_role == FEEDBACK_ROLE_TEACHER:
                teacher_feedback_count += 1
            elif feedback.source_role == FEEDBACK_ROLE_SCHOOL:
                school_feedback_count += 1
            elif feedback.source_role == FEEDBACK_ROLE_OPERATION:
                operation_feedback_count += 1

            if feedback.status in {FEEDBACK_STATUS_RESOLVED, FEEDBACK_STATUS_CLOSED}:
                resolved_feedback_count += 1

        closed_problem_count = 0
        for problem in pilot_problems:
            problem_by_type[problem.problem_type] = problem_by_type.get(problem.problem_type, 0) + 1
            if problem.status == PROBLEM_STATUS_CLOSED:
                closed_problem_count += 1

        parent_feedback_submit_rate = self._safe_rate(parent_feedback_count, active_parent_users)
        teacher_feedback_submit_rate = self._safe_rate(teacher_feedback_count, active_teacher_users)
        resolved_feedback_rate = self._safe_rate(resolved_feedback_count, len(feedback_events))
        closed_problem_rate = self._safe_rate(closed_problem_count, len(pilot_problems))

        resolved_operation_feedbacks = sum(
            1
            for feedback in feedback_events
            if feedback.feedback_type == FEEDBACK_TYPE_OPERATION
            and feedback.status in {FEEDBACK_STATUS_RESOLVED, FEEDBACK_STATUS_CLOSED}
        )
        intervention_fill_rate = self._safe_rate(resolved_operation_feedbacks, executed_interventions)

        return FeedbackTraceabilitySnapshot(
            generated_at=datetime.now().isoformat(),
            total_feedback=len(feedback_events),
            parent_feedback_count=parent_feedback_count,
            teacher_feedback_count=teacher_feedback_count,
            school_feedback_count=school_feedback_count,
            operation_feedback_count=operation_feedback_count,
            resolved_feedback_count=resolved_feedback_count,
            total_problems=len(pilot_problems),
            closed_problem_count=closed_problem_count,
            parent_feedback_submit_rate=parent_feedback_submit_rate,
            teacher_feedback_submit_rate=teacher_feedback_submit_rate,
            resolved_feedback_rate=resolved_feedback_rate,
            closed_problem_rate=closed_problem_rate,
            intervention_fill_rate=intervention_fill_rate,
            feedback_by_type=feedback_by_type,
            problem_by_type=problem_by_type,
            open_problem_count=len(pilot_problems) - closed_problem_count,
        )

    def build_review_summary(
        self,
        feedback_events: list["FeedbackEvent"],
        pilot_problems: list[PilotProblem],
    ) -> dict[str, Any]:
        feedback_status_counts: dict[str, int] = {}
        for feedback in feedback_events:
            feedback_status_counts[feedback.status] = feedback_status_counts.get(feedback.status, 0) + 1

        problem_status_counts: dict[str, int] = {}
        problem_type_counts: dict[str, int] = {}
        for problem in pilot_problems:
            problem_status_counts[problem.status] = problem_status_counts.get(problem.status, 0) + 1
            problem_type_counts[problem.problem_type] = problem_type_counts.get(problem.problem_type, 0) + 1

        top_problem_types = sorted(
            problem_type_counts.items(),
            key=lambda item: (-item[1], item[0]),
        )

        return {
            "generated_at": datetime.now().isoformat(),
            "feedback_total": len(feedback_events),
            "problem_total": len(pilot_problems),
            "feedback_status_counts": feedback_status_counts,
            "problem_status_counts": problem_status_counts,
            "top_problem_types": top_problem_types,
        }

    @staticmethod
    def _safe_rate(numerator: int, denominator: int) -> float:
        if denominator <= 0:
            return 0.0
        return numerator / denominator


@dataclass
class FeedbackEvent:
    """
    Feedback event capturing user input from product interaction.

    Follows OBS-010 Section 27 field recommendations:
    - feedback_id, source_role, source_user_id, tenant_id
    - target_type, target_ref, feedback_type
    - feedback_text / option, created_at, status
    - routed_to, resolved_at

    MVP fields only - extensible for future needs.
    """

    feedback_id: str
    source_role: str  # FEEDBACK_ROLE_*
    source_user_id: str
    tenant_id: str  # School or organization ID

    target_type: str  # FEEDBACK_TARGET_*
    target_ref: str  # Reference to target object (report_id, student_id, etc.)
    feedback_type: str  # FEEDBACK_TYPE_*

    created_at: str
    status: str = FEEDBACK_STATUS_PENDING  # FEEDBACK_STATUS_*

    # Feedback content - either option_id or text
    feedback_option_id: str | None = None
    feedback_text: str | None = None

    # Optional structured data
    rating: int | None = None  # 1-5 scale if applicable
    tags: list[str] = field(default_factory=list)

    # Routing information (populated by system)
    routed_to: str | None = None  # ROUTE_*
    assigned_to: str | None = None  # User ID if assigned
    resolved_at: str | None = None
    resolution_notes: str | None = None

    # Context capture
    page_url: str | None = None
    session_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize feedback event to dictionary."""
        return {
            "feedback_id": self.feedback_id,
            "source_role": self.source_role,
            "source_user_id": self.source_user_id,
            "tenant_id": self.tenant_id,
            "target_type": self.target_type,
            "target_ref": self.target_ref,
            "feedback_type": self.feedback_type,
            "created_at": self.created_at,
            "status": self.status,
            "feedback_option_id": self.feedback_option_id,
            "feedback_text": self.feedback_text,
            "rating": self.rating,
            "tags": self.tags,
            "routed_to": self.routed_to,
            "assigned_to": self.assigned_to,
            "resolved_at": self.resolved_at,
            "resolution_notes": self.resolution_notes,
            "page_url": self.page_url,
            "session_id": self.session_id,
        }

    @classmethod
    def create_from_option(
        cls,
        source_role: str,
        source_user_id: str,
        tenant_id: str,
        target_type: str,
        target_ref: str,
        feedback_option: FeedbackOption,
        page_url: str | None = None,
        session_id: str | None = None,
    ) -> "FeedbackEvent":
        """Create feedback event from predefined option."""
        now = datetime.now().isoformat()
        return cls(
            feedback_id=f"FB_{now.replace('-', '').replace(':', '').replace('.', '')[:15]}_{source_user_id[:8]}",
            source_role=source_role,
            source_user_id=source_user_id,
            tenant_id=tenant_id,
            target_type=target_type,
            target_ref=target_ref,
            feedback_type=feedback_option.feedback_type,
            created_at=now,
            feedback_option_id=feedback_option.option_id,
            feedback_text=feedback_option.label,
            page_url=page_url,
            session_id=session_id,
        )

    @classmethod
    def create_from_text(
        cls,
        source_role: str,
        source_user_id: str,
        tenant_id: str,
        target_type: str,
        target_ref: str,
        feedback_type: str,
        feedback_text: str,
        tags: list[str] | None = None,
        page_url: str | None = None,
        session_id: str | None = None,
    ) -> "FeedbackEvent":
        """Create feedback event from free text input."""
        now = datetime.now().isoformat()
        return cls(
            feedback_id=f"FB_{now.replace('-', '').replace(':', '').replace('.', '')[:15]}_{source_user_id[:8]}",
            source_role=source_role,
            source_user_id=source_user_id,
            tenant_id=tenant_id,
            target_type=target_type,
            target_ref=target_ref,
            feedback_type=feedback_type,
            created_at=now,
            feedback_text=feedback_text,
            tags=tags or [],
            page_url=page_url,
            session_id=session_id,
        )

    def route(self) -> str:
        """
        Determine routing destination based on feedback type.

        Returns the route destination (ROUTE_*) and updates routed_to.

        Follows OBS-010 Section 20-24 routing rules:
        - calibration -> review_queue
        - experience -> product_pool
        - operation -> operation_pool
        - exception -> tech_pool
        """
        if self.feedback_type == FEEDBACK_TYPE_CALIBRATION:
            self.routed_to = ROUTE_REVIEW_QUEUE
        elif self.feedback_type == FEEDBACK_TYPE_EXPERIENCE:
            self.routed_to = ROUTE_PRODUCT_POOL
        elif self.feedback_type == FEEDBACK_TYPE_OPERATION:
            self.routed_to = ROUTE_OPERATION_POOL
        elif self.feedback_type == FEEDBACK_TYPE_EXCEPTION:
            self.routed_to = ROUTE_TECH_POOL
        else:
            # Unknown type defaults to review queue
            self.routed_to = ROUTE_REVIEW_QUEUE

        self.status = FEEDBACK_STATUS_ROUTED
        return self.routed_to

    def mark_resolved(self, resolution_notes: str | None = None) -> None:
        """Mark feedback as resolved."""
        self.status = FEEDBACK_STATUS_RESOLVED
        self.resolved_at = datetime.now().isoformat()
        if resolution_notes:
            self.resolution_notes = resolution_notes

    def mark_in_progress(self, assigned_to: str | None = None) -> None:
        """Mark feedback as in progress."""
        self.status = FEEDBACK_STATUS_IN_PROGRESS
        if assigned_to:
            self.assigned_to = assigned_to

    def validate(self) -> tuple[bool, list[str]]:
        """
        Validate feedback event structure.

        Returns (is_valid, error_messages).
        """
        errors: list[str] = []

        if self.source_role not in FEEDBACK_ROLES:
            errors.append(f"invalid source_role: {self.source_role}")

        if self.target_type not in FEEDBACK_TARGETS:
            errors.append(f"invalid target_type: {self.target_type}")

        if self.feedback_type not in FEEDBACK_TYPES:
            errors.append(f"invalid feedback_type: {self.feedback_type}")

        if self.status not in FEEDBACK_STATUSES:
            errors.append(f"invalid status: {self.status}")

        if self.routed_to and self.routed_to not in ROUTE_DESTINATIONS:
            errors.append(f"invalid routed_to: {self.routed_to}")

        if not self.feedback_option_id and not self.feedback_text:
            errors.append("either feedback_option_id or feedback_text must be provided")

        if self.rating is not None and not (1 <= self.rating <= 5):
            errors.append(f"rating must be 1-5, got: {self.rating}")

        return (len(errors) == 0, errors)


@dataclass
class FeedbackRouter:
    """
    Router for processing and routing feedback events.

    Provides routing logic and pool management helpers.
    """

    # Routing table: feedback_type -> route_destination
    routing_table: dict[str, str] = field(default_factory=lambda: {
        FEEDBACK_TYPE_CALIBRATION: ROUTE_REVIEW_QUEUE,
        FEEDBACK_TYPE_EXPERIENCE: ROUTE_PRODUCT_POOL,
        FEEDBACK_TYPE_OPERATION: ROUTE_OPERATION_POOL,
        FEEDBACK_TYPE_EXCEPTION: ROUTE_TECH_POOL,
    })

    def route_feedback(self, feedback: FeedbackEvent) -> str:
        """Route a feedback event to appropriate pool."""
        destination = self.routing_table.get(
            feedback.feedback_type,
            ROUTE_REVIEW_QUEUE
        )
        feedback.routed_to = destination
        feedback.status = FEEDBACK_STATUS_ROUTED
        return destination

    def get_pool_name(self, route_destination: str) -> str:
        """Get human-readable pool name for route destination."""
        pool_names = {
            ROUTE_REVIEW_QUEUE: "状态校准池",
            ROUTE_PRODUCT_POOL: "产品优化池",
            ROUTE_OPERATION_POOL: "运营动作池",
            ROUTE_TECH_POOL: "技术问题池",
        }
        return pool_names.get(route_destination, "未分类池")


# Predefined feedback options for common scenarios (OBS-010 Section 10, 11, 17, 18)

# Parent report feedback options
PARENT_REPORT_OPTIONS = [
    FeedbackOption(
        option_id="PR_ACCURATE",
        label="报告内容贴近实际",
        feedback_type=FEEDBACK_TYPE_EXPERIENCE,
        value="positive",
    ),
    FeedbackOption(
        option_id="PR_INACCURATE",
        label="报告内容与实际不符",
        feedback_type=FEEDBACK_TYPE_CALIBRATION,
        value="calibration_needed",
    ),
    FeedbackOption(
        option_id="PR_HELPFUL",
        label="报告对我有帮助",
        feedback_type=FEEDBACK_TYPE_EXPERIENCE,
        value="helpful",
    ),
    FeedbackOption(
        option_id="PR_SUPPLEMENT",
        label="我有情况要补充",
        feedback_type=FEEDBACK_TYPE_CALIBRATION,
        value="supplement",
    ),
]

# Teacher detail feedback options
TEACHER_DETAIL_OPTIONS = [
    FeedbackOption(
        option_id="TD_ACCURATE",
        label="判断贴近教学观察",
        feedback_type=FEEDBACK_TYPE_EXPERIENCE,
        value="positive",
    ),
    FeedbackOption(
        option_id="TD_FOLLOWED",
        label="已跟进",
        feedback_type=FEEDBACK_TYPE_OPERATION,
        value="followed_up",
    ),
    FeedbackOption(
        option_id="TD_CONTINUE",
        label="需要继续关注",
        feedback_type=FEEDBACK_TYPE_OPERATION,
        value="continue_observing",
    ),
    FeedbackOption(
        option_id="TD_ERROR",
        label="存在映射错误",
        feedback_type=FEEDBACK_TYPE_CALIBRATION,
        value="mapping_error",
    ),
]

# Dashboard feedback options
DASHBOARD_OPTIONS = [
    FeedbackOption(
        option_id="DB_SMOOTH",
        label="推进顺畅",
        feedback_type=FEEDBACK_TYPE_EXPERIENCE,
        value="positive",
    ),
    FeedbackOption(
        option_id="DB_BLOCKED",
        label="遇到卡点",
        feedback_type=FEEDBACK_TYPE_OPERATION,
        value="blocked",
    ),
    FeedbackOption(
        option_id="DB_SUPPORT",
        label="需要支持",
        feedback_type=FEEDBACK_TYPE_OPERATION,
        value="support_needed",
    ),
    FeedbackOption(
        option_id="DB_ANOMALY",
        label="数据异常",
        feedback_type=FEEDBACK_TYPE_EXCEPTION,
        value="anomaly_reported",
    ),
]
