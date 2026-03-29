"""GRAPH minimal object models for knowledge graph storage."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class GraphNode:
    """Base node in the knowledge graph."""

    node_id: str
    node_type: str  # "student", "knowledge", "ability", "chapter", "event"
    created_at: str
    updated_at: str
    properties: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize node to dictionary."""
        return {
            "node_id": self.node_id,
            "node_type": self.node_type,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "properties": self.properties,
        }


@dataclass(frozen=True)
class GraphEdge:
    """Edge representing a relationship between two nodes."""

    edge_id: str
    source_node_id: str
    target_node_id: str
    edge_type: str  # "knows", "prerequisite", " masters", "assessed_by", "located_in"
    created_at: str
    properties: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize edge to dictionary."""
        return {
            "edge_id": self.edge_id,
            "source_node_id": self.source_node_id,
            "target_node_id": self.target_node_id,
            "edge_type": self.edge_type,
            "created_at": self.created_at,
            "properties": self.properties,
        }


@dataclass(frozen=True)
class StudentNode(GraphNode):
    """Node representing a student in the graph."""

    def __post_init__(self) -> None:
        if self.node_type != "student":
            raise ValueError("StudentNode must have node_type 'student'")


@dataclass(frozen=True)
class KnowledgeNode(GraphNode):
    """Node representing a knowledge point in the graph."""

    def __post_init__(self) -> None:
        if self.node_type != "knowledge":
            raise ValueError("KnowledgeNode must have node_type 'knowledge'")

    @property
    def knowledge_id(self) -> str:
        return self.node_id

    @property
    def mastery_level(self) -> float | None:
        return self.properties.get("mastery_level")


@dataclass(frozen=True)
class AbilityNode(GraphNode):
    """Node representing an ability in the graph."""

    def __post_init__(self) -> None:
        if self.node_type != "ability":
            raise ValueError("AbilityNode must have node_type 'ability'")

    @property
    def ability_id(self) -> str:
        return self.node_id

    @property
    def ability_level(self) -> float | None:
        return self.properties.get("ability_level")


@dataclass(frozen=True)
class ChapterNode(GraphNode):
    """Node representing a chapter in the graph."""

    def __post_init__(self) -> None:
        if self.node_type != "chapter":
            raise ValueError("ChapterNode must have node_type 'chapter'")

    @property
    def chapter_node_id(self) -> str:
        return self.node_id

    @property
    def coverage(self) -> float | None:
        return self.properties.get("coverage")


@dataclass(frozen=True)
class EventNode(GraphNode):
    """Node representing a learning event in the graph."""

    def __post_init__(self) -> None:
        if self.node_type != "event":
            raise ValueError("EventNode must have node_type 'event'")

    @property
    def event_id(self) -> str:
        return self.node_id

    @property
    def event_status(self) -> str | None:
        return self.properties.get("event_status")


@dataclass
class GraphSnapshot:
    """
    Snapshot of the entire graph state at a point in time.

    Used for versioning, backup, and temporal queries.
    """

    snapshot_id: str
    created_at: str
    version: str
    nodes: dict[str, GraphNode] = field(default_factory=dict)
    edges: dict[str, GraphEdge] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def add_node(self, node: GraphNode) -> None:
        """Add or update a node in the snapshot."""
        self.nodes[node.node_id] = node

    def remove_node(self, node_id: str) -> None:
        """Remove a node from the snapshot."""
        self.nodes.pop(node_id, None)

    def add_edge(self, edge: GraphEdge) -> None:
        """Add or update an edge in the snapshot."""
        self.edges[edge.edge_id] = edge

    def remove_edge(self, edge_id: str) -> None:
        """Remove an edge from the snapshot."""
        self.edges.pop(edge_id, None)

    def get_neighbors(self, node_id: str, direction: str = "both") -> list[str]:
        """Get IDs of nodes connected to the given node."""
        neighbors = set()
        for edge in self.edges.values():
            if direction in ("both", "out"):
                if edge.source_node_id == node_id:
                    neighbors.add(edge.target_node_id)
            if direction in ("both", "in"):
                if edge.target_node_id == node_id:
                    neighbors.add(edge.source_node_id)
        return list(neighbors)

    def to_dict(self) -> dict[str, Any]:
        """Serialize snapshot to dictionary."""
        return {
            "snapshot_id": self.snapshot_id,
            "created_at": self.created_at,
            "version": self.version,
            "nodes": {nid: node.to_dict() for nid, node in self.nodes.items()},
            "edges": {eid: edge.to_dict() for eid, edge in self.edges.items()},
            "metadata": self.metadata,
        }


@dataclass
class GraphQueryResult:
    """Result of a graph query operation."""

    success: bool
    nodes: list[GraphNode] = field(default_factory=list)
    edges: list[GraphEdge] = field(default_factory=list)
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize query result to dictionary."""
        return {
            "success": self.success,
            "nodes": [n.to_dict() for n in self.nodes],
            "edges": [e.to_dict() for e in self.edges],
            "error": self.error,
        }
