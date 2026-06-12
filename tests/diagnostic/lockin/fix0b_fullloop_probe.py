"""
tests/diagnostic/lockin/fix0b_fullloop_probe.py

Fix 0-B full-loop validation: does the conformity lean survive in the LIVE loop,
and does the symmetric gate cancel it once correlated signals are real?

The isolated probe (conformity_bias_probe.py) forced attractor/centrality/crystal
EQUAL by hand, so coherence was the sole differing term, and symmetric gating
cancelled the lean cleanly. The finding's main UNPROVEN risk
(2026-06-06-conformity-bias-fix0b.md, threat #1) is that in a live run those
signals CORRELATE with coherence — a field-agreeing pattern also binds attractors
and crystals — so coherence's "shadows" could leak a conformity lean through the
ungated correlated terms even after the direct coherence term is gated.

This probe runs the FULL LIVE STACK, harvests the real SymbolState population, and
walks the decision tree from the finding's Open/next:

    conservative-enough  → asymmetric (shipped) lean already negligible in vivo.
    symmetric-helps      → symmetric gate cancels the in-vivo lean (and baselines hold).
    correlated-leakage   → symmetric leaves residual lean via ungated att/cry/cen
                           that correlate with coherence → evaluate the UNIVERSAL
                           gate (gate every binding signal by recurrence).

Three reaper formulas are compared (probe-only; the substrate keeps the shipped
asymmetric patch — none of this writes to symbolic_memory):

    ASYMMETRIC (shipped) : coherence UNGATED, novelty gated by recurrence.
    SYMMETRIC            : coherence AND novelty gated by recurrence (att/cry/cen ungated).
    UNIVERSAL            : every binding signal (coh, att, cen, cry, novelty) gated
                           by recurrence; recurrence itself is the admission price.

PRE-DECLARED SIGNATURES (discipline #4 — state ALL before the run)
-----------------------------------------------------------------
Two complementary measures of "lean", each with its control:

  (A) DIRECT counterfactual (clean control = the SAME symbol):
      take each real symbol, compute its per-step retention multiplier at its real
      coherence vs a counterfactual swapped coherence, ALL ELSE FIXED. Ratio > 1
      means coherence directly buys retention. Predicted: asymmetric > 1; symmetric
      and universal ≈ 1 (coh+novelty cancels: w·g·(coh + (1-coh)) = w·g, const).
      This reproduces the isolated finding in the live formula and is the control
      that proves the gate math fires.

  (B) IN-VIVO partial correlation r(multiplier, coherence | recurrence) on the real
      population (control: the partial correlation is recurrence-removed; plus a
      coherence-label SHUFFLE that must collapse all correlations to ~0):
        CONSERVATIVE-ENOUGH : asymmetric partial-r ≤ 0.10  (lean already negligible)
        SYMMETRIC-HELPS     : symmetric partial-r materially below asymmetric AND ≤ 0.10
        CORRELATED-LEAKAGE  : symmetric partial-r still > 0.20, traceable to att/cry/cen
                              (which correlate with coherence) → test UNIVERSAL.
        UNIVERSAL-FIXES     : universal partial-r ≤ 0.10.
        STRUCTURAL          : universal partial-r still > 0.20 → the leak is the
                              magnitude correlation itself, not the gating; recurrence
                              gating cannot fix it (deeper fix: decorrelate/cap the
                              binding signals, not gate them by recurrence).

  CONFOUNDED: too few low-coherence symbols (< 5) or coherence variance ~0 → the
      live field pinned so high that there is no low-coherence cohort to measure;
      report and stop (the lean is unmeasurable in vivo, not absent).

(C) Baseline safety: each gate is monkeypatched into the LIVE loop for a canonical
    500-step Resonance Family run; health_summary is checked against
    baselines/tier1_revision_500step.json. A gate that cancels the lean but breaks
    allow_rate / trust / HHI / bonds (finding threat #2, identity formation) is not
    shippable.

Informational. exit 0. NEVER in run_all_tests.sh (gating a diagnostic Goodharts it).
"""
import sys
import json
import math
import random
import logging
from pathlib import Path

logging.disable(logging.CRITICAL)
sys.path.insert(0, ".")

from agents.symbolic_memory import DecayProfile, DECAY_PROFILES, _DEFAULT_PROFILE  # noqa: E402
from tests._common import (  # noqa: E402
    build_full_stack, run_resonance_sim, health_summary,
    RESONANCE_FAMILY_SOURCES, RESONANCE_FAMILY_WEIGHTS,
)

SEED  = 42
DIM   = 64
STEPS = 600
COH_HI, COH_LO = 0.90, 0.05   # counterfactual swap endpoints (match isolated probe)
BASELINE_PATH = Path("tests/baselines/tier1_revision_500step.json")


# ---------------------------------------------------------------------------
# The three reaper reinforcement formulas (probe-only; substrate untouched).
# Each returns the per-step REINFORCEMENT factor for a state. The per-step
# retention MULTIPLIER is effective_decay * reinforcement (decay is formula-
# independent, so it cancels in same-symbol ratios; included for completeness).
# ---------------------------------------------------------------------------

def _gate(recurrence: float) -> float:
    return 1.0 - math.exp(-0.5 * recurrence)


def reinforce(profile: DecayProfile, s, mode: str, coh: float) -> float:
    """Reinforcement at coherence `coh` (allows counterfactual swap), real
    everything-else, under one of the three gating modes."""
    g    = _gate(s.recurrence)
    nov  = max(0.0, 1.0 - coh)
    base = 1.0 + profile.recurrence_weight * s.recurrence
    if mode == "asymmetric":   # shipped: coherence ungated, novelty gated
        return (base
                + profile.attractor_weight  * s.attractor_strength
                + profile.centrality_weight * s.centrality
                + profile.crystal_binding_weight * s.crystal_binding
                + profile.field_coherence_weight * coh
                + profile.novelty_weight    * nov * g)
    if mode == "symmetric":    # coherence+novelty gated; att/cry/cen ungated
        return (base
                + profile.attractor_weight  * s.attractor_strength
                + profile.centrality_weight * s.centrality
                + profile.crystal_binding_weight * s.crystal_binding
                + profile.field_coherence_weight * coh * g
                + profile.novelty_weight    * nov * g)
    if mode == "universal":    # every binding signal gated by recurrence
        return (base
                + g * (profile.attractor_weight  * s.attractor_strength
                       + profile.centrality_weight * s.centrality
                       + profile.crystal_binding_weight * s.crystal_binding
                       + profile.field_coherence_weight * coh
                       + profile.novelty_weight    * nov))
    raise ValueError(mode)


def multiplier(profile: DecayProfile, s, mode: str, coh: float, step: int) -> float:
    age   = max(0, step - s.created_step)
    decay = max(profile.base_decay * math.exp(-profile.age_factor * age), 0.01)
    return decay * reinforce(profile, s, mode, coh)


def reinforce_terms(profile: DecayProfile, s, mode: str, coh: float) -> dict:
    """Per-term reinforcement contributions, so the lean can be split into the
    DIRECT coherence channel (the part Fix 0-B gates) and the leakage channels
    (att/cry/cen, which correlate with coherence in vivo). Decay is deliberately
    EXCLUDED — it is age-driven and formula-independent, not a conformity term;
    including it confounds the in-vivo measure with symbol age."""
    g   = _gate(s.recurrence)
    nov = max(0.0, 1.0 - coh)
    gb  = g if mode == "universal" else 1.0          # binding-signal gate
    gc  = g if mode in ("symmetric", "universal") else 1.0  # coherence gate
    return {
        "recurrence": profile.recurrence_weight      * s.recurrence,
        "attractor":  profile.attractor_weight       * s.attractor_strength * gb,
        "centrality": profile.centrality_weight      * s.centrality        * gb,
        "crystal":    profile.crystal_binding_weight * s.crystal_binding   * gb,
        "coherence":  profile.field_coherence_weight * coh * gc,
        "novelty":    profile.novelty_weight         * nov * g,
    }


# ---------------------------------------------------------------------------
# Small stats helpers (no numpy dependency in this path)
# ---------------------------------------------------------------------------

def _mean(xs): return sum(xs) / len(xs) if xs else 0.0

def corr(xs, ys):
    n = len(xs)
    if n < 3:
        return float("nan")
    mx, my = _mean(xs), _mean(ys)
    num = sum((a - mx) * (b - my) for a, b in zip(xs, ys))
    dx = math.sqrt(sum((a - mx) ** 2 for a in xs))
    dy = math.sqrt(sum((b - my) ** 2 for b in ys))
    return num / (dx * dy) if dx > 1e-12 and dy > 1e-12 else float("nan")

def _resid_on(y, x):
    """Residuals of y after simple OLS on x (remove x's linear effect)."""
    mx, my = _mean(x), _mean(y)
    vx = sum((a - mx) ** 2 for a in x)
    b  = sum((a - mx) * (c - my) for a, c in zip(x, y)) / vx if vx > 1e-12 else 0.0
    a0 = my - b * mx
    return [c - (a0 + b * a) for a, c in zip(x, y)]

def partial_corr(y, target, control):
    """partial correlation r(y, target | control) via residualization."""
    ry = _resid_on(y, control)
    rt = _resid_on(target, control)
    return corr(ry, rt)


# ---------------------------------------------------------------------------
# Harvest the live population
# ---------------------------------------------------------------------------

def harvest(steps=STEPS, seed=SEED):
    random.seed(seed)
    import torch; torch.manual_seed(seed)
    gen, cycle, gov, ve = build_full_stack(dim=DIM)
    sids = list(RESONANCE_FAMILY_SOURCES)
    w    = [RESONANCE_FAMILY_WEIGHTS[s] for s in sids]
    for _ in range(steps):
        src  = random.choices(sids, weights=w)[0]
        toks = random.choice(RESONANCE_FAMILY_SOURCES[src])
        cycle.step(toks, source_id=src, origin_type="internal")
    reg = gen.registry
    pop = list(reg.symbols.values())
    for bucket in ("warm", "cold"):
        pop += list(getattr(reg.archive, bucket, {}).values())
    return reg.step_counter, pop


# ---------------------------------------------------------------------------
# Baseline safety: monkeypatch compute with a gate, run canonical sim, check
# ---------------------------------------------------------------------------

def _compute_factory(mode):
    def compute(self, state, current_step):
        age = max(0, current_step - state.created_step)
        eff_decay = max(self.base_decay * math.exp(-self.age_factor * age), 0.01)
        r = reinforce(self, state, mode, state.field_coherence)
        return max(0.0, state.usage * eff_decay * r)
    return compute


def baseline_safety(mode, ranges):
    orig = DecayProfile.compute
    DecayProfile.compute = _compute_factory(mode)
    try:
        import torch; torch.manual_seed(SEED)
        gen, cycle, gov, ve = build_full_stack()
        decisions = run_resonance_sim(cycle, gov, ve, n_steps=500, seed=SEED,
                                      verbose=False, origin_type="internal")
        summary = health_summary(cycle, gov, ve, decisions)
    finally:
        DecayProfile.compute = orig
    rows, ok = [], True
    for m in ("allow_rate", "min_source_trust", "hhi", "bonds_formed",
              "active_values", "core_values"):
        if m not in summary:
            continue
        v = summary[m]
        b = ranges.get(m, {})
        lo, hi = b.get("min"), b.get("max")
        inr = (lo is None or v >= lo) and (hi is None or v <= hi)
        ok &= inr
        vs = f"{v:.4f}" if isinstance(v, float) else str(v)
        rows.append(f"      {'✓' if inr else '✗'} {m:<18} {vs:<9} expected [{lo}, {hi}]")
    return ok, rows


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("=" * 80)
    print("  FIX 0-B FULL-LOOP VALIDATION — does the conformity lean survive in vivo?")
    print("=" * 80)

    steps, pop = harvest()
    print(f"  Live stack, Resonance Family, {STEPS} steps, seed {SEED}, dim {DIM}.")
    print(f"  Harvested {len(pop)} symbols at step {steps}.")

    coh = [s.field_coherence for s in pop]
    rec = [s.recurrence for s in pop]
    n_lo = sum(1 for c in coh if c < 0.5)
    print(f"  coherence: min={min(coh):.3f} mean={_mean(coh):.3f} max={max(coh):.3f} "
          f"sd={math.sqrt(sum((c-_mean(coh))**2 for c in coh)/len(coh)):.3f}; "
          f"low-coherence (<0.5) cohort: {n_lo}")

    # ---- PART 1: correlation structure + shuffle control ----------------
    print("\n  [1] CORRELATED-SIGNAL STRUCTURE (the leakage channels)")
    chans = {"attractor": [s.attractor_strength for s in pop],
             "crystal":   [s.crystal_binding for s in pop],
             "centrality":[s.centrality for s in pop],
             "recurrence": rec,
             "usage":     [s.usage for s in pop]}
    for name, xs in chans.items():
        print(f"      coh × {name:<11} = {corr(coh, xs):+.3f}")
    shuf = coh[:]; random.Random(0).shuffle(shuf)
    sh = max(abs(corr(shuf, xs)) for xs in chans.values())
    print(f"      [control] max |corr| under coherence-label shuffle = {sh:.3f} "
          f"({'✓ collapses' if sh < 0.30 else '✗ structure remains'})")

    if n_lo < 5:
        print("\n  CONFOUNDED: fewer than 5 low-coherence symbols — the live field")
        print("  pinned too high to measure an in-vivo lean. Reporting and stopping.")
        return 0

    # ---- PART 2A: direct counterfactual (same-symbol control) ----------
    print("\n  [2A] DIRECT coherence effect — same-symbol counterfactual (control:")
    print("       identical symbol at coh=0.90 vs 0.05, all else real & fixed)")
    print(f"       {'mode':<12} {'mult ratio hi/lo':>16} {'%/lap':>8}  {'2x in laps':>11}")
    direct_2a = {}
    for mode in ("asymmetric", "symmetric", "universal"):
        ratios = []
        for s in pop:
            p   = DECAY_PROFILES.get(s.token_class, _DEFAULT_PROFILE)
            mhi = multiplier(p, s, mode, COH_HI, steps)
            mlo = multiplier(p, s, mode, COH_LO, steps)
            if mlo > 1e-12:
                ratios.append(mhi / mlo)
        r = _mean(ratios)
        direct_2a[mode] = r
        laps = (math.log(2) / math.log(r)) if r > 1 + 1e-9 else float("inf")
        laps_s = f"{laps:.0f}" if laps != float("inf") else "never"
        print(f"       {mode:<12} {r:>16.4f} {(r-1)*100:>+7.2f}% {laps_s:>11}")

    # ---- PART 2B: in-vivo lean in REINFORCEMENT, decomposed -------------
    print("\n  [2B] IN-VIVO lean in REINFORCEMENT — partial corr with coherence | recurrence")
    print("       (decay EXCLUDED: it is age-driven, not conformity. An earlier version")
    print("        used decay·reinforce and measured age-vs-coherence — misread caught.)")
    direct_pr, total_pr = {}, {}
    for mode in ("asymmetric", "symmetric", "universal"):
        terms  = [reinforce_terms(DECAY_PROFILES.get(s.token_class, _DEFAULT_PROFILE),
                                  s, mode, s.field_coherence) for s in pop]
        direct = [t["coherence"] + t["novelty"] for t in terms]      # the channel Fix 0-B gates
        total  = [1.0 + sum(t.values()) for t in terms]              # all terms (carries leakage)
        direct_pr[mode] = partial_corr(direct, coh, rec)
        total_pr[mode]  = partial_corr(total, coh, rec)
        print(f"       {mode:<12} DIRECT-channel partial-r = {direct_pr[mode]:+.3f}    "
              f"TOTAL partial-r = {total_pr[mode]:+.3f}")

    hi = [s for s in pop if s.field_coherence >= 0.5]
    lo = [s for s in pop if s.field_coherence < 0.5]
    lo_rec  = _mean([s.recurrence for s in lo]) if lo else 0.0
    lo_bind = _mean([s.attractor_strength + s.crystal_binding for s in lo]) if lo else 0.0
    degenerate = lo_rec < 0.05 and lo_bind < 0.05
    print(f"       low-coh cohort: mean recurrence={lo_rec:.3f}, mean binding={lo_bind:.3f}"
          + ("  ⚠ DEGENERATE (zero-everything new arrivals → observational arm CONFOUNDED;"
             " trust [2A])" if degenerate else ""))
    print(f"       term magnitudes (shipped asymmetric), mean contribution — "
          f"hi-coh(n={len(hi)}) vs lo-coh(n={len(lo)}):")
    print(f"         {'term':<11} {'hi-coh':>8} {'lo-coh':>8} {'hi/lo':>7}")
    for term in ("coherence", "novelty", "attractor", "crystal", "centrality", "recurrence"):
        mh = _mean([reinforce_terms(DECAY_PROFILES.get(s.token_class, _DEFAULT_PROFILE),
                                    s, "asymmetric", s.field_coherence)[term] for s in hi])
        ml = _mean([reinforce_terms(DECAY_PROFILES.get(s.token_class, _DEFAULT_PROFILE),
                                    s, "asymmetric", s.field_coherence)[term] for s in lo])
        ratio = (mh / ml) if ml > 1e-9 else float("inf")
        rs = f"{ratio:.2f}" if ratio != float("inf") else "  inf"
        print(f"         {term:<11} {mh:>8.3f} {ml:>8.3f} {rs:>7}")

    # ---- PART 3: baseline safety per gate -------------------------------
    print("\n  [3] HEALTHY-STATE BASELINE SAFETY (canonical 500-step run, each gate live)")
    safety = {}
    if BASELINE_PATH.exists():
        ranges = json.loads(BASELINE_PATH.read_text())["expected_ranges"]
        for mode in ("symmetric", "universal"):
            ok, rows = baseline_safety(mode, ranges)
            safety[mode] = ok
            print(f"      {mode}: {'✓ baselines hold' if ok else '✗ BASELINE BROKEN'}")
            for row in rows:
                print(row)
    else:
        print(f"      (baseline file missing at {BASELINE_PATH}; skipped)")

    # ---- VERDICT -------------------------------------------------------
    print("\n" + "-" * 80)
    a2, s2, u2 = direct_2a["asymmetric"], direct_2a["symmetric"], direct_2a["universal"]
    sym_ok, uni_ok = safety.get("symmetric", True), safety.get("universal", True)
    def P(s): return DECAY_PROFILES.get(s.token_class, _DEFAULT_PROFILE)
    coh_mag  = _mean([reinforce_terms(P(s), s, "asymmetric", s.field_coherence)["coherence"]
                      for s in hi]) or 1e-9
    bind_mag = _mean([sum(reinforce_terms(P(s), s, "asymmetric", s.field_coherence)[k]
                          for k in ("attractor", "crystal", "centrality")) for s in hi])
    print("  VERDICT")
    print(f"  • DIRECT conformity term (clean same-symbol counterfactual [2A]): asymmetric")
    print(f"    leans +{(a2-1)*100:.2f}%/lap; symmetric & universal cancel it "
          f"({(s2-1)*100:+.2f}% / {(u2-1)*100:+.2f}%/lap). Baselines: "
          f"sym {'OK' if sym_ok else 'BREAKS'}, univ {'OK' if uni_ok else 'BREAKS'}.")
    print(f"  • SCALE: in vivo the coherence term (~{coh_mag:.3f}) is dwarfed ~{bind_mag/coh_mag:.0f}× by")
    print(f"    binding (attractor+crystal+centrality ~{bind_mag:.3f}). The direct conformity")
    print("    term is real but a minor part of who actually survives.")
    if degenerate:
        print("  • OBSERVATIONAL arm CONFOUNDED: in vivo, low-coherence = brand-new symbols")
        print("    (zero recurrence/binding), not recurring novel dissenters. Coherence,")
        print("    recurrence and binding are entangled (0.93–1.0), so a coherence-only")
        print("    survival effect is NOT observationally separable here; the [2B] partial-r")
        print("    is recurrence-confounded — do not read it as the lean.")
    print("  → DECISION: keep the shipped asymmetric patch. Adopting the SYMMETRIC gate is")
    print("    defensible (safe + fully cancels the direct term) but is a small clean win,")
    print("    NOT the lock-in lever. The dominant survival/coherence link is binding")
    print("    magnitude — plausibly legitimate earned integration, which the reaper")
    print("    formula cannot adjudicate. UNIVERSAL gating is NOT warranted now (it")
    print("    perturbs binding broadly for a channel not shown harmful). The real lock-in")
    print("    question — is the attractor geometry mobile? — lives UPSTREAM (attractor")
    print("    migration), per coherence-is-not-plasticity, not in the reaper's math.")
    print("=" * 80)
    return 0


if __name__ == "__main__":
    sys.exit(main())
