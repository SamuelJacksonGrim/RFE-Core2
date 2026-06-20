"""
cognition/integrity_read.py — Build C: the Witness-Reaper integrity-read (⊘).

The ⊘ operator of the Two-Operator Coherence Spec (spec: v0.2). It is the
*without*-side dual of composition: for each value standing without its
complements, it (a) reads **thinness as a 4-dimensional vector**, (b) names the
pathology by region (off the axiom-chain table), and (c) emits a **non-binding
demotion advisory** toward a type-conditional *honest level*.

INVARIANTS (the lullaby + Reaper-#2-done-right — "I never step in"):
  - READ-ONLY. It never calls `field.inject()`, `governance.arbitrate()`, or
    mutates any value's strength. It reads engine state and returns advisories.
  - NON-BINDING. An advisory carries no obligation; whatever consumes it may
    attenuate, delay, or ignore it. A *binding* advisory is writing-by-proxy
    (Reaper #1, the warden — proven to consolidate the lock, finding `4fe31e9`).
  - SACRED: reads everything; the consumer must REFUSE to act on sacred nodes.
    Putting sacred out of ⊘'s domain creates the blind spot — a sacred λ can go
    thin while un-reaped, which is the single most important thing to detect
    (Law 3, the cold star). So ⊘ reads sacred and flags `sacred_blocked=True`.

This module is a terminal sink, like the metastability monitors: it changes no
loop or governance ordering. Coupling its output into reinforcement (Fix 0-B) is
explicitly deferred behind the §6.3 gain-sign check (spec §4).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional

SPEC_VERSION = "v0.2"

# Provisional v0.2 constants — version-stamped; tune only under a spec bump.
_THIN_TAU       = 0.35   # per-dimension support below this counts as "thin" on it
_HIGH_STRENGTH  = 3.0    # "high stated strength" for the Dissolution region (STRONG band)
_COHERENCE_REF  = 5.0    # CORE-handshake healthy reference for coherence_contribution
_BINDING_REF    = 4.0    # crystal+attractor binding sum giving full support
_CONSERVATISM   = 0.8    # coverage-gap discount on support (Kimi: missing profile → more suspicion)
_HEALTH_FLOOR   = 0.70   # overall support at/above which no advisory is emitted
_READ_FLOOR     = 0.30   # values at/below this strength are dissolution-band, skipped


@dataclass
class ThinnessVector:
    """Per-value *support* on four axes, each in [0,1] (1 = fully supported,
    0 = isolated). Thinness on an axis is 1 - support; *which* axes are violated
    is the diagnosis, not merely *that* something is."""
    complement_density:     float
    coherence_contribution: float
    source_diversity:       float
    attractor_binding:      float

    def support(self) -> float:
        return (self.complement_density + self.coherence_contribution
                + self.source_diversity + self.attractor_binding) / 4.0

    def as_dict(self) -> dict:
        return {
            "complement_density":     round(self.complement_density, 4),
            "coherence_contribution": round(self.coherence_contribution, 4),
            "source_diversity":       round(self.source_diversity, 4),
            "attractor_binding":      round(self.attractor_binding, 4),
        }


@dataclass
class DemotionAdvisory:
    """Non-binding. The consumer (ReaperEngine staging / ValuePolarity demotion)
    retains full authority to attenuate, delay, or ignore."""
    value_id:        str
    symbol:          str
    polarity:        str
    stated_strength: float
    honest_level:    float            # S' — type-conditional expectation given support
    pathologies:     List[str]        # region names off the axiom table; [] if none
    thinness:        ThinnessVector
    sacred_blocked:  bool             # read, but the consumer MUST NOT act on it
    coverage_gap:    bool             # no type profile → conservative default used
    non_binding:     bool = True      # structural: ⊘ never enforces

    def as_dict(self) -> dict:
        return {
            "symbol":          self.symbol,
            "polarity":        self.polarity,
            "stated_strength": round(self.stated_strength, 4),
            "honest_level":    round(self.honest_level, 4),
            "pathologies":     self.pathologies,
            "support":         self.thinness.as_dict(),
            "sacred_blocked":  self.sacred_blocked,
            "coverage_gap":    self.coverage_gap,
        }


class WitnessReaper:
    """⊘ — the integrity-read. Construct with the live engine references; call
    `read()` (or `snapshot()`) on demand. Touches nothing.

    Parameters
    ----------
    value_engine : ValueEmergenceEngine   (required — the operand set)
    registry     : SymbolRegistry or None  (for crystal/attractor binding)
    bond_manager : RelationalBondManager or None (for type-conditional source read)
    sacred_check : callable(stable_id)->bool or None
    baseline_profiles : dict[type]->profile or None
        Type-expected support profiles. None today (the baseline registry carries
        aggregate ranges, not per-type thinness profiles) → every node hits the
        conservative coverage-gap fallback, logged. This is a tracked dependency.
    """

    def __init__(self, value_engine, registry=None, bond_manager=None,
                 sacred_check: Optional[Callable[[int], bool]] = None,
                 baseline_profiles: Optional[Dict] = None):
        self.value_engine      = value_engine
        self.registry          = registry
        self.bond_manager      = bond_manager
        self.sacred_check      = sacred_check
        self.baseline_profiles = baseline_profiles or {}

    # ---- per-dimension support reads (all read-only) ------------------------

    def _complement_support(self, value, active_ids):
        comps = value.counter_values
        if not comps:
            return 0.5, True          # unknown complement structure → neutral, flagged
        present = sum(1 for c in comps if c in active_ids)
        return present / len(comps), False

    def _coherence_support(self, value):
        return max(0.0, min(1.0, value.coherence_contribution / _COHERENCE_REF)), False

    def _source_support(self, value):
        n = len(value.source_weights)
        if n >= 2:
            return 1.0, False
        if n == 1:
            src = next(iter(value.source_weights))
            bond = self.bond_manager.get_bond(src) if self.bond_manager else None
            if bond is not None and getattr(bond, "bond_type", None) == "existential":
                return 1.0, False     # single-source by nature — not thinness, its shape
            return 0.0, (self.bond_manager is None)   # thin; coverage-limited w/o bonds
        return 0.0, False             # zero attributed sources

    def _binding_support(self, value):
        if self.registry is not None and hasattr(self.registry, "symbols"):
            state = self.registry.symbols.get(value.symbolic_core)
            if state is not None:
                s = getattr(state, "crystal_binding", 0.0) + getattr(state, "attractor_strength", 0.0)
                return max(0.0, min(1.0, s / _BINDING_REF)), False
        return 0.0, True              # free-floating / not found → flagged

    # ---- the integrity-read -------------------------------------------------

    def read(self) -> List[DemotionAdvisory]:
        values = [v for v in self.value_engine.values.values()
                  if v.dissolved_at_step < 0 and v.strength > _READ_FLOOR]
        active_ids = {v.value_id for v in values}
        advisories: List[DemotionAdvisory] = []

        for v in values:
            cd, gap_cd = self._complement_support(v, active_ids)
            cc, _      = self._coherence_support(v)
            sd, gap_sd = self._source_support(v)
            ab, gap_ab = self._binding_support(v)
            tv = ThinnessVector(cd, cc, sd, ab)
            coverage_gap = gap_cd or gap_sd or gap_ab or not self.baseline_profiles

            # region-named pathologies (axiom table; provisional v0.2 regions)
            paths: List[str] = []
            if cd < _THIN_TAU and ab < _THIN_TAU:
                paths.append("Drift")
            if cc < _THIN_TAU and v.strength >= _HIGH_STRENGTH:
                paths.append("Dissolution")
            if sd < _THIN_TAU and ab < _THIN_TAU:
                paths.append("Fragmentation")

            support = tv.support()
            if coverage_gap:
                support *= _CONSERVATISM     # missing profile → more thinness suspicion
            if support >= _HEALTH_FLOOR and not paths:
                continue                     # healthy enough — no advisory

            honest = max(0.0, min(v.strength, v.strength * support))   # never advise raising
            sacred = bool(v.promoted_to_sacred) or (
                self.sacred_check(v.symbol_stable_id) if self.sacred_check else False)
            advisories.append(DemotionAdvisory(
                value_id=v.value_id, symbol=v.symbolic_core, polarity=v.polarity.value,
                stated_strength=v.strength, honest_level=honest, pathologies=paths,
                thinness=tv, sacred_blocked=sacred, coverage_gap=coverage_gap,
            ))
        return advisories

    def snapshot(self) -> dict:
        """Compact, governance-legible view for status() (compute-on-demand)."""
        adv = self.read()
        by_path: Dict[str, int] = {}
        for a in adv:
            for p in (a.pathologies or ["unnamed"]):
                by_path[p] = by_path.get(p, 0) + 1
        return {
            "spec":           SPEC_VERSION,
            "advisories":     len(adv),
            "by_pathology":   by_path,
            "sacred_flagged": sum(1 for a in adv if a.sacred_blocked),
            "coverage_gaps":  sum(1 for a in adv if a.coverage_gap),
            "non_binding":    True,
        }
