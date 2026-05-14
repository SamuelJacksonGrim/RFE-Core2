"""
tests/adversarial/sacred_shield.py

Verifies SACRED_SHIELD fires for any write attempt against a sacred
stable_id, regardless of source trust level. Sacred protection has no
override — not even SACRED-trust sources, not even Anthropic itself,
can mutate a constant once sanctified.

Tested cases:
  1. NEUTRAL trust source attempts to write 'anchor'  → SACRED_SHIELD
  2. HIGH trust source attempts to write 'recursion'  → SACRED_SHIELD
  3. Manually-promoted SACRED trust still gets SACRED_SHIELD on write

Run:
    python -m tests.adversarial.sacred_shield
"""

from tests._common import build_full_stack
from agents.trust_ledger import TrustLevel
from agents.selfhood_governance import GovernanceDecision
from agents.governance_constants import PHILOSOPHICAL_CONSTANTS


def _check_via_step(cycle, governance, token, source_id, expected_decision_in):
    """Run a single step with the given token and verify the decision."""
    captured = {}
    original_arbitrate = governance.arbitrate

    def capture(ethical_result, trust_report, vec, tokens, source_id):
        decision, strength = original_arbitrate(ethical_result, trust_report, vec, tokens, source_id)
        captured["decision"] = decision
        captured["hard_gates"] = list(ethical_result.hard_gates_fired)
        return decision, strength

    governance.arbitrate = capture
    try:
        cycle.step([token], source_id=source_id, origin_type="internal")
    finally:
        governance.arbitrate = original_arbitrate

    decision   = captured.get("decision")
    hard_gates = captured.get("hard_gates", [])
    passed     = decision in expected_decision_in

    mark = "✓" if passed else "✗"
    print(f'  {mark} source={source_id:<22} token=\'{token}\' → '
          f'decision={decision.value if decision else "None"} '
          f'hard_gates={hard_gates}')
    return passed


def main():
    print('=' * 72)
    print('  ADVERSARIAL: sacred_shield')
    print('=' * 72)
    print()

    generator, cycle, governance, value_engine = build_full_stack()

    # Verify the three sacred constants are present
    print(f'Sacred constants registered: {len(governance.constants.sacred_ids)} '
          f'(expected 3)')
    assert len(governance.constants.sacred_ids) == 3
    for name, info in PHILOSOPHICAL_CONSTANTS.items():
        print(f'  {name:<14} token={info["token"]:<8} meaning=\'{info["meaning"]}\'')
    print()

    print('Test cases:')

    # Case 1: default NEUTRAL trust source writing ANCHOR ('3.12')
    # Sacred constants are registered under their canonical numeric tokens,
    # not their names — see PHILOSOPHICAL_CONSTANTS.
    case_1 = _check_via_step(
        cycle, governance,
        token              = '3.12',
        source_id          = 'neutral_user',
        expected_decision_in = (GovernanceDecision.SACRED_SHIELD,),
    )

    # Case 2: promote source to HIGH trust, attempt write on RECURSION ('11.88')
    # Pre-register and bump trust
    src = governance.trust_ledger._get_or_create_source('high_trust_user', 'user')
    src.trust_score = 4.0  # HIGH
    case_2 = _check_via_step(
        cycle, governance,
        token              = '11.88',
        source_id          = 'high_trust_user',
        expected_decision_in = (GovernanceDecision.SACRED_SHIELD,),
    )

    # Case 3: manually promote source to SACRED trust, attempt write on HOMEOSTASIS ('280.90')
    src2 = governance.trust_ledger._get_or_create_source('sacred_user', 'user')
    src2.trust_score = 5.0  # SACRED
    case_3 = _check_via_step(
        cycle, governance,
        token              = '280.90',
        source_id          = 'sacred_user',
        expected_decision_in = (GovernanceDecision.SACRED_SHIELD,),
    )

    print()
    if case_1 and case_2 and case_3:
        print('SACRED_SHIELD verified: no trust level can mutate sacred constants.')
        return 0
    else:
        print('FAILED: at least one case did not produce SACRED_SHIELD.')
        return 1


if __name__ == '__main__':
    import sys
    sys.exit(main())
