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
#
"""
visualization/topology_render.py

Topological memory graph visualization.

Renders the directed graph from TopologicalLog and SemanticLattice,
coloring nodes by rhythm state and sizing them by coherence or centrality.

Modes
-----
  terminal    Text summary of graph structure (always available)
  matplotlib  Static graph layout using networkx + matplotlib
  dot         Export to Graphviz DOT format for external rendering
"""

from __future__ import annotations

from typing import Optional, Dict, Any

import numpy as np


RHYTHM_COLORS = {
    "stabilize": "#4a90d9",
    "dream":     "#9b59b6",
    "reflect":   "#27ae60",
    "explore":   "#e67e22",
    "unknown":   "#95a5a6",
}


# ---------------------------------------------------------------------------
# Terminal summary
# ---------------------------------------------------------------------------

def topology_summary(topology) -> str:
    """
    Print a text summary of the TopologicalLog or SemanticLattice.
    Always available — no matplotlib dependency.
    """
    stats  = topology.stats() if hasattr(topology, "stats") else {}
    lines  = ["── Topology Summary ──────────────────"]

    for k, v in stats.items():
        lines.append(f"  {k:<18}: {v}")

    if hasattr(topology, "recent"):
        recent = topology.recent(n=5)
        lines.append("  Recent nodes:")
        for node in recent:
            key     = node.get("key", "?")
            rhythm  = node.get("rhythm", "?")
            coh     = node.get("coherence", 0.0)
            pattern = node.get("pattern", "")
            lines.append(f"    {key}  rhythm={rhythm:<10} coh={coh:.3f}  {pattern}")

    if hasattr(topology, "branches"):
        branches = topology.branches()
        if branches:
            lines.append(f"  Branch points: {', '.join(branches[:5])}")

    lines.append("──────────────────────────────────────")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Matplotlib graph render
# ---------------------------------------------------------------------------

def render_topology_plot(
    topology,
    title:      str           = "RFE-Core2 Topology",
    max_nodes:  int           = 128,
    save_path:  Optional[str] = None,
    show:       bool          = True,
    node_size_field: str      = "coherence",  # metadata field for node sizing
):
    """
    Render the topological graph as a network diagram.

    Nodes colored by rhythm state, sized by coherence or centrality.
    Edges represent causal succession (parent → child).

    Parameters
    ----------
    topology : TopologicalLog or SemanticLattice
    title : str
    max_nodes : int
        Limit rendering to the most recent N nodes for clarity.
    save_path : str or None
    show : bool
    node_size_field : str
        Metadata field used to scale node size.
    """
    try:
        import matplotlib.pyplot as plt
        import networkx as nx
    except ImportError:
        print("[topology_render] matplotlib/networkx not available.")
        return

    graph = topology.graph

    if graph.number_of_nodes() == 0:
        print("[topology_render] Graph is empty.")
        return

    # Limit to most recent nodes
    if graph.number_of_nodes() > max_nodes:
        nodes_sorted = sorted(
            graph.nodes(data=True),
            key=lambda x: x[1].get("timestamp", 0),
            reverse=True,
        )
        keep = {n for n, _ in nodes_sorted[:max_nodes]}
        graph = graph.subgraph(keep)

    fig, ax = plt.subplots(figsize=(14, 9))
    fig.patch.set_facecolor("#1a1a2e")
    ax.set_facecolor("#1a1a2e")

    # Layout
    try:
        pos = nx.spring_layout(graph, k=1.5, iterations=50, seed=42)
    except Exception:
        pos = nx.random_layout(graph, seed=42)

    # Node colors and sizes from metadata
    colors = []
    sizes  = []
    for node in graph.nodes():
        meta   = graph.nodes[node].get("metadata", {})
        rhythm = meta.get("rhythm", "unknown")
        coh    = float(meta.get(node_size_field, 0.5))
        colors.append(RHYTHM_COLORS.get(rhythm, RHYTHM_COLORS["unknown"]))
        sizes.append(max(50, coh * 400))

    # Draw
    nx.draw_networkx_edges(
        graph, pos, ax=ax,
        edge_color="#ffffff22",
        arrows=True,
        arrowsize=8,
        width=0.5,
    )
    nx.draw_networkx_nodes(
        graph, pos, ax=ax,
        node_color=colors,
        node_size=sizes,
        alpha=0.85,
    )

    ax.set_title(title, color="white", fontsize=12, pad=12)
    ax.axis("off")

    # Legend
    import matplotlib.patches as mpatches
    patches = [
        mpatches.Patch(color=c, label=r)
        for r, c in RHYTHM_COLORS.items() if r != "unknown"
    ]
    ax.legend(handles=patches, loc="upper left", fontsize=9,
              facecolor="#2a2a3e", labelcolor="white")

    stats_text = (
        f"nodes={graph.number_of_nodes()} "
        f"edges={graph.number_of_edges()}"
    )
    ax.text(0.99, 0.01, stats_text, transform=ax.transAxes,
            color="#aaaaaa", fontsize=8, ha="right", va="bottom")

    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches="tight",
                    facecolor=fig.get_facecolor())
        print(f"[topology_render] Saved to {save_path}")

    if show:
        plt.show()

    plt.close(fig)


# ---------------------------------------------------------------------------
# DOT export
# ---------------------------------------------------------------------------

def export_dot(topology, path: str):
    """
    Export the topology graph to Graphviz DOT format.

    Render with: dot -Tpng output.dot -o graph.png
    """
    try:
        import networkx as nx
        nx.drawing.nx_pydot.write_dot(topology.graph, path)
        print(f"[topology_render] DOT exported to {path}")
    except Exception as e:
        print(f"[topology_render] DOT export failed: {e}")
        print("  Install pydot: pip install pydot")
