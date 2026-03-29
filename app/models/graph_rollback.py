"""F8-T3: GRAPH degradation and object-level rollback."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Literal

from app.models.graph_models import GraphEdge, GraphNode, GraphSnapshot
from app.models.graph_writer import GraphStore, WriteLogEntry, WriteResult


@dataclass(frozen=True)
class ConfidenceLevel:
    """
    Confidence level for graph entities.

    Used to determine whether to solidify relationships or mark as weak.
    """

    level: Literal["high", "medium", "low", "unverified"]
    score: float  # 0.0 - 1.0
    reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "level": self.level,
            "score": self.score,
            "reason": self.reason,
        }

    @classmethod
    def from_score(cls, score: float) -> "ConfidenceLevel":
        """Create confidence level from numeric score."""
        if score >= 0.8:
            return cls(level="high", score=score)
        elif score >= 0.6:
            return cls(level="medium", score=score)
        elif score >= 0.4:
            return cls(level="low", score=score)
        else:
            return cls(level="unverified", score=score)


@dataclass(frozen=False)
class DegradedEntity:
    """Entity marked as degraded (weak/unverified)."""

    entity_type: str  # "node" or "edge"
    entity_id: str
    original_snapshot_id: str
    degraded_at: str
    degradation_reason: str
    confidence: ConfidenceLevel
    rollback_target_snapshot_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "original_snapshot_id": self.original_snapshot_id,
            "degraded_at": self.degraded_at,
            "degradation_reason": self.degradation_reason,
            "confidence": self.confidence.to_dict(),
            "rollback_target_snapshot_id": self.rollback_target_snapshot_id,
        }

    def set_rollback_target(self, snapshot_id: str) -> None:
        """Set the rollback target snapshot ID."""
        object.__setattr__(self, 'rollback_target_snapshot_id', snapshot_id)


@dataclass
class RollbackResult:
    """Result of a rollback operation."""

    success: bool
    entity_type: str  # "node" or "edge"
    entity_id: str
    from_snapshot_id: str
    to_snapshot_id: str
    rolled_back_at: str

    error: str | None = None
    affected_edges: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "from_snapshot_id": self.from_snapshot_id,
            "to_snapshot_id": self.to_snapshot_id,
            "rolled_back_at": self.rolled_back_at,
            "error": self.error,
            "affected_edges": self.affected_edges,
        }


@dataclass
class VersionChain:
    """
    Tracks version chain integrity for an entity.

    Ensures rollback doesn't break the version chain.
    """

    entity_type: str
    entity_id: str
    version_history: list[str] = field(default_factory=list)  # List of snapshot_ids
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def add_version(self, snapshot_id: str) -> None:
        """Record a new version."""
        self.version_history.append(snapshot_id)

    def get_previous_version(self, current_snapshot_id: str) -> str | None:
        """Get the previous version before current."""
        try:
            idx = self.version_history.index(current_snapshot_id)
            if idx > 0:
                return self.version_history[idx - 1]
        except ValueError:
            pass
        return None

    def validate_chain(self) -> tuple[bool, str]:
        """Validate version chain integrity."""
        if not self.version_history:
            return False, "Version history is empty"
        if len(self.version_history) != len(set(self.version_history)):
            return False, "Duplicate versions detected"
        return True, "Chain valid"


class GraphRollbackManager:
    """
    Manages object-level rollback operations.

    Features:
    1. Track version history per entity
    2. Rollback individual nodes/edges
    3. Protect version chain integrity
    """

    def __init__(self, store: GraphStore):
        self.store = store
        self._version_chains: dict[str, VersionChain] = {}
        self._degraded_entities: dict[str, DegradedEntity] = {}

    def _get_chain_key(self, entity_type: str, entity_id: str) -> str:
        """Generate key for version chain lookup."""
        return f"{entity_type}:{entity_id}"

    def record_version(
        self,
        entity_type: str,
        entity_id: str,
        snapshot_id: str,
    ) -> None:
        """Record a new version in the entity's version chain."""
        key = self._get_chain_key(entity_type, entity_id)
        if key not in self._version_chains:
            self._version_chains[key] = VersionChain(
                entity_type=entity_type,
                entity_id=entity_id,
            )
        self._version_chains[key].add_version(snapshot_id)

    def get_version_chain(self, entity_type: str, entity_id: str) -> VersionChain | None:
        """Get version chain for an entity."""
        key = self._get_chain_key(entity_type, entity_id)
        return self._version_chains.get(key)

    def rollback_node(
        self,
        node_id: str,
        target_snapshot_id: str,
        trace_id: str | None = None,
    ) -> RollbackResult:
        """
        Rollback a node to a previous version.

        Args:
            node_id: ID of node to rollback
            target_snapshot_id: Snapshot ID to rollback to
            trace_id: Optional trace ID for auditing

        Returns:
            RollbackResult with success status
        """
        now = datetime.now().isoformat()

        current_snapshot = self.store.get_latest_snapshot()
        if current_snapshot is None:
            return RollbackResult(
                success=False,
                entity_type="node",
                entity_id=node_id,
                from_snapshot_id="none",
                to_snapshot_id=target_snapshot_id,
                rolled_back_at=now,
                error="No current snapshot found",
            )

        target_snapshot = self.store.load_snapshot(target_snapshot_id)
        if target_snapshot is None:
            return RollbackResult(
                success=False,
                entity_type="node",
                entity_id=node_id,
                from_snapshot_id=current_snapshot.snapshot_id,
                to_snapshot_id=target_snapshot_id,
                rolled_back_at=now,
                error=f"Target snapshot {target_snapshot_id} not found",
            )

        if node_id not in target_snapshot.nodes:
            return RollbackResult(
                success=False,
                entity_type="node",
                entity_id=node_id,
                from_snapshot_id=current_snapshot.snapshot_id,
                to_snapshot_id=target_snapshot_id,
                rolled_back_at=now,
                error=f"Node {node_id} not found in target snapshot",
            )

        # Get the node from target snapshot
        restored_node = target_snapshot.nodes[node_id]

        # Create rollback snapshot
        rollback_snapshot = GraphSnapshot(
            snapshot_id=self._generate_rollback_snapshot_id(current_snapshot.snapshot_id),
            created_at=now,
            version=current_snapshot.version,
            nodes=dict(current_snapshot.nodes),
            edges=dict(current_snapshot.edges),
            metadata={
                **current_snapshot.metadata,
                "rollback": True,
                "rollback_entity_type": "node",
                "rollback_entity_id": node_id,
                "rollback_from": current_snapshot.snapshot_id,
                "rollback_to": target_snapshot_id,
                "trace_id": trace_id,
            },
        )

        # Apply restored node
        rollback_snapshot.nodes[node_id] = restored_node

        # Find affected edges (edges connected to this node)
        affected_edges = []
        for edge_id, edge in list(current_snapshot.edges.items()):
            if edge.source_node_id == node_id or edge.target_node_id == node_id:
                # Check if edge exists in target snapshot
                if edge_id in target_snapshot.edges:
                    rollback_snapshot.edges[edge_id] = target_snapshot.edges[edge_id]
                    affected_edges.append(edge_id)
                else:
                    # Edge doesn't exist in target, remove it
                    rollback_snapshot.edges.pop(edge_id, None)
                    affected_edges.append(edge_id)

        # Save rollback snapshot
        self.store.save_snapshot(rollback_snapshot)

        # Record version
        self.record_version("node", node_id, rollback_snapshot.snapshot_id)

        return RollbackResult(
            success=True,
            entity_type="node",
            entity_id=node_id,
            from_snapshot_id=current_snapshot.snapshot_id,
            to_snapshot_id=target_snapshot_id,
            rolled_back_at=now,
            affected_edges=affected_edges,
        )

    def rollback_edge(
        self,
        edge_id: str,
        target_snapshot_id: str,
        trace_id: str | None = None,
    ) -> RollbackResult:
        """
        Rollback an edge to a previous version.

        Args:
            edge_id: ID of edge to rollback
            target_snapshot_id: Snapshot ID to rollback to
            trace_id: Optional trace ID for auditing

        Returns:
            RollbackResult with success status
        """
        now = datetime.now().isoformat()

        current_snapshot = self.store.get_latest_snapshot()
        if current_snapshot is None:
            return RollbackResult(
                success=False,
                entity_type="edge",
                entity_id=edge_id,
                from_snapshot_id="none",
                to_snapshot_id=target_snapshot_id,
                rolled_back_at=now,
                error="No current snapshot found",
            )

        target_snapshot = self.store.load_snapshot(target_snapshot_id)
        if target_snapshot is None:
            return RollbackResult(
                success=False,
                entity_type="edge",
                entity_id=edge_id,
                from_snapshot_id=current_snapshot.snapshot_id,
                to_snapshot_id=target_snapshot_id,
                rolled_back_at=now,
                error=f"Target snapshot {target_snapshot_id} not found",
            )

        # Create rollback snapshot
        rollback_snapshot = GraphSnapshot(
            snapshot_id=self._generate_rollback_snapshot_id(current_snapshot.snapshot_id),
            created_at=now,
            version=current_snapshot.version,
            nodes=dict(current_snapshot.nodes),
            edges=dict(current_snapshot.edges),
            metadata={
                **current_snapshot.metadata,
                "rollback": True,
                "rollback_entity_type": "edge",
                "rollback_entity_id": edge_id,
                "rollback_from": current_snapshot.snapshot_id,
                "rollback_to": target_snapshot_id,
                "trace_id": trace_id,
            },
        )

        # Apply restored edge or remove if not in target
        if edge_id in target_snapshot.edges:
            rollback_snapshot.edges[edge_id] = target_snapshot.edges[edge_id]
        else:
            rollback_snapshot.edges.pop(edge_id, None)

        # Save rollback snapshot
        self.store.save_snapshot(rollback_snapshot)

        # Record version
        self.record_version("edge", edge_id, rollback_snapshot.snapshot_id)

        return RollbackResult(
            success=True,
            entity_type="edge",
            entity_id=edge_id,
            from_snapshot_id=current_snapshot.snapshot_id,
            to_snapshot_id=target_snapshot_id,
            rolled_back_at=now,
        )

    def mark_degraded(
        self,
        entity_type: str,
        entity_id: str,
        confidence: ConfidenceLevel,
        reason: str,
    ) -> DegradedEntity:
        """
        Mark an entity as degraded (weak/unverified).

        Degraded entities are flagged for review and can be rolled back.

        Args:
            entity_type: "node" or "edge"
            entity_id: Entity ID
            confidence: Confidence level
            reason: Reason for degradation

        Returns:
            DegradedEntity record
        """
        now = datetime.now().isoformat()
        current_snapshot = self.store.get_latest_snapshot()

        degraded = DegradedEntity(
            entity_type=entity_type,
            entity_id=entity_id,
            original_snapshot_id=current_snapshot.snapshot_id if current_snapshot else "none",
            degraded_at=now,
            degradation_reason=reason,
            confidence=confidence,
        )

        key = self._get_chain_key(entity_type, entity_id)
        self._degraded_entities[key] = degraded

        return degraded

    def get_degraded(self, entity_type: str, entity_id: str) -> DegradedEntity | None:
        """Get degradation record for an entity."""
        key = self._get_chain_key(entity_type, entity_id)
        return self._degraded_entities.get(key)

    def clear_degraded(self, entity_type: str, entity_id: str) -> bool:
        """Clear degradation flag for an entity."""
        key = self._get_chain_key(entity_type, entity_id)
        if key in self._degraded_entities:
            del self._degraded_entities[key]
            return True
        return False

    def list_degraded_entities(self) -> list[DegradedEntity]:
        """List all currently degraded entities."""
        return list(self._degraded_entities.values())

    def _generate_rollback_snapshot_id(self, current_snapshot_id: str) -> str:
        """Generate rollback snapshot ID that sorts after current snapshot.

        Uses 'ZRB_' prefix (Z sorts after S) followed by current snapshot number
        to ensure it sorts as the latest snapshot.
        """
        try:
            # Extract number from current snapshot ID (e.g., "SNP_000000000002" -> 2)
            if current_snapshot_id.startswith("SNP_"):
                current_num = int(current_snapshot_id.split("_")[1])
                # Use ZRB_ prefix which sorts after SNP_ and add large number
                next_num = current_num + 1000
                return f"ZRB_{next_num:012d}"
            elif current_snapshot_id.startswith("ZRB_"):
                current_num = int(current_snapshot_id.split("_")[1])
                next_num = current_num + 1
                return f"ZRB_{next_num:012d}"
        except (ValueError, IndexError):
            pass
        # Fallback to timestamp-based ID with ZRB prefix
        now = datetime.now().isoformat().replace("-", "").replace(":", "").replace(".", "")[:14]
        return f"ZRB_{now}"


class DegradedGraphWriter:
    """
    Graph writer that supports degradation and rollback.

    Wraps GraphWriter with degradation-aware logic.
    """

    def __init__(self, store: GraphStore):
        self.store = store
        self.rollback_manager = GraphRollbackManager(store)
        self._degraded_threshold = 0.6  # Entities below this confidence are degraded

    def set_degradation_threshold(self, threshold: float) -> None:
        """Set confidence threshold for degradation."""
        self._degraded_threshold = threshold

    def write_node_with_confidence(
        self,
        node: GraphNode,
        confidence: ConfidenceLevel,
        trace_id: str | None = None,
    ) -> tuple[WriteResult, bool]:
        """
        Write a node with confidence level.

        Low confidence nodes are marked as degraded instead of solidified.

        Args:
            node: Node to write
            confidence: Confidence level
            trace_id: Optional trace ID

        Returns:
            Tuple of (WriteResult, is_degraded)
        """
        is_degraded = confidence.score < self._degraded_threshold

        # Write the node normally
        from app.models.graph_writer import GraphWriter
        writer = GraphWriter(self.store)
        result = writer.write_node(node, trace_id)

        # Record version for rollback capability
        if result.success:
            self.rollback_manager.record_version("node", node.node_id, result.snapshot_id)

            # Mark as degraded if low confidence
            if is_degraded:
                self.rollback_manager.mark_degraded(
                    entity_type="node",
                    entity_id=node.node_id,
                    confidence=confidence,
                    reason=f"Low confidence write (score={confidence.score})",
                )

        return result, is_degraded

    def write_edge_with_confidence(
        self,
        edge: GraphEdge,
        confidence: ConfidenceLevel,
        trace_id: str | None = None,
    ) -> tuple[WriteResult, bool]:
        """
        Write an edge with confidence level.

        Low confidence edges are marked as degraded instead of solidified.

        Args:
            edge: Edge to write
            confidence: Confidence level
            trace_id: Optional trace ID

        Returns:
            Tuple of (WriteResult, is_degraded)
        """
        is_degraded = confidence.score < self._degraded_threshold

        # Write the edge normally
        from app.models.graph_writer import GraphWriter
        writer = GraphWriter(self.store)
        result = writer.write_edge(edge, trace_id)

        # Record version for rollback capability
        if result.success:
            self.rollback_manager.record_version("edge", edge.edge_id, result.snapshot_id)

            # Mark as degraded if low confidence
            if is_degraded:
                self.rollback_manager.mark_degraded(
                    entity_type="edge",
                    edge_id=edge.edge_id,
                    confidence=confidence,
                    reason=f"Low confidence write (score={confidence.score})",
                )

        return result, is_degraded

    def rollback_if_degraded(
        self,
        entity_type: str,
        entity_id: str,
    ) -> RollbackResult | None:
        """
        Automatically rollback a degraded entity.

        Args:
            entity_type: "node" or "edge"
            entity_id: Entity ID

        Returns:
            RollbackResult if rollback was performed, None if not degraded
        """
        degraded = self.rollback_manager.get_degraded(entity_type, entity_id)
        if degraded is None:
            return None

        # Find the snapshot before degradation
        target_snapshot_id = degraded.rollback_target_snapshot_id
        if target_snapshot_id is None:
            # Use the original snapshot as rollback target
            target_snapshot_id = degraded.original_snapshot_id

        if entity_type == "node":
            return self.rollback_manager.rollback_node(entity_id, target_snapshot_id)
        else:
            return self.rollback_manager.rollback_edge(entity_id, target_snapshot_id)
