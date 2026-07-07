"""
tests/diagnostic/calibration/rhythm_band_equilibria_probe.py

Measure each rhythm band's SELF-CONSISTENT EQUILIBRIUM ENERGY by pinning the
classifier so one band's dynamics run unconditionally in the composed stack.

Why this exists (F9): the rhythm thresholds feed back into the energy that
classifies them — stabilize diffuses the field (energy sink), explore injects
extra mutation (energy source) — so bands cannot be calibrated against an
energy distribution measured under the old bands (the 2026-06-27 naive rescale
collapsed the system into a stabilize basin exactly this way). The pinned-run
equilibria turn that circularity into a constraint set:

  - stabilize threshold BELOW its pinned equilibrium → self-terminates upward
    (no warmup trap);
  - dream band below its equilibrium → a passage, climbs out;
  - reflect band containing its equilibrium → the home base;
  - explore threshold at/above its equilibrium → a reachable burst, not a basin.

Re-run this probe BEFORE retuning any threshold in
`ResonanceField.DEFAULT_THRESHOLDS` / `configs/field.yaml` — the equilibria are
workload- and dynamics-dependent, so any change to decay, diffuse_alpha,
injection strengths, or band behaviors moves them.
(finding: docs/findings/2026-07-06-f9-rhythm-band-rescale.md)

Informational; exit 0; NEVER in run_all_tests.sh.
"""
import sys, logging, random
import numpy as np

logging.disable(logging.CRITICAL)
sys.path.insert(0, ".")

from agents.generator import Generator                      # noqa: E402
from agents.selfhood_governance import SelfhoodGovernance   # noqa: E402
from agents.value_emergence import ValueEmergenceEngine     # noqa: E402
from loop.autonomous_cycle import AutonomousCycle           # noqa: E402
from cognition.stream_recorder import StreamRecorder        # noqa: E402

SOURCES = {
    "source_a": [["identity","continuity","witness"],["anchor","recursion","homeostasis"],["architect","design","intent"]],
    "source_b": [["recursive","cognition","substrate"],["coherence","integration","synthesis"],["watcher","witness","mirror"]],
    "source_c": [["memory","crystal","attractor"],["relational","bond","connection"],["temporal","stream","continuity"]],
    "source_d": [["mutation","bifurcation","chaos"],["explore","novelty","edge"],["wave","collapse","coherence"]],
}
WEIGHTS = {"source_a":0.40,"source_b":0.25,"source_c":0.20,"source_d":0.15}

# Threshold pins: force the classifier to one band regardless of energy.
PINS = {
    "stabilize": {"stabilize": 1e9, "dream": 1e9, "reflect": 1e9},
    "dream":     {"stabilize": 0.0, "dream": 1e9, "reflect": 1e9},
    "reflect":   {"stabilize": 0.0, "dream": 0.0, "reflect": 1e9},
    "explore":   {"stabilize": 0.0, "dream": 0.0, "reflect": 0.0},
}

STEPS = 400
TAIL  = 100   # equilibrium = stats over the last TAIL steps


def build(dim: int, seed: int):
    random.seed(seed); np.random.seed(seed)
    import torch; torch.manual_seed(seed)
    gen = Generator(vocab_size=8192, dim=dim, depth=4, heads=4)
    from training.corpus import load_corpus, to_rhythm_seeds, TRAIN_PATH
    from training.rhythm_pretraining import RhythmPretrainer, PretrainingConfig
    RhythmPretrainer(gen, rhythm_seeds=to_rhythm_seeds(load_corpus(TRAIN_PATH)),
                     config=PretrainingConfig(n_epochs=8)).pretrain()
    gen.eval()
    cycle = AutonomousCycle(generator=gen, dim=dim, use_chorus=True,
                            log_interval=999999, reflect_novelty_attenuation=True)
    gov = SelfhoodGovernance(registry=gen.registry); cycle.attach_governance(gov)
    ve = ValueEmergenceEngine(registry=gen.registry, generator=gen, governance=gov)
    cycle.attach_value_engine(ve)
    cycle.attach_stream_recorder(StreamRecorder(window=STEPS))
    return cycle


def run_pinned(dim: int, band: str, seed: int = 42):
    cycle = build(dim, seed)
    cycle.field.thresholds = dict(cycle.field.thresholds, **PINS[band])
    rng = random.Random(1188)
    sids = list(SOURCES); w = [WEIGHTS[s] for s in sids]
    energies = []
    for _ in range(STEPS):
        s = rng.choices(sids, weights=w)[0]
        cycle.step(rng.choice(SOURCES[s]), source_id=s, origin_type="internal")
        energies.append(cycle.field.observe().energy)
    d = cycle.stream_recorder.snapshot()["decisions"]
    allows = sum(d.get(k, 0) for k in ("ALLOW", "ALLOW_WEAKENED", "MONITOR"))
    e = np.array(energies); tail = e[-TAIL:]
    return {
        "band": band, "dim": dim,
        "eq_mean": float(tail.mean()), "eq_min": float(tail.min()),
        "eq_max": float(tail.max()),
        "traj_max": float(e.max()),
        "e_at_50": float(e[49]), "e_at_100": float(e[99]), "e_at_200": float(e[199]),
        "allow_rate": allows / STEPS,
    }


def main() -> int:
    for dim in (128, 64):
        print(f"\n===== dim {dim} =====")
        print(f"{'band':<10}{'eq_mean':>9}{'eq_min':>9}{'eq_max':>9}{'traj_max':>10}"
              f"{'E@50':>8}{'E@100':>8}{'E@200':>8}{'allow':>7}")
        for band in ("stabilize", "dream", "reflect", "explore"):
            r = run_pinned(dim, band)
            print(f"{r['band']:<10}{r['eq_mean']:>9.1f}{r['eq_min']:>9.1f}{r['eq_max']:>9.1f}"
                  f"{r['traj_max']:>10.1f}{r['e_at_50']:>8.1f}{r['e_at_100']:>8.1f}"
                  f"{r['e_at_200']:>8.1f}{r['allow_rate']:>7.2f}")
            sys.stdout.flush()
    print("\n(Informational. Compare against the table in "
          "docs/findings/2026-07-06-f9-rhythm-band-rescale.md before retuning bands.)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
