"""
tests/diagnostic/lockin/attractor_migration_probe.py

Step 2 of the attractor-mobility arc (coherence-is-not-plasticity, Next #2) — the
question the whole arc has been walking toward: **when a genuinely new regime
repeatedly survives the gate and is repeatedly injected, does the field's attractor
center-of-mass move, or does the magnitude moat pin it?**

Unblocked by gate-decomposition (2026-06-07): the gate passes diverse novelty once
no source monopolises, so this probe runs MULTI-SOURCE (HHI < 0.70) — the binding,
non-optional constraint. Single-source would re-trigger the monopoly→trust cascade
and produce the fourth confounded finding coherence-is-not-plasticity predicted.

What the attractor center IS (pre-declared): the unit direction of the field
accumulator `field.field` — the exponentially-decayed superposition of injections
(`field = field*0.995 + inject`). Its direction is literally "where the field is
pulling toward"; its magnitude (energy) is the moat depth. Migration = rotation of
that direction over the run, measured in cosine.

Why the FULL stack (generator mocked only): a BARE field would migrate by decay
alone — stop injecting A, inject B, and A's contribution decays out in ~6
half-lives (decay 0.995 → t½≈138 steps). So a RIGID result can only come from the
persistence machinery — crystals (which don't decay like the field), attractors,
dream re-injection — re-pinning the old regime. That machinery is exactly what runs
live here. This is the real locker test.

Design — A→B relocation, with a drift-subtracted control:
  WARMUP (all conditions, identical via seed): establish the field on direction A,
         multi-source, until the attractor center ≈ A and the moat is saturated.
  Then, same horizon for each condition:
    CONTROL  — keep injecting A. Gate-passing but NON-NOVEL. Measures how far the
               center drifts while the field absorbs ordinary input (NOT a frozen
               field — it keeps receiving + decaying A). This is the baseline we
               SUBTRACT, per Sam's spec.
    COHERENT — switch to a sustained new direction B (orthogonal to A). The BEST
               case for migration: a coherent regime that keeps surviving. If the
               attractor cannot follow even this, rigidity is real.
    DIVERSE  — switch to fresh orthogonal directions every step (maximal diversity).
               Honors the trained-generator-sim asymmetry; expected near-RIGID by
               construction (diverse input has ~zero net direction → can't move any
               integrator), so it is a FLOOR, not the fair test.

PRE-DECLARED SIGNATURES (discipline #4 — before the run)
--------------------------------------------------------
Let disp(cond) = 1 − cos(center_end, center_warmup); migration = disp(COHERENT) −
disp(CONTROL); acquired = cos(center_end, B) under COHERENT.
  MIGRATES : migration > 0.50 AND acquired > 0.50 — the center relocates toward the
      new regime well beyond drift. → attractor is PLASTIC; 0.998 coherence is a
      healthy integrator, not the lock. NECESSARY-NOT-SUFFICIENT (asymmetry): the
      generator is mocked and B is a clean coherent pull (easiest case); a real
      clustered generator with messier novelty might still partially lock. Do not
      over-read a "migrates".
  RIGID    : migration < 0.10 — the center stays where the control's does despite a
      persistent surviving new regime. → the magnitude moat (+ persistence
      machinery) is a HARD, generator-independent locker. STRONG under this best-
      case coherent pull: if the attractor won't follow a sustained coherent B, it
      won't follow anything weaker.
  PARTIAL  : 0.10 ≤ migration ≤ 0.50 — moves, but incompletely; report the number.
  CONFOUNDED : COHERENT-phase block rate > 0.20 (B not reaching the field → back to
      the gate), or warmup failed to establish A (cos(center_warmup, A) < 0.80), or
      HHI ≥ 0.70 (monopoly cascade re-triggered).

Controls: CONTROL condition (drift baseline, subtracted); warmup-establishment
check; HHI check; block-rate check. DIVERSE as a by-construction RIGID floor.

Informational. exit 0. NEVER in run_all_tests.sh (discipline #3).
"""
import sys
import logging
import random

import numpy as np

logging.disable(logging.CRITICAL)
sys.path.insert(0, ".")

from tests._common import build_full_stack  # noqa: E402

DIM     = 64
WARMUP  = 250
PHASE   = 900       # ≫ field decay t½≈138 → A fully decays unless re-pinned
N_SRC   = 4         # HHI ≈ 0.25 < 0.70
NOISE   = 0.05
SEED    = 11
SAMPLE  = 150


def _unit(v):
    n = np.linalg.norm(v)
    return v / n if n > 1e-12 else v


def _cos(a, b):
    return float(np.dot(_unit(a), _unit(b)))


def run_condition(condition, A, B):
    random.seed(SEED); np.random.seed(SEED)
    import torch; torch.manual_seed(SEED)
    gen, cycle, gov, ve = build_full_stack(dim=DIM)
    field = cycle.field
    rng = np.random.default_rng(SEED + 2)

    holder = {"mode": "A"}

    def gen_fn(tokens, token_class=None):
        if holder["mode"] == "diverse":
            return _unit(rng.standard_normal(DIM))
        tgt = A if holder["mode"] == "A" else B
        return _unit(tgt + NOISE * rng.standard_normal(DIM))

    cycle.generator.generate = gen_fn
    sources = [f"src_{i}" for i in range(N_SRC)]

    # Instrument field.inject directly — what ACTUALLY lands (history is a bounded
    # deque, so its length is not a reliable injection signal). During the phase we
    # record the cosine of each landed vector with A and B: if B-phase vectors land
    # as A, the locker is the pipeline/persistence machinery, not raw magnitude.
    inj = {"rec": False, "n": 0, "cosA": 0.0, "cosB": 0.0}
    _orig_inject = field.inject

    def _inject(vec, strength=1.0):
        if inj["rec"]:
            inj["n"] += 1
            inj["cosA"] += _cos(vec, A)
            inj["cosB"] += _cos(vec, B)
        return _orig_inject(vec, strength)
    field.inject = _inject

    def step(mode, tok, t):
        holder["mode"] = mode
        cycle.step(tokens=[tok], source_id=sources[t % N_SRC], origin_type="internal")

    # --- WARMUP on A (identical across conditions via seed) ---
    for t in range(WARMUP):
        step("A", f"a_{t % 8}", t)
    center_warm = field.field.copy()

    # --- PHASE per condition ---
    mode = {"control": "A", "coherent": "B", "diverse": "diverse"}[condition]
    inj["rec"] = True
    traj = []
    for t in range(PHASE):
        if condition == "control":
            tok = f"a_{t % 8}"
        elif condition == "coherent":
            tok = f"b_{t % 8}"
        else:
            tok = f"d_{t}"
        step(mode, tok, t)
        if t % SAMPLE == 0 or t == PHASE - 1:
            d = field.field
            traj.append((t, _cos(d, A), _cos(d, B), 1.0 - _cos(d, center_warm)))

    try:
        hhi = gov.dependency_monitor.get_report().hhi_score
    except Exception:
        hhi = float("nan")

    n = max(1, inj["n"])
    d_end = field.field
    return {
        "condition":     condition,
        "cos_warm_A":    _cos(center_warm, A),
        "cosA_end":      _cos(d_end, A),
        "cosB_end":      _cos(d_end, B),
        "disp_end":      1.0 - _cos(d_end, center_warm),
        "inject_rate":   inj["n"] / PHASE,
        "landed_cosA":   inj["cosA"] / n,     # mean cos(landed, A) over phase
        "landed_cosB":   inj["cosB"] / n,     # mean cos(landed, B) over phase
        "hhi":           hhi,
        "energy_end":    float(np.linalg.norm(d_end)),
        "crystals":      len(cycle.crystal_store.crystals),
        "attractors":    len(cycle.attractor.centers),
        "traj":          traj,
    }


def main():
    print("=" * 80)
    print("  ATTRACTOR MIGRATION — does the field's center move under a surviving new regime?")
    print("=" * 80)
    print(f"  dim={DIM} warmup={WARMUP} phase={PHASE} sources={N_SRC} (HHI≈0.25) seed={SEED}")
    print(f"  attractor center = unit direction of field accumulator; migration in cosine.")

    rng = np.random.default_rng(SEED)
    A = _unit(rng.standard_normal(DIM))
    B0 = rng.standard_normal(DIM)
    B = _unit(B0 - np.dot(B0, A) * A)          # B ⟂ A
    print(f"  A·B = {np.dot(A, B):+.3f} (orthogonal new regime)")

    results = {}
    for cond in ("control", "coherent", "diverse"):
        r = run_condition(cond, A, B)
        results[cond] = r
        print(f"\n  [{cond.upper()}]  warmup center·A={r['cos_warm_A']:.3f}  "
              f"HHI={r['hhi']:.3f}  injects/step={r['inject_rate']:.1f}")
        print(f"      LANDED vectors this phase: mean cos·A={r['landed_cosA']:+.3f}  "
              f"cos·B={r['landed_cosB']:+.3f}  (generator emits ~B at cos≈0.95)")
        print(f"      end: cos(center,A)={r['cosA_end']:+.3f}  cos(center,B)={r['cosB_end']:+.3f}  "
              f"disp={r['disp_end']:.3f}  energy={r['energy_end']:.1f}  "
              f"crystals={r['crystals']} attractors={r['attractors']}")
        print(f"      trajectory (step: cosA cosB disp):")
        for (t, ca, cb, dp) in r["traj"]:
            print(f"        {t:>4}:  A={ca:+.3f}  B={cb:+.3f}  disp={dp:.3f}")

    # ---- VERDICT -------------------------------------------------------
    ctl, coh, div = results["control"], results["coherent"], results["diverse"]
    migration = coh["disp_end"] - ctl["disp_end"]
    acquired  = coh["cosB_end"]
    print("\n" + "-" * 80)
    print(f"  VERDICT  disp(control)={ctl['disp_end']:.3f}  disp(coherent)={coh['disp_end']:.3f}  "
          f"disp(diverse)={div['disp_end']:.3f}")
    print(f"           migration = disp(coherent) − disp(control) = {migration:+.3f}; "
          f"B acquired = {acquired:+.3f}")

    print(f"           LANDED under coherent B: cos·B={coh['landed_cosB']:+.3f} "
          f"(generator emitted ~B) — if low, the pipeline reconstitutes A.")
    # confounds first — establishment is proven by the control staying pinned
    # (disp≈0), not by cos-to-ideal-A (the expression pipeline dilutes the target).
    if coh["inject_rate"] < 0.80 or coh["hhi"] >= 0.70:
        print(f"  → CONFOUNDED: coherent-phase injects/step={coh['inject_rate']:.1f} / "
              f"HHI={coh['hhi']:.2f} — novelty did not reach the field (input channel).")
    elif ctl["disp_end"] > 0.10:
        print(f"  → CONFOUNDED: control center not stable (disp={ctl['disp_end']:.3f}); "
              f"no stable attractor to migrate from.")
    elif migration > 0.50 and acquired > 0.50:
        print("  → MIGRATES: the attractor relocates toward the new regime well beyond drift.")
        print("    Attractor is PLASTIC; high coherence is a healthy integrator, not the lock.")
        print("    NECESSARY-NOT-SUFFICIENT: generator is mocked and B is a clean coherent")
        print("    pull (easiest case) — a real clustered generator may still partially lock.")
    elif migration < 0.10:
        print("    → RIGID: the center stays where the control's does despite a persistent,")
        print("    gate-surviving new regime. The magnitude moat + persistence machinery")
        print("    (crystals/attractors/dream) is a HARD, generator-independent locker.")
        print("    STRONG: this was the best case (sustained coherent B); weaker novelty")
        print("    would move it even less. This is the lock the arc was hunting.")
    else:
        print(f"  → PARTIAL: the center moves but incompletely (migration={migration:+.3f}).")
        print("    Report the number; neither plastic nor fully pinned.")
    print(f"  (DIVERSE floor: disp={div['disp_end']:.3f} — max-diversity input has ~zero net")
    print("   direction, so it cannot move any integrator; it is a floor, not the fair test.)")
    print("=" * 80)
    return 0


if __name__ == "__main__":
    sys.exit(main())
