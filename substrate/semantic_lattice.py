"""
substrate/semantic_lattice.py

Semantic lattice — evolving graph topology over the vector memory space.

Not:
    memory = list

But:
    memory = evolving manifold

The lattice is a directed graph where:
  - Nodes are vector keys (from VectorSpace)
  - Edges connect semantically similar vectors (cosine similarity > threshold)
  - Edge weights represent semantic proximity
  - Node centrality identifies conceptual gravity wells
  - Graph topology encodes the conceptual landscape

This is the substrate for:
  - Concept emergence (high-centrality nodes = semantic attractors)
  - Semantic curvature (local density = conceptual depth)
  - Path-based reasoning (traversal = analogical inference)
  - Centrality signal relay back to symbolic ecology

Architecture
------------
  Incremental edge building: new vectors are connected to their k-nearest
  neighbors in VectorSpace. The graph grows as the system processes input.

  Centrality is computed on demand (PageRank or degree-based).
  High-centrality nodes relay signals to generator.update_centrality().
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

import numpy as np
import networkx as nx


class SemanticLattice:
    """
    Evolving semantic graph topology.

    Parameters
    ----------
    similarity_threshold : float
        Minimum cosine similarity to form an edge between two nodes.
    k_neighbors : int
        Number of nearest neighbors to connect when adding a node.
    max_nodes : int or None
        Maximum graph size. Oldest low-centrality nodes pruned when exceeded.
    edge_decay : float
        Per-step weight decay applied to all edges.
    centrality_relay_top_n : int
        Number of top-centrality nodes to relay signals for per emit call.
    """

    def __init__(
        self,
        similarity_threshold:   float = 0.75,
        k_neighbors:            int   = 5,
        max_nodes:              Optional[int] = 2048,
        edge_decay:             float = 0.999,
        centrality_relay_top_n: int   = 10,
    ):
        self.similarity_threshold   = similarity_threshold
        self.k_neighbors            = k_neighbors
        self.max_nodes              = max_nodes
        self.edge_decay             = edge_decay
        self.centrality_relay_top_n = centrality_relay_top_n

        self.graph: nx.DiGraph = nx.DiGraph()
        self._step = 0

    # ------------------------------------------------------------------
    # Node management
    # ------------------------------------------------------------------

    def add_node(
        self,
        key:          str,
        vector:       np.ndarray,
        vector_space=None,   # VectorSpace for neighbor lookup
        metadata:     Optional[dict] = None,
    ):
        """
        Add a vector as a node and connect it to its k-nearest neighbors.

        Parameters
        ----------
        key : str
            Unique node identifier (matches VectorSpace key).
        vector : np.ndarray
        vector_space : VectorSpace or None
            If provided, nearest-neighbor edges are built immediately.
        metadata : dict or None
        """
        self.graph.add_node(
            key,
            vector   = vector.copy(),
            step     = self._step,
            metadata = metadata or {},
        )

        if vector_space is not None:
            self._connect_neighbors(key, vector, vector_space)

        if self.max_nodes and self.graph.number_of_nodes() > self.max_nodes:
            self._prune_weakest_node()

    # ------------------------------------------------------------------
    # Edge management
    # ------------------------------------------------------------------

    def _connect_neighbors(self, key: str, vector: np.ndarray, vector_space):
        """Connect key to its k-nearest neighbors in VectorSpace."""
        neighbors = vector_space.nearest(
            vector,
            top_k   = self.k_neighbors + 1,
            exclude = [key],
        )
        for neighbor_key, score in neighbors:
            if score >= self.similarity_threshold and self.graph.has_node(neighbor_key):
                self.graph.add_edge(key, neighbor_key, weight=float(score))
                self.graph.add_edge(neighbor_key, key, weight=float(score))

    def connect(self, key_a: str, key_b: str, weight: float = 1.0):
        """Manually add a directed edge."""
        if self.graph.has_node(key_a) and self.graph.has_node(key_b):
            self.graph.add_edge(key_a, key_b, weight=weight)

    def decay_edges(self):
        """Apply weight decay to all edges. Call periodically."""
        for u, v, data in self.graph.edges(data=True):
            data["weight"] *= self.edge_decay

        # Prune edges that have decayed below threshold
        weak = [
            (u, v) for u, v, d in self.graph.edges(data=True)
            if d["weight"] < 0.01
        ]
        self.graph.remove_edges_from(weak)
        self._step += 1

    # ------------------------------------------------------------------
    # Centrality
    # ------------------------------------------------------------------

    def centrality(self, method: str = "pagerank") -> Dict[str, float]:
        """
        Compute node centrality scores.

        Parameters
        ----------
        method : str
            "pagerank" | "degree" | "betweenness"

        Returns
        -------
        Dict[str, float] mapping node key → centrality score ∈ [0, 1]
        """
        if self.graph.number_of_nodes() == 0:
            return {}

        if method == "pagerank":
            try:
                scores = nx.pagerank(
                    self.graph,
                    weight="weight",
                    alpha=0.85,
                    max_iter=100,
                )
            except nx.PowerIterationFailedConvergence:
                scores = {n: 1.0 / self.graph.number_of_nodes()
                          for n in self.graph.nodes}

        elif method == "degree":
            d = dict(self.graph.degree(weight="weight"))
            max_d = max(d.values()) if d else 1.0
            scores = {k: v / (max_d + 1e-8) for k, v in d.items()}

        elif method == "betweenness":
            scores = nx.betweenness_centrality(self.graph, weight="weight", normalized=True)

        else:
            raise ValueError(f"Unknown centrality method: '{method}'")

        return scores

    def top_nodes(self, n: int = 10, method: str = "pagerank") -> List[Tuple[str, float]]:
        """Return top n nodes by centrality score."""
        scores = self.centrality(method)
        return sorted(scores.items(), key=lambda x: x[1], reverse=True)[:n]

    # ------------------------------------------------------------------
    # Signal relay
    # ------------------------------------------------------------------

    def emit_centrality(
        self,
        generator,
        vector_space=None,
        method: str = "pagerank",
    ) -> Dict[str, float]:
        """
        Compute centrality and relay signals to generator + symbolic ecology.

        High-centrality nodes represent conceptual gravity wells — their
        origin tokens should decay more slowly in the symbolic ecology.

        Parameters
        ----------
        generator : Generator
            For centrality signal relay.
        vector_space : VectorSpace or None
            For token lookups (if node metadata contains tokens).
        method : str
            Centrality computation method.

        Returns
        -------
        Dict[str, float] top node → centrality
        """
        if generator is None or self.graph.number_of_nodes() == 0:
            return {}

        scores    = self.centrality(method)
        top       = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        top       = top[:self.centrality_relay_top_n]

        relayed: Dict[str, float] = {}
        for key, score in top:
            node_data = self.graph.nodes.get(key, {})
            tokens    = node_data.get("metadata", {}).get("tokens", [])
            if tokens:
                generator.signal_centrality(tokens, centrality=score)
            relayed[key] = round(score, 6)

        return relayed

    # ------------------------------------------------------------------
    # Traversal
    # ------------------------------------------------------------------

    def neighbors(self, key: str, depth: int = 1) -> List[str]:
        """Return all nodes reachable from key within `depth` hops."""
        if not self.graph.has_node(key):
            return []
        ego = nx.ego_graph(self.graph, key, radius=depth)
        return [n for n in ego.nodes if n != key]

    def semantic_path(self, source: str, target: str) -> Optional[List[str]]:
        """Shortest semantic path between two nodes. None if unreachable."""
        try:
            return nx.shortest_path(self.graph, source, target, weight="weight")
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            return None

    def semantic_distance(self, source: str, target: str) -> float:
        """Shortest path length. Returns inf if unreachable."""
        try:
            return float(nx.shortest_path_length(
                self.graph, source, target, weight="weight"
            ))
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            return float("inf")

    # ------------------------------------------------------------------
    # Curvature
    # ------------------------------------------------------------------

    def local_density(self, key: str) -> float:
        """
        Local graph density around a node.
        High density = conceptual gravity well.
        """
        if not self.graph.has_node(key):
            return 0.0
        neighbors = list(self.graph.neighbors(key))
        if len(neighbors) < 2:
            return 0.0
        subgraph = self.graph.subgraph(neighbors)
        return float(nx.density(subgraph))

    # ------------------------------------------------------------------
    # Pruning
    # ------------------------------------------------------------------

    def _prune_weakest_node(self):
        """Remove the node with the lowest degree (least connected)."""
        degrees = dict(self.graph.degree())
        if not degrees:
            return
        weakest = min(degrees, key=degrees.get)
        self.graph.remove_node(weakest)

    # ------------------------------------------------------------------
    # Diagnostics
    # ------------------------------------------------------------------

    def stats(self) -> dict:
        return {
            "nodes":      self.graph.number_of_nodes(),
            "edges":      self.graph.number_of_edges(),
            "density":    round(nx.density(self.graph), 6) if self.graph.number_of_nodes() > 1 else 0.0,
            "components": nx.number_weakly_connected_components(self.graph),
            "step":       self._step,
        }
