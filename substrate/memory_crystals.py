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
substrate/memory_crystals.py

Memory crystallization — persistent attractor structures from high-coherence states.

A crystal forms when a vector simultaneously satisfies:
    composite coherence  >= coherence_threshold
    temporal stability   >= stability_threshold
    relational score     >= relation_threshold

Once formed, crystals:
  - Reinforce on re-activation (stability grows)
  - Decay slowly when not activated
  - Influence the field on activation (soft injection)
  - Deduplicate against existing crystals (merge if too similar)
  - Signal back to the Generator's symbolic ecology

Crystals are the system's long-term memory:
    beliefs, archetypes, values, symbolic cores.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

import numpy as np


# ---------------------------------------------------------------------------
# MemoryCrystal
# ---------------------------------------------------------------------------

@dataclass
class MemoryCrystal:
    """
    A single crystallized memory attractor.

    Parameters
    ----------
    vector : np.ndarray
        The normalized latent vector at crystallization time.
    origin_tokens : list of str
        Tokens that generated this vector (for ecology signal relay).
    stability : float
        Initial stability score (from crystallization_pressure at formation).
    coherence : float
        Coherence score at formation time.
    """
    vector:        np.ndarray
    origin_tokens: List[str]
    stability:     float
    coherence:     float
    activation_count: int   = 0
    created_at:    float    = field(default_factory=time.time)
    last_activated: float   = field(default_factory=time.time)
    usage:         float    = 1.0        # decays over time like SymbolState

    def reinforce(self, amount: float = 0.02):
        """Strengthen on re-activation."""
        self.stability        = min(self.stability * (1.0 + amount), 10.0)
        self.activation_count += 1
        self.last_activated   = time.time()
        self.usage            += 1.0

    def decay(self, rate: float = 0.9995):
        """Slow usage decay — crystals persist much longer than raw vectors."""
        self.usage *= rate

    def age(self) -> float:
        """Seconds since last activation."""
        return time.time() - self.last_activated

    def is_viable(self, min_usage: float = 0.01) -> bool:
        return self.usage >= min_usage


# ---------------------------------------------------------------------------
# CrystalStore
# ---------------------------------------------------------------------------

class CrystalStore:
    """
    Crystal lifecycle manager.

    Responsibilities
    ----------------
    - Evaluate crystallization candidates (CoherenceReport → maybe_crystallize)
    - Deduplicate against existing crystals (merge if cosine similarity > merge_threshold)
    - Reinforce existing crystals on re-encounter
    - Decay inactive crystals
    - Influence the ResonanceField on activation
    - Relay crystal_binding signals to the Generator's symbolic ecology

    Parameters
    ----------
    coherence_threshold : float
        Minimum composite coherence for crystallization.
    stability_threshold : float
        Minimum crystallization_pressure (G×T) for crystallization.
    relation_threshold : float
        Minimum long-term relational score for crystallization.
    merge_threshold : float
        Cosine similarity above which two crystals are merged.
    max_crystals : int
        Maximum number of crystals. Oldest/weakest are evicted when exceeded.
    decay_rate : float
        Per-step usage decay applied during decay_step().
    field_injection_strength : float
        Strength of soft field injection on crystal activation.
    """

    def __init__(
        self,
        coherence_threshold:       float = 0.75,
        stability_threshold:       float = 0.60,
        relation_threshold:        float = 0.80,
        merge_threshold:           float = 0.92,
        max_crystals:              int   = 512,
        decay_rate:                float = 0.9995,
        field_injection_strength:  float = 0.3,
    ):
        self.coherence_threshold      = coherence_threshold
        self.stability_threshold      = stability_threshold
        self.relation_threshold       = relation_threshold
        self.merge_threshold          = merge_threshold
        self.max_crystals             = max_crystals
        self.decay_rate               = decay_rate
        self.field_injection_strength = field_injection_strength

        self.crystals: List[MemoryCrystal] = []

    # ------------------------------------------------------------------
    # Crystallization
    # ------------------------------------------------------------------

    def maybe_crystallize(
        self,
        vec:               np.ndarray,
        composite_coherence: float,
        crystallization_pressure: float,
        long_relation:     float,
        origin_tokens:     Optional[List[str]] = None,
        field=None,
        generator=None,
    ) -> Optional[MemoryCrystal]:
        """
        Evaluate a vector as a crystallization candidate.

        Returns the crystal if formed or reinforced, else None.

        Parameters
        ----------
        vec : np.ndarray
        composite_coherence : float
            From CoherenceReport.composite
        crystallization_pressure : float
            From CoherenceReport.crystallization_pressure (G × T)
        long_relation : float
            From RelationalProfile.long
        origin_tokens : list of str or None
            Source tokens for ecology signal relay.
        field : ResonanceField or None
            If provided, activated crystals inject softly into the field.
        generator : Generator or None
            If provided, crystal_binding signal is relayed to the ecology.
        """
        # Check thresholds
        if composite_coherence < self.coherence_threshold:
            return None
        if crystallization_pressure < self.stability_threshold:
            return None
        if long_relation < self.relation_threshold:
            return None

        # Check for existing similar crystal → reinforce instead of duplicate
        existing = self._find_similar(vec)
        if existing is not None:
            existing.reinforce()
            self._activate_crystal(existing, field, generator, origin_tokens)
            return existing

        # Form new crystal
        crystal = MemoryCrystal(
            vector        = vec.copy().astype(np.float32),
            origin_tokens = list(origin_tokens or []),
            stability     = crystallization_pressure,
            coherence     = composite_coherence,
        )
        self.crystals.append(crystal)

        if len(self.crystals) > self.max_crystals:
            self._evict_weakest()

        self._activate_crystal(crystal, field, generator, origin_tokens)
        return crystal

    # ------------------------------------------------------------------
    # Activation
    # ------------------------------------------------------------------

    def activate_nearest(
        self,
        vec:       np.ndarray,
        field=None,
        generator=None,
        top_k:     int = 3,
    ) -> List[Tuple[MemoryCrystal, float]]:
        """
        Find and activate the top_k crystals nearest to vec.
        Activated crystals reinforce and optionally inject into the field.

        Returns list of (crystal, cosine_score) pairs.
        """
        if not self.crystals:
            return []

        scored = self._score_all(vec)
        scored = sorted(scored, key=lambda x: x[1], reverse=True)[:top_k]

        results = []
        for crystal, score in scored:
            crystal.reinforce(amount=0.01 * score)
            self._activate_crystal(crystal, field, generator, crystal.origin_tokens)
            results.append((crystal, score))

        return results

    # ------------------------------------------------------------------
    # Field influence
    # ------------------------------------------------------------------

    def _activate_crystal(
        self,
        crystal:   MemoryCrystal,
        field,
        generator,
        tokens:    Optional[List[str]],
    ):
        """
        Side effects on activation:
        - Soft field injection (if field provided)
        - crystal_binding signal relay (if generator provided)
        """
        if field is not None:
            field.inject(crystal.vector, strength=self.field_injection_strength)

        if generator is not None and tokens:
            generator.signal_crystal(tokens, delta=0.3)

    # ------------------------------------------------------------------
    # Decay step
    # ------------------------------------------------------------------

    def decay_step(self):
        """
        Apply usage decay to all crystals and evict non-viable ones.
        Call periodically from autonomous_cycle (e.g. on "stabilize" rhythm).
        """
        for crystal in self.crystals:
            crystal.decay(self.decay_rate)

        self.crystals = [c for c in self.crystals if c.is_viable()]

    # ------------------------------------------------------------------
    # Nearest / query
    # ------------------------------------------------------------------

    def nearest(
        self,
        vec:   np.ndarray,
        top_k: int = 5,
    ) -> List[Tuple[MemoryCrystal, float]]:
        """Return top_k crystals by cosine similarity to vec."""
        if not self.crystals:
            return []
        scored = self._score_all(vec)
        return sorted(scored, key=lambda x: x[1], reverse=True)[:top_k]

    def centroid(self) -> Optional[np.ndarray]:
        """Normalized centroid of all crystal vectors."""
        if not self.crystals:
            return None
        mean = np.mean([c.vector for c in self.crystals], axis=0)
        norm = np.linalg.norm(mean)
        return (mean / (norm + 1e-8)).astype(np.float32)

    def strongest(self, n: int = 5) -> List[MemoryCrystal]:
        """Return n crystals with highest stability."""
        return sorted(self.crystals, key=lambda c: c.stability, reverse=True)[:n]

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _find_similar(self, vec: np.ndarray) -> Optional[MemoryCrystal]:
        """Find an existing crystal with cosine similarity > merge_threshold."""
        if not self.crystals:
            return None
        scored = self._score_all(vec)
        if not scored:
            return None
        best_crystal, best_score = max(scored, key=lambda x: x[1])
        if best_score >= self.merge_threshold:
            return best_crystal
        return None

    def _score_all(self, vec: np.ndarray) -> List[Tuple[MemoryCrystal, float]]:
        """Vectorized cosine scoring against all crystals."""
        if not self.crystals:
            return []
        matrix = np.stack([c.vector for c in self.crystals])
        q_norm = vec / (np.linalg.norm(vec) + 1e-8)
        m_norm = matrix / (np.linalg.norm(matrix, axis=1, keepdims=True) + 1e-8)
        scores = (m_norm @ q_norm).tolist()
        return list(zip(self.crystals, scores))

    def _evict_weakest(self):
        """Remove the crystal with the lowest stability × usage product."""
        if not self.crystals:
            return
        weakest = min(self.crystals, key=lambda c: c.stability * c.usage)
        self.crystals.remove(weakest)

    # ------------------------------------------------------------------
    # Diagnostics
    # ------------------------------------------------------------------

    def summary(self) -> dict:
        if not self.crystals:
            return {"count": 0}
        stabilities = [c.stability for c in self.crystals]
        usages      = [c.usage for c in self.crystals]
        return {
            "count":           len(self.crystals),
            "mean_stability":  round(float(np.mean(stabilities)), 4),
            "max_stability":   round(float(np.max(stabilities)), 4),
            "mean_usage":      round(float(np.mean(usages)), 4),
            "total_activations": sum(c.activation_count for c in self.crystals),
        }
