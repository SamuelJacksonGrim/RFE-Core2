"""
tests/integration/reflective_loop_lock_guard.py

Regression guard for the plasticity arc's keystone result: **the reflective loop is
the lock.** It pins the *characteristic*, not a value — if a future change alters the
reflective loop's convergence (or accidentally relocates the lock), this catches that
the lock characteristic moved.

Asserts, on the live full stack (generator output mocked A→B, multi-source HHI<0.70,
the exact setup of `attractor_migration_probe` / `reconstruction_ablation_probe`):

  RIGID with the loop intact   — baseline migration < 0.10 (the field does NOT follow
                                 a persistent gate-surviving new regime).
  MIGRATES with the loop off   — suppressing only `reflector.reflect` lifts migration
                                 > 0.50 (the lock releases, and ONLY via this path).

Source of truth: `2026-06-07-reconstruction-ablation.md` (baseline ≈ +0.008,
no_reflect ≈ +0.90–0.96 across 3 seeds). Thresholds are deliberately loose (0.10 /
0.50) — this is a shape guard, not an exact-value test (per tests/README philosophy).

Run:
    python -m tests.integration.reflective_loop_lock_guard
Exit 0 if both characteristics hold; non-zero if the lock characteristic moved.
Re-run with a different seed before concluding a real regression (stochastic init).
"""
from __future__ import annotations

import sys

import numpy as np

from tests.diagnostic.reconstruction_ablation_probe import run, _unit, DIM

RIGID_MAX    = 0.10   # loop intact: migration must stay below this
MIGRATE_MIN  = 0.50   # loop off:   migration must exceed this


def main(seed: int = 11) -> int:
    print("=" * 72)
    print("  GUARD: the reflective loop is the lock (loop on = RIGID, off = migrates)")
    print("=" * 72)

    rng = np.random.default_rng(seed)
    A = _unit(rng.standard_normal(DIM))
    B0 = rng.standard_normal(DIM)
    B = _unit(B0 - np.dot(B0, A) * A)            # orthogonal new regime

    drift   = run("none", "A", A, B)["disp"]                 # non-novel drift baseline
    base    = run("none", "B", A, B)["disp"] - drift         # loop intact, novel regime
    noreflect = run("no_reflect", "B", A, B)["disp"] - drift # only the loop suppressed

    print(f"  seed={seed}  drift={drift:.3f}")
    print(f"  migration (loop intact)    = {base:+.3f}   expect < {RIGID_MAX}  (RIGID)")
    print(f"  migration (loop suppressed) = {noreflect:+.3f}   expect > {MIGRATE_MIN}  (MIGRATES)")

    rigid_ok    = base < RIGID_MAX
    migrate_ok  = noreflect > MIGRATE_MIN
    print()
    print(f"  {'✓' if rigid_ok else '✗'} loop intact is RIGID")
    print(f"  {'✓' if migrate_ok else '✗'} loop suppressed MIGRATES (lock releases via this path only)")
    print()

    if rigid_ok and migrate_ok:
        print("  PASS — the lock characteristic holds: the reflective loop is the lever.")
        return 0
    print("  FAIL — the lock characteristic MOVED. Before concluding a regression:")
    print("    1. re-run with another seed (init variance);")
    print("    2. if consistent, the reflective loop's convergence behaviour changed —")
    print("       check `loop/autonomous_cycle.py` step 6 / `cognition/reflective_loop.py`.")
    return 1


if __name__ == "__main__":
    seed = int(sys.argv[1]) if len(sys.argv) > 1 else 11
    sys.exit(main(seed))
