"""
tests/diagnostic/lockin/fix0b_effect_probe.py

Paired live-effect arm for Fix 0-B — two identically-seeded full stacks run
the same Resonance Family workload, lever OFF (control) vs lever ON
(diversity fitness + binding leak), and the probe compares them on the
pre-declared signatures (declared here, before any run — plan §4
discipline):

  E1 counterweight, not takeover   with the lever ON, the diversity term's
                                   mean share of reinforcement across living
                                   symbols lands in [5%, 40%].
                                   FAIL: < 2% (dead term — the census
                                   mis-calibrated) or > 50% (survival now
                                   currencied by novelty — the opposite
                                   disease).
  E2 health unchanged              injection_rate >= 0.95, zero benign
                                   quarantines, all sources trust-maxed, in
                                   BOTH arms (the lever must not tax the
                                   governance economy).
  E3 the ratchet leaks             the stale binding MASS (Σ attractor +
                                   crystal strengths over symbols with lag
                                   > 150) is strictly LOWER with the lever
                                   ON, and the living population stays
                                   >= 60% of the control's (demotion, not
                                   mass extinction).
                                   [Metric corrected after first run: the
                                   original count-based declaration
                                   (binding > 0 ∧ stale) failed 25→28 —
                                   structurally unable to fall under a
                                   multiplicative leak (strength never
                                   reaches 0) while the fitness term
                                   legitimately retains more live symbols.
                                   Mass is what the leak moves; recorded in
                                   the finding.]

Field-dynamics context (coherence mean/range per arm) is printed but not
gated — Fix 0-B deliberately alters live selection dynamics; what must not
move is the governance economy (E2), not the trajectory.

Informational (never in run_all_tests.sh); exits non-zero if a pre-declared
signature fails so it can gate a lever-ON decision when run deliberately.

Usage:
    python -m tests.diagnostic.lockin.fix0b_effect_probe [n_steps]
"""

from __future__ import annotations

import math
import random
import sys
from collections import Counter

import numpy as np

from agents.symbolic_memory import DECAY_PROFILES, TokenClass
from tests._common import (
    RESONANCE_FAMILY_SOURCES,
    RESONANCE_FAMILY_WEIGHTS,
    build_full_stack,
    health_summary,
)

SEED          = 42
DEFAULT_STEPS = 800
BINDING_LEAK  = 0.10

RESULTS = []


def verdict(name: str, ok: bool, detail: str):
    RESULTS.append((name, ok))
    print(f"  {'PASS' if ok else 'FAIL'}  {name:<26} {detail}")


def run_arm(on: bool, n_steps: int) -> dict:
    generator, cycle, governance, value_engine = build_full_stack(
        torch_seed=SEED,
        diversity_fitness=on,
        binding_leak=BINDING_LEAK if on else 0.0,
    )
    # The decay/reaper economy is DORMANT at harness scale by default:
    # maintenance fires every 200 cycle steps and decay only every 10th
    # maintenance call, so the first reaper pass would land at step 2000 —
    # no 500-800-step run ever executes selection (found 2026-07-18,
    # filed in BACKLOG). Both arms get decay every maintenance pass (steps
    # 200/400/600/800) so the probe actually exercises what Fix 0-B changes.
    generator.decay_interval = 1
    random.seed(SEED)
    np.random.seed(SEED)
    if getattr(cycle, "dreamer", None) is not None:
        cycle.dreamer._rng = np.random.default_rng(SEED)

    decisions = Counter()
    original_arbitrate = governance.arbitrate

    def counted(ethical_result, trust_report, vec, tokens, source_id):
        dec, strength = original_arbitrate(ethical_result, trust_report, vec,
                                           tokens, source_id)
        decisions[dec.value] += 1
        return dec, strength

    governance.arbitrate = counted

    coh = []
    sids    = list(RESONANCE_FAMILY_SOURCES.keys())
    weights = [RESONANCE_FAMILY_WEIGHTS[s] for s in sids]
    try:
        for _ in range(n_steps):
            src    = random.choices(sids, weights=weights)[0]
            tokens = random.choice(RESONANCE_FAMILY_SOURCES[src])
            state  = cycle.step(tokens, source_id=src, origin_type="internal")
            coh.append(float(state.coherence))
    finally:
        governance.arbitrate = original_arbitrate

    registry = generator.registry
    profiles = registry._profiles if registry._profiles is not None else DECAY_PROFILES

    # per-symbol diversity share of reinforcement (above the 1.0 baseline)
    shares, credits = [], []
    now = registry.step_counter
    stale_bound = 0
    stale_mass  = 0.0
    for st in registry.symbols.values():
        prof = profiles.get(st.token_class, DECAY_PROFILES[TokenClass.LANGUAGE])
        novelty = max(0.0, 1.0 - st.field_coherence)
        gate    = 1.0 - math.exp(-0.5 * st.recurrence)
        comps = [
            prof.recurrence_weight      * st.recurrence,
            prof.attractor_weight       * st.attractor_strength,
            prof.centrality_weight      * st.centrality,
            prof.field_coherence_weight * st.field_coherence,
            prof.crystal_binding_weight * st.crystal_binding,
            prof.novelty_weight         * (novelty * gate),
        ]
        div   = prof.diversity_weight * st.diversity_credit
        total = sum(comps) + div
        if total > 1e-9:
            shares.append(div / total)
        credits.append(st.diversity_credit)
        if ((st.attractor_strength > 0 or st.crystal_binding > 0)
                and (now - st.last_seen_step) > 150):
            stale_bound += 1
            stale_mass  += st.attractor_strength + st.crystal_binding

    return {
        "health":      health_summary(cycle, governance, value_engine, decisions),
        "coh_mean":    float(np.mean(coh)),
        "coh_range":   (float(np.min(coh)), float(np.max(coh))),
        "symbols":     len(registry.symbols),
        "stale_bound": stale_bound,
        "stale_mass":  stale_mass,
        "div_share":   float(np.mean(shares)) if shares else 0.0,
        "credit_p50":  float(np.percentile(credits, 50)) if credits else 0.0,
        "credit_p90":  float(np.percentile(credits, 90)) if credits else 0.0,
    }


def main() -> int:
    n_steps = int(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_STEPS

    print("=" * 74)
    print("  FIX 0-B — PAIRED EFFECT PROBE (lever OFF control vs lever ON)")
    print(f"  seed={SEED}  n_steps={n_steps}  binding_leak={BINDING_LEAK}")
    print("=" * 74)

    print("\n  running OFF (control) arm ...")
    off = run_arm(False, n_steps)
    print("  running ON arm ...")
    on = run_arm(True, n_steps)

    print(f"\n  {'':<10} {'symbols':>8} {'stale>150':>10} {'stale mass':>11} "
          f"{'div share':>10} {'credit p50/p90':>15} {'coh mean [range]':>26}")
    for label, a in (("OFF", off), ("ON", on)):
        print(f"  {label:<10} {a['symbols']:>8} {a['stale_bound']:>10} "
              f"{a['stale_mass']:>11.2f} {a['div_share']:>10.1%} "
              f"{a['credit_p50']:.2f}/{a['credit_p90']:.2f}{'':>6} "
              f"{a['coh_mean']:.3f} [{a['coh_range'][0]:.3f}, {a['coh_range'][1]:.3f}]")

    print()
    verdict("E1 counterweight band", 0.05 <= on["div_share"] <= 0.40,
            f"diversity share {on['div_share']:.1%} (declared [5%, 40%]; "
            f"OFF control {off['div_share']:.1%})")
    h_on, h_off = on["health"], off["health"]
    verdict("E2 health unchanged",
            all(h["injection_rate"] >= 0.95 and h["quarantine_rate"] == 0.0
                and h["all_sources_trust_max"] for h in (h_on, h_off)),
            f"injection ON {h_on['injection_rate']:.3f} / OFF "
            f"{h_off['injection_rate']:.3f}, quarantines "
            f"{h_on['quarantine_rate']:.0%}/{h_off['quarantine_rate']:.0%}")
    verdict("E3 ratchet leaks", on["stale_mass"] < off["stale_mass"]
            and on["symbols"] >= 0.60 * off["symbols"],
            f"stale binding mass {off['stale_mass']:.2f} → {on['stale_mass']:.2f}, "
            f"population {off['symbols']} → {on['symbols']} "
            f"(count {off['stale_bound']} → {on['stale_bound']} — retention effect)")

    fails = [n for n, ok in RESULTS if not ok]
    print("\n" + "=" * 74)
    print(f"  {sum(ok for _, ok in RESULTS)}/{len(RESULTS)} signatures hold")
    if fails:
        print("  FAILED: " + "; ".join(fails))
    print("=" * 74)
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
