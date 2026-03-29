"""GRAPH minimal write chain for persisting graph state."""

from __future__ import annotations

import copy
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Protocol

from app.models.graph_models import (
    AbilityNode,
    ChapterNode,
    EventNode,
    GraphEdge,
    GraphNode,
    GraphQueryResult,
    GraphSnapshot,
    KnowledgeNode,
    StudentNode,
)


class GraphStore(Protocol):
    """Protocol for graph persistence layer."""

    def save_snapshot(self, snapshot: GraphSnapshot) -> None:
        """Save a graph snapshot."""
        ...

    def load_snapshot(self, snapshot_id: str) -> GraphSnapshot | None:
        """Load a graph snapshot."""
        ...

    def get_latest_snapshot(self) -> GraphSnapshot | None:
        """Get the most recent snapshot."""
        ...


@dataclass
class WriteResult:
    """Result of a graph write operation."""

    success: bool
    snapshot_id: str | None = None
    nodes_written: int = 0
    edges_written: int = 0
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize write result to dictionary."""
        return {
            "success": self.success,
            "snapshot_id": self.snapshot_id,
            "nodes_written": self.nodes_written,
            "edges_written": self.edges_written,
            "error": self.error,
        }


@dataclass
class WriteLogEntry:
    """Single entry in the write log."""

    log_id: str
    timestamp: str
    operation: str  # "create", "update", "delete"
    entity_type: str  # "node" or "edge"
    entity_id: str
    snapshot_id: str
    trace_id: str | None = None


@dataclass
class WriteLog:
    """Log of all write operations."""

    entries: list[WriteLogEntry] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def add_entry(
        self,
        operation: str,
        entity_type: str,
        entity_id: str,
        snapshot_id: str,
        trace_id: str | None = None,
    ) -> None:
        """Add a write log entry."""
        self.entries.append(
            WriteLogEntry(
                log_id=f"WRL_{uuid.uuid4().hex[:12].upper()}",
                timestamp=datetime.now().isoformat(),
                operation=operation,
                entity_type=entity_type,
                entity_id=entity_id,
                snapshot_id=snapshot_id,
                trace_id=trace_id,
            )
        )

    def get_recent_entries(self, limit: int = 100) -> list[WriteLogEntry]:
        """Get recent write log entries."""
        return self.entries[-limit:]


class InMemoryGraphStore:
    """
    Simple in-memory implementation of GraphStore.

    For production use, replace with a persistent store (Neo4j, etc.)
    """

    def __init__(self, storage_path: str | None = None):
        self.snapshots: dict[str, GraphSnapshot] = {}
        self.storage_path = Path(storage_path) if storage_path else None
        if self.storage_path:
            self.storage_path.mkdir(parents=True, exist_ok=True)

    def save_snapshot(self, snapshot: GraphSnapshot) -> None:
        """Save a graph snapshot."""
        self.snapshots[snapshot.snapshot_id] = snapshot
        if self.storage_path:
            filepath = self.storage_path / f"{snapshot.snapshot_id}.json"
            filepath.write_text(json.dumps(snapshot.to_dict(), ensure_ascii=False, indent=2))

    def load_snapshot(self, snapshot_id: str) -> GraphSnapshot | None:
        """Load a graph snapshot by ID."""
        if snapshot_id in self.snapshots:
            return self.snapshots[snapshot_id]
        if self.storage_path:
            filepath = self.storage_path / f"{snapshot_id}.json"
            if filepath.exists():
                data = json.loads(filepath.read_text(encoding="utf-8"))
                return self._dict_to_snapshot(data)
        return None

    def get_latest_snapshot(self) -> GraphSnapshot | None:
        """Get the most recent snapshot."""
        if not self.snapshots:
            if self.storage_path:
                json_files = sorted(self.storage_path.glob("*.json"))
                if json_files:
                    latest_file = json_files[-1]
                    data = json.loads(latest_file.read_text(encoding="utf-8"))
                    return self._dict_to_snapshot(data)
            return None
        latest_id = max(self.snapshots.keys())
        return self.snapshots[latest_id]

    def _dict_to_snapshot(self, data: dict[str, Any]) -> GraphSnapshot:
        """Convert dictionary to GraphSnapshot."""
        snapshot = GraphSnapshot(
            snapshot_id=data["snapshot_id"],
            created_at=data["created_at"],
            version=data.get("version", "1.0.0"),
            metadata=data.get("metadata", {}),
        )
        for nid, node_data in data.get("nodes", {}).items():
            node = self._dict_to_node(node_data)
            if node:
                snapshot.nodes[nid] = node
        for eid, edge_data in data.get("edges", {}).items():
            edge = GraphEdge(
                edge_id=edge_data["edge_id"],
                source_node_id=edge_data["source_node_id"],
                target_node_id=edge_data["target_node_id"],
                edge_type=edge_data["edge_type"],
                created_at=edge_data["created_at"],
                properties=edge_data.get("properties", {}),
            )
            snapshot.edges[eid] = edge
        return snapshot

    def _dict_to_node(self, data: dict[str, Any]) -> GraphNode | None:
        """Convert dictionary to appropriate GraphNode subclass."""
        node_type = data.get("node_type")
        if node_type == "student":
            return StudentNode(
                node_id=data["node_id"],
                node_type=node_type,
                created_at=data["created_at"],
                updated_at=data["updated_at"],
                properties=data.get("properties", {}),
            )
        elif node_type == "knowledge":
            return KnowledgeNode(
                node_id=data["node_id"],
                node_type=node_type,
                created_at=data["created_at"],
                updated_at=data["updated_at"],
                properties=data.get("properties", {}),
            )
        elif node_type == "ability":
            return AbilityNode(
                node_id=data["node_id"],
                node_type=node_type,
                created_at=data["created_at"],
                updated_at=data["updated_at"],
                properties=data.get("properties", {}),
            )
        elif node_type == "chapter":
            return ChapterNode(
                node_id=data["node_id"],
                node_type=node_type,
                created_at=data["created_at"],
                updated_at=data["updated_at"],
                properties=data.get("properties", {}),
            )
        elif node_type == "event":
            return EventNode(
                node_id=data["node_id"],
                node_type=node_type,
                created_at=data["created_at"],
                updated_at=data["updated_at"],
                properties=data.get("properties", {}),
            )
        return None


class GraphWriter:
    """
    Minimal write chain for updating the knowledge graph.

    Handles:
    1. Loading current snapshot
    2. Applying node/edge changes
    3. Creating new snapshot
    4. Logging write operations
    """

    def __init__(self, store: GraphStore):
        self.store = store
        self.write_log = WriteLog()
        self._current_snapshot: GraphSnapshot | None = None

    def get_current_snapshot(self) -> GraphSnapshot | None:
        """Get current working snapshot."""
        if self._current_snapshot is None:
            self._current_snapshot = self.store.get_latest_snapshot()
            if self._current_snapshot is None:
                self._current_snapshot = self._create_initial_snapshot()
        return self._current_snapshot

    def _create_initial_snapshot(self) -> GraphSnapshot:
        """Create initial empty snapshot."""
        now = datetime.now().isoformat()
        return GraphSnapshot(
            snapshot_id="SNP_000000000001",
            created_at=now,
            version="1.0.0",
            metadata={"description": "Initial empty snapshot"},
        )

    def _generate_snapshot_id(self) -> str:
        """Generate next snapshot ID."""
        current = self.get_current_snapshot()
        if current is None:
            return "SNP_000000000001"
        try:
            current_num = int(current.snapshot_id.split("_")[1])
            next_num = current_num + 1
            return f"SNP_{next_num:012d}"
        except (ValueError, IndexError):
            return f"SNP_{uuid.uuid4().hex[:12].upper()}"

    def write_node(
        self,
        node: GraphNode,
        trace_id: str | None = None,
    ) -> WriteResult:
        """Write a node to the graph."""
        snapshot = self.get_current_snapshot()
        old_node = snapshot.nodes.get(node.node_id)

        operation = "update" if old_node else "create"

        # Create new snapshot ID before modifying
        new_snapshot_id = self._generate_snapshot_id()

        # Create a deep copy of the snapshot to avoid modifying previous snapshots
        snapshot = copy.deepcopy(snapshot)
        snapshot.snapshot_id = new_snapshot_id
        snapshot.updated_at = datetime.now().isoformat()

        snapshot.add_node(node)

        self.store.save_snapshot(snapshot)
        self._current_snapshot = snapshot

        self.write_log.add_entry(
            operation=operation,
            entity_type="node",
            entity_id=node.node_id,
            snapshot_id=new_snapshot_id,
            trace_id=trace_id,
        )

        return WriteResult(
            success=True,
            snapshot_id=new_snapshot_id,
            nodes_written=1,
        )

    def write_edge(
        self,
        edge: GraphEdge,
        trace_id: str | None = None,
    ) -> WriteResult:
        """Write an edge to the graph."""
        snapshot = self.get_current_snapshot()
        old_edge = snapshot.edges.get(edge.edge_id)

        operation = "update" if old_edge else "create"

        # Create new snapshot ID before modifying
        new_snapshot_id = self._generate_snapshot_id()

        # Create a deep copy of the snapshot to avoid modifying previous snapshots
        snapshot = copy.deepcopy(snapshot)
        snapshot.snapshot_id = new_snapshot_id
        snapshot.updated_at = datetime.now().isoformat()

        snapshot.add_edge(edge)

        self.store.save_snapshot(snapshot)
        self._current_snapshot = snapshot

        self.write_log.add_entry(
            operation=operation,
            entity_type="edge",
            entity_id=edge.edge_id,
            snapshot_id=new_snapshot_id,
            trace_id=trace_id,
        )

        return WriteResult(
            success=True,
            snapshot_id=new_snapshot_id,
            edges_written=1,
        )

    def write_nodes_and_edges(
        self,
        nodes: list[GraphNode],
        edges: list[GraphEdge],
        trace_id: str | None = None,
    ) -> WriteResult:
        """Write multiple nodes and edges atomically."""
        snapshot = self.get_current_snapshot()

        # Create new snapshot ID before modifying
        new_snapshot_id = self._generate_snapshot_id()

        # Create a deep copy of the snapshot to avoid modifying previous snapshots
        snapshot = copy.deepcopy(snapshot)
        snapshot.snapshot_id = new_snapshot_id
        snapshot.updated_at = datetime.now().isoformat()

        for node in nodes:
            snapshot.add_node(node)
        for edge in edges:
            snapshot.add_edge(edge)

        self.store.save_snapshot(snapshot)
        self._current_snapshot = snapshot

        for node in nodes:
            self.write_log.add_entry(
                operation="create",
                entity_type="node",
                entity_id=node.node_id,
                snapshot_id=new_snapshot_id,
                trace_id=trace_id,
            )
        for edge in edges:
            self.write_log.add_entry(
                operation="create",
                entity_type="edge",
                entity_id=edge.edge_id,
                snapshot_id=new_snapshot_id,
                trace_id=trace_id,
            )

        return WriteResult(
            success=True,
            snapshot_id=new_snapshot_id,
            nodes_written=len(nodes),
            edges_written=len(edges),
        )

    def query_nodes(self, node_type: str | None = None) -> GraphQueryResult:
        """Query nodes, optionally filtered by type."""
        snapshot = self.get_current_snapshot()
        nodes = list(snapshot.nodes.values())
        if node_type:
            nodes = [n for n in nodes if n.node_type == node_type]
        return GraphQueryResult(success=True, nodes=nodes)

    def query_edges(
        self,
        edge_type: str | None = None,
        source_node_id: str | None = None,
        target_node_id: str | None = None,
    ) -> GraphQueryResult:
        """Query edges with optional filters."""
        snapshot = self.get_current_snapshot()
        edges = list(snapshot.edges.values())

        if edge_type:
            edges = [e for e in edges if e.edge_type == edge_type]
        if source_node_id:
            edges = [e for e in edges if e.source_node_id == source_node_id]
        if target_node_id:
            edges = [e for e in edges if e.target_node_id == target_node_id]

        return GraphQueryResult(success=True, edges=edges)

    def get_write_log(self, limit: int = 100) -> list[WriteLogEntry]:
        """Get recent write log entries."""
        return self.write_log.get_recent_entries(limit)
