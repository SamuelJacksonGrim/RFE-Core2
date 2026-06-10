"""
tests/diagnostic/fix2_live_token_probe.py

THE LIVE-GENERATOR TEST. Everything Fix-2-side so far (governor validation, the cost
probe, the trigger calibration's novelty/attack arms) used a MOCK generator emitting
clean deterministic A/B vectors. This probe runs the REAL generator and injects real
token vocabularies of our own choosing, to answer the questions the mocks cannot:

  Q1. Does real token novelty ever cross the Fix-2 trigger (gnov > 0.65, >=2 sources)?
      The dropout/dim audit says real novelty is *marginal* at dim 64 (deterministic
      generator pairwise cos ~0.79) but that near-orthogonal regimes EXIST at dim 256
      (cos down to +0.018). So: dim 64 should leave Fix 2 DORMANT on real tokens (which
      would *confirm* the 2026-06-08 deferral is correct at dim 64); dim 256 should let
      real novelty cross and Fix 2 engage.
  Q2. When Fix 2 engages on real tokens (dim 256), does it recover migration like it did
      on the mock? (mock: +0.006 -> +0.166, ~28x)
  Q3. THE ONE I MOST WANT: is the ~14% manipulation-layer wake we saw at gain 0.5 an
      ARTIFACT of the mock's PERFECT orthogonality? Real token regimes are far less
      orthogonal, so the loosened real expression may not read as an attack -> manip
      could be near zero. If so, Fix 2 is cleanly viable on the real system at dim 256.
  Q4. What target gain is the operating point on real tokens? (sweep 0.5/0.6/0.7)

Design notes:
  - eval() mode for generator AND rec_attn: deterministic, so gnov reflects real token
    structure, not dropout. (The as-deployed system runs TRAIN — dropout would inflate
    benign gnov toward ~0.39; T=0.65 still clears it. The eval read is the clean one and
    is the right measurement per the epistemic discipline §4; train is the deployment
    caveat, noted, not the scientific condition.)
  - Real generator (NOT mocked). generator.generate is only WRAPPED to capture gnov +
    drive the governor; the reflect blend applies the governor gain. Nothing is faked.
  - VOCAB_A / VOCAB_B are two disjoint real-word sets. Because the generator is an
    untrained hash-embedding encoder, the A/B separation is RANK-bounded, not semantic —
    so word choice is irrelevant and dim is the clean lever. We inject 3-token samples
    per step (multi-source) to give the encoder real sequences to pool.

PRE-DECLARED SIGNATURES
-----------------------
Per dim, measure regime separation sep=cos(A_dir,B_dir), then OFF vs ON:
  dim 64  EXPECT: sep > 0.70 (collinear) -> steady gnov < 0.65 -> loosen ~0 -> Fix 2
          DORMANT -> migration(ON) ~= migration(OFF) (RIGID). Confirms: real token
          novelty does not trigger Fix 2 at dim 64; the deferral is correct there.
  dim 256 EXPECT: sep < 0.70 -> gnov can exceed 0.65 -> Fix 2 ENGAGES (loosen > 0) ->
          migration(ON) > migration(OFF). manip% under ON = the real-token cost.
          HYPOTHESIS: manip% < the mock's 14% (less-orthogonal regime).
Target sweep (dim 256, ON, target in 0.5/0.6/0.7): report migration + manip% each; the
  operating point is the highest plasticity at manip% == 0 (or lowest manip).

Informational. exit 0. NEVER in run_all_tests.sh.
"""
from __future__ import annotations

import logging
import random

import numpy as np

logging.disable(logging.CRITICAL)

from tests._common import build_full_stack
from cognition.reflective_loop import ReflectionResult
from cognition.reflective_loop_governor import ReflectiveLoopGovernor

WARMUP = 100
PHASE = 250
N_SRC = 4
SEED = 11
DIMS = [64, 256]

VOCAB_A = ["resonance", "witness", "anchor", "coherence",
           "field", "bond", "crystal", "lantern"]
VOCAB_B = ["glacier", "tariff", "mitochondria", "saxophone",
           "asphalt", "quark", "plankton", "ledger"]


def _unit(v):
    v = np.asarray(v, dtype=float)
    n = np.linalg.norm(v)
    return v / n if n > 1e-12 else v


def _cos(a, b):
    return float(np.dot(_unit(a), _unit(b)))


def _eval_stack(dim):
    random.seed(SEED); np.random.seed(SEED)
    import torch; torch.manual_seed(SEED)
    gen, cycle, govn, ve = build_full_stack(dim=dim)
    gen.eval(); cycle.rec_attn.eval()      # deterministic: gnov = real token structure
    return gen, cycle


def _regime_dirs(gen):
    """Deterministic mean direction of each vocabulary, and within-vocab tightness."""
    A_vecs = [_unit(gen.generate([w])) for w in VOCAB_A]
    B_vecs = [_unit(gen.generate([w])) for w in VOCAB_B]
    A_dir = _unit(np.mean(A_vecs, axis=0))
    B_dir = _unit(np.mean(B_vecs, axis=0))
    def tight(vs):
        cs = [_cos(vs[i], vs[j]) for i in range(len(vs)) for j in range(i + 1, len(vs))]
        return float(np.mean(cs))
    return A_dir, B_dir, _cos(A_dir, B_dir), tight(A_vecs), tight(B_vecs)


def _attach(cycle, gov, A_dir, B_dir, enabled):
    """Wrap the REAL generator for gnov + governor drive, and the reflect for the gain
    blend. Per-step manip flag (rolled, not sticky)."""
    ctrl = {"gn_done": True, "manip_cur": False, "manip_prev": False,
            "manip_steps": 0, "src": None, "rec": [], "inj_n": 0, "inj_cB": 0.0,
            "inj_on": False}
    orig_gen     = cycle.generator.generate
    orig_reflect = cycle.reflector.reflect
    orig_manip   = cycle.governance.handle_manipulation_signals
    orig_inject  = cycle.field.inject

    def gen(*a, **k):
        out = orig_gen(*a, **k)
        if not ctrl["gn_done"]:
            ctrl["gn_done"] = True
            gn = 1.0 - abs(_cos(out, cycle.field.field))
            gov.observe(gn, ctrl["src"])
            g = gov.update(manip_active=ctrl["manip_prev"],
                           attractor_count=len(cycle.attractor.centers))
            ctrl["rec"].append((gn, ctrl["src"], g, gov.loosening))
        return out

    def reflect(vec, **k):
        r = orig_reflect(vec, **k)
        if not enabled or gov.gain >= 1.0:
            return r
        g = gov.gain
        bl = _unit((1.0 - g) * np.asarray(vec, dtype=float)
                   + g * np.asarray(r.vector, dtype=float))
        return ReflectionResult(vector=bl.astype(np.float32), passes=r.passes,
                                converged=r.converged, final_coherence=r.final_coherence,
                                delta_trace=r.delta_trace)

    def manip(signals, *a, **k):
        ctrl["manip_cur"] = True; ctrl["manip_steps"] += 1
        return orig_manip(signals, *a, **k)

    def inject(vec, strength=1.0):
        if ctrl["inj_on"]:
            ctrl["inj_n"] += 1; ctrl["inj_cB"] += _cos(vec, B_dir)
        return orig_inject(vec, strength)

    cycle.generator.generate = gen
    if enabled:
        cycle.reflector.reflect = reflect
    cycle.governance.handle_manipulation_signals = manip
    cycle.field.inject = inject

    def reset(src):
        ctrl["manip_prev"] = ctrl["manip_cur"]; ctrl["manip_cur"] = False
        ctrl["gn_done"] = False; ctrl["src"] = src
    ctrl["reset"] = reset
    return ctrl


def run_phase(dim, mode, enabled, A_dir, B_dir, target=0.50):
    """warmup on VOCAB_A then PHASE on (A if mode=='A' else B). Real generator, eval.
    Returns dict: disp (field move vs warmup center), gnov_steady, loosen_rate, manip_pct,
    landed_cosB."""
    gen, cycle = _eval_stack(dim)
    gov = ReflectiveLoopGovernor(gain_target=target, gain_floor=min(0.45, target))
    ctrl = _attach(cycle, gov, A_dir, B_dir, enabled)
    src_pool = [f"src_{i}" for i in range(N_SRC)]

    for t in range(WARMUP):
        ctrl["reset"](src_pool[t % N_SRC])
        cycle.step(random.sample(VOCAB_A, 3), source_id=src_pool[t % N_SRC],
                   origin_type="internal")
    center_warm = cycle.field.field.copy()

    ctrl["inj_on"] = True
    for t in range(PHASE):
        ctrl["reset"](src_pool[t % N_SRC])
        toks = random.sample(VOCAB_A if mode == "A" else VOCAB_B, 3)
        cycle.step(toks, source_id=src_pool[t % N_SRC], origin_type="internal")

    rec = ctrl["rec"][-PHASE:]
    return {
        "disp":        1.0 - _cos(cycle.field.field, center_warm),
        "gnov_steady": float(np.mean([r[0] for r in rec])) if rec else 0.0,
        "loosen_rate": float(np.mean([1.0 if r[3] else 0.0 for r in rec])) if rec else 0.0,
        "manip_pct":   ctrl["manip_steps"] / max(1, WARMUP + PHASE),
        "landed_cosB": ctrl["inj_cB"] / max(1, ctrl["inj_n"]),
    }


def main() -> int:
    print("#" * 92)
    print("  FIX-2 ON THE LIVE GENERATOR — real tokens, real encoder. Does real novelty")
    print("  trigger it, recover migration, and what does it cost? (eval/deterministic)")
    print("#" * 92)

    summary = {}
    for dim in DIMS:
        gen, _ = _eval_stack(dim)
        A_dir, B_dir, sep, tA, tB = _regime_dirs(gen)
        print("\n" + "=" * 92)
        print(f"  DIM {dim}   regime separation cos(A,B) = {sep:+.3f}   "
              f"(within-A tightness {tA:+.3f}, within-B {tB:+.3f})")
        confound = sep > 0.70
        if confound:
            print(f"  -> sep > 0.70: VOCAB_A and VOCAB_B are nearly collinear at dim {dim}; "
                  "real token regimes")
            print("     are too similar to constitute distinct regimes (rank-bound). "
                  "Fix 2 should stay dormant.")

        a_ctrl = run_phase(dim, "A", enabled=False, A_dir=A_dir, B_dir=B_dir)
        off_b  = run_phase(dim, "B", enabled=False, A_dir=A_dir, B_dir=B_dir)
        on_b   = run_phase(dim, "B", enabled=True,  A_dir=A_dir, B_dir=B_dir, target=0.50)
        mig_off = off_b["disp"] - a_ctrl["disp"]
        mig_on  = on_b["disp"]  - a_ctrl["disp"]

        print(f"\n  {'':<16}{'gnov':>7}{'loosen%':>9}{'migration':>11}{'landed cosB':>13}{'manip%':>8}")
        print(f"  {'OFF (gain 1.0)':<16}{off_b['gnov_steady']:>7.3f}{0.0:>9.0%}"
              f"{mig_off:>+11.3f}{off_b['landed_cosB']:>+13.3f}{off_b['manip_pct']:>8.0%}")
        print(f"  {'ON  (target.50)':<16}{on_b['gnov_steady']:>7.3f}{on_b['loosen_rate']:>9.0%}"
              f"{mig_on:>+11.3f}{on_b['landed_cosB']:>+13.3f}{on_b['manip_pct']:>8.0%}")

        engaged = on_b["loosen_rate"] > 0.05
        summary[dim] = {"sep": sep, "engaged": engaged, "mig_off": mig_off, "mig_on": mig_on,
                        "manip_on": on_b["manip_pct"], "gnov_on": on_b["gnov_steady"],
                        "loosen": on_b["loosen_rate"]}

        if dim == 256 and engaged:
            print("\n  TARGET-GAIN SWEEP (dim 256, ON, real tokens):")
            print(f"  {'target':>8}{'loosen%':>9}{'migration':>11}{'landed cosB':>13}{'manip%':>8}")
            sweep = {}
            for tg in (0.50, 0.60, 0.70):
                r = run_phase(dim, "B", enabled=True, A_dir=A_dir, B_dir=B_dir, target=tg)
                m = r["disp"] - a_ctrl["disp"]
                sweep[tg] = (m, r["manip_pct"])
                print(f"  {tg:>8.2f}{r['loosen_rate']:>9.0%}{m:>+11.3f}"
                      f"{r['landed_cosB']:>+13.3f}{r['manip_pct']:>8.0%}")
            summary[dim]["sweep"] = sweep

    print("\n" + "#" * 92)
    print("  SUMMARY")
    print("#" * 92)
    for dim, s in summary.items():
        verdict = ("ENGAGED — recovers plasticity" if s["engaged"]
                   else "DORMANT — real novelty sub-threshold (deferral correct at this dim)")
        print(f"  dim {dim:<4} sep={s['sep']:+.3f}  gnov_on={s['gnov_on']:.3f}  "
              f"loosen={s['loosen']:.0%}  mig OFF{s['mig_off']:+.3f}->ON{s['mig_on']:+.3f}  "
              f"manip_on={s['manip_on']:.0%}  | {verdict}")
    print("#" * 92)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
