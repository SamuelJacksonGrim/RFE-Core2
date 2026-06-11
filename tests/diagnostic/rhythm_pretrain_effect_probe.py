"""
tests/diagnostic/rhythm_pretrain_effect_probe.py

Does training actually move generator diversity? First empirical data point
for the training path (docs/training/).

Pretrains the canonical-config generator (vocab 4096, dim 64, depth 3,
heads 4) with RhythmPretrainer on the built-in DEFAULT_RHYTHM_SEEDS, and
measures BEFORE vs AFTER, in eval mode (deterministic — the honest substrate
per 2026-06-08-generator-dropout-diversity.md; same metrics as
generator_diversity_audit.py):

  [seeds]   mean pairwise cosine, effective rank (participation ratio of
            singular values²), and rhythm nearest-neighbour accuracy
            (chance = 0.25) over the 20 rhythm seed sequences — the
            distribution actually trained on;
  [general] the same battery over random 1–3-token samples from a disjoint
            120-token vocabulary — the generalization control. The seeds do
            not cover these tokens, so movement here is NOT expected from
            seed-only training (that gap is the data-curation case).
  [control] determinism (same sequence ×5, eval) — must stay 1.0.

PRE-DECLARED READS
------------------
  TRAINS:     loss falls; seed rhythm_acc rises well above chance; seed
              eff_rank rises / mean cos falls. Training is a live lever.
  NARROW:     seed metrics move, general battery doesn't → the objective
              works but coverage is seed-limited; a curated corpus is the
              missing piece (expected for 20 sequences).
  INERT:      nothing moves → the trainer does not learn; training path
              claim fails.
  CONFOUNDED: determinism < 1.0 in eval → dropout leak; measurements
              contaminated (the 2026-06-08 trap).

Informational. exit 0. NEVER in run_all_tests.sh.

Run:
    python -m tests.diagnostic.rhythm_pretrain_effect_probe [n_epochs]
"""

from __future__ import annotations

import itertools
import logging
import random
import sys

import numpy as np

logging.disable(logging.CRITICAL)

import torch

from agents.generator import Generator
from training.rhythm_pretraining import (DEFAULT_RHYTHM_SEEDS,
                                         PretrainingConfig, RhythmPretrainer)

GENERAL_VOCAB = [f"tok_{i}" for i in range(120)]


def _unit(v):
    v = np.asarray(v, dtype=float)
    return v / (np.linalg.norm(v) + 1e-9)


def _spread(vecs: np.ndarray):
    """Mean pairwise cosine + effective rank (participation ratio of λ=s²)."""
    n = len(vecs)
    cs = [float(np.dot(vecs[i], vecs[j]))
          for i, j in itertools.combinations(range(n), 2)]
    lam = np.linalg.svd(vecs, compute_uv=False) ** 2
    eff_rank = float((lam.sum() ** 2) / (np.sum(lam ** 2) + 1e-12))
    return float(np.mean(cs)), eff_rank


def _seed_battery(g: Generator):
    """Eval-mode metrics over the 20 rhythm seed sequences."""
    g.eval()
    seqs, labels = [], []
    for rhythm, seed_seqs in DEFAULT_RHYTHM_SEEDS.items():
        for s in seed_seqs:
            seqs.append(s)
            labels.append(rhythm)
    vecs = np.array([_unit(g.generate(s)) for s in seqs])
    mean_cos, eff_rank = _spread(vecs)

    # rhythm nearest-neighbour accuracy (chance 0.25 with 4 balanced classes)
    sim = vecs @ vecs.T
    np.fill_diagonal(sim, -1.0)
    correct = sum(labels[int(np.argmax(sim[i]))] == labels[i]
                  for i in range(len(seqs)))
    return mean_cos, eff_rank, correct / len(seqs)


def _general_battery(g: Generator, n: int = 60, seed: int = 0):
    """Eval-mode metrics over random token samples from the disjoint vocab."""
    g.eval()
    rng = random.Random(seed)
    vecs = np.array([
        _unit(g.generate(rng.sample(GENERAL_VOCAB, rng.randint(1, 3))))
        for _ in range(n)
    ])
    return _spread(vecs)


def _determinism(g: Generator) -> float:
    g.eval()
    reps = np.array([_unit(g.generate(["tok_5"])) for _ in range(5)])
    return float(np.mean([np.dot(reps[i], reps[j])
                          for i, j in itertools.combinations(range(5), 2)]))


def main(n_epochs: int = 40) -> int:
    print('=' * 78)
    print('  DIAGNOSTIC: rhythm pretraining effect — does training move diversity?')
    print('=' * 78)
    print()

    random.seed(0)
    np.random.seed(0)
    torch.manual_seed(0)
    g = Generator(vocab_size=4096, dim=64, depth=3, heads=4)

    pre_seed = _seed_battery(g)
    pre_gen = _general_battery(g)
    pre_det = _determinism(g)

    trainer = RhythmPretrainer(g, config=PretrainingConfig(n_epochs=n_epochs))
    report = trainer.pretrain()

    post_seed = _seed_battery(g)
    post_gen = _general_battery(g)
    post_det = _determinism(g)

    print(f'  pretraining: epochs={report.epochs}  '
          f'loss {report.loss_history[0]:.4f} → {report.final_loss:.4f}  '
          f'final rhythm_acc={report.final_rhythm_acc:.3f}')
    print()
    print(f'  {"battery":<28} {"":>10} {"mean_cos":>9} {"eff_rank":>9} {"rhythm_acc":>11}')
    print(f'  {"[seeds] 20 rhythm seqs":<28} {"BEFORE":>10} {pre_seed[0]:>9.3f} '
          f'{pre_seed[1]:>9.1f} {pre_seed[2]:>11.2f}')
    print(f'  {"":<28} {"AFTER":>10} {post_seed[0]:>9.3f} '
          f'{post_seed[1]:>9.1f} {post_seed[2]:>11.2f}')
    print(f'  {"[general] disjoint vocab":<28} {"BEFORE":>10} {pre_gen[0]:>9.3f} '
          f'{pre_gen[1]:>9.1f} {"—":>11}')
    print(f'  {"":<28} {"AFTER":>10} {post_gen[0]:>9.3f} '
          f'{post_gen[1]:>9.1f} {"—":>11}')
    print()
    print(f'  [control] determinism (eval, same seq ×5): '
          f'before={pre_det:.3f} after={post_det:.3f}  (must be ~1.0)')
    print()

    if pre_det < 0.999 or post_det < 0.999:
        print('  READ: CONFOUNDED — eval-mode determinism broken; dropout leak.')
    elif post_seed[2] > 0.5 and post_seed[1] > pre_seed[1]:
        general_moved = abs(post_gen[1] - pre_gen[1]) > 0.5
        print('  READ: TRAINS — the objective restructures the trained '
              'distribution (seed eff_rank and rhythm clustering rise).')
        if not general_moved:
            print('        ...and NARROW — the disjoint-vocab battery is '
                  'unmoved, as pre-declared: 20 seed sequences cannot '
                  'restructure 120 unseen tokens. Coverage, not the '
                  'mechanism, is the binding constraint → curated corpus.')
    else:
        print('  READ: INERT — seed metrics did not move; the trainer does '
              'not learn on this objective.')
    print()
    return 0


if __name__ == '__main__':
    epochs = int(sys.argv[1]) if len(sys.argv) > 1 else 40
    sys.exit(main(epochs))
