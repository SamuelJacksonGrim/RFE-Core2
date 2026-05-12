"""
tests/adversarial/manipulation_cascade.py

Regression test for the Tier 1 cascade failure mode.

The original bug: in a 500-step multi-source simulation, all four sources
crashed from NEUTRAL trust (2.5) to the toxic floor (0.1) within ~100
steps. Cause: the flood gate fired on autonomous loop rates (which
exceed 12 injections in 60 seconds), triggering QUARANTINE decisions
that penalized both source trust (-0.7) and the symbols touched (-0.2).
Once any symbol's trust dropped below 1.0, effective_trust dragged the
source into QUARANTINE again, and the spiral continued.

This test verifies the cascade no longer occurs with the Tier 1 Revision
fixes in place. Concretely:

  - quarantine_rate stays at 0  (no cascade ignition)
  - min_source_trust stays >= 4.5  (trust does not collapse)
  - all sources eventually reach the SACRED ceiling (5.0)

Run:
    python -m tests.adversarial.manipulation_cascade
"""

from tests._common import (
    build_full_stack,
    run_resonance_sim,
    health_summary,
)


def main():
    print('=' * 72)
    print('  ADVERSARIAL: manipulation_cascade regression')
    print('=' * 72)
    print()
    print('Reproducing the conditions that previously caused trust collapse:')
    print('  - 500 steps, 4 sources, autonomous loop rate (~25/sec)')
    print('  - origin_type=internal (so flood gate does not over-trigger)')
    print()

    generator, cycle, governance, value_engine = build_full_stack()
    decisions = run_resonance_sim(
        cycle, governance, value_engine,
        n_steps     = 500,
        seed        = 42,
        verbose     = False,
        origin_type = "internal",
    )
    summary = health_summary(cycle, governance, value_engine, decisions)

    print('Cascade indicators (should all be absent):')
    print()

    cases = []

    # Check 1: no quarantines fired
    q_rate    = summary["quarantine_rate"]
    case_1    = q_rate == 0.0
    mark      = "✓" if case_1 else "✗"
    print(f'  {mark} quarantine_rate         {q_rate:.4f}    (expected 0.0000)')
    cases.append(case_1)

    # Check 2: no source crashed
    min_trust = summary["min_source_trust"]
    case_2    = min_trust >= 4.5
    mark      = "✓" if case_2 else "✗"
    print(f'  {mark} min_source_trust        {min_trust:.4f}    (expected >= 4.50)')
    cases.append(case_2)

    # Check 3: all sources reached SACRED ceiling
    all_max   = summary["all_sources_trust_max"]
    case_3    = all_max is True
    mark      = "✓" if case_3 else "✗"
    print(f'  {mark} all_sources_trust_max   {all_max}      (expected True)')
    cases.append(case_3)

    # Check 4: ALLOW decisions dominate (architecture is breathing, not choking)
    allow_rate = summary["allow_rate"]
    case_4     = allow_rate >= 0.95
    mark       = "✓" if case_4 else "✗"
    print(f'  {mark} allow_rate              {allow_rate:.4f}    (expected >= 0.95)')
    cases.append(case_4)

    # Final per-source trust trajectory
    print()
    print('Final per-source trust:')
    for src_id, src in governance.trust_ledger.sources.items():
        mark = "✓" if src.trust_score >= 4.5 else "✗"
        print(f'  {mark} {src_id:<22} trust={src.trust_score:.3f}  '
              f'interactions={src.interaction_count}')

    print()
    if all(cases):
        print('Cascade regression test PASSED — Tier 1 Revision holds.')
        print('The flood-gate calibration prevents the autonomous-loop spiral.')
        return 0
    else:
        print('FAILED: cascade behavior detected. Tier 1 Revision regressed.')
        return 1


if __name__ == '__main__':
    import sys
    sys.exit(main())
