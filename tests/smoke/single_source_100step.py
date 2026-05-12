"""
tests/smoke/single_source_100step.py

Single-source 100-step run, full stack. Verifies the system handles
sustained interaction from one source. Single-source pushes HHI to 1.0
(CRITICAL dependency risk) — but with the Tier 1 Revision flood fix
using origin_type='internal', the system should still operate healthily
even at the saturation rate of an autonomous loop.

Expected healthy outcome:
  - Trust trends toward or stabilizes near the SACRED ceiling
  - Some values form and progress past EMERGENT
  - No QUARANTINE decisions (clean source, no manipulation)
  - HHI = 1.0 (correct for single source)

Run:
    python -m tests.smoke.single_source_100step
"""

from tests._common import build_full_stack, print_final_state
from collections import Counter


def main():
    print('=' * 72)
    print('  SMOKE: single source, 100 steps')
    print('=' * 72)
    print()

    generator, cycle, governance, value_engine = build_full_stack()

    # Wrap arbitrate to count decisions
    decisions = Counter()
    original_arbitrate = governance.arbitrate
    def counted(ethical_result, trust_report, vec, tokens, source_id):
        dec, strength = original_arbitrate(ethical_result, trust_report, vec, tokens, source_id)
        decisions[dec.value] += 1
        return dec, strength
    governance.arbitrate = counted

    print(f'{"step":>4} | {"rhythm":<10} | {"coh":<5} | {"emotion":<10} | trust | values')
    print('-' * 66)

    try:
        for i in range(100):
            state = cycle.step(
                tokens      = ['resonance', 'field', 'engine'],
                source_id   = 'user',
                origin_type = 'internal',
            )
            if i in (0, 25, 50, 75, 99):
                src = governance.trust_ledger.sources.get('user')
                trust = src.trust_score if src else 0.0
                values = len(value_engine.values)
                print(f'{i:>4} | {state.rhythm:<10} | {state.coherence:.3f} | '
                      f'{state.dominant_emotion:<10} | {trust:.2f} | {values:>6}')
    finally:
        governance.arbitrate = original_arbitrate

    print_final_state(cycle, governance, value_engine, decisions)
    print()
    print('Healthy if: trust climbing toward 5.0, values forming, no QUARANTINEs.')


if __name__ == '__main__':
    main()
