"""School and Class Dashboard models for OBS-009.

This module provides aggregate dashboard views for school and class levels,
following OBS-009 design principles:
- 聚合优先 (aggregation first)
- 风险分层优先 (risk stratification first)
- 趋势优先 (trend first)
- 可下钻但不失控 (drill-down with boundaries)

Note: This module re-exports models from obs_models.py for logical separation
and provides additional validation and assertion helpers for QA-008 acceptance.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


# Re-export from obs_models.py for logical separation
# These are the core dashboard models
from app.models.obs_models import (
    ClassDashboardSummary,
    SchoolDashboardSummary,
    GradeSummary,
    MajorIssue,
    RiskDistribution,
    SubjectIssue,
    FollowUpStatus,
    OBSDisplayBuilder,
)


@dataclass(frozen=True)
class DashboardAssertions:
    """
    Assertion helpers for dashboard QA acceptance (QA-008).

    Provides validation rules and boundary checks for:
    - Class dashboard structure
    - School dashboard structure
    - Risk distribution consistency
    - Data quality thresholds
    - Compare dimension boundary notes
    """

    # Data quality thresholds
    MIN_COVERAGE_THRESHOLD: float = 0.5  # Minimum data coverage for valid conclusions
    MIN_SAMPLE_SIZE: int = 10  # Minimum students for class aggregation
    HIGH_RISK_ATTENTION_RATIO: float = 0.1  # >10% high risk = attention needed

    def validate_class_dashboard(self, dashboard: ClassDashboardSummary) -> tuple[bool, list[str]]:
        """
        Validate class dashboard structure and data quality.

        Returns (is_valid, error_messages).
        """
        errors: list[str] = []

        # Required fields check
        if not dashboard.class_id:
            errors.append("class_id is required")
        if not dashboard.class_name:
            errors.append("class_name is required")
        if not dashboard.school_id:
            errors.append("school_id is required")
        if not dashboard.grade_id:
            errors.append("grade_id is required")

        # Data coverage check
        if dashboard.data_coverage_rate < self.MIN_COVERAGE_THRESHOLD:
            errors.append(f"数据覆盖率 {dashboard.data_coverage_rate:.1%} 低于阈值 {self.MIN_COVERAGE_THRESHOLD:.1%}，结论仅供参考")

        # Sample size check
        if dashboard.total_students < self.MIN_SAMPLE_SIZE:
            errors.append(f"班级人数 {dashboard.total_students} 少于 {self.MIN_SAMPLE_SIZE} 人，聚合结果仅供参考")

        # Risk distribution consistency
        risk_total = (
            dashboard.risk_distribution.low_risk_count +
            dashboard.risk_distribution.medium_risk_count +
            dashboard.risk_distribution.high_risk_count
        )
        if risk_total != dashboard.total_students:
            # Warning, not error - some students may be unassigned
            errors.append(f"风险分布总人数 ({risk_total}) 与总学生数 ({dashboard.total_students}) 不一致")

        # High risk ratio check
        if dashboard.total_students > 0:
            high_risk_ratio = dashboard.risk_distribution.high_risk_count / dashboard.total_students
            if high_risk_ratio > self.HIGH_RISK_ATTENTION_RATIO:
                errors.append(f"高风险学生占比 {high_risk_ratio:.1%} 超过 {self.HIGH_RISK_ATTENTION_RATIO:.1%}，需重点关注")

        # Subject issues consistency
        for issue in dashboard.subject_issues:
            if issue.affected_students > dashboard.total_students:
                errors.append(f"学科问题影响人数 ({issue.affected_students}) 超过班级总人数 ({dashboard.total_students})")

        return (len(errors) == 0, errors)

    def validate_school_dashboard(self, dashboard: SchoolDashboardSummary) -> tuple[bool, list[str]]:
        """
        Validate school dashboard structure and data quality.

        Returns (is_valid, error_messages).
        """
        errors: list[str] = []

        # Required fields check
        if not dashboard.school_id:
            errors.append("school_id is required")
        if not dashboard.school_name:
            errors.append("school_name is required")

        # Grade summaries consistency
        total_classes_from_grades = sum(gs.class_count for gs in dashboard.grade_summaries)
        total_students_from_grades = sum(gs.student_count for gs in dashboard.grade_summaries)

        if total_classes_from_grades != dashboard.total_classes:
            errors.append(f"年级汇总班级数 ({total_classes_from_grades}) 与总班级数 ({dashboard.total_classes}) 不一致")

        if total_students_from_grades != dashboard.total_students:
            errors.append(f"年级汇总学生数 ({total_students_from_grades}) 与总学生数 ({dashboard.total_students}) 不一致")

        # Active rate bounds
        if not (0.0 <= dashboard.active_rate <= 1.0):
            errors.append(f"活跃率 {dashboard.active_rate} 超出 [0, 1] 范围")

        # Follow-up status bounds
        follow_up = dashboard.follow_up_status
        if not (0.0 <= follow_up.focus_student_followed_rate <= 1.0):
            errors.append(f"重点学生跟进率 {follow_up.focus_student_followed_rate} 超出 [0, 1] 范围")
        if not (0.0 <= follow_up.teacher_feedback_rate <= 1.0):
            errors.append(f"教师反馈率 {follow_up.teacher_feedback_rate} 超出 [0, 1] 范围")
        if not (0.0 <= follow_up.parent_feedback_rate <= 1.0):
            errors.append(f"家长反馈率 {follow_up.parent_feedback_rate} 超出 [0, 1] 范围")

        return (len(errors) == 0, errors)

    def validate_risk_distribution(self, dist: RiskDistribution, total: int) -> tuple[bool, list[str]]:
        """Validate risk distribution consistency."""
        errors: list[str] = []

        calculated_total = dist.low_risk_count + dist.medium_risk_count + dist.high_risk_count
        if calculated_total != total:
            errors.append(f"风险分布总人数 ({calculated_total}) 与总人数 ({total}) 不一致")

        if dist.risk_trend not in {"rising", "stable", "falling"}:
            errors.append(f"风险趋势 {dist.risk_trend} 不在允许范围内 (rising/stable/falling)")

        return (len(errors) == 0, errors)

    def validate_subject_issue(self, issue: SubjectIssue, max_students: int) -> tuple[bool, list[str]]:
        """Validate subject issue consistency."""
        errors: list[str] = []

        if issue.affected_students > max_students:
            errors.append(f"影响人数 ({issue.affected_students}) 超过最大可能值 ({max_students})")

        if issue.priority not in {"high", "medium", "low"}:
            errors.append(f"优先级 {issue.priority} 不在允许范围内 (high/medium/low)")

        if issue.trend not in {"rising", "stable", "falling"}:
            errors.append(f"趋势 {issue.trend} 不在允许范围内 (rising/stable/falling)")

        return (len(errors) == 0, errors)

    def get_compare_boundary_notes(
        self,
        data_quality: dict[str, Any],
        compare_type: str,
    ) -> list[str]:
        """
        Get boundary notes for comparison displays (OBS-007).

        Args:
            data_quality: Dict with keys: sample_size, completeness, window_consistency
            compare_type: Type of comparison being made

        Returns:
            List of boundary warning messages
        """
        warnings: list[str] = []

        sample_size = data_quality.get("sample_size", 0)
        completeness = data_quality.get("completeness", 0.0)
        window_consistent = data_quality.get("window_consistent", True)

        if sample_size < self.MIN_SAMPLE_SIZE:
            warnings.append(f"样本量不足 ({sample_size} < {self.MIN_SAMPLE_SIZE})，对比结果仅供参考")

        if completeness < self.MIN_COVERAGE_THRESHOLD:
            warnings.append(f"数据完整度偏低 ({completeness:.1%} < {self.MIN_COVERAGE_THRESHOLD:.1%})")

        if not window_consistent:
            warnings.append("时间窗口不一致，对比可能无效")

        # Role-specific warnings
        if compare_type == "class_relative":
            warnings.append("班级相对对比仅适用于老师端和学校端，家长端不展示")

        return warnings


# Acceptance test data builders (for QA-008)

@dataclass
class DashboardTestBuilder:
    """
    Builder for creating test dashboard instances with realistic data.

    Used in QA-008 acceptance tests to generate:
    - Normal scenario dashboards
    - Degraded scenario dashboards
    - Edge case dashboards
    """

    school_id: str = "SCH_TEST"
    school_name: str = "测试学校"
    grade_id: str = "G1"
    grade_name: str = "高一"

    def build_normal_class_dashboard(self) -> ClassDashboardSummary:
        """Build a normal scenario class dashboard."""
        builder = OBSDisplayBuilder()

        aggregate_data = {
            "total_students": 45,
            "active_students": 42,
            "data_coverage_rate": 0.93,
            "risk_distribution": {
                "low_risk_count": 35,
                "medium_risk_count": 8,
                "high_risk_count": 2,
                "risk_trend": "stable",
            },
            "subject_issues": [
                {
                    "subject": "物理",
                    "issue_type": "knowledge_point",
                    "issue_name": "受力分析",
                    "affected_students": 5,
                    "trend": "stable",
                    "priority": "medium",
                },
            ],
            "follow_up_rate": 0.80,
            "feedback_rate": 0.75,
            "trend_direction": "improving",
        }

        return builder.build_class_dashboard_summary(
            class_id="CLS_TEST_001",
            class_name="高一 (1) 班",
            school_id=self.school_id,
            grade_id=self.grade_id,
            aggregate_data=aggregate_data,
        )

    def build_high_risk_class_dashboard(self) -> ClassDashboardSummary:
        """Build a high-risk scenario class dashboard (>20% high risk)."""
        builder = OBSDisplayBuilder()

        aggregate_data = {
            "total_students": 40,
            "active_students": 30,
            "data_coverage_rate": 0.75,
            "risk_distribution": {
                "low_risk_count": 20,
                "medium_risk_count": 12,
                "high_risk_count": 8,  # 20% high risk
                "risk_trend": "rising",
            },
            "subject_issues": [
                {
                    "subject": "物理",
                    "issue_type": "knowledge_point",
                    "issue_name": "受力分析集中错误",
                    "affected_students": 15,
                    "trend": "rising",
                    "priority": "high",
                },
                {
                    "subject": "数学",
                    "issue_type": "question_type",
                    "issue_name": "图像题型大面积错误",
                    "affected_students": 12,
                    "trend": "rising",
                    "priority": "high",
                },
            ],
            "follow_up_rate": 0.40,
            "feedback_rate": 0.35,
            "trend_direction": "declining",
        }

        return builder.build_class_dashboard_summary(
            class_id="CLS_TEST_HIGH_RISK",
            class_name="高一 (3) 班",
            school_id=self.school_id,
            grade_id=self.grade_id,
            aggregate_data=aggregate_data,
        )

    def build_degraded_class_dashboard(self) -> tuple[ClassDashboardSummary, list[str]]:
        """Build a degraded scenario class dashboard (low data coverage)."""
        builder = OBSDisplayBuilder()

        aggregate_data = {
            "total_students": 45,
            "active_students": 10,
            "data_coverage_rate": 0.22,  # Low coverage
            "risk_distribution": {
                "low_risk_count": 8,
                "medium_risk_count": 2,
                "high_risk_count": 0,
                "risk_trend": "unknown",
            },
            "subject_issues": [],  # No subject issues due to low data
            "follow_up_rate": 0.0,
            "feedback_rate": 0.0,
            "trend_direction": "unknown",
        }

        dashboard = builder.build_class_dashboard_summary(
            class_id="CLS_TEST_DEGRADED",
            class_name="高一 (5) 班",
            school_id=self.school_id,
            grade_id=self.grade_id,
            aggregate_data=aggregate_data,
        )

        # Apply degraded rules
        data_available = {
            "knowledge": False,
            "ability": False,
            "confidence": False,
            "class_data": False,
            "coverage": False,
        }
        dashboard, messages = builder.apply_degraded_rules_to_dashboard(dashboard, data_available)

        return (dashboard, messages)

    def build_normal_school_dashboard(self) -> SchoolDashboardSummary:
        """Build a normal scenario school dashboard."""
        builder = OBSDisplayBuilder()

        aggregate_data = {
            "total_classes": 12,
            "total_students": 540,
            "active_rate": 0.85,
            "grade_summaries": [
                {
                    "grade_id": "G1",
                    "grade_name": "高一",
                    "class_count": 4,
                    "student_count": 180,
                    "risk_distribution": {
                        "low_risk_count": 140,
                        "medium_risk_count": 35,
                        "high_risk_count": 5,
                        "risk_trend": "stable",
                    },
                },
                {
                    "grade_id": "G2",
                    "grade_name": "高二",
                    "class_count": 4,
                    "student_count": 180,
                    "risk_distribution": {
                        "low_risk_count": 130,
                        "medium_risk_count": 40,
                        "high_risk_count": 10,
                        "risk_trend": "stable",
                    },
                },
                {
                    "grade_id": "G3",
                    "grade_name": "高三",
                    "class_count": 4,
                    "student_count": 180,
                    "risk_distribution": {
                        "low_risk_count": 120,
                        "medium_risk_count": 45,
                        "high_risk_count": 15,
                        "risk_trend": "rising",
                    },
                },
            ],
            "major_issues": [
                {
                    "issue_category": "subject",
                    "issue_summary": "物理受力分析在多班级集中出现",
                    "affected_grades": 2,
                    "affected_classes": 6,
                    "priority": "high",
                },
            ],
            "follow_up_status": {
                "focus_student_followed_rate": 0.75,
                "teacher_feedback_rate": 0.80,
                "parent_feedback_rate": 0.60,
            },
        }

        return builder.build_school_dashboard_summary(
            school_id=self.school_id,
            school_name=self.school_name,
            aggregate_data=aggregate_data,
        )


# Module exports for QA-008 tests
__all__ = [
    # Re-exported models
    "ClassDashboardSummary",
    "SchoolDashboardSummary",
    "GradeSummary",
    "MajorIssue",
    "RiskDistribution",
    "SubjectIssue",
    "FollowUpStatus",
    "OBSDisplayBuilder",
    # QA assertion helpers
    "DashboardAssertions",
    # Test data builders
    "DashboardTestBuilder",
]
