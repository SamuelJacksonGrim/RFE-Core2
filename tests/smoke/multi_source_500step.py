"""
tests/smoke/multi_source_500step.py

The canonical workload for verifying Tier 1 Revision behavior.

Resonance Family configuration — four sources (samuel/claude/gemini/grok)
weighted 40/25/20/15 — runs 500 steps. This is the test that drove the
Tier 1 Revision diagnostic process: it exposed the flood-gate cascade,
the false-positive trust_wash signal, and the bond formation failure
mode that led to the adaptive threshold + allow_rate metric.

Expected healthy outcome (from baselines/tier1_revision_500step.json):
  - allow_rate >= 0.95
  - all sources at trust 5.0 (SACRED ceiling)
  - HHI < 0.30  (LOW risk, healthy multi-source distribution)
  - bonds_formed >= 1 (some source produced crystals)
  - active_values >= 30
  - strong_values >= 2

Run:
    python -m tests.smoke.multi_source_500step
"""

from tests._common import (
    build_full_stack,
    run_resonance_sim,
    print_final_state,
    health_summary,
)


def main():
    print('=' * 72)
    print('  SMOKE: Resonance Family multi-source, 500 steps')
    print('=' * 72)
    print()

    generator, cycle, governance, value_engine = build_full_stack()

    decisions = run_resonance_sim(
        cycle            = cycle,
        governance       = governance,
        value_engine     = value_engine,
        n_steps          = 500,
        seed             = 42,
        checkpoint_steps = [50, 100, 200, 300, 400, 499],
        origin_type      = 'internal',
    )

    print_final_state(cycle, governance, value_engine, decisions)

    print()
    print('=' * 72)
    print('  HEALTH SUMMARY')
    print('=' * 72)
    summary = health_summary(cycle, governance, value_engine, decisions)
    for k, v in summary.items():
        if isinstance(v, float):
            print(f'  {k:<28} {v:.4f}')
        else:
            print(f'  {k:<28} {v}')

    print()
    print('Expected ranges (Tier 1 Revision healthy state):')
    print('  allow_rate                   >= 0.95')
    print('  all_sources_trust_max         True')
    print('  hhi                          < 0.30')
    print('  bonds_formed                 >= 1')
    print('  active_values                >= 30')
    print('  strong_values                >= 2')


if __name__ == '__main__':
    main()
