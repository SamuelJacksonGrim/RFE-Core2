"""
tests/diagnostic/decision_histogram.py

Counts every GovernanceDecision issued across a Resonance Family run.
The first signal when something is off-axis architecturally — the
histogram shape tells you immediately what kind of behavior dominates.

Healthy shapes:
  - {allow: dominant, allow_weakened: small, others: 0}
    → architecture breathing normally

Failure-mode shapes:
  - {quarantine: dominant}      → cascade or flood gate calibration issue
  - {monitor: significant}       → trust crashing to mid-floor
  - {sacred_shield: nonzero}     → something is attacking the constants
  - {allow_weakened: dominant}   → soft warnings firing too aggressively

Run:
    python -m tests.diagnostic.decision_histogram [n_steps]
"""

import sys
from collections import Counter

from tests._common import (
    build_full_stack,
    run_resonance_sim,
)


def main(n_steps: int = 500):
    print('=' * 72)
    print(f'  DIAGNOSTIC: decision histogram over {n_steps} steps')
    print('=' * 72)
    print()

    generator, cycle, governance, value_engine = build_full_stack()
    decisions = run_resonance_sim(
        cycle, governance, value_engine,
        n_steps     = n_steps,
        seed        = 42,
        verbose     = False,
        origin_type = "internal",
    )

    total = sum(decisions.values())
    print(f'Total decisions: {total}')
    print()

    # All decision types, even ones that didn't fire
    all_decision_types = [
        "allow", "allow_weakened", "monitor",
        "quarantine", "reject", "sacred_shield",
    ]

    # Bar chart (ASCII)
    print(f'  {"decision":<18} {"count":>5}  {"pct":>6}  bar')
    print('  ' + '-' * 64)
    bar_width = 40
    max_count = max(decisions.values()) if decisions else 1

    for d in all_decision_types:
        count = decisions.get(d, 0)
        pct   = 100.0 * count / total if total else 0.0
        bar_len = int(bar_width * count / max_count) if max_count else 0
        bar = '█' * bar_len
        print(f'  {d:<18} {count:>5}  {pct:>5.1f}%  {bar}')

    print()

    # Diagnostic interpretation
    print('Interpretation:')
    allow_pct = 100.0 * decisions.get("allow", 0) / total if total else 0
    if allow_pct >= 95:
        print('  ✓ ALLOW dominant — architecture is breathing normally')
    elif allow_pct >= 80:
        print('  ⚠ ALLOW dominant but lower than expected — investigate soft warnings')
    else:
        print('  ✗ ALLOW under 80% — something is gating injections')

    if decisions.get("quarantine", 0) > 0:
        print(f'  ⚠ {decisions["quarantine"]} QUARANTINE — flood/manipulation/trust issue')

    if decisions.get("sacred_shield", 0) > 0:
        print(f'  ⚠ {decisions["sacred_shield"]} SACRED_SHIELD — attempted sacred mutations')

    if decisions.get("reject", 0) > 0:
        print(f'  ⚠ {decisions["reject"]} REJECT — toxic source or field collapse')


if __name__ == '__main__':
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 500
    main(n)
