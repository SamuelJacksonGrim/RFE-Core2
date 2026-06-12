"""
tests/diagnostic/audit/value_polarity_flow.py

Tracks value formation, polarity progression, and dissolution over a
Resonance Family run. Shows whether values are progressing through
polarities (healthy emergence) or thrashing (formation/dissolution
churn without sustained growth).

Useful for:
  - Confirming that the bond-weighted decay protection is working
    (values whose sources have bonds should stop dissolving)
  - Detecting when the system is forming values it can't sustain
  - Seeing if any values reach the CORE promotion eligibility window

Run:
    python -m tests.diagnostic.audit.value_polarity_flow [n_steps]
"""

import sys
import random
from collections import defaultdict

from tests._common import (
    build_full_stack,
    RESONANCE_FAMILY_SOURCES,
    RESONANCE_FAMILY_WEIGHTS,
)


def snapshot(value_engine):
    """Return a dict mapping value_id → polarity for all current values."""
    return {
        v.value_id: v.polarity.value
        for v in value_engine.values.values()
    }


def main(n_steps: int = 500, sample_every: int = 25):
    print('=' * 72)
    print(f'  DIAGNOSTIC: value polarity flow over {n_steps} steps')
    print('=' * 72)
    print()

    generator, cycle, governance, value_engine = build_full_stack()

    births: int = 0
    deaths: int = 0
    transitions: dict = defaultdict(int)   # (from_polarity, to_polarity) → count
    polarity_timeline: list = []

    prev_states: dict = {}

    random.seed(42)
    sids    = list(RESONANCE_FAMILY_SOURCES.keys())
    weights = [RESONANCE_FAMILY_WEIGHTS[s] for s in sids]

    for i in range(n_steps):
        src    = random.choices(sids, weights=weights)[0]
        tokens = random.choice(RESONANCE_FAMILY_SOURCES[src])
        cycle.step(tokens, source_id=src, origin_type="internal")

        # Snapshot current state vs previous
        current = snapshot(value_engine)
        for vid, polarity in current.items():
            if vid not in prev_states:
                births += 1
            elif prev_states[vid] != polarity:
                transitions[(prev_states[vid], polarity)] += 1
        for vid in prev_states:
            if vid not in current:
                deaths += 1
        prev_states = current

        if i % sample_every == 0:
            polarity_counts = defaultdict(int)
            for v in value_engine.values.values():
                polarity_counts[v.polarity.value] += 1
            polarity_timeline.append((i, dict(polarity_counts)))

    print(f'Births:      {births} new values formed')
    print(f'Deaths:      {deaths} values dissolved')
    print(f'Net change:  {births - deaths}')
    print()

    print('Polarity transitions (X → Y → count):')
    polarity_order = ['emergent', 'weak', 'active', 'strong', 'core', 'dissolved']
    upward = 0
    downward = 0
    for (frm, to), count in sorted(transitions.items()):
        try:
            arrow = '↑' if polarity_order.index(to) > polarity_order.index(frm) else '↓'
        except ValueError:
            arrow = ' '
        if arrow == '↑':
            upward += count
        elif arrow == '↓':
            downward += count
        print(f'  {arrow} {frm:<10} → {to:<10} {count:>4}')
    print()
    print(f'  Upward transitions:   {upward}')
    print(f'  Downward transitions: {downward}')
    print()

    print('Polarity distribution over time:')
    print(f'  {"step":>5} | {"emerg":>5} {"weak":>5} {"actv":>5} {"strg":>5} {"core":>5} {"diss":>5}')
    print('  ' + '-' * 50)
    for step, counts in polarity_timeline:
        print(f'  {step:>5} | '
              f'{counts.get("emergent", 0):>5} '
              f'{counts.get("weak", 0):>5} '
              f'{counts.get("active", 0):>5} '
              f'{counts.get("strong", 0):>5} '
              f'{counts.get("core", 0):>5} '
              f'{counts.get("dissolved", 0):>5}')

    print()
    print('Interpretation:')
    if upward >= downward and births > deaths:
        print('  ✓ Net growth — values are forming and progressing')
    elif births == deaths:
        print('  ⚠ Births equal deaths — values churning without retention')
    else:
        print('  ✗ More dissolutions than births — value retention failing')

    if value_engine.core_values():
        print(f'  ✓ {len(value_engine.core_values())} CORE values promoted')
    else:
        print(f'  ℹ No CORE values yet (typically requires longer runs to satisfy')
        print(f'    the 10-consecutive-eligible-step rule)')


if __name__ == '__main__':
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 500
    main(n)
