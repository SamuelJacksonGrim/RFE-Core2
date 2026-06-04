"""
tests/diagnostic/metastability_validation.py

PRE-DECLARED validation gate for substrate/metastability.py (Fix 1). Informational,
exit 0, never CI-gated. Declares pass conditions BEFORE running, so the metric is
proven against stated targets rather than tuned to whatever it happens to output.

GATE (all must hold):
  G1 locked       synthetic single-config field        -> LOW   + state "locked"
  G2 cycling      deterministic limit cycle (A,B,C,A..) -> LOW   + state "cycling"
                  (this is the prior ~0.756 false-negative; must die here)
  G3 metastable   aperiodic wandering among configs     -> HIGH  + state "metastable"
  G4 structureless random/neutral field at ~0.50        -> LOW   + state "structureless"
                  (distinct from "locked": opposite intervention)
  G5 LIVE         real-Generator-warmed field (~0.99)   -> LOW   + state "locked"
                  (separations must hold on the live field, not just synthetic)
"""
import sys, logging
import numpy as np
logging.disable(logging.CRITICAL)

from substrate.metastability import compute_metastability

DIM = 64
rng = np.random.default_rng(0)
def unit(v):
    n = np.linalg.norm(v); return v/n if n > 1e-12 else v

anchors = [unit(np.random.default_rng(s).standard_normal(DIM)) for s in range(6)]

def synth_locked(n=200):
    base = anchors[0]
    return [base * (1.0 + 0.01*rng.standard_normal()) for _ in range(n)]  # one config, tiny jitter

def synth_cycle(n=200):           # deterministic limit cycle over 3 configs
    return [anchors[i % 3] for i in range(n)]

def synth_metastable(n=200):      # aperiodic: random walk among configs, varied dwell
    out, cur = [], 0
    for _ in range(n):
        if rng.random() < 0.18:           # switch sometimes, irregular dwell
            cur = int(rng.integers(0, 5))
        out.append(anchors[cur] * (1.0 + 0.02*rng.standard_normal()))
    return out

def synth_structureless(n=200):   # pure noise, no stable config
    return [unit(rng.standard_normal(DIM)) for _ in range(n)]

def live_configs(n=120):
    import torch
    torch.manual_seed(7)
    from substrate.resonance_field import ResonanceField
    from agents.generator import Generator
    g = Generator(dim=128, depth=2, heads=4); g.eval()
    f = ResonanceField(dim=128)
    vocab = [["resonance","field"],["memory","crystal"],["bond","trust"],
             ["self","witness"],["value","emerge"],["anchor","return"]]
    cfgs, cohs = [], []
    for s in range(n):
        f.inject(g.generate(vocab[s % len(vocab)]), 1.0); f.decay()
        cfgs.append(f.observe().raw.copy())
        cohs.append(f.observe().spectral.phase_coherence)
    return cfgs, float(np.mean(cohs))

def check(name, report, want_state, want_high):
    ok_state = report.regime_state == want_state
    ok_level = (report.metastability >= 0.40) if want_high else (report.metastability < 0.40)
    verdict = "PASS" if (ok_state and ok_level) else "FAIL"
    print(f"  {name:14s} meta={report.metastability:.3f}  state={report.regime_state:13s} "
          f"reg={report.n_regimes} seqH={report.sequence_entropy_score:.2f} "
          f"dwellCV={report.dwell_variance_score:.2f}  -> {verdict}")
    return ok_state and ok_level

def main():
    print("="*84)
    print("  METASTABILITY METRIC — pre-declared validation gate (Fix 1)")
    print("="*84)
    print("  G1 locked->LOW/locked  G2 cycle->LOW/cycling  G3 wander->HIGH/metastable")
    print("  G4 noise->LOW/structureless  G5 live~0.99->LOW/locked")
    print("-"*84)

    results = []
    results.append(check("G1 locked",       compute_metastability(synth_locked(), coherence=0.99), "locked", False))
    results.append(check("G2 cycling",      compute_metastability(synth_cycle(),  coherence=0.95), "cycling", False))
    results.append(check("G3 metastable",   compute_metastability(synth_metastable(), coherence=0.62), "metastable", True))
    results.append(check("G4 structureless",compute_metastability(synth_structureless(), coherence=0.50), "structureless", False))

    # Old-vs-new on the limit cycle: prove the sequence-entropy term kills 0.756.
    print("-"*84)
    cyc = compute_metastability(synth_cycle(), coherence=0.95)
    print(f"  LIMIT-CYCLE DIAGNOSTIC: new meta={cyc.metastability:.3f} (prior scalar draft ~0.756). "
          f"seqH={cyc.sequence_entropy_score:.3f} is the veto term; multiplicity={cyc.multiplicity_score:.2f}, "
          f"dwellCV={cyc.dwell_variance_score:.2f} can stay high but seqH~0 collapses the geometric mean.")

    print("-"*84)
    try:
        cfgs, mean_coh = live_configs()
        live = compute_metastability(cfgs, coherence=mean_coh)
        print(f"  (live field mean coherence: {mean_coh:.3f})")
        results.append(check("G5 live",      live, "locked", False))
    except Exception as e:
        print(f"  G5 live: SKIPPED ({type(e).__name__}: {e}) — run where torch+generator available")

    print("-"*84)
    print(f"  GATE: {sum(results)}/{len(results)} checks passed"
          f"{'  — ALL PASS' if all(results) else '  — FAILURES PRESENT, metric not yet trustworthy'}")
    print()
    return 0

if __name__ == "__main__":
    sys.exit(main())
