#!/usr/bin/env python3
"""ISSUE-005: Tests for batch write logging create/update detection."""

from __future__ import annotations

import sys
from pathlib import Path

repo_root = Path(__file__).resolve().parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from datetime import datetime

from app.models.graph_models import GraphEdge, KnowledgeNode, StudentNode
from app.models.graph_writer import GraphWriter, InMemoryGraphStore


def _make_store():
    return InMemoryGraphStore()


def _make_writer(store=None):
    if store is None:
        store = _make_store()
    return GraphWriter(store)


def _make_node(nid="N1", node_type="knowledge"):
    now = datetime.now().isoformat()
    return KnowledgeNode(
        node_id=nid,
        node_type=node_type,
        created_at=now,
        updated_at=now,
        properties={"mastery_level": 0.5},
    )


def _make_edge(eid="E1", source="N1", target="N2"):
    now = datetime.now().isoformat()
    return GraphEdge(
        edge_id=eid,
        source_node_id=source,
        target_node_id=target,
        edge_type="knows",
        created_at=now,
    )


def _run_case(test_func) -> tuple[bool, str]:
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

def test_batch_all_creates() -> None:
    """First batch write: all entities should be logged as create."""
    w = _make_writer()
    n1 = _make_node("N1")
    n2 = _make_node("N2")
    e1 = _make_edge("E1", "N1", "N2")

    w.write_nodes_and_edges([n1, n2], [e1])

    entries = w.get_write_log(limit=10)
    assert len(entries) == 3, f"expected 3 entries, got {len(entries)}"

    node_entries = [e for e in entries if e.entity_type == "node"]
    edge_entries = [e for e in entries if e.entity_type == "edge"]

    assert len(node_entries) == 2
    assert len(edge_entries) == 1

    for ne in node_entries:
        assert ne.operation == "create", f"node {ne.entity_id} should be create, got {ne.operation}"

    for ee in edge_entries:
        assert ee.operation == "create", f"edge {ee.entity_id} should be create, got {ee.operation}"


def test_batch_all_updates() -> None:
    """Second batch write with same IDs: all entities should be logged as update."""
    w = _make_writer()
    n1 = _make_node("N1")
    e1 = _make_edge("E1", "N1", "N2")

    # First batch: creates
    w.write_nodes_and_edges([n1], [e1])

    # Second batch: same IDs with changed properties -> updates
    n1_v2 = _make_node("N1")
    n1_v2.properties["mastery_level"] = 0.8
    e1_v2 = _make_edge("E1", "N1", "N2")

    w.write_nodes_and_edges([n1_v2], [e1_v2])

    entries = w.get_write_log(limit=10)
    assert len(entries) == 4, f"expected 4 entries, got {len(entries)}"

    # First 2 entries are from first batch (create)
    assert entries[0].operation == "create"
    assert entries[1].operation == "create"

    # Second batch (2 entries) should both be update
    assert entries[2].operation == "update", f"expected update, got {entries[2].operation}"
    assert entries[3].operation == "update", f"expected update, got {entries[3].operation}"


def test_batch_mixed_create_and_update() -> None:
    """Batch with both new and existing entities: mixed operations."""
    w = _make_writer()
    n1 = _make_node("N1")
    n2 = _make_node("N2")
    e1 = _make_edge("E1", "N1", "N2")

    # First batch: create N1, N2, E1
    w.write_nodes_and_edges([n1, n2], [e1])

    # Second batch: update N1, create N3, create E2 (N2 not in this batch)
    n1_v2 = _make_node("N1")
    n3 = _make_node("N3")
    e2 = _make_edge("E2", "N1", "N3")

    w.write_nodes_and_edges([n1_v2, n3], [e2])

    entries = w.get_write_log(limit=10)
    assert len(entries) == 6, f"expected 6 entries, got {len(entries)}"

    # Second batch entries: indices 3, 4 (nodes), 5 (edges)
    # Node N1 should be update, N3 should be create
    node_entries_2nd = entries[3:5]
    assert node_entries_2nd[0].entity_id == "N1"
    assert node_entries_2nd[0].operation == "update", f"N1 should be update, got {node_entries_2nd[0].operation}"
    assert node_entries_2nd[1].entity_id == "N3"
    assert node_entries_2nd[1].operation == "create", f"N3 should be create, got {node_entries_2nd[1].operation}"

    # Edge E2 should be create
    edge_entries_2nd = entries[5:6]
    assert edge_entries_2nd[0].entity_id == "E2"
    assert edge_entries_2nd[0].operation == "create"


def test_batch_edge_update_node_create() -> None:
    """Existing edge update + new node create in same batch."""
    w = _make_writer()
    n1 = _make_node("N1")
    n2 = _make_node("N2")
    e1 = _make_edge("E1", "N1", "N2")

    w.write_nodes_and_edges([n1, n2], [e1])

    # Second batch: update E1 + create N3
    e1_v2 = _make_edge("E1", "N1", "N2")
    n3 = _make_node("N3")

    w.write_nodes_and_edges([n3], [e1_v2])

    entries = w.get_write_log(limit=10)
    assert len(entries) == 5

    # Last 2 entries from second batch: node N3 (create), edge E1 (update)
    assert entries[3].entity_id == "N3"
    assert entries[3].operation == "create"
    assert entries[4].entity_id == "E1"
    assert entries[4].operation == "update"


def test_batch_empty_lists() -> None:
    """Empty batch should produce no log entries."""
    w = _make_writer()
    w.write_nodes_and_edges([], [])

    entries = w.get_write_log(limit=10)
    assert len(entries) == 0


def test_batch_single_write_paths_unchanged() -> None:
    """Regression: single write_node and write_edge still detect create/update."""
    w = _make_writer()
    n1 = _make_node("N1")

    # Single create
    w.write_node(n1)
    assert w.get_write_log(limit=10)[0].operation == "create"

    # Single update
    n1_v2 = _make_node("N1")
    w.write_node(n1_v2)
    assert w.get_write_log(limit=10)[1].operation == "update"

    # Single edge create
    e1 = _make_edge("E1", "N1", "N2")
    w.write_edge(e1)
    assert w.get_write_log(limit=10)[2].operation == "create"

    # Single edge update
    e1_v2 = _make_edge("E1", "N1", "N2")
    w.write_edge(e1_v2)
    assert w.get_write_log(limit=10)[3].operation == "update"


# ---------------------------------------------------------------------------
# CLI runner
# ---------------------------------------------------------------------------

CASES = [
    test_batch_all_creates,
    test_batch_all_updates,
    test_batch_mixed_create_and_update,
    test_batch_edge_update_node_create,
    test_batch_empty_lists,
    test_batch_single_write_paths_unchanged,
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
    sys.exit(main())
