from __future__ import annotations

from app.models.feedback_event import (
    FEEDBACK_ROLE_PARENT,
    FEEDBACK_ROLE_TEACHER,
    FEEDBACK_STATUS_CLOSED,
    FEEDBACK_STATUS_RESOLVED,
    FEEDBACK_TARGET_PARENT_REPORT,
    FEEDBACK_TARGET_TEACHER_DETAIL,
    FEEDBACK_TYPE_CALIBRATION,
    FEEDBACK_TYPE_EXPERIENCE,
    FEEDBACK_TYPE_OPERATION,
    PROBLEM_SEVERITY_P1,
    PROBLEM_SEVERITY_P2,
    PROBLEM_STATUS_CLOSED,
    PROBLEM_STATUS_PENDING_ANALYSIS,
    PilotProblem,
    FeedbackEvent,
    FeedbackTraceabilityBuilder,
)


def test_pilot_problem_lifecycle_and_validation():
    problem = PilotProblem(
        problem_id="PROB_20260402_001",
        source="teacher",
        problem_type="data",
        title="学生详情映射错误",
        description="学生详情页展示了错误班级归属",
        scope="class",
        severity=PROBLEM_SEVERITY_P1,
        status=PROBLEM_STATUS_PENDING_ANALYSIS,
        owner="ops",
        created_at="2026-04-02T10:00:00",
        related_feedback_ids=["FB_001"],
    )

    is_valid, errors = problem.validate()
    assert is_valid, errors

    problem.mark_in_progress(owner="eng")
    assert problem.status == "in_progress"
    assert problem.owner == "eng"

    problem.mark_pending_verification()
    assert problem.status == "pending_verification"

    problem.close(
        resolution_notes="已修正班级映射并回归验证",
        solution="修正 teacher detail 归属映射规则",
        root_cause="班级关系缓存键错误",
    )
    assert problem.status == PROBLEM_STATUS_CLOSED
    assert problem.closed_at is not None
    assert problem.solution == "修正 teacher detail 归属映射规则"


def test_traceability_snapshot_computes_rates():
    feedback_events = [
        FeedbackEvent.create_from_text(
            source_role=FEEDBACK_ROLE_PARENT,
            source_user_id="USR_PARENT_001",
            tenant_id="SCH_001",
            target_type=FEEDBACK_TARGET_PARENT_REPORT,
            target_ref="RPT_001",
            feedback_type=FEEDBACK_TYPE_EXPERIENCE,
            feedback_text="报告有帮助",
        ),
        FeedbackEvent.create_from_text(
            source_role=FEEDBACK_ROLE_PARENT,
            source_user_id="USR_PARENT_002",
            tenant_id="SCH_001",
            target_type=FEEDBACK_TARGET_PARENT_REPORT,
            target_ref="RPT_002",
            feedback_type=FEEDBACK_TYPE_CALIBRATION,
            feedback_text="状态判断不准",
        ),
        FeedbackEvent.create_from_text(
            source_role=FEEDBACK_ROLE_TEACHER,
            source_user_id="USR_TEACHER_001",
            tenant_id="SCH_001",
            target_type=FEEDBACK_TARGET_TEACHER_DETAIL,
            target_ref="TSD_001",
            feedback_type=FEEDBACK_TYPE_OPERATION,
            feedback_text="已完成课堂跟进",
        ),
    ]

    feedback_events[0].status = FEEDBACK_STATUS_RESOLVED
    feedback_events[1].status = FEEDBACK_STATUS_CLOSED
    feedback_events[2].status = FEEDBACK_STATUS_RESOLVED

    problems = [
        PilotProblem(
            problem_id="PROB_001",
            source="parent",
            problem_type="ux",
            title="报告术语过多",
            description="家长看不懂部分术语",
            scope="system",
            severity=PROBLEM_SEVERITY_P2,
            status=PROBLEM_STATUS_CLOSED,
            owner="product",
            created_at="2026-04-02T10:00:00",
            closed_at="2026-04-02T12:00:00",
        ),
        PilotProblem(
            problem_id="PROB_002",
            source="teacher",
            problem_type="data",
            title="学生详情映射错误",
            description="班级归属显示错误",
            scope="class",
            severity=PROBLEM_SEVERITY_P1,
            status=PROBLEM_STATUS_PENDING_ANALYSIS,
            owner="ops",
            created_at="2026-04-02T10:30:00",
        ),
    ]

    snapshot = FeedbackTraceabilityBuilder().build_snapshot(
        feedback_events,
        problems,
        active_parent_users=5,
        active_teacher_users=2,
        executed_interventions=2,
    )

    assert snapshot.total_feedback == 3
    assert snapshot.parent_feedback_count == 2
    assert snapshot.teacher_feedback_count == 1
    assert snapshot.parent_feedback_submit_rate == 0.4
    assert snapshot.teacher_feedback_submit_rate == 0.5
    assert snapshot.resolved_feedback_rate == 1.0
    assert snapshot.closed_problem_rate == 0.5
    assert snapshot.intervention_fill_rate == 0.5
    assert snapshot.problem_by_type["data"] == 1
    assert snapshot.feedback_by_type[FEEDBACK_TYPE_OPERATION] == 1


def test_traceability_snapshot_handles_zero_denominator():
    snapshot = FeedbackTraceabilityBuilder().build_snapshot(
        feedback_events=[],
        pilot_problems=[],
        active_parent_users=0,
        active_teacher_users=0,
        executed_interventions=0,
    )

    assert snapshot.parent_feedback_submit_rate == 0.0
    assert snapshot.teacher_feedback_submit_rate == 0.0
    assert snapshot.resolved_feedback_rate == 0.0
    assert snapshot.closed_problem_rate == 0.0
    assert snapshot.intervention_fill_rate == 0.0


def test_review_summary_highlights_problem_mix():
    feedback_events = [
        FeedbackEvent.create_from_text(
            source_role=FEEDBACK_ROLE_PARENT,
            source_user_id="USR_PARENT_001",
            tenant_id="SCH_001",
            target_type=FEEDBACK_TARGET_PARENT_REPORT,
            target_ref="RPT_001",
            feedback_type=FEEDBACK_TYPE_EXPERIENCE,
            feedback_text="报告有帮助",
        )
    ]

    problems = [
        PilotProblem(
            problem_id="PROB_001",
            source="parent",
            problem_type="ux",
            title="报告术语过多",
            description="家长看不懂部分术语",
            scope="system",
            severity=PROBLEM_SEVERITY_P2,
            status=PROBLEM_STATUS_PENDING_ANALYSIS,
            owner="product",
            created_at="2026-04-02T10:00:00",
        ),
        PilotProblem(
            problem_id="PROB_002",
            source="teacher",
            problem_type="ux",
            title="老师端操作复杂",
            description="页面操作链过长",
            scope="system",
            severity=PROBLEM_SEVERITY_P2,
            status=PROBLEM_STATUS_PENDING_ANALYSIS,
            owner="product",
            created_at="2026-04-02T11:00:00",
        ),
        PilotProblem(
            problem_id="PROB_003",
            source="teacher",
            problem_type="data",
            title="学生详情映射错误",
            description="班级归属显示错误",
            scope="class",
            severity=PROBLEM_SEVERITY_P1,
            status=PROBLEM_STATUS_PENDING_ANALYSIS,
            owner="ops",
            created_at="2026-04-02T12:00:00",
        ),
    ]

    summary = FeedbackTraceabilityBuilder().build_review_summary(feedback_events, problems)

    assert summary["feedback_total"] == 1
    assert summary["problem_total"] == 3
    assert summary["problem_status_counts"][PROBLEM_STATUS_PENDING_ANALYSIS] == 3
    assert summary["top_problem_types"][0] == ("ux", 2)
