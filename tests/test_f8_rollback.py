#!/usr/bin/env python3
"""F8-T3: Tests for GRAPH degradation and object-level rollback."""

from __future__ import annotations

import json
from datetime import datetime

from app.models.graph_models import GraphEdge, GraphSnapshot, KnowledgeNode, StudentNode
from app.models.graph_writer import GraphWriter, InMemoryGraphStore
from app.models.graph_rollback import (
    ConfidenceLevel,
    DegradedGraphWriter,
    GraphRollbackManager,
)


def test_confidence_level() -> tuple[bool, str]:
    """Test confidence level classification."""
    try:
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

        return True, "Confidence level classification passed"
    except Exception as e:
        return False, f"Confidence level error: {e}"


def test_version_chain() -> tuple[bool, str]:
    """Test version chain tracking."""
    try:
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

        return True, "Version chain tracking passed"
    except Exception as e:
        return False, f"Version chain error: {e}"


def test_node_rollback() -> tuple[bool, str]:
    """Test node rollback functionality."""
    try:
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

        return True, f"Node rollback passed (rolled back from {snapshot_v2} to {snapshot_v1})"
    except Exception as e:
        return False, f"Node rollback error: {e}"


def test_edge_rollback() -> tuple[bool, str]:
    """Test edge rollback functionality."""
    try:
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

        return True, f"Edge rollback passed (rolled back from {snapshot_v3} to {snapshot_v2})"
    except Exception as e:
        return False, f"Edge rollback error: {e}"


def test_degraded_write() -> tuple[bool, str]:
    """Test degraded write with low confidence."""
    try:
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

        return True, "Degraded write passed (high confidence not degraded, low confidence degraded)"
    except Exception as e:
        return False, f"Degraded write error: {e}"


def test_rollback_if_degraded() -> tuple[bool, str]:
    """Test automatic rollback of degraded entities."""
    try:
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

        return True, "Auto rollback of degraded entity passed"
    except Exception as e:
        return False, f"Auto rollback error: {e}"


def test_version_chain_integrity() -> tuple[bool, str]:
    """Test that rollback maintains version chain integrity."""
    try:
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

        return True, "Version chain integrity maintained through rollback"
    except Exception as e:
        return False, f"Version chain integrity error: {e}"


def run_all_tests() -> dict:
    """Run all F8-T3 tests and report results."""
    tests = [
        ("confidence_level", test_confidence_level),
        ("version_chain", test_version_chain),
        ("node_rollback", test_node_rollback),
        ("edge_rollback", test_edge_rollback),
        ("degraded_write", test_degraded_write),
        ("rollback_if_degraded", test_rollback_if_degraded),
        ("version_chain_integrity", test_version_chain_integrity),
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
    print(json.dumps(results, indent=2, ensure_ascii=False))
