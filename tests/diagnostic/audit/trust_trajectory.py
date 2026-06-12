"""
tests/diagnostic/audit/trust_trajectory.py

Tracks per-source trust score over time, sampled at regular intervals.
Renders the trajectories as small ASCII line charts so you can see at
a glance whether trust is climbing, stable, oscillating, or crashing.

This is the diagnostic that first showed the cascade pattern during
Tier 1 Revision — samuel going 2.5 → 3.29 → 0.10 across 40 steps was
a cliff visible in the trajectory but invisible in summary statistics.

Run:
    python -m tests.diagnostic.audit.trust_trajectory [n_steps]
"""

import sys
import random
from collections import defaultdict

from tests._common import (
    build_full_stack,
    RESONANCE_FAMILY_SOURCES,
    RESONANCE_FAMILY_WEIGHTS,
)


def render_sparkline(values, width=40, lo=0.0, hi=5.0):
    """Render a list of floats as an ASCII sparkline."""
    chars = ' ▁▂▃▄▅▆▇█'
    if not values:
        return ''
    out = []
    for v in values:
        normalized = max(0.0, min(1.0, (v - lo) / (hi - lo)))
        idx = int(normalized * (len(chars) - 1))
        out.append(chars[idx])
    return ''.join(out)


def main(n_steps: int = 500, sample_every: int = 10):
    print('=' * 72)
    print(f'  DIAGNOSTIC: trust trajectory over {n_steps} steps')
    print('=' * 72)
    print()

    generator, cycle, governance, value_engine = build_full_stack()

    # Per-source trust history
    history: dict = defaultdict(list)

    random.seed(42)
    sids    = list(RESONANCE_FAMILY_SOURCES.keys())
    weights = [RESONANCE_FAMILY_WEIGHTS[s] for s in sids]

    for i in range(n_steps):
        src    = random.choices(sids, weights=weights)[0]
        tokens = random.choice(RESONANCE_FAMILY_SOURCES[src])
        cycle.step(tokens, source_id=src, origin_type="internal")

        if i % sample_every == 0:
            for s in RESONANCE_FAMILY_SOURCES:
                rec = governance.trust_ledger.sources.get(s)
                history[s].append(rec.trust_score if rec else 2.5)

    print(f'Sampled every {sample_every} steps; {len(next(iter(history.values())))} samples')
    print()
    print(f'  {"source":<22} {"start":>5} {"mid":>5} {"end":>5}  trajectory (0.0 →→→ 5.0)')
    print('  ' + '-' * 78)

    for src_id in RESONANCE_FAMILY_SOURCES:
        h = history[src_id]
        if not h:
            continue
        start = h[0]
        mid   = h[len(h) // 2]
        end   = h[-1]
        spark = render_sparkline(h, width=40, lo=0.0, hi=5.0)
        print(f'  {src_id:<22} {start:>5.2f} {mid:>5.2f} {end:>5.2f}  {spark}')

    print()
    print('Legend: each char is one sample. Higher = more trust.')
    print('Healthy pattern: all sources climb monotonically and saturate at the top.')
    print()

    # Diagnostic flags
    print('Interpretation:')
    healthy = True
    for src_id in RESONANCE_FAMILY_SOURCES:
        h = history[src_id]
        if not h:
            continue
        end = h[-1]
        if end < 1.0:
            print(f'  ✗ {src_id} crashed to {end:.2f} — cascade pattern')
            healthy = False
        elif end < 3.0:
            print(f'  ⚠ {src_id} mid-floor at {end:.2f} — trust dynamics issue')
            healthy = False
    if healthy:
        print('  ✓ All sources stabilized at or near SACRED ceiling.')


if __name__ == '__main__':
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 500
    main(n)
