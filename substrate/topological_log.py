# Copyright 2026 Samuel Jackson Grim
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
substrate/topological_log.py

Topological memory log — directed graph over cognitive events.

Each node is a vector key with associated metadata (tokens, coherence,
relational profile, rhythm, field energy, timestamp). Edges encode
causal/temporal succession.

Capabilities
------------
  - Add nodes with parent linkage (temporal succession)
  - Ancestry tracing (full lineage of a node)
  - Branch detection (nodes with multiple successors)
  - Recency queries
  - Metadata filtering
  - Path length between nodes
  - Subgraph extraction around a focal node
"""

import time
from typing import Any, Dict, List, Optional, Tuple

import networkx as nx


class TopologicalLog:
    """
    Directed acyclic graph (DAG) over cognitive events.

    Nodes
    -----
    key : str
        Unique identifier (typically a short UUID fragment).
    timestamp : float
        Wall-clock time of insertion.
    metadata : dict
        Arbitrary contextual data — tokens, coherence, relational profile,
        rhythm state, field energy, emotional gradients, etc.

    Edges
    -----
    parent → child : directed, represents temporal/causal succession.
    """

    def __init__(self):
        self.graph: nx.DiGraph = nx.DiGraph()

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    def add(
        self,
        key: str,
        parent: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """
        Add a node to the topology.

        Parameters
        ----------
        key : str
            Unique node identifier.
        parent : str or None
            Key of the immediately preceding node. Creates a directed edge.
        metadata : dict or None
            Contextual data stored on the node.
        """
        self.graph.add_node(
            key,
            timestamp=time.time(),
            metadata=metadata or {},
        )

        if parent is not None and self.graph.has_node(parent):
            self.graph.add_edge(parent, key)

    def annotate(self, key: str, updates: Dict[str, Any]):
        """
        Merge additional metadata into an existing node.
        Safe to call after initial insertion (e.g. once coherence is computed).
        """
        if not self.graph.has_node(key):
            raise KeyError(f"Node '{key}' not found in topology.")
        self.graph.nodes[key]["metadata"].update(updates)

    # ------------------------------------------------------------------
    # Read — single node
    # ------------------------------------------------------------------

    def get(self, key: str) -> Optional[Dict[str, Any]]:
        """Return full node data dict, or None if not found."""
        if not self.graph.has_node(key):
            return None
        node = self.graph.nodes[key]
        return {
            "key":       key,
            "timestamp": node["timestamp"],
            **node["metadata"],
        }

    def metadata(self, key: str) -> Dict[str, Any]:
        """Return just the metadata dict for a node."""
        if not self.graph.has_node(key):
            return {}
        return dict(self.graph.nodes[key].get("metadata", {}))

    # ------------------------------------------------------------------
    # Read — collections
    # ------------------------------------------------------------------

    def recent(self, n: int = 5) -> List[Dict[str, Any]]:
        """
        Return the n most recently inserted nodes, newest first.
        """
        nodes = [
            {"key": k, "timestamp": d["timestamp"], **d["metadata"]}
            for k, d in self.graph.nodes(data=True)
        ]
        nodes.sort(key=lambda x: x["timestamp"], reverse=True)
        return nodes[:n]

    def filter(
        self,
        field: str,
        min_val: Optional[float] = None,
        max_val: Optional[float] = None,
        exact: Optional[Any] = None,
    ) -> List[Dict[str, Any]]:
        """
        Return nodes whose metadata[field] satisfies the given condition.

        Examples
        --------
        log.filter("coherence", min_val=0.8)          # high coherence nodes
        log.filter("rhythm", exact="dream")            # dream-state nodes
        log.filter("field_energy", min_val=2, max_val=5)
        """
        results = []
        for k, d in self.graph.nodes(data=True):
            val = d.get("metadata", {}).get(field)
            if val is None:
                continue
            if exact is not None and val != exact:
                continue
            if min_val is not None and val < min_val:
                continue
            if max_val is not None and val > max_val:
                continue
            results.append({"key": k, "timestamp": d["timestamp"], **d["metadata"]})

        results.sort(key=lambda x: x["timestamp"], reverse=True)
        return results

    # ------------------------------------------------------------------
    # Topology analysis
    # ------------------------------------------------------------------

    def ancestry(self, key: str) -> List[str]:
        """
        Return the full ancestor chain for `key`, root first.
        Follows the directed edge path backward through parents.
        """
        if not self.graph.has_node(key):
            return []

        chain = []
        current = key
        visited = set()

        while current is not None:
            if current in visited:
                break  # cycle guard
            visited.add(current)
            chain.append(current)
            predecessors = list(self.graph.predecessors(current))
            current = predecessors[0] if predecessors else None

        chain.reverse()
        return chain

    def branches(self) -> List[str]:
        """
        Return keys of nodes that have more than one successor.
        These represent cognitive branch points — moments where
        the trajectory forked.
        """
        return [
            k for k in self.graph.nodes
            if self.graph.out_degree(k) > 1
        ]

    def path_length(self, source: str, target: str) -> Optional[int]:
        """
        Shortest directed path length between two nodes.
        Returns None if no path exists.
        """
        try:
            return nx.shortest_path_length(self.graph, source, target)
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            return None

    def neighborhood(self, key: str, radius: int = 2) -> List[str]:
        """
        Return all nodes within `radius` hops of `key`
        (both predecessors and successors, undirected traversal).
        """
        if not self.graph.has_node(key):
            return []

        undirected = self.graph.to_undirected()
        ego = nx.ego_graph(undirected, key, radius=radius)
        return [n for n in ego.nodes if n != key]

    def roots(self) -> List[str]:
        """Nodes with no predecessors (entry points into the topology)."""
        return [k for k in self.graph.nodes if self.graph.in_degree(k) == 0]

    def leaves(self) -> List[str]:
        """Nodes with no successors (current frontier of the topology)."""
        return [k for k in self.graph.nodes if self.graph.out_degree(k) == 0]

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    def stats(self) -> Dict[str, Any]:
        return {
            "nodes":    self.graph.number_of_nodes(),
            "edges":    self.graph.number_of_edges(),
            "branches": len(self.branches()),
            "roots":    len(self.roots()),
            "leaves":   len(self.leaves()),
        }
