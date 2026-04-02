#!/usr/bin/env python3
"""Tests for DEV-014: School and Class Dashboard QA-008 Acceptance Support.

This module provides comprehensive acceptance tests for:
- Class dashboard structure and data quality (OBS-009)
- School dashboard aggregation consistency
- Risk distribution validation
- Subject issue assertions
- Compare dimension boundary notes (OBS-007)
- Degraded scenario handling

Follows QA-008 acceptance criteria:
- 聚合优先 (aggregation first)
- 风险分层优先 (risk stratification first)
- 趋势优先 (trend first)
- 可下钻但不失控 (drill-down with boundaries)
"""

from __future__ import annotations

import sys
from pathlib import Path

# Add repository root to Python path
repo_root = Path(__file__).resolve().parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from app.models.school_dashboard import (
    DashboardAssertions,
    DashboardTestBuilder,
    ClassDashboardSummary,
    SchoolDashboardSummary,
    RiskDistribution,
    SubjectIssue,
)


def _run_case(test_func) -> tuple[bool, str]:
    """Adapt pytest-style test functions for CLI summary output."""
    try:
        test_func()
    except AssertionError as exc:
        return False, str(exc) or "assertion failed"
    except Exception as exc:  # pragma: no cover - defensive CLI adapter
        return False, f"{type(exc).__name__}: {exc}"
    return True, "passed"


def test_normal_class_dashboard_validation() -> None:
    """Test normal scenario class dashboard validation."""
    builder = DashboardTestBuilder()
    dashboard = builder.build_normal_class_dashboard()

    assertions = DashboardAssertions()
    is_valid, errors = assertions.validate_class_dashboard(dashboard)

    assert is_valid, f"Normal dashboard should be valid: {errors}"
    assert dashboard.total_students == 45
    assert dashboard.data_coverage_rate == 0.93
    assert dashboard.risk_distribution.high_risk_count == 2
    assert dashboard.risk_distribution.risk_trend == "stable"
    assert len(dashboard.subject_issues) == 1


def test_high_risk_class_dashboard_validation() -> None:
    """Test high-risk scenario class dashboard validation (>20% high risk)."""
    builder = DashboardTestBuilder()
    dashboard = builder.build_high_risk_class_dashboard()

    assertions = DashboardAssertions()
    is_valid, errors = assertions.validate_class_dashboard(dashboard)

    # High risk dashboard should have warnings but still be structurally valid
    assert dashboard.total_students == 40
    assert dashboard.data_coverage_rate == 0.75
    assert dashboard.risk_distribution.high_risk_count == 8  # 20%
    assert dashboard.risk_distribution.risk_trend == "rising"
    assert len(dashboard.subject_issues) == 2

    # Check that high risk warning is generated
    high_risk_ratio = dashboard.risk_distribution.high_risk_count / dashboard.total_students
    assert high_risk_ratio == 0.20
    assert any("高风险学生占比" in err for err in errors), "Should warn about high risk ratio"


def test_degraded_class_dashboard_validation() -> None:
    """Test degraded scenario class dashboard validation (low data coverage)."""
    builder = DashboardTestBuilder()
    dashboard, degraded_messages = builder.build_degraded_class_dashboard()

    assertions = DashboardAssertions()
    is_valid, errors = assertions.validate_class_dashboard(dashboard)

    # Degraded dashboard should have errors due to low coverage
    assert dashboard.data_coverage_rate == 0.22
    assert dashboard.risk_distribution.risk_trend == "unknown"
    assert len(dashboard.subject_issues) == 0  # No subject issues due to low data

    # Check validation errors for low coverage
    assert not is_valid, "Degraded dashboard should have validation errors"
    assert any("覆盖率" in err for err in errors), "Should warn about low coverage"
    assert any("数据覆盖率" in err for err in errors), "Should specify data coverage issue"

    # Check degraded messages
    assert len(degraded_messages) > 0, "Should have degraded rule messages"


def test_school_dashboard_validation() -> None:
    """Test normal scenario school dashboard validation."""
    builder = DashboardTestBuilder()
    dashboard = builder.build_normal_school_dashboard()

    assertions = DashboardAssertions()
    is_valid, errors = assertions.validate_school_dashboard(dashboard)

    assert is_valid, f"School dashboard should be valid: {errors}"
    assert dashboard.total_classes == 12
    assert dashboard.total_students == 540
    assert dashboard.active_rate == 0.85
    assert len(dashboard.grade_summaries) == 3
    assert len(dashboard.major_issues) == 1

    # Verify grade summaries consistency
    total_from_grades = sum(gs.class_count for gs in dashboard.grade_summaries)
    assert total_from_grades == dashboard.total_classes

    total_students_from_grades = sum(gs.student_count for gs in dashboard.grade_summaries)
    assert total_students_from_grades == dashboard.total_students


def test_risk_distribution_assertions() -> None:
    """Test risk distribution validation assertions."""
    assertions = DashboardAssertions()

    # Valid risk distribution
    valid_dist = RiskDistribution(
        low_risk_count=35,
        medium_risk_count=8,
        high_risk_count=2,
        risk_trend="stable",
    )
    is_valid, errors = assertions.validate_risk_distribution(valid_dist, total=45)
    assert is_valid, f"Valid distribution should pass: {errors}"

    # Invalid total
    is_valid, errors = assertions.validate_risk_distribution(valid_dist, total=50)
    assert not is_valid
    assert any("不一致" in err for err in errors)

    # Invalid trend
    invalid_trend = RiskDistribution(
        low_risk_count=35,
        medium_risk_count=8,
        high_risk_count=2,
        risk_trend="unknown",
    )
    is_valid, errors = assertions.validate_risk_distribution(invalid_trend, total=45)
    assert not is_valid
    assert any("风险趋势" in err for err in errors)


def test_subject_issue_assertions() -> None:
    """Test subject issue validation assertions."""
    assertions = DashboardAssertions()

    # Valid subject issue
    valid_issue = SubjectIssue(
        subject="物理",
        issue_type="knowledge_point",
        issue_name="受力分析",
        affected_students=5,
        trend="stable",
        priority="medium",
    )
    is_valid, errors = assertions.validate_subject_issue(valid_issue, max_students=45)
    assert is_valid, f"Valid subject issue should pass: {errors}"

    # Invalid - too many affected students
    is_valid, errors = assertions.validate_subject_issue(valid_issue, max_students=3)
    assert not is_valid
    assert any("影响人数" in err for err in errors)

    # Invalid priority
    invalid_priority = SubjectIssue(
        subject="物理",
        issue_type="knowledge_point",
        issue_name="受力分析",
        affected_students=5,
        trend="stable",
        priority="urgent",
    )
    is_valid, errors = assertions.validate_subject_issue(invalid_priority, max_students=45)
    assert not is_valid
    assert any("优先级" in err for err in errors)


def test_compare_boundary_notes() -> None:
    """Test compare dimension boundary notes (OBS-007 compliance)."""
    assertions = DashboardAssertions()

    # Good data quality
    good_quality = {
        "sample_size": 45,
        "completeness": 0.93,
        "window_consistent": True,
    }
    notes = assertions.get_compare_boundary_notes(good_quality, "class_relative")
    assert len(notes) == 1  # Only class_relative warning
    assert any("家长端不展示" in note for note in notes)

    # Low sample size
    low_sample = {
        "sample_size": 5,
        "completeness": 0.93,
        "window_consistent": True,
    }
    notes = assertions.get_compare_boundary_notes(low_sample, "class_relative")
    assert any("样本量不足" in note for note in notes)

    # Low completeness
    low_completeness = {
        "sample_size": 45,
        "completeness": 0.30,
        "window_consistent": True,
    }
    notes = assertions.get_compare_boundary_notes(low_completeness, "class_relative")
    assert any("数据完整度偏低" in note for note in notes)

    # Inconsistent window
    inconsistent_window = {
        "sample_size": 45,
        "completeness": 0.93,
        "window_consistent": False,
    }
    notes = assertions.get_compare_boundary_notes(inconsistent_window, "class_relative")
    assert any("时间窗口不一致" in note for note in notes)


def test_threshold_constants() -> None:
    """Test assertion threshold constants."""
    assertions = DashboardAssertions()

    assert assertions.MIN_COVERAGE_THRESHOLD == 0.5
    assert assertions.MIN_SAMPLE_SIZE == 10
    assert assertions.HIGH_RISK_ATTENTION_RATIO == 0.1


def test_dashboard_test_builder_scenarios() -> None:
    """Test DashboardTestBuilder scenario generation."""
    builder = DashboardTestBuilder()

    # Test all builders
    normal_class = builder.build_normal_class_dashboard()
    assert normal_class.class_id == "CLS_TEST_001"
    assert normal_class.data_coverage_rate == 0.93

    high_risk_class = builder.build_high_risk_class_dashboard()
    assert high_risk_class.class_id == "CLS_TEST_HIGH_RISK"
    assert high_risk_class.risk_distribution.risk_trend == "rising"

    degraded_class, _ = builder.build_degraded_class_dashboard()
    assert degraded_class.class_id == "CLS_TEST_DEGRADED"
    assert degraded_class.data_coverage_rate == 0.22

    normal_school = builder.build_normal_school_dashboard()
    assert normal_school.school_id == "SCH_TEST"
    assert len(normal_school.grade_summaries) == 3


def main():
    """Run all tests and report results."""
    print("=" * 60)
    print("DEV-014: School and Class Dashboard QA-008 Acceptance Tests")
    print("=" * 60)
    print()

    tests = [
        ("Normal Class Dashboard Validation", test_normal_class_dashboard_validation),
        ("High-Risk Class Dashboard Validation", test_high_risk_class_dashboard_validation),
        ("Degraded Class Dashboard Validation", test_degraded_class_dashboard_validation),
        ("School Dashboard Validation", test_school_dashboard_validation),
        ("Risk Distribution Assertions", test_risk_distribution_assertions),
        ("Subject Issue Assertions", test_subject_issue_assertions),
        ("Compare Boundary Notes (OBS-007)", test_compare_boundary_notes),
        ("Threshold Constants", test_threshold_constants),
        ("DashboardTestBuilder Scenarios", test_dashboard_test_builder_scenarios),
    ]

    results: list[tuple[str, bool, str]] = []

    for test_name, test_func in tests:
        success, message = _run_case(test_func)
        results.append((test_name, success, message))
        status = "PASS" if success else "FAIL"
        print(f"[{status}] {test_name}: {message}")

    print()
    print("=" * 60)
    print("Test Summary")
    print("=" * 60)

    passed = sum(1 for _, success, _ in results if success)
    total = len(results)

    print(f"Passed: {passed}/{total}")

    if passed == total:
        print("\nConclusion: All tests passed. DEV-014 acceptance support is ready for QA-008.")
        return 0
    else:
        print("\nConclusion: Some tests failed. Review errors above.")
        return 1


if __name__ == "__main__":
    exit(main())


# ============== Pytest wrapper ==============

def test_dev014_normal_class_dashboard():
    """DEV-014: Normal class dashboard validation."""
    test_normal_class_dashboard_validation()


def test_dev014_high_risk_class_dashboard():
    """DEV-014: High-risk class dashboard validation."""
    test_high_risk_class_dashboard_validation()


def test_dev014_degraded_class_dashboard():
    """DEV-014: Degraded class dashboard validation."""
    test_degraded_class_dashboard_validation()


def test_dev014_school_dashboard():
    """DEV-014: School dashboard validation."""
    test_school_dashboard_validation()


def test_dev014_risk_distribution_assertions():
    """DEV-014: Risk distribution assertions."""
    test_risk_distribution_assertions()


def test_dev014_subject_issue_assertions():
    """DEV-014: Subject issue assertions."""
    test_subject_issue_assertions()


def test_dev014_compare_boundary_notes():
    """DEV-014: Compare boundary notes (OBS-007)."""
    test_compare_boundary_notes()


def test_dev014_threshold_constants():
    """DEV-014: Threshold constants."""
    test_threshold_constants()


def test_dev014_dashboard_test_builder():
    """DEV-014: DashboardTestBuilder scenarios."""
    test_dashboard_test_builder_scenarios()
