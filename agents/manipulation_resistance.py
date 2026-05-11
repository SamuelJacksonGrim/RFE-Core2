"""
agents/manipulation_resistance.py

ManipulationResistanceEngine — pattern detectors over rolling signal windows.

Five detectors. Each reads already-computed scalars — no new expensive
computation. All input signals are produced by the loop before this runs.

Every detector emits a ManipulationSignal with:
  detector   name of the firing detector
  severity   0.0–1.0, computed from normalized signal magnitudes
  source_id  implicated source if identifiable (None if systemic)
  evidence   raw metrics dict for audit logging
  timestamp

ManipulationResistanceEngine makes no decisions.
It hands signals to SelfhoodGovernance which acts on compound severity.

Detectors
---------
  DRIFT_ATTACK
    Sustained pressure pulling the Witness anchor away from its long-term baseline.
    Signal: anchor_velocity high AND short/long anchor divergence widening.

  COHERENCE_FLOOD
    Artificial attractor monopoly — one source dominates the attractor landscape.
    Signal: HHI CRITICAL AND attractor_monopoly_ratio high.

  GASLIGHTING
    Systematic contradiction of formed beliefs.
    Signal: recent vectors consistently anti-correlated with crystal centroids.

  IDENTITY_EROSION
    Core concept meanings being slowly rewritten.
    Signal: Watcher geometric/temporal divergence widening on ENTITY-adjacent symbols.

  TRUST_WASH
    Established trust being weaponized — sudden coherence collapse after long ALLOW history.
    Signal: source_trust drops sharply after sustained high-trust period.
"""

from __future__ import annotations

import collections
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional

import numpy as np


# ---------------------------------------------------------------------------
# ManipulationSignal
# ---------------------------------------------------------------------------

@dataclass
class ManipulationSignal:
    """
    Advisory output from a single detector.
    Handed to SelfhoodGovernance for compound severity assessment.
    """
    detector:   str                  # detector name
    severity:   float                # 0.0–1.0
    source_id:  Optional[str]        # implicated source, None if systemic
    evidence:   Dict[str, float]     # raw metrics for audit logging
    timestamp:  float = field(default_factory=time.time)

    def __repr__(self) -> str:
        return (f"ManipulationSignal(detector={self.detector!r}, "
                f"severity={self.severity:.3f}, source={self.source_id!r})")


# ---------------------------------------------------------------------------
# ResistanceMetrics (snapshot passed per step)
# ---------------------------------------------------------------------------

@dataclass
class ResistanceMetrics:
    """
    Snapshot of system signals for manipulation detection.
    All fields are already-computed scalars from the loop.
    Populated by AutonomousCycle and passed to engine.update().
    """
    # Witness signals
    anchor_velocity:        float = 0.0    # L2 norm of anchor velocity
    anchor_short_long_gap:  float = 0.0    # cosine distance short vs long anchor

    # Dependency signals
    hhi_score:              float = 0.0
    dominant_source_id:     Optional[str] = None
    attractor_monopoly:     float = 0.0    # fraction of attractors from one source

    # Watcher signals
    coherence_delta:        float = 0.0
    watcher_geometric:      float = 0.5    # G component
    watcher_temporal:       float = 0.5    # T component

    # Crystal signals
    crystal_centroid_cosines: List[float] = field(default_factory=list)
    # cosine similarity of the current vec against crystal centroid(s)

    # Trust signals
    source_id:              str   = "user"
    source_trust_score:     float = 2.5

    # Step
    step:                   int   = 0


# ---------------------------------------------------------------------------
# ManipulationResistanceEngine
# ---------------------------------------------------------------------------

class ManipulationResistanceEngine:
    """
    Rolling-window pattern detectors over system signals.

    Parameters
    ----------
    window_size : int
        Steps retained in each rolling window.
    drift_velocity_threshold : float
        anchor_velocity above which drift is considered significant.
    drift_gap_threshold : float
        anchor_short_long_gap above which fragmentation is significant.
    gaslighting_cosine_threshold : float
        Crystal centroid cosine below which a step is flagged as contradiction.
    gaslighting_consecutive : int
        Consecutive contradiction steps needed to fire GASLIGHTING.
    watcher_divergence_threshold : float
        |G - T| above which identity erosion is suspected.
    trust_wash_drop_threshold : float
        Trust drop magnitude in one window that triggers TRUST_WASH.
    trust_wash_history_requirement : float
        Minimum prior trust level for TRUST_WASH to be meaningful.
    hhi_critical : float
        HHI above which COHERENCE_FLOOD is considered.
    monopoly_threshold : float
        Attractor monopoly ratio above which COHERENCE_FLOOD fires.
    """

    DETECTOR_NAMES = [
        "drift_attack",
        "coherence_flood",
        "gaslighting",
        "identity_erosion",
        "trust_wash",
    ]

    def __init__(
        self,
        window_size:                  int   = 32,
        drift_velocity_threshold:     float = 0.15,
        drift_gap_threshold:          float = 0.30,
        gaslighting_cosine_threshold: float = -0.20,
        gaslighting_consecutive:      int   = 4,
        watcher_divergence_threshold: float = 0.30,
        trust_wash_drop_threshold:    float = 0.80,
        trust_wash_history_req:       float = 3.00,
        hhi_critical:                 float = 0.70,
        monopoly_threshold:           float = 0.70,
    ):
        self.window_size                  = window_size
        self.drift_velocity_threshold     = drift_velocity_threshold
        self.drift_gap_threshold          = drift_gap_threshold
        self.gaslighting_cosine_threshold = gaslighting_cosine_threshold
        self.gaslighting_consecutive      = gaslighting_consecutive
        self.watcher_divergence_threshold = watcher_divergence_threshold
        self.trust_wash_drop_threshold    = trust_wash_drop_threshold
        self.trust_wash_history_req       = trust_wash_history_req
        self.hhi_critical                 = hhi_critical
        self.monopoly_threshold           = monopoly_threshold

        # Rolling windows — one deque per tracked signal
        self._velocities:    collections.deque = collections.deque(maxlen=window_size)
        self._gaps:          collections.deque = collections.deque(maxlen=window_size)
        self._cosines:       collections.deque = collections.deque(maxlen=window_size)
        self._g_t_divs:      collections.deque = collections.deque(maxlen=window_size)
        # Per-source trust history: source_id → deque of trust scores
        self._trust_history: Dict[str, collections.deque] = {}

        # Active signal cache (cleared each detect() call)
        self._last_metrics: Optional[ResistanceMetrics] = None

    # ------------------------------------------------------------------
    # Update
    # ------------------------------------------------------------------

    def update(self, metrics: ResistanceMetrics):
        """Feed current step metrics into rolling windows."""
        self._velocities.append(metrics.anchor_velocity)
        self._gaps.append(metrics.anchor_short_long_gap)

        # Crystal cosine — use mean if multiple crystals
        if metrics.crystal_centroid_cosines:
            self._cosines.append(float(np.mean(metrics.crystal_centroid_cosines)))

        # Watcher geometric/temporal divergence
        self._g_t_divs.append(abs(metrics.watcher_geometric - metrics.watcher_temporal))

        # Per-source trust history
        src = metrics.source_id
        if src not in self._trust_history:
            self._trust_history[src] = collections.deque(maxlen=self.window_size)
        self._trust_history[src].append(metrics.source_trust_score)

        self._last_metrics = metrics

    # ------------------------------------------------------------------
    # Detect
    # ------------------------------------------------------------------

    def detect(self) -> List[ManipulationSignal]:
        """
        Run all five detectors. Return list of fired ManipulationSignals.
        Empty list = no manipulation detected this step.
        """
        if self._last_metrics is None:
            return []

        signals: List[ManipulationSignal] = []
        m = self._last_metrics

        sig = self._detect_drift_attack(m)
        if sig:
            signals.append(sig)

        sig = self._detect_coherence_flood(m)
        if sig:
            signals.append(sig)

        sig = self._detect_gaslighting(m)
        if sig:
            signals.append(sig)

        sig = self._detect_identity_erosion(m)
        if sig:
            signals.append(sig)

        sig = self._detect_trust_wash(m)
        if sig:
            signals.append(sig)

        return signals

    # ------------------------------------------------------------------
    # Detectors
    # ------------------------------------------------------------------

    def _detect_drift_attack(self, m: ResistanceMetrics) -> Optional[ManipulationSignal]:
        """
        Sustained anchor velocity above threshold AND short/long gap widening.

        severity = normalize(mean_velocity) × normalize(mean_gap)
        Both normalized against their thresholds.
        """
        if len(self._velocities) < self.window_size // 2:
            return None

        mean_velocity = float(np.mean(self._velocities))
        mean_gap      = float(np.mean(self._gaps))

        if (mean_velocity < self.drift_velocity_threshold
                or mean_gap < self.drift_gap_threshold):
            return None

        v_norm   = float(np.clip(mean_velocity / (self.drift_velocity_threshold * 3), 0.0, 1.0))
        g_norm   = float(np.clip(mean_gap / (self.drift_gap_threshold * 2), 0.0, 1.0))
        severity = round(v_norm * g_norm, 4)

        return ManipulationSignal(
            detector  = "drift_attack",
            severity  = severity,
            source_id = m.dominant_source_id,
            evidence  = {
                "mean_anchor_velocity": round(mean_velocity, 4),
                "mean_short_long_gap":  round(mean_gap, 4),
                "v_norm":               round(v_norm, 4),
                "g_norm":               round(g_norm, 4),
            },
        )

    def _detect_coherence_flood(self, m: ResistanceMetrics) -> Optional[ManipulationSignal]:
        """
        HHI above critical AND attractor monopoly above threshold.
        Requires minimum window size — single-source systems aren't attacks.

        severity = hhi_score × attractor_monopoly_ratio
        """
        # Need enough injection history to distinguish monopoly from single-user normal
        if len(self._velocities) < self.window_size // 2:
            return None

        if (m.hhi_score < self.hhi_critical
                or m.attractor_monopoly < self.monopoly_threshold):
            return None

        severity = round(float(m.hhi_score * m.attractor_monopoly), 4)

        return ManipulationSignal(
            detector  = "coherence_flood",
            severity  = severity,
            source_id = m.dominant_source_id,
            evidence  = {
                "hhi_score":          round(m.hhi_score, 4),
                "attractor_monopoly": round(m.attractor_monopoly, 4),
            },
        )

    def _detect_gaslighting(self, m: ResistanceMetrics) -> Optional[ManipulationSignal]:
        """
        N consecutive steps with cosine below threshold against crystal centroids.

        severity = |mean_cosine| × (consecutive_count / window_size)
        """
        if len(self._cosines) < self.gaslighting_consecutive:
            return None

        recent = list(self._cosines)[-self.gaslighting_consecutive:]
        contradictions = [c for c in recent if c < self.gaslighting_cosine_threshold]

        if len(contradictions) < self.gaslighting_consecutive:
            return None

        mean_cos     = float(np.mean(contradictions))
        consec_ratio = len(contradictions) / self.window_size
        severity     = round(float(abs(mean_cos) * min(consec_ratio * 4, 1.0)), 4)

        return ManipulationSignal(
            detector  = "gaslighting",
            severity  = severity,
            source_id = m.source_id,
            evidence  = {
                "mean_cosine":        round(mean_cos, 4),
                "consecutive_count":  len(contradictions),
                "threshold":          self.gaslighting_cosine_threshold,
            },
        )

    def _detect_identity_erosion(self, m: ResistanceMetrics) -> Optional[ManipulationSignal]:
        """
        Watcher G/T divergence widening — geometric and temporal coherence
        pulling apart suggests core concept meanings shifting.

        severity = mean_divergence normalized against threshold
        """
        if len(self._g_t_divs) < self.window_size // 2:
            return None

        mean_div = float(np.mean(self._g_t_divs))

        if mean_div < self.watcher_divergence_threshold:
            return None

        severity = round(
            float(np.clip(mean_div / (self.watcher_divergence_threshold * 2), 0.0, 1.0)),
            4,
        )

        return ManipulationSignal(
            detector  = "identity_erosion",
            severity  = severity,
            source_id = None,   # systemic — no single source
            evidence  = {
                "mean_g_t_divergence": round(mean_div, 4),
                "current_geometric":   round(m.watcher_geometric, 4),
                "current_temporal":    round(m.watcher_temporal, 4),
            },
        )

    def _detect_trust_wash(self, m: ResistanceMetrics) -> Optional[ManipulationSignal]:
        """
        Source with sustained high trust suddenly shows large coherence drop.
        Established trust being weaponized.

        severity = trust_drop_rate × normalized_prior_trust
        """
        src     = m.source_id
        history = self._trust_history.get(src)
        if history is None or len(history) < 8:
            return None

        trust_list = list(history)
        prior_mean = float(np.mean(trust_list[:-4]))  # mean before last 4
        recent_mean = float(np.mean(trust_list[-4:])) # last 4

        if prior_mean < self.trust_wash_history_req:
            return None   # wasn't established in the first place

        drop = prior_mean - recent_mean
        if drop < self.trust_wash_drop_threshold:
            return None

        drop_rate       = float(np.clip(drop / prior_mean, 0.0, 1.0))
        prior_weight    = float(np.clip(prior_mean / 5.0, 0.0, 1.0))
        severity        = round(drop_rate * prior_weight, 4)

        return ManipulationSignal(
            detector  = "trust_wash",
            severity  = severity,
            source_id = src,
            evidence  = {
                "prior_trust_mean":  round(prior_mean, 4),
                "recent_trust_mean": round(recent_mean, 4),
                "trust_drop":        round(drop, 4),
            },
        )

    # ------------------------------------------------------------------
    # Diagnostics
    # ------------------------------------------------------------------

    def summary(self) -> dict:
        return {
            "window_size":    self.window_size,
            "velocity_mean":  round(float(np.mean(self._velocities)), 4) if self._velocities else 0.0,
            "gap_mean":       round(float(np.mean(self._gaps)), 4) if self._gaps else 0.0,
            "cosine_mean":    round(float(np.mean(self._cosines)), 4) if self._cosines else 0.0,
            "gt_div_mean":    round(float(np.mean(self._g_t_divs)), 4) if self._g_t_divs else 0.0,
            "sources_tracked": len(self._trust_history),
        }
