"""Fresh contrastive pretrain of the live 5-rhythm encoder at a chosen dim.

Same corpus, same RhythmPretrainer objective, same architecture
(vocab 8192, depth 4, heads 4, ff_mult 4) as the production boot path.
Dimension is the only intended variable.

Writes a NEW checkpoint. Refuses the live 128D filenames.

    python -m tools.dim256.train_5rhythm --dim 256 --epochs 20 --seed 0
"""
from __future__ import annotations

import argparse
import json
import logging
import random
import sys
from pathlib import Path

import numpy as np
import torch

from agents.generator import Generator
from tools.dim256.geometry import dump_json, population, refuse_protected, separability
from training.corpus import (
    HOLDOUT_PATH,
    TRAIN_PATH,
    corpus_version,
    load_corpus,
    to_rhythm_seeds,
)
from training.rhythm_pretraining import PretrainingConfig, RhythmPretrainer

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


def _encode(gen: Generator, records, batch: int = 256) -> np.ndarray:
    gen.eval()
    out = []
    for i in range(0, len(records), batch):
        out.append(gen.encode_batch([r["tokens"] for r in records[i:i + batch]]))
    return np.concatenate(out, axis=0).astype(np.float64)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dim", type=int, required=True)
    ap.add_argument("--epochs", type=int, default=20)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--batch-size", type=int, default=8)
    ap.add_argument(
        "--weights",
        default="",
        help="output .pt (default data/checkpoints/generator_weights_5rhythm_<dim>.pt)",
    )
    ap.add_argument("--ecology", default="")
    ap.add_argument(
        "--report",
        default="",
        help="JSON readout path (default docs/findings/logs/2026-09-23-dim256/train_dim<dim>.json)",
    )
    args = ap.parse_args()

    tag = f"{args.dim}"
    weights = args.weights or f"data/checkpoints/generator_weights_5rhythm_{tag}.pt"
    ecology = args.ecology or f"data/checkpoints/generator_ecology_5rhythm_{tag}.json"
    refuse_protected(weights)
    refuse_protected(ecology)

    report_path = args.report or (
        f"docs/findings/logs/2026-09-23-dim256/train_dim{args.dim}_s{args.seed}.json"
    )

    random.seed(args.seed)
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(args.seed)

    train = load_corpus(TRAIN_PATH)
    holdout = load_corpus(HOLDOUT_PATH)
    version = corpus_version()
    print(
        f"corpus v{version} train={len(train)} holdout={len(holdout)} "
        f"dim={args.dim} epochs={args.epochs} seed={args.seed} "
        f"device={'cuda' if torch.cuda.is_available() else 'cpu'}",
        flush=True,
    )

    gen = Generator(
        vocab_size=8192,
        dim=args.dim,
        depth=4,
        heads=4,
        ff_mult=4,
        dropout=0.1,
        # Offline pretrain: do not reap the corpus mid-pass. The live loop's
        # maintenance interval is a runtime concern, not part of the objective.
        auto_decay_interval=None,
    )
    # Register corpus tokens BEFORE AdamW binds parameters, so a resize
    # cannot orphan the optimizer onto a stale embedding.
    vocab_toks = sorted({t for rec in train for t in rec["tokens"]})
    gen.encode_batch([[t] for t in vocab_toks])
    print(
        f"registered {len(vocab_toks)} train tokens; "
        f"embedding {tuple(gen.embedding.weight.shape)} device={gen.device}",
        flush=True,
    )

    trainer = RhythmPretrainer(
        gen,
        rhythm_seeds=to_rhythm_seeds(train),
        config=PretrainingConfig(
            n_epochs=args.epochs,
            batch_size=args.batch_size,
            log_interval=5,
        ),
    )
    opt_ids = {id(p) for g in trainer.optimizer.param_groups for p in g["params"]}
    if id(gen.embedding.weight) not in opt_ids:
        raise SystemExit("optimizer is not bound to the live embedding; aborting")

    pre = trainer.pretrain()
    gen.eval()

    Zho = _encode(gen, holdout)
    labels = [r["rhythm"] for r in holdout]
    sep = separability(Zho, labels)
    pop = population(Zho)

    Path(weights).parent.mkdir(parents=True, exist_ok=True)
    gen.save_checkpoint(weights, ecology)
    print(f"SAVED {weights}", flush=True)
    print(f"SAVED {ecology}", flush=True)

    report = {
        "corpus_version": version,
        "train_n": len(train),
        "holdout_n": len(holdout),
        "dim": args.dim,
        "epochs": args.epochs,
        "seed": args.seed,
        "batch_size": args.batch_size,
        "device": str(gen.device),
        "torch": torch.__version__,
        "final_loss": pre.final_loss,
        "final_rhythm_acc": pre.final_rhythm_acc,
        "loss_history": pre.loss_history,
        "weights": weights,
        "ecology": ecology,
        "holdout_population": pop,
        "holdout_separability": sep,
    }
    dump_json(report_path, report)
    print(f"REPORT {report_path}", flush=True)
    print(
        f"worst_pair {sep['worst_pair']}  offdiag_mean {sep['offdiag_mean']}  "
        f"participation {pop['participation_ratio']}  "
        f"quiet {pop['quiet_dims_lt_1pct_median']}/{pop['dim']}  "
        f"dead {pop['dead_dims_std_lt_1e-3']}",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
