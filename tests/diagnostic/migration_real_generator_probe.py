"""
tests/diagnostic/migration_real_generator_probe.py

Re-verifies the keystone RIGID migration result on the REAL generator (not the B-mock).
The attractor-migration finding (2026-06-07) measured RIGID by *mocking* an orthogonal
new regime B into the field. But lock #1 is resolved — the live generator emits genuine
directional diversity (2026-06-08-generator-diversity-remeasure). So: does the field
still reconstitute REAL generator diversity, or did the mock overstate the lock?

Design (best case for migration, on real directions):
  For each seed, search the vocab for the MOST-SEPARATED token pair the generator
  produces — tokA → A_dir, tokB → B_dir (lowest cos(A_dir, B_dir)). Then, on the full
  live stack (loop intact, NO governor — this re-verifies the EXISTING system):
    warmup   inject tokA (multi-source, HHI<0.70) → field establishes on A_dir
    phase B  inject tokB → does the field's attractor center migrate toward B_dir?
    control  continue tokA → drift baseline (subtracted)
  migration = disp(phase B) − disp(control); attractor center = unit(field.field).
  field.inject is instrumented to show what actually LANDS (cos to A_dir / B_dir).

Real B is LESS novel than the mock's orthogonal B (bounded generator diversity), so
this is the *fair* test: if even a maximally-separated real direction can't move the
field, RIGID holds for real diversity.

PRE-DECLARED SIGNATURES (before the run)
----------------------------------------
  RIGID    : migration < 0.10 across seeds → the reflective loop reconstitutes REAL
      diversity too; the mock did not overstate the lock; Fix 2 is needed AND live.
  MIGRATES : migration > 0.50 → the field adapts to real generator diversity on its
      own; the lock was partly an artifact of the orthogonal mock → rescope Fix 2.
  PARTIAL  : 0.10–0.50 → real diversity moves the field somewhat; report and rescope.
  CONFOUNDED (per seed): cos(A_dir, B_dir) > 0.70 (the generator can't present two
      distinct enough real regimes this init) → that seed can't test migration; skip
      it. If ALL seeds confound → the real generator's diversity is too low to migrate
      *anything*, which is its own finding (lock #1 resolved but diversity marginal).

Informational. exit 0. NEVER in run_all_tests.sh.
"""
from __future__ import annotations

import logging
import random

import numpy as np

logging.disable(logging.CRITICAL)

from tests._common import build_full_stack

DIM = 64
WARMUP = 150
PHASE = 400
N_SRC = 4
SEEDS = [0, 1, 2]
N_CAND = 24            # candidate tokens to search for the most-separated pair
SAMPLE = 100


def _unit(v):
    v = np.asarray(v, dtype=float)
    return v / (np.linalg.norm(v) + 1e-9)


def _cos(a, b):
    return float(np.dot(_unit(a), _unit(b)))


def _separated_pair(cycle):
    """Find the token pair whose real generator directions are most separated."""
    toks = [f"concept_{i}" for i in range(N_CAND)]
    dirs = {t: _unit(cycle.generator.generate([t])) for t in toks}
    best = None
    for i in range(N_CAND):
        for j in range(i + 1, N_CAND):
            c = _cos(dirs[toks[i]], dirs[toks[j]])
            if best is None or c < best[2]:
                best = (toks[i], toks[j], c)
    ta, tb, sep = best
    return ta, tb, dirs[ta], dirs[tb], sep


def _run(seed, mode):
    """mode 'A' = control (continue A); 'B' = switch to B in the phase.
    Returns (disp, landed_cosA, landed_cosB, A_dir, B_dir, sep)."""
    random.seed(seed); np.random.seed(seed)
    import torch; torch.manual_seed(seed)
    gen, cycle, gov, ve = build_full_stack(dim=DIM)
    field = cycle.field
    tokA, tokB, A_dir, B_dir, sep = _separated_pair(cycle)
    sources = [f"src_{i}" for i in range(N_SRC)]

    inj = {"rec": False, "n": 0, "cA": 0.0, "cB": 0.0}
    orig = field.inject

    def _inject(vec, strength=1.0):
        if inj["rec"]:
            inj["n"] += 1
            inj["cA"] += _cos(vec, A_dir); inj["cB"] += _cos(vec, B_dir)
        return orig(vec, strength)
    field.inject = _inject

    for t in range(WARMUP):
        cycle.step([tokA], source_id=sources[t % N_SRC], origin_type="internal")
    center_warm = field.field.copy()

    tok = tokA if mode == "A" else tokB
    inj["rec"] = True
    for t in range(PHASE):
        cycle.step([tok], source_id=sources[t % N_SRC], origin_type="internal")

    n = max(1, inj["n"])
    disp = 1.0 - _cos(field.field, center_warm)
    return disp, inj["cA"] / n, inj["cB"] / n, A_dir, B_dir, sep


def main() -> int:
    print("=" * 84)
    print("  MIGRATION ON THE REAL GENERATOR — does the field reconstitute real diversity?")
    print("=" * 84)
    migs, confounded = [], 0
    for seed in SEEDS:
        ctl = _run(seed, "A")
        nov = _run(seed, "B")
        sep = nov[5]
        mig = nov[0] - ctl[0]
        conf = sep > 0.70
        if conf:
            confounded += 1
        else:
            migs.append(mig)
        print(f"\n  seed {seed}: most-separated real pair cos(A_dir,B_dir)={sep:+.3f}"
              + ("  ⚠ CONFOUNDED (regimes too similar)" if conf else ""))
        print(f"      disp(control)={ctl[0]:.3f}  disp(novel B)={nov[0]:.3f}  "
              f"migration={mig:+.3f}")
        print(f"      landed under B: cos·A_dir={nov[1]:+.3f}  cos·B_dir={nov[2]:+.3f} "
              f"(generator emits B at cos·B_dir≈1)")

    print("\n" + "-" * 84)
    if not migs:
        print(f"  → ALL {confounded} SEEDS CONFOUNDED: the real generator can't present two")
        print("    distinct enough regimes (cos(A,B) > 0.70) to test migration. Lock #1 is")
        print("    resolved but real diversity is marginal at this dim — its own finding.")
        print("=" * 84)
        return 0
    mu = float(np.mean(migs))
    print(f"  VERDICT  mean migration over {len(migs)} non-confounded seeds = {mu:+.3f}"
          + (f"  ({confounded} confounded)" if confounded else ""))
    if mu < 0.10:
        print("  → RIGID on the real generator: the reflective loop reconstitutes REAL")
        print("    diversity too — the mock did NOT overstate the lock. Fix 2 is needed AND")
        print("    LIVE (not dormant). Proceed to build the governor, re-verified on real input.")
    elif mu > 0.50:
        print("  → MIGRATES on the real generator: the field adapts to real diversity on its")
        print("    own; the lock was partly an artifact of the orthogonal mock. RESCOPE Fix 2.")
    else:
        print(f"  → PARTIAL ({mu:+.3f}): real diversity moves the field somewhat. Rescope —")
        print("    the mock's orthogonal B overstated the lock's severity; read per-seed above.")
    print("=" * 84)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
