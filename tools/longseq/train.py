"""Contrastive pretrain for one cell of the long-sequence grid.

Same RhythmPretrainer recipe as tools/dim256/train_5rhythm.py: vocab 8192,
depth 4, heads 4, ff_mult 4, 20 epochs, batch 8, seed 0. The arm selects
the corpus. Short is the live v1.3.0 jsonl, read only. Other arms read
data/corpus/scratch/longseq/<arm>/.

Writes a new checkpoint. Refuses the live 128 names and last night's
dim-256 paired files.

    python -m tools.longseq.train --arm long --dim 256
"""
from __future__ import annotations

import argparse
import hashlib
import logging
import random
import sys
from pathlib import Path

import numpy as np
import torch

from agents.generator import Generator
from tools.dim256.geometry import dump_json, population, refuse_protected, separability
from training.corpus import HOLDOUT_PATH, TRAIN_PATH, load_corpus, to_rhythm_seeds
from training.rhythm_pretraining import PretrainingConfig, RhythmPretrainer

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

ROOT = Path(__file__).resolve().parents[2]
SCRATCH = ROOT / "data" / "corpus" / "scratch" / "longseq"
LOG_DIR = ROOT / "docs" / "findings" / "logs" / "2026-09-23-longseq"

# Last night's paired files are the short-cell record. Do not overwrite them.
ALSO_PROTECTED = {
    "generator_weights_5rhythm_256.pt",
    "generator_ecology_5rhythm_256.json",
    "generator_weights_5rhythm_128paired.pt",
    "generator_ecology_5rhythm_128paired.json",
    "decoder_5rhythm_256.pt",
}


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def _refuse(path: str) -> None:
    refuse_protected(path)
    if Path(path).name in ALSO_PROTECTED:
        raise SystemExit(f"refusing to overwrite a dim-256 paired artifact: {path}")


def _paths(arm: str) -> tuple[Path, Path]:
    if arm == "short":
        return TRAIN_PATH, HOLDOUT_PATH
    base = SCRATCH / arm
    return base / "rhythm_train.jsonl", base / "rhythm_holdout.jsonl"


def _encode(gen: Generator, records, batch: int = 256) -> np.ndarray:
    gen.eval()
    out = []
    for i in range(0, len(records), batch):
        out.append(gen.encode_batch([r["tokens"] for r in records[i:i + batch]]))
    return np.concatenate(out, axis=0).astype(np.float64)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", choices=("short", "long", "length", "vocab"), required=True)
    ap.add_argument("--dim", type=int, required=True)
    ap.add_argument("--epochs", type=int, default=20)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--batch-size", type=int, default=8)
    args = ap.parse_args()

    train_path, hold_path = _paths(args.arm)
    weights = f"data/checkpoints/longseq_{args.arm}_d{args.dim}.pt"
    ecology = f"data/checkpoints/longseq_{args.arm}_d{args.dim}.ecology.json"
    _refuse(weights)
    _refuse(ecology)
    report_path = LOG_DIR / f"train_{args.arm}_d{args.dim}.json"

    random.seed(args.seed)
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(args.seed)

    train = load_corpus(train_path)
    holdout = load_corpus(hold_path)
    print(
        f"arm={args.arm} train={len(train)} holdout={len(holdout)} "
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
        auto_decay_interval=None,
    )
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
    if any(v != v for v in pre.loss_history):  # NaN
        raise SystemExit(f"loss went NaN: {pre.loss_history}")
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
        "arm": args.arm,
        "train_sha256": _sha256(train_path),
        "holdout_sha256": _sha256(hold_path),
        "train_n": len(train),
        "holdout_n": len(holdout),
        "train_vocab": len(vocab_toks),
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
    dump_json(str(report_path), report)
    print(f"REPORT {report_path}", flush=True)
    print(
        f"worst_pair {sep['worst_pair']}  offdiag_mean {sep['offdiag_mean']}  "
        f"participation {pop['participation_ratio']}  "
        f"eff_rank {pop['eff_rank_512cap']}",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
