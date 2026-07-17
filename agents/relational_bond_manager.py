"""
agents/relational_bond_manager.py

RelationalBondManager — emergent relational bond formation and tracking.

Bonds are not declared. They emerge from accumulated shared experience.

A RelationalBond forms automatically when a source crosses all three
formation thresholds simultaneously:
  - interaction_count    temporal depth (many interactions over time)
  - coherence_mean       consistent quality (positive field impact)
  - crystal_count        structural footprint (something crystallized)

Bond type is inferred from the pattern of accumulated signals.
A confidence score accompanies the type for borderline cases.

Priority order:  existential → emotional → intellectual → transactional

Bonds are dynamic. They update in real time from GovernanceFeedback,
strengthening during positive governance outcomes and weakening during
negative ones. They never flip instantly — EMA smoothing prevents
a single bad interaction from destroying a deep bond.

Effect on SelfhoodGovernance
----------------------------
  Bonded sources get a trust_floor — trust won't decay below
  bond_strength × FLOOR_FACTOR regardless of individual outcomes.
  This models the difference between trust (earned per-interaction)
  and relationship (earned over time, more resilient).

  QUARANTINE of a bonded source is still permitted but logged as
  a significant relational event. The bond itself weakens but persists.
"""

from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass, field
from typing import Dict, List, Literal, Optional, Tuple, TYPE_CHECKING

import numpy as np

from agents.bond_accumulator import AccumulatorOutcome, BondFormationAccumulator

if TYPE_CHECKING:
    from agents.trust_ledger import GovernanceFeedback

# ---------------------------------------------------------------------------
# BondType and constants
# ---------------------------------------------------------------------------

BondType = Literal["intellectual", "emotional", "existential", "transactional"]

PRIORITY: List[BondType] = ["existential", "emotional", "intellectual", "transactional"]
BORDERLINE_MARGIN = 0.12   # scores within this margin → use priority, report confidence
FLOOR_FACTOR      = 0.40   # bonded source trust floor = bond_strength × FLOOR_FACTOR


# ---------------------------------------------------------------------------
# RelationalBond
# ---------------------------------------------------------------------------

@dataclass
class RelationalBond:
    """
    A single emergent relational bond with a source.

    All fields update dynamically from lived experience and GovernanceFeedback.
    bond_type and bond_confidence are re-inferred after each significant update.
    """
    source_id:          str
    bond_type:          BondType
    bond_confidence:    float            # 0.0–1.0, from _infer_bond_type()
    bond_strength:      float = 1.0      # 0.0–5.0, grows slowly, decays slowly
    bond_depth:         int   = 0        # steps since first interaction
    interaction_count:  int   = 0
    coherence_mean:     float = 0.0      # EMA of coherence_delta from this source
    emotional_signature: float = 0.0    # EMA of joy/stability during interactions
    crystal_count:      int   = 0        # crystals containing this source's symbols
    attractor_count:    int   = 0        # attractor centers seeded by this source
    entity_signal:      float = 0.0      # fraction of interactions touching ENTITY symbols
    formed_at:          float = field(default_factory=time.time)
    last_reinforced:    float = field(default_factory=time.time)

    @property
    def trust_floor(self) -> float:
        """Minimum trust score for this source regardless of decay."""
        return round(self.bond_strength * FLOOR_FACTOR, 4)

    @property
    def is_established(self) -> bool:
        """Bond is established if strength > 1.5 and depth > 50 steps."""
        return self.bond_strength > 1.5 and self.bond_depth > 50

    def to_dict(self) -> dict:
        return {
            "source_id":         self.source_id,
            "bond_type":         self.bond_type,
            "bond_confidence":   self.bond_confidence,
            "bond_strength":     round(self.bond_strength, 4),
            "bond_depth":        self.bond_depth,
            "interaction_count": self.interaction_count,
            "coherence_mean":    round(self.coherence_mean, 4),
            "emotional_signature": round(self.emotional_signature, 4),
            "crystal_count":     self.crystal_count,
            "attractor_count":   self.attractor_count,
            "entity_signal":     round(self.entity_signal, 4),
            "trust_floor":       self.trust_floor,
            "established":       self.is_established,
        }


# ---------------------------------------------------------------------------
# RelationalBondManager
# ---------------------------------------------------------------------------

class RelationalBondManager:
    """
    Emergent bond formation and dynamic management.

    Parameters
    ----------
    formation_interaction_threshold : int
        Minimum interactions before a bond can form.
    formation_coherence_threshold : float
        Minimum mean coherence_delta for bond formation.
    formation_crystal_threshold : int
        Minimum crystals with source's symbols for bond formation.
    ema_alpha : float
        EMA weight for coherence_mean and emotional_signature updates.
    strength_decay : float
        Per-step strength decay when source is inactive.
    ddm_formation : bool
        Opt-in (default OFF): route the formation *quality* decision through
        the leaky asymmetric drift-diffusion accumulator
        (agents/bond_accumulator.py) instead of the instantaneous
        coherence_mean / allow_rate disjunction. The structural
        preconditions (interaction_count, crystal_count) still apply at
        commit time — the accumulator replaces only the quality read.
    ddm_config : dict or None
        Constructor overrides for BondFormationAccumulator (physics
        constants; architect-set).
    """

    def __init__(
        self,
        formation_interaction_threshold: int   = 20,
        formation_coherence_threshold:   float = 0.10,
        formation_crystal_threshold:     int   = 1,
        ema_alpha:                       float = 0.08,
        strength_decay:                  float = 0.0005,
        adaptive_threshold:              bool  = True,
        min_coherence_threshold:         float = 0.01,
        variance_window:                 int   = 64,
        allow_rate_threshold:            float = 0.80,
        strength_lr:                     float = 0.01,
        ddm_formation:                   bool  = False,
        ddm_config:                      Optional[dict] = None,
    ):
        self.formation_interaction_threshold = formation_interaction_threshold
        self.formation_coherence_threshold   = formation_coherence_threshold
        self.formation_crystal_threshold     = formation_crystal_threshold
        self.ema_alpha                       = ema_alpha
        self.strength_decay                  = strength_decay
        self.allow_rate_threshold            = allow_rate_threshold
        # Strength growth rate per positive interaction, applied to the
        # absolute v0.3 field_alignment (≈0.75–0.99 measured, p50 ~0.98 —
        # bond_signal_calibration_probe 2026-07-09). Calibration: a bond forms
        # at strength 1.0 and establishes at >1.5, so at 0.01 a source with a
        # 0.25 share of traffic establishes after ~200 further global steps;
        # a 0.15-share source needs ~340. Deep relationships take real time,
        # frequent partners deepen faster. (The old formula used the marginal
        # coherence_delta + satisfaction, both structurally ≈0 in a saturated
        # field — bonds flatlined at 1.0 forever; the same F7/F8 disease.)
        self.strength_lr                     = strength_lr

        # Adaptive threshold (Intervention 5)
        # threshold = max(min_threshold, formation_coherence_threshold × field_variance)
        # In hyper-coherent saturated fields, per-step deltas are small even
        # when positive. Fixed thresholds calibrated for chaotic regimes
        # prevent bond formation in stable ones. Adaptive scales by the
        # variance of recent coherence_deltas across all sources.
        self.adaptive_threshold      = adaptive_threshold
        self.min_coherence_threshold = min_coherence_threshold
        self._coherence_window:      deque = deque(maxlen=variance_window)

        # Formation-as-accumulation lever (opt-in, default OFF). When ON,
        # the accumulator owns the quality decision; OFF is byte-identical
        # to the classic path (no RNG consumed, no state touched).
        self._ddm: Optional[BondFormationAccumulator] = (
            BondFormationAccumulator(**(ddm_config or {})) if ddm_formation else None
        )

        self._bonds:    Dict[str, RelationalBond] = {}
        self._step:     int = 0

        # Per-source interaction counters (pre-bond)
        self._pre_bond: Dict[str, dict] = {}

    # ------------------------------------------------------------------
    # Feedback subscription
    # ------------------------------------------------------------------

    def receive_feedback(self, feedback: "GovernanceFeedback"):
        """
        Update bond state from GovernanceFeedback.
        Called by SelfhoodGovernance after every arbitration decision.
        """
        source_id = feedback.source_id
        decision  = feedback.decision
        metrics   = feedback.outcome_metrics

        coherence_delta = feedback.coherence_delta
        satisfaction    = metrics.get("emotional_satisfaction", 0.0)
        trust_impact    = metrics.get("trust_impact", 0.0)
        positive        = decision in ("allow", "allow_weakened", "monitor")
        is_clean_allow  = decision == "allow"   # for decision_quality tracking

        # Track for adaptive threshold (Intervention 5)
        self._coherence_window.append(coherence_delta)

        # Track pre-bond interactions
        self._update_pre_bond(source_id, coherence_delta, satisfaction, is_clean_allow)

        # Update existing bond
        if source_id in self._bonds:
            bond = self._bonds[source_id]
            bond.interaction_count  += 1
            bond.bond_depth         += 1

            # EMA updates
            bond.coherence_mean     = (
                (1 - self.ema_alpha) * bond.coherence_mean
                + self.ema_alpha * coherence_delta
            )
            bond.emotional_signature = (
                (1 - self.ema_alpha) * bond.emotional_signature
                + self.ema_alpha * satisfaction
            )

            # Strength delta — positive outcomes reinforce, negative weaken.
            # Growth is currencied in the absolute v0.3 field_alignment (the
            # live signal), not the marginal coherence_delta (structurally ≈0
            # in a saturated field — bonds used to flatline at 1.0 and never
            # establish). satisfaction is kept in the sum so the affective
            # term comes alive if the satisfaction economy is ever repaired.
            if positive:
                alignment = metrics.get("field_alignment", 0.0)
                delta = self.strength_lr * max(0.0, alignment + satisfaction)
            else:
                delta = -0.15 * abs(trust_impact)

            bond.bond_strength = float(np.clip(bond.bond_strength + delta, 0.0, 5.0))
            bond.last_reinforced = time.time()

            # Re-infer bond type after update
            bond.bond_type, bond.bond_confidence = self._infer_bond_type(bond)

        else:
            # Check if pre-bond source now qualifies for bond formation
            if self._ddm is not None:
                self._ddm_step(source_id, decision, metrics.get("field_alignment", 0.0))
            else:
                self._maybe_form_bond(source_id)

        self._step += 1

    # ------------------------------------------------------------------
    # Crystal and attractor signals
    # ------------------------------------------------------------------

    def notify_crystal(self, source_id: str):
        """Called when a crystal forms whose origin_tokens came from source_id."""
        self._pre_bond_field(source_id, "crystal_count", 1)
        if source_id in self._bonds:
            self._bonds[source_id].crystal_count += 1
            self._bonds[source_id].bond_strength = min(
                5.0, self._bonds[source_id].bond_strength + 0.1
            )

    def notify_attractor(self, source_id: str):
        """Called when an attractor center is seeded by this source."""
        self._pre_bond_field(source_id, "attractor_count", 1)
        if source_id in self._bonds:
            self._bonds[source_id].attractor_count += 1

    def notify_entity_signal(self, source_id: str, delta: float = 0.1):
        """Called when ENTITY-class symbols are involved from this source."""
        if source_id in self._bonds:
            bond = self._bonds[source_id]
            bond.entity_signal = float(np.clip(bond.entity_signal + delta, 0.0, 1.0))

    # ------------------------------------------------------------------
    # Bond queries
    # ------------------------------------------------------------------

    def get_bond(self, source_id: str) -> Optional[RelationalBond]:
        return self._bonds.get(source_id)

    def trust_floor(self, source_id: str) -> float:
        """Return trust floor for source, 0.0 if no bond."""
        bond = self._bonds.get(source_id)
        return bond.trust_floor if bond is not None else 0.0

    def all_bonds(self) -> List[RelationalBond]:
        return list(self._bonds.values())

    def established_bonds(self) -> List[RelationalBond]:
        return [b for b in self._bonds.values() if b.is_established]

    def decay_step(self):
        """Apply slow strength decay to all bonds. Call periodically."""
        for bond in list(self._bonds.values()):
            bond.bond_strength = float(
                np.clip(bond.bond_strength - self.strength_decay, 0.0, 5.0)
            )
            bond.bond_depth += 1

    # ------------------------------------------------------------------
    # Bond type inference
    # ------------------------------------------------------------------

    def _infer_bond_type(self, bond: RelationalBond) -> Tuple[BondType, float]:
        """
        Infer bond type from accumulated signals.

        Scoring per type (all ∈ [0, 1]):
          existential   temporal depth + attractor footprint + entity signal
          emotional     emotional_signature + crystal affective weight
          intellectual  coherence_mean + anti-emotional signal
          transactional interaction density + low coherence + no crystals

        Priority order: existential → emotional → intellectual → transactional
        Within BORDERLINE_MARGIN (0.12): pick by priority, report actual confidence.
        """
        scores: Dict[str, float] = {
            "existential":   self._score_existential(bond),
            "emotional":     self._score_emotional(bond),
            "intellectual":  self._score_intellectual(bond),
            "transactional": self._score_transactional(bond),
        }

        max_score = max(scores.values())

        # Candidates within borderline margin — priority governs among them
        candidates = {t for t in PRIORITY if scores[t] >= max_score - BORDERLINE_MARGIN}

        # Select highest priority candidate
        selected: BondType = next(t for t in PRIORITY if t in candidates)
        confidence = round(float(scores[selected]), 4)

        return selected, confidence

    def _score_existential(self, bond: RelationalBond) -> float:
        """Deep temporal + identity footprint."""
        depth_score     = min(bond.bond_depth / 500.0, 1.0)
        attractor_score = min(bond.attractor_count / 3.0, 1.0)
        entity_score    = float(np.clip(bond.entity_signal, 0.0, 1.0))
        return float(depth_score * 0.40 + attractor_score * 0.35 + entity_score * 0.25)

    def _score_emotional(self, bond: RelationalBond) -> float:
        """High joy/stability correlation + crystal affective weight."""
        emotional = float(np.clip(bond.emotional_signature, 0.0, 1.0))
        crystal   = min(bond.crystal_count / 5.0, 1.0)
        return float(emotional * 0.65 + crystal * 0.35)

    def _score_intellectual(self, bond: RelationalBond) -> float:
        """High coherence, low emotional signature, abstract."""
        coh_score      = float(np.clip(bond.coherence_mean, 0.0, 1.0))
        anti_emotional = float(np.clip(1.0 - bond.emotional_signature, 0.0, 1.0))
        return float(coh_score * 0.60 + anti_emotional * 0.40)

    def _score_transactional(self, bond: RelationalBond) -> float:
        """High interaction count, low quality, no structural footprint."""
        interaction = min(bond.interaction_count / 100.0, 1.0)
        low_coh     = float(np.clip(1.0 - bond.coherence_mean, 0.0, 1.0))
        no_crystals = 1.0 if bond.crystal_count == 0 else max(0.0, 1.0 - bond.crystal_count / 3.0)
        return float(interaction * 0.40 + low_coh * 0.30 + no_crystals * 0.30)

    # ------------------------------------------------------------------
    # Bond formation
    # ------------------------------------------------------------------

    def _structural_preconditions_met(self, source_id: str) -> bool:
        """
        The non-quality half of the formation contract — temporal depth
        (interaction_count) + structural footprint (crystal_count). ONE
        implementation shared by both formation paths (classic gate and the
        DDM lever) so the documented thresholds cannot silently diverge.
        """
        pre = self._pre_bond.get(source_id)
        return (
            pre is not None
            and pre["interaction_count"] >= self.formation_interaction_threshold
            and pre["crystal_count"]     >= self.formation_crystal_threshold
        )

    def _maybe_form_bond(self, source_id: str):
        """Check if pre-bond source now qualifies for bond formation."""
        pre = self._pre_bond.get(source_id)
        if pre is None:
            return

        coherence_threshold = self._effective_coherence_threshold()
        interactions = pre["interaction_count"]
        allow_rate   = (pre["allow_count"] / interactions) if interactions > 0 else 0.0

        # Quality signal: EITHER positive coherence accumulation crosses the
        # adaptive threshold, OR the source has a strong rate of clean ALLOW
        # decisions. In saturated fields the latter is the realistic signal —
        # coherence_mean cannot accumulate when individual deltas are forced
        # near zero. allow_rate captures "consistent participation."
        coh_qualifies   = pre["coherence_mean"] >= coherence_threshold
        allow_qualifies = allow_rate >= self.allow_rate_threshold
        quality_qualifies = coh_qualifies or allow_qualifies

        if not (quality_qualifies and self._structural_preconditions_met(source_id)):
            return

        self._form_bond(source_id)

    def _ddm_step(self, source_id: str, decision: str, field_alignment: float):
        """
        Formation-as-accumulation (opt-in): advance the candidate's decision
        variable one step; on an ACCEPT crossing, commit the bond iff the
        structural preconditions (temporal depth + crystal footprint) hold —
        the accumulator replaces only the instantaneous quality read. When a
        precondition lags, the candidate is held at the bound (evidence must
        be sustained while the footprint catches up — the window refreshes
        while V stays there); structured negative evidence can still pull it
        down and deny.
        """
        outcome = self._ddm.observe(source_id, decision, field_alignment)
        if outcome is not AccumulatorOutcome.ACCEPT:
            return

        if self._structural_preconditions_met(source_id):
            self._ddm.commit(source_id)
            self._form_bond(source_id)
        # else: the candidate is held at the bound by the accumulator itself
        # (observe() clamps V and refreshes the window while it stays there);
        # nothing to do until the structural footprint catches up.

    def _form_bond(self, source_id: str):
        """Create the bond from accumulated pre-bond state (the commitment)."""
        pre = self._pre_bond[source_id]
        seed = RelationalBond(
            source_id           = source_id,
            bond_type           = "transactional",   # placeholder before inference
            bond_confidence     = 0.5,
            bond_strength       = 1.0,
            bond_depth          = pre["interaction_count"],
            interaction_count   = pre["interaction_count"],
            coherence_mean      = pre["coherence_mean"],
            emotional_signature = pre["emotional_signature"],
            crystal_count       = pre["crystal_count"],
            attractor_count     = pre["attractor_count"],
        )
        seed.bond_type, seed.bond_confidence = self._infer_bond_type(seed)
        self._bonds[source_id] = seed

        # Clear pre-bond tracking
        del self._pre_bond[source_id]
        if self._ddm is not None:
            self._ddm.drop(source_id)

    def _effective_coherence_threshold(self) -> float:
        """
        Adaptive bond formation threshold (Intervention 5).

        In hyper-coherent saturated fields, per-step coherence_deltas are
        small even when positive. A static threshold of 0.10 calibrated
        for chaotic regimes prevents bond formation in stable ones.

        threshold = max(min_threshold, formation_threshold × variance_scale)

        where variance_scale is the std of recent coherence_deltas. Stable
        fields → low variance → low threshold (small positive deltas count).
        Chaotic fields → high variance → high threshold (only large deltas count).
        """
        if not self.adaptive_threshold or len(self._coherence_window) < 8:
            return self.formation_coherence_threshold

        std = float(np.std(self._coherence_window))
        adaptive = self.formation_coherence_threshold * (std / 0.10)
        return max(self.min_coherence_threshold, adaptive)

    def _update_pre_bond(
        self,
        source_id:       str,
        coherence_delta: float,
        satisfaction:    float,
        is_clean_allow:  bool = False,
    ):
        if source_id not in self._pre_bond:
            self._pre_bond[source_id] = {
                "interaction_count":   0,
                "coherence_mean":      0.0,
                "emotional_signature": 0.0,
                "crystal_count":       0,
                "attractor_count":     0,
                "allow_count":         0,     # for allow_rate metric
            }
        pre = self._pre_bond[source_id]
        pre["interaction_count"] += 1
        if is_clean_allow:
            pre["allow_count"] += 1

        alpha = self.ema_alpha
        # Track positive contribution (clipped at 0). In saturated fields this
        # may converge to zero — that's why we also track allow_rate.
        positive_contribution = max(0.0, coherence_delta)
        pre["coherence_mean"]     = (1 - alpha) * pre["coherence_mean"] + alpha * positive_contribution
        pre["emotional_signature"] = (1 - alpha) * pre["emotional_signature"] + alpha * satisfaction

    def _pre_bond_field(self, source_id: str, field_name: str, delta: int):
        if source_id not in self._pre_bond:
            self._pre_bond[source_id] = {
                "interaction_count": 0, "coherence_mean": 0.0,
                "emotional_signature": 0.0, "crystal_count": 0, "attractor_count": 0,
                "allow_count": 0,
            }
        self._pre_bond[source_id][field_name] = (
            self._pre_bond[source_id].get(field_name, 0) + delta
        )

    # ------------------------------------------------------------------
    # Diagnostics
    # ------------------------------------------------------------------

    def summary(self) -> dict:
        bonds = self.all_bonds()
        if not bonds:
            result = {"bonds": 0, "established": 0}
        else:
            result = {
                "bonds":       len(bonds),
                "established": len(self.established_bonds()),
                "by_type": {
                    t: sum(1 for b in bonds if b.bond_type == t)
                    for t in PRIORITY
                },
                "strongest": sorted(
                    [b.to_dict() for b in bonds],
                    key=lambda d: d["bond_strength"],
                    reverse=True,
                )[:5],
            }
        if self._ddm is not None:
            result["ddm"] = self._ddm.summary()
        return result
