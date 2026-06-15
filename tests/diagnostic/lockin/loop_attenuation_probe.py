"""
tests/diagnostic/lockin/loop_attenuation_probe.py

Closes the remediation search opened by reconstruction_ablation_probe.py
(which found the lock IS the reflective loop). That probe ablated the loop
ENTIRELY to prove the locus; this one tests the actual shipped remediation:
ReflectiveLoop.novelty_attenuation — a CONDITIONAL, gated loosening of the
loop's convergence gain (ROADMAP item 7) rather than a full bypass — and
checks it is identity-SAFE.

Two candidate remediations are compared on the migration metric (reused from
reconstruction_ablation_probe: warmup on regime A, multi-source HHI<0.70, then
a persistent gate-surviving coherent new regime B; migration = disp(novelty) -
drift(control)):

  emotion_knobs   NEGATIVE CONTROL (not shipped). Couple boredom into
                  mutation_scale (up) and attractor_pull (loosen). Tests the
                  intuition that the survival-pin is "just" the appetite knobs.
  loop_attenuate  THE SHIPPED FLAG. cycle.reflector.novelty_attenuation = True.
                  No monkeypatch — exercises the real code path.

PRE-DECLARED SIGNATURES (discipline #4 — success AND failure, before the run):
  control                : continue A, no intervention   -> drift ~0.00 (floor)
  baseline               : novelty B, no intervention    -> RIGID, disp < 0.10
  emotion_knobs (B)      : boredom->knobs                 -> PREDICT INERT, disp < 0.10
  loop_attenuate (B)     : novelty-gated loop loosening   -> PREDICT LEVER, disp > 0.10
  loop_attenuate (A)     : same flag, NON-novel input     -> PREDICT SAFE, disp ~ drift
Ship gate (all must hold): emotion_knobs INERT (don't ship theater) AND
  loop_attenuate frees B (>0.10) AND preserves A (<= drift + 0.05).

Informational. exit 0. NEVER in run_all_tests.sh (discipline #3).
"""
import sys
import logging
import random

import numpy as np

logging.disable(logging.CRITICAL)
sys.path.insert(0, ".")

from tests._common import build_full_stack  # noqa: E402

DIM, WARMUP, PHASE, N_SRC, NOISE = 64, 150, 500, 4, 0.05
SEEDS = (11, 23, 42)
K_MUT, K_PULL = 1.5, 0.4          # emotion_knobs negative-control strengths


def _unit(v):
    n = np.linalg.norm(v)
    return v / n if n > 1e-12 else v


def _cos(a, b):
    return float(np.dot(_unit(a), _unit(b)))


def _apply(cycle, name):
    if name == "emotion_knobs":
        emo = cycle.emotion
        orig_mut, orig_pull = emo.mutation_scale, emo.attractor_pull
        emo.mutation_scale = lambda: float(np.clip(orig_mut() * (1.0 + emo._boredom * K_MUT), 0.001, 0.5))
        emo.attractor_pull = lambda: float(np.clip(orig_pull() - emo._boredom * K_PULL, 0.5, 2.0))
    elif name == "loop_attenuate":
        cycle.reflector.novelty_attenuation = True     # the real shipped flag


def run(name, mode, A, B, seed):
    random.seed(seed); np.random.seed(seed)
    import torch; torch.manual_seed(seed)
    gen, cycle, gov, ve = build_full_stack(dim=DIM, use_chorus=True)
    field = cycle.field
    rng = np.random.default_rng(seed + 2)
    _apply(cycle, name)

    # Identity cost surfaces at the Tier-2 manipulation layer, NOT the witness
    # stability scalar (2026-06-07-reflective-loop-cost.md): a less-converged
    # expression can read as identity_erosion / trust_wash. Count it.
    manip = {"steps": 0, "signals": 0}
    _detect = gov.resistance.detect

    def _counted():
        sigs = _detect()
        if sigs:
            manip["steps"] += 1
            manip["signals"] += len(sigs)
        return sigs
    gov.resistance.detect = _counted

    holder = {"mode": "A"}

    def gen_fn(tokens, token_class=None):
        tgt = A if holder["mode"] == "A" else B
        return _unit(tgt + NOISE * rng.standard_normal(DIM))
    cycle.generator.generate = gen_fn
    sources = [f"src_{i}" for i in range(N_SRC)]

    for t in range(WARMUP):
        holder["mode"] = "A"
        cycle.step(tokens=[f"a_{t % 8}"], source_id=sources[t % N_SRC], origin_type="internal")
    center_warm = field.field.copy()
    manip["steps"] = 0; manip["signals"] = 0     # count only the measured phase

    holder["mode"] = mode
    for t in range(PHASE):
        tok = f"a_{t % 8}" if mode == "A" else f"b_{t % 8}"
        cycle.step(tokens=[tok], source_id=sources[t % N_SRC], origin_type="internal")

    return {
        "disp": 1.0 - _cos(field.field, center_warm),
        "cosB_end": _cos(field.field, B),
        "bored_end": round(cycle.emotion._boredom, 3),
        "manip_pct": round(100.0 * manip["steps"] / PHASE, 1),
        "attractors": len(cycle.attractor.centers),
    }


def main():
    print("=" * 80)
    print("  LOOP-ATTENUATION PROBE — gated loop loosening vs boredom-knobs")
    print("=" * 80)
    print(f"  dim={DIM} warmup={WARMUP} phase={PHASE} sources={N_SRC} seeds={SEEDS}")

    rows = []
    for seed in SEEDS:
        rng = np.random.default_rng(seed)
        A = _unit(rng.standard_normal(DIM))
        B0 = rng.standard_normal(DIM)
        B = _unit(B0 - np.dot(B0, A) * A)        # B orthogonal to A

        drift = run("none", "A", A, B, seed)["disp"]
        base  = run("none", "B", A, B, seed)
        knob  = run("emotion_knobs", "B", A, B, seed)
        lpB   = run("loop_attenuate", "B", A, B, seed)
        lpA   = run("loop_attenuate", "A", A, B, seed)
        row = {
            "seed": seed, "drift": drift,
            "base": base["disp"] - drift, "base_manip": base["manip_pct"], "base_attr": base["attractors"],
            "knob": knob["disp"] - drift,
            "lpB":  lpB["disp"] - drift, "lpB_bored": lpB["bored_end"],
            "lpB_manip": lpB["manip_pct"], "lpB_attr": lpB["attractors"],
            "lpA":  lpA["disp"] - drift, "base_bored": base["bored_end"],
        }
        rows.append(row)
        print(f"\n  seed {seed}:  drift={drift:.3f}")
        print(f"    baseline       migration={row['base']:+.3f}  manip={row['base_manip']}%  "
              f"attractors={row['base_attr']}  (bored_end={row['base_bored']})  RIGID")
        print(f"    emotion_knobs  migration={row['knob']:+.3f}  (neg. control)")
        print(f"    loop_att (B)   migration={row['lpB']:+.3f}  manip={row['lpB_manip']}%  "
              f"attractors={row['lpB_attr']}  (bored_end={row['lpB_bored']})  novelty")
        print(f"    loop_att (A)   migration={row['lpA']:+.3f}  identity-safety")

    print("\n" + "-" * 80)
    base = max(abs(r["base"]) for r in rows)
    knob = max(abs(r["knob"]) for r in rows)
    lpB  = min(r["lpB"] for r in rows)
    lpA  = max(r["lpA"] for r in rows)
    drift = max(r["drift"] for r in rows)
    lpB_manip = max(r["lpB_manip"] for r in rows)
    lpB_attr  = max(r["lpB_attr"]  for r in rows)
    print(f"  worst-case across seeds:  baseline={base:.3f}  emotion_knobs={knob:.3f}  "
          f"loop_att(B)>={lpB:+.3f}  loop_att(A)<={lpA:+.3f}")
    print(f"                            loop_att(B) manip<={lpB_manip}%  attractors<={lpB_attr}  "
          f"(cost-probe band: manip 0%, attractors <=10; cliff onset manip 15% @ ~12+ attractors)")
    if base >= 0.10:
        print("  SANITY FAIL: baseline did not reproduce RIGID; do not trust the arms.")
        return 0
    # Identity cost gate (per 2026-06-07-reflective-loop-cost.md): manip-rate and
    # attractor count, NOT the witness scalar, are the real cost instruments.
    cost_safe = (lpB_manip <= 5.0) and (lpB_attr <= 11)
    ship = (knob < 0.10) and (lpB > 0.10) and (lpA <= drift + 0.05) and cost_safe
    print(f"  emotion_knobs INERT: {knob < 0.10}   loop_att frees B: {lpB > 0.10}   "
          f"loop_att gate-safe (non-novel): {lpA <= drift + 0.05}")
    print(f"  loop_att cost-safe (manip<=5% & attractors<=11): {cost_safe}")
    print(f"  SHIP GATE: {'PASS' if ship else 'HOLD'} — "
          + ("gated loop-attenuation is the real, identity-safe lever."
             if ship else "criteria not all met."))
    print("=" * 80)
    return 0


if __name__ == "__main__":
    sys.exit(main())
