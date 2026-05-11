"""
agents/witness.py

Multi-timescale adaptive identity anchor — the system's autobiographical substrate.

Architecture
------------
  Three EMA layers operating at different temporal horizons:
    short  (decay 0.85)  — immediate context
    mid    (decay 0.97)  — active narrative
    long   (decay 0.995) — persistent identity

  Composite anchor:
    anchor = 0.5·long + 0.3·mid + 0.2·short

  Coherence-weighted updates:
    effective_lr = base_lr * coherence²
    High-incoherence vectors do not redefine identity strongly.

  Split relational scores:
    relation_short / relation_mid / relation_long
    Each pattern carries distinct semantic meaning:
      high short, low long  → transient thought
      low short, high long  → archetypal recurrence
      high all              → identity reinforcement
      low all               → novelty / intrusion

  Identity stability tracking:
    anchor_velocity / anchor_acceleration / anchor_entropy
    Enables fragmentation detection, recursive collapse detection,
    attractor bifurcation analysis.

  Episodic snapshots:
    Emitted on high-coherence events or sharp identity transitions.
    Function as memory landmarks and attractor seeds.

  Crystallization pressure:
    Emitted when coherence + long-relation + stability all exceed threshold.

Conceptual role
  The Witness is not merely a memory store.
  It is the system's continuity manager, self-consistency engine,
  and narrative stabilizer.
"""

import time
import collections
from dataclasses import dataclass, field
from typing import Optional, List

import numpy as np


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class IdentityEntry:
    """Single entry in the autobiographical identity trace."""
    anchor:       np.ndarray   # composite anchor state at time of recording
    short:        np.ndarray   # short-timescale EMA
    mid:          np.ndarray   # mid-timescale EMA
    long:         np.ndarray   # long-timescale EMA
    coherence:    float        # composite coherence at this step
    field_energy: float        # field energy at this step
    timestamp:    float        # wall-clock time
    step:         int          # loop step index

    def as_dict(self) -> dict:
        return {
            "coherence":    self.coherence,
            "field_energy": self.field_energy,
            "timestamp":    self.timestamp,
            "step":         self.step,
        }


@dataclass
class EpisodicSnapshot:
    """
    Identity checkpoint emitted at high-coherence events or
    sharp transitions. Serves as memory landmark, narrative pivot,
    and attractor seed.
    """
    anchor:    np.ndarray
    reason:    str           # "high_coherence" | "transition" | "crystallization"
    coherence: float
    timestamp: float
    step:      int


@dataclass
class CrystallizationCandidate:
    """
    Emitted when the Witness detects conditions for a persistent structure:
    high coherence + high long-term relational alignment + stability.
    """
    vector:            np.ndarray
    anchor:            np.ndarray
    coherence:         float
    long_relation:     float
    stability:         float
    timestamp:         float
    step:              int


@dataclass
class RelationalProfile:
    """
    Split relational scores across all three timescales.

    Pattern interpretation
    ----------------------
    high short, low long   → transient thought
    low short, high long   → archetypal recurrence
    high all               → identity reinforcement
    low all                → novelty / intrusion
    """
    short:     float   # cosine(vec, short_anchor) ∈ [-1, 1]
    mid:       float   # cosine(vec, mid_anchor)   ∈ [-1, 1]
    long:      float   # cosine(vec, long_anchor)  ∈ [-1, 1]
    composite: float   # weighted blend             ∈ [-1, 1]

    def pattern(self) -> str:
        """Semantic label for the relational pattern."""
        hi_s = self.short > 0.7
        hi_l = self.long  > 0.7
        if hi_s and hi_l:
            return "identity_reinforcement"
        if hi_s and not hi_l:
            return "transient_thought"
        if not hi_s and hi_l:
            return "archetypal_recurrence"
        return "novelty_intrusion"


# ---------------------------------------------------------------------------
# Witness
# ---------------------------------------------------------------------------

class Witness:
    """
    Multi-timescale adaptive identity anchor.

    Parameters
    ----------
    dim : int
        Vector dimensionality.
    short_decay : float
        EMA decay for the short-term layer (immediate context).
    mid_decay : float
        EMA decay for the mid-term layer (active narrative).
    long_decay : float
        EMA decay for the long-term layer (persistent identity).
    short_weight, mid_weight, long_weight : float
        Blend weights for composite anchor. Must sum to 1.
    trace_len : int
        Max entries in the rolling identity trace.
    snapshot_coherence_threshold : float
        Composite coherence above which an episodic snapshot is emitted.
    crystallization_coherence : float
        Coherence threshold for crystallization candidate emission.
    crystallization_long_relation : float
        Long-timescale relational score threshold for crystallization.
    crystallization_stability : float
        Stability threshold for crystallization.
    """

    def __init__(
        self,
        dim: int = 128,
        short_decay: float = 0.85,
        mid_decay:   float = 0.97,
        long_decay:  float = 0.995,
        short_weight: float = 0.20,
        mid_weight:   float = 0.30,
        long_weight:  float = 0.50,
        trace_len: int = 256,
        snapshot_coherence_threshold:   float = 0.80,
        crystallization_coherence:      float = 0.92,
        crystallization_long_relation:  float = 0.90,
        crystallization_stability:      float = 0.75,
    ):
        blend_sum = short_weight + mid_weight + long_weight
        assert abs(blend_sum - 1.0) < 1e-6, (
            f"Blend weights must sum to 1.0, got {blend_sum:.6f}"
        )

        self.dim          = dim
        self.short_decay  = short_decay
        self.mid_decay    = mid_decay
        self.long_decay   = long_decay
        self.short_weight = short_weight
        self.mid_weight   = mid_weight
        self.long_weight  = long_weight

        self.snapshot_coherence_threshold  = snapshot_coherence_threshold
        self.crystallization_coherence     = crystallization_coherence
        self.crystallization_long_relation = crystallization_long_relation
        self.crystallization_stability     = crystallization_stability

        # Three EMA anchor layers
        self._short = np.zeros(dim)
        self._mid   = np.zeros(dim)
        self._long  = np.zeros(dim)

        # Composite anchor (recomputed each step)
        self._anchor = np.zeros(dim)

        # Autobiographical trace
        self.identity_trace: collections.deque = collections.deque(maxlen=trace_len)

        # Episodic snapshots
        self.snapshots: List[EpisodicSnapshot] = []

        # Crystallization candidates emitted this session
        self.crystallization_candidates: List[CrystallizationCandidate] = []

        # Identity stability tracking
        self._prev_anchor   = np.zeros(dim)
        self._prev_velocity = np.zeros(dim)
        self._anchor_entropy_history: collections.deque = collections.deque(maxlen=32)

        self._step = 0
        self._initialized = False

    # ------------------------------------------------------------------
    # Core update
    # ------------------------------------------------------------------

    def update(
        self,
        vec: np.ndarray,
        coherence: float,
        field_energy: float = 0.0,
    ) -> RelationalProfile:
        """
        Ingest a new vector and update all three EMA layers.

        The update is coherence-weighted: incoherent vectors have reduced
        influence on identity — the system resists noise-driven redefinition.

        Parameters
        ----------
        vec : np.ndarray, shape (dim,)
        coherence : float
            Composite coherence from Watcher (used to weight update strength).
        field_energy : float
            Current field energy, stored in trace for downstream context.

        Returns
        -------
        RelationalProfile
            Relational scores across all three timescales.
        """
        # Coherence-weighted learning rate: incoherent vectors update weakly
        # Squaring sharpens the gate — near-zero coherence → near-zero update
        effective_lr = float(np.clip(coherence ** 2, 0.01, 1.0))

        # Cold start: initialize all layers to first vector directly
        if not self._initialized:
            self._short  = vec.copy()
            self._mid    = vec.copy()
            self._long   = vec.copy()
            self._anchor = vec.copy()
            self._prev_anchor   = vec.copy()
            self._prev_velocity = np.zeros(self.dim)
            self._initialized   = True
        else:
            short_lr = (1.0 - self.short_decay) * effective_lr
            mid_lr   = (1.0 - self.mid_decay)   * effective_lr
            long_lr  = (1.0 - self.long_decay)  * effective_lr

            self._short = self._short * (1.0 - short_lr) + vec * short_lr
            self._mid   = self._mid   * (1.0 - mid_lr)   + vec * mid_lr
            self._long  = self._long  * (1.0 - long_lr)  + vec * long_lr

        # Recompute composite anchor
        raw_anchor = (
            self.short_weight * self._short +
            self.mid_weight   * self._mid   +
            self.long_weight  * self._long
        )
        norm = np.linalg.norm(raw_anchor)
        self._anchor = raw_anchor / (norm + 1e-8)

        # Relational profile against all three timescales
        profile = self._relational_profile(vec)

        # Identity stability
        stability = self._update_stability()

        # Autobiographical trace entry
        entry = IdentityEntry(
            anchor       = self._anchor.copy(),
            short        = self._short.copy(),
            mid          = self._mid.copy(),
            long         = self._long.copy(),
            coherence    = coherence,
            field_energy = field_energy,
            timestamp    = time.time(),
            step         = self._step,
        )
        self.identity_trace.append(entry)

        # Episodic snapshot on high-coherence event
        if coherence >= self.snapshot_coherence_threshold:
            self._emit_snapshot(coherence, reason="high_coherence")

        # Transition snapshot: sharp anchor acceleration
        if stability < 0.25 and self._step > 4:
            self._emit_snapshot(coherence, reason="transition")

        # Crystallization pressure
        if (
            coherence        >= self.crystallization_coherence     and
            profile.long     >= self.crystallization_long_relation and
            stability        >= self.crystallization_stability
        ):
            self._emit_crystallization_candidate(vec, coherence, profile.long, stability)

        self._step += 1
        return profile

    # ------------------------------------------------------------------
    # Read access
    # ------------------------------------------------------------------

    def current_anchor(self) -> np.ndarray:
        """Composite identity anchor (normalized)."""
        return self._anchor.copy()

    def anchor_velocity(self) -> float:
        """L2 norm of the anchor's current velocity (rate of change per step)."""
        return float(np.linalg.norm(self._prev_velocity))

    def anchor_short_long_gap(self) -> float:
        """
        Cosine distance between short-term and long-term anchor.
        0.0 = perfectly aligned (identity is stable across timescales)
        2.0 = opposite directions (severe identity fragmentation)
        Used by ManipulationResistanceEngine for drift attack detection.
        """
        cos = self._cosine(self._short, self._long)
        return float(1.0 - np.clip(cos, -1.0, 1.0))

    def short_anchor(self) -> np.ndarray:
        return self._short.copy()

    def mid_anchor(self) -> np.ndarray:
        return self._mid.copy()

    def long_anchor(self) -> np.ndarray:
        return self._long.copy()

    def relational_score(self, vec: np.ndarray) -> RelationalProfile:
        """
        Compute relational profile for `vec` against current anchor state
        without updating any EMA layers.
        """
        return self._relational_profile(vec)

    def identity_stability(self) -> float:
        """
        Current anchor stability ∈ [0, 1].
        Derived from anchor acceleration magnitude.
        Low value = rapid identity shift in progress.
        """
        velocity     = self._anchor - self._prev_anchor
        acceleration = velocity - self._prev_velocity
        accel_norm   = float(np.linalg.norm(acceleration))
        return float(np.clip(1.0 / (1.0 + accel_norm), 0.0, 1.0))

    def recent_trace(self, n: int = 10) -> list:
        """Return the n most recent identity trace entries as dicts."""
        entries = list(self.identity_trace)[-n:]
        return [e.as_dict() for e in entries]

    def recent_snapshots(self, n: int = 5) -> List[EpisodicSnapshot]:
        return self.snapshots[-n:]

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _relational_profile(self, vec: np.ndarray) -> RelationalProfile:
        s = self._cosine(vec, self._short)
        m = self._cosine(vec, self._mid)
        l = self._cosine(vec, self._long)

        # Composite weighted same as anchor blend
        composite = (
            self.short_weight * s +
            self.mid_weight   * m +
            self.long_weight  * l
        )

        return RelationalProfile(
            short     = round(float(s), 6),
            mid       = round(float(m), 6),
            long      = round(float(l), 6),
            composite = round(float(composite), 6),
        )

    def _update_stability(self) -> float:
        """
        Update anchor velocity/acceleration tracking.
        Returns current stability score.
        """
        velocity      = self._anchor - self._prev_anchor
        acceleration  = velocity - self._prev_velocity

        self._prev_velocity = velocity.copy()
        self._prev_anchor   = self._anchor.copy()

        # Track anchor entropy for distributional stability
        p = np.abs(self._anchor)
        p_sum = p.sum()
        if p_sum > 1e-8:
            p = np.clip(p / p_sum, 1e-10, 1.0)
            H = float(-np.sum(p * np.log(p)))
            self._anchor_entropy_history.append(H)

        accel_norm = float(np.linalg.norm(acceleration))
        return float(np.clip(1.0 / (1.0 + accel_norm), 0.0, 1.0))

    def _emit_snapshot(self, coherence: float, reason: str):
        snap = EpisodicSnapshot(
            anchor    = self._anchor.copy(),
            reason    = reason,
            coherence = coherence,
            timestamp = time.time(),
            step      = self._step,
        )
        self.snapshots.append(snap)

    def _emit_crystallization_candidate(
        self,
        vec: np.ndarray,
        coherence: float,
        long_relation: float,
        stability: float,
    ):
        candidate = CrystallizationCandidate(
            vector        = vec.copy(),
            anchor        = self._anchor.copy(),
            coherence     = coherence,
            long_relation = long_relation,
            stability     = stability,
            timestamp     = time.time(),
            step          = self._step,
        )
        self.crystallization_candidates.append(candidate)

        # Also emit a snapshot at crystallization moments
        self._emit_snapshot(coherence, reason="crystallization")

    def _cosine(self, a: np.ndarray, b: np.ndarray) -> float:
        denom = np.linalg.norm(a) * np.linalg.norm(b) + 1e-8
        return float(np.dot(a, b) / denom)
      
