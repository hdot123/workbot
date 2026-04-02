"""Comparison dimensions and result models for OBS layer.

Follows OBS-007 design: 对比维度与观察口径
Supports time comparison, subject internal comparison, class relative comparison,
intervention before/after comparison, and teaching progress comparison.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Literal


# Comparison type enumeration
CompareType = Literal[
    "time_comparison",          # 时间对比：与自己过去比
    "subject_internal",         # 学科内部对比：知识点/题型结构
    "knowledge_chain",          # 知识链路对比：前置/当前/后续
    "class_relative",           # 班级相对对比：在群体中的位置
    "teaching_progress",        # 教学进度对比：与教学进度对齐
    "intervention_before_after", # 干预前后对比
]

# Comparison direction
CompareDirection = Literal[
    "improving",      # 变好/提升
    "declining",      # 变差/下降
    "stable",         # 稳定
    "fluctuating",    # 波动
    "higher",         # 高于参照
    "lower",          # 低于参照
    "aligned",        # 对齐/匹配
    "behind",         # 落后
]

# Comparison strength (for controlling expression intensity)
CompareStrength = Literal[
    "weak",      # 轻微
    "moderate",  # 中等
    "strong",    # 明显
]

# Role-based visibility
CompareRole = Literal["parent", "teacher", "school", "student"]

# Time window standard
TimeWindow = Literal[
    "last_7d",
    "last_14d",
    "last_30d",
    "this_week",
    "last_week",
    "this_month",
    "last_month",
    "this_semester",
    "pre_exam",
    "post_exam",
]


@dataclass(frozen=True)
class ComparisonWindow:
    """
    Defines a comparison time window with boundary.

    Used to ensure consistent time window references across comparisons.
    """

    window_type: TimeWindow
    start_time: str | None = None  # ISO format
    end_time: str | None = None    # ISO format
    sample_size: int | None = None  # Number of data points
    data_completeness: float | None = None  # 0.0-1.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "window_type": self.window_type,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "sample_size": self.sample_size,
            "data_completeness": self.data_completeness,
        }

    @classmethod
    def create_standard(cls, window_type: TimeWindow) -> ComparisonWindow:
        """Create a standard window without explicit time bounds."""
        return cls(window_type=window_type)


@dataclass(frozen=True)
class CompareDimension:
    """
    Defines a comparison dimension with scope and rules.

    Follows OBS-007 principles:
    - 自我对比优先于群体对比
    - 结构对比优先于单分值对比
    - 教学阶段要对齐
    - 对比必须说明边界
    """

    dimension_id: str
    compare_type: CompareType
    name: str
    description: str

    # Scope definition
    scope: str = "student"  # "student", "class", "grade", "school"
    subject: str | None = None  # Subject filter
    knowledge_ids: list[str] = field(default_factory=list)  # Knowledge point filter

    # Role visibility
    visible_roles: list[CompareRole] = field(default_factory=lambda: ["parent", "teacher", "school"])

    # Boundary conditions
    min_sample_size: int = 3  # Minimum data points required
    min_data_completeness: float = 0.5  # Minimum data completeness

    # Expression control
    strength: CompareStrength = "moderate"
    boundary_notes: str | None = None  # When comparison may be misleading

    def to_dict(self) -> dict[str, Any]:
        return {
            "dimension_id": self.dimension_id,
            "compare_type": self.compare_type,
            "name": self.name,
            "description": self.description,
            "scope": self.scope,
            "subject": self.subject,
            "knowledge_ids": self.knowledge_ids,
            "visible_roles": self.visible_roles,
            "min_sample_size": self.min_sample_size,
            "min_data_completeness": self.min_data_completeness,
            "strength": self.strength,
            "boundary_notes": self.boundary_notes,
        }

    def is_visible_to(self, role: CompareRole) -> bool:
        """Check if this dimension is visible to given role."""
        return role in self.visible_roles

    def should_apply_boundary_warning(self, data_quality: dict[str, Any]) -> bool:
        """Check if boundary warning should be shown."""
        sample_size = data_quality.get("sample_size", 0)
        completeness = data_quality.get("data_completeness", 0.0)
        return sample_size < self.min_sample_size or completeness < self.min_data_completeness


@dataclass
class ComparisonResult:
    """
    Result of a comparison operation.

    Structured output following OBS-007 section 19 recommendations.
    """

    result_id: str
    dimension_id: str
    compare_type: CompareType

    # Windows being compared
    base_window: ComparisonWindow
    target_window: ComparisonWindow

    # Result expression
    direction: CompareDirection
    strength: CompareStrength = "moderate"
    confidence: float = 1.0  # 0.0-1.0

    # Quantitative data (optional)
    base_value: float | None = None
    target_value: float | None = None
    delta: float | None = None
    delta_percent: float | None = None

    # Qualitative summary
    summary: str = ""
    boundary_notes: str | None = None  # When comparison has limitations

    # Scope context
    scope: str = "student"
    subject: str | None = None
    knowledge_ids: list[str] = field(default_factory=list)

    # Role-based rendering
    visible_roles: list[CompareRole] = field(default_factory=lambda: ["parent", "teacher", "school"])

    def to_dict(self) -> dict[str, Any]:
        return {
            "result_id": self.result_id,
            "dimension_id": self.dimension_id,
            "compare_type": self.compare_type,
            "base_window": self.base_window.to_dict(),
            "target_window": self.target_window.to_dict(),
            "direction": self.direction,
            "strength": self.strength,
            "confidence": self.confidence,
            "base_value": self.base_value,
            "target_value": self.target_value,
            "delta": self.delta,
            "delta_percent": self.delta_percent,
            "summary": self.summary,
            "boundary_notes": self.boundary_notes,
            "scope": self.scope,
            "subject": self.subject,
            "knowledge_ids": self.knowledge_ids,
            "visible_roles": self.visible_roles,
        }

    def should_show_to(self, role: CompareRole) -> bool:
        """Check if this result should be shown to given role."""
        return role in self.visible_roles


@dataclass(frozen=True)
class ComparisonRule:
    """
    Rule for computing comparison results.

    Encapsulates logic for determining direction, strength, and boundary conditions.
    """

    rule_id: str
    dimension_id: str
    compare_type: CompareType

    # Threshold configuration
    improving_threshold: float = 0.1  # Delta >= 0.1 = improving
    declining_threshold: float = -0.1  # Delta <= -0.1 = declining
    strong_delta: float = 0.2  # |delta| >= 0.2 = strong strength

    # Confidence rules
    min_sample_size: int = 3
    completeness_weight: float = 0.3  # Weight of data completeness in confidence

    def compute_direction(self, delta: float) -> CompareDirection:
        """Compute comparison direction from delta."""
        if delta >= self.improving_threshold:
            return "improving"
        elif delta <= self.declining_threshold:
            return "declining"
        else:
            return "stable"

    def compute_strength(self, delta: float) -> CompareStrength:
        """Compute comparison strength from delta magnitude."""
        abs_delta = abs(delta)
        if abs_delta >= self.strong_delta:
            return "strong"
        elif abs_delta >= self.improving_threshold:
            return "moderate"
        else:
            return "weak"

    def compute_confidence(self, sample_size: int, data_completeness: float) -> float:
        """Compute confidence score based on data quality."""
        # Sample size component (0-0.7)
        if sample_size >= self.min_sample_size:
            size_score = min(0.7, sample_size / (self.min_sample_size * 3) * 0.7)
        else:
            size_score = (sample_size / self.min_sample_size) * 0.7 * 0.5

        # Completeness component (0-0.3)
        completeness_score = data_completeness * self.completeness_weight

        return min(1.0, size_score + completeness_score)


# Standard dimension templates following OBS-007 MVP recommendations

STANDARD_DIMENSIONS: dict[str, CompareDimension] = {
    "time_comparison_weekly": CompareDimension(
        dimension_id="CDM_TIME_WEEKLY",
        compare_type="time_comparison",
        name="周度时间对比",
        description="与上一周相比的学习状态变化",
        scope="student",
        visible_roles=["parent", "teacher", "student"],
        boundary_notes="数据覆盖不足时对比结果仅供参考",
    ),
    "time_comparison_monthly": CompareDimension(
        dimension_id="CDM_TIME_MONTHLY",
        compare_type="time_comparison",
        name="月度时间对比",
        description="与上一月相比的学习状态变化",
        scope="student",
        visible_roles=["parent", "teacher", "student"],
    ),
    "subject_internal_knowledge": CompareDimension(
        dimension_id="CDM_SUBJECT_KNOWLEDGE",
        compare_type="subject_internal",
        name="学科知识点结构对比",
        description="学科内部不同知识点的掌握情况对比",
        scope="student",
        subject=None,  # Flexible subject
        min_sample_size=5,
    ),
    "subject_internal_question_type": CompareDimension(
        dimension_id="CDM_SUBJECT_QTYPE",
        compare_type="subject_internal",
        name="学科题型结构对比",
        description="学科内部不同题型的表现对比",
        scope="student",
        subject=None,
        min_sample_size=5,
    ),
    "class_relative_position": CompareDimension(
        dimension_id="CDM_CLASS_POSITION",
        compare_type="class_relative",
        name="班级相对位置",
        description="学生在班级中的相对位置变化",
        scope="class",
        visible_roles=["teacher", "school"],  # NOT visible to parent
        min_sample_size=10,  # Need sufficient class size
        boundary_notes="班级人数较少时相对位置仅供参考",
    ),
    "teaching_progress_alignment": CompareDimension(
        dimension_id="CDM_TEACHING_PROGRESS",
        compare_type="teaching_progress",
        name="教学进度对齐",
        description="学习进度与教学进度的对比",
        scope="class",
        visible_roles=["teacher", "school", "parent"],
    ),
    "intervention_before_after": CompareDimension(
        dimension_id="CDM_INTERVENTION",
        compare_type="intervention_before_after",
        name="干预前后对比",
        description="干预动作执行前后的效果对比",
        scope="student",
        visible_roles=["teacher", "school"],
        min_sample_size=2,  # Pre and post
    ),
}


def get_standard_dimension(dimension_id: str) -> CompareDimension | None:
    """Get a standard dimension by template key or dimension_id."""
    dimension = STANDARD_DIMENSIONS.get(dimension_id)
    if dimension is not None:
        return dimension
    for candidate in STANDARD_DIMENSIONS.values():
        if candidate.dimension_id == dimension_id:
            return candidate
    return None


def create_comparison_result(
    dimension: CompareDimension,
    base_window: ComparisonWindow,
    target_window: ComparisonWindow,
    base_value: float | None = None,
    target_value: float | None = None,
    delta: float | None = None,
    sample_size: int = 0,
    data_completeness: float = 1.0,
    summary: str = "",
) -> ComparisonResult:
    """
    Factory function to create a comparison result from a dimension.

    Automatically computes direction, strength, and confidence.
    """
    # Compute delta if not provided
    if delta is None and base_value is not None and target_value is not None:
        delta = base_value - target_value

    # Create rule and compute metrics
    rule = ComparisonRule(
        rule_id=f"RULE_{dimension.dimension_id}",
        dimension_id=dimension.dimension_id,
        compare_type=dimension.compare_type,
    )

    if delta is not None:
        direction = rule.compute_direction(delta)
        strength = rule.compute_strength(delta)
    else:
        direction = "stable"
        strength = "weak"

    confidence = rule.compute_confidence(sample_size, data_completeness)

    # Check boundary notes
    boundary_notes = None
    if dimension.should_apply_boundary_warning({"sample_size": sample_size, "data_completeness": data_completeness}):
        boundary_notes = dimension.boundary_notes or "数据质量不足，对比结果仅供参考"

    # Compute delta percent
    delta_percent = None
    if delta is not None and target_value is not None and target_value != 0:
        delta_percent = delta / abs(target_value)

    return ComparisonResult(
        result_id=f"CMP_{dimension.dimension_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
        dimension_id=dimension.dimension_id,
        compare_type=dimension.compare_type,
        base_window=base_window,
        target_window=target_window,
        direction=direction,
        strength=strength,
        confidence=confidence,
        base_value=base_value,
        target_value=target_value,
        delta=delta,
        delta_percent=delta_percent,
        summary=summary,
        boundary_notes=boundary_notes,
        scope=dimension.scope,
        subject=dimension.subject,
        knowledge_ids=dimension.knowledge_ids,
        visible_roles=dimension.visible_roles,
    )
