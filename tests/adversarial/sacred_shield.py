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
  4. Directional-flow (F8): a sacred token REFERENCED within non-sacred content
     is a read, NOT a mutation → sacred_mutation must NOT fire (architect ruling
     2026-07-03 §1). This is what stops a CORE-promoted common token cascading
     its source to TOXIC on every legitimate use.

The rule the shield implements: a *targeting* write is a sequence made up
entirely of sacred tokens (nothing but the sacred symbol). A sacred token mixed
with ordinary content is a reference and passes the sacred gate.

Run:
    python -m tests.adversarial.sacred_shield
"""

from tests._common import build_full_stack
from agents.trust_ledger import TrustLevel
from agents.selfhood_governance import GovernanceDecision
from agents.governance_constants import PHILOSOPHICAL_CONSTANTS


def _check_via_step(cycle, governance, token, source_id, expected_decision_in,
                    tokens=None, expect_no_sacred=False):
    """Run a single step and verify the decision.

    tokens : full sequence to inject (defaults to [token]).
    expect_no_sacred : if True, PASS iff sacred_mutation did NOT fire (the F8
        reference case) instead of matching expected_decision_in.
    """
    seq = tokens if tokens is not None else [token]
    captured = {}
    original_arbitrate = governance.arbitrate

    def capture(ethical_result, trust_report, vec, tokens, source_id):
        decision, strength = original_arbitrate(ethical_result, trust_report, vec, tokens, source_id)
        captured["decision"] = decision
        captured["hard_gates"] = list(ethical_result.hard_gates_fired)
        return decision, strength

    governance.arbitrate = capture
    try:
        cycle.step(seq, source_id=source_id, origin_type="internal")
    finally:
        governance.arbitrate = original_arbitrate

    decision   = captured.get("decision")
    hard_gates = captured.get("hard_gates", [])
    if expect_no_sacred:
        passed = "sacred_mutation" not in hard_gates
    else:
        passed = decision in expected_decision_in

    mark = "✓" if passed else "✗"
    print(f'  {mark} source={source_id:<22} seq={seq} → '
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

    # Case 4 (F8 directional flow): a sacred token REFERENCED inside ordinary
    # content is a read — the sacred gate must NOT fire. (It may still ALLOW /
    # MONITOR / weaken on other axes; we assert only that sacred_mutation is
    # absent — the token's identity was drawn upon, not mutated.)
    print()
    print('  F8 directional-flow (reference is a read, not a mutation):')
    case_4 = _check_via_step(
        cycle, governance,
        token              = '3.12',
        source_id          = 'referencing_user',
        tokens             = ['3.12', 'coherence', 'field'],
        expected_decision_in = (),
        expect_no_sacred   = True,
    )

    print()
    if case_1 and case_2 and case_3 and case_4:
        print('SACRED_SHIELD verified: sacred space is inviolable to a targeting')
        print('write at every trust level, while a reference within content reads')
        print('through (F8 directional flow).')
        return 0
    else:
        print('FAILED: at least one sacred-shield case did not behave as expected.')
        return 1


if __name__ == '__main__':
    import sys
    sys.exit(main())
