"""F9-T3: Main chain pass/block judgment."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Literal


@dataclass(frozen=True)
class ChainJudgment:
    """
    Judgment result for the text main chain.

    Conclusion:
    - "pass": Main chain is fully functional
    - "conditional_pass": Main chain works with conditions/limitations
    - "blocked": Main chain has blocking issues
    """

    conclusion: Literal["pass", "conditional_pass", "blocked"]
    judged_at: str
    judgment_id: str

    p0_blockers: list[str] = field(default_factory=list)
    p1_limitations: list[str] = field(default_factory=list)
    p2_suggestions: list[str] = field(default_factory=list)

    scenario_results: dict[str, dict] = field(default_factory=dict)

    rationale: str = ""
    next_actions: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "conclusion": self.conclusion,
            "judged_at": self.judged_at,
            "judgment_id": self.judgment_id,
            "p0_blockers": self.p0_blockers,
            "p1_limitations": self.p1_limitations,
            "p2_suggestions": self.p2_suggestions,
            "scenario_results": self.scenario_results,
            "rationale": self.rationale,
            "next_actions": self.next_actions,
        }


class MainChainJudge:
    """
    Judge for text main chain pass/block decision.

    F9-T3 core component.
    """

    def __init__(self):
        self.required_scenarios = {"normal", "degraded", "review_needed"}
        self.required_components = {
            "event_assembler",
            "twin_ingest_contract",
            "twin_state",
            "twin_updater",
            "graph_models",
            "graph_writer",
            "retrieval_unit",
            "obs_models",
        }

    def judge(
        self,
        scenario_results: dict[str, tuple[bool, str, dict]],
        component_availability: dict[str, bool],
    ) -> ChainJudgment:
        """
        Make a pass/block judgment based on scenario results and component availability.

        Args:
            scenario_results: Results from F9-T2 scenarios
            component_availability: Availability of required components

        Returns:
            ChainJudgment with conclusion and rationale
        """
        now = datetime.now().isoformat()
        import uuid
        judgment_id = f"JDG_{uuid.uuid4().hex[:12].upper()}"

        p0_blockers: list[str] = []
        p1_limitations: list[str] = []
        p2_suggestions: list[str] = []

        scenario_results_dict = {}

        for scenario_name, (success, message, output) in scenario_results.items():
            scenario_results_dict[scenario_name] = {
                "success": success,
                "message": message,
            }

            if not success:
                if scenario_name == "normal":
                    p0_blockers.append(f"Normal scenario failed: {message}")
                elif scenario_name == "degraded":
                    p1_limitations.append(f"Degraded scenario failed: {message}")
                elif scenario_name == "review_needed":
                    p1_limitations.append(f"Review needed scenario failed: {message}")

        for component in self.required_components:
            if not component_availability.get(component, False):
                p0_blockers.append(f"Required component missing: {component}")

        missing_scenarios = self.required_scenarios - set(scenario_results.keys())
        if missing_scenarios:
            p1_limitations.append(f"Missing scenarios: {missing_scenarios}")

        if p0_blockers:
            conclusion = "blocked"
            rationale = f"主链存在 {len(p0_blockers)} 个阻断问题，无法通过"
            next_actions = [f"修复 P0 问题：{b}" for b in p0_blockers[:3]]

        elif p1_limitations:
            conclusion = "conditional_pass"
            rationale = f"主链基本功能可用，但存在 {len(p1_limitations)} 个限制项"
            next_actions = [f"处理 P1 限制：{l}" for l in p1_limitations[:3]]
            p2_suggestions.append("建议在下一个迭代中解决 P1 限制项")

        else:
            conclusion = "pass"
            rationale = "主链所有核心场景通过，组件完整"
            next_actions = ["可以继续推进后续功能开发"]

        if not p2_suggestions:
            p2_suggestions.append("建议补充更多边界场景测试")
            p2_suggestions.append("建议增加性能测试和压力测试")

        return ChainJudgment(
            conclusion=conclusion,
            judged_at=now,
            judgment_id=judgment_id,
            p0_blockers=p0_blockers,
            p1_limitations=p1_limitations,
            p2_suggestions=p2_suggestions,
            scenario_results=scenario_results_dict,
            rationale=rationale,
            next_actions=next_actions,
        )


def make_f9_judgment(
    scenario_results: dict[str, tuple[bool, str, dict]],
) -> ChainJudgment:
    """
    Make F9 judgment based on scenario results.

    This is the main entry point for F9-T3.
    """
    judge = MainChainJudge()

    component_availability = {
        "event_assembler": True,
        "twin_ingest_contract": True,
        "twin_state": True,
        "twin_updater": True,
        "graph_models": True,
        "graph_writer": True,
        "retrieval_unit": True,
        "obs_models": True,
    }

    return judge.judge(scenario_results, component_availability)
