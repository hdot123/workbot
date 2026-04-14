#!/usr/bin/env python3
"""Structural-reference scoping tests for RetrievalUnitAssembler."""

from __future__ import annotations

import sys
from pathlib import Path

repo_root = Path(__file__).resolve().parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from datetime import datetime

from app.models.graph_models import GraphSnapshot
from app.models.retrieval_unit import RetrievalUnitAssembler
from app.models.twin_state import (
    AbilityState, BehaviorRecord, ChapterProgress,
    KnowledgeState, StudentTwinState,
)



# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_twin_state(
    student_id="STU_001",
    chapter_ids=None,
    knowledge_ids=None,
    ability_ids=None,
    behaviors=None,
):
    chapter_ids = chapter_ids or ["CH_A", "CH_B"]
    knowledge_ids = knowledge_ids or ["KP_1", "KP_2", "KP_3"]
    ability_ids = ability_ids or ["AP_1", "AP_2"]
    now = datetime.now().isoformat()
    return StudentTwinState(
        student_id=student_id,
        created_at=now,
        updated_at=now,
        knowledge_states={
            kid: KnowledgeState(knowledge_id=kid, mastery_level=0.7, last_updated=now)
            for kid in knowledge_ids
        },
        ability_states={
            aid: AbilityState(ability_id=aid, ability_level=0.6, last_updated=now)
            for aid in ability_ids
        },
        chapter_progress={
            cid: ChapterProgress(
                chapter_node_id=cid,
                coverage=0.5,
                knowledge_mastery_avg=0.7,
                last_studied=now,
            )
            for cid in chapter_ids
        },
        behavior_records=behaviors or [],
    )


def _make_assembler(
    chapter_knowledge_map=None,
    knowledge_to_ability_map=None,
    chapter_names=None,
):
    return RetrievalUnitAssembler(
        twin_store=_FakeTwinStore(),
        graph_store=_FakeGraphStore(),
        chapter_names=chapter_names or {},
        chapter_knowledge_map=chapter_knowledge_map,
        knowledge_to_ability_map=knowledge_to_ability_map,
    )


class _FakeTwinStore:
    def __init__(self, state=None):
        self._state = state

    def get_state(self, student_id):
        return self._state

    def save_state(self, state):
        self._state = state


class _FakeGraphStore:
    def get_latest_snapshot(self):
        return None


def _run_case(test_func):
    try:
        test_func()
    except AssertionError as exc:
        return False, str(exc) or "assertion failed"
    except Exception as exc:
        return False, f"{type(exc).__name__}: {exc}"
    return True, "passed"



# ---------------------------------------------------------------------------
# Test cases
# ---------------------------------------------------------------------------

def test_mapped_scoping():
    """When maps are present, each chapter gets only its scoped knowledge/abilities."""
    asm = _make_assembler(
        chapter_knowledge_map={"CH_A": ["KP_1", "KP_2"], "CH_B": ["KP_3"]},
        knowledge_to_ability_map={"KP_1": ["AP_1"], "KP_2": ["AP_1", "AP_2"], "KP_3": ["AP_2"]},
        chapter_names={"CH_A": "Chapter A", "CH_B": "Chapter B"},
    )
    twin = _make_twin_state(
        chapter_ids=["CH_A", "CH_B"],
        knowledge_ids=["KP_1", "KP_2", "KP_3"],
        ability_ids=["AP_1", "AP_2"],
    )
    refs = asm.assemble_structural_refs(twin)
    assert len(refs) == 2, f"expected 2 refs, got {len(refs)}"

    by_ch = {r.chapter_node_id: r for r in refs}
    assert sorted(by_ch["CH_A"].knowledge_ids) == ["KP_1", "KP_2"]
    assert sorted(by_ch["CH_A"].ability_ids) == ["AP_1", "AP_2"]
    assert by_ch["CH_B"].knowledge_ids == ["KP_3"]
    assert by_ch["CH_B"].ability_ids == ["AP_2"]

def test_empty_fallback_when_no_maps():
    """When no maps are provided, knowledge_ids and ability_ids are empty lists."""
    asm = _make_assembler()
    twin = _make_twin_state(
        chapter_ids=["CH_A"],
        knowledge_ids=["KP_1", "KP_2", "KP_3"],
        ability_ids=["AP_1", "AP_2"],
    )
    refs = asm.assemble_structural_refs(twin)
    assert len(refs) == 1
    assert refs[0].chapter_node_id == "CH_A"
    assert refs[0].knowledge_ids == [], f"expected [], got {refs[0].knowledge_ids}"
    assert refs[0].ability_ids == [], f"expected [], got {refs[0].ability_ids}"


def test_partial_coverage():
    """Some chapters mapped, some not. Unmapped chapters get empty lists."""
    asm = _make_assembler(
        chapter_knowledge_map={"CH_A": ["KP_1"]},
        knowledge_to_ability_map={"KP_1": ["AP_1"]},
    )
    twin = _make_twin_state(
        chapter_ids=["CH_A", "CH_B"],
        knowledge_ids=["KP_1", "KP_2"],
        ability_ids=["AP_1", "AP_2"],
    )
    refs = asm.assemble_structural_refs(twin)
    assert len(refs) == 2
    by_ch = {r.chapter_node_id: r for r in refs}
    assert by_ch["CH_A"].knowledge_ids == ["KP_1"]
    assert by_ch["CH_A"].ability_ids == ["AP_1"]
    assert by_ch["CH_B"].knowledge_ids == []
    assert by_ch["CH_B"].ability_ids == []


def test_missing_knowledge_in_ability_map():
    """Knowledge present in chapter map but missing from ability map -> empty ability_ids."""
    asm = _make_assembler(
        chapter_knowledge_map={"CH_A": ["KP_1", "KP_UNKNOWN"]},
        knowledge_to_ability_map={"KP_1": ["AP_1"]},
    )
    twin = _make_twin_state(
        chapter_ids=["CH_A"],
        knowledge_ids=["KP_1", "KP_UNKNOWN"],
        ability_ids=["AP_1"],
    )
    refs = asm.assemble_structural_refs(twin)
    assert len(refs) == 1
    assert sorted(refs[0].knowledge_ids) == ["KP_1", "KP_UNKNOWN"]
    assert refs[0].ability_ids == ["AP_1"]

def test_assemble_current_state_unchanged():
    """Regression: assemble_current_state computes correct averages."""
    asm = _make_assembler()
    now = datetime.now().isoformat()
    twin = _make_twin_state(
        knowledge_ids=["KP_1", "KP_2"],
        ability_ids=["AP_1"],
        chapter_ids=["CH_A"],
    )
    twin.knowledge_states["KP_1"] = KnowledgeState(knowledge_id="KP_1", mastery_level=0.4, last_updated=now)
    twin.knowledge_states["KP_2"] = KnowledgeState(knowledge_id="KP_2", mastery_level=0.8, last_updated=now)
    twin.ability_states["AP_1"] = AbilityState(ability_id="AP_1", ability_level=0.9, last_updated=now)
    twin.chapter_progress["CH_A"] = ChapterProgress(
        chapter_node_id="CH_A", coverage=0.6, knowledge_mastery_avg=0.7, last_studied=now,
    )
    view = asm.assemble_current_state(twin)
    assert abs(view.knowledge_mastery_avg - 0.6) < 0.001
    assert abs(view.ability_level_avg - 0.9) < 0.001
    assert abs(view.chapter_coverage_avg - 0.6) < 0.001


def test_assemble_key_events_unchanged():
    """Regression: assemble_key_events returns behavior records correctly."""
    behaviors = [
        BehaviorRecord(behavior_tag="focus_drop", observed_at="2026-01-01T10:00:00", intensity=0.5, context="Lost focus"),
        BehaviorRecord(behavior_tag="improvement", observed_at="2026-01-02T10:00:00", intensity=0.5, context="Improved"),
    ]
    asm = _make_assembler()
    twin = _make_twin_state(behaviors=behaviors)
    events = asm.assemble_key_events(twin, limit=10)
    assert len(events) == 2
    assert events[0].event_type == "behavior_observation"
    assert events[0].event_status == "success"


def test_full_assemble_with_maps():
    """End-to-end: assemble() produces complete context with correctly scoped refs."""
    twin = _make_twin_state(chapter_ids=["CH_A"], knowledge_ids=["KP_1"], ability_ids=["AP_1"])
    fake_store = _FakeTwinStore(twin)
    asm = RetrievalUnitAssembler(
        twin_store=fake_store,
        graph_store=_FakeGraphStore(),
        chapter_names={"CH_A": "Chapter A"},
        chapter_knowledge_map={"CH_A": ["KP_1"]},
        knowledge_to_ability_map={"KP_1": ["AP_1"]},
    )
    ctx = asm.assemble("STU_001")
    assert ctx.is_complete
    assert ctx.retrieval_unit.current_state is not None
    assert len(ctx.retrieval_unit.structural_refs) == 1
    sref = ctx.retrieval_unit.structural_refs[0]
    assert sref.chapter_node_id == "CH_A"
    assert sref.knowledge_ids == ["KP_1"]
    assert sref.ability_ids == ["AP_1"]
    assert sref.chapter_name == "Chapter A"


def test_assemble_structural_refs_with_graph_snapshot_compat():
    """assemble_structural_refs(twin, graph_snapshot=...) works and matches no-graph_snapshot result."""
    asm = _make_assembler(
        chapter_knowledge_map={"CH_A": ["KP_1"]},
        knowledge_to_ability_map={"KP_1": ["AP_1"]},
        chapter_names={"CH_A": "Chapter A"},
    )
    twin = _make_twin_state(chapter_ids=["CH_A"], knowledge_ids=["KP_1"], ability_ids=["AP_1"])
    refs_no_graph = asm.assemble_structural_refs(twin)
    refs_with_graph = asm.assemble_structural_refs(
        twin,
        graph_snapshot=GraphSnapshot(snapshot_id="snap_1", created_at=datetime.now().isoformat(), version="1.0"),
    )
    assert len(refs_with_graph) == len(refs_no_graph)
    assert refs_with_graph[0].chapter_node_id == refs_no_graph[0].chapter_node_id
    assert refs_with_graph[0].knowledge_ids == refs_no_graph[0].knowledge_ids
    assert refs_with_graph[0].ability_ids == refs_no_graph[0].ability_ids


def test_explicit_empty_maps_same_as_absent():
    """Explicit empty maps {} behave the same as absent maps and yield [] for knowledge_ids/ability_ids."""
    asm_no_map = _make_assembler()
    asm_empty_map = _make_assembler(
        chapter_knowledge_map={},
        knowledge_to_ability_map={},
    )
    twin = _make_twin_state(chapter_ids=["CH_A"], knowledge_ids=["KP_1"], ability_ids=["AP_1"])
    refs_no_map = asm_no_map.assemble_structural_refs(twin)
    refs_empty_map = asm_empty_map.assemble_structural_refs(twin)
    assert len(refs_no_map) == 1
    assert len(refs_empty_map) == 1
    assert refs_no_map[0].knowledge_ids == []
    assert refs_no_map[0].ability_ids == []
    assert refs_empty_map[0].knowledge_ids == refs_no_map[0].knowledge_ids
    assert refs_empty_map[0].ability_ids == refs_no_map[0].ability_ids


# ---------------------------------------------------------------------------
# CLI runner
# ---------------------------------------------------------------------------

CASES = [
    test_mapped_scoping,
    test_empty_fallback_when_no_maps,
    test_partial_coverage,
    test_missing_knowledge_in_ability_map,
    test_assemble_current_state_unchanged,
    test_assemble_key_events_unchanged,
    test_full_assemble_with_maps,
    test_assemble_structural_refs_with_graph_snapshot_compat,
    test_explicit_empty_maps_same_as_absent,
]


def main():
    passed = 0
    failed = 0
    for case in CASES:
        ok, msg = _run_case(case)
        status = "PASS" if ok else "FAIL"
        print(f"  [{status}] {case.__name__}: {msg}")
        if ok:
            passed += 1
        else:
            failed += 1
    print(f"\nResults: {passed} passed, {failed} failed, {len(CASES)} total")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
