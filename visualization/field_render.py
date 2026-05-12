"""
visualization/field_render.py

Resonance field visualization.

Two render modes:
  terminal    ASCII heatmap of field vector, printable anywhere
  matplotlib  Line/area plot of field energy, rhythm, and spectral features

Designed to be called from the autonomous loop for live monitoring,
or post-hoc from a list of FieldState snapshots.
"""

from __future__ import annotations

import math
from typing import List, Optional, Tuple

import numpy as np


# ---------------------------------------------------------------------------
# Terminal render
# ---------------------------------------------------------------------------

DENSITY_CHARS = " ·:;+=xX$&@#"


def field_to_ascii(
    field_vec: np.ndarray,
    width:     int = 64,
    label:     str = "",
) -> str:
    """
    Render a field vector as a single-line ASCII density bar.

    Values are mapped to density characters proportional to their
    absolute magnitude. Positive values use the right half of the
    character set; negative use the left.
    """
    n     = len(field_vec)
    chunk = max(1, n // width)
    chars = []

    for i in range(0, min(n, width * chunk), chunk):
        block = field_vec[i : i + chunk]
        val   = float(np.mean(block))
        # Map [-1, 1] to [0, len(DENSITY_CHARS)-1]
        norm  = (np.tanh(val) + 1.0) / 2.0
        idx   = int(norm * (len(DENSITY_CHARS) - 1))
        chars.append(DENSITY_CHARS[idx])

    bar = "".join(chars)
    if label:
        return f"{label:>12} │{bar}│"
    return f"│{bar}│"


def render_field_terminal(
    field_vec:    np.ndarray,
    rhythm:       str         = "",
    energy:       float       = 0.0,
    coherence:    float       = 0.0,
    step:         int         = 0,
    width:        int         = 64,
) -> str:
    """
    Full terminal frame for one field state.

    Returns a multi-line string ready for print().
    """
    resonated = np.tanh(field_vec)
    lines = [
        f"┌─ step {step:>5} ─ rhythm: {rhythm:<10} energy: {energy:>7.4f} coherence: {coherence:>6.4f} ─┐",
        field_to_ascii(field_vec,  width=width, label="raw"),
        field_to_ascii(resonated,  width=width, label="resonated"),
        field_to_ascii(np.abs(field_vec), width=width, label="magnitude"),
        "└" + "─" * (width + 2) + "┘",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Matplotlib render (optional — graceful fallback if not available)
# ---------------------------------------------------------------------------

def render_field_plot(
    field_history:   List[np.ndarray],
    energy_history:  List[float],
    rhythm_history:  List[str],
    coherence_history: List[float],
    title:           str = "RFE-Core2 Field State",
    save_path:       Optional[str] = None,
    show:            bool = True,
):
    """
    Plot field energy, coherence, and rhythm over time.

    Parameters
    ----------
    field_history : list of np.ndarray
    energy_history : list of float
    rhythm_history : list of str
    coherence_history : list of float
    title : str
    save_path : str or None
    show : bool
    """
    try:
        import matplotlib.pyplot as plt
        import matplotlib.patches as mpatches
    except ImportError:
        print("[field_render] matplotlib not available. Install with: pip install matplotlib")
        return

    RHYTHM_COLORS = {
        "stabilize": "#4a90d9",
        "dream":     "#9b59b6",
        "reflect":   "#27ae60",
        "explore":   "#e67e22",
    }

    steps = list(range(len(energy_history)))

    fig, axes = plt.subplots(3, 1, figsize=(14, 8), sharex=True)
    fig.suptitle(title, fontsize=13, fontweight="bold")

    # --- Energy ---
    ax = axes[0]
    ax.plot(steps, energy_history, color="#2c3e50", linewidth=1.2)
    ax.fill_between(steps, energy_history, alpha=0.15, color="#2c3e50")
    ax.set_ylabel("Field Energy")
    ax.grid(True, alpha=0.3)

    # Shade by rhythm
    for i, rhythm in enumerate(rhythm_history):
        color = RHYTHM_COLORS.get(rhythm, "#aaaaaa")
        ax.axvspan(i - 0.5, i + 0.5, alpha=0.08, color=color)

    # --- Coherence ---
    ax = axes[1]
    ax.plot(steps, coherence_history, color="#16a085", linewidth=1.2)
    ax.fill_between(steps, coherence_history, alpha=0.15, color="#16a085")
    ax.set_ylim(0, 1)
    ax.set_ylabel("Coherence")
    ax.axhline(0.5, color="#aaa", linestyle="--", linewidth=0.8)
    ax.grid(True, alpha=0.3)

    # --- Field heatmap (last N states) ---
    ax = axes[2]
    if field_history:
        n_show = min(len(field_history), 64)
        mat    = np.stack([np.tanh(f) for f in field_history[-n_show:]])
        im     = ax.imshow(
            mat.T, aspect="auto", origin="lower",
            cmap="RdBu_r", vmin=-1, vmax=1,
            extent=[len(field_history) - n_show, len(field_history), 0, mat.shape[1]],
        )
        ax.set_ylabel("Field Dim")
        fig.colorbar(im, ax=ax, fraction=0.02, pad=0.02)

    axes[-1].set_xlabel("Step")

    # Rhythm legend
    patches = [
        mpatches.Patch(color=c, label=r, alpha=0.6)
        for r, c in RHYTHM_COLORS.items()
    ]
    fig.legend(handles=patches, loc="upper right", ncol=4, fontsize=9)

    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches="tight")
        print(f"[field_render] Saved to {save_path}")

    if show:
        plt.show()

    plt.close(fig)


# ---------------------------------------------------------------------------
# FieldRenderer — stateful helper for live loop use
# ---------------------------------------------------------------------------

class FieldRenderer:
    """
    Stateful renderer that accumulates history from StepState objects
    and renders on demand.

    Usage in autonomous loop:
        renderer = FieldRenderer()
        state = cycle.step(tokens)
        renderer.ingest(state, field_vec)
        print(renderer.terminal_frame())
    """

    def __init__(self, maxlen: int = 512, terminal_width: int = 64):
        self.maxlen         = maxlen
        self.terminal_width = terminal_width

        self.field_history:     List[np.ndarray] = []
        self.energy_history:    List[float]      = []
        self.rhythm_history:    List[str]        = []
        self.coherence_history: List[float]      = []
        self._last_state = None

    def ingest(self, step_state, field_vec: np.ndarray):
        """Feed one StepState + raw field vector into the renderer."""
        self._last_state = step_state
        self.field_history.append(field_vec.copy())
        self.energy_history.append(step_state.field_energy)
        self.rhythm_history.append(step_state.rhythm)
        self.coherence_history.append(step_state.coherence)

        if len(self.field_history) > self.maxlen:
            self.field_history.pop(0)
            self.energy_history.pop(0)
            self.rhythm_history.pop(0)
            self.coherence_history.pop(0)

    def terminal_frame(self) -> str:
        """Return current terminal frame as a string."""
        if not self.field_history or self._last_state is None:
            return "[FieldRenderer] No data yet."
        s = self._last_state
        return render_field_terminal(
            field_vec = self.field_history[-1],
            rhythm    = s.rhythm,
            energy    = s.field_energy,
            coherence = s.coherence,
            step      = s.step,
            width     = self.terminal_width,
        )

    def plot(self, **kwargs):
        """Render matplotlib plot of accumulated history."""
        render_field_plot(
            field_history     = self.field_history,
            energy_history    = self.energy_history,
            rhythm_history    = self.rhythm_history,
            coherence_history = self.coherence_history,
            **kwargs,
        )
