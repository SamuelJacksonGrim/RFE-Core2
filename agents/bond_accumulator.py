"""
agents/bond_accumulator.py

BondFormationAccumulator — bond formation as accumulation-to-bound.

Replaces the *quality* half of the instantaneous bond-formation gate with a
leaky, asymmetric drift-diffusion accumulator (DDM). A bond is proposed when
integrated evidence crosses an accept bound, not when a snapshot read clears
a threshold. Mechanism adapted from Armstrong & Vlasov (PNAS 2026, preprint
bioRxiv 2025.03.29.646003) — the substrate-free mechanism and its acceptance
signatures only; none of the neuroanatomy transfers or is claimed to.

Continuous form (Ornstein-Uhlenbeck flavored):

    dV = (mu_evidence - leak * V) dt + sigma dW

discretized one step per GovernanceFeedback for the candidate source
(Euler-Maruyama, dt = 1 feedback step):

    V <- V + (mu - leak * V) + sigma * randn()
    V >= B_accept  -> ACCEPT          (bond proposed; manager still checks
                                       the structural formation preconditions)
    V <= B_reject  -> REJECT_ACTIVE   (structured negative evidence — a
                                       decision, not the absence of one)
    steps > T_max  -> REJECT_TIMEOUT  (nothing accumulated; input was noise)

Evidence — what drives the drift
--------------------------------
The drift rides the LIVE per-contribution signal, not the marginal
coherence_delta (structurally ~0 in a saturated field — the F7/F8/F9 disease;
see docs/findings/2026-07-09-bond-establishment-gate.md). Per feedback step:

    allow                    c = +field_alignment            (p50 ~0.98 live)
    allow_weakened, monitor  c = +WEAK_EVIDENCE_FACTOR * field_alignment
    reject                   c = -0.3   } mirror the trust-penalty
    quarantine               c = -0.5   } magnitudes — one shared
    sacred_shield            c = -1.0   } severity economy

    mu = G_PLUS * max(c, 0) - G_MINUS * max(-c, 0)
    G_MINUS = G_PLUS * TRUST_ASYMMETRY

ALLOW_WEAKENED is weak POSITIVE evidence, never negative: ambient systemic
weakening (identity_erosion on dream-band traffic) is not the source's fault
— same reasoning as the governance attribution rule (2026-07-06) and the
Consistency Drip ("showing up matters").

Asymmetry — where the 40-80x lives
-----------------------------------
Two independent levers carry "easier to lose than earn":
  drift asymmetry   TRUST_ASYMMETRY = 60 — matches the existing trust
                    economy (+0.01 drip vs 0.4-0.8 penalties = 40-80x;
                    BACKLOG "trust learning-rate asymmetry")
  bound geometry    B_accept = 1.0 far, B_reject = -0.5 near, V0 = 0.0
                    biased toward the reject side.
A perfect source (c = 1.0 every step, no leak, no noise) needs at least
B_accept / G_PLUS = 20 steps to cross — the accumulator's minimum decision
time reproduces the classical formation_interaction_threshold (20) by
construction. A single max-magnitude spike moves V by G_PLUS = 0.05 (burst
immune); sustained weakened trickle equilibrates at
G_PLUS * WEAK_FACTOR * align / leak ~ 0.49 < B_accept, and with sigma =
0.02 the OU stationary noise sd is sigma / sqrt(2 * leak) = 0.10, so the
accept bound sits ~5.1 stationary-sd above the trickle equilibrium (trickle
immune — the leak wins and noise cannot bridge the gap; at the earlier 0.25
weak factor the gap was 3.9 sd and ~1% of 2000-step trickle trials crossed:
measured, then closed) and 5 stationary-sd above pure noise (no spurious
accepts; B_reject likewise 5 sd from a pure-noise walk). One quarantine
drives V by -1.5 (active rejection in one step — denial is cheap).

Placement & invariants
----------------------
Lives INSIDE RelationalBondManager's pre-bond path, fed per
GovernanceFeedback — downstream of arbitrate(), exactly where the
instantaneous gate it replaces lived. The field NEVER reads V: the only
output is a discrete formation proposal, and a formed bond's sole effect
remains the existing trust_floor (bond_strength * 0.40, hard-capped by the
strength clip). V is hard-clamped to [B_reject, B_accept] (bounded state,
runtime guard) and all per-source state is population-capped. Sacred
symbols, attribution, and the governance authority hierarchy are untouched.
Opt-in, default OFF (graduation rule).

All physics constants below are the architect's hand — placeholders chosen
by calibration against the live substrate, finalized by Samuel, not
self-proposed by the system.
"""

from __future__ import annotations

import logging
from collections import Counter, OrderedDict, deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Optional

import numpy as np

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Outcomes
# ---------------------------------------------------------------------------

class AccumulatorOutcome(Enum):
    NONE           = "none"            # still accumulating (no decision yet)
    ACCEPT         = "accept"          # crossed B_accept — bond proposed
    REJECT_ACTIVE  = "reject_active"   # crossed B_reject — decisive rejection
    REJECT_TIMEOUT = "reject_timeout"  # choice window elapsed — input was noise


# Evidence value per blocking decision — mirrors the trust-penalty magnitudes
# (_TRUST_IMPACT in selfhood_governance) so bond denial and trust loss share
# one severity economy.
_NEGATIVE_EVIDENCE: Dict[str, float] = {
    "reject":        -0.3,
    "quarantine":    -0.5,
    "sacred_shield": -1.0,
}

# Decisions that inject (positive-evidence side)
_CLEAN_POSITIVE = frozenset({"allow"})
_WEAK_POSITIVE  = frozenset({"allow_weakened", "monitor"})


# ---------------------------------------------------------------------------
# Per-candidate state
# ---------------------------------------------------------------------------

@dataclass
class CandidateState:
    """Accumulation state for one pre-bond candidate source."""
    V:            float = 0.0
    steps:        int   = 0          # steps in the current choice window
    windows:      int   = 0          # completed windows (any outcome)
    outcomes:     Counter = field(default_factory=Counter)
    last_outcome: str   = AccumulatorOutcome.NONE.value
    trace:        deque = field(default_factory=lambda: deque(maxlen=64))

    def snapshot(self) -> dict:
        return {
            "V":            round(self.V, 4),
            "steps":        self.steps,
            "windows":      self.windows,
            "outcomes":     dict(self.outcomes),
            "last_outcome": self.last_outcome,
        }


# ---------------------------------------------------------------------------
# BondFormationAccumulator
# ---------------------------------------------------------------------------

class BondFormationAccumulator:
    """
    Leaky asymmetric drift-diffusion accumulator for bond formation.

    One decision variable V per pre-bond candidate source, advanced one step
    per GovernanceFeedback for that source. Emits a discrete
    AccumulatorOutcome; commits nothing itself — RelationalBondManager owns
    the formation decision and still applies the structural preconditions
    (interaction_count, crystal_count).

    Parameters (architect-set physics; see module docstring)
    ----------
    g_plus : float
        Drift gain on positive evidence.
    trust_asymmetry : float
        g_minus / g_plus ratio, in [40, 80]. Negative evidence drifts this
        many times faster than positive.
    leak : float
        Forgetting rate. Larger = more trickle-immune, less sensitive to
        genuine slow evidence (the key robustness/sensitivity trade-off).
    sigma : float
        Diffusion noise scale. Must be nonzero — without it the varCE
        signature cannot exist and the accumulator degenerates to a ramp.
    b_accept, b_reject, v0 : float
        Bound geometry and starting bias (accept far, reject near).
    t_max : int
        Choice-window length in per-source feedback steps before a
        no-decision times out to default reject.
    weak_evidence_factor : float
        Evidence weight for allow_weakened / monitor relative to clean allow.
    seed : int
        Dedicated RNG seed — the accumulator never touches the global numpy
        stream, so runs stay deterministic with the lever ON or OFF.
    max_candidates : int
        Population cap on tracked candidates (oldest-touched evicted).
    """

    def __init__(
        self,
        g_plus:               float = 0.05,
        trust_asymmetry:      float = 60.0,
        leak:                 float = 0.02,
        sigma:                float = 0.02,
        b_accept:             float = 1.0,
        b_reject:             float = -0.5,
        v0:                   float = 0.0,
        t_max:                int   = 400,
        weak_evidence_factor: float = 0.20,
        seed:                 int   = 1188,
        max_candidates:       int   = 64,
    ):
        if sigma <= 0.0:
            raise ValueError(
                "sigma must be > 0: a noiseless accumulator is a deterministic "
                "ramp — the diffusion signature (varCE) cannot exist and the "
                "mechanism is a threshold in an accumulator costume.")
        if not (b_reject < v0 < b_accept):
            raise ValueError("bound geometry must satisfy b_reject < v0 < b_accept")

        self.g_plus               = float(g_plus)
        self.trust_asymmetry      = float(trust_asymmetry)
        self.g_minus              = float(g_plus) * float(trust_asymmetry)
        self.leak                 = float(leak)
        self.sigma                = float(sigma)
        self.b_accept             = float(b_accept)
        self.b_reject             = float(b_reject)
        self.v0                   = float(v0)
        self.t_max                = int(t_max)
        self.weak_evidence_factor = float(weak_evidence_factor)
        self.max_candidates       = int(max_candidates)

        self._rng = np.random.default_rng(seed)
        self._candidates: "OrderedDict[str, CandidateState]" = OrderedDict()

    # ------------------------------------------------------------------
    # Evidence mapping
    # ------------------------------------------------------------------

    def evidence(self, decision: str, field_alignment: float) -> float:
        """Signed per-step evidence c for one governance outcome."""
        alignment = float(np.clip(field_alignment, 0.0, 1.0))
        if decision in _CLEAN_POSITIVE:
            return alignment
        if decision in _WEAK_POSITIVE:
            return self.weak_evidence_factor * alignment
        return _NEGATIVE_EVIDENCE.get(decision, 0.0)

    def drift(self, c: float) -> float:
        """Asymmetric drift mu from signed evidence c."""
        return self.g_plus * max(c, 0.0) - self.g_minus * max(-c, 0.0)

    # ------------------------------------------------------------------
    # The accumulation step
    # ------------------------------------------------------------------

    def observe(
        self,
        source_id:       str,
        decision:        str,
        field_alignment: float,
    ) -> AccumulatorOutcome:
        """
        Advance the candidate's decision variable one step and report the
        outcome. ACCEPT does NOT reset — the manager confirms the structural
        preconditions and calls commit() (forming the bond) or hold_at_bound()
        (preconditions not yet met: V pins at the bound, the window keeps
        running, and negative evidence can still pull the candidate back
        down). REJECT_* reset the window internally.
        """
        state = self._candidates.get(source_id)
        if state is None:
            state = CandidateState(V=self.v0)
            self._candidates[source_id] = state
            self._evict_if_needed()
        else:
            self._candidates.move_to_end(source_id)

        c  = self.evidence(decision, field_alignment)
        mu = self.drift(c)

        # Euler-Maruyama, dt = 1 feedback step
        state.V += (mu - self.leak * state.V) + self.sigma * float(self._rng.standard_normal())
        state.steps += 1
        state.trace.append(round(state.V, 4))

        if state.V >= self.b_accept:
            state.V = self.b_accept           # runtime clamp — V is bounded state
            outcome = AccumulatorOutcome.ACCEPT
        elif state.V <= self.b_reject:
            state.V = self.b_reject
            outcome = AccumulatorOutcome.REJECT_ACTIVE
            self._close_window(state, outcome)
        elif state.steps >= self.t_max:
            outcome = AccumulatorOutcome.REJECT_TIMEOUT
            self._close_window(state, outcome)
        else:
            outcome = AccumulatorOutcome.NONE

        state.last_outcome = outcome.value
        return outcome

    # ------------------------------------------------------------------
    # Manager-side resolutions
    # ------------------------------------------------------------------

    def commit(self, source_id: str):
        """The manager formed the bond — retire the candidate's accumulator."""
        state = self._candidates.pop(source_id, None)
        if state is not None:
            state.outcomes[AccumulatorOutcome.ACCEPT.value] += 1
            logger.info(
                "Bond accumulator ACCEPT committed: source='%s' after %d steps "
                "(windows=%d)", source_id, state.steps, state.windows + 1)

    def hold_at_bound(self, source_id: str):
        """
        ACCEPT crossed but a structural precondition (interactions/crystals)
        is not yet met: pin V at B_accept and keep the window running.
        Evidence must be *sustained* while the footprint catches up.
        """
        state = self._candidates.get(source_id)
        if state is not None:
            state.V = self.b_accept

    def drop(self, source_id: str):
        """Forget a candidate entirely (e.g. bond formed by another path)."""
        self._candidates.pop(source_id, None)

    # ------------------------------------------------------------------
    # Introspection (observe-only; never fed back into the loop)
    # ------------------------------------------------------------------

    def state(self, source_id: str) -> Optional[dict]:
        s = self._candidates.get(source_id)
        return s.snapshot() if s is not None else None

    def trace(self, source_id: str) -> list:
        s = self._candidates.get(source_id)
        return list(s.trace) if s is not None else []

    def summary(self) -> dict:
        return {
            "candidates": {sid: s.snapshot() for sid, s in self._candidates.items()},
            "params": {
                "g_plus":          self.g_plus,
                "trust_asymmetry": self.trust_asymmetry,
                "leak":            self.leak,
                "sigma":           self.sigma,
                "b_accept":        self.b_accept,
                "b_reject":        self.b_reject,
                "v0":              self.v0,
                "t_max":           self.t_max,
            },
        }

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _close_window(self, state: CandidateState, outcome: AccumulatorOutcome):
        state.outcomes[outcome.value] += 1
        state.windows += 1
        state.V = self.v0
        state.steps = 0

    def _evict_if_needed(self):
        while len(self._candidates) > self.max_candidates:
            evicted, _ = self._candidates.popitem(last=False)
            logger.debug("Bond accumulator: evicted stale candidate '%s'", evicted)
