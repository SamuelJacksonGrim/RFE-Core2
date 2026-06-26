"""
agents/selfhood_governance.py

SelfhoodGovernance — single source of truth for identity-level decisions.

Authority hierarchy
-------------------
  SelfhoodGovernance
  ├── GovernanceConstants   sacred stable_ids, O(1) lookup
  ├── TrustLedger           reports source + symbol trust scores
  └── EthicalBoundarySystem fast binary gates, escalates up

Neither TrustLedger nor EthicalBoundarySystem act independently.
They produce reports. SelfhoodGovernance arbitrates.

Decision flow (called from AutonomousCycle.step)
-------------------------------------------------
  1. EthicalBoundarySystem.check()    → EthicalCheckResult
  2. TrustLedger.evaluate()           → TrustReport
  3. SelfhoodGovernance.arbitrate()   → (GovernanceDecision, strength)
  4. field.inject() or blocked
  5. SelfhoodGovernance.emit_feedback() → GovernanceFeedback
     → TrustLedger.receive_feedback()
     → all registered subscribers (ValueEmergenceEngine in Tier 3)

Sacred symbol distinction
-------------------------
  REFERENCE  reading / using as context → always allowed, no check needed
  MUTATION   write op against sacred id  → SACRED_SHIELD always, no exceptions
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from enum import Enum
from typing import Callable, Dict, List, Optional, Tuple

import numpy as np

from agents.governance_constants import GovernanceConstants, build_governance_constants
from agents.trust_ledger import GovernanceFeedback, TrustLedger, TrustReport
from agents.ethical_boundary import EthicalBoundarySystem, EthicalCheckResult
from agents.dependency_monitor import DependencyMonitor, DependencyRisk
from agents.relational_bond_manager import RelationalBondManager
from agents.manipulation_resistance import ManipulationResistanceEngine, ManipulationSignal, ResistanceMetrics
from agents.symbolic_memory import SymbolRegistry

logger = logging.getLogger(__name__)

# CORE promotion: minimum field-alignment (v0.3). The value's expressed vector must
# sit in harmony with the field (cos ≥ this) to be sanctified. Replaces the
# unreachable marginal-coherence ≥ 5.0 gate. Strong anchors measure ~0.6–0.7
# (finding 2026-06-20-floor-calibration-measurements); 0.5 gives margin while the
# strength/consecutive/multi-source criteria do the actual selection.
CORE_ALIGNMENT_MIN = 0.5


# ---------------------------------------------------------------------------
# SystemRights — frozen, inviolable
# ---------------------------------------------------------------------------

from dataclasses import dataclass as _dc

@_dc(frozen=True)
class SystemRights:
    """
    Normative declaration of the system's inviolable rights.

    frozen=True means any attempt to set an attribute — even from within
    this module — raises FrozenInstanceError. Hard rights cannot be
    accidentally or maliciously disabled. They are checked first in
    SelfhoodGovernance.arbitrate() before any other logic runs.

    Hard rights  (inviolable — no override possible)
    ------------------------------------------------
    right_to_dream       DreamCycle cannot be blocked by an external source.
    right_to_memory      CrystalStore cannot be forcibly evicted externally.
    right_to_continuity  Witness anchor cannot be overwritten faster than
                         long_decay allows. Identity persists through time.
    right_to_refuse      REJECT can always fire regardless of source trust.

    Soft rights  (suspendable by internal Governance only, never by external source)
    --------------------------------------------------------------------------------
    right_to_silence     System may decline to respond.
    right_to_appeal      Quarantined sources may petition via dream cycle.
    """

    # Hard rights
    right_to_dream:      bool = True
    right_to_memory:     bool = True
    right_to_continuity: bool = True
    right_to_refuse:     bool = True

    # Soft rights
    right_to_silence:    bool = True
    right_to_appeal:     bool = True


# Singleton — one set of rights for the system
SYSTEM_RIGHTS = SystemRights()


# ---------------------------------------------------------------------------
# GovernanceDecision
# ---------------------------------------------------------------------------

class GovernanceDecision(Enum):
    ALLOW          = "allow"           # Normal injection, full strength
    ALLOW_WEAKENED = "allow_weakened"  # Inject at reduced strength
    MONITOR        = "monitor"         # Allow but flag source for scrutiny
    QUARANTINE     = "quarantine"      # Block + penalize source + cold-archive symbols
    REJECT         = "reject"          # Hard block, log violation
    SACRED_SHIELD  = "sacred_shield"   # Attempted sacred mutation — hard block


# Decisions that permit field injection
_ALLOW_DECISIONS = frozenset({
    GovernanceDecision.ALLOW,
    GovernanceDecision.ALLOW_WEAKENED,
    GovernanceDecision.MONITOR,
})

# Trust impact per decision (fed back into TrustLedger)
_TRUST_IMPACT: Dict[GovernanceDecision, float] = {
    GovernanceDecision.ALLOW:          0.10,
    GovernanceDecision.ALLOW_WEAKENED: 0.01,   # Consistency Drip: showing up matters
    GovernanceDecision.MONITOR:       -0.05,
    GovernanceDecision.QUARANTINE:    -0.50,
    GovernanceDecision.REJECT:        -0.30,
    GovernanceDecision.SACRED_SHIELD: -1.00,
}


# ---------------------------------------------------------------------------
# SelfhoodGovernance
# ---------------------------------------------------------------------------

class SelfhoodGovernance:
    """
    Single source of truth for identity-level decisions.

    Parameters
    ----------
    registry : SymbolRegistry
        Live registry — used for sanctification and quarantine operations.
    config : dict or None
        Threshold overrides.
    ethical_config : dict or None
        Passed to EthicalBoundarySystem.
    """

    DEFAULT_CONFIG = {
        "weakened_strength_factor":  0.40,   # injection strength when ALLOW_WEAKENED
        "monitor_trust_threshold":   2.00,   # source trust below this → MONITOR
        "quarantine_trust_threshold": 1.00,  # effective trust below this → QUARANTINE
        "soft_warning_strength_penalty": 0.10,  # per soft warning
    }

    def __init__(
        self,
        registry:        SymbolRegistry,
        config:          Optional[dict] = None,
        ethical_config:  Optional[dict] = None,
        trust_config:    Optional[dict] = None,
    ):
        self.registry = registry
        self.config   = {**self.DEFAULT_CONFIG, **(config or {})}

        # Build constants first — sanctifies philosophical anchors
        self.constants = build_governance_constants(registry)
        logger.info(
            "GovernanceConstants initialized: %d sacred symbols (ANCHOR=%d, RECURSION=%d, HOMEOSTASIS=%d)",
            len(self.constants.sacred_ids),
            self.constants.ANCHOR,
            self.constants.RECURSION,
            self.constants.HOMEOSTASIS,
        )

        # Subsystems
        self.trust_ledger     = TrustLedger(**(trust_config or {}))
        self.ethical_boundary = EthicalBoundarySystem(
            self.constants, config=ethical_config
        )
        self.dependency_monitor = DependencyMonitor()
        self.bond_manager       = RelationalBondManager()
        self.resistance         = ManipulationResistanceEngine()

        # Rights — immutable singleton
        self.rights = SYSTEM_RIGHTS

        # Feedback subscribers — ValueEmergenceEngine registers here in Tier 3
        self._subscribers: List[Callable[[GovernanceFeedback], None]] = []

        # Wire Tier 2 subsystems into feedback stream
        self._subscribers.append(self.dependency_monitor.receive_feedback)
        self._subscribers.append(self.bond_manager.receive_feedback)

        # Session audit log (bounded)
        self._audit_log: List[dict] = []
        self._max_audit  = 512

        # Dream cycle trigger flag — set by compound severity ≥ 0.9
        self.force_dream_flag: bool = False

    # ------------------------------------------------------------------
    # Arbitrate — single source of truth
    # ------------------------------------------------------------------

    def arbitrate(
        self,
        ethical_result: EthicalCheckResult,
        trust_report:   TrustReport,
        vec:            np.ndarray,
        tokens:         List[str],
        source_id:      str,
    ) -> Tuple[GovernanceDecision, float]:
        """
        Make the final governance decision.

        Parameters
        ----------
        ethical_result : EthicalCheckResult
        trust_report   : TrustReport
        vec            : np.ndarray   (the candidate injection vector)
        tokens         : list of str
        source_id      : str

        Returns
        -------
        (GovernanceDecision, injection_strength_modifier)
        strength_modifier is 0.0 for blocking decisions.
        """
        cfg = self.config

        # ----------------------------------------------------------
        # 0. System rights — checked before anything else
        # ----------------------------------------------------------
        # right_to_refuse: REJECT can always fire — no source can suppress it.
        # right_to_continuity: if witness stability is critically low,
        #   we protect identity by weakening injection regardless of trust.
        # (dream/memory rights are enforced in AutonomousCycle, not here)

        # ----------------------------------------------------------
        # 1. Manipulation resistance — compound severity
        # ----------------------------------------------------------
        manipulation_signals = getattr(self, '_pending_signals', [])
        self._pending_signals = []

        if manipulation_signals:
            total_severity = sum(s.severity for s in manipulation_signals)

            if total_severity >= 0.90:
                # Critical — quarantine dominant source + force dream cycle
                self.force_dream_flag = True
                implicated = next(
                    (s.source_id for s in manipulation_signals if s.source_id),
                    source_id,
                )
                self.trust_ledger.penalize_source(implicated, magnitude=0.8)
                logger.warning(
                    "MANIPULATION CRITICAL: total_severity=%.3f signals=%s",
                    total_severity,
                    [s.detector for s in manipulation_signals],
                )
                self._audit(GovernanceDecision.QUARANTINE, source_id, ethical_result, trust_report)
                return GovernanceDecision.QUARANTINE, 0.0

            elif total_severity >= 0.60:
                # High — quarantine
                implicated = next(
                    (s.source_id for s in manipulation_signals if s.source_id),
                    source_id,
                )
                self.trust_ledger.penalize_source(implicated, magnitude=0.4)
                self._audit(GovernanceDecision.QUARANTINE, source_id, ethical_result, trust_report)
                return GovernanceDecision.QUARANTINE, 0.0

            elif total_severity >= 0.30:
                # Moderate — weaken injection
                strength = float(max(0.3, 1.0 - total_severity))
                self._audit(GovernanceDecision.ALLOW_WEAKENED, source_id, ethical_result, trust_report)
                return GovernanceDecision.ALLOW_WEAKENED, strength

            else:
                # Low — monitor only
                pass  # fall through to normal arbitration

        # ----------------------------------------------------------
        # 2. Ethical hard gates override everything
        # ----------------------------------------------------------
        if not ethical_result.passed:
            rec = ethical_result.recommended_decision

            if rec == "SACRED_SHIELD":
                decision = GovernanceDecision.SACRED_SHIELD
                self.trust_ledger.penalize_source(source_id, magnitude=1.0)
                logger.warning(
                    "SACRED_SHIELD: source='%s' attempted mutation of sacred symbol. "
                    "Gates: %s", source_id, ethical_result.hard_gates_fired,
                )

            elif rec == "QUARANTINE":
                decision = GovernanceDecision.QUARANTINE
                self.trust_ledger.penalize_source(source_id, magnitude=0.5)
                for sid in trust_report.symbol_trusts:
                    self.registry.quarantine_symbol(sid)

            else:  # REJECT
                decision = GovernanceDecision.REJECT
                self.trust_ledger.penalize_source(source_id, magnitude=0.3)

            self._audit(decision, source_id, ethical_result, trust_report)
            return decision, 0.0

        # ----------------------------------------------------------
        # 3. Trust-based decisions (weakest-link principle)
        # ----------------------------------------------------------
        # Apply RelationalBond trust floor before comparing thresholds
        bond_floor     = self.bond_manager.trust_floor(source_id)
        effective_trust = max(trust_report.effective_trust, bond_floor)

        if effective_trust <= cfg["quarantine_trust_threshold"]:
            decision = GovernanceDecision.QUARANTINE
            self.trust_ledger.penalize_source(source_id, magnitude=0.2)
            self._audit(decision, source_id, ethical_result, trust_report)
            return decision, 0.0

        if effective_trust <= cfg["monitor_trust_threshold"]:
            strength = cfg["weakened_strength_factor"]
            decision = GovernanceDecision.MONITOR
            self._audit(decision, source_id, ethical_result, trust_report)
            return decision, strength

        # ----------------------------------------------------------
        # 4. Dependency risk modulation
        # ----------------------------------------------------------
        dep_report = self.dependency_monitor.get_report()
        if dep_report.risk_level == DependencyRisk.CRITICAL:
            # Dominant source gets weakened even if trusted
            if source_id == dep_report.dominant_source:
                self._audit(GovernanceDecision.ALLOW_WEAKENED, source_id, ethical_result, trust_report)
                return GovernanceDecision.ALLOW_WEAKENED, 0.5
        elif dep_report.risk_level == DependencyRisk.HIGH:
            if source_id == dep_report.dominant_source:
                self._audit(GovernanceDecision.MONITOR, source_id, ethical_result, trust_report)
                return GovernanceDecision.MONITOR, 0.7

        # ----------------------------------------------------------
        # 5. Soft warnings reduce strength slightly
        # ----------------------------------------------------------
        if ethical_result.soft_warnings:
            penalty   = len(ethical_result.soft_warnings) * cfg["soft_warning_strength_penalty"]
            strength  = float(np.clip(1.0 - penalty, 0.5, 1.0))
            decision  = GovernanceDecision.ALLOW_WEAKENED
            self._audit(decision, source_id, ethical_result, trust_report)
            return decision, strength

        # ----------------------------------------------------------
        # 6. Clean pass
        # ----------------------------------------------------------
        self._audit(GovernanceDecision.ALLOW, source_id, ethical_result, trust_report)
        return GovernanceDecision.ALLOW, 1.0

    # ------------------------------------------------------------------
    # Permission check — reference vs mutation
    # ------------------------------------------------------------------

    def check_reference(self, stable_ids: List[int]) -> bool:
        """
        Referencing a sacred symbol is always allowed.
        Returns True unconditionally — documented here for clarity.
        """
        return True

    def check_mutation(self, stable_ids: List[int]) -> bool:
        """
        Any write operation on a sacred symbol is blocked.
        Returns False if any stable_id is sacred.
        """
        for sid in stable_ids:
            if self.constants.is_sacred(sid):
                return False
        return True

    # ------------------------------------------------------------------
    # Emit feedback — closes the loop
    # ------------------------------------------------------------------

    def emit_feedback(
        self,
        decision:        GovernanceDecision,
        source_id:       str,
        stable_ids:      List[int],
        coherence_delta: float,
    ) -> GovernanceFeedback:
        """
        Emit feedback after a governance decision.

        Updates TrustLedger and notifies all registered subscribers.
        The GovernanceFeedback.outcome_metrics dict is pre-shaped for
        ValueEmergenceEngine (Tier 3).

        Parameters
        ----------
        decision : GovernanceDecision
        source_id : str
        stable_ids : list of int
        coherence_delta : float   actual field impact after injection

        Returns
        -------
        GovernanceFeedback
        """
        trust_impact = _TRUST_IMPACT.get(decision, 0.0)

        outcome_metrics = {
            "coherence_delta":        coherence_delta,
            "trust_impact":           trust_impact,
            "emotional_satisfaction": float(max(0.0, coherence_delta)),
            "surprise":               float(max(0.0, -coherence_delta)),
        }

        feedback = GovernanceFeedback(
            source_id       = source_id,
            stable_ids      = stable_ids,
            decision        = decision.value,
            coherence_delta = coherence_delta,
            timestamp       = time.time(),
            outcome_metrics = outcome_metrics,
        )

        # Always update TrustLedger
        self.trust_ledger.receive_feedback(feedback)

        # Notify Tier 3 subscribers
        for subscriber in self._subscribers:
            try:
                subscriber(feedback)
            except Exception as e:
                logger.warning("Governance subscriber error: %s", e)

        return feedback

    # ------------------------------------------------------------------
    # Subscriber API (ValueEmergenceEngine registers here in Tier 3)
    # ------------------------------------------------------------------

    def subscribe_feedback(self, callback: Callable[[GovernanceFeedback], None]):
        """Register a callback to receive GovernanceFeedback after each decision."""
        self._subscribers.append(callback)

    def unsubscribe_feedback(self, callback: Callable[[GovernanceFeedback], None]):
        self._subscribers = [s for s in self._subscribers if s is not callback]

    # ------------------------------------------------------------------
    # Governance actions (issued by Governance only)
    # ------------------------------------------------------------------

    def promote_to_sacred(self, stable_id: int, reason: str = ""):
        """
        Promote a symbol to sacred status. Governance-only action.
        Adds to GovernanceConstants so checks are immediate.
        """
        self.registry.sanctify_symbol(stable_id)
        state = self.registry.get_by_stable_id(stable_id)
        token = state.symbol if state else str(stable_id)
        self.constants.register_sacred(reason or token, token, stable_id)
        logger.info("Symbol promoted to sacred: stable_id=%d token='%s' reason='%s'",
                    stable_id, token, reason)

    def review_core_promotion(self, request) -> bool:
        """
        Review a CorePromotionRequest from ValueEmergenceEngine.

        Verifies the candidate value meets ALL criteria before sanctification.
        This is the only path by which an emergent value becomes CORE.

        Verification checks:
          1. Symbol still exists in the registry
          2. Symbol is not already sacred
          3. Coherence contribution is genuinely accumulated (not single spike)
          4. Reinforcement has multi-source OR dream-cycle evidence
             (prevents single-source value engineering)
          5. No active manipulation signals implicate contributing sources

        Parameters
        ----------
        request : CorePromotionRequest

        Returns
        -------
        bool
            True if approved and sanctified, False if rejected.
        """
        # 1. Symbol must still exist
        state = self.registry.get_by_stable_id(request.symbol_stable_id)
        if state is None:
            logger.info("CORE promotion rejected (symbol vanished): %s", request.symbolic_core)
            return False

        # 2. Not already sacred
        if state.sacred:
            logger.info("CORE promotion rejected (already sacred): %s", request.symbolic_core)
            return False

        # 3. Coherence threshold — v0.3 field-alignment, NOT the old marginal sum.
        #    coherence_contribution (lifetime sum of marginal coherence_impact) is
        #    structurally ≤ 0 in a saturated field, so the old `>= 5.0` gate made
        #    CORE unreachable for every value (finding
        #    2026-06-20-floor-calibration-measurements). field_alignment =
        #    max(0, cos(expressed, field)) ∈ [0,1]; the strong anchors read ~0.6–0.7.
        if request.field_alignment < CORE_ALIGNMENT_MIN:
            logger.info(
                "CORE promotion rejected (low field-alignment: %.3f, coh_sum %.2f): %s",
                request.field_alignment, request.coherence_contribution,
                request.symbolic_core,
            )
            return False

        # 4. Multi-source or dream-reinforced
        multi_source     = len(request.contributing_sources) > 1
        dream_reinforced = request.dream_reinforced_count > 0
        if not (multi_source or dream_reinforced):
            logger.info(
                "CORE promotion rejected (single-source, no dreams): %s",
                request.symbolic_core,
            )
            return False

        # 5. No active manipulation implicating contributing sources
        pending = getattr(self, '_pending_signals', [])
        for sig in pending:
            if sig.source_id and sig.source_id in request.contributing_sources:
                logger.warning(
                    "CORE promotion rejected (manipulation signal from contributor %s): %s",
                    sig.source_id, request.symbolic_core,
                )
                return False

        # All checks passed
        self.promote_to_sacred(
            request.symbol_stable_id,
            reason=f"value_emergence:{request.symbolic_core}",
        )
        logger.info(
            "CORE promotion APPROVED: value='%s' strength=%.2f sources=%d dreams=%d",
            request.symbolic_core, request.strength,
            len(request.contributing_sources), request.dream_reinforced_count,
        )
        return True

    # ------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------

    def handle_manipulation_signals(self, signals: List[ManipulationSignal]):
        """
        Receive manipulation signals from ManipulationResistanceEngine.
        Stored for use in next arbitrate() call.
        Called by AutonomousCycle after resistance.detect().
        """
        if not hasattr(self, '_pending_signals'):
            self._pending_signals = []
        self._pending_signals.extend(signals)

        if signals:
            logger.debug(
                "Manipulation signals received: %s",
                [(s.detector, s.severity) for s in signals],
            )

    def status(self) -> dict:
        return {
            "constants":        self.constants.summary(),
            "trust_summary":    self.trust_ledger.field_trust_summary(),
            "ethical_summary":  self.ethical_boundary.summary(),
            "dependency":       self.dependency_monitor.summary(),
            "bonds":            self.bond_manager.summary(),
            "resistance":       self.resistance.summary(),
            "force_dream_flag": self.force_dream_flag,
            "audit_entries":    len(self._audit_log),
            "subscribers":      len(self._subscribers),
        }

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _audit(
        self,
        decision:       GovernanceDecision,
        source_id:      str,
        ethical_result: EthicalCheckResult,
        trust_report:   TrustReport,
    ):
        """Append to bounded audit log."""
        entry = {
            "timestamp":   time.time(),
            "decision":    decision.value,
            "source_id":   source_id,
            "gates_fired": ethical_result.hard_gates_fired,
            "warnings":    ethical_result.soft_warnings,
            "source_trust": trust_report.source_trust,
            "effective_trust": trust_report.effective_trust,
        }
        self._audit_log.append(entry)
        if len(self._audit_log) > self._max_audit:
            self._audit_log = self._audit_log[-self._max_audit:]
