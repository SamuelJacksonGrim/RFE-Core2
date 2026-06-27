"""
tests/diagnostic/calibration/floor_calibration_probe.py

Measure-before-you-change instrument for the two structural cracks the pass-3
evaluation found (`docs/findings/2026-06-25-ground-truth-pass3-stack-evaluation.md`):

  A. RHYTHM/ENERGY — the field energy scale at dim 128 vs the rhythm bands
     (stabilize<0.5 · dream 0.5-2 · reflect 2-5 · explore>=5). Reports the real
     energy distribution and PREVIEWS the rhythm spread under candidate calibrations
     (energy normalizations / rescaled bands) WITHOUT changing anything.

  B. CORE coherence signal — the gate `coherence_contribution >= 5.0` against the
     dead marginal accumulator. Reports, per value, the current (dead) signal AND
     candidate alignment-based signals, so we can see which one would let the right
     values (the identity anchors) cross 5.0 and hold the rest back — i.e. choose a
     signal+threshold that DISCRIMINATES, not one that promotes everything or nothing.

This commits NO change. It is the ruler we measure the change against, before and
after. Informational; exit 0; NEVER in run_all_tests.sh.
"""
import sys, logging, random, statistics as st
import numpy as np

logging.disable(logging.CRITICAL)
sys.path.insert(0, ".")

from agents.generator import Generator                                # noqa: E402
from agents.selfhood_governance import SelfhoodGovernance            # noqa: E402
from agents.value_emergence import ValueEmergenceEngine              # noqa: E402
from loop.autonomous_cycle import AutonomousCycle                    # noqa: E402

DIM, STEPS = 128, 600
SOURCES = {
    "source_samuel": [["identity","continuity","witness"],["anchor","recursion","homeostasis"],["architect","design","intent"]],
    "source_claude": [["recursive","cognition","substrate"],["coherence","integration","synthesis"],["watcher","witness","mirror"]],
    "source_gemini": [["memory","crystal","attractor"],["relational","bond","connection"],["temporal","stream","continuity"]],
    "source_grok":   [["mutation","bifurcation","chaos"],["explore","novelty","edge"],["wave","collapse","coherence"]],
}
WEIGHTS = {"source_samuel":0.40,"source_claude":0.25,"source_gemini":0.20,"source_grok":0.15}


def _align(gen, token, f_unit):
    try:
        v = np.asarray(gen.generate([token]), dtype=float).ravel()
        n = np.linalg.norm(v)
        return max(0.0, float(np.dot(v, f_unit) / n)) if n > 1e-8 else 0.0
    except Exception:
        return 0.0


def _band(energy, thr):
    s, d, r = thr
    if energy < s:  return "stabilize"
    if energy < d:  return "dream"
    if energy < r:  return "reflect"
    return "explore"


def main() -> int:
    random.seed(42); np.random.seed(42)
    import torch; torch.manual_seed(42)
    gen = Generator(vocab_size=8192, dim=DIM, depth=4, heads=4)
    from training.corpus import load_corpus, to_rhythm_seeds, TRAIN_PATH
    from training.rhythm_pretraining import RhythmPretrainer, PretrainingConfig
    RhythmPretrainer(gen, rhythm_seeds=to_rhythm_seeds(load_corpus(TRAIN_PATH)),
                     config=PretrainingConfig(n_epochs=8)).pretrain()
    gen.eval()
    cycle = AutonomousCycle(generator=gen, dim=DIM, use_chorus=True, log_interval=999999,
                            reflect_novelty_attenuation=True)
    gov = SelfhoodGovernance(registry=gen.registry); cycle.attach_governance(gov)
    ve = ValueEmergenceEngine(registry=gen.registry, generator=gen, governance=gov)
    cycle.attach_value_engine(ve)

    rng = random.Random(1188); sids = list(SOURCES); w = [WEIGHTS[s] for s in sids]
    energies = []
    # per-value accumulated alignment (the counterfactual CORE accumulator): each step,
    # for every active value, add its current expressed-field alignment. This is the
    # positive analogue of coherence_contribution's marginal sum.
    accum_align = {}
    for i in range(STEPS):
        s = rng.choices(sids, weights=w)[0]
        cycle.step(rng.choice(SOURCES[s]), source_id=s, origin_type="internal")
        energies.append(cycle.field.observe().energy)
        if i % 5 == 0:                                  # sample every 5 steps (cost)
            f = np.asarray(cycle.field.field, dtype=float).ravel()
            fn = np.linalg.norm(f); f_unit = f / fn if fn > 1e-8 else f
            for v in ve.values.values():
                if v.dissolved_at_step < 0:
                    accum_align[v.value_id] = accum_align.get(v.value_id, 0.0) + \
                                              _align(gen, v.symbolic_core, f_unit) * 5

    # ---------- A. RHYTHM / ENERGY ----------
    e = np.array(energies)
    qs = np.percentile(e, [10, 25, 50, 75, 90])
    print("="*78); print("  FLOOR CALIBRATION PROBE — measure before changing"); print("="*78)
    print(f"\n[A] FIELD ENERGY (dim {DIM}, {STEPS} steps)")
    print(f"    min={e.min():.2f}  q10={qs[0]:.2f}  q25={qs[1]:.2f}  median={qs[2]:.2f}  "
          f"q75={qs[3]:.2f}  q90={qs[4]:.2f}  max={e.max():.2f}")
    candidates = {
        "current bands (0.5/2/5) on raw energy":      (lambda x: x, (0.5, 2.0, 5.0)),
        "normalize energy / median, bands 0.5/1/2":   (lambda x: x/qs[2], (0.5, 1.0, 2.0)),
        "rescaled bands at energy quantiles q25/q50/q75": (lambda x: x, (qs[1], qs[2], qs[3])),
    }
    print("    rhythm spread under candidate calibrations (want a real spread, not 99% one band):")
    for name,(norm,thr) in candidates.items():
        from collections import Counter
        c = Counter(_band(norm(x), thr) for x in e)
        frac = {k: round(c.get(k,0)/len(e),2) for k in ("stabilize","dream","reflect","explore")}
        print(f"      {name:<48} {frac}")

    # ---------- B. CORE coherence signal ----------
    vals = [v for v in ve.values.values() if v.dissolved_at_step < 0]
    cc = [v.coherence_contribution for v in vals]
    f = np.asarray(cycle.field.field, dtype=float).ravel(); fn = np.linalg.norm(f); fu = f/fn if fn>1e-8 else f
    inst = {v.value_id: _align(gen, v.symbolic_core, fu) for v in vals}
    print(f"\n[B] CORE COHERENCE SIGNAL (gate: coherence_contribution >= 5.0)")
    print(f"    CURRENT signal (marginal sum): mean={st.mean(cc):+.2f} max={max(cc):+.2f} "
          f"→ values passing >=5.0: {sum(1 for x in cc if x>=5.0)}/{len(vals)}  (DEAD)")
    aa = [accum_align.get(v.value_id,0.0) for v in vals]
    print(f"    CANDIDATE accumulated-alignment: mean={st.mean(aa):.2f} max={max(aa):.2f} "
          f"→ would pass >=5.0: {sum(1 for x in aa if x>=5.0)}/{len(vals)}")
    print(f"    instantaneous alignment: mean={st.mean(list(inst.values())):.2f} "
          f"max={max(inst.values()):.2f}")
    print("    per-value (top by strength) — does a candidate DISCRIMINATE the anchors?")
    print(f"      {'symbol':<14}{'str':>6}{'reinf':>7}{'cc(old)':>9}{'inst_align':>11}{'accum_align':>12}")
    for v in sorted(vals, key=lambda x:-x.strength)[:10]:
        print(f"      {v.symbolic_core:<14}{v.strength:>6.2f}{v.reinforcement_count:>7}"
              f"{v.coherence_contribution:>9.2f}{inst.get(v.value_id,0):>11.3f}"
              f"{accum_align.get(v.value_id,0):>12.2f}")
    print("\n  (No change applied. Re-run after a calibration change to compare.)")
    print("="*78)
    return 0


if __name__ == "__main__":
    sys.exit(main())
