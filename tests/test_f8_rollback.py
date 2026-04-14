#!/usr/bin/env python3
"""F8-T3: Tests for GRAPH degradation and object-level rollback."""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Add repository root to Python path for running tests from root directory
repo_root = Path(__file__).resolve().parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from datetime import datetime

from app.models.graph_models import GraphEdge, GraphSnapshot, KnowledgeNode, StudentNode
from app.models.graph_writer import GraphWriter, InMemoryGraphStore
from app.models.graph_rollback import (
    ConfidenceLevel,
    DegradedGraphWriter,
    GraphRollbackManager,
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


def test_confidence_level() -> None:
    """Test confidence level classification."""
    high = ConfidenceLevel.from_score(0.85)
    assert high.level == "high"
    assert high.score == 0.85

    medium = ConfidenceLevel.from_score(0.65)
    assert medium.level == "medium"
    assert medium.score == 0.65

    low = ConfidenceLevel.from_score(0.50)
    assert low.level == "low"
    assert low.score == 0.50

    unverified = ConfidenceLevel.from_score(0.30)
    assert unverified.level == "unverified"
    assert unverified.score == 0.30


def test_version_chain() -> None:
    """Test version chain tracking."""
    store = InMemoryGraphStore()
    manager = GraphRollbackManager(store)

    # Record multiple versions
    manager.record_version("node", "NODE_001", "SNP_001")
    manager.record_version("node", "NODE_001", "SNP_002")
    manager.record_version("node", "NODE_001", "SNP_003")

    chain = manager.get_version_chain("node", "NODE_001")
    assert chain is not None
    assert len(chain.version_history) == 3
    assert chain.version_history == ["SNP_001", "SNP_002", "SNP_003"]

    # Validate chain
    valid, message = chain.validate_chain()
    assert valid, message


def test_node_rollback() -> None:
    """Test node rollback functionality."""
    store = InMemoryGraphStore()
    writer = GraphWriter(store)
    manager = GraphRollbackManager(store)

    # Create initial node version 1
    node_v1 = KnowledgeNode(
        node_id="KP_001",
        node_type="knowledge",
        created_at="2026-03-26T10:00:00",
        updated_at="2026-03-26T10:00:00",
        properties={"name": "质点", "mastery_level": 0.5},
    )
    result1 = writer.write_node(node_v1, trace_id="TRC_001")
    assert result1.success
    manager.record_version("node", "KP_001", result1.snapshot_id)
    snapshot_v1 = result1.snapshot_id

    # Update to version 2
    node_v2 = KnowledgeNode(
        node_id="KP_001",
        node_type="knowledge",
        created_at="2026-03-26T10:00:00",
        updated_at="2026-03-26T11:00:00",
        properties={"name": "质点", "mastery_level": 0.8},
    )
    result2 = writer.write_node(node_v2, trace_id="TRC_002")
    assert result2.success
    manager.record_version("node", "KP_001", result2.snapshot_id)
    snapshot_v2 = result2.snapshot_id

    # Verify current state is v2
    current = store.get_latest_snapshot()
    assert current.nodes["KP_001"].mastery_level == 0.8

    # Rollback to v1
    rollback_result = manager.rollback_node("KP_001", snapshot_v1)
    assert rollback_result.success, rollback_result.error
    assert rollback_result.from_snapshot_id == snapshot_v2
    assert rollback_result.to_snapshot_id == snapshot_v1

    # Verify state is back to v1
    current = store.get_latest_snapshot()
    assert current.nodes["KP_001"].mastery_level == 0.5


def test_edge_rollback() -> None:
    """Test edge rollback functionality."""
    store = InMemoryGraphStore()
    writer = GraphWriter(store)
    manager = GraphRollbackManager(store)

    # Create nodes
    student = StudentNode(
        node_id="STU_001",
        node_type="student",
        created_at="2026-03-26T10:00:00",
        updated_at="2026-03-26T10:00:00",
        properties={"name": "测试学生"},
    )
    knowledge = KnowledgeNode(
        node_id="KP_001",
        node_type="knowledge",
        created_at="2026-03-26T10:00:00",
        updated_at="2026-03-26T10:00:00",
        properties={"name": "质点"},
    )
    result = writer.write_nodes_and_edges([student, knowledge], [], trace_id="TRC_001")
    assert result.success
    snapshot_v1 = result.snapshot_id

    # Create edge version 1
    edge_v1 = GraphEdge(
        edge_id="EDGE_001",
        source_node_id="STU_001",
        target_node_id="KP_001",
        edge_type="masters",
        created_at="2026-03-26T10:00:00",
        properties={"mastery_level": 0.5},
    )
    result1 = writer.write_edge(edge_v1, trace_id="TRC_002")
    assert result1.success
    manager.record_version("edge", "EDGE_001", result1.snapshot_id)
    snapshot_v2 = result1.snapshot_id

    # Update edge to version 2
    edge_v2 = GraphEdge(
        edge_id="EDGE_001",
        source_node_id="STU_001",
        target_node_id="KP_001",
        edge_type="masters",
        created_at="2026-03-26T10:00:00",
        properties={"mastery_level": 0.8},
    )
    result2 = writer.write_edge(edge_v2, trace_id="TRC_003")
    assert result2.success
    manager.record_version("edge", "EDGE_001", result2.snapshot_id)
    snapshot_v3 = result2.snapshot_id

    # Rollback edge to v1
    rollback_result = manager.rollback_edge("EDGE_001", snapshot_v2)
    assert rollback_result.success, rollback_result.error

    # Verify edge is back to v1
    current = store.get_latest_snapshot()
    assert current.edges["EDGE_001"].properties["mastery_level"] == 0.5


def test_degraded_write() -> None:
    """Test degraded write with low confidence."""
    store = InMemoryGraphStore()
    writer = DegradedGraphWriter(store)

    # High confidence write (should NOT be degraded)
    node_high = KnowledgeNode(
        node_id="KP_HIGH",
        node_type="knowledge",
        created_at="2026-03-26T10:00:00",
        updated_at="2026-03-26T10:00:00",
        properties={"name": "高置信度知识点"},
    )
    confidence_high = ConfidenceLevel(level="high", score=0.85)
    result, is_degraded = writer.write_node_with_confidence(node_high, confidence_high)
    assert result.success
    assert not is_degraded, "High confidence node should not be degraded"

    # Low confidence write (SHOULD be degraded)
    node_low = KnowledgeNode(
        node_id="KP_LOW",
        node_type="knowledge",
        created_at="2026-03-26T10:00:00",
        updated_at="2026-03-26T10:00:00",
        properties={"name": "低置信度知识点"},
    )
    confidence_low = ConfidenceLevel(level="low", score=0.45)
    result, is_degraded = writer.write_node_with_confidence(node_low, confidence_low)
    assert result.success
    assert is_degraded, "Low confidence node should be degraded"

    # Verify degradation record
    degraded = writer.rollback_manager.get_degraded("node", "KP_LOW")
    assert degraded is not None
    assert degraded.confidence.score == 0.45
    assert "Low confidence" in degraded.degradation_reason



def test_degraded_edge_write() -> None:
    """Test degraded edge write with low confidence.

    Regression: write_edge_with_confidence previously called mark_degraded
    with edge_id=... instead of entity_id=..., causing TypeError.
    """
    store = InMemoryGraphStore()
    writer = GraphWriter(store)

    # Create prerequisite nodes
    from app.models.graph_models import StudentNode, KnowledgeNode
    student = StudentNode(
        node_id="STU_EDGE_001", node_type="student",
        created_at="2026-03-26T10:00:00", updated_at="2026-03-26T10:00:00",
        properties={"name": "测试学生"})
    knowledge = KnowledgeNode(
        node_id="KP_EDGE_001", node_type="knowledge",
        created_at="2026-03-26T10:00:00", updated_at="2026-03-26T10:00:00",
        properties={"name": "知识点"})
    writer.write_nodes_and_edges([student, knowledge], [], trace_id="TRC_EDGE_SETUP")

    d_writer = DegradedGraphWriter(store)

    from app.models.graph_models import GraphEdge
    edge = GraphEdge(
        edge_id="EDGE_LOW_CONF",
        source_node_id="STU_EDGE_001",
        target_node_id="KP_EDGE_001",
        edge_type="masters",
        created_at="2026-03-26T10:00:00",
        properties={"mastery_level": 0.3},
    )
    confidence_low = ConfidenceLevel(level="low", score=0.35)

    # This used to raise TypeError: unexpected keyword argument 'edge_id'
    result, is_degraded = d_writer.write_edge_with_confidence(edge, confidence_low)
    assert result.success
    assert is_degraded, "Low confidence edge should be degraded"

    # Verify degradation record is retrievable by entity_type + entity_id
    degraded = d_writer.rollback_manager.get_degraded("edge", "EDGE_LOW_CONF")
    assert degraded is not None
    assert degraded.confidence.score == 0.35
    assert "Low confidence" in degraded.degradation_reason


def test_rollback_if_degraded() -> None:
    """Test automatic rollback of degraded entities."""
    store = InMemoryGraphStore()
    writer = DegradedGraphWriter(store)
    writer.set_degradation_threshold(0.6)

    # Initial write (high confidence)
    node_v1 = KnowledgeNode(
        node_id="KP_ROLLBACK",
        node_type="knowledge",
        created_at="2026-03-26T10:00:00",
        updated_at="2026-03-26T10:00:00",
        properties={"name": "初始状态", "mastery_level": 0.5},
    )
    confidence_high = ConfidenceLevel(level="high", score=0.85)
    result1, _ = writer.write_node_with_confidence(node_v1, confidence_high)
    assert result1.success
    snapshot_v1 = result1.snapshot_id

    # Low confidence update (will be degraded)
    node_v2 = KnowledgeNode(
        node_id="KP_ROLLBACK",
        node_type="knowledge",
        created_at="2026-03-26T10:00:00",
        updated_at="2026-03-26T11:00:00",
        properties={"name": "低置信更新", "mastery_level": 0.9},
    )
    confidence_low = ConfidenceLevel(level="low", score=0.40)
    result2, is_degraded = writer.write_node_with_confidence(node_v2, confidence_low)
    assert result2.success
    assert is_degraded

    # Verify current state is v2
    current = store.get_latest_snapshot()
    assert current.nodes["KP_ROLLBACK"].mastery_level == 0.9

    # Set rollback target to v1 using the setter method
    degraded = writer.rollback_manager.get_degraded("node", "KP_ROLLBACK")
    assert degraded is not None
    degraded.set_rollback_target(snapshot_v1)

    # Auto rollback
    rollback_result = writer.rollback_if_degraded("node", "KP_ROLLBACK")
    assert rollback_result is not None
    assert rollback_result.success, rollback_result.error

    # Verify state is back to v1
    current = store.get_latest_snapshot()
    assert current.nodes["KP_ROLLBACK"].mastery_level == 0.5
    assert current.nodes["KP_ROLLBACK"].properties["name"] == "初始状态"


def test_version_chain_integrity() -> None:
    """Test that rollback maintains version chain integrity."""
    store = InMemoryGraphStore()
    writer = GraphWriter(store)
    manager = GraphRollbackManager(store)

    # Create multiple versions
    for i in range(5):
        node = KnowledgeNode(
            node_id=f"KP_CHAIN_{i}",
            node_type="knowledge",
            created_at="2026-03-26T10:00:00",
            updated_at=f"2026-03-26T{10+i}:00:00",
            properties={"version": i, "mastery_level": 0.5 + i * 0.1},
        )
        result = writer.write_node(node, trace_id=f"TRC_{i}")
        manager.record_version("node", node.node_id, result.snapshot_id)

    # Perform rollback
    chain = manager.get_version_chain("node", "KP_CHAIN_0")
    if chain and len(chain.version_history) > 1:
        target = chain.version_history[0]
        rollback_result = manager.rollback_node("KP_CHAIN_0", target)
        assert rollback_result.success

    # Verify chain is still valid
    for i in range(5):
        chain = manager.get_version_chain("node", f"KP_CHAIN_{i}")
        if chain:
            valid, message = chain.validate_chain()
            assert valid, f"Chain validation failed for KP_CHAIN_{i}: {message}"




def test_rollback_if_degraded_auto() -> None:
    """Test automatic rollback of degraded entities without manual target setting.

    This is the core regression test: when rollback_target_snapshot_id is None,
    rollback_if_degraded must use the version chain to find the prior snapshot,
    NOT use the post-write snapshot as the target (which would be a no-op).
    """
    store = InMemoryGraphStore()
    writer = DegradedGraphWriter(store)
    writer.set_degradation_threshold(0.6)

    # Initial write (high confidence) - establishes version 1
    node_v1 = KnowledgeNode(
        node_id="KP_AUTO",
        node_type="knowledge",
        created_at="2026-03-26T10:00:00",
        updated_at="2026-03-26T10:00:00",
        properties={"name": "初始状态", "mastery_level": 0.5},
    )
    confidence_high = ConfidenceLevel(level="high", score=0.85)
    result1, is_degraded = writer.write_node_with_confidence(node_v1, confidence_high)
    assert result1.success
    assert not is_degraded

    # Low confidence update (will be degraded) - establishes version 2
    node_v2 = KnowledgeNode(
        node_id="KP_AUTO",
        node_type="knowledge",
        created_at="2026-03-26T10:00:00",
        updated_at="2026-03-26T11:00:00",
        properties={"name": "低置信更新", "mastery_level": 0.9},
    )
    confidence_low = ConfidenceLevel(level="low", score=0.40)
    result2, is_degraded = writer.write_node_with_confidence(node_v2, confidence_low)
    assert result2.success
    assert is_degraded

    # Verify current state is v2
    current = store.get_latest_snapshot()
    assert current.nodes["KP_AUTO"].mastery_level == 0.9

    # Do NOT set rollback_target_snapshot_id — this is the key difference
    degraded = writer.rollback_manager.get_degraded("node", "KP_AUTO")
    assert degraded is not None
    assert degraded.rollback_target_snapshot_id is None  # Not manually set

    # Auto rollback should find the prior snapshot via version chain
    rollback_result = writer.rollback_if_degraded("node", "KP_AUTO")
    assert rollback_result is not None
    assert rollback_result.success, rollback_result.error
    # Must NOT be a no-op: target should differ from the degraded snapshot
    assert rollback_result.to_snapshot_id != degraded.original_snapshot_id,         "Rollback target should not be the post-write snapshot (no-op)"

    # Verify state is back to v1
    current = store.get_latest_snapshot()
    assert current.nodes["KP_AUTO"].mastery_level == 0.5
    assert current.nodes["KP_AUTO"].properties["name"] == "初始状态"


def test_rollback_if_degraded_first_write_no_prior() -> None:
    """Test that degrading the very first write of an entity returns a clear error.

    When an entity has no prior snapshot (first write is degraded),
    rollback_if_degraded should fail with an explicit error, not silently succeed.
    """
    store = InMemoryGraphStore()
    writer = DegradedGraphWriter(store)
    writer.set_degradation_threshold(0.6)

    # Single low-confidence write — no prior snapshot exists
    node = KnowledgeNode(
        node_id="KP_FIRST",
        node_type="knowledge",
        created_at="2026-03-26T10:00:00",
        updated_at="2026-03-26T10:00:00",
        properties={"name": "孤立写入"},
    )
    confidence_low = ConfidenceLevel(level="low", score=0.35)
    result, is_degraded = writer.write_node_with_confidence(node, confidence_low)
    assert result.success
    assert is_degraded

    # Auto rollback should fail with clear error (no prior snapshot)
    rollback_result = writer.rollback_if_degraded("node", "KP_FIRST")
    assert rollback_result is not None
    assert rollback_result.success is False
    assert "No prior snapshot" in rollback_result.error


def run_all_tests() -> dict:
    """Run all F8-T3 tests and report results."""
    tests = [
        ("confidence_level", test_confidence_level),
        ("version_chain", test_version_chain),
        ("node_rollback", test_node_rollback),
        ("edge_rollback", test_edge_rollback),
        ("degraded_write", test_degraded_write),
        ("degraded_edge_write", test_degraded_edge_write),
        ("rollback_if_degraded", test_rollback_if_degraded),
        ("rollback_if_degraded_auto", test_rollback_if_degraded_auto),
        ("rollback_if_degraded_first_write_no_prior", test_rollback_if_degraded_first_write_no_prior),
        ("version_chain_integrity", test_version_chain_integrity),
    ]

    results = {name: _run_case(func) for name, func in tests}

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
    print(json.dumps(results, indent=2, ensure_ascii=False))


# ============== Pytest wrapper ==============
# Minimal pytest-compatible tests for CI integration

def test_f8_confidence_level():
    """F8-T3-C: Confidence level classification."""
    test_confidence_level()


def test_f8_version_chain():
    """F8-T3-V: Version chain tracking."""
    test_version_chain()


def test_f8_node_rollback():
    """F8-T3-N: Node rollback functionality."""
    test_node_rollback()


def test_f8_edge_rollback():
    """F8-T3-E: Edge rollback functionality."""
    test_edge_rollback()


def test_f8_degraded_write():
    """F8-T3-D: Degraded write with low confidence."""
    test_degraded_write()


def test_f8_rollback_if_degraded():
    """F8-T3-R: Automatic rollback of degraded entities."""
    test_rollback_if_degraded()


def test_f8_version_chain_integrity():
    """F8-T3-I: Version chain integrity through rollback."""
    test_version_chain_integrity()


def test_f8_rollback_if_degraded_auto():
    """F8-T3-A: Automatic rollback of degraded entities (no manual target)."""
    test_rollback_if_degraded_auto()


def test_f8_rollback_if_degraded_first_write_no_prior():
    """F8-T3-F: First-write degradation with no prior snapshot."""
    test_rollback_if_degraded_first_write_no_prior()

def test_f8_degraded_edge_write():
    """F8-T3-G: Degraded edge write with low confidence."""
    test_degraded_edge_write()


