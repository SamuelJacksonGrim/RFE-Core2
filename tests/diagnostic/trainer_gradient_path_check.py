"""
tests/diagnostic/trainer_gradient_path_check.py

Structural validator for the training stack's gradient path — do the three
trainers actually backpropagate into the generator?

Generator.generate()/encode_batch() are @torch.no_grad() by design (inference
API). A trainer that builds its loss on their output severs the autograd graph:
backward() raises (`element 0 of tensors does not require grad`) and no weight
ever moves. This was the shipped state of SelfDistillationTrainer and
RhythmPretrainer until 2026-06-11 (ContrastiveAlignmentTrainer was the working
control — it routed through a grad-enabled forward). Recorded in
`docs/findings/2026-06-11-trainer-gradient-path.md`.

Three checks per trainer:
  1. train() / pretrain() completes without raising;
  2. generator weights actually change (max|ΔW| > 0 over all parameters);
  3. the caller's train/eval mode is restored afterward — the live-loop
     dropout policy is an open architect decision
     (2026-06-08-generator-dropout-diversity.md) and a trainer must not
     silently flip it.

Deterministic in structure (stochastic batches, but the assertions are
structural, not value-based). Exit 0 = all gradient paths intact, 1 = broken.

Run:
    python -m tests.diagnostic.trainer_gradient_path_check
"""

from __future__ import annotations

import logging
import sys

import numpy as np

logging.disable(logging.CRITICAL)

import torch

from agents.generator import Generator
from training.contrastive_alignment import ContrastiveAlignmentTrainer
from training.rhythm_pretraining import PretrainingConfig, RhythmPretrainer
from training.self_distillation import SelfDistillationTrainer


def _fresh(seed: int = 0) -> Generator:
    np.random.seed(seed)
    torch.manual_seed(seed)
    return Generator(vocab_size=256, dim=32, depth=1, heads=2)


def _snapshot(g: Generator):
    return [p.detach().clone() for p in g.parameters()]


def _max_delta(g: Generator, before) -> float:
    return max(
        float((p.detach() - b).abs().max())
        for p, b in zip(g.parameters(), before)
    )


def _unit(rng, dim: int) -> np.ndarray:
    v = rng.normal(size=dim).astype(np.float32)
    return v / np.linalg.norm(v)


def _check(name: str, run_fn, build_fn) -> bool:
    """Run one trainer in both caller modes; verify grads flow + mode restored."""
    ok = True
    for caller_mode in ("train", "eval"):
        g, trainer = build_fn()
        g.train(caller_mode == "train")
        before = _snapshot(g)
        try:
            run_fn(trainer)
        except Exception as e:
            print(f'  ✗ {name:<24} [{caller_mode}-mode caller] raised '
                  f'{type(e).__name__}: {e}')
            ok = False
            continue
        delta = _max_delta(g, before)
        moved = delta > 0.0
        restored = g.training == (caller_mode == "train")
        mark = '✓' if (moved and restored) else '✗'
        print(f'  {mark} {name:<24} [{caller_mode}-mode caller] '
              f'max|ΔW|={delta:.2e}  mode_restored={restored}')
        ok = ok and moved and restored
    return ok


def main() -> int:
    print('=' * 72)
    print('  DIAGNOSTIC: trainer gradient-path check  (training stack)')
    print('=' * 72)
    print()

    rng = np.random.default_rng(0)

    def build_distill():
        g = _fresh()
        t = SelfDistillationTrainer(g, batch_size=4, max_steps_per_call=1)
        for i in range(8):
            t.collect([f"tok{i}", f"tok{i + 1}"], _unit(rng, 32), coherence=0.9)
        return g, t

    def build_contrastive():
        g = _fresh()
        t = ContrastiveAlignmentTrainer(
            g, batch_size=2, n_positives=1, n_negatives=2, max_steps_per_call=1,
        )
        rhythms = ["stabilize", "dream", "reflect", "explore"]
        for i in range(16):
            t.collect([f"tok{i}", f"tok{(i * 3) % 16}"], _unit(rng, 32),
                      rhythm=rhythms[i % 4], coherence=0.8)
        return g, t

    def build_rhythm():
        g = _fresh()
        t = RhythmPretrainer(g, config=PretrainingConfig(n_epochs=1, batch_size=8))
        return g, t

    all_ok = True
    all_ok &= _check('SelfDistillationTrainer', lambda t: t.train(), build_distill)
    all_ok &= _check('ContrastiveAlignment', lambda t: t.train(), build_contrastive)
    all_ok &= _check('RhythmPretrainer', lambda t: t.pretrain(), build_rhythm)

    print()
    if all_ok:
        print('GRADIENT PATHS INTACT — all three trainers backpropagate into the '
              'generator and restore the caller\'s mode.')
        return 0
    print('GRADIENT PATH BROKEN — see ✗ rows above.')
    return 1


if __name__ == '__main__':
    sys.exit(main())
