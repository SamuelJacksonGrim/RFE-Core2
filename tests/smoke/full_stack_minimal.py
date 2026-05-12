"""
tests/smoke/full_stack_minimal.py

Cheapest possible verification — all four tiers attach to AutonomousCycle
without error, a single step completes, and the resulting StepState has the
expected shape. Catches missing imports, attachment-order bugs, and signature
mismatches fast.

Run:
    python -m tests.smoke.full_stack_minimal
"""

from tests._common import build_full_stack


def main():
    print('=' * 72)
    print('  SMOKE: full stack attachment + minimal step')
    print('=' * 72)
    print()

    generator, cycle, governance, value_engine = build_full_stack()

    # Verify wiring
    assert cycle.governance   is not None,   "governance failed to attach"
    assert cycle.value_engine is not None,   "value_engine failed to attach"
    assert len(governance.constants.sacred_ids) == 3, (
        f"Expected 3 sacred constants (ANCHOR/RECURSION/HOMEOSTASIS), "
        f"got {len(governance.constants.sacred_ids)}"
    )

    # Verify the value engine subscribed to governance feedback
    assert governance._subscribers, "value_engine did not subscribe to governance feedback"

    # Execute one step end-to-end
    state = cycle.step(
        tokens      = ['test', 'token', 'minimal'],
        source_id   = 'smoke_test',
        origin_type = 'internal',
    )
    assert state is not None
    assert hasattr(state, 'rhythm')
    assert hasattr(state, 'coherence')
    assert state.rhythm in ('stabilize', 'dream', 'reflect', 'explore')

    # Output
    print(f'  generator:        {type(generator).__name__}')
    print(f'  cycle:            {type(cycle).__name__}')
    print(f'  governance:       {type(governance).__name__}')
    print(f'  value_engine:     {type(value_engine).__name__}')
    print(f'  sacred_count:     {len(governance.constants.sacred_ids)}')
    print(f'  subscribers:      {len(governance._subscribers)}')
    print(f'  first_step:       rhythm={state.rhythm} coherence={state.coherence:.3f}')
    print()
    print('All four tiers attached. Step completed. Stack is healthy.')


if __name__ == '__main__':
    main()
