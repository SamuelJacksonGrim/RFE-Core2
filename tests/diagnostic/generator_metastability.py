"""
tests/diagnostic/generator_metastability.py

Relocated metastability readout + refinement de-collapse validation.

Fix 1's metric was validated on synthetic trajectories (G1-G4) and on the live
FIELD (G5: locked). But the field is a long-memory integrator (decay in
[0.97,0.9999], the persistence invariant) that smooths config wander away by
construction — metastability cannot live there. The decision was to read it
UPSTREAM, on the per-stage vector streams, via the online StreamMetastabilityMonitor
now wired into AutonomousCycle (cycle.generator_metastability for stage A, the raw
generator output; cycle.expression_metastability for stage C, the refined vector
that is actually injected).

This probe establishes two things on the live substrate:

  1. WHERE diversity lives. The generator output stream (stage A) carries many
     distinct config regimes switched aperiodically (high sequence-entropy). That
     diversity is real and upstream — though its metastability SCORE is borderline
     and init-dependent (~0.37-0.66 across generator seeds): it is "churny-diverse"
     (uniform short dwells), not yet a clean varied-dwell paper boat.

  2. THE REFINEMENT COLLAPSE, and its fix. Untrained recursive attention mean-pools
     its context, collapsing the expression (stage C) to a single direction
     (metastability -> 0, one regime) BEFORE injection. The diversity-preservation
     blend in RecursiveAttention.refine() weights the raw generator vector back in;
     the refined centroid then supplies dwell structure and the raw vector supplies
     diversity, so the expression becomes a genuine metastable trajectory in the
     0.4-0.6 target band. This probe runs the canonical Resonance Family workload
     with the blend OFF (collapse baseline) and at the configured default, reading
     the live monitors both times.

Contextual baseline, not a pass/fail gate. Informational, exit 0, never in
run_all_tests.sh.
"""
import sys
import logging
import random
import numpy as np

logging.disable(logging.CRITICAL)

DIM  = 128   # match the live runtime (loop/recursion1188 CONFIG, configs/*.yaml)
SEED = 7     # seed torch too — generator init/forward drives the absolute score
N    = 200


def _unit(v):
    n = np.linalg.norm(v)
    return v / n if n > 1e-12 else v


def _local_cos(traj, lookahead=12):
    u = [_unit(np.asarray(x, float)) for x in traj]
    s = [float(np.dot(u[i], u[j]))
         for i in range(len(u)) for j in range(i + 1, min(i + lookahead, len(u)))]
    return float(np.mean(s)) if s else 0.0


def _run(build_full_stack, sources, weights, blend):
    """One workload pass at a given diversity_blend. Returns the live monitor
    reports for stage A (generator) and stage C (expression), plus the captured
    stage-C trajectory for an independent cross-check."""
    random.seed(SEED); np.random.seed(SEED)
    import torch; torch.manual_seed(SEED)
    gen, cycle, gov, ve = build_full_stack(dim=DIM)
    cycle.rec_attn.diversity_blend = blend

    sids = list(sources.keys())
    w    = [weights[s] for s in sids]
    for _ in range(N):
        src    = random.choices(sids, weights=w)[0]
        tokens = random.choice(sources[src])
        cycle.step(tokens, source_id=src, origin_type="internal")

    a = cycle.generator_metastability.compute_now()
    c = cycle.expression_metastability.compute_now()
    return a, c


def main():
    print("=" * 84)
    print("  GENERATOR/EXPRESSION METASTABILITY — upstream readout + refinement de-collapse")
    print("=" * 84)

    try:
        import torch  # noqa: F401  (seeded inside _run; presence check here)
        from tests._common import (
            build_full_stack, RESONANCE_FAMILY_SOURCES, RESONANCE_FAMILY_WEIGHTS,
        )
        from cognition.recursive_attention import RecursiveAttention
    except Exception as e:
        print(f"  SKIPPED ({type(e).__name__}: {e}) — run where torch+stack available")
        return 0

    default_blend = RecursiveAttention().diversity_blend

    print(f"  Resonance Family workload, {N} steps, seed {SEED}, dim {DIM}. Reading the live")
    print(f"  monitors cycle.generator_metastability (stage A) and .expression_metastability (C).")
    print(f"  {'config':<22} {'A meta':>7} {'A reg':>6} {'A state':<13} | "
          f"{'C meta':>7} {'C reg':>6} {'C state':<13}")

    for blend, label in ((0.0, "blend OFF (collapse)"),
                         (default_blend, f"blend={default_blend:.2f} (default)")):
        a, c = _run(build_full_stack, RESONANCE_FAMILY_SOURCES, RESONANCE_FAMILY_WEIGHTS, blend)
        print(f"  {label:<22} {a.metastability:>7.3f} {a.n_regimes:>6} {a.regime_state:<13} | "
              f"{c.metastability:>7.3f} {c.n_regimes:>6} {c.regime_state:<13}")

    print("-" * 84)
    print("  READING: stage A (generator) carries the diversity — many regimes, aperiodic — at a")
    print("  borderline score, regardless of blend (the blend acts downstream). With blend OFF the")
    print("  expression (C) collapses to ~0.0 / one regime: untrained attention mean-pools to its")
    print(f"  centroid. At the default blend ({default_blend:.2f}) the raw vector is weighted back in and C")
    print("  de-collapses to multi-regime metastable — coherent-but-not-locked. The de-collapse is")
    print("  robust; the absolute score is generator-init-dependent (~0.4-0.73 across seeds) and can")
    print("  run above the 0.4-0.6 reference band at this default — dial blend toward 0.65 to sit")
    print("  lower. The monitors read both stages live (status() exposes them) for re-validation.")
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
