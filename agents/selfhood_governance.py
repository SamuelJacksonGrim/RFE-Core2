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
from agents.symbolic_memory import SymbolRegistry

logger = logging.getLogger(__name__)


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
    GovernanceDecision.ALLOW_WEAKENED: 0.00,
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
        self.trust_ledger    = TrustLedger(**(trust_config or {}))
        self.ethical_boundary = EthicalBoundarySystem(
            self.constants, config=ethical_config
        )

        # Feedback subscribers — ValueEmergenceEngine registers here in Tier 3
        self._subscribers: List[Callable[[GovernanceFeedback], None]] = []

        # Session audit log (bounded)
        self._audit_log: List[dict] = []
        self._max_audit  = 512

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
        # 1. Ethical hard gates override everything
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
        # 2. Trust-based decisions (weakest-link principle)
        # ----------------------------------------------------------
        effective_trust = trust_report.effective_trust

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
        # 3. Soft warnings reduce strength slightly
        # ----------------------------------------------------------
        if ethical_result.soft_warnings:
            penalty   = len(ethical_result.soft_warnings) * cfg["soft_warning_strength_penalty"]
            strength  = float(np.clip(1.0 - penalty, 0.5, 1.0))
            decision  = GovernanceDecision.ALLOW_WEAKENED
            self._audit(decision, source_id, ethical_result, trust_report)
            return decision, strength

        # ----------------------------------------------------------
        # 4. Clean pass
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

    # ------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------

    def status(self) -> dict:
        return {
            "constants":       self.constants.summary(),
            "trust_summary":   self.trust_ledger.field_trust_summary(),
            "ethical_summary": self.ethical_boundary.summary(),
            "audit_entries":   len(self._audit_log),
            "subscribers":     len(self._subscribers),
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
