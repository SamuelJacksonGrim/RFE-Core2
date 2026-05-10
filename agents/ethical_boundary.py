"""
agents/ethical_boundary.py

EthicalBoundarySystem — fast binary injection gate.

Runs before TrustLedger and SelfhoodGovernance. If a hard gate fires,
SelfhoodGovernance gets the result immediately and can issue REJECT or
SACRED_SHIELD without waiting for trust scoring.

Design constraints
------------------
  - Every hard gate must be O(1) or O(set lookup). No vector math.
  - Inputs are scalars already computed by the loop — no new work.
  - EthicalBoundarySystem has no power of its own. It raises flags.
    SelfhoodGovernance decides what to do with them.

Hard gates (block injection)
----------------------------
  source_toxic         source TrustLevel == TOXIC
  sacred_mutation      write op targeting a sacred stable_id
  field_collapse       coherence_delta below floor (scalar comparison)
  identity_drift       witness stability below floor (scalar comparison)
  flood                source exceeded injection rate ceiling

Soft warnings (advisory only, do not block)
-------------------------------------------
  low_coherence        coherence_delta negative but above hard floor
  novel_source         source_id has never been seen before
  high_tension         Watcher coherence_delta in warning band
"""

from __future__ import annotations

import collections
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from agents.governance_constants import GovernanceConstants
    from agents.trust_ledger import TrustLevel


# ---------------------------------------------------------------------------
# EthicalCheckResult
# ---------------------------------------------------------------------------

@dataclass
class EthicalCheckResult:
    """
    Output of EthicalBoundarySystem.check().
    Passed to SelfhoodGovernance.arbitrate().
    """
    passed:               bool
    hard_gates_fired:     List[str]
    soft_warnings:        List[str]
    recommended_decision: str   # "ALLOW" | "REJECT" | "SACRED_SHIELD" | "QUARANTINE"

    def __bool__(self) -> bool:
        return self.passed


# ---------------------------------------------------------------------------
# EthicalBoundarySystem
# ---------------------------------------------------------------------------

class EthicalBoundarySystem:
    """
    Lightweight binary injection gate.

    Parameters
    ----------
    governance_constants : GovernanceConstants
        For sacred_ids set membership checks.
    config : dict or None
        Threshold overrides.
    """

    DEFAULT_CONFIG = {
        "coherence_floor":          -0.30,   # hard block below this
        "coherence_soft_threshold": -0.05,   # soft warning below this
        "stability_floor":           0.10,   # hard block below this
        "flood_window_seconds":     60.0,    # rolling window for rate check
        "flood_ceiling":             12,     # max injections per window per source
    }

    def __init__(
        self,
        governance_constants: "GovernanceConstants",
        config: Optional[dict] = None,
    ):
        self.constants = governance_constants
        self.config    = {**self.DEFAULT_CONFIG, **(config or {})}

        # Per-source injection timestamps — bounded deque, O(1) append
        self._injection_log: Dict[str, collections.deque] = {}

    # ------------------------------------------------------------------
    # Main check
    # ------------------------------------------------------------------

    def check(
        self,
        op:                  str,          # "read" | "write"
        source_trust_level:  "TrustLevel",
        stable_ids:          List[int],
        coherence_delta:     float,
        witness_stability:   float,
        source_id:           str,
        known_source:        bool = True,  # False if source_id never seen before
    ) -> EthicalCheckResult:
        """
        Run all gates against already-computed scalars.

        Parameters
        ----------
        op : str
            "read" — referencing a symbol (usually allowed)
            "write" — registering / injecting / modifying a symbol
        source_trust_level : TrustLevel
            Current level from TrustLedger (dict lookup by caller).
        stable_ids : list of int
            Symbols involved in this operation.
        coherence_delta : float
            From CoherenceReport.coherence_delta (already computed).
        witness_stability : float
            From Witness.identity_stability() (already computed).
        source_id : str
        known_source : bool
            False if this source_id has never appeared in TrustLedger.
        """
        from agents.trust_ledger import TrustLevel

        hard: List[str] = []
        soft: List[str] = []

        # -- Log injection for flood check --
        self._log_injection(source_id)

        # ==========================================================
        # HARD GATES (O(1) each)
        # ==========================================================

        # 1. Toxic source — reject immediately regardless of content
        if source_trust_level == TrustLevel.TOXIC:
            hard.append("source_toxic")

        # 2. Sacred mutation — write op targeting a sacred symbol
        if op == "write" and stable_ids:
            for sid in stable_ids:
                if self.constants.is_sacred(sid):
                    hard.append("sacred_mutation")
                    break

        # 3. Field collapse — coherence_delta below floor (scalar compare)
        if coherence_delta < self.config["coherence_floor"]:
            hard.append("field_collapse")

        # 4. Identity drift — witness stability critically low
        if witness_stability < self.config["stability_floor"]:
            hard.append("identity_drift")

        # 5. Flood — source injection rate above ceiling
        if self._is_flooding(source_id):
            hard.append("flood")

        # ==========================================================
        # SOFT WARNINGS (advisory, no blocking)
        # ==========================================================

        # Coherence in warning band (negative but above hard floor)
        if (self.config["coherence_floor"] <= coherence_delta
                < self.config["coherence_soft_threshold"]):
            soft.append("low_coherence")

        # Novel source — first time we've seen this source_id
        if not known_source:
            soft.append("novel_source")

        # ==========================================================
        # Recommendation
        # ==========================================================

        passed = len(hard) == 0

        if not passed:
            if "sacred_mutation" in hard:
                rec = "SACRED_SHIELD"
            elif "flood" in hard:
                rec = "QUARANTINE"
            elif "source_toxic" in hard:
                rec = "REJECT"
            else:
                rec = "REJECT"
        else:
            rec = "ALLOW"

        return EthicalCheckResult(
            passed               = passed,
            hard_gates_fired     = hard,
            soft_warnings        = soft,
            recommended_decision = rec,
        )

    # ------------------------------------------------------------------
    # Flood tracking  (O(1) amortized)
    # ------------------------------------------------------------------

    def _log_injection(self, source_id: str):
        """Record this injection timestamp for rate tracking."""
        if source_id not in self._injection_log:
            self._injection_log[source_id] = collections.deque()
        self._injection_log[source_id].append(time.time())

    def _is_flooding(self, source_id: str) -> bool:
        """
        Count injections within the rolling window.
        Evicts stale entries from the left in O(k) where k = stale count.
        """
        if source_id not in self._injection_log:
            return False

        log    = self._injection_log[source_id]
        cutoff = time.time() - self.config["flood_window_seconds"]

        # Evict stale timestamps
        while log and log[0] < cutoff:
            log.popleft()

        return len(log) > self.config["flood_ceiling"]

    # ------------------------------------------------------------------
    # Diagnostics
    # ------------------------------------------------------------------

    def summary(self) -> dict:
        return {
            "tracked_sources":  len(self._injection_log),
            "config":           self.config,
        }
