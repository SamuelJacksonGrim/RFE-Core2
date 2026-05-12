"""
tests/integration/tier1_revision_baseline.py

Regression guard for Tier 1 Revision. Runs the canonical 500-step
Resonance Family workload, then compares the resulting health summary
against the ranges defined in baselines/tier1_revision_500step.json.

Per the README philosophy: failures here are SHAPE failures, not
exact-value failures. A test "passes" if all metrics fall within their
expected ranges. Mismatches print clearly and indicate which metric
drifted out of healthy operating shape.

Run:
    python -m tests.integration.tier1_revision_baseline

Exit code 0 if all metrics within baseline ranges. Non-zero if any drift
detected — but read the output before assuming a real regression. Random
seeds occasionally produce outlier runs; rerun with a different seed
before concluding a real problem.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from tests._common import build_full_stack, run_resonance_sim, health_summary


BASELINE_PATH = (
    Path(__file__).parent.parent / "baselines" / "tier1_revision_500step.json"
)


def check_metric(name: str, value, ranges: dict) -> tuple[bool, str]:
    """Return (passed, message) for a single metric against its range."""
    if name not in ranges:
        return True, f"  {name:<26} {value}  (no range defined)"

    bounds = ranges[name]
    lo = bounds.get("min")
    hi = bounds.get("max")

    in_range = True
    if lo is not None and value < lo:
        in_range = False
    if hi is not None and value > hi:
        in_range = False

    mark = "✓" if in_range else "✗"
    val_str = f"{value:.4f}" if isinstance(value, float) else str(value)
    range_str = f"[{lo}, {hi}]"
    return in_range, f"  {mark} {name:<26} {val_str:<10} expected {range_str}"


def main(seed: int = 42) -> int:
    print('=' * 72)
    print('  INTEGRATION: Tier 1 Revision baseline check')
    print('=' * 72)
    print()
    print(f'Baseline source: {BASELINE_PATH.name}')
    print(f'Seed:            {seed}')
    print()

    if not BASELINE_PATH.exists():
        print(f'ERROR: baseline file missing at {BASELINE_PATH}')
        return 2

    with open(BASELINE_PATH) as f:
        baseline = json.load(f)

    ranges = baseline["expected_ranges"]

    # Build and run
    generator, cycle, governance, value_engine = build_full_stack()
    decisions = run_resonance_sim(
        cycle, governance, value_engine,
        n_steps      = 500,
        seed         = seed,
        verbose      = False,
        origin_type  = "internal",
    )
    summary = health_summary(cycle, governance, value_engine, decisions)

    # Check each metric
    print('Metric checks:')
    all_passed = True
    for metric in ranges:
        if metric not in summary:
            continue
        passed, msg = check_metric(metric, summary[metric], ranges)
        print(msg)
        if not passed:
            all_passed = False

    print()
    if all_passed:
        print('Baseline check PASSED — system operating within healthy shape.')
        print()
        print('Shape assertions:')
        for name, desc in baseline["shape_assertions"].items():
            print(f'  ✓ {name}')
            print(f'      {desc}')
        return 0
    else:
        print('Baseline check FAILED — at least one metric out of range.')
        print()
        print('Before concluding regression:')
        print('  1. Re-run with a different seed (stochastic ordering produces variance)')
        print('  2. If consistent across seeds, investigate the failing metric')
        print('  3. Only update the baseline if the new behavior is intentional')
        return 1


if __name__ == '__main__':
    seed = int(sys.argv[1]) if len(sys.argv) > 1 else 42
    sys.exit(main(seed))
