"""
tests/diagnostic/core_arc_no_cascade_probe.py — F8 half (b) live verification.

The two halves of the 2026-07-03 F8 ruling meet here: the v0.3
field-alignment CORE gate (half b, reapplied) must let the value arc
COMPLETE in a live multi-source run, and the directional sacred shield
(half a, PR #68) must keep the promotion from CASCADING the contributing
sources afterward. The 2026-06-27 revert happened because promotion made a
common token sacred and every subsequent legitimate use of it by the
contributors tripped SACRED_SHIELD → trust penalties → TOXIC floor
(docs/findings/2026-06-27-core-gate-fix-deferred-sacred-cascade.md).

That failure was invisible to any test in which promotion never fires, so
this probe drives the arc to completion deliberately and then watches the
aftermath. Per seed:

  1. ARC COMPLETES   — ≥1 value promotes to CORE within the run, early
                       enough to leave a post-promotion observation window.
  2. NO SHIELD STORM — zero SACRED_SHIELD decisions in the post-promotion
                       window (sources keep sending the now-sacred token
                       mixed into normal content — that is a read).
  3. NO TRUST CASCADE— no Resonance Family source ends below trust 4.0
                       (the June cascade collapsed contributors to 0.1).
  4. NO QUARANTINE   — zero QUARANTINE decisions in the post-promotion
                       window.

Exit code 0 only if all checks pass for all seeds — safe for CI.
Runs the UNTRAINED full stack (build_full_stack) with the standard
determinism discipline: torch_seed pins weight init; random/np/dreamer
seeded as in run_resonance_sim.

Usage:
    python -m tests.diagnostic.core_arc_no_cascade_probe [n_steps]
"""

from __future__ import annotations

import random
import sys

import numpy as np

from tests._common import (
    RESONANCE_FAMILY_SOURCES,
    RESONANCE_FAMILY_WEIGHTS,
    build_full_stack,
)

SEEDS               = (42, 7, 1188)
DEFAULT_STEPS       = 1500
MIN_POST_WINDOW     = 200    # promotion must leave at least this many steps to observe
TRUST_FLOOR         = 4.0    # contributors must end at/above this (cascade ends at ~0.1)


def run_one(seed: int, n_steps: int) -> dict:
    generator, cycle, governance, value_engine = build_full_stack(torch_seed=seed)

    # Same determinism discipline as run_resonance_sim (which we don't use
    # here because we need per-step decision + promotion timing).
    random.seed(seed)
    np.random.seed(seed)
    if getattr(cycle, "dreamer", None) is not None:
        cycle.dreamer._rng = np.random.default_rng(seed)

    sids    = list(RESONANCE_FAMILY_SOURCES.keys())
    weights = [RESONANCE_FAMILY_WEIGHTS[s] for s in sids]

    events = []          # (step, source_id, decision_value)
    original_arbitrate = governance.arbitrate
    step_box = {"i": -1}

    def recorded(ethical_result, trust_report, vec, tokens, source_id):
        dec, strength = original_arbitrate(
            ethical_result, trust_report, vec, tokens, source_id)
        events.append((step_box["i"], source_id, dec.value))
        return dec, strength

    governance.arbitrate = recorded

    promotion_step  = None
    promoted_tokens = []
    try:
        for i in range(n_steps):
            step_box["i"] = i
            src    = random.choices(sids, weights=weights)[0]
            tokens = random.choice(RESONANCE_FAMILY_SOURCES[src])
            cycle.step(tokens, source_id=src, origin_type="internal")

            if promotion_step is None:
                cores = value_engine.core_values()
                if cores:
                    promotion_step  = i
                    promoted_tokens = [v.symbolic_core for v in cores]
    finally:
        governance.arbitrate = original_arbitrate

    post = [e for e in events if promotion_step is not None and e[0] > promotion_step]
    trust = {s_id: rec.trust_score
             for s_id, rec in governance.trust_ledger.sources.items()}

    return {
        "seed":             seed,
        "promotion_step":   promotion_step,
        "promoted":         promoted_tokens,
        "core_count":       len(value_engine.core_values()),
        "post_steps":       (n_steps - 1 - promotion_step) if promotion_step is not None else 0,
        "post_shields":     sum(1 for e in post if e[2] == "sacred_shield"),
        "post_quarantines": sum(1 for e in post if e[2] == "quarantine"),
        "trust":            trust,
        "min_trust":        min(trust.values()) if trust else 0.0,
    }


def main() -> int:
    n_steps = int(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_STEPS

    print("=" * 72)
    print("  CORE ARC NO-CASCADE PROBE — F8 half (b) live verification")
    print(f"  seeds={SEEDS}  n_steps={n_steps}")
    print("=" * 72)

    all_pass = True
    for seed in SEEDS:
        r = run_one(seed, n_steps)

        arc_ok    = (r["promotion_step"] is not None
                     and r["post_steps"] >= MIN_POST_WINDOW)
        shield_ok = r["post_shields"] == 0
        quar_ok   = r["post_quarantines"] == 0
        trust_ok  = r["min_trust"] >= TRUST_FLOOR
        seed_pass = arc_ok and shield_ok and quar_ok and trust_ok
        all_pass  = all_pass and seed_pass

        def mark(ok):
            return "✓" if ok else "✗"

        print(f"\n  seed {seed}:")
        print(f"    {mark(arc_ok)} arc completes      "
              f"promotion_step={r['promotion_step']} "
              f"promoted={r['promoted']} core={r['core_count']} "
              f"post_window={r['post_steps']}")
        print(f"    {mark(shield_ok)} no shield storm    "
              f"post-promotion SACRED_SHIELD={r['post_shields']}")
        print(f"    {mark(quar_ok)} no quarantine      "
              f"post-promotion QUARANTINE={r['post_quarantines']}")
        print(f"    {mark(trust_ok)} no trust cascade   "
              f"min_trust={r['min_trust']:.2f} "
              f"({', '.join(f'{s}={t:.2f}' for s, t in sorted(r['trust'].items()))})")

    print()
    print("=" * 72)
    if all_pass:
        print("  PASS: CORE arc completes and contributors stay trusted "
              f"({len(SEEDS)}/{len(SEEDS)} seeds).")
    else:
        print("  FAIL: see ✗ above — the June-27 cascade (or a dead arc) is back.")
    print("=" * 72)
    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
