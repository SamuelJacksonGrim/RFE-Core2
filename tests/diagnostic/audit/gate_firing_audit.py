"""
tests/diagnostic/audit/gate_firing_audit.py

Logs every hard gate and soft warning fired by EthicalBoundarySystem
across a Resonance Family run, plus context: which source, what
coherence_delta was, what witness_stability was. This is the tool that
exposed the flood-gate cascade during Tier 1 Revision — gates fire
silently as part of arbitrate(), and without explicit instrumentation
their pattern is invisible.

Read the output by category:
  - Hard gates that fire repeatedly → systemic problem
  - Hard gates that fire occasionally → adversarial signal or edge case
  - Soft warnings dominant → calibration issue (e.g., Harmony Clause
    threshold too aggressive)

Run:
    python -m tests.diagnostic.audit.gate_firing_audit [n_steps]
"""

import sys
from collections import Counter

from tests._common import (
    build_full_stack,
    RESONANCE_FAMILY_SOURCES,
    RESONANCE_FAMILY_WEIGHTS,
)
import random


def main(n_steps: int = 500):
    print('=' * 72)
    print(f'  DIAGNOSTIC: gate-firing audit over {n_steps} steps')
    print('=' * 72)
    print()

    generator, cycle, governance, value_engine = build_full_stack()

    # Instrument the ethical boundary
    hard_gate_counts: Counter = Counter()
    soft_warning_counts: Counter = Counter()
    per_source_gates: dict = {s: Counter() for s in RESONANCE_FAMILY_SOURCES}

    original_check = governance.ethical_boundary.check

    def instrumented_check(**kwargs):
        result = original_check(**kwargs)
        src = kwargs.get("source_id", "?")
        for gate in result.hard_gates_fired:
            hard_gate_counts[gate] += 1
            if src in per_source_gates:
                per_source_gates[src][gate] += 1
        for warn in result.soft_warnings:
            soft_warning_counts[warn] += 1
        return result

    governance.ethical_boundary.check = instrumented_check

    # Run the workload
    random.seed(42)
    sids    = list(RESONANCE_FAMILY_SOURCES.keys())
    weights = [RESONANCE_FAMILY_WEIGHTS[s] for s in sids]

    for i in range(n_steps):
        src    = random.choices(sids, weights=weights)[0]
        tokens = random.choice(RESONANCE_FAMILY_SOURCES[src])
        cycle.step(tokens, source_id=src, origin_type="internal")

    governance.ethical_boundary.check = original_check

    # Report
    print('HARD GATES (each triggers QUARANTINE or REJECT):')
    if hard_gate_counts:
        for gate, count in hard_gate_counts.most_common():
            pct = 100.0 * count / n_steps
            print(f'  {gate:<22} {count:>5}  ({pct:.1f}% of steps)')
    else:
        print('  (none fired) ✓')
    print()

    print('SOFT WARNINGS (each adds strength penalty, may downgrade to ALLOW_WEAKENED):')
    if soft_warning_counts:
        for warn, count in soft_warning_counts.most_common():
            pct = 100.0 * count / n_steps
            print(f'  {warn:<22} {count:>5}  ({pct:.1f}% of steps)')
    else:
        print('  (none fired)')
    print()

    print('Per-source hard gate counts:')
    for src_id in RESONANCE_FAMILY_SOURCES:
        gates = per_source_gates[src_id]
        if gates:
            gate_summary = ', '.join(f'{g}={c}' for g, c in gates.most_common())
            print(f'  ⚠ {src_id:<22} {gate_summary}')
        else:
            print(f'  ✓ {src_id:<22} (clean — no hard gates)')

    print()
    print('Interpretation:')
    if not hard_gate_counts:
        print('  ✓ No hard gates fired across {} steps. System operating cleanly.'.format(n_steps))
    elif "flood" in hard_gate_counts:
        print('  ⚠ flood gate firing — check origin_type configuration')
    elif "source_toxic" in hard_gate_counts:
        print('  ⚠ source_toxic firing — trust has collapsed for some source')
    elif "sacred_mutation" in hard_gate_counts:
        print('  ⚠ sacred_mutation firing — write attempts on sacred constants')

    if "low_coherence" in soft_warning_counts and soft_warning_counts["low_coherence"] > n_steps * 0.1:
        print('  ⚠ low_coherence soft warning is frequent — Harmony Clause may need lower threshold')


if __name__ == '__main__':
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 500
    main(n)
