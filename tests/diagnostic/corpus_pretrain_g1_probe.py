"""
tests/diagnostic/corpus_pretrain_g1_probe.py

Gate G1 — held-out generalization of corpus pretraining (Phase 1 of
docs/training/training_plan.md).

Pretrains the canonical-config generator (vocab 4096, dim 64, depth 3,
heads 4) with RhythmPretrainer on the curated corpus TRAIN split
(data/corpus/rhythm_train.jsonl), then reads every metric on the HOLDOUT
split — sequences never trained on, tokens fully inside the train
vocabulary — in eval mode (the honest deterministic substrate per
2026-06-08-generator-dropout-diversity.md). Metrics as in
generator_diversity_audit.py / rhythm_pretrain_effect_probe.py.

GATE G1 (pre-declared in training_plan.md BEFORE any corpus run):
  PASS requires ALL of:
    - holdout eff_rank (eval) >= 2x the untrained baseline
    - holdout rhythm-NN accuracy >= 0.75 (chance 0.25)
    - determinism = 1.0 (>= 0.999; eval, same sequence x5)
    - embedding norms bounded: max row norm grows < 10x over training
  FAIL = within-vocabulary generalization doesn't happen -> revisit corpus
  design before touching anything else.

Exit 0 = gate passed, 1 = gate failed. Run deliberately (minutes of CPU
training, init-dependent); NEVER in run_all_tests.sh. Findings produced from
this probe must name the corpus version it ran on.

Run:
    python -m tests.diagnostic.corpus_pretrain_g1_probe [n_epochs] [--seed N] [--save]

    --seed  generator init seed (default 0); replicate at a second seed
            before recording a finding — the absolute numbers are
            init-dependent, the gate should not be.
    --save  writes the pretrained boot checkpoint to data/checkpoints/
            (generator.save_checkpoint) for Phase 2 reuse.
"""

from __future__ import annotations

import itertools
import logging
import random
import sys
from pathlib import Path

import numpy as np

logging.disable(logging.CRITICAL)

import torch

from agents.generator import Generator
from training.corpus import (HOLDOUT_PATH, TRAIN_PATH, corpus_version,
                             load_corpus, to_rhythm_seeds)
from training.rhythm_pretraining import PretrainingConfig, RhythmPretrainer

CHECKPOINT_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "checkpoints"


def _unit(v):
    v = np.asarray(v, dtype=float)
    return v / (np.linalg.norm(v) + 1e-9)


def _holdout_battery(g: Generator, records):
    """Eval-mode mean_cos / eff_rank / rhythm-NN accuracy over holdout."""
    g.eval()
    seqs = [r["tokens"] for r in records]
    labels = [r["rhythm"] for r in records]
    vecs = np.array([_unit(v) for v in g.encode_batch(seqs)])

    lam = np.linalg.svd(vecs, compute_uv=False) ** 2
    eff_rank = float((lam.sum() ** 2) / (np.sum(lam ** 2) + 1e-12))

    sim = vecs @ vecs.T
    mean_cos = float((sim.sum() - len(seqs)) / (len(seqs) * (len(seqs) - 1)))
    np.fill_diagonal(sim, -1.0)
    correct = sum(labels[int(np.argmax(sim[i]))] == labels[i]
                  for i in range(len(seqs)))
    return mean_cos, eff_rank, correct / len(seqs)


def _determinism(g: Generator, seq) -> float:
    g.eval()
    reps = np.array([_unit(g.generate(list(seq))) for _ in range(5)])
    return float(np.mean([np.dot(reps[i], reps[j])
                          for i, j in itertools.combinations(range(5), 2)]))


def _max_embedding_norm(g: Generator) -> float:
    with torch.no_grad():
        return float(g.embedding.weight.norm(dim=-1).max())


def main(n_epochs: int = 8, save: bool = False, seed: int = 0) -> int:
    version = corpus_version()
    print('=' * 78)
    print(f'  DIAGNOSTIC: Gate G1 — corpus pretraining, held-out generalization')
    print(f'  corpus v{version}  ·  epochs={n_epochs}  ·  seed={seed}  ·  eval-mode readout')
    print('=' * 78)
    print()

    train_recs = load_corpus(TRAIN_PATH)
    holdout_recs = load_corpus(HOLDOUT_PATH)
    print(f'  train={len(train_recs)} seqs  holdout={len(holdout_recs)} seqs '
          f'(sequences never trained on, tokens in train vocabulary)')
    print()

    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    g = Generator(vocab_size=4096, dim=64, depth=3, heads=4)

    pre = _holdout_battery(g, holdout_recs)
    pre_det = _determinism(g, holdout_recs[0]["tokens"])
    pre_norm = _max_embedding_norm(g)

    trainer = RhythmPretrainer(
        g,
        rhythm_seeds=to_rhythm_seeds(train_recs),
        config=PretrainingConfig(n_epochs=n_epochs),
    )
    report = trainer.pretrain()

    post = _holdout_battery(g, holdout_recs)
    post_det = _determinism(g, holdout_recs[0]["tokens"])
    post_norm = _max_embedding_norm(g)

    print(f'  pretraining: epochs={report.epochs}  '
          f'loss {report.loss_history[0]:.4f} → {report.final_loss:.4f}  '
          f'train-side rhythm_acc={report.final_rhythm_acc:.3f}')
    print()
    print(f'  {"HOLDOUT (eval)":<22} {"mean_cos":>9} {"eff_rank":>9} {"rhythm_acc":>11}')
    print(f'  {"BEFORE (untrained)":<22} {pre[0]:>9.3f} {pre[1]:>9.2f} {pre[2]:>11.3f}')
    print(f'  {"AFTER":<22} {post[0]:>9.3f} {post[1]:>9.2f} {post[2]:>11.3f}')
    print()
    print(f'  determinism: before={pre_det:.4f} after={post_det:.4f}')
    print(f'  max embedding row norm: before={pre_norm:.3f} after={post_norm:.3f} '
          f'({post_norm / max(pre_norm, 1e-9):.1f}x)')
    print()

    gates = [
        (post[1] >= 2.0 * pre[1],
         f'eff_rank >= 2x untrained baseline ({post[1]:.2f} vs 2x{pre[1]:.2f}={2*pre[1]:.2f})'),
        (post[2] >= 0.75,
         f'rhythm-NN accuracy >= 0.75 ({post[2]:.3f}, chance 0.25)'),
        (pre_det >= 0.999 and post_det >= 0.999,
         f'determinism = 1.0 ({pre_det:.4f} / {post_det:.4f})'),
        (post_norm < 10.0 * pre_norm,
         f'embedding norms bounded, growth < 10x ({post_norm/max(pre_norm,1e-9):.1f}x)'),
    ]
    all_ok = True
    print('  GATE G1:')
    for ok, label in gates:
        print(f'    {"✓" if ok else "✗"} {label}')
        all_ok &= ok
    print()

    if save:
        CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)
        stem = CHECKPOINT_DIR / f'boot_rhythm_corpus_v{version}_{n_epochs}ep_s{seed}'
        g.save_checkpoint(str(stem) + '.pt', str(stem) + '.ecology.json')
        print(f'  checkpoint saved: {stem}.pt / .ecology.json')
        print()

    print(f'  GATE G1 {"PASSED" if all_ok else "FAILED"} — corpus v{version}, '
          f'{n_epochs} epochs, seed {seed}.')
    if not all_ok:
        print('  Per training_plan.md: within-vocabulary generalization did not '
              'happen → revisit corpus design before touching anything else.')
    print()
    return 0 if all_ok else 1


if __name__ == '__main__':
    args = [a for a in sys.argv[1:]]
    save_flag = '--save' in args
    args = [a for a in args if a != '--save']
    seed_val = 0
    if '--seed' in args:
        i = args.index('--seed')
        seed_val = int(args[i + 1])
        del args[i:i + 2]
    epochs = int(args[0]) if args else 8
    sys.exit(main(epochs, save=save_flag, seed=seed_val))
