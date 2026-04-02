#!/usr/bin/env python3
"""Tests for DEV-012: Feedback loop event recording and routing."""

from __future__ import annotations

import sys
from pathlib import Path

# Add repository root to Python path
repo_root = Path(__file__).resolve().parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from app.models.feedback_event import (
    FeedbackEvent,
    FeedbackOption,
    FeedbackRouter,
    FEEDBACK_TYPE_CALIBRATION,
    FEEDBACK_TYPE_EXPERIENCE,
    FEEDBACK_TYPE_OPERATION,
    FEEDBACK_TYPE_EXCEPTION,
    FEEDBACK_STATUS_PENDING,
    FEEDBACK_STATUS_ROUTED,
    FEEDBACK_STATUS_IN_PROGRESS,
    FEEDBACK_STATUS_RESOLVED,
    FEEDBACK_ROLE_PARENT,
    FEEDBACK_ROLE_TEACHER,
    FEEDBACK_ROLE_SCHOOL,
    FEEDBACK_TARGET_PARENT_REPORT,
    FEEDBACK_TARGET_TEACHER_DETAIL,
    FEEDBACK_TARGET_SCHOOL_DASHBOARD,
    ROUTE_REVIEW_QUEUE,
    ROUTE_PRODUCT_POOL,
    ROUTE_OPERATION_POOL,
    ROUTE_TECH_POOL,
    PARENT_REPORT_OPTIONS,
    TEACHER_DETAIL_OPTIONS,
    DASHBOARD_OPTIONS,
)


def run_feedback_event_creation_from_option() -> tuple[bool, str]:
    """Test creating feedback event from predefined option."""
    try:
        option = FeedbackOption(
            option_id="PR_ACCURATE",
            label="报告内容贴近实际",
            feedback_type=FEEDBACK_TYPE_EXPERIENCE,
            value="positive",
        )

        event = FeedbackEvent.create_from_option(
            source_role=FEEDBACK_ROLE_PARENT,
            source_user_id="USR_PARENT_001",
            tenant_id="SCH_001",
            target_type=FEEDBACK_TARGET_PARENT_REPORT,
            target_ref="WKR_2026-03-24_STU_001",
            feedback_option=option,
            page_url="/parent/report/2026-W13",
        )

        assert event.source_role == FEEDBACK_ROLE_PARENT
        assert event.target_type == FEEDBACK_TARGET_PARENT_REPORT
        assert event.feedback_type == FEEDBACK_TYPE_EXPERIENCE
        assert event.feedback_option_id == "PR_ACCURATE"
        assert event.status == FEEDBACK_STATUS_PENDING
        assert event.page_url == "/parent/report/2026-W13"

        return True, f"Feedback event created from option: {event.feedback_id}"
    except Exception as e:
        return False, f"Feedback event creation error: {e}"


def run_feedback_event_creation_from_text() -> tuple[bool, str]:
    """Test creating feedback event from free text."""
    try:
        event = FeedbackEvent.create_from_text(
            source_role=FEEDBACK_ROLE_TEACHER,
            source_user_id="USR_TEACHER_001",
            tenant_id="SCH_001",
            target_type=FEEDBACK_TARGET_TEACHER_DETAIL,
            target_ref="TSD_STU_001_20260326",
            feedback_type=FEEDBACK_TYPE_CALIBRATION,
            feedback_text="当前重点知识点判断不准确，该学生实际掌握良好",
            tags=["calibration", "knowledge_state"],
        )

        assert event.source_role == FEEDBACK_ROLE_TEACHER
        assert event.feedback_type == FEEDBACK_TYPE_CALIBRATION
        assert "判断不准确" in event.feedback_text
        assert len(event.tags) == 2

        return True, f"Feedback event created from text: {event.feedback_id}"
    except Exception as e:
        return False, f"Feedback event text creation error: {e}"


def run_feedback_routing() -> tuple[bool, str]:
    """Test feedback routing based on type."""
    try:
        # Test calibration -> review_queue
        calibration = FeedbackEvent.create_from_text(
            source_role=FEEDBACK_ROLE_PARENT,
            source_user_id="USR_001",
            tenant_id="SCH_001",
            target_type=FEEDBACK_TARGET_PARENT_REPORT,
            target_ref="RPT_001",
            feedback_type=FEEDBACK_TYPE_CALIBRATION,
            feedback_text="内容不准确",
        )
        route = calibration.route()
        assert route == ROUTE_REVIEW_QUEUE
        assert calibration.status == FEEDBACK_STATUS_ROUTED

        # Test experience -> product_pool
        experience = FeedbackEvent.create_from_text(
            source_role=FEEDBACK_ROLE_PARENT,
            source_user_id="USR_001",
            tenant_id="SCH_001",
            target_type=FEEDBACK_TARGET_PARENT_REPORT,
            target_ref="RPT_001",
            feedback_type=FEEDBACK_TYPE_EXPERIENCE,
            feedback_text="很有帮助",
        )
        route = experience.route()
        assert route == ROUTE_PRODUCT_POOL

        # Test operation -> operation_pool
        operation = FeedbackEvent.create_from_text(
            source_role=FEEDBACK_ROLE_TEACHER,
            source_user_id="USR_001",
            tenant_id="SCH_001",
            target_type=FEEDBACK_TARGET_TEACHER_DETAIL,
            target_ref="TSD_001",
            feedback_type=FEEDBACK_TYPE_OPERATION,
            feedback_text="已跟进",
        )
        route = operation.route()
        assert route == ROUTE_OPERATION_POOL

        # Test exception -> tech_pool
        exception = FeedbackEvent.create_from_text(
            source_role=FEEDBACK_ROLE_SCHOOL,
            source_user_id="USR_001",
            tenant_id="SCH_001",
            target_type=FEEDBACK_TARGET_SCHOOL_DASHBOARD,
            target_ref="SCH_DASH_001",
            feedback_type=FEEDBACK_TYPE_EXCEPTION,
            feedback_text="数据显示异常",
        )
        route = exception.route()
        assert route == ROUTE_TECH_POOL

        return True, "Feedback routing validated for all 4 types"
    except Exception as e:
        return False, f"Feedback routing error: {e}"


def run_feedback_lifecycle() -> tuple[bool, str]:
    """Test feedback status lifecycle."""
    try:
        event = FeedbackEvent.create_from_text(
            source_role=FEEDBACK_ROLE_PARENT,
            source_user_id="USR_001",
            tenant_id="SCH_001",
            target_type=FEEDBACK_TARGET_PARENT_REPORT,
            target_ref="RPT_001",
            feedback_type=FEEDBACK_TYPE_CALIBRATION,
            feedback_text="测试反馈",
        )

        # Initial state
        assert event.status == FEEDBACK_STATUS_PENDING

        # Route
        event.route()
        assert event.status == FEEDBACK_STATUS_ROUTED
        assert event.routed_to is not None

        # Mark in progress
        event.mark_in_progress(assigned_to="USR_REVIEWER_001")
        assert event.status == FEEDBACK_STATUS_IN_PROGRESS
        assert event.assigned_to == "USR_REVIEWER_001"

        # Mark resolved
        event.mark_resolved(resolution_notes="已确认并修正状态")
        assert event.status == FEEDBACK_STATUS_RESOLVED
        assert event.resolved_at is not None
        assert event.resolution_notes == "已确认并修正状态"

        return True, "Feedback lifecycle validated: pending -> routed -> in_progress -> resolved"
    except Exception as e:
        return False, f"Feedback lifecycle error: {e}"


def run_feedback_validation() -> tuple[bool, str]:
    """Test feedback event validation."""
    try:
        # Valid event
        valid_event = FeedbackEvent.create_from_text(
            source_role=FEEDBACK_ROLE_PARENT,
            source_user_id="USR_001",
            tenant_id="SCH_001",
            target_type=FEEDBACK_TARGET_PARENT_REPORT,
            target_ref="RPT_001",
            feedback_type=FEEDBACK_TYPE_CALIBRATION,
            feedback_text="测试",
        )
        is_valid, errors = valid_event.validate()
        assert is_valid, f"Valid event should pass validation: {errors}"

        # Invalid event - invalid role
        invalid_event = FeedbackEvent(
            feedback_id="FB_TEST",
            source_role="invalid_role",
            source_user_id="USR_001",
            tenant_id="SCH_001",
            target_type=FEEDBACK_TARGET_PARENT_REPORT,
            target_ref="RPT_001",
            feedback_type=FEEDBACK_TYPE_CALIBRATION,
            created_at="2026-03-26T10:00:00",
            feedback_text="测试",
        )
        is_valid, errors = invalid_event.validate()
        assert not is_valid
        assert any("source_role" in err for err in errors)

        # Invalid rating
        invalid_rating_event = FeedbackEvent.create_from_text(
            source_role=FEEDBACK_ROLE_PARENT,
            source_user_id="USR_001",
            tenant_id="SCH_001",
            target_type=FEEDBACK_TARGET_PARENT_REPORT,
            target_ref="RPT_001",
            feedback_type=FEEDBACK_TYPE_EXPERIENCE,
            feedback_text="测试",
        )
        invalid_rating_event.rating = 10  # Invalid rating
        is_valid, errors = invalid_rating_event.validate()
        assert not is_valid
        assert any("rating" in err for err in errors)

        return True, "Feedback validation rules verified"
    except Exception as e:
        return False, f"Feedback validation error: {e}"


def run_predefined_options() -> tuple[bool, str]:
    """Test predefined feedback options."""
    try:
        # Parent report options
        assert len(PARENT_REPORT_OPTIONS) >= 2
        parent_option_ids = {o.option_id for o in PARENT_REPORT_OPTIONS}
        assert "PR_ACCURATE" in parent_option_ids
        assert "PR_INACCURATE" in parent_option_ids

        # Teacher detail options
        assert len(TEACHER_DETAIL_OPTIONS) >= 2
        teacher_option_ids = {o.option_id for o in TEACHER_DETAIL_OPTIONS}
        assert "TD_ACCURATE" in teacher_option_ids
        assert "TD_FOLLOWED" in teacher_option_ids

        # Dashboard options
        assert len(DASHBOARD_OPTIONS) >= 2
        dashboard_option_ids = {o.option_id for o in DASHBOARD_OPTIONS}
        assert "DB_SMOOTH" in dashboard_option_ids
        assert "DB_ANOMALY" in dashboard_option_ids

        return True, f"Predefined options validated: {len(PARENT_REPORT_OPTIONS)} parent, {len(TEACHER_DETAIL_OPTIONS)} teacher, {len(DASHBOARD_OPTIONS)} dashboard"
    except Exception as e:
        return False, f"Predefined options error: {e}"


def run_feedback_router() -> tuple[bool, str]:
    """Test FeedbackRouter class."""
    try:
        router = FeedbackRouter()

        # Test routing
        event = FeedbackEvent.create_from_text(
            source_role=FEEDBACK_ROLE_PARENT,
            source_user_id="USR_001",
            tenant_id="SCH_001",
            target_type=FEEDBACK_TARGET_PARENT_REPORT,
            target_ref="RPT_001",
            feedback_type=FEEDBACK_TYPE_CALIBRATION,
            feedback_text="测试",
        )

        destination = router.route_feedback(event)
        assert destination == ROUTE_REVIEW_QUEUE
        assert event.routed_to == ROUTE_REVIEW_QUEUE

        # Test pool name lookup
        assert router.get_pool_name(ROUTE_REVIEW_QUEUE) == "状态校准池"
        assert router.get_pool_name(ROUTE_PRODUCT_POOL) == "产品优化池"
        assert router.get_pool_name(ROUTE_OPERATION_POOL) == "运营动作池"
        assert router.get_pool_name(ROUTE_TECH_POOL) == "技术问题池"

        return True, "FeedbackRouter validated"
    except Exception as e:
        return False, f"FeedbackRouter error: {e}"


def run_feedback_to_dict() -> tuple[bool, str]:
    """Test feedback event serialization."""
    try:
        event = FeedbackEvent.create_from_text(
            source_role=FEEDBACK_ROLE_TEACHER,
            source_user_id="USR_TEACHER_001",
            tenant_id="SCH_001",
            target_type=FEEDBACK_TARGET_TEACHER_DETAIL,
            target_ref="TSD_001",
            feedback_type=FEEDBACK_TYPE_OPERATION,
            feedback_text="已跟进",
            tags=["follow_up"],
        )
        event.route()

        event_dict = event.to_dict()

        assert event_dict["feedback_id"] == event.feedback_id
        assert event_dict["source_role"] == FEEDBACK_ROLE_TEACHER
        assert event_dict["target_type"] == FEEDBACK_TARGET_TEACHER_DETAIL
        assert event_dict["feedback_type"] == FEEDBACK_TYPE_OPERATION
        assert event_dict["feedback_text"] == "已跟进"
        assert event_dict["tags"] == ["follow_up"]
        assert event_dict["routed_to"] == ROUTE_OPERATION_POOL
        assert event_dict["status"] == FEEDBACK_STATUS_ROUTED

        return True, "Feedback to_dict serialization validated"
    except Exception as e:
        return False, f"Feedback to_dict error: {e}"


def main():
    """Run all tests and report results."""
    print("=" * 50)
    print("DEV-012: Feedback Loop Event Tests")
    print("=" * 50)
    print()

    tests = [
        ("Feedback Event Creation (Option)", run_feedback_event_creation_from_option),
        ("Feedback Event Creation (Text)", run_feedback_event_creation_from_text),
        ("Feedback Routing", run_feedback_routing),
        ("Feedback Lifecycle", run_feedback_lifecycle),
        ("Feedback Validation", run_feedback_validation),
        ("Predefined Options", run_predefined_options),
        ("Feedback Router", run_feedback_router),
        ("Feedback Serialization", run_feedback_to_dict),
    ]

    results: list[tuple[str, bool, str]] = []

    for test_name, test_func in tests:
        success, message = test_func()
        results.append((test_name, success, message))
        status = "PASS" if success else "FAIL"
        print(f"[{status}] {test_name}: {message}")

    print()
    print("=" * 50)
    print("Test Summary")
    print("=" * 50)

    passed = sum(1 for _, success, _ in results if success)
    total = len(results)

    print(f"Passed: {passed}/{total}")

    if passed == total:
        print("\nConclusion: All tests passed. Feedback loop MVP is functional.")
        return 0
    else:
        print("\nConclusion: Some tests failed. Review errors above.")
        return 1


if __name__ == "__main__":
    exit(main())


# ============== Pytest wrapper ==============

def test_feedback_event_creation_from_option():
    """Test creating feedback event from predefined option."""
    success, message = run_feedback_event_creation_from_option()
    assert success, message


def test_feedback_event_creation_from_text():
    """Test creating feedback event from free text."""
    success, message = run_feedback_event_creation_from_text()
    assert success, message


def test_feedback_routing():
    """Test feedback routing based on type."""
    success, message = run_feedback_routing()
    assert success, message


def test_feedback_lifecycle():
    """Test feedback status lifecycle."""
    success, message = run_feedback_lifecycle()
    assert success, message


def test_feedback_validation():
    """Test feedback event validation."""
    success, message = run_feedback_validation()
    assert success, message


def test_predefined_options():
    """Test predefined feedback options."""
    success, message = run_predefined_options()
    assert success, message


def test_feedback_router():
    """Test FeedbackRouter class."""
    success, message = run_feedback_router()
    assert success, message


def test_feedback_to_dict():
    """Test feedback event serialization."""
    success, message = run_feedback_to_dict()
    assert success, message

def test_dev012_feedback_event_from_option():
    """DEV-012: Feedback event creation from predefined option."""
    success, message = run_feedback_event_creation_from_option()
    assert success, message


def test_dev012_feedback_event_from_text():
    """DEV-012: Feedback event creation from free text."""
    success, message = run_feedback_event_creation_from_text()
    assert success, message


def test_dev012_feedback_routing():
    """DEV-012: Feedback routing by type."""
    success, message = run_feedback_routing()
    assert success, message


def test_dev012_feedback_lifecycle():
    """DEV-012: Feedback status lifecycle."""
    success, message = run_feedback_lifecycle()
    assert success, message


def test_dev012_feedback_validation():
    """DEV-012: Feedback event validation."""
    success, message = run_feedback_validation()
    assert success, message


def test_dev012_predefined_options():
    """DEV-012: Predefined feedback options."""
    success, message = run_predefined_options()
    assert success, message


def test_dev012_feedback_router():
    """DEV-012: FeedbackRouter class."""
    success, message = run_feedback_router()
    assert success, message


def test_dev012_feedback_serialization():
    """DEV-012: Feedback event serialization."""
    success, message = run_feedback_to_dict()
    assert success, message
