"""
agents/dependency_monitor.py

DependencyMonitor — injection source concentration monitor.

Measures how concentrated recent field injections are across sources
using the Herfindahl-Hirschman Index (HHI).

HHI = Σ(market_share²)
  0.0 → perfectly distributed across many sources
  1.0 → all injections from one source (monopoly)

Subscribes to GovernanceFeedback so it tracks only allowed injections —
rejected/quarantined attempts don't count toward concentration.

Reports to SelfhoodGovernance. Makes no decisions of its own.
"""

from __future__ import annotations

import collections
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from agents.trust_ledger import GovernanceFeedback


# ---------------------------------------------------------------------------
# Risk levels
# ---------------------------------------------------------------------------

class DependencyRisk:
    LOW      = "LOW"       # HHI < 0.30
    MODERATE = "MODERATE"  # HHI 0.30–0.50
    HIGH     = "HIGH"      # HHI 0.50–0.70
    CRITICAL = "CRITICAL"  # HHI >= 0.70


# ---------------------------------------------------------------------------
# DependencyReport
# ---------------------------------------------------------------------------

@dataclass
class DependencyReport:
    """
    Advisory output of DependencyMonitor.get_report().
    SelfhoodGovernance decides how to act on it.
    """
    hhi_score:            float                  # 0.0–1.0
    dominant_source:      Optional[str]          # source_id with highest share
    dominant_share:       float                  # fraction from dominant source
    risk_level:           str                    # DependencyRisk constant
    source_distribution:  Dict[str, float]       # source_id → share
    window_size:          int                    # actual entries in window
    recommendation:       str                   # "ok" | "rebalance" | "restrict" | "dream_cycle"


# ---------------------------------------------------------------------------
# DependencyMonitor
# ---------------------------------------------------------------------------

class DependencyMonitor:
    """
    Rolling HHI concentration monitor over injection sources.

    Parameters
    ----------
    window_size : int
        Maximum injections tracked in the rolling window.
    low_threshold : float
        HHI below this → LOW risk.
    moderate_threshold : float
        HHI below this → MODERATE risk.
    high_threshold : float
        HHI below this → HIGH risk.
        HHI at or above this → CRITICAL.
    """

    def __init__(
        self,
        window_size:         int   = 128,
        low_threshold:       float = 0.30,
        moderate_threshold:  float = 0.50,
        high_threshold:      float = 0.70,
    ):
        self.window_size        = window_size
        self.low_threshold      = low_threshold
        self.moderate_threshold = moderate_threshold
        self.high_threshold     = high_threshold

        # Bounded rolling window of source_ids for allowed injections
        self._window: collections.deque = collections.deque(maxlen=window_size)
        # Attractor source index: source_id → count of attractor centers it seeded
        self._attractor_sources: Dict[str, int] = collections.defaultdict(int)

    # ------------------------------------------------------------------
    # Feedback subscription (called by SelfhoodGovernance.subscribe_feedback)
    # ------------------------------------------------------------------

    def receive_feedback(self, feedback: "GovernanceFeedback"):
        """
        Record the source of every allowed injection.
        Rejected/quarantined attempts are NOT counted — they never reached the field.
        """
        if feedback.decision in ("allow", "allow_weakened", "monitor"):
            self._window.append(feedback.source_id)

    def record_attractor(self, source_id: str):
        """
        Called by AutonomousCycle when an attractor center is formed.
        Tracks which source seeded each attractor for monopoly detection.
        """
        self._attractor_sources[source_id] += 1

    # ------------------------------------------------------------------
    # Report
    # ------------------------------------------------------------------

    def get_report(self) -> DependencyReport:
        """
        Compute current HHI and return advisory report.
        O(n) where n = number of unique sources in window (typically small).
        """
        if not self._window:
            return DependencyReport(
                hhi_score           = 0.0,
                dominant_source     = None,
                dominant_share      = 0.0,
                risk_level          = DependencyRisk.LOW,
                source_distribution = {},
                window_size         = 0,
                recommendation      = "ok",
            )

        total  = len(self._window)
        counts: Dict[str, int] = collections.Counter(self._window)
        shares: Dict[str, float] = {src: count / total for src, count in counts.items()}

        hhi             = float(sum(s ** 2 for s in shares.values()))
        dominant        = max(shares, key=shares.get)
        dominant_share  = shares[dominant]

        risk = self._risk_level(hhi)
        rec  = self._recommendation(risk, dominant, dominant_share)

        return DependencyReport(
            hhi_score           = round(hhi, 4),
            dominant_source     = dominant,
            dominant_share      = round(dominant_share, 4),
            risk_level          = risk,
            source_distribution = {k: round(v, 4) for k, v in shares.items()},
            window_size         = total,
            recommendation      = rec,
        )

    def attractor_monopoly_ratio(self) -> float:
        """
        Fraction of attractor centers seeded by the single most dominant source.
        0.0 = diverse | 1.0 = all attractors from one source.
        Used by ManipulationResistanceEngine for COHERENCE_FLOOD detection.
        """
        if not self._attractor_sources:
            return 0.0
        total = sum(self._attractor_sources.values())
        if total == 0:
            return 0.0
        dominant = max(self._attractor_sources.values())
        return round(dominant / total, 4)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _risk_level(self, hhi: float) -> str:
        if hhi >= self.high_threshold:
            return DependencyRisk.CRITICAL
        if hhi >= self.moderate_threshold:
            return DependencyRisk.HIGH
        if hhi >= self.low_threshold:
            return DependencyRisk.MODERATE
        return DependencyRisk.LOW

    def _recommendation(self, risk: str, dominant: str, share: float) -> str:
        if risk == DependencyRisk.CRITICAL:
            return "dream_cycle"
        if risk == DependencyRisk.HIGH:
            return "restrict"
        if risk == DependencyRisk.MODERATE:
            return "rebalance"
        return "ok"

    # ------------------------------------------------------------------
    # Diagnostics
    # ------------------------------------------------------------------

    def summary(self) -> dict:
        report = self.get_report()
        return {
            "hhi":              report.hhi_score,
            "risk":             report.risk_level,
            "dominant_source":  report.dominant_source,
            "dominant_share":   report.dominant_share,
            "window_size":      report.window_size,
            "attractor_monopoly": self.attractor_monopoly_ratio(),
        }
