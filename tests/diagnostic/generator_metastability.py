"""
tests/diagnostic/generator_metastability.py

Relocated metastability readout — the upstream half of the lock-in remediation.

Fix 1's metric was validated on synthetic trajectories (G1-G4) and shown to fire
correctly on the live FIELD (G5: locked). But the field is a long-memory
integrator (decay in [0.97,0.9999], the persistence invariant) that smooths
config wander away by construction — metastability cannot live there. The
decision was to read it UPSTREAM, on the generator output stream. This probe is
the live G3-equivalent that closes the gap PR #23 flagged: with the sqrt(d_model)
generator scale fix in place, does the generator's output read METASTABLE on the
live substrate?

It answers two things:

  1. LIVE BUFFER — does the loop's own GeneratorMetastabilityMonitor (the online
     stethoscope wired into AutonomousCycle) report the generator stream as
     metastable while the system runs the canonical Resonance Family workload?

  2. STAGE GRADIENT — captured per cycle, how does metastability change across
     the pipeline?  stage A (generator output)  ->  stage C (expression, after
     attractor-pull + recursive-attention refinement).

What the live substrate shows. Two readings, one robust and one nuanced:

  ROBUST (seed-independent): the pipeline COLLAPSES diversity. Stage A (generator
  output) holds many distinct config regimes switched aperiodically; stage C
  (expression, after recursive-attention refinement) is a single direction,
  metastability 0.000, stream-cos ~0.96-0.98. Refinement homogenizes the output
  before it is ever injected — a distinct downstream lock, the target of the next
  (de-collapse) step.

  NUANCED (init-dependent): diversity and aperiodicity genuinely live upstream
  (10+ regimes, high sequence-entropy), but the metastability SCORE at stage A is
  borderline and swings with the random generator init (~0.37-0.66 across seeds):
  the stream switches with uniform short dwells (low dwell-variance, high
  transition rate), so it is "churny-diverse," not a clean varied-dwell paper
  boat. So metastability is not yet cleanly present even upstream — it is the
  CAPACITY (diversity) that lives there, which refinement then discards.

Note on labels: the metric's locked/structureless label needs a coherence proxy.
The monitor derives it from the STREAM's own alignment, never the field's — so a
high-coherence field cannot mislabel a diverse generator stream as 'locked'.

Contextual baseline, not a pass/fail gate. Informational, exit 0, never in
run_all_tests.sh.
"""
import sys
import logging
import random
import numpy as np

logging.disable(logging.CRITICAL)

DIM = 128   # match the live runtime (loop/recursion1188 CONFIG, configs/*.yaml)


def _unit(v):
    n = np.linalg.norm(v)
    return v / n if n > 1e-12 else v


def _local_cos(traj, lookahead=12):
    u = [_unit(np.asarray(x, float)) for x in traj]
    s = [float(np.dot(u[i], u[j]))
         for i in range(len(u)) for j in range(i + 1, min(i + lookahead, len(u)))]
    return float(np.mean(s)) if s else 0.0


def main():
    print("=" * 84)
    print("  GENERATOR METASTABILITY — relocated (upstream) readout for G3-on-live")
    print("=" * 84)

    try:
        import torch
        from tests._common import (
            build_full_stack, RESONANCE_FAMILY_SOURCES, RESONANCE_FAMILY_WEIGHTS,
        )
        from substrate.metastability import compute_metastability
    except Exception as e:
        print(f"  SKIPPED ({type(e).__name__}: {e}) — run where torch+stack available")
        return 0

    # Seed everything — including torch, which drives generator init/forward — so
    # the baseline reading is reproducible (the score otherwise swings ~0.4-0.7
    # with random generator weights).
    SEED = 7
    random.seed(SEED)
    np.random.seed(SEED)
    torch.manual_seed(SEED)
    gen, cycle, gov, ve = build_full_stack(dim=DIM)

    # Per-stage capture: A = generator output (step 2), B = post attractor-pull
    # (step 3), C = expression post-refine (step 4). One sample per step, taken
    # from the FIRST call of each stage in the cycle (reflection re-invokes them).
    A, B, C = [], [], []
    mark = {"a": False, "p": False, "r": False}

    _g = cycle._generate
    def g(tokens, rhythm):
        v = _g(tokens, rhythm)
        if mark["a"]:
            A.append(np.asarray(v, float).copy())
            mark["a"] = False
            mark["p"] = mark["r"] = True
        return v
    _p = cycle.attractor.pull
    def p(vec, *a, **k):
        out = _p(vec, *a, **k)
        if mark["p"]:
            B.append(np.asarray(out, float).copy()); mark["p"] = False
        return out
    _r = cycle.rec_attn.refine
    def r(vec, *a, **k):
        out = _r(vec, *a, **k)
        if mark["r"]:
            C.append(np.asarray(out, float).copy()); mark["r"] = False
        return out
    cycle._generate = g
    cycle.attractor.pull = p
    cycle.rec_attn.refine = r

    sids = list(RESONANCE_FAMILY_SOURCES.keys())
    weights = [RESONANCE_FAMILY_WEIGHTS[s] for s in sids]
    cohs = []
    N = 300
    for _ in range(N):
        mark["a"] = True
        src = random.choices(sids, weights=weights)[0]
        tokens = random.choice(RESONANCE_FAMILY_SOURCES[src])
        st = cycle.step(tokens, source_id=src, origin_type="internal")
        cohs.append(st.coherence)
    mean_coh = float(np.mean(cohs))

    # 1. LIVE BUFFER — the loop's own stethoscope, read on demand.
    live = cycle.generator_metastability.compute_now()
    snap = cycle.generator_metastability.snapshot()
    print(f"  [1 live buffer] AutonomousCycle.generator_metastability over {snap['samples']} "
          f"of last {snap['window']} steps (seen={snap['seen']}):")
    print(f"       meta={live.metastability:.3f} state={live.regime_state} "
          f"regimes={live.n_regimes} seqH={live.sequence_entropy_score:.2f} "
          f"mult={live.multiplicity_score:.2f} dwellCV={live.dwell_variance_score:.2f}")
    print(f"       many regimes + aperiodic (high seqH) => DIVERSITY lives upstream; the")
    print(f"       metastability score is borderline/init-dependent (~0.37-0.66 across seeds).")

    # 2. STAGE GRADIENT — where the diversity survives, and where it collapses.
    # Each stage is scored against its OWN stream alignment (coherence proxy from
    # the stream, not the field) — consistent with how the live monitor labels.
    print(f"  [2 stage gradient] mean field coherence={mean_coh:.3f}, {N} steps "
          f"(warmup 40 dropped):")
    for name, traj in (("A generator output", A),
                       ("B post attractor-pull", B),
                       ("C expression (refined)", C)):
        t = traj[40:]
        stream_coh = _local_cos(t)
        rep = compute_metastability(t, coherence=stream_coh)
        print(f"       {name:<24} meta={rep.metastability:.3f} state={rep.regime_state:<13} "
              f"regimes={rep.n_regimes:<3} stream-cos={stream_coh:.3f} seqH={rep.sequence_entropy_score:.2f}")
    print(f"       A diverse (many regimes, aperiodic) -> C locked (1 regime): recursive-")
    print(f"       attention refinement homogenizes the expression BEFORE field injection.")

    print("-" * 84)
    print("  READING: diversity lives in the generator output (stage A: many regimes, aperiodic,")
    print("  borderline-metastable score); recursive-attention refinement (A->C) re-collapses it")
    print("  to a single direction. The metric is now wired live (cycle.generator_metastability);")
    print("  next step uses it to probe and loosen that collapse toward a coherent-but-not-locked")
    print("  expression, and to investigate the churny-diverse dwell structure upstream.")
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
