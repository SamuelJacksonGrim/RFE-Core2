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

import numpy as np

# v0.3: the ⊘ coherence axis was redesigned from marginal coherence_contribution
# (structurally ≤ 0 in a saturated field → dead-at-zero) to absolute field-alignment
# of the EXPRESSED vector (max(0, cos(generate(token), field))). A thinness-metric
# definition change → spec bump, per the findings discipline.
SPEC_VERSION = "v0.3"

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
                 baseline_profiles: Optional[Dict] = None, field=None):
        self.value_engine      = value_engine
        self.registry          = registry
        self.bond_manager      = bond_manager
        self.sacred_check      = sacred_check
        self.baseline_profiles = baseline_profiles or {}
        # ResonanceField handle for the absolute-alignment coherence read. When
        # None, the coherence axis degrades to neutral+flagged (no marginal-delta
        # fallback — that signal is dead by construction in a saturated field).
        self.field             = field

    # ---- per-dimension support reads (all read-only) ------------------------

    def _complement_support(self, value, active_ids):
        comps = value.counter_values
        if not comps:
            return 0.5, True          # unknown complement structure → neutral, flagged
        present = sum(1 for c in comps if c in active_ids)
        return present / len(comps), False

    def _coherence_support(self, value):
        """Absolute field-alignment — how well the value sits with the field NOW:
        max(0, cos(EXPRESSED vector, current field state)). Replaces the marginal
        `coherence_contribution / _COHERENCE_REF` signal, which is structurally ≤ 0
        in a saturated field (injecting into a near-maxed field only dilutes it), so
        it read 0 for every value.

        The expressed vector — `generator.generate([symbolic_core])` — is what
        actually enters the field (embedding → generate → … → inject); the raw
        embedding row sits in a different, near-orthogonal space and gives a dead,
        compressed read. Coherence is a field *effect*: support is the value's
        expressed *direction* relative to the field, which does not saturate even
        when the field's coherence *magnitude* is maxed. Neutral+flagged when the
        field or generator is unavailable (never the dead marginal fallback).

        Read-only and off the hot path: one `generate` per value on demand. A broad
        guard returns neutral rather than ever propagating into the loop (firewall)."""
        if self.field is None:
            return 0.5, True
        try:
            vec = np.asarray(self.value_engine.generator.generate([value.symbolic_core]),
                             dtype=float).ravel()
        except Exception:                       # read-only: never propagate to the loop
            return 0.5, True
        f = np.asarray(getattr(self.field, "field", self.field), dtype=float).ravel()
        nv = float(np.linalg.norm(vec)); nf = float(np.linalg.norm(f))
        if nv < 1e-8 or nf < 1e-8 or vec.shape != f.shape:
            return 0.5, True
        cos = float(np.dot(vec, f) / (nv * nf))
        return max(0.0, cos), False

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
            cc, gap_cc = self._coherence_support(v)
            sd, gap_sd = self._source_support(v)
            ab, gap_ab = self._binding_support(v)
            tv = ThinnessVector(cd, cc, sd, ab)
            coverage_gap = gap_cd or gap_cc or gap_sd or gap_ab or not self.baseline_profiles

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


class IntegrityDecayConsumer:
    """The first *consumer* of ⊘'s advice — advisory-into-decay (spec §4, the
    deferred-no-longer step). ⊘ stays read-only and non-binding; THIS object does
    the writing, and it is the one place authority lives.

    Per cycle, `apply()` reads the Witness-Reaper's advisories and, for each
    **non-sacred** value standing thin, pulls its strength a `rate` fraction of the
    way toward a convergent floor (see below):

        strength ← strength − rate · (strength − floor)      (floor ≤ strength)

    This is the answer to "nothing ever gets used": ⊘'s name-the-pathology read now
    has a downstream effect on value strength.

    **The floor is what makes it converge, not collapse.** ⊘'s `honest_level` is
    `strength × support` (Build C) — always *below* current strength, so naively
    pulling toward it every cycle has no fixed point but zero (over-demotion
    collapse, a pre-declared failure signature — observed in vivo at `rate=0.05`,
    250 cycles: mean 2.23 → 0.43). The consumer owns the convergence policy (the
    reaper just reads): it remembers the **peak honest level ever advised** for each
    value and never pulls below it. A value inflated past its support relaxes to the
    most-generous honest reading it ever earned and *holds* — demotion with a fixed
    point, not a slide to zero. (Authority lives in the consumer, by design; this is
    where that authority is exercised responsibly.)

    It is still:
      - **Conservative coupling**, not binding: a fractional pull toward a remembered
        honest floor, never a hard set, never below 0.
      - **Sacred-safe**: `sacred_blocked` advisories are skipped (Law 3 — ⊘ reads
        them so they are not a blind spot, but the consumer must not act).
      - **6c-clean**: it never feeds the λ-ledger; the λ-reinforcement `f` must not
        read this path. Disjoint by construction (this module imports no ledger).
      - **Opt-in**: attached via `ValueEmergenceEngine.set_integrity_consumer`;
        unattached, the system is observe-only and Tier 3 is byte-identical.

    Demotion is reported, never silent (the guardrail against silently dissolving
    CORE values): `apply()` returns the list of (symbol, before, after) touched and
    accumulates counters surfaced by `snapshot()`.

    Selectivity (`named_only`, default True): ⊘'s aggregate support reading is, in
    short/low-dim runs, dragged down for *every* value by the cc-axis confound
    (`coherence_contribution` ≈ 0 below the 5.0 CORE ref — Build C finding). Acting
    on that universal thinness over-demotes the whole field (observed). So by
    default the consumer acts ONLY on values carrying a **named pathology region**
    (Drift / Dissolution / Fragmentation) — the validated, live-triggerable part of
    ⊘ — leaving merely-unnamed-thin values alone. `named_only=False` restores acting
    on all sub-health-floor advisories (the aggressive mode; documented to collapse
    under the current confounded reading — keep it for the §4 discriminator, not for
    production).
    """

    def __init__(self, reaper: "WitnessReaper", value_engine, rate: float = 0.05,
                 named_only: bool = True):
        self.reaper       = reaper
        self.value_engine = value_engine
        self.rate         = max(0.0, min(1.0, float(rate)))
        self.named_only   = bool(named_only)
        self.applied_count   = 0   # cycles where ≥1 demotion happened
        self.demotions_total = 0   # total values pulled
        self.sacred_skipped  = 0   # sacred advisories refused
        self.skipped_unnamed = 0   # thin-but-unnamed advisories left alone (named_only)
        self.last_touched: List[tuple] = []
        # Per-value convergent floor: the peak honest level ⊘ has ever advised for
        # this value. The pull never goes below it → fixed point, no collapse.
        self._floor: Dict[str, float] = {}

    def apply(self) -> List[tuple]:
        """Run one consumption pass. Returns [(symbol, before, after), ...]."""
        advisories = self.reaper.read()
        touched: List[tuple] = []
        for a in advisories:
            if a.sacred_blocked:
                self.sacred_skipped += 1
                continue
            if self.named_only and not a.pathologies:
                self.skipped_unnamed += 1
                continue
            value = self.value_engine.values.get(a.value_id)
            if value is None or value.promoted_to_sacred:
                continue
            before = float(value.strength)
            # Convergent floor = peak honest level ever advised for this value.
            floor = max(self._floor.get(a.value_id, 0.0), float(a.honest_level))
            self._floor[a.value_id] = floor
            target = min(floor, before)                   # never raise
            after  = before - self.rate * (before - target)
            after  = max(0.0, after)
            if after < before - 1e-9:
                value.strength = float(after)
                self.value_engine._update_polarity(value)
                touched.append((a.symbol, round(before, 4), round(after, 4)))
                self.demotions_total += 1
        if touched:
            self.applied_count += 1
        self.last_touched = touched
        return touched

    def snapshot(self) -> dict:
        return {
            "spec":            SPEC_VERSION,
            "rate":            self.rate,
            "named_only":      self.named_only,
            "cycles_applied":  self.applied_count,
            "demotions_total": self.demotions_total,
            "sacred_skipped":  self.sacred_skipped,
            "skipped_unnamed": self.skipped_unnamed,
            "last_touched":    self.last_touched,
            "binding":         False,   # a conservative pull, not a warden
        }
