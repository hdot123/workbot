#!/usr/bin/env python3
"""Tests for comparison dimensions and result models (DEV-013).

Tests cover:
1. CompareDimension structure and validation
2. ComparisonResult structure and serialization
3. ComparisonRule direction/strength/confidence computation
4. Standard dimension templates
5. Factory function create_comparison_result
6. Role-based visibility rules
7. Boundary warning conditions
"""

from __future__ import annotations

import sys
from pathlib import Path

# Add repository root to Python path
repo_root = Path(__file__).resolve().parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from app.models.compare_dimension import (
    CompareDimension,
    ComparisonResult,
    ComparisonWindow,
    ComparisonRule,
    CompareType,
    CompareDirection,
    CompareStrength,
    CompareRole,
    TimeWindow,
    STANDARD_DIMENSIONS,
    get_standard_dimension,
    create_comparison_result,
)


def test_comparison_window_structure() -> tuple[bool, str]:
    """Test ComparisonWindow basic structure."""
    try:
        # Minimal window
        window_minimal = ComparisonWindow(window_type="last_7d")
        assert window_minimal.window_type == "last_7d"
        assert window_minimal.sample_size is None

        # Full window
        window_full = ComparisonWindow(
            window_type="this_week",
            start_time="2026-03-24T00:00:00",
            end_time="2026-03-30T23:59:59",
            sample_size=10,
            data_completeness=0.85,
        )
        assert window_full.start_time == "2026-03-24T00:00:00"
        assert window_full.sample_size == 10
        assert window_full.data_completeness == 0.85

        # Test to_dict
        window_dict = window_full.to_dict()
        assert window_dict["window_type"] == "this_week"
        assert window_dict["sample_size"] == 10

        # Test create_standard
        window_standard = ComparisonWindow.create_standard("last_week")
        assert window_standard.window_type == "last_week"
        assert window_standard.start_time is None

        return True, "ComparisonWindow structure validated"
    except Exception as e:
        return False, f"ComparisonWindow error: {e}"


def test_compare_dimension_structure() -> tuple[bool, str]:
    """Test CompareDimension basic structure."""
    try:
        # Minimal dimension
        dim_minimal = CompareDimension(
            dimension_id="CDM_TEST_001",
            compare_type="time_comparison",
            name="测试对比",
            description="测试用途",
        )
        assert dim_minimal.dimension_id == "CDM_TEST_001"
        assert dim_minimal.scope == "student"
        assert len(dim_minimal.visible_roles) == 3  # parent, teacher, school

        # Full dimension with restrictions
        dim_full = CompareDimension(
            dimension_id="CDM_TEST_002",
            compare_type="class_relative",
            name="班级相对位置",
            description="学生在班级中的排名变化",
            scope="class",
            visible_roles=["teacher", "school"],  # NOT parent
            min_sample_size=10,
            boundary_notes="班级人数较少时仅供参考",
        )
        assert dim_full.scope == "class"
        assert "parent" not in dim_full.visible_roles
        assert dim_full.min_sample_size == 10

        # Test is_visible_to
        assert dim_full.is_visible_to("teacher") is True
        assert dim_full.is_visible_to("parent") is False

        # Test to_dict
        dim_dict = dim_full.to_dict()
        assert dim_dict["dimension_id"] == "CDM_TEST_002"
        assert dim_dict["visible_roles"] == ["teacher", "school"]

        return True, "CompareDimension structure validated"
    except Exception as e:
        return False, f"CompareDimension error: {e}"


def test_comparison_result_structure() -> tuple[bool, str]:
    """Test ComparisonResult structure and serialization."""
    try:
        base_window = ComparisonWindow(window_type="this_week")
        target_window = ComparisonWindow(window_type="last_week")

        result = ComparisonResult(
            result_id="CMP_TEST_001",
            dimension_id="CDM_TIME_WEEKLY",
            compare_type="time_comparison",
            base_window=base_window,
            target_window=target_window,
            direction="improving",
            strength="moderate",
            confidence=0.85,
            base_value=0.75,
            target_value=0.65,
            delta=0.10,
            delta_percent=0.154,
            summary="本周表现较上周有所提升",
            scope="student",
        )

        assert result.result_id == "CMP_TEST_001"
        assert result.direction == "improving"
        assert result.confidence == 0.85

        # Test to_dict
        result_dict = result.to_dict()
        assert result_dict["result_id"] == "CMP_TEST_001"
        assert result_dict["base_window"]["window_type"] == "this_week"
        assert result_dict["delta"] == 0.10

        # Test should_show_to
        assert result.should_show_to("parent") is True
        result.visible_roles = ["teacher", "school"]
        assert result.should_show_to("parent") is False
        assert result.should_show_to("teacher") is True

        return True, "ComparisonResult structure validated"
    except Exception as e:
        return False, f"ComparisonResult error: {e}"


def test_comparison_rule_computation() -> tuple[bool, str]:
    """Test ComparisonRule direction/strength/confidence computation."""
    try:
        rule = ComparisonRule(
            rule_id="RULE_TEST_001",
            dimension_id="CDM_TIME_WEEKLY",
            compare_type="time_comparison",
            improving_threshold=0.1,
            declining_threshold=-0.1,
            strong_delta=0.2,
        )

        # Test direction computation
        assert rule.compute_direction(0.15) == "improving"
        assert rule.compute_direction(-0.15) == "declining"
        assert rule.compute_direction(0.05) == "stable"
        assert rule.compute_direction(-0.05) == "stable"

        # Test strength computation
        assert rule.compute_strength(0.25) == "strong"
        assert rule.compute_strength(-0.25) == "strong"
        assert rule.compute_strength(0.15) == "moderate"
        assert rule.compute_strength(0.05) == "weak"

        # Test confidence computation
        # High quality: good sample size and completeness
        confidence_high = rule.compute_confidence(sample_size=10, data_completeness=1.0)
        assert confidence_high > 0.8

        # Low quality: insufficient sample size
        confidence_low_sample = rule.compute_confidence(sample_size=1, data_completeness=1.0)
        assert confidence_low_sample < 0.5

        # Low quality: poor completeness
        confidence_low_complete = rule.compute_confidence(sample_size=10, data_completeness=0.2)
        assert confidence_low_complete < 0.5

        return True, f"ComparisonRule computation validated: high_conf={confidence_high:.2f}, low_sample={confidence_low_sample:.2f}"
    except Exception as e:
        return False, f"ComparisonRule error: {e}"


def test_standard_dimensions() -> tuple[bool, str]:
    """Test standard dimension templates."""
    try:
        # Verify standard dimensions exist
        assert len(STANDARD_DIMENSIONS) >= 5

        # Check specific dimensions
        time_weekly = get_standard_dimension("CDM_TIME_WEEKLY")
        assert time_weekly is not None
        assert time_weekly.compare_type == "time_comparison"
        assert "parent" in time_weekly.visible_roles

        class_relative = get_standard_dimension("CDM_CLASS_POSITION")
        assert class_relative is not None
        assert class_relative.compare_type == "class_relative"
        assert "parent" not in class_relative.visible_roles  # Parent should NOT see class relative

        intervention = get_standard_dimension("CDM_INTERVENTION")
        assert intervention is not None
        assert intervention.compare_type == "intervention_before_after"

        return True, f"Standard dimensions validated: {len(STANDARD_DIMENSIONS)} templates"
    except Exception as e:
        return False, f"Standard dimensions error: {e}"


def test_create_comparison_result_factory() -> tuple[bool, str]:
    """Test create_comparison_result factory function."""
    try:
        dimension = CompareDimension(
            dimension_id="CDM_TEST_FACTORY",
            compare_type="time_comparison",
            name="工厂测试对比",
            description="测试工厂函数",
            min_sample_size=3,
        )

        base_window = ComparisonWindow(window_type="this_week", sample_size=10, data_completeness=0.9)
        target_window = ComparisonWindow(window_type="last_week", sample_size=8, data_completeness=0.85)

        result = create_comparison_result(
            dimension=dimension,
            base_window=base_window,
            target_window=target_window,
            base_value=0.80,
            target_value=0.65,
            sample_size=10,
            data_completeness=0.9,
            summary="本周表现明显提升",
        )

        assert result.dimension_id == "CDM_TEST_FACTORY"
        assert result.compare_type == "time_comparison"
        assert result.direction == "improving"  # delta = 0.15 >= 0.1
        assert result.strength == "moderate"  # 0.15 < 0.2
        assert result.confidence > 0.5
        assert result.base_value == 0.80
        assert result.target_value == 0.65
        assert result.delta == 0.15
        assert result.delta_percent is not None

        # Test declining scenario
        result_declining = create_comparison_result(
            dimension=dimension,
            base_window=base_window,
            target_window=target_window,
            base_value=0.50,
            target_value=0.75,
            sample_size=10,
            data_completeness=0.9,
        )
        assert result_declining.direction == "declining"
        assert result_declining.strength == "strong"  # delta = -0.25

        # Test low data quality boundary warning
        result_low_quality = create_comparison_result(
            dimension=dimension,
            base_window=base_window,
            target_window=target_window,
            base_value=0.70,
            target_value=0.65,
            sample_size=1,  # Below min_sample_size
            data_completeness=0.3,  # Below min_data_completeness
        )
        assert result_low_quality.boundary_notes is not None

        return True, f"Factory function validated: improving={result.direction}, declining={result_declining.direction}, boundary_warning={result_low_quality.boundary_notes is not None}"
    except Exception as e:
        return False, f"Factory function error: {e}"


def test_role_based_visibility() -> tuple[bool, str]:
    """Test role-based visibility rules following OBS-007."""
    try:
        # Parent should NOT see class_relative comparison
        class_relative = get_standard_dimension("CDM_CLASS_POSITION")
        assert class_relative is not None
        assert "parent" not in class_relative.visible_roles
        assert "teacher" in class_relative.visible_roles
        assert "school" in class_relative.visible_roles

        # Parent SHOULD see time comparison
        time_weekly = get_standard_dimension("CDM_TIME_WEEKLY")
        assert time_weekly is not None
        assert "parent" in time_weekly.visible_roles
        assert "student" in time_weekly.visible_roles

        # Intervention comparison: teacher and school only
        intervention = get_standard_dimension("CDM_INTERVENTION")
        assert intervention is not None
        assert "parent" not in intervention.visible_roles
        assert "teacher" in intervention.visible_roles

        return True, "Role-based visibility rules validated per OBS-007"
    except Exception as e:
        return False, f"Role visibility error: {e}"


def test_boundary_warning_conditions() -> tuple[bool, str]:
    """Test boundary warning conditions for low data quality."""
    try:
        dimension = CompareDimension(
            dimension_id="CDM_TEST_BOUNDARY",
            compare_type="time_comparison",
            name="边界测试",
            description="测试边界警告",
            min_sample_size=5,
            min_data_completeness=0.6,
            boundary_notes="数据不足时对比仅供参考",
        )

        # Good data quality - no warning
        assert dimension.should_apply_boundary_warning({
            "sample_size": 10,
            "data_completeness": 0.9
        }) is False

        # Low sample size - warning
        assert dimension.should_apply_boundary_warning({
            "sample_size": 2,
            "data_completeness": 0.9
        }) is True

        # Low completeness - warning
        assert dimension.should_apply_boundary_warning({
            "sample_size": 10,
            "data_completeness": 0.3
        }) is True

        # Both low - warning
        assert dimension.should_apply_boundary_warning({
            "sample_size": 1,
            "data_completeness": 0.2
        }) is True

        return True, "Boundary warning conditions validated"
    except Exception as e:
        return False, f"Boundary warning error: {e}"


def test_obs007_compliance() -> tuple[bool, str]:
    """Test OBS-007 design principles compliance."""
    try:
        # Principle 1: 自我对比优先于群体对比
        # Time comparison should be visible to parent
        time_dim = get_standard_dimension("CDM_TIME_WEEKLY")
        assert time_dim is not None
        assert time_dim.compare_type == "time_comparison"
        assert "parent" in time_dim.visible_roles

        # Class relative should NOT be visible to parent
        class_dim = get_standard_dimension("CDM_CLASS_POSITION")
        assert class_dim is not None
        assert class_dim.compare_type == "class_relative"
        assert "parent" not in class_dim.visible_roles

        # Principle 2: 结构对比优先于单分值对比
        # Subject internal comparisons exist
        subject_knowledge = get_standard_dimension("CDM_SUBJECT_KNOWLEDGE")
        assert subject_knowledge is not None
        assert subject_knowledge.compare_type == "subject_internal"

        # Principle 3: 教学阶段要对齐
        teaching_progress = get_standard_dimension("CDM_TEACHING_PROGRESS")
        assert teaching_progress is not None
        assert teaching_progress.compare_type == "teaching_progress"

        # Principle 4: 对比必须说明边界
        # All dimensions should have boundary_notes capability
        for dim_id, dim in STANDARD_DIMENSIONS.items():
            assert hasattr(dim, "boundary_notes")
            assert hasattr(dim, "should_apply_boundary_warning")

        # Principle 5: 不为制造刺激而对比
        # Strength control exists for expression intensity
        result = ComparisonResult(
            result_id="CMP_TEST_STRENGTH",
            dimension_id="CDM_TIME_WEEKLY",
            compare_type="time_comparison",
            base_window=ComparisonWindow(window_type="this_week"),
            target_window=ComparisonWindow(window_type="last_week"),
            direction="improving",
            strength="moderate",  # Controllable strength
        )
        assert result.strength in ["weak", "moderate", "strong"]

        return True, "OBS-007 design principles compliance validated"
    except Exception as e:
        return False, f"OBS-007 compliance error: {e}"


def run_all_tests() -> dict:
    """Run all comparison dimension tests."""
    tests = [
        ("comparison_window_structure", test_comparison_window_structure),
        ("compare_dimension_structure", test_compare_dimension_structure),
        ("comparison_result_structure", test_comparison_result_structure),
        ("comparison_rule_computation", test_comparison_rule_computation),
        ("standard_dimensions", test_standard_dimensions),
        ("factory_function", test_create_comparison_result_factory),
        ("role_visibility", test_role_based_visibility),
        ("boundary_warning", test_boundary_warning_conditions),
        ("obs007_compliance", test_obs007_compliance),
    ]

    results = {name: func() for name, func in tests}

    summary = {
        "total": len(tests),
        "passed": sum(1 for r in results.values() if r[0]),
        "failed": sum(1 for r in results.values() if not r[0]),
    }

    return {
        "summary": summary,
        "results": {
            name: {"success": success, "message": message}
            for name, (success, message) in results.items()
        },
    }


if __name__ == "__main__":
    results = run_all_tests()
    import json
    print(json.dumps(results, indent=2, ensure_ascii=False))

    # Print summary
    print("\n" + "=" * 50)
    print(f"Passed: {results['summary']['passed']}/{results['summary']['total']}")
    if results["summary"]["failed"] == 0:
        print("Conclusion: All comparison dimension tests passed.")
    else:
        print("Conclusion: Some tests failed. Review errors above.")
