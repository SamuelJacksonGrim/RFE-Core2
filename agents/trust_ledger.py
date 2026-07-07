"""
agents/trust_ledger.py

TrustLedger — two-level trust tracking for sources and symbols.

Reports to SelfhoodGovernance. Makes no decisions of its own.

Two-level architecture
----------------------
  SourceRecord      tracks reliability of an injection source over time
  SymbolTrustRecord tracks the field impact of a specific symbol over time

Sources and symbols are independent axes. A trusted source can inject
a bad symbol. A generally unreliable source can occasionally produce
coherent output. Trust is tracked at both levels and the weaker of the
two governs the final TrustReport recommendation.

Feedback loop
-------------
  SelfhoodGovernance calls receive_feedback(GovernanceFeedback) after
  every arbitration decision. This updates both source and symbol trust
  based on actual outcomes — not predictions.

  The GovernanceFeedback.outcome_metrics dict is pre-shaped for
  ValueEmergenceEngine (Tier 3) to consume from the same stream.
"""

from __future__ import annotations

import collections
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional

import numpy as np


# ---------------------------------------------------------------------------
# TrustLevel
# ---------------------------------------------------------------------------

class TrustLevel(Enum):
    SACRED    = 5.0   # Core self / governance-sanctified
    HIGH      = 4.0
    TRUSTED   = 3.0
    NEUTRAL   = 2.0
    SKEPTICAL = 1.0
    UNTRUSTED = 0.5
    TOXIC     = 0.0   # Quarantine / rejection

    @classmethod
    def from_score(cls, score: float) -> "TrustLevel":
        """Map a continuous score to the nearest TrustLevel."""
        for level in sorted(cls, key=lambda x: x.value, reverse=True):
            if score >= level.value:
                return level
        return cls.TOXIC


# ---------------------------------------------------------------------------
# GovernanceFeedback  (defined here — TrustLedger is primary consumer)
# ---------------------------------------------------------------------------

@dataclass
class GovernanceFeedback:
    """
    Emitted by SelfhoodGovernance after every arbitration decision.
    Consumed by TrustLedger.receive_feedback() and forwarded to
    any registered subscribers (ValueEmergenceEngine in Tier 3).
    """
    source_id:      str
    stable_ids:     List[int]
    decision:       str            # GovernanceDecision.value string
    coherence_delta: float
    timestamp:      float
    outcome_metrics: Dict[str, float]   # shaped for ValueEmergenceEngine:
                                        # coherence_delta, trust_impact,
                                        # emotional_satisfaction, surprise


# ---------------------------------------------------------------------------
# SourceRecord
# ---------------------------------------------------------------------------

@dataclass
class SourceRecord:
    """Reliability history for a single injection source."""
    source_id:         str
    origin_type:       str           # "user"|"api"|"dream"|"internal"|"training"
    first_seen:        float
    interaction_count: int   = 0
    # Starts TRUSTED (architect ruling 2026-07-06: presumed good-faith —
    # "the system can't learn who to trust if it's always untrusting").
    # Distrust is learned from behavior, not presumed: every detector,
    # penalty, and the ladder down to TOXIC are unchanged, and starting at
    # 3.0 arms the trust-wash (build-then-betray) detector from first
    # contact (its prior-mean requirement is 3.0).
    trust_score:       float = 3.0
    last_updated:      float = field(default_factory=time.time)
    reliability_history: collections.deque = field(
        default_factory=lambda: collections.deque(maxlen=64)
    )

    # Internal dream / self-reflection sources get a higher start
    INTERNAL_ORIGINS = frozenset({"dream", "internal", "self_reflection", "training"})

    def __post_init__(self):
        if self.origin_type in self.INTERNAL_ORIGINS:
            self.trust_score = 4.0   # internal sources start HIGH


# ---------------------------------------------------------------------------
# SymbolTrustRecord
# ---------------------------------------------------------------------------

@dataclass
class SymbolTrustRecord:
    """Field-impact history for a specific symbol."""
    stable_id:       int
    source_id:       str     = ""
    symbol_trust:    float   = 3.0   # inherits from source at birth, diverges thereafter
    field_impact_ema: float  = 0.0   # EMA of coherence_delta values
    violation_count: int     = 0
    last_updated:    float   = field(default_factory=time.time)
    coherence_history: collections.deque = field(
        default_factory=lambda: collections.deque(maxlen=32)
    )


# ---------------------------------------------------------------------------
# TrustReport
# ---------------------------------------------------------------------------

@dataclass
class TrustReport:
    """
    Output of TrustLedger.evaluate().
    Advisory only — SelfhoodGovernance makes the final call.
    """
    source_id:        str
    source_trust:     float
    source_level:     TrustLevel
    symbol_trusts:    Dict[int, float]   # stable_id → trust score
    min_symbol_trust: float              # weakest-link symbol score
    coherence_impact: float              # the vec's estimated field impact
    recommendation:   str               # "ALLOW" | "MONITOR" | "QUARANTINE"

    @property
    def effective_trust(self) -> float:
        """Weakest link: min of source trust and min symbol trust."""
        return min(self.source_trust, self.min_symbol_trust)


# ---------------------------------------------------------------------------
# TrustLedger
# ---------------------------------------------------------------------------

class TrustLedger:
    """
    Two-level trust tracker. Reports to SelfhoodGovernance.

    Parameters
    ----------
    decay_rate : float
        Per-interaction trust decay for sources.
        Scaled by (1 - stability) so emotionally stable periods decay less.
    symbol_ema_alpha : float
        EMA weight for symbol field_impact updates.
    history_window : int
        Rolling window size for reliability history.
    """

    def __init__(
        self,
        decay_rate:        float = 0.003,
        symbol_ema_alpha:  float = 0.15,
        quarantine_floor:  float = 0.3,
        monitor_threshold: float = 2.0,
    ):
        self.decay_rate        = decay_rate
        self.symbol_ema_alpha  = symbol_ema_alpha
        self.quarantine_floor  = quarantine_floor
        self.monitor_threshold = monitor_threshold

        self.sources: Dict[str, SourceRecord]         = {}
        self.symbol_records: Dict[int, SymbolTrustRecord] = {}

        # Emotional stability reference — injected by AutonomousCycle
        self._stability_ref: Optional[object] = None

    # ------------------------------------------------------------------
    # Evaluate (called before injection, produces advisory TrustReport)
    # ------------------------------------------------------------------

    def evaluate(
        self,
        source_id:       str,
        origin_type:     str,
        stable_ids:      List[int],
        coherence_delta: float,
        field_energy:    float = 0.0,
    ) -> TrustReport:
        """
        Evaluate source and symbol trust for an incoming injection.

        Parameters
        ----------
        source_id : str
        origin_type : str
        stable_ids : list of int
            stable_ids of tokens being injected.
        coherence_delta : float
            From CoherenceReport — estimated field impact.
        field_energy : float
            Current field energy (context for evaluation).

        Returns
        -------
        TrustReport  (advisory — SelfhoodGovernance decides)
        """
        # 1. Source record
        source = self._get_or_create_source(source_id, origin_type)
        source.interaction_count += 1
        source.last_updated       = time.time()
        source.trust_score        = self._decay_source(source)

        # 2. Symbol records
        symbol_trusts: Dict[int, float] = {}
        for sid in stable_ids:
            record = self._get_or_create_symbol(sid, source_id, source.trust_score)
            record.coherence_history.append(coherence_delta)
            record.field_impact_ema = (
                (1.0 - self.symbol_ema_alpha) * record.field_impact_ema
                + self.symbol_ema_alpha * coherence_delta
            )
            record.last_updated = time.time()
            symbol_trusts[sid]  = record.symbol_trust

        # 3. Recommendation (advisory)
        min_sym = min(symbol_trusts.values()) if symbol_trusts else source.trust_score
        effective = min(source.trust_score, min_sym)

        if effective <= self.quarantine_floor:
            rec = "QUARANTINE"
        elif effective <= self.monitor_threshold:
            rec = "MONITOR"
        else:
            rec = "ALLOW"

        return TrustReport(
            source_id        = source_id,
            source_trust     = round(source.trust_score, 4),
            source_level     = TrustLevel.from_score(source.trust_score),
            symbol_trusts    = {k: round(v, 4) for k, v in symbol_trusts.items()},
            min_symbol_trust = round(min_sym, 4),
            coherence_impact = round(coherence_delta, 6),
            recommendation   = rec,
        )

    # ------------------------------------------------------------------
    # Feedback reception (called by SelfhoodGovernance after arbitration)
    # ------------------------------------------------------------------

    def receive_feedback(self, feedback: GovernanceFeedback):
        """
        Update source and symbol trust from actual governance outcome.

        Positive outcomes (ALLOW, MONITOR) gently reinforce.
        Negative outcomes (QUARANTINE, REJECT, SACRED_SHIELD) penalize.
        """
        source = self.sources.get(feedback.source_id)
        if source is None:
            return

        trust_delta = feedback.outcome_metrics.get("trust_impact", 0.0)
        source.trust_score = float(
            np.clip(source.trust_score + trust_delta, 0.1, 5.0)
        )
        source.reliability_history.append(source.trust_score)

        # Symbol-level update
        positive_decision = feedback.decision in ("allow", "allow_weakened", "monitor")

        for sid in feedback.stable_ids:
            if sid not in self.symbol_records:
                continue
            record = self.symbol_records[sid]
            if positive_decision:
                # Gentle positive reinforcement scaled by coherence
                delta = 0.05 * max(0.0, feedback.coherence_delta)
            else:
                delta = -0.2
                record.violation_count += 1

            record.symbol_trust = float(
                np.clip(record.symbol_trust + delta, 0.1, 5.0)
            )

    # ------------------------------------------------------------------
    # Trust summary (used by AutonomousCycle status)
    # ------------------------------------------------------------------

    def field_trust_summary(self) -> dict:
        if not self.sources:
            return {"average_source_trust": 3.0, "sources": 0}

        s_trusts = [s.trust_score for s in self.sources.values()]
        y_trusts = [r.symbol_trust for r in self.symbol_records.values()]

        return {
            "sources":             len(self.sources),
            "average_source_trust": round(float(np.mean(s_trusts)), 4),
            "toxic_sources":       sum(1 for t in s_trusts if t < 0.5),
            "sacred_sources":      sum(1 for t in s_trusts if t >= 4.7),
            "symbols_tracked":     len(self.symbol_records),
            "quarantined_symbols": sum(
                1 for r in self.symbol_records.values() if r.violation_count > 2
            ),
            "average_symbol_trust": round(float(np.mean(y_trusts)), 4) if y_trusts else 3.0,
        }

    # ------------------------------------------------------------------
    # Direct penalty (called by SelfhoodGovernance on hard blocks)
    # ------------------------------------------------------------------

    def penalize_source(self, source_id: str, magnitude: float = 0.3):
        """Directly reduce source trust. Used on QUARANTINE/REJECT decisions."""
        source = self.sources.get(source_id)
        if source is not None:
            source.trust_score = float(np.clip(source.trust_score - magnitude, 0.1, 5.0))
            source.reliability_history.append(source.trust_score)

    def reward_source(self, source_id: str, magnitude: float = 0.1):
        """Directly increase source trust. Used on consistently good outcomes."""
        source = self.sources.get(source_id)
        if source is not None:
            source.trust_score = float(np.clip(source.trust_score + magnitude, 0.1, 5.0))

    # ------------------------------------------------------------------
    # Dream cycle hook
    # ------------------------------------------------------------------

    def on_dream_cycle_complete(self):
        """
        Called after dream_cycle.py completes.
        Possible redemption: TOXIC symbols that survive dreaming get a
        floor raise — dreams are an internal process, more trustworthy
        than external injection.
        """
        for record in self.symbol_records.values():
            if record.symbol_trust < 0.5:
                record.symbol_trust = max(record.symbol_trust, 0.8)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_or_create_source(self, source_id: str, origin_type: str) -> SourceRecord:
        if source_id not in self.sources:
            self.sources[source_id] = SourceRecord(
                source_id   = source_id,
                origin_type = origin_type,
                first_seen  = time.time(),
            )
        return self.sources[source_id]

    def _get_or_create_symbol(
        self,
        stable_id: int,
        source_id: str,
        source_trust: float,
    ) -> SymbolTrustRecord:
        if stable_id not in self.symbol_records:
            self.symbol_records[stable_id] = SymbolTrustRecord(
                stable_id    = stable_id,
                source_id    = source_id,
                symbol_trust = source_trust,  # inherit from source at birth
            )
        return self.symbol_records[stable_id]

    def _decay_source(self, source: SourceRecord) -> float:
        """
        Decay source trust by decay_rate, modulated by emotional stability.
        Stable periods decay less — trust persists when the system is coherent.
        """
        stability = 0.7   # default if no emotion ref attached
        if self._stability_ref is not None:
            stability = float(getattr(self._stability_ref, "stability", 0.7))

        decay = self.decay_rate * (1.0 - stability)
        return float(np.clip(source.trust_score - decay, 0.1, 5.0))
