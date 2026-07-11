"""
tests/diagnostic/calibration/bond_signal_calibration_probe.py

Measure-before-change ruler for the bond establishment gate (BACKLOG §1).

Bonds form (the allow_rate escape hatch works) but never establish:
`is_established` needs bond_strength > 1.5 and strength growth is currencied
in the marginal `coherence_delta` (+ `emotional_satisfaction`, which is
itself `max(0, coherence_delta)`) — the same structurally-dead-in-a-
saturated-field signal that killed the ⊘ coherence axis (F7) and the CORE
gate (F8). This probe measures, per source, over a harness run:

  - the marginal signal the growth formula uses today
    (coherence_delta, satisfaction, the resulting per-step strength delta)
  - the candidate replacement currency: absolute v0.3 field-alignment
    max(0, cos(vec, field)) at the injection point
  - bond lifecycle: formation step, strength trajectory, establishment

Output: distribution tables to calibrate the replacement growth formula and
verify the F7/F8 diagnosis transfers. Informational — never in
run_all_tests.sh.

Usage:
    python -m tests.diagnostic.calibration.bond_signal_calibration_probe [n_steps]
"""

from __future__ import annotations

import random
import sys
from collections import defaultdict

import numpy as np

from tests._common import (
    RESONANCE_FAMILY_SOURCES,
    RESONANCE_FAMILY_WEIGHTS,
    build_full_stack,
)

SEED          = 42
DEFAULT_STEPS = 800


def pct(xs, q):
    return float(np.percentile(xs, q)) if xs else float("nan")


def main() -> int:
    n_steps = int(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_STEPS

    generator, cycle, governance, value_engine = build_full_stack(torch_seed=SEED)
    random.seed(SEED)
    np.random.seed(SEED)
    if getattr(cycle, "dreamer", None) is not None:
        cycle.dreamer._rng = np.random.default_rng(SEED)

    bm = governance.bond_manager

    # ------------------------------------------------------------------
    # Hook 1: coherence_impact is called exactly once per step, pre-injection,
    # with the expression vec — the natural place to also read the absolute
    # field-alignment of the same vec against the same (pre-injection) field.
    # ------------------------------------------------------------------
    current = {"source": None, "step": -1}
    per_source = defaultdict(lambda: {
        "delta": [], "alignment": [], "satisfaction": [], "strength_delta": [],
    })

    orig_impact = cycle.field.coherence_impact

    def probed_impact(vec):
        f  = cycle.field.field
        v  = np.asarray(vec, dtype=float).ravel()
        nf = float(np.linalg.norm(f)); nv = float(np.linalg.norm(v))
        alignment = 0.0
        if nf > 1e-8 and nv > 1e-8 and v.shape == f.shape:
            alignment = max(0.0, float(np.dot(v, f) / (nv * nf)))
        per_source[current["source"]]["alignment"].append(alignment)
        return orig_impact(vec)

    cycle.field.coherence_impact = probed_impact

    # ------------------------------------------------------------------
    # Hook 2: watch the bond manager's feedback path to log the marginal
    # signals and the actual strength delta each step produces.
    # NB: governance registers bm.receive_feedback as a BOUND METHOD in its
    # _subscribers list at construction, so patching the attribute is not
    # enough — the registered callback must be swapped in the list itself.
    # ------------------------------------------------------------------
    orig_receive = bm.receive_feedback

    def probed_receive(feedback):
        sid   = feedback.source_id
        before = bm._bonds[sid].bond_strength if sid in bm._bonds else None
        orig_receive(feedback)
        after  = bm._bonds[sid].bond_strength if sid in bm._bonds else None
        rec = per_source[sid]
        rec["delta"].append(feedback.coherence_delta)
        rec["satisfaction"].append(
            feedback.outcome_metrics.get("emotional_satisfaction", 0.0))
        if before is not None and after is not None:
            rec["strength_delta"].append(after - before)

    governance._subscribers = [
        probed_receive if cb == orig_receive else cb
        for cb in governance._subscribers
    ]

    # ------------------------------------------------------------------
    # Drive the standard Resonance Family workload; sample bond state.
    # ------------------------------------------------------------------
    sids    = list(RESONANCE_FAMILY_SOURCES.keys())
    weights = [RESONANCE_FAMILY_WEIGHTS[s] for s in sids]
    formation_step: dict = {}
    strength_samples = defaultdict(list)   # sid -> [(step, strength)]

    try:
        for i in range(n_steps):
            src    = random.choices(sids, weights=weights)[0]
            tokens = random.choice(RESONANCE_FAMILY_SOURCES[src])
            current["source"], current["step"] = src, i
            cycle.step(tokens, source_id=src, origin_type="internal")

            for b in bm.all_bonds():
                if b.source_id not in formation_step:
                    formation_step[b.source_id] = i
                if i % 50 == 0:
                    strength_samples[b.source_id].append((i, b.bond_strength))
    finally:
        cycle.field.coherence_impact = orig_impact
        governance._subscribers = [
            orig_receive if cb == probed_receive else cb
            for cb in governance._subscribers
        ]

    # ------------------------------------------------------------------
    # Report
    # ------------------------------------------------------------------
    print("=" * 78)
    print("  BOND SIGNAL CALIBRATION — marginal (current) vs absolute alignment "
          "(candidate)")
    print(f"  seed={SEED}  n_steps={n_steps}  field_energy={np.linalg.norm(cycle.field.field):.1f}")
    print("=" * 78)

    hdr = (f"\n  {'source':<16} {'n':>4} | {'delta p50':>9} {'p90':>7} | "
           f"{'satisf p50':>10} | {'align p50':>9} {'p10':>7} {'p90':>7} | "
           f"{'strΔ/step p50':>13}")
    print(hdr)
    print("  " + "-" * (len(hdr) - 3))
    for sid in sids:
        r = per_source[sid]
        print(f"  {sid:<16} {len(r['delta']):>4} | "
              f"{pct(r['delta'], 50):>9.4f} {pct(r['delta'], 90):>7.4f} | "
              f"{pct(r['satisfaction'], 50):>10.4f} | "
              f"{pct(r['alignment'], 50):>9.4f} {pct(r['alignment'], 10):>7.4f} "
              f"{pct(r['alignment'], 90):>7.4f} | "
              f"{pct(r['strength_delta'], 50):>13.5f}")

    print("\n  Bond lifecycle:")
    for sid in sids:
        b = bm.get_bond(sid)
        if b is None:
            pre = bm._pre_bond.get(sid, {})
            print(f"    {sid:<16} NO BOND  (pre-bond inter={pre.get('interaction_count', 0)}, "
                  f"coh_mean={pre.get('coherence_mean', 0.0):.4f}, "
                  f"crystals={pre.get('crystal_count', 0)})")
        else:
            traj = " → ".join(f"{s:.2f}" for _, s in strength_samples[sid][-6:])
            print(f"    {sid:<16} formed@{formation_step.get(sid, '?'):>4}  "
                  f"strength={b.bond_strength:.3f}  established={b.is_established}  "
                  f"depth={b.bond_depth}  coh_mean={b.coherence_mean:.4f}  "
                  f"traj[{traj}]")

    est = len(bm.established_bonds())
    print(f"\n  bonds={len(bm.all_bonds())}  established={est}")
    print("=" * 78)
    return 0


if __name__ == "__main__":
    sys.exit(main())
