"""
tools/ignition/train_ignite.py — the CII acceptance test for generator training.

Does training the generator on the in-repo corpus (data/corpus/) turn RFE's
expression-level ignition from an init lottery (locked for most random
generators) into a reliable property?

Paired by seed (same generator initialization in both arms): measure the
expression CII untrained vs after rhythm-pretraining. eval-mode in both (the
decided operating regime). The robust signal is the REGIME STATE
(locked -> metastable); the Cs scalar is the v0.1 operationalization.

    python -m tools.ignition.train_ignite [--epochs N] [--seeds 1,2,3]
"""
from __future__ import annotations

import argparse
import logging
import random
import sys

logging.disable(logging.CRITICAL)
sys.path.insert(0, ".")

import numpy as np
import torch

from tests._common import build_full_stack                       # noqa: E402
from tools.ignition.cii import compute_ignition, g as g_fn       # noqa: E402
from training.corpus import load_corpus, to_rhythm_seeds, TRAIN_PATH      # noqa: E402
from training.rhythm_pretraining import RhythmPretrainer, PretrainingConfig  # noqa: E402

VOCAB = ["resonance", "field", "engine", "memory", "crystal", "attractor",
         "identity", "continuity", "witness", "curiosity", "wonder", "exploration",
         "recursive", "cognition", "substrate", "dream", "wave", "collapse",
         "coherence", "symbolic", "ecology", "metabolism"]
SRC = [f"src_{i}" for i in range(4)]          # HHI<0.70


def _measure(cycle):
    rng = random.Random(999)
    rows = []
    for i in range(80):
        st = cycle.step(rng.sample(VOCAB, 3), source_id=SRC[i % 4], origin_type="internal")
        rows.append(compute_ignition(cycle, st))
    warm = rows[27:]
    R  = sum(x.R for x in warm) / len(warm)
    I  = sum(x.I for x in warm) / len(warm)
    Cm = sum(x.Cm for x in warm) / len(warm)
    r  = cycle.expression_metastability.compute_now()
    cii = R * I * (Cm * g_fn(float(r.metastability)))
    return r.regime_state, float(r.metastability), r.n_regimes, cii


def _build(seed):
    random.seed(seed); np.random.seed(seed); torch.manual_seed(seed)
    return build_full_stack()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--epochs", type=int, default=8)
    ap.add_argument("--seeds", default="1,2,3")
    args = ap.parse_args()
    seeds = [int(s) for s in args.seeds.split(",")]
    corpus_seeds = to_rhythm_seeds(load_corpus(TRAIN_PATH))

    print("=" * 78)
    print(f"  CII ACCEPTANCE TEST — does corpus training ignite the expression?")
    print(f"  (paired by seed; eval-mode; {args.epochs} epochs; expression-stream CII)")
    print("=" * 78)
    print(f"  seed | UNTRAINED                          | TRAINED")
    ign_u = ign_t = 0
    for seed in seeds:
        _g0, c0, _, _ = _build(seed); c0.generator.eval()
        us, um, un, uc = _measure(c0)

        g1, c1, _, _ = _build(seed)
        RhythmPretrainer(g1, rhythm_seeds=corpus_seeds,
                         config=PretrainingConfig(n_epochs=args.epochs)).pretrain()
        g1.eval()
        ts, tm, tn, tc = _measure(c1)

        ign_u += (us == "metastable"); ign_t += (ts == "metastable")
        print(f"   {seed}   | {us:11} meta={um:.3f} reg={un} CII={uc:5.2f} | "
              f"{ts:11} meta={tm:.3f} reg={tn} CII={tc:5.2f}")
    print("-" * 78)
    print(f"  ignited (expression metastable): untrained {ign_u}/{len(seeds)}  ->  trained {ign_t}/{len(seeds)}")
    print("=" * 78)
    return 0


if __name__ == "__main__":
    sys.exit(main())
