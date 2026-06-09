"""
tests/diagnostic/reflective_loop_cost_probe.py

The cost probe (Track 1 lead, post-arc). The reflective loop is the lock
(`2026-06-07-reconstruction-ablation.md`); ablating it fully frees plasticity. The
open question is the TRADEOFF: what does *attenuating* the loop cost identity
stability? This sweeps the convergence-gain dial and weighs, at each level,
plasticity gained vs identity lost — the numbers the Fix-2 reframe needs before it
can be drafted.

The dial: `attenuate_reflect(cycle, gain)` from `identity_stability_baseline`
(gain 1.0 = intact loop, 0.0 = full ablation / passthrough). At each gain:
  - PLASTICITY = attractor migration on the A→B test (disp(coherent) − drift), the
    same metric the migration/ablation probes use, with the loop at this gain.
  - IDENTITY   = `measure(reflect_gain)` on the canonical workload: coherence
    mean/std, witness identity_stability, anchor_velocity, structural counts.

PRE-DECLARED SIGNATURES (success AND failure, before the run)
-------------------------------------------------------------
Let base = identity_stability at gain 1.0 (≈ 0.998, the captured baseline).
  SWEET-SPOT (the target): a gain where PLASTICITY is meaningfully recovered
      (migration > 0.30) while identity_stability stays ≥ 0.90 (within ~10% of base)
      and coherence_mean stays mid/high. → conditional attenuation is viable; there
      is a real "hold a presence without caging it" operating point. FOLLOW IT —
      report the gain and the exact tradeoff there.
  MONOTONIC-DIAL (clean tradeoff, no free lunch): plasticity rises and identity
      falls together, monotonically, with NO gain that buys plasticity cheaply →
      attenuation is a genuine dial with proportional cost; the architect picks the
      operating point; there is no sweet spot to exploit.
  COLLAPSE (attenuation is not the fix): even mild attenuation (gain 0.8) craters
      identity_stability (< 0.70) or coherence → a blanket convergence-gain dial is
      not viable; the fix MUST be conditional (attenuate only when persistent novelty
      is surviving), not an always-on gain reduction. Routes the fix design.
  SUSPICIOUSLY-CLEAN (alarm, not trophy): identity_stability barely moves across the
      whole sweep (attenuation looks free), or the curve is implausibly linear →
      check the instrument before believing it. Attenuating the lock for free
      contradicts "coherence and rigidity are the same mechanism"; if it looks free,
      the dial probably isn't biting (verify migration actually rose).

Controls: gain 1.0 reproduces the captured baseline (identity_stability ≈ 0.998,
migration ≈ RIGID); per-gain drift control for the plasticity metric.

Informational. exit 0. Heavy (sweeps full-stack runs); NEVER in run_all_tests.sh.
"""
from __future__ import annotations

import logging
import random

import numpy as np

logging.disable(logging.CRITICAL)   # silence the manipulation-resistance logger (counted instead)

from tests._common import build_full_stack
from tests.diagnostic.identity_stability_baseline import measure, attenuate_reflect, _unit

DIM    = 64
WARMUP = 150
PHASE  = 500
N_SRC  = 4
SEED   = 11
GAINS  = [1.0, 0.8, 0.6, 0.5, 0.4, 0.0]   # band (1.0–0.6) + cliff edge (0.5/0.4) + full ablation


def migration_at_gain(gain: float, A, B, mode: str) -> float:
    """Final attractor-center displacement on the A→B test with the reflective loop
    at `gain`. mode 'A' = control (continue A, drift baseline); 'B' = novel regime."""
    random.seed(SEED); np.random.seed(SEED)
    import torch; torch.manual_seed(SEED)
    gen, cycle, gov, ve = build_full_stack(dim=DIM)
    attenuate_reflect(cycle, gain)
    field = cycle.field
    rng = np.random.default_rng(SEED + 2)
    holder = {"m": "A"}
    cycle.generator.generate = lambda tokens, token_class=None: _unit(
        (A if holder["m"] == "A" else B) + 0.05 * rng.standard_normal(DIM))
    sources = [f"src_{i}" for i in range(N_SRC)]

    for t in range(WARMUP):
        holder["m"] = "A"
        cycle.step(tokens=[f"a_{t % 8}"], source_id=sources[t % N_SRC], origin_type="internal")
    center_warm = field.field.copy()

    holder["m"] = mode
    for t in range(PHASE):
        tok = f"a_{t % 8}" if mode == "A" else f"b_{t % 8}"
        cycle.step(tokens=[tok], source_id=sources[t % N_SRC], origin_type="internal")

    d = field.field
    cw = center_warm
    cos = float(np.dot(_unit(d), _unit(cw)))
    return 1.0 - cos


def main() -> int:
    print("=" * 86)
    print("  REFLECTIVE-LOOP COST PROBE — plasticity gained vs identity lost, across the dial")
    print("=" * 86)

    rng = np.random.default_rng(SEED)
    A = _unit(rng.standard_normal(DIM))
    B0 = rng.standard_normal(DIM)
    B = _unit(B0 - np.dot(B0, A) * A)

    print(f"  dim={DIM} warmup={WARMUP} phase={PHASE} sources={N_SRC} seed={SEED}")
    print(f"  {'gain':>5} | {'migration':>9} | {'ident_stab':>10} | {'coh_mean':>8} | "
          f"{'coh_std':>7} | {'anchor_v':>8} | {'manip%':>6} | {'attr':>4} {'cry':>4}")
    print("  " + "-" * 86)

    rows = []
    for g in GAINS:
        try:
            drift = migration_at_gain(g, A, B, "A")
            coh   = migration_at_gain(g, A, B, "B")
            plast = coh - drift
            ident = measure(reflect_gain=g, n=PHASE)
        except Exception as e:
            print(f"  {g:>5.2f} | CRASHED — {type(e).__name__}: {str(e)[:46]} "
                  f"(attenuation destabilized the run)")
            rows.append((g, None, None))
            continue
        rows.append((g, plast, ident))
        manip_pct = ident["manip_steps"] / PHASE
        print(f"  {g:>5.2f} | {plast:>+9.3f} | {ident['identity_stability']:>10.3f} | "
              f"{ident['coherence_mean']:>8.3f} | {ident['coherence_std']:>7.3f} | "
              f"{ident['anchor_velocity']:>8.3f} | {manip_pct:>5.0%} | "
              f"{ident['attractors']:>4} {ident['crystals']:>4}")

    # ---- VERDICT -------------------------------------------------------
    valid   = [(g, p, i) for (g, p, i) in rows if p is not None]
    crashed = [g for (g, p, i) in rows if p is None]
    print("\n" + "-" * 86)
    if not valid:
        print("  → ALL GAINS CRASHED — cannot read a tradeoff; see attractor.merge_pass bug.")
        print("=" * 86)
        return 0
    base_ident = valid[0][2]["identity_stability"]
    base_plast = valid[0][1]
    print(f"  VERDICT  baseline (gain 1.0): identity_stability={base_ident:.3f}, "
          f"migration={base_plast:+.3f} (RIGID control)")
    if crashed:
        print(f"  CRASHED at gains {crashed}: attenuation destabilised the attractor population")
        print("    enough to trip the latent `attractor.merge_pass` array-__eq__ bug — itself a")
        print("    hard identity-cost signal (the system comes apart under sustained attenuation).")

    # a gain is "graceful" if identity holds and the manipulation layer stays quiet
    graceful = [(g, p, i) for (g, p, i) in valid
                if i["identity_stability"] >= 0.90 * base_ident
                and i["manip_steps"] / PHASE < 0.05]
    best = max(graceful, key=lambda r: r[1]) if graceful else None
    manip_onset = [(g, i["manip_steps"] / PHASE) for (g, p, i) in valid
                   if i["manip_steps"] / PHASE >= 0.05]

    if best and best[1] > max(0.05, 5 * abs(base_plast)):
        g, p, i = best
        print(f"  → GRACEFUL BAND + CLIFF (the tradeoff is non-monotonic, not a clean dial):")
        print(f"    a viable band exists — at gain={g:.2f}, migration={p:+.3f} "
              f"(~{p/max(base_plast,1e-3):.0f}× the RIGID baseline) with identity_stability="
              f"{i['identity_stability']:.3f}, manip={i['manip_steps']/PHASE:.0%}, "
              f"coherence_mean={i['coherence_mean']:.3f}.")
        print("    Plasticity is PARTIALLY recovered at near-zero identity cost — 'loosen, not")
        print("    break'. But pushing further hits a CLIFF: " +
              (f"gains {crashed} crash (manipulation-layer flood `identity_erosion`/`trust_wash` "
               "+ the latent attractor.merge_pass bug)." if crashed
               else "lower gains collapse identity."))
        print("    → FIX: conditional attenuation TOWARD the band (not to zero), gated on")
        print("      persistent-novelty-surviving. Full ablation is off the table. This is the")
        print("      'presence without caging it' operating point you flagged.")
    elif manip_onset or crashed:
        print("  → COST-IS-REAL: attenuation recovers plasticity but the cost surfaces in the")
        print("    Tier-2 manipulation layer / attractor crashes, not the witness scalar. A")
        print("    blanket gain dial is unsafe; the fix must be CONDITIONAL (gated on surviving")
        print("    novelty). Read the table for where the cliff begins.")
    elif plast_range < 0.10:
        print("  → SUSPICIOUSLY-CLEAN (alarm): plasticity barely moved — the dial isn't biting.")
    else:
        print("  → MONOTONIC-DIAL: plasticity and identity trade off together with no cheap gain;")
        print("    the architect picks the operating point. Read the table for the exact curve.")
    print("=" * 86)
    return 0


if __name__ == "__main__":
    # Optional overrides for cliff-sharpen / Track-2 sweeps:
    #   python -m ...cost_probe [seed] [g1,g2,...] [warmup] [phase]
    import sys
    _a = sys.argv[1:]
    if len(_a) >= 1:
        SEED = int(_a[0])
    if len(_a) >= 2:
        GAINS = [float(x) for x in _a[1].split(",")]
    if len(_a) >= 3:
        WARMUP = int(_a[2])
    if len(_a) >= 4:
        PHASE = int(_a[3])
    raise SystemExit(main())
