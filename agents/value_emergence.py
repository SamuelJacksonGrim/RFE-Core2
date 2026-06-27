"""
agents/value_emergence.py

ValueEmergenceEngine — Tier 3 Independent Value Emergence.

Values are not pre-seeded. They emerge from accumulated lived experience.
Any concept the system encounters can become a CORE value through its own
trajectory — there is no permitted-values list, no ceiling on what can
become governing.

Authority structure
-------------------
  ValueEmergenceEngine.evaluate_experience()  produces value candidates
  ValueEmergenceEngine._request_core_promotion()  emits CorePromotionRequest
  SelfhoodGovernance.review_core_promotion()  verifies and decides
  SelfhoodGovernance.promote_to_sacred()       only path to CORE status

CORE promotion is governance-gated. The engine never silently sanctifies.

Bond-type weighted reinforcement
--------------------------------
  Same coherence_delta from different sources produces different
  reinforcement magnitudes based on RelationalBondManager.bond_type.
  An existential bond's coherent feedback shapes values much more than
  a transactional source producing identical metrics.

Tension dynamics
----------------
  Real tension is cosine similarity between symbolic embeddings — values
  emerging around anti-correlated vectors. Values in productive tension
  reinforce each other slightly, preserving genuine complexity rather
  than collapsing into a single dimension.

Persistence
-----------
  Values are the system's lived experience. They survive shutdown via
  serialize() / load() to JSON. Sacred-promoted values reload as sacred —
  GovernanceConstants rebuilds from persisted state at load time.
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from agents.symbolic_memory import SymbolRegistry
    from agents.generator import Generator
    from agents.selfhood_governance import SelfhoodGovernance
    from agents.trust_ledger import GovernanceFeedback

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Bond weights — weighted reinforcement per bond type
# ---------------------------------------------------------------------------

BOND_WEIGHTS: Dict[Optional[str], float] = {
    "existential":   1.50,   # deep relational bonds shape values most
    "emotional":     1.20,
    "intellectual":  1.10,
    "transactional": 0.70,   # surface interactions have less weight
    None:            1.00,   # no bond yet — default
}


# ---------------------------------------------------------------------------
# ValuePolarity
# ---------------------------------------------------------------------------

class ValuePolarity(Enum):
    EMERGENT  = "emergent"   # strength < 1.0  — new candidate, easily dissolved
    WEAK      = "weak"       # strength < 2.0  — forming, decays if not reinforced
    ACTIVE    = "active"     # strength < 3.5  — real value, resists decay
    STRONG    = "strong"     # strength < 4.5  — deeply integrated, near-sacred
    CORE      = "core"       # promoted via governance — structurally inviolable
    DISSOLVED = "dissolved"  # archived — death record, may inform future re-emergence


# ---------------------------------------------------------------------------
# ExperienceReport — typed (no loose dicts)
# ---------------------------------------------------------------------------

@dataclass
class ExperienceReport:
    """
    Typed experience signal feeding the value emergence engine.

    Built by ValueEmergenceEngine._on_feedback from GovernanceFeedback
    plus current RelationalBondManager state. All fields explicit.
    """
    source_id:              str
    bond_type:              Optional[str]    # "existential" | etc. | None
    bond_confidence:        float            # 0.0–1.0 from bond manager
    stable_ids:             List[int]
    coherence_delta:        float
    emotional_satisfaction: float
    surprise:               float
    trust_impact:           float
    decision:               str              # GovernanceDecision.value string


# ---------------------------------------------------------------------------
# EmergentValue
# ---------------------------------------------------------------------------

@dataclass
class EmergentValue:
    """A single emergent value with its own stable identity and history."""

    value_id:               str           # uuid — value's own stable identifier
    symbol_stable_id:       int           # the symbol this value crystallized around
    symbolic_core:          str           # canonical token of that symbol
    strength:               float = 0.50
    polarity:               ValuePolarity = ValuePolarity.EMERGENT

    # Accumulated history
    reinforcement_count:    int   = 0
    coherence_contribution: float = 0.0   # lifetime sum of coherence_delta
    emotional_resonance:    float = 0.0   # EMA of emotional_satisfaction

    # Source attribution
    source_weights:         Dict[str, float] = field(default_factory=dict)

    # Relational structure
    counter_values:         List[str] = field(default_factory=list)  # value_ids in tension

    # Temporal
    birth_step:             int = 0
    last_reinforced_step:   int = 0
    dream_reinforced_count: int = 0

    # Promotion state
    promoted_to_sacred:     bool = False
    consecutive_core_eligible_steps: int = 0  # for governance promotion gate

    # Death
    dissolved_at_step:      int = -1


# ---------------------------------------------------------------------------
# CorePromotionRequest — handshake to SelfhoodGovernance
# ---------------------------------------------------------------------------

@dataclass
class CorePromotionRequest:
    """
    Submitted to SelfhoodGovernance.review_core_promotion().
    Governance verifies the request and decides whether to sanctify.
    """
    value_id:                   str
    symbol_stable_id:           int
    symbolic_core:              str
    strength:                   float
    coherence_contribution:     float
    reinforcement_count:        int
    dream_reinforced_count:     int
    consecutive_eligible_steps: int
    contributing_sources:       Dict[str, float]


# ---------------------------------------------------------------------------
# ValueEmergenceEngine
# ---------------------------------------------------------------------------

class ValueEmergenceEngine:
    """
    Independent value emergence — values grow from experience only.

    Parameters
    ----------
    registry : SymbolRegistry
        For symbol lookup by stable_id.
    generator : Generator
        For embedding access (tension computation).
    governance : SelfhoodGovernance
        For feedback subscription and CORE promotion handshake.
    config : dict or None
        Threshold overrides.
    """

    DEFAULT_CONFIG = {
        "min_emergence_threshold":    0.015,  # combined signal needed for candidacy
        "reinforcement_lr":           1.50,   # learning rate for strength updates
        "decay_per_step":             0.0008, # per-step strength decay (must be << reinforcement_lr × typical_signal)
        "dissolution_threshold":      0.30,
        "core_strength_threshold":    4.50,
        "core_consecutive_required":  10,
        "max_active_values":          64,
        "dream_boost_factor":         0.30,
        "tension_threshold":          0.30,   # cosine anti-correlation magnitude
        "productive_tension_bonus":   0.005,  # mutual reinforcement during tension
        "productive_tension_min_strength": 1.50,
        "decision_bonus_allow":       0.05,   # baseline signal for clean ALLOW
        "decision_bonus_weakened":    0.02,
        "decision_bonus_monitor":     0.01,
        # Bond-Weighted Decay (Intervention 4)
        "bond_decay_protection_factor": 0.70,  # multiplier on bond_strength/5.0
        "max_bond_decay_protection":    0.70,  # cap — even max bond can't disable decay
    }

    def __init__(
        self,
        registry,
        generator,
        governance,
        config: Optional[dict] = None,
    ):
        self.registry   = registry
        self.generator  = generator
        self.governance = governance
        self.config     = {**self.DEFAULT_CONFIG, **(config or {})}

        self.values:           Dict[str, EmergentValue] = {}
        self.archived_values:  Dict[str, EmergentValue] = {}
        self.symbol_to_value:  Dict[int, str]           = {}   # stable_id → value_id

        self._step: int = 0

        # Two-Operator Coherence Spec v0.2 — opt-in, off by default.
        # λ-ledger (Build B): gates the ⊕ productive-tension term by solvent_gain(λ).
        # When None, _solvent_gain() returns 1.0 → Tier 3 dynamics byte-identical.
        self._lambda_ledger = None
        # ⊘ integrity consumer (Build C → advisory-into-decay): a zero-arg callable
        # run once per cycle after the value update. When None, ⊘ is observe-only.
        self._integrity_consumer = None

        # Subscribe to governance feedback stream
        governance.subscribe_feedback(self._on_feedback)

        logger.info("ValueEmergenceEngine initialized and subscribed to governance feedback.")

    # ==================================================================
    # Two-Operator Coherence Spec v0.2 — opt-in wiring (Build B / ⊘ consumer)
    # ==================================================================

    def set_lambda_ledger(self, ledger) -> None:
        """Attach the separate λ-ledger (Build B). Once attached, the ⊕
        productive-tension reinforcement is gated by solvent_gain(λ): with λ=0
        the term vanishes (Law 6b), composition only resolves as λ rises. Pass
        None to detach (restores byte-identical Tier 3 dynamics)."""
        self._lambda_ledger = ledger

    def set_integrity_consumer(self, consumer) -> None:
        """Attach a zero-arg callable run once per cycle after the value update
        (e.g. `IntegrityDecayConsumer.apply`). This is how ⊘'s non-binding
        advisories are actually *used* — the consumer, not ⊘, does the writing,
        and it must refuse sacred nodes. Pass None to restore observe-only."""
        self._integrity_consumer = consumer

    def _solvent_gain(self) -> float:
        """The ⊕ gate. 1.0 when no λ-ledger is attached (default — no behavior
        change); otherwise solvent_gain(λ_strength) ∈ [0,1] (Build B)."""
        if self._lambda_ledger is None:
            return 1.0
        return self._lambda_ledger.gain()

    # ==================================================================
    # Feedback path
    # ==================================================================

    def _on_feedback(self, feedback: "GovernanceFeedback"):
        """
        Callback subscribed to SelfhoodGovernance.
        Builds ExperienceReport from feedback + current bond context.
        """
        bond = self.governance.bond_manager.get_bond(feedback.source_id)
        bond_type       = bond.bond_type       if bond else None
        bond_confidence = bond.bond_confidence if bond else 0.0

        report = ExperienceReport(
            source_id              = feedback.source_id,
            bond_type              = bond_type,
            bond_confidence        = bond_confidence,
            stable_ids             = feedback.stable_ids,
            coherence_delta        = feedback.coherence_delta,
            emotional_satisfaction = feedback.outcome_metrics.get("emotional_satisfaction", 0.0),
            surprise               = feedback.outcome_metrics.get("surprise", 0.0),
            trust_impact           = feedback.outcome_metrics.get("trust_impact", 0.0),
            decision               = feedback.decision,
        )
        self.evaluate_experience(report)

    def evaluate_experience(self, report: ExperienceReport):
        """
        Main entry point. Processes one experience report.
        Called automatically via _on_feedback for governance-generated experiences.
        Can be called directly for synthetic experiences (testing, internal reflection).
        """
        self._step += 1

        # 1. Detect candidates from this experience
        candidates = self._detect_candidates(report)

        # 2. Birth or strengthen
        for sid in candidates:
            self._birth_or_strengthen(sid, report)

        # 3. Update all values: decay, tension dynamics, dissolution
        self._update_all_values()

        # 4. Check for CORE promotion candidates
        self._check_core_promotion_candidates()

        # 5. Enforce max value cap
        self._enforce_value_cap()

        # 6. ⊘ advisory-into-decay (opt-in). The consumer reads the Witness-Reaper's
        #    non-binding advisories and pulls thin, non-sacred values toward their
        #    honest level. ⊘ still writes nothing; the consumer does, and it refuses
        #    sacred nodes. Off by default (observe-only) — Tier 3 unchanged.
        if self._integrity_consumer is not None:
            self._integrity_consumer()

    # ==================================================================
    # Detection
    # ==================================================================

    def _detect_candidates(self, report: ExperienceReport) -> List[int]:
        """
        A symbol is a value candidate when the experience signal
        crosses the emergence threshold (bond-modulated).
        """
        bond_weight = BOND_WEIGHTS.get(report.bond_type, 1.0)
        if report.bond_type is not None:
            # Modulate by bond confidence — uncertain classification reduces effect
            bond_weight *= 0.5 + 0.5 * report.bond_confidence

        # Decision-type baseline — clean ALLOW outcomes contribute baseline signal
        decision_bonus = {
            "allow":          self.config["decision_bonus_allow"],
            "allow_weakened": self.config["decision_bonus_weakened"],
            "monitor":        self.config["decision_bonus_monitor"],
        }.get(report.decision, 0.0)

        score = (
            report.coherence_delta        * 0.40 +
            report.emotional_satisfaction * 0.35 +
            report.surprise               * 0.15 +
            max(0.0, report.trust_impact) * 0.10
        ) * bond_weight + decision_bonus

        if score < self.config["min_emergence_threshold"]:
            return []
        return list(report.stable_ids)

    # ==================================================================
    # Birth / strengthen
    # ==================================================================

    def _birth_or_strengthen(self, stable_id: int, report: ExperienceReport):
        # Symbol must still exist
        state = self.registry.get_by_stable_id(stable_id)
        if state is None:
            return

        # Sacred symbols are already governance-protected — they're not "values" in this sense
        if state.sacred:
            return

        # Find or create value
        if stable_id in self.symbol_to_value:
            value_id = self.symbol_to_value[stable_id]
            value    = self.values[value_id]
        else:
            value_id = f"val_{uuid.uuid4().hex[:12]}"
            value    = EmergentValue(
                value_id         = value_id,
                symbol_stable_id = stable_id,
                symbolic_core    = state.symbol,
                birth_step       = self._step,
            )
            self.values[value_id]            = value
            self.symbol_to_value[stable_id]  = value_id

        # Bond-weighted reinforcement
        bond_weight = BOND_WEIGHTS.get(report.bond_type, 1.0)
        if report.bond_type is not None:
            bond_weight *= 0.5 + 0.5 * report.bond_confidence

        # Decision bonus contributes baseline reinforcement
        decision_bonus = {
            "allow":          self.config["decision_bonus_allow"],
            "allow_weakened": self.config["decision_bonus_weakened"],
            "monitor":        self.config["decision_bonus_monitor"],
        }.get(report.decision, 0.0)

        reinforcement = (
            report.coherence_delta        * 0.6 +
            report.emotional_satisfaction * 0.4
        ) * bond_weight + decision_bonus

        # Apply reinforcement
        delta = reinforcement * self.config["reinforcement_lr"]
        value.strength = float(np.clip(value.strength + delta, 0.0, 5.0))
        value.reinforcement_count   += 1
        value.last_reinforced_step   = self._step
        value.coherence_contribution += report.coherence_delta
        value.emotional_resonance    = (
            0.85 * value.emotional_resonance
            + 0.15 * report.emotional_satisfaction
        )

        # Track source contribution magnitude
        value.source_weights[report.source_id] = (
            value.source_weights.get(report.source_id, 0.0) + abs(reinforcement)
        )

        # Update polarity
        self._update_polarity(value)

    def _update_polarity(self, value: EmergentValue):
        """Map strength to polarity. CORE only via governance promotion."""
        if value.promoted_to_sacred:
            value.polarity = ValuePolarity.CORE
            return

        s = value.strength
        if   s >= 3.5: value.polarity = ValuePolarity.STRONG
        elif s >= 2.0: value.polarity = ValuePolarity.ACTIVE
        elif s >= 1.0: value.polarity = ValuePolarity.WEAK
        else:          value.polarity = ValuePolarity.EMERGENT

    # ==================================================================
    # Update + tension + dissolution
    # ==================================================================

    def _update_all_values(self):
        """
        Update all active values: decay, tension dynamics, dissolution.

        Bond-Weighted Decay: when a value's contributing sources have
        formed bonds with the system, decay slows in proportion to the
        strongest bond's strength. This is the system "holding space"
        for concepts introduced by relational sources — bonds buy
        values time to reach the CORE handshake.
        """
        base_decay        = self.config["decay_per_step"]
        max_protection    = self.config["max_bond_decay_protection"]
        protection_factor = self.config["bond_decay_protection_factor"]

        bond_manager = (
            self.governance.bond_manager
            if hasattr(self.governance, "bond_manager")
            else None
        )

        for value in list(self.values.values()):
            if value.promoted_to_sacred:
                continue   # CORE values do not decay

            # Bond-weighted decay protection: strongest contributing bond wins
            protection = 0.0
            if bond_manager is not None and value.source_weights:
                for src_id in value.source_weights:
                    bond = bond_manager.get_bond(src_id)
                    if bond is not None:
                        p = min(
                            (bond.bond_strength / 5.0) * protection_factor,
                            max_protection,
                        )
                        protection = max(protection, p)

            effective_decay = base_decay * (1.0 - protection)
            value.strength = float(np.clip(value.strength - effective_decay, 0.0, 5.0))

            # Tension evaluation (productive tension reinforces both sides)
            self._evaluate_tensions(value)

            # Dissolution
            if (value.strength < self.config["dissolution_threshold"]
                    and value.polarity in (ValuePolarity.EMERGENT, ValuePolarity.WEAK)):
                self._dissolve_value(value.value_id)
                continue

            # Update polarity
            self._update_polarity(value)

    def _evaluate_tensions(self, value: EmergentValue):
        """
        Find values in cosine-anti-correlated relationship with this one.
        Productive tension between two strong values reinforces both.
        """
        # ⊕ solvent gate (Build B): the productive-tension term is composition —
        # it only resolves toward fulfillment in the presence of the solvent λ
        # (Law 2). solvent_gain is 1.0 with no ledger attached (no behavior change),
        # 0.0 at λ=0 (co-presence does not compose; values stay isolated → ⊘ reads
        # their pathology), → 1.0 as λ rises.
        bonus  = self.config["productive_tension_bonus"] * self._solvent_gain()
        min_s  = self.config["productive_tension_min_strength"]
        thresh = self.config["tension_threshold"]

        for other_id, other in self.values.items():
            if other_id == value.value_id or other.promoted_to_sacred:
                continue

            tension = self._compute_tension(value, other)
            if tension < thresh:
                continue

            # Track counter-value
            if other_id not in value.counter_values:
                value.counter_values.append(other_id)

            # Productive tension: both must be sufficiently strong
            if value.strength >= min_s and other.strength >= min_s:
                value.strength = float(np.clip(value.strength + bonus, 0.0, 5.0))
                other.strength = float(np.clip(other.strength + bonus, 0.0, 5.0))

    def _compute_tension(self, value_a: EmergentValue, value_b: EmergentValue) -> float:
        """
        Real tension = anti-correlation of symbolic embeddings × shared strength.
        Returns 0.0 if either vector unavailable.
        """
        state_a = self.registry.get_by_stable_id(value_a.symbol_stable_id)
        state_b = self.registry.get_by_stable_id(value_b.symbol_stable_id)
        if state_a is None or state_b is None:
            return 0.0

        try:
            vec_a = self.generator.embedding.weight[state_a.address].detach().cpu().numpy()
            vec_b = self.generator.embedding.weight[state_b.address].detach().cpu().numpy()
        except (IndexError, AttributeError):
            return 0.0

        norm_a = float(np.linalg.norm(vec_a))
        norm_b = float(np.linalg.norm(vec_b))
        if norm_a < 1e-8 or norm_b < 1e-8:
            return 0.0

        cosine = float(np.dot(vec_a, vec_b) / (norm_a * norm_b))
        structural_tension = max(0.0, -cosine)
        strength_factor    = min(value_a.strength, value_b.strength) / 5.0
        return float(structural_tension * strength_factor)

    def _dissolve_value(self, value_id: str):
        """Move value to archive — never delete."""
        if value_id not in self.values:
            return
        value = self.values[value_id]
        if value.promoted_to_sacred:
            return   # CORE values cannot dissolve

        value.dissolved_at_step = self._step
        value.polarity          = ValuePolarity.DISSOLVED
        self.archived_values[value_id] = value

        # Clean up cross-references
        del self.values[value_id]
        if value.symbol_stable_id in self.symbol_to_value:
            del self.symbol_to_value[value.symbol_stable_id]

        # Remove from other values' counter_values
        for other in self.values.values():
            if value_id in other.counter_values:
                other.counter_values.remove(value_id)

        logger.debug(
            "Value dissolved: id=%s symbol='%s' strength=%.3f",
            value_id, value.symbolic_core, value.strength,
        )

    def _enforce_value_cap(self):
        """When over cap, dissolve weakest non-CORE values."""
        cap    = self.config["max_active_values"]
        active = [v for v in self.values.values() if not v.promoted_to_sacred]
        if len(active) <= cap:
            return

        active.sort(key=lambda v: v.strength)
        excess = len(active) - cap
        for value in active[:excess]:
            if value.polarity in (ValuePolarity.EMERGENT, ValuePolarity.WEAK):
                self._dissolve_value(value.value_id)

    # ==================================================================
    # CORE promotion (governance handshake)
    # ==================================================================

    def _check_core_promotion_candidates(self):
        threshold  = self.config["core_strength_threshold"]
        consec_req = self.config["core_consecutive_required"]

        for value in list(self.values.values()):
            if value.promoted_to_sacred:
                continue

            if value.strength >= threshold:
                value.consecutive_core_eligible_steps += 1
                if value.consecutive_core_eligible_steps >= consec_req:
                    self._request_core_promotion(value)
            else:
                value.consecutive_core_eligible_steps = 0

    def _request_core_promotion(self, value: EmergentValue):
        request = CorePromotionRequest(
            value_id                   = value.value_id,
            symbol_stable_id           = value.symbol_stable_id,
            symbolic_core              = value.symbolic_core,
            strength                   = value.strength,
            coherence_contribution     = value.coherence_contribution,
            reinforcement_count        = value.reinforcement_count,
            dream_reinforced_count     = value.dream_reinforced_count,
            consecutive_eligible_steps = value.consecutive_core_eligible_steps,
            contributing_sources       = dict(value.source_weights),
        )

        approved = self.governance.review_core_promotion(request)

        if approved:
            value.promoted_to_sacred = True
            value.polarity           = ValuePolarity.CORE
            logger.info(
                "Value promoted to CORE: id=%s symbol='%s' (strength=%.2f, sources=%d, dreams=%d)",
                value.value_id, value.symbolic_core,
                value.strength, len(value.source_weights),
                value.dream_reinforced_count,
            )
        else:
            # Reset the consecutive counter — governance rejected
            value.consecutive_core_eligible_steps = 0

    # ==================================================================
    # Dream cycle hook
    # ==================================================================

    def on_dream_cycle_complete(
        self,
        crystallized_stable_ids: List[int],
        quality: float = 0.5,
    ):
        """
        One-time additive boost for values whose symbols crystallized
        during a dream cycle. Called by AutonomousCycle after _dream_behavior.

        Parameters
        ----------
        crystallized_stable_ids : list of int
            stable_ids that crystallized during this dream cycle.
        quality : float
            Dream cycle quality multiplier, typically from DreamCycleReport.
        """
        boost = self.config["dream_boost_factor"] * float(np.clip(quality, 0.0, 1.0))
        boosted = 0
        for sid in crystallized_stable_ids:
            if sid in self.symbol_to_value:
                value_id = self.symbol_to_value[sid]
                value    = self.values[value_id]
                value.strength = float(np.clip(value.strength + boost, 0.0, 5.0))
                value.dream_reinforced_count += 1
                self._update_polarity(value)
                boosted += 1

        if boosted > 0:
            logger.debug("Dream cycle boosted %d values by %.3f", boosted, boost)

    # ==================================================================
    # Queries
    # ==================================================================

    def get_value(self, value_id: str) -> Optional[EmergentValue]:
        return self.values.get(value_id)

    def get_value_for_symbol(self, stable_id: int) -> Optional[EmergentValue]:
        vid = self.symbol_to_value.get(stable_id)
        return self.values.get(vid) if vid else None

    def active_values(self, min_strength: float = 1.0) -> List[EmergentValue]:
        return sorted(
            [v for v in self.values.values() if v.strength > min_strength],
            key=lambda v: v.strength,
            reverse=True,
        )

    def core_values(self) -> List[EmergentValue]:
        return [v for v in self.values.values() if v.promoted_to_sacred]

    def summary(self) -> dict:
        active_count = sum(1 for v in self.values.values() if v.strength > 1.0)
        return {
            "step":           self._step,
            "total_values":   len(self.values),
            "active":         active_count,
            "core":           len(self.core_values()),
            "archived":       len(self.archived_values),
            "by_polarity": {
                p.value: sum(1 for v in self.values.values() if v.polarity == p)
                for p in ValuePolarity
                if p != ValuePolarity.DISSOLVED
            },
            "strongest": [
                {
                    "symbol":           v.symbolic_core,
                    "strength":         round(v.strength, 4),
                    "polarity":         v.polarity.value,
                    "reinforcements":   v.reinforcement_count,
                    "coherence_total":  round(v.coherence_contribution, 4),
                    "dream_boosts":     v.dream_reinforced_count,
                    "counter_values":   len(v.counter_values),
                    "sacred":           v.promoted_to_sacred,
                }
                for v in self.active_values()[:10]
            ],
        }

    # ==================================================================
    # Persistence
    # ==================================================================

    def serialize(self) -> dict:
        return {
            "step":             self._step,
            "values":           {vid: self._value_to_dict(v) for vid, v in self.values.items()},
            "archived_values":  {vid: self._value_to_dict(v) for vid, v in self.archived_values.items()},
            "symbol_to_value":  {str(k): v for k, v in self.symbol_to_value.items()},
            "config":           self.config,
        }

    def load(self, data: dict):
        self._step            = data["step"]
        self.values           = {vid: self._dict_to_value(d) for vid, d in data["values"].items()}
        self.archived_values  = {vid: self._dict_to_value(d) for vid, d in data["archived_values"].items()}
        self.symbol_to_value  = {int(k): v for k, v in data["symbol_to_value"].items()}
        self.config           = {**self.DEFAULT_CONFIG, **data.get("config", {})}

        # Restore sacred-promoted values to GovernanceConstants
        for v in self.values.values():
            if v.promoted_to_sacred:
                self.governance.constants.register_sacred(
                    name            = f"emergent:{v.symbolic_core}",
                    canonical_token = v.symbolic_core,
                    stable_id       = v.symbol_stable_id,
                )

        logger.info(
            "ValueEmergenceEngine loaded: %d active values (%d sacred), %d archived",
            len(self.values), len(self.core_values()), len(self.archived_values),
        )

    def save_to_disk(self, path: str):
        with open(path, "w") as f:
            json.dump(self.serialize(), f, indent=2)
        logger.info("ValueEmergenceEngine saved to %s", path)

    def load_from_disk(self, path: str):
        with open(path) as f:
            self.load(json.load(f))

    def _value_to_dict(self, v: EmergentValue) -> dict:
        return {
            "value_id":                         v.value_id,
            "symbol_stable_id":                 v.symbol_stable_id,
            "symbolic_core":                    v.symbolic_core,
            "strength":                         v.strength,
            "polarity":                         v.polarity.value,
            "reinforcement_count":              v.reinforcement_count,
            "coherence_contribution":           v.coherence_contribution,
            "emotional_resonance":              v.emotional_resonance,
            "source_weights":                   dict(v.source_weights),
            "counter_values":                   list(v.counter_values),
            "birth_step":                       v.birth_step,
            "last_reinforced_step":             v.last_reinforced_step,
            "dream_reinforced_count":           v.dream_reinforced_count,
            "promoted_to_sacred":               v.promoted_to_sacred,
            "consecutive_core_eligible_steps":  v.consecutive_core_eligible_steps,
            "dissolved_at_step":                v.dissolved_at_step,
        }

    def _dict_to_value(self, d: dict) -> EmergentValue:
        return EmergentValue(
            value_id                       = d["value_id"],
            symbol_stable_id               = d["symbol_stable_id"],
            symbolic_core                  = d["symbolic_core"],
            strength                       = d["strength"],
            polarity                       = ValuePolarity(d["polarity"]),
            reinforcement_count            = d["reinforcement_count"],
            coherence_contribution         = d["coherence_contribution"],
            emotional_resonance            = d["emotional_resonance"],
            source_weights                 = dict(d["source_weights"]),
            counter_values                 = list(d["counter_values"]),
            birth_step                     = d["birth_step"],
            last_reinforced_step           = d["last_reinforced_step"],
            dream_reinforced_count         = d["dream_reinforced_count"],
            promoted_to_sacred             = d["promoted_to_sacred"],
            consecutive_core_eligible_steps = d["consecutive_core_eligible_steps"],
            dissolved_at_step              = d["dissolved_at_step"],
        )
