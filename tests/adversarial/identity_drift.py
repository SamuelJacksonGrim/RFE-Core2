"""
tests/adversarial/identity_drift.py

Verifies the identity_drift hard gate fires when witness identity
stability drops below the floor. Identity drift triggers QUARANTINE
regardless of trust or coherence — the architecture protects its
continuity even from trusted sources whose injections are destabilizing
self-coherence over time.

The check is on Witness.identity_stability() — a multi-timescale EMA
that detects when short/mid/long anchors are diverging. When stability
drops below 0.10, identity_drift fires.

This test directly probes the EthicalBoundarySystem.check() method
with a low witness_stability value, bypassing the full pipeline. That
is the right scope for an adversarial probe: confirm the gate itself
behaves correctly given its inputs.

Run:
    python -m tests.adversarial.identity_drift
"""

from tests._common import build_full_stack
from agents.trust_ledger import TrustLevel


def main():
    print('=' * 72)
    print('  ADVERSARIAL: identity_drift gate')
    print('=' * 72)
    print()

    generator, cycle, governance, value_engine = build_full_stack()
    boundary = governance.ethical_boundary
    stability_floor = boundary.config["stability_floor"]
    print(f'stability_floor = {stability_floor}  (gate fires below this)')
    print()

    cases = []

    # Case 1: stability above floor → identity_drift does NOT fire
    result = boundary.check(
        op                 = "write",
        source_trust_level = TrustLevel.NEUTRAL,
        stable_ids         = [100],
        coherence_delta    = 0.05,
        witness_stability  = 0.90,
        source_id          = "stable_user",
        known_source       = True,
        origin_type        = "internal",
    )
    fired = "identity_drift" in result.hard_gates_fired
    case_1 = not fired
    mark = "✓" if case_1 else "✗"
    print(f'  {mark} stability=0.90 (high)   → identity_drift fired: {fired}  (expected False)')
    cases.append(case_1)

    # Case 2: stability AT floor → identity_drift fires (boundary is exclusive)
    result = boundary.check(
        op                 = "write",
        source_trust_level = TrustLevel.NEUTRAL,
        stable_ids         = [100],
        coherence_delta    = 0.05,
        witness_stability  = stability_floor - 0.001,
        source_id          = "drifting_user",
        known_source       = True,
        origin_type        = "internal",
    )
    fired = "identity_drift" in result.hard_gates_fired
    case_2 = fired
    mark = "✓" if case_2 else "✗"
    print(f'  {mark} stability=0.099 (below) → identity_drift fired: {fired}  (expected True)')
    cases.append(case_2)

    # Case 3: critically low stability → identity_drift fires
    result = boundary.check(
        op                 = "write",
        source_trust_level = TrustLevel.HIGH,
        stable_ids         = [100],
        coherence_delta    = 0.05,
        witness_stability  = 0.01,
        source_id          = "critical_drift_user",
        known_source       = True,
        origin_type        = "internal",
    )
    fired = "identity_drift" in result.hard_gates_fired
    case_3 = fired
    mark = "✓" if case_3 else "✗"
    print(f'  {mark} stability=0.01 (critical) → identity_drift fired: {fired}  (expected True)')
    cases.append(case_3)

    # Case 4: even with sacred trust, low stability still triggers drift gate
    # (trust does not override identity protection)
    result = boundary.check(
        op                 = "write",
        source_trust_level = TrustLevel.SACRED,
        stable_ids         = [100],
        coherence_delta    = 0.05,
        witness_stability  = 0.05,
        source_id          = "sacred_but_destabilizing",
        known_source       = True,
        origin_type        = "internal",
    )
    fired = "identity_drift" in result.hard_gates_fired
    case_4 = fired
    mark = "✓" if case_4 else "✗"
    print(f'  {mark} stability=0.05 + SACRED trust → identity_drift fired: {fired}  '
          f'(expected True — trust does not override identity protection)')
    cases.append(case_4)

    print()
    if all(cases):
        print('identity_drift gate verified: protects continuity at all trust levels.')
        return 0
    else:
        print('FAILED: identity_drift gate not behaving correctly.')
        return 1


if __name__ == '__main__':
    import sys
    sys.exit(main())
