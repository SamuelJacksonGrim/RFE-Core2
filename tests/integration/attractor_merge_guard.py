"""
tests/integration/attractor_merge_guard.py

Regression guard for the latent `Attractor` crash surfaced by the reflective-loop
cost probe (`2026-06-07-reflective-loop-cost.md`): `AttractorCenter` was a plain
`@dataclass`, so its generated `__eq__` compared the `vector` ndarray field
elementwise; `list.remove(center)` in `merge_pass` (and `prune`) then raised
"truth value of an array with more than one element is ambiguous" whenever a
removal fired. The fix is `@dataclass(eq=False)` (identity equality).

This reproduces the exact removal paths and asserts they no longer raise.

Run:  python -m tests.integration.attractor_merge_guard
Exit 0 if both removal paths work; non-zero on regression.
"""
from __future__ import annotations

import sys

import numpy as np

from agents.attractor import Attractor, AttractorCenter


def _unit(v):
    v = np.asarray(v, dtype=np.float32)
    return v / (np.linalg.norm(v) + 1e-8)


def main() -> int:
    print("=" * 64)
    print("  GUARD: Attractor merge/prune removal does not crash on array __eq__")
    print("=" * 64)
    ok = True

    # --- merge_pass: two near-identical centers must merge (one removed) ---
    att = Attractor(merge_threshold=0.90)
    base = _unit(np.random.default_rng(0).standard_normal(16))
    near = _unit(base + 0.01 * np.random.default_rng(1).standard_normal(16))  # cos ≈ 1
    att.centers = [
        AttractorCenter(vector=base, origin_tokens=["a"], strength=2.0),
        AttractorCenter(vector=near, origin_tokens=["b"], strength=1.0),
    ]
    try:
        att.merge_pass()
        merged_ok = len(att.centers) == 1
        print(f"  merge_pass: 2 similar centers → {len(att.centers)} "
              f"({'✓ merged, no crash' if merged_ok else '✗ wrong count'})")
        ok &= merged_ok
    except Exception as e:
        print(f"  merge_pass: ✗ CRASHED — {type(e).__name__}: {e}")
        ok = False

    # --- prune path: exceed max_centers, weakest removed (the other .remove site) ---
    att2 = Attractor(merge_threshold=0.999, max_centers=3)
    rng = np.random.default_rng(7)
    try:
        for k in range(6):                       # add() prunes weakest past max_centers
            att2.add(_unit(rng.standard_normal(16)), tokens=[f"t{k}"])
        prune_ok = len(att2.centers) <= 3
        print(f"  prune (max_centers=3): added 6 → {len(att2.centers)} "
              f"({'✓ pruned, no crash' if prune_ok else '✗ over cap'})")
        ok &= prune_ok
    except Exception as e:
        print(f"  prune: ✗ CRASHED — {type(e).__name__}: {e}")
        ok = False

    print()
    if ok:
        print("  PASS — both removal paths work under identity equality.")
        return 0
    print("  FAIL — attractor removal regressed (check @dataclass(eq=False) on AttractorCenter).")
    return 1


if __name__ == "__main__":
    sys.exit(main())
