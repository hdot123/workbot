#!/usr/bin/env python3
"""
F9-T2: Text main chain integration test scenarios.

Covers:
- Normal scenario (成功样例)
- Degraded scenario (降级样例)
- Review needed scenario (review_needed 样例)
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Add repository root to Python path for running tests from root directory
repo_root = Path(__file__).resolve().parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from datetime import datetime

from app.models.event_assembler import TextInput, assemble_event
from app.models.twin_ingest_contract import TwinIngestContract, TwinIngestDecision
from app.models.twin_state import StudentTwinState, KnowledgeState, AbilityState, ChapterProgress
from app.models.twin_updater import TWINStateUpdater, StateUpdateResult
from app.models.graph_models import StudentNode, KnowledgeNode, GraphEdge
from app.models.graph_writer import GraphWriter, InMemoryGraphStore
from app.models.obs_models import OBSDisplayBuilder
from app.models.retrieval_unit import RetrievalUnitAssembler, RetrievalContext


class InMemoryStateStore:
    """Simple in-memory state store for testing."""

    def __init__(self):
        self.states: dict[str, StudentTwinState] = {}

    def get_state(self, student_id: str) -> StudentTwinState | None:
        return self.states.get(student_id)

    def save_state(self, state: StudentTwinState) -> None:
        self.states[state.student_id] = state


def create_base_twin_state(student_id: str) -> StudentTwinState:
    """Create a base twin state with some initial data."""
    now = datetime.now().isoformat()
    state = StudentTwinState.create_empty(student_id, now)

    state.knowledge_states["PHY_PEP_G1_V1_KP_001"] = KnowledgeState(
        knowledge_id="PHY_PEP_G1_V1_KP_001",
        mastery_level=0.75,
        last_updated=now,
        evidence_count=3,
        trend="improving",
    )

    state.ability_states["PHY_AP_001"] = AbilityState(
        ability_id="PHY_AP_001",
        ability_level=0.70,
        last_updated=now,
        evidence_count=3,
    )

    state.chapter_progress["PHY_PEP_G1_V1_CH_01"] = ChapterProgress(
        chapter_node_id="PHY_PEP_G1_V1_CH_01",
        coverage=0.50,
        knowledge_mastery_avg=0.75,
        last_studied=now,
        time_spent_minutes=30,
        exercise_count=5,
    )

    return state


def run_normal_scenario() -> tuple[bool, str, dict]:
    """
    F9-T2 Normal scenario: Complete flow with knowledge refs.

    Flow: Text input -> Event assembly -> TWIN update -> Graph write -> Retrieval assembly
    """
    try:
        student_id = "STU_NORMAL_001"

        twin_store = InMemoryStateStore()
        twin_store.save_state(create_base_twin_state(student_id))

        graph_store = InMemoryGraphStore()
        graph_writer = GraphWriter(graph_store)

        updater = TWINStateUpdater(twin_store)

        contract = TwinIngestContract(
            event_id="EVT_NORMAL_001",
            student_id=student_id,
            event_type="parent_feedback_event",
            source_type="parent_text",
            event_time="2026-03-26T10:00:00",
            region_id="安徽",
            stage_level="高中",
            grade_level="高一",
            subject="物理",
            curriculum_version_id="PHY_PEP_G1_V1",
            event_status="success",
            confidence_score=0.85,
            event_summary="学生今天复习了质点概念，掌握良好",
            raw_input_ref="raw:EVT_NORMAL_001",
            trace_id="TRC_NORMAL_001",
            knowledge_refs=["PHY_PEP_G1_V1_KP_001"],
            ability_refs=["PHY_AP_001"],
        )

        result = updater.process_event(contract)

        if not result.success:
            return False, f"TWIN update failed: {result.error}", {}

        assembler = RetrievalUnitAssembler(
            twin_store=twin_store,
            graph_store=graph_store,
            chapter_names={"PHY_PEP_G1_V1_CH_01": "第一章 运动的描述"},
            knowledge_names={"PHY_PEP_G1_V1_KP_001": "质点的概念"},
            ability_names={"PHY_AP_001": "理解概念的能力"},
        )

        context = assembler.assemble(student_id)

        output = {
            "scenario": "normal",
            "student_id": student_id,
            "twin_update_success": result.success,
            "retrieval_complete": context.is_complete,
            "current_state": context.retrieval_unit.current_state.to_dict() if context.retrieval_unit.current_state else None,
            "key_events_count": len(context.retrieval_unit.key_events),
            "structural_refs_count": len(context.retrieval_unit.structural_refs),
        }

        return True, "Normal scenario passed", output

    except Exception as e:
        return False, f"Normal scenario error: {e}", {}


def run_degraded_scenario() -> tuple[bool, str, dict]:
    """
    F9-T2 Degraded scenario: Event without knowledge refs.

    Flow: Text input -> Event assembly (no knowledge refs) -> TWIN update (degraded) -> Retrieval
    """
    try:
        student_id = "STU_DEGRADED_001"

        twin_store = InMemoryStateStore()
        twin_store.save_state(create_base_twin_state(student_id))

        graph_store = InMemoryGraphStore()

        updater = TWINStateUpdater(twin_store)

        contract = TwinIngestContract(
            event_id="EVT_DEGRADED_001",
            student_id=student_id,
            event_type="parent_feedback_event",
            source_type="parent_text",
            event_time="2026-03-26T11:00:00",
            region_id="安徽",
            stage_level="高中",
            grade_level="高一",
            subject="物理",
            curriculum_version_id="PHY_PEP_G1_V1",
            event_status="degraded",
            confidence_score=0.55,
            event_summary="家长反馈孩子学习状态不佳，但无具体知识点信息",
            raw_input_ref="raw:EVT_DEGRADED_001",
            trace_id="TRC_DEGRADED_001",
            knowledge_refs=[],
            ability_refs=[],
            behavior_tags=["low_engagement"],
            parent_context_summary="孩子最近学习不太积极",
        )

        result = updater.process_event(contract)

        # Degraded 场景：event_status="degraded" 会被 twin_ingest_contract 识别为需要 review
        # 预期行为：success=True, was_skipped=True, skipped_reason="low_confidence"
        if not result.success:
            return False, f"TWIN update failed: {result.error}", {}

        # 验证 degraded 事件被正确识别并路由到 review
        is_expected_degraded = result.was_skipped and result.skipped_reason in [
            "low_confidence",
            "event_requires_review_first",
        ]

        assembler = RetrievalUnitAssembler(
            twin_store=twin_store,
            graph_store=graph_store,
            chapter_names={"PHY_PEP_G1_V1_CH_01": "第一章 运动的描述"},
            knowledge_names={"PHY_PEP_G1_V1_KP_001": "质点的概念"},
            ability_names={"PHY_AP_001": "理解概念的能力"},
        )

        context = assembler.assemble(student_id)

        output = {
            "scenario": "degraded",
            "student_id": student_id,
            "twin_update_success": result.success,
            "twin_update_skipped": result.was_skipped,
            "skipped_reason": result.skipped_reason,
            "is_expected_behavior": is_expected_degraded,
            "retrieval_complete": context.is_complete,
            "has_behavior_update": len(result.behavior_updates) > 0 if result.success else False,
            "current_state": context.retrieval_unit.current_state.to_dict() if context.retrieval_unit.current_state else None,
        }

        # Degraded 场景只要正确识别并处理（无论是更新还是跳过）就算通过
        if is_expected_degraded:
            return True, "Degraded scenario passed (correctly routed to review)", output
        else:
            return False, f"Degraded scenario unexpected result: skipped={result.was_skipped}, reason={result.skipped_reason}", output

    except Exception as e:
        return False, f"Degraded scenario error: {e}", {}


def run_review_needed_scenario() -> tuple[bool, str, dict]:
    """
    F9-T2 Review needed scenario: Low confidence event requires review.

    Flow: Text input -> Event assembly (low confidence) -> TWIN (skipped for review) -> Retrieval
    """
    try:
        student_id = "STU_REVIEW_001"

        twin_store = InMemoryStateStore()
        twin_store.save_state(create_base_twin_state(student_id))

        graph_store = InMemoryGraphStore()

        updater = TWINStateUpdater(twin_store)

        contract = TwinIngestContract(
            event_id="EVT_REVIEW_001",
            student_id=student_id,
            event_type="parent_feedback_event",
            source_type="parent_text",
            event_time="2026-03-26T12:00:00",
            region_id="安徽",
            stage_level="高中",
            grade_level="高一",
            subject="物理",
            curriculum_version_id="PHY_PEP_G1_V1",
            event_status="review_needed",
            confidence_score=0.40,
            event_summary="家长反馈内容模糊，需要人工审核",
            raw_input_ref="raw:EVT_REVIEW_001",
            trace_id="TRC_REVIEW_001",
            knowledge_refs=["PHY_PEP_G1_V1_KP_001"],
            ability_refs=["PHY_AP_001"],
            review_ticket_ref="REV_TICKET_001",
        )

        result = updater.process_event(contract)

        # Review needed 场景：event_status="review_needed" 会被路由到 review
        # 预期行为：success=True, was_skipped=True, skipped_reason="explicit_review_needed"
        if not result.success:
            return False, f"TWIN update failed: {result.error}", {}

        # 验证 review_needed 事件被正确识别并路由到 review
        is_expected_review = result.was_skipped and result.skipped_reason in [
            "explicit_review_needed",
            "low_confidence",
        ]

        assembler = RetrievalUnitAssembler(
            twin_store=twin_store,
            graph_store=graph_store,
            chapter_names={"PHY_PEP_G1_V1_CH_01": "第一章 运动的描述"},
            knowledge_names={"PHY_PEP_G1_V1_KP_001": "质点的概念"},
            ability_names={"PHY_AP_001": "理解概念的能力"},
        )

        context = assembler.assemble(student_id)

        output = {
            "scenario": "review_needed",
            "student_id": student_id,
            "twin_update_success": result.success,
            "twin_update_skipped": result.was_skipped,
            "skipped_reason": result.skipped_reason,
            "is_expected_behavior": is_expected_review,
            "retrieval_complete": context.is_complete,
            "current_state": context.retrieval_unit.current_state.to_dict() if context.retrieval_unit.current_state else None,
        }

        # Review needed 场景只要正确识别并跳过就算通过
        if is_expected_review:
            return True, "Review needed scenario passed (correctly routed to review)", output
        else:
            return False, f"Review needed scenario unexpected result: skipped={result.was_skipped}, reason={result.skipped_reason}", output

    except Exception as e:
        return False, f"Review needed scenario error: {e}", {}


def run_all_scenarios() -> dict:
    """Run all F9-T2 scenarios and collect results."""
    results = {
        "normal": run_normal_scenario(),
        "degraded": run_degraded_scenario(),
        "review_needed": run_review_needed_scenario(),
    }

    summary = {
        "total": 3,
        "passed": sum(1 for r in results.values() if r[0]),
        "failed": sum(1 for r in results.values() if not r[0]),
    }

    return {
        "summary": summary,
        "results": {
            name: {"success": success, "message": message, "output": output}
            for name, (success, message, output) in results.items()
        },
    }


if __name__ == "__main__":
    results = run_all_scenarios()
    print(json.dumps(results, indent=2, ensure_ascii=False))


# ============== Pytest wrapper ==============
# Minimal pytest-compatible tests for CI integration

def test_f9_normal_scenario():
    """F9-T2-N: Normal scenario test."""
    success, message, output = run_normal_scenario()
    assert success, message
    assert output.get("twin_update_success") is True
    assert output.get("retrieval_complete") is True


def test_f9_degraded_scenario():
    """F9-T2-D: Degraded scenario test."""
    success, message, output = run_degraded_scenario()
    assert success, message
    assert output.get("is_expected_behavior") is True


def test_f9_review_needed_scenario():
    """F9-T2-R: Review needed scenario test."""
    success, message, output = run_review_needed_scenario()
    assert success, message
    assert output.get("is_expected_behavior") is True
