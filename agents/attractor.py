"""
agents/attractor.py

Attractor basin dynamics — stable identity structures from recurrent states.

Attractors form when vectors repeatedly converge on similar regions of the
embedding space. They function as:
  - Semantic gravity wells
  - Identity anchors
  - Belief structures
  - Archetype seeds

Lifecycle
---------
  Formation   : vector added when relational score > formation_threshold
  Pull        : nearby vectors are blended toward the nearest attractor
  Reinforcement: re-encountered attractors grow in strength
  Decay       : inactive attractors weaken over time
  Merge       : attractors that converge too closely are collapsed
  Pruning     : weak attractors below viability threshold are removed
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

import numpy as np


# ---------------------------------------------------------------------------
# AttractorCenter
# ---------------------------------------------------------------------------

@dataclass
class AttractorCenter:
    vector:         np.ndarray
    origin_tokens:  List[str]
    strength:       float = 1.0       # grows on reinforcement
    activation_count: int = 0
    created_at:     float = field(default_factory=time.time)
    last_activated: float = field(default_factory=time.time)
    usage:          float = 1.0       # decays when inactive

    def reinforce(self, amount: float = 0.05):
        self.strength          = min(self.strength + amount, 20.0)
        self.activation_count += 1
        self.last_activated    = time.time()
        self.usage            += 1.0

    def decay(self, rate: float = 0.998):
        self.usage    *= rate
        self.strength *= (0.9995)   # strength decays slower than usage

    def is_viable(self, min_usage: float = 0.1) -> bool:
        return self.usage >= min_usage

    def weighted_pull(self, vec: np.ndarray, blend: float) -> np.ndarray:
        """
        Blend vec toward this attractor center.
        blend=0.0 → no pull, blend=1.0 → snap to center.
        """
        blended = (1.0 - blend) * vec + blend * self.vector
        norm    = np.linalg.norm(blended)
        return (blended / (norm + 1e-8)).astype(np.float32)


# ---------------------------------------------------------------------------
# Attractor
# ---------------------------------------------------------------------------

class Attractor:
    """
    Attractor basin manager.

    Parameters
    ----------
    formation_threshold : float
        Minimum cosine similarity for a vector to seed a new attractor center.
        (Used externally — the loop decides when to call add().)
    pull_threshold : float
        Minimum similarity to the nearest center to apply pull.
    pull_blend : float
        Base blend factor. Scaled by similarity: stronger match = stronger pull.
    merge_threshold : float
        Centers with cosine similarity above this are merged into one.
    max_centers : int
        Maximum number of attractor centers. Weakest are pruned when exceeded.
    decay_rate : float
        Per-step usage decay applied during decay_step().
    """

    def __init__(
        self,
        formation_threshold: float = 0.88,
        pull_threshold:      float = 0.75,
        pull_blend:          float = 0.15,
        merge_threshold:     float = 0.95,
        max_centers:         int   = 64,
        decay_rate:          float = 0.998,
    ):
        self.formation_threshold = formation_threshold
        self.pull_threshold      = pull_threshold
        self.pull_blend          = pull_blend
        self.merge_threshold     = merge_threshold
        self.max_centers         = max_centers
        self.decay_rate          = decay_rate

        self.centers: List[AttractorCenter] = []

    # ------------------------------------------------------------------
    # Add
    # ------------------------------------------------------------------

    def add(
        self,
        vec:    np.ndarray,
        tokens: Optional[List[str]] = None,
        generator=None,
    ) -> AttractorCenter:
        """
        Add a vector as a new attractor center, or reinforce an existing one.

        If a center with similarity > merge_threshold already exists,
        reinforces it rather than creating a duplicate.
        """
        existing = self._find_similar(vec, self.merge_threshold)
        if existing is not None:
            # Soft update the center vector toward the new vector
            merged = 0.9 * existing.vector + 0.1 * vec
            norm   = np.linalg.norm(merged)
            existing.vector = (merged / (norm + 1e-8)).astype(np.float32)
            existing.reinforce(amount=0.1)
            if generator and tokens:
                generator.signal_attractor(tokens, delta=0.3)
            return existing

        center = AttractorCenter(
            vector        = vec.copy().astype(np.float32),
            origin_tokens = list(tokens or []),
        )
        self.centers.append(center)

        if len(self.centers) > self.max_centers:
            self._prune_weakest()

        if generator and tokens:
            generator.signal_attractor(tokens, delta=0.5)

        return center

    # ------------------------------------------------------------------
    # Pull
    # ------------------------------------------------------------------

    def pull(
        self,
        vec:    np.ndarray,
        generator=None,
    ) -> np.ndarray:
        """
        Blend vec toward its nearest attractor center (if above threshold).

        Pull strength scales with similarity — close matches pull harder.
        Returns the (possibly modified) vector, always normalized.
        """
        if not self.centers:
            return vec

        best_center, best_score = self._nearest(vec)

        if best_score < self.pull_threshold:
            return vec

        # Scale blend by similarity: at threshold → minimal pull,
        # at 1.0 → full pull_blend
        t       = (best_score - self.pull_threshold) / (1.0 - self.pull_threshold + 1e-8)
        blend   = self.pull_blend * float(np.clip(t, 0.0, 1.0))

        best_center.reinforce(amount=0.02 * best_score)

        if generator and best_center.origin_tokens:
            generator.signal_attractor(best_center.origin_tokens, delta=0.1)

        return best_center.weighted_pull(vec, blend)

    # ------------------------------------------------------------------
    # Merge
    # ------------------------------------------------------------------

    def merge_pass(self):
        """
        Scan for pairs of centers that are too similar and merge them.
        The stronger center absorbs the weaker one.
        Runs in O(n²) — call periodically, not every step.
        """
        merged = True
        while merged and len(self.centers) > 1:
            merged = False
            for i in range(len(self.centers)):
                for j in range(i + 1, len(self.centers)):
                    if j >= len(self.centers):
                        break
                    a, b = self.centers[i], self.centers[j]
                    sim  = self._cosine(a.vector, b.vector)
                    if sim >= self.merge_threshold:
                        # Stronger absorbs weaker
                        dominant   = a if a.strength >= b.strength else b
                        recessive  = b if dominant is a else a
                        # Weighted merge
                        total      = dominant.strength + recessive.strength
                        w_d        = dominant.strength / total
                        w_r        = recessive.strength / total
                        merged_vec = w_d * dominant.vector + w_r * recessive.vector
                        norm       = np.linalg.norm(merged_vec)
                        dominant.vector = (merged_vec / (norm + 1e-8)).astype(np.float32)
                        dominant.strength += recessive.strength * 0.5
                        dominant.activation_count += recessive.activation_count
                        self.centers.remove(recessive)
                        merged = True
                        break
                if merged:
                    break

    # ------------------------------------------------------------------
    # Decay step
    # ------------------------------------------------------------------

    def decay_step(self):
        """
        Apply usage decay and prune non-viable centers.
        Call periodically from autonomous_cycle.
        """
        for center in self.centers:
            center.decay(self.decay_rate)

        self.centers = [c for c in self.centers if c.is_viable()]

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------

    def nearest_centers(
        self,
        vec:   np.ndarray,
        top_k: int = 3,
    ) -> List[Tuple[AttractorCenter, float]]:
        """Return top_k centers sorted by cosine similarity."""
        if not self.centers:
            return []
        scored = [(c, self._cosine(vec, c.vector)) for c in self.centers]
        return sorted(scored, key=lambda x: x[1], reverse=True)[:top_k]

    def basin_centroid(self) -> Optional[np.ndarray]:
        """Strength-weighted centroid of all attractor centers."""
        if not self.centers:
            return None
        total_strength = sum(c.strength for c in self.centers)
        if total_strength < 1e-8:
            return None
        weighted = sum(
            c.vector * (c.strength / total_strength)
            for c in self.centers
        )
        norm = np.linalg.norm(weighted)
        return (weighted / (norm + 1e-8)).astype(np.float32)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _nearest(self, vec: np.ndarray) -> Tuple[AttractorCenter, float]:
        scored = [(c, self._cosine(vec, c.vector)) for c in self.centers]
        return max(scored, key=lambda x: x[1])

    def _find_similar(
        self,
        vec:       np.ndarray,
        threshold: float,
    ) -> Optional[AttractorCenter]:
        if not self.centers:
            return None
        best, score = self._nearest(vec)
        return best if score >= threshold else None

    def _prune_weakest(self):
        weakest = min(self.centers, key=lambda c: c.strength * c.usage)
        self.centers.remove(weakest)

    def _cosine(self, a: np.ndarray, b: np.ndarray) -> float:
        return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-8))

    # ------------------------------------------------------------------
    # Diagnostics
    # ------------------------------------------------------------------

    def summary(self) -> dict:
        if not self.centers:
            return {"count": 0}
        strengths = [c.strength for c in self.centers]
        return {
            "count":          len(self.centers),
            "mean_strength":  round(float(np.mean(strengths)), 4),
            "max_strength":   round(float(np.max(strengths)), 4),
            "total_activations": sum(c.activation_count for c in self.centers),
        }
