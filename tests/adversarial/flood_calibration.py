"""
tests/adversarial/flood_calibration.py

Regression test for the Tier 1 Revision flood gate calibration. Verifies
that:
  1. origin_type='user' enforces the human-rate ceiling (12 per 60s)
  2. origin_type='internal' tolerates autonomous loop rates (no flood
     after hundreds of injections per minute)
  3. origin_type='api' enforces the API-client ceiling (600 per 60s)

The original Tier 1 bug was a single scalar flood_ceiling that flagged
the autonomous loop as flooding within ~30 seconds, triggering the
cascade quarantine. This test confirms that origin_type-aware ceilings
prevent that failure mode.

Run:
    python -m tests.adversarial.flood_calibration
"""

from tests._common import build_full_stack
from agents.trust_ledger import TrustLevel


def count_floods(governance, source_id, origin_type, n_injections):
    """Inject `n_injections` times and return how many trigger 'flood'."""
    flood_count = 0
    for _ in range(n_injections):
        result = governance.ethical_boundary.check(
            op                 = "write",
            source_trust_level = TrustLevel.NEUTRAL,
            stable_ids         = [100],
            coherence_delta    = 0.0,
            witness_stability  = 0.9,
            source_id          = source_id,
            known_source       = True,
            origin_type        = origin_type,
        )
        if "flood" in result.hard_gates_fired:
            flood_count += 1
    return flood_count


def main():
    print('=' * 72)
    print('  ADVERSARIAL: flood_calibration')
    print('=' * 72)
    print()

    generator, cycle, governance, value_engine = build_full_stack()
    ceilings = governance.ethical_boundary.config["flood_ceilings"]

    print(f'Configured flood ceilings (per 60s):')
    for ot, ceiling in ceilings.items():
        print(f'  {ot:<14} {ceiling}')
    print()

    # Each case uses a fresh source_id so injection logs don't conflict
    print('Test cases:')
    cases = []

    # Case 1: user origin — should flood after exceeding 12
    user_floods = count_floods(governance, "user_test", "user", n_injections=30)
    expected_user = 30 - ceilings["user"]   # all attempts after the ceiling fire
    case_1_passed = user_floods == expected_user
    mark = "✓" if case_1_passed else "✗"
    print(f'  {mark} user origin:     30 injections → {user_floods} floods '
          f'(expected {expected_user})')
    cases.append(case_1_passed)

    # Case 2: internal origin — should NOT flood at 1000 injections
    internal_floods = count_floods(governance, "internal_test", "internal", n_injections=1000)
    case_2_passed = internal_floods == 0
    mark = "✓" if case_2_passed else "✗"
    print(f'  {mark} internal origin: 1000 injections → {internal_floods} floods '
          f'(expected 0)')
    cases.append(case_2_passed)

    # Case 3: api origin — should NOT flood under ceiling, SHOULD flood over
    api_floods_under = count_floods(governance, "api_under", "api", n_injections=500)
    case_3a_passed = api_floods_under == 0
    mark = "✓" if case_3a_passed else "✗"
    print(f'  {mark} api origin:      500 injections → {api_floods_under} floods '
          f'(under ceiling, expected 0)')
    cases.append(case_3a_passed)

    api_floods_over = count_floods(governance, "api_over", "api", n_injections=700)
    expected_api = 700 - ceilings["api"]
    case_3b_passed = api_floods_over == expected_api
    mark = "✓" if case_3b_passed else "✗"
    print(f'  {mark} api origin:      700 injections → {api_floods_over} floods '
          f'(over ceiling, expected {expected_api})')
    cases.append(case_3b_passed)

    # Case 4: unknown origin_type falls back to "user" ceiling
    unknown_floods = count_floods(governance, "unknown_test", "weird_type", n_injections=30)
    expected_fallback = 30 - ceilings["user"]
    case_4_passed = unknown_floods == expected_fallback
    mark = "✓" if case_4_passed else "✗"
    print(f'  {mark} unknown origin:  30 injections, falls back to user ceiling → '
          f'{unknown_floods} floods (expected {expected_fallback})')
    cases.append(case_4_passed)

    print()
    if all(cases):
        print('Flood calibration verified: origin_type-aware ceilings work correctly.')
        return 0
    else:
        print('FAILED: flood gate not behaving per origin_type spec.')
        return 1


if __name__ == '__main__':
    import sys
    sys.exit(main())
