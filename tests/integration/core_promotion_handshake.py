"""
tests/integration/core_promotion_handshake.py

Verifies SelfhoodGovernance.review_core_promotion() correctly applies
all five verification checks:

  1. Symbol still exists in registry
  2. Symbol is not already sacred
  3. Coherence contribution ≥ 5.0
  4. Multi-source OR dream-reinforced
  5. No active manipulation implicating contributing sources

The five rejection paths must all fire; the "all-pass" case must approve.
This is the regression guard for the value emergence → governance
handshake — Tier 4 will modify the feedback signal that drives value
strength, and we must be sure the promotion contract still holds.

Run:
    python -m tests.integration.core_promotion_handshake
"""

import sys

from tests._common import build_full_stack
from agents.value_emergence import CorePromotionRequest
from agents.manipulation_resistance import ManipulationSignal


def make_request(
    value_id:                   str   = "test_value",
    symbol_stable_id:           int   = None,    # filled in per test
    symbolic_core:              str   = "test_symbol",
    strength:                   float = 4.6,
    coherence_contribution:     float = 6.0,
    reinforcement_count:        int   = 20,
    dream_reinforced_count:     int   = 0,
    consecutive_eligible_steps: int   = 10,
    contributing_sources:       dict  = None,
) -> CorePromotionRequest:
    """Construct a CorePromotionRequest with sensible defaults."""
    if contributing_sources is None:
        contributing_sources = {"source_a": 0.5, "source_b": 0.5}
    return CorePromotionRequest(
        value_id                   = value_id,
        symbol_stable_id           = symbol_stable_id,
        symbolic_core              = symbolic_core,
        strength                   = strength,
        coherence_contribution     = coherence_contribution,
        reinforcement_count        = reinforcement_count,
        dream_reinforced_count     = dream_reinforced_count,
        consecutive_eligible_steps = consecutive_eligible_steps,
        contributing_sources       = contributing_sources,
    )


def expect(case_name: str, result: bool, expected: bool) -> bool:
    passed = result == expected
    mark = "✓" if passed else "✗"
    outcome = "APPROVED" if result else "REJECTED"
    expected_outcome = "APPROVE" if expected else "REJECT"
    print(f'  {mark} {case_name:<52} → {outcome:<10} (expected {expected_outcome})')
    return passed


def main():
    print('=' * 72)
    print('  INTEGRATION: CORE promotion handshake')
    print('=' * 72)
    print()

    generator, cycle, governance, value_engine = build_full_stack()
    registry = generator.registry
    results = []

    # ──────────────────────────────────────────────────────────────────
    # Case 1: REJECT — symbol does not exist in registry
    # ──────────────────────────────────────────────────────────────────
    governance._pending_signals = []
    req = make_request(
        symbol_stable_id = 999999,    # never registered
        symbolic_core    = "nonexistent_symbol",
    )
    result = governance.review_core_promotion(req)
    results.append(expect("Symbol vanished from registry", result, False))

    # ──────────────────────────────────────────────────────────────────
    # Case 2: REJECT — symbol is already sacred
    # ──────────────────────────────────────────────────────────────────
    # Use one of the three philosophical constants — already sacred at boot
    sacred_id = next(iter(governance.constants.sacred_ids))
    state = registry.get_by_stable_id(sacred_id)
    governance._pending_signals = []
    req = make_request(
        symbol_stable_id = sacred_id,
        symbolic_core    = state.symbol,
    )
    result = governance.review_core_promotion(req)
    results.append(expect("Symbol already sacred", result, False))

    # ──────────────────────────────────────────────────────────────────
    # Case 3: REJECT — coherence contribution below threshold
    # ──────────────────────────────────────────────────────────────────
    sid = registry.register("low_coherence_value").stable_id
    governance._pending_signals = []
    req = make_request(
        symbol_stable_id       = sid,
        symbolic_core          = "low_coherence_value",
        coherence_contribution = 3.0,    # below 5.0 threshold
    )
    result = governance.review_core_promotion(req)
    results.append(expect("Coherence contribution below 5.0", result, False))

    # ──────────────────────────────────────────────────────────────────
    # Case 4: REJECT — single source, no dream reinforcement
    # ──────────────────────────────────────────────────────────────────
    sid = registry.register("single_source_value").stable_id
    governance._pending_signals = []
    req = make_request(
        symbol_stable_id       = sid,
        symbolic_core          = "single_source_value",
        contributing_sources   = {"only_source": 1.0},   # single source
        dream_reinforced_count = 0,                      # no dreams
    )
    result = governance.review_core_promotion(req)
    results.append(expect("Single source, no dream reinforcement", result, False))

    # ──────────────────────────────────────────────────────────────────
    # Case 5: REJECT — manipulation signal implicates contributor
    # ──────────────────────────────────────────────────────────────────
    sid = registry.register("contaminated_value").stable_id
    governance._pending_signals = [
        ManipulationSignal(
            detector="trust_wash", severity=0.5,
            source_id="bad_actor", evidence={},
        )
    ]
    req = make_request(
        symbol_stable_id     = sid,
        symbolic_core        = "contaminated_value",
        contributing_sources = {"bad_actor": 0.6, "good_source": 0.4},
    )
    result = governance.review_core_promotion(req)
    results.append(expect("Manipulation signal from contributing source",
                          result, False))

    # ──────────────────────────────────────────────────────────────────
    # Case 6: APPROVE — multi-source, no dreams, all gates pass
    # ──────────────────────────────────────────────────────────────────
    sid = registry.register("clean_multi_source_value").stable_id
    governance._pending_signals = []
    req = make_request(
        symbol_stable_id       = sid,
        symbolic_core          = "clean_multi_source_value",
        contributing_sources   = {"source_a": 0.4, "source_b": 0.4, "source_c": 0.2},
        dream_reinforced_count = 0,
    )
    result = governance.review_core_promotion(req)
    results.append(expect("Clean multi-source promotion", result, True))

    # Verify it actually became sacred
    state_after = registry.get_by_stable_id(sid)
    sacred_after = state_after is not None and state_after.sacred
    mark = "✓" if sacred_after else "✗"
    print(f'  {mark} {"Symbol marked sacred after approval":<52} → '
          f'{"sacred=True" if sacred_after else "sacred=False"}')
    results.append(sacred_after)

    # ──────────────────────────────────────────────────────────────────
    # Case 7: APPROVE — single source + dream-reinforced
    # ──────────────────────────────────────────────────────────────────
    sid = registry.register("dream_reinforced_value").stable_id
    governance._pending_signals = []
    req = make_request(
        symbol_stable_id       = sid,
        symbolic_core          = "dream_reinforced_value",
        contributing_sources   = {"only_source": 1.0},   # single source
        dream_reinforced_count = 5,                      # but dream-reinforced
    )
    result = governance.review_core_promotion(req)
    results.append(expect("Single-source value with dream reinforcement",
                          result, True))

    print()
    print('=' * 72)
    passed = sum(1 for r in results if r)
    total  = len(results)
    if passed == total:
        print(f'  ALL CHECKS PASS: {passed}/{total} handshake gates verified.')
        return 0
    else:
        print(f'  FAILED: {passed}/{total} checks correct.')
        return 1


if __name__ == '__main__':
    sys.exit(main())
