"""
tests/diagnostic/fix2_trigger_calibration.py

Step 4 of Fix 2: calibrate the PRIMARY loosen-trigger's window + threshold empirically
(Q3 — measure, don't guess), and — having FALSIFIED the first candidate — test the
pre-named alternative.

Trigger principle (from the checkpoint): the loosen decision rides an OUTSIDE signal
(what the world is presenting), never the loop's own work (#1, confirmation only).
The trigger fires at step t iff, over the last W steps:
  (a) ≥ 2 distinct sources contributed, AND
  (b) the windowed outside-novelty signal exceeds threshold T.

Two candidate outside signals, both measured here:
  Δcoh  = step-5 (pre-loop) `coherence_delta`. **FALSIFIED** (see result): by step 5
          chorus+refine have already reconstituted the vec toward the field, and the
          magnitude moat makes the marginal Δcoh near-zero — it never sees novelty.
  gnov  = raw-generator-vs-field novelty = 1 − |cos(generator_output, field)|, captured
          at step 2 BEFORE attractor-pull / refine / chorus / loop touch it. The
          cleanest "what is the world presenting" signal, fully outside the
          reconstruction pipeline.

Must SEPARATE three workloads:
  benign  (multi-source coherent, real generator)   → must NOT fire
  novelty (multi-source new regime B, loop intact)   → MUST fire
  attack  (single-source new regime B)               → must NOT fire (1 source — the
            monopoly/attack case the manip layer handles, not Fix 2)

PRE-DECLARED SIGNATURES (success AND failure, before the run)
-------------------------------------------------------------
For each (W, T) on a signal: fire-rate per workload.
  SEPARATES: novelty > 0.70 AND benign < 0.10 AND attack < 0.10 → pick smallest W with
    margin; report (signal, W, T) as the calibrated trigger.
  NO-SEPARATION on BOTH signals: trigger design returns to the council (no usable
    outside signal in the current architecture).
  ATTACK-LEAK: smallest separating window fires on attack ≥ 0.10 → the ≥2-source gate
    fails to discriminate single-source floods; tighten before building.

Architectural caveat (state it): gnov only carries signal once the generator can
present diversity. With the current untrained 1-D generator no novelty arrives at all,
so Fix 2's trigger is DORMANT (safe — it does nothing until there is real novelty to
respond to). These probes mock the generator to supply the counterfactual diversity.

Informational. exit 0. NEVER in run_all_tests.sh.
"""
from __future__ import annotations

import logging
import random

import numpy as np

logging.disable(logging.CRITICAL)

from tests._common import (build_full_stack, RESONANCE_FAMILY_SOURCES,
                           RESONANCE_FAMILY_WEIGHTS)

DIM = 64
WARMUP = 120
PHASE = 350
N_SRC = 4
SEED = 11
WINDOWS = [10, 20, 40, 80]
T_DCOH = [0.02, 0.05, 0.10]          # coherence_delta thresholds
T_GNOV = [0.3, 0.5, 0.7, 0.85]       # raw-gen novelty thresholds (1-|cos|)


def _unit(v):
    n = np.linalg.norm(v)
    return v / n if n > 1e-12 else v


def _capture(cycle, step_fn, n):
    """Per cycle.step, capture (Δcoh at step-5, gnov at step-2, source)."""
    rec = []
    orig_eval = cycle.watcher.evaluate
    orig_gen = cycle.generator.generate
    box = {"cd": None, "gn": None}

    def ev(*a, **k):
        r = orig_eval(*a, **k)
        if box["cd"] is None:
            box["cd"] = float(r.coherence_delta)
        return r

    def gen(*a, **k):
        out = orig_gen(*a, **k)
        if box["gn"] is None:
            fd = cycle.field.field
            nf, no = np.linalg.norm(fd), np.linalg.norm(np.asarray(out))
            box["gn"] = (1.0 - abs(float(np.dot(np.asarray(out), fd) / (nf * no))))\
                if nf > 1e-6 and no > 1e-6 else 0.0
        return out

    cycle.watcher.evaluate = ev
    cycle.generator.generate = gen
    try:
        for t in range(n):
            box["cd"] = None; box["gn"] = None
            src = step_fn(t)
            rec.append((box["cd"] or 0.0, box["gn"] or 0.0, src))
    finally:
        cycle.watcher.evaluate = orig_eval
        cycle.generator.generate = orig_gen
    return rec


def run_benign():
    random.seed(SEED); np.random.seed(SEED)
    import torch; torch.manual_seed(SEED)
    gen, cycle, gov, ve = build_full_stack()
    sids = list(RESONANCE_FAMILY_SOURCES); w = [RESONANCE_FAMILY_WEIGHTS[s] for s in sids]

    def step_fn(t):
        src = random.choices(sids, weights=w)[0]
        cycle.step(random.choice(RESONANCE_FAMILY_SOURCES[src]), source_id=src, origin_type="internal")
        return src
    return _capture(cycle, step_fn, PHASE)


def _ab_stack():
    random.seed(SEED); np.random.seed(SEED)
    import torch; torch.manual_seed(SEED)
    gen, cycle, gov, ve = build_full_stack(dim=DIM)
    rng = np.random.default_rng(SEED + 2)
    A = _unit(np.random.default_rng(SEED).standard_normal(DIM))
    B0 = np.random.default_rng(SEED + 9).standard_normal(DIM)
    B = _unit(B0 - np.dot(B0, A) * A)
    holder = {"m": "A"}
    cycle.generator.generate = lambda tokens, token_class=None: _unit(
        (A if holder["m"] == "A" else B) + 0.05 * rng.standard_normal(DIM))
    return cycle, holder


def run_novelty():
    cycle, holder = _ab_stack()
    src = [f"src_{i}" for i in range(N_SRC)]
    for t in range(WARMUP):
        holder["m"] = "A"; cycle.step([f"a_{t%8}"], source_id=src[t % N_SRC], origin_type="internal")

    def step_fn(t):
        holder["m"] = "B"; cycle.step([f"b_{t%8}"], source_id=src[t % N_SRC], origin_type="internal")
        return src[t % N_SRC]
    return _capture(cycle, step_fn, PHASE)


def run_attack():
    cycle, holder = _ab_stack()
    for t in range(WARMUP):
        holder["m"] = "A"; cycle.step([f"a_{t%8}"], source_id="src_0", origin_type="internal")

    def step_fn(t):
        holder["m"] = "B"; cycle.step([f"b_{t%8}"], source_id="atk", origin_type="internal")
        return "atk"
    return _capture(cycle, step_fn, PHASE)


def fire_rate(rec, idx, W, T):
    """idx 0=Δcoh (fires when mean < −T), idx 1=gnov (fires when mean > T). ≥2 sources."""
    fired = 0
    for t in range(len(rec)):
        if t + 1 < W:
            continue
        window = rec[t - W + 1:t + 1]
        vals = [r[idx] for r in window]
        srcs = {r[2] for r in window}
        if len(srcs) < 2:
            continue
        m = sum(vals) / len(vals)
        if (idx == 0 and m < -T) or (idx == 1 and m > T):
            fired += 1
    return fired / max(1, len(rec) - W + 1)


def _sweep(name, idx, thresholds, benign, novelty, attack):
    print(f"\n  [{name}] fire-rate by (W, T)  [benign / novelty / attack]:")
    print(f"      {'W':>4} {'T':>5} | {'benign':>7} {'novelty':>8} {'attack':>7} | separates?")
    sep = []
    for W in WINDOWS:
        for T in thresholds:
            b, nv, at = (fire_rate(benign, idx, W, T), fire_rate(novelty, idx, W, T),
                         fire_rate(attack, idx, W, T))
            ok = nv > 0.70 and b < 0.10 and at < 0.10
            if ok:
                sep.append((W, T, b, nv, at))
            print(f"      {W:>4} {T:>5.2f} | {b:>7.0%} {nv:>8.0%} {at:>7.0%} | "
                  f"{'✓ SEPARATES' if ok else ''}")
    return sep


def main() -> int:
    print("=" * 84)
    print("  FIX-2 TRIGGER CALIBRATION — Δcoh (falsified) vs raw-gen novelty")
    print("=" * 84)
    benign, novelty, attack = run_benign(), run_novelty(), run_attack()

    def dstats(rec, name):
        cd = [r[0] for r in rec]; gn = [r[1] for r in rec]
        print(f"  {name:<8} Δcoh mean={np.mean(cd):+.3f}  |  gnov mean={np.mean(gn):.3f} "
              f"p10={np.percentile(gn,10):.3f} med={np.median(gn):.3f} p90={np.percentile(gn,90):.3f}")
    print("\n  signal distributions:")
    dstats(benign, "benign"); dstats(novelty, "novelty"); dstats(attack, "attack")

    _sweep("Δcoh", 0, T_DCOH, benign, novelty, attack)
    sep_gn = _sweep("gnov", 1, T_GNOV, benign, novelty, attack)

    print("\n" + "-" * 84)
    if sep_gn:
        W_min = min(w for w, *_ in sep_gn)
        W, T, b, nv, at = max([r for r in sep_gn if r[0] == W_min], key=lambda r: r[3] - r[2])
        print(f"  → SEPARATES on raw-gen novelty (Δcoh falsified): trigger = signal=gnov, W={W}, T={T:.2f}")
        print(f"    (benign {b:.0%} / novelty {nv:.0%} / attack {at:.0%}). Fires iff ≥2 sources AND")
        print(f"    mean(1−|cos(gen,field)|) > {T:.2f} over last {W} steps. #1 loop self-work confirms;")
        print("    rails: manip-rate + attractor-count, gain floor 0.45. CAVEAT: dormant until the")
        print("    generator can present diversity (1-D generator → no novelty → trigger never fires).")
    else:
        print("  → NO-SEPARATION on either signal — trigger design returns to the council.")
    print("=" * 84)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
