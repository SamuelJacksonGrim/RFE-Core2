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
agents/watcher.py

Three-layer coherence model: the system's epistemic immune system.

Layers
------
  G  Geometric Coherence   — contextual vector alignment
  T  Temporal Stability    — smoothness through time (acceleration / jerk)
  R  Field Resonance       — harmonic compatibility with active field state

Composite score
  C = α·G + β·T + γ·R   (weights configurable, must sum to 1)

Additional diagnostics
  entropy_drift            — rate of change in the vector's information distribution
  coherence_delta          — how much injecting this vector stabilizes / destabilizes the field
  crystallization_pressure — G × T, candidate signal for MemoryCrystal promotion

Conceptual role
  The Watcher does not merely filter.
  It determines:
    - what integrates into the field
    - what destabilizes it
    - what crystallizes into memory
    - what gets rejected or mutated
    - how identity persists through time
"""

import collections
from dataclasses import dataclass
from typing import Optional, TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from substrate.resonance_field import ResonanceField


# ---------------------------------------------------------------------------
# Report dataclass
# ---------------------------------------------------------------------------

@dataclass
class CoherenceReport:
    """
    Full diagnostic snapshot from a single Watcher evaluation.

    All scalar fields are in [0, 1] except coherence_delta (unbounded).
    """
    geometric:               float   # G — contextual cosine alignment
    temporal:                float   # T — stability through time
    resonance:               float   # R — field harmonic compatibility
    composite:               float   # C = α·G + β·T + γ·R
    entropy_drift:           float   # rate of change in vector entropy
    coherence_delta:         float   # field coherence change post-injection (signed)
    crystallization_pressure: float  # G × T — crystallization candidate score
    stable:                  bool    # composite >= threshold

    def as_dict(self) -> dict:
        return {
            "geometric":               self.geometric,
            "temporal":                self.temporal,
            "resonance":               self.resonance,
            "composite":               self.composite,
            "entropy_drift":           self.entropy_drift,
            "coherence_delta":         self.coherence_delta,
            "crystallization_pressure": self.crystallization_pressure,
            "stable":                  self.stable,
        }


# ---------------------------------------------------------------------------
# Watcher
# ---------------------------------------------------------------------------

class Watcher:
    """
    Three-layer coherence evaluator.

    Parameters
    ----------
    dim : int
        Vector dimensionality.
    history_len : int
        Number of recent vectors retained for temporal analysis.
    threshold : float
        Minimum composite coherence score to be considered stable.
    alpha : float
        Weight for geometric coherence layer.
    beta : float
        Weight for temporal stability layer.
    gamma : float
        Weight for field resonance layer.
        alpha + beta + gamma must equal 1.0.
    field : ResonanceField or None
        If provided, enables recursive coherence_delta computation.
    """

    def __init__(
        self,
        dim: int = 128,
        history_len: int = 16,
        threshold: float = 0.4,
        alpha: float = 0.40,
        beta: float = 0.35,
        gamma: float = 0.25,
        field: Optional["ResonanceField"] = None,
    ):
        weight_sum = alpha + beta + gamma
        assert abs(weight_sum - 1.0) < 1e-6, (
            f"Layer weights must sum to 1.0, got {weight_sum:.6f}"
        )

        self.dim         = dim
        self.threshold   = threshold
        self.alpha       = alpha
        self.beta        = beta
        self.gamma       = gamma
        self.field       = field

        # Rolling history for temporal analysis
        self._history:        collections.deque = collections.deque(maxlen=history_len)
        self._velocities:     collections.deque = collections.deque(maxlen=history_len)
        self._entropy_history: collections.deque = collections.deque(maxlen=history_len)

        # Incremental rolling centroid — avoids recomputing over full history
        self._rolling_sum:   np.ndarray = np.zeros(dim)
        self._rolling_count: int = 0

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def evaluate(
        self,
        vec: np.ndarray,
        anchor: np.ndarray,
        field_state: Optional[np.ndarray] = None,
    ) -> CoherenceReport:
        """
        Full three-layer coherence evaluation for a single vector.

        Parameters
        ----------
        vec : np.ndarray, shape (dim,)
            Incoming vector to evaluate.
        anchor : np.ndarray, shape (dim,)
            Current Witness identity anchor.
        field_state : np.ndarray or None
            Resonated field state. If None and self.field is set,
            uses self.field.resonate(). If neither available, resonance
            defaults to neutral (0.5).

        Returns
        -------
        CoherenceReport
        """
        # Resolve field state once, reuse across layers
        if field_state is None and self.field is not None:
            field_state = self.field.resonate()

        G = self._geometric_coherence(vec, anchor, field_state)
        T = self._temporal_stability(vec)
        R = self._field_resonance(vec, field_state)

        composite = self.alpha * G + self.beta * T + self.gamma * R

        entropy_drift            = self._entropy_drift(vec)
        coherence_delta          = self._coherence_delta(vec)
        crystallization_pressure = G * T

        # Commit to history after all reads (avoid self-contamination)
        self._update_history(vec)

        return CoherenceReport(
            geometric               = round(float(G), 6),
            temporal                = round(float(T), 6),
            resonance               = round(float(R), 6),
            composite               = round(float(composite), 6),
            entropy_drift           = round(float(entropy_drift), 6),
            coherence_delta         = round(float(coherence_delta), 6),
            crystallization_pressure = round(float(crystallization_pressure), 6),
            stable                  = bool(composite >= self.threshold),
        )

    def filter_stream(
        self,
        vectors: list,
        anchor: np.ndarray,
        field_state: Optional[np.ndarray] = None,
    ) -> list:
        """
        Return only vectors whose composite coherence >= self.threshold.
        History is updated for each evaluated vector in order.
        """
        return [v for v in vectors if self.evaluate(v, anchor, field_state).stable]

    def attach_field(self, field: "ResonanceField"):
        """Late-bind a ResonanceField after construction."""
        self.field = field

    # ------------------------------------------------------------------
    # Layer 1 — Geometric Coherence
    # ------------------------------------------------------------------

    def _geometric_coherence(
        self,
        vec: np.ndarray,
        anchor: np.ndarray,
        field_state: Optional[np.ndarray],
    ) -> float:
        """
        Contextual geometric coherence:

            G = 0.5·cos(vec, anchor)
              + 0.3·cos(vec, rolling_mean)
              + 0.2·cos(vec, field_state)

        Measures alignment against identity anchor, recent trajectory
        centroid, and the current field. Contextual rather than purely local.

        Raw cosine ∈ [-1, 1] is mapped to [0, 1] before weighting.
        """
        def _c01(a, b):
            return (self._cosine(a, b) + 1.0) / 2.0

        g_anchor = _c01(vec, anchor)

        if self._rolling_count > 0:
            rolling_mean = self._rolling_sum / self._rolling_count
            g_rolling = _c01(vec, rolling_mean)
        else:
            g_rolling = 0.5  # neutral prior — no trajectory yet

        if field_state is not None and np.linalg.norm(field_state) > 1e-6:
            g_field = _c01(vec, field_state)
        else:
            g_field = 0.5  # neutral — field not yet charged

        G = 0.5 * g_anchor + 0.3 * g_rolling + 0.2 * g_field
        return float(np.clip(G, 0.0, 1.0))

    # ------------------------------------------------------------------
    # Layer 2 — Temporal Stability
    # ------------------------------------------------------------------

    def _temporal_stability(self, vec: np.ndarray) -> float:
        """
        Stability through time via vector acceleration and entropy variance.

        Cognitively coherent systems evolve smoothly.
        Fragmentation and collapse show up as high acceleration (rapid
        direction changes) or high entropy variance (distributional chaos).

            T = 1 / (1 + ||acceleration|| + entropy_variance)

        Returns 0.9 (high, stable prior) when history is too shallow.
        """
        if len(self._history) < 1:
            return 0.9

        velocity = vec - self._history[-1]
        self._velocities.append(velocity.copy())

        if len(self._velocities) < 2:
            # Single velocity: use magnitude as a proxy for rate of change
            T = 1.0 / (1.0 + float(np.linalg.norm(velocity)))
            return float(np.clip(T, 0.0, 1.0))

        acceleration   = self._velocities[-1] - self._velocities[-2]
        accel_magnitude = float(np.linalg.norm(acceleration))

        # Entropy variance adds a second destabilization signal:
        # rapid entropy fluctuation even without direction change
        if len(self._entropy_history) >= 3:
            entropy_var = float(np.var(list(self._entropy_history)[-8:]))
        else:
            entropy_var = 0.0

        T = 1.0 / (1.0 + accel_magnitude + entropy_var)
        return float(np.clip(T, 0.0, 1.0))

    # ------------------------------------------------------------------
    # Layer 3 — Field Resonance
    # ------------------------------------------------------------------

    def _field_resonance(
        self,
        vec: np.ndarray,
        field_state: Optional[np.ndarray],
    ) -> float:
        """
        Harmonic compatibility with active field state.

            R = cos(vec, field_state), mapped to [0, 1]

        Cold-start / zero field → neutral 0.5 to avoid early collapse.

        Extension point: spectral/FFT harmonic analysis lives here.
        Phase synchrony and resonance band matching to be added when
        ResonanceField gains FFT support.
        """
        if field_state is None:
            return 0.5

        if np.linalg.norm(field_state) < 1e-6:
            return 0.5  # field not yet charged — neutral

        raw = self._cosine(vec, field_state)
        return float(np.clip((raw + 1.0) / 2.0, 0.0, 1.0))

    # ------------------------------------------------------------------
    # Recursive Coherence Delta
    # ------------------------------------------------------------------

    def _coherence_delta(self, vec: np.ndarray) -> float:
        """
        How much does injecting `vec` into the field change the field's
        internal coherence?

            delta = coherence(field_after) - coherence(field_before)

        Positive delta → vec stabilizes the field.
        Negative delta → vec destabilizes it (potential reject / quarantine).

        This is the key signal for adaptive cognition pressure: vectors
        are judged not only by their own alignment but by their systemic
        effect on the field ecology.

        Non-destructive: the probe does not modify self.field.
        """
        field = self.field
        if field is None or len(field.history) == 0:
            return 0.0

        history_window = list(field.history)[-16:]
        history_mean   = np.mean(history_window, axis=0)

        before = float(
            (self._cosine(field.field, history_mean) + 1.0) / 2.0
        )

        # Simulate inject + resonate (mirrors ResonanceField behavior)
        probed_field = np.tanh(field.field + vec * 0.5)
        after = float(
            (self._cosine(probed_field, history_mean) + 1.0) / 2.0
        )

        return float(after - before)

    # ------------------------------------------------------------------
    # Entropy Drift
    # ------------------------------------------------------------------

    def _entropy_drift(self, vec: np.ndarray) -> float:
        """
        Rate of change in the vector's distributional entropy.

            H(v) = -Σ p·log(p)   where  p = |v| / Σ|v|

        High entropy drift = information distribution shifting rapidly.
        Signals instability or phase transition.

        Normalized by log(dim) (maximum possible entropy for this dimensionality).
        """
        p = np.abs(vec)
        p_sum = p.sum()

        if p_sum < 1e-8:
            return 0.0

        p = np.clip(p / p_sum, 1e-10, 1.0)
        H = float(-np.sum(p * np.log(p)))

        self._entropy_history.append(H)

        if len(self._entropy_history) < 2:
            return 0.0

        drift   = abs(float(self._entropy_history[-1]) - float(self._entropy_history[-2]))
        max_H   = np.log(self.dim)
        return float(np.clip(drift / max_H, 0.0, 1.0))

    # ------------------------------------------------------------------
    # Internal utilities
    # ------------------------------------------------------------------

    def _cosine(self, a: np.ndarray, b: np.ndarray) -> float:
        denom = np.linalg.norm(a) * np.linalg.norm(b) + 1e-8
        return float(np.dot(a, b) / denom)

    def _update_history(self, vec: np.ndarray):
        """Commit vector to rolling history. Called after all reads."""
        self._history.append(vec.copy())
        self._rolling_sum   += vec
        self._rolling_count += 1
