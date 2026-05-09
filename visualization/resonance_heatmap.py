"""
visualization/resonance_heatmap.py

Resonance heatmap — 2D visualization of the field's evolving landscape.

Three heatmap layers:
  field_heatmap       field vector components over time (step × dim)
  coherence_heatmap   per-step coherence across multiple metrics
  attractor_landscape cosine similarity of each step's vector to each
                      attractor center — reveals basin dynamics

Terminal mode uses Unicode block characters for inline inspection.
Matplotlib mode produces publication-quality figures.
"""

from __future__ import annotations

from typing import List, Optional

import numpy as np


# ---------------------------------------------------------------------------
# Terminal heatmap (Unicode blocks)
# ---------------------------------------------------------------------------

BLOCKS = " ░▒▓█"


def array_to_block_row(row: np.ndarray, width: int = 64) -> str:
    """Map a 1D array to a single row of Unicode block characters."""
    n     = len(row)
    chunk = max(1, n // width)
    chars = []
    for i in range(0, min(n, width * chunk), chunk):
        val  = float(np.mean(row[i : i + chunk]))
        norm = float(np.clip((np.tanh(val) + 1.0) / 2.0, 0.0, 1.0))
        idx  = int(norm * (len(BLOCKS) - 1))
        chars.append(BLOCKS[idx])
    return "".join(chars)


def render_heatmap_terminal(
    field_history:     List[np.ndarray],
    coherence_history: List[float],
    n_rows:            int = 16,
    width:             int = 64,
) -> str:
    """
    Render a compact terminal heatmap of recent field history.

    Shows the last n_rows steps as rows of Unicode blocks,
    with coherence values on the right margin.
    """
    if not field_history:
        return "[resonance_heatmap] No data."

    recent    = field_history[-n_rows:]
    coh_recent = coherence_history[-n_rows:] if coherence_history else [0.0] * len(recent)

    lines = ["┌─ Resonance Heatmap " + "─" * (width - 18) + "┐"]
    for i, (fvec, coh) in enumerate(zip(recent, coh_recent)):
        row  = array_to_block_row(fvec, width=width)
        lines.append(f"│{row}│ {coh:.3f}")
    lines.append("└" + "─" * width + "─────┘")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Matplotlib heatmaps
# ---------------------------------------------------------------------------

def render_heatmap_plot(
    field_history:      List[np.ndarray],
    coherence_history:  List[float],
    attractor_centers:  Optional[List[np.ndarray]] = None,
    crystal_vectors:    Optional[List[np.ndarray]] = None,
    title:              str           = "RFE-Core2 Resonance Heatmap",
    save_path:          Optional[str] = None,
    show:               bool          = True,
    max_steps:          int           = 128,
):
    """
    Multi-panel resonance heatmap.

    Panels
    ------
    1. Field heatmap        : (step, dim) — tanh-normalized field over time
    2. Coherence trace      : coherence over time as a line
    3. Attractor landscape  : cosine similarity of each step to each attractor center

    Parameters
    ----------
    field_history : list of np.ndarray
    coherence_history : list of float
    attractor_centers : list of np.ndarray or None
    crystal_vectors : list of np.ndarray or None
    """
    try:
        import matplotlib.pyplot as plt
        import matplotlib.gridspec as gridspec
    except ImportError:
        print("[resonance_heatmap] matplotlib not available.")
        return

    if not field_history:
        print("[resonance_heatmap] No field history to render.")
        return

    # Trim to max_steps
    field_history     = field_history[-max_steps:]
    coherence_history = coherence_history[-max_steps:] if coherence_history else []

    field_mat = np.stack([np.tanh(f) for f in field_history])   # (steps, dim)
    steps     = list(range(len(field_history)))

    n_panels = 2 + (1 if attractor_centers else 0)
    fig = plt.figure(figsize=(14, 3 * n_panels))
    fig.patch.set_facecolor("#0d1117")
    gs  = gridspec.GridSpec(n_panels, 1, hspace=0.35)

    # ── Panel 1: Field heatmap ──
    ax1 = fig.add_subplot(gs[0])
    ax1.set_facecolor("#0d1117")
    im1 = ax1.imshow(
        field_mat.T, aspect="auto", origin="lower",
        cmap="plasma", vmin=-1, vmax=1,
        extent=[0, len(steps), 0, field_mat.shape[1]],
    )
    ax1.set_title("Field Vector (tanh)", color="white", fontsize=10)
    ax1.set_ylabel("Dim", color="#aaa")
    ax1.tick_params(colors="#aaa")
    fig.colorbar(im1, ax=ax1, fraction=0.015, pad=0.02)

    # ── Panel 2: Coherence trace ──
    ax2 = fig.add_subplot(gs[1])
    ax2.set_facecolor("#0d1117")
    if coherence_history:
        ax2.plot(steps[:len(coherence_history)], coherence_history,
                 color="#00d2ff", linewidth=1.2)
        ax2.fill_between(steps[:len(coherence_history)], coherence_history,
                         alpha=0.15, color="#00d2ff")
    ax2.set_ylim(0, 1)
    ax2.axhline(0.5, color="#444", linestyle="--", linewidth=0.8)
    ax2.set_title("Coherence", color="white", fontsize=10)
    ax2.set_ylabel("Score", color="#aaa")
    ax2.tick_params(colors="#aaa")
    ax2.grid(True, alpha=0.15, color="#333")

    # ── Panel 3: Attractor landscape ──
    if attractor_centers and len(attractor_centers) > 0:
        ax3 = fig.add_subplot(gs[2])
        ax3.set_facecolor("#0d1117")

        landscape = np.zeros((len(attractor_centers), len(field_history)))
        for ci, center in enumerate(attractor_centers):
            for si, fvec in enumerate(field_history):
                sim = float(np.dot(fvec, center) /
                           (np.linalg.norm(fvec) * np.linalg.norm(center) + 1e-8))
                landscape[ci, si] = sim

        im3 = ax3.imshow(
            landscape, aspect="auto", origin="lower",
            cmap="hot", vmin=-1, vmax=1,
            extent=[0, len(steps), 0, len(attractor_centers)],
        )
        ax3.set_title("Attractor Landscape (cosine similarity)", color="white", fontsize=10)
        ax3.set_ylabel("Attractor", color="#aaa")
        ax3.set_xlabel("Step", color="#aaa")
        ax3.tick_params(colors="#aaa")
        fig.colorbar(im3, ax=ax3, fraction=0.015, pad=0.02)

    fig.suptitle(title, color="white", fontsize=12, y=1.01)
    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches="tight",
                    facecolor=fig.get_facecolor())
        print(f"[resonance_heatmap] Saved to {save_path}")

    if show:
        plt.show()

    plt.close(fig)


# ---------------------------------------------------------------------------
# HeatmapRenderer — stateful helper
# ---------------------------------------------------------------------------

class HeatmapRenderer:
    """
    Stateful heatmap renderer that accumulates history from the loop.

    Usage:
        hmap = HeatmapRenderer()
        state = cycle.step(tokens)
        hmap.ingest(state, cycle.field.field.copy())
        print(hmap.terminal())
    """

    def __init__(self, maxlen: int = 256, terminal_width: int = 64):
        self.maxlen         = maxlen
        self.terminal_width = terminal_width
        self.field_history:     List[np.ndarray] = []
        self.coherence_history: List[float]      = []

    def ingest(self, step_state, raw_field: np.ndarray):
        self.field_history.append(raw_field.copy())
        self.coherence_history.append(step_state.coherence)
        if len(self.field_history) > self.maxlen:
            self.field_history.pop(0)
            self.coherence_history.pop(0)

    def terminal(self, n_rows: int = 12) -> str:
        return render_heatmap_terminal(
            self.field_history,
            self.coherence_history,
            n_rows = n_rows,
            width  = self.terminal_width,
        )

    def plot(self, attractor_centers=None, **kwargs):
        render_heatmap_plot(
            field_history     = self.field_history,
            coherence_history = self.coherence_history,
            attractor_centers = attractor_centers,
            **kwargs,
        )
