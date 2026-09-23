"""Train the completion objective. Writes new checkpoint files only.

    python -m tools.completion.train --dim 128 --epochs 20 --seed 0
    python -m tools.completion.train --dim 256 --epochs 20 --seed 0

Refuses the live 128 names and the contrastive dim-256 baselines.
"""

from __future__ import annotations

import argparse
import logging
import random
import sys
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F

from agents.generator import Generator
from tools.completion.corpus import content_of, load_jsonl
from tools.completion.geometry import dump_json, encode_texts, population
from tools.completion.live_guard import REPO, assert_live_intact, refuse_protected
from training.completion import (
    COND_SCALE,
    CompletionConfig,
    CompletionHead,
    CompletionTrainer,
    RHYTHM_LOSS_WEIGHT,
    pack_targets,
)
from training.corpus import HOLDOUT_PATH, RHYTHMS, TRAIN_PATH, corpus_version, load_corpus

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

SCRATCH = REPO.parent / "scratch" / "completion"


def _content_vocab(records) -> list[str]:
    words = {t for rec in records for t in content_of(rec["tokens"])}
    return sorted(words)


def _optimizer_holds_embedding(optimizer, generator) -> bool:
    ids = {id(p) for group in optimizer.param_groups for p in group["params"]}
    return id(generator.embedding.weight) in ids


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dim", type=int, required=True)
    ap.add_argument("--epochs", type=int, default=20)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--batch-size", type=int, default=128)
    ap.add_argument("--rhythm-weight", type=float, default=None)
    ap.add_argument("--cond-scale", type=float, default=None)
    ap.add_argument("--lr", type=float, default=1e-3)
    ap.add_argument("--weight-decay", type=float, default=1e-5)
    ap.add_argument("--tag", default="", help="filename suffix, e.g. _cbow")
    ap.add_argument(
        "--embeddings-only",
        action="store_true",
        help="freeze the transformer and the projection; train token embeddings and the head",
    )
    ap.add_argument("--train-rows", default=str(SCRATCH / "completion_train.jsonl"))
    ap.add_argument("--hold-rows", default=str(SCRATCH / "completion_holdout.jsonl"))
    args = ap.parse_args()

    live = assert_live_intact()
    tag = args.tag
    weights = f"data/checkpoints/generator_weights_completion_{args.dim}{tag}.pt"
    ecology = f"data/checkpoints/generator_ecology_completion_{args.dim}{tag}.json"
    head_path = f"data/checkpoints/completion_head_{args.dim}{tag}.pt"
    rhythm_weight = RHYTHM_LOSS_WEIGHT if args.rhythm_weight is None else args.rhythm_weight
    cond_scale = COND_SCALE if args.cond_scale is None else args.cond_scale
    for path in (weights, ecology, head_path):
        refuse_protected(path)

    random.seed(args.seed)
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(args.seed)

    live_train = load_corpus(TRAIN_PATH)
    live_hold = load_corpus(HOLDOUT_PATH)
    rows = load_jsonl(Path(args.train_rows))
    hold_rows = load_jsonl(Path(args.hold_rows))
    vocab = _content_vocab(live_train)
    missing = sorted({w for r in rows for w in r["targets"] if w not in set(vocab)})
    if missing:
        raise SystemExit(f"train target outside content vocab: {missing[:6]}")

    print(
        f"corpus v{corpus_version()} completion-train={len(rows)} "
        f"completion-hold={len(hold_rows)} content_vocab={len(vocab)} "
        f"dim={args.dim} epochs={args.epochs} seed={args.seed} "
        f"rhythm_weight={rhythm_weight} cond_scale={cond_scale} "
        f"lr={args.lr} wd={args.weight_decay} "
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
    # Register before AdamW binds, including glue the context still embeds.
    surface = sorted({t for rec in live_train for t in rec["tokens"]})
    gen.eval()
    gen.encode_batch([[t] for t in surface])
    if args.embeddings_only:
        for name, param in gen.named_parameters():
            if not name.startswith("embedding."):
                param.requires_grad = False
        frozen = sum(not p.requires_grad for p in gen.parameters())
        print(f"embeddings-only: froze {frozen} tensors", flush=True)
    print(
        f"registered {len(surface)} surface tokens; "
        f"embedding {tuple(gen.embedding.weight.shape)} device={gen.device}",
        flush=True,
    )

    rhythm_index = {name: i for i, name in enumerate(RHYTHMS)}
    head = CompletionHead(vocab, args.dim, len(RHYTHMS), gen.device)
    trainer = CompletionTrainer(
        gen,
        head,
        CompletionConfig(
            n_epochs=args.epochs,
            batch_size=args.batch_size,
            log_interval=1,
            learning_rate=args.lr,
            weight_decay=args.weight_decay,
            rhythm_weight=rhythm_weight,
            cond_scale=cond_scale,
        ),
    )
    if not _optimizer_holds_embedding(trainer.optimizer, gen):
        raise SystemExit("optimizer is not bound to the live embedding; aborting")

    # Same cloud the contrastive run was scored on: the live holdout lines.
    history = []

    def snapshot(epoch_done: int) -> None:
        gen.eval()
        head.eval()
        Z = encode_texts(gen, [r["tokens"] for r in live_hold])
        pop = population(Z)
        Zctx = encode_texts(gen, [r["context"] for r in hold_rows])
        pop_ctx = population(Zctx)
        word_ce = _holdout_word_ce(
            gen, head, hold_rows, rhythm_index, trainer.config.cond_scale,
        )
        snap = {
            "epoch": epoch_done,
            "live_holdout_participation": pop["participation_ratio"],
            "live_holdout_eff_rank": pop["eff_rank_512cap"],
            "context_holdout_participation": pop_ctx["participation_ratio"],
            "context_holdout_eff_rank": pop_ctx["eff_rank_512cap"],
            "completion_holdout_word_ce": word_ce,
        }
        history.append(snap)
        print(
            f"snap epoch {epoch_done}  PR {pop['participation_ratio']}  "
            f"eff {pop['eff_rank_512cap']}  ctx_PR {pop_ctx['participation_ratio']}  "
            f"hold_word_ce {word_ce}",
            flush=True,
        )

    snapshot(0)
    pre = trainer.pretrain(rows, rhythm_index, on_epoch_end=snapshot)

    if not _optimizer_holds_embedding(trainer.optimizer, gen):
        raise SystemExit("embedding was resized out from under the optimizer")

    gen.eval()
    head.eval()
    Path(weights).parent.mkdir(parents=True, exist_ok=True)
    gen.save_checkpoint(weights, ecology)
    torch.save(
        {
            "state_dict": head.state_dict(),
            "vocab": head.vocab,
            "rhythms": list(RHYTHMS),
            "dim": args.dim,
            "cond_scale": trainer.config.cond_scale,
            "rhythm_weight": trainer.config.rhythm_weight,
        },
        head_path,
    )
    print(f"SAVED {weights}", flush=True)
    print(f"SAVED {ecology}", flush=True)
    print(f"SAVED {head_path}", flush=True)

    report = {
        "objective": "completion",
        "corpus_version": corpus_version(),
        "dim": args.dim,
        "epochs": args.epochs,
        "seed": args.seed,
        "batch_size": args.batch_size,
        "learning_rate": args.lr,
        "weight_decay": args.weight_decay,
        "embeddings_only": args.embeddings_only,
        "cond_scale": trainer.config.cond_scale,
        "rhythm_weight": trainer.config.rhythm_weight,
        "content_vocab": len(vocab),
        "train_rows": len(rows),
        "hold_rows": len(hold_rows),
        "device": str(gen.device),
        "torch": torch.__version__,
        "final_loss": pre.final_loss,
        "final_word_ce": pre.final_word_ce,
        "final_train_rhythm_acc": pre.final_rhythm_acc,
        "loss_history": pre.loss_history,
        "word_ce_history": pre.word_ce_history,
        "rhythm_acc_history": pre.rhythm_acc_history,
        "snapshots": history,
        "weights": weights,
        "ecology": ecology,
        "head": head_path,
        "live_sha256": live,
    }
    suffix = tag if tag else ""
    out = (
        f"docs/findings/logs/2026-09-23-completion/"
        f"train_dim{args.dim}{suffix}_s{args.seed}.json"
    )
    dump_json(out, report)
    assert_live_intact()
    print(f"REPORT {out}", flush=True)
    return 0


@torch.no_grad()
def _holdout_word_ce(gen, head, rows, rhythm_index, cond_scale: float) -> float | None:
    """Co-trained head, word term only, on the completion holdout."""
    if not rows:
        return None
    device = gen.device
    total = 0.0
    seen = 0
    for start in range(0, len(rows), 256):
        batch = rows[start:start + 256]
        rhythm_ids = torch.tensor(
            [rhythm_index[r["rhythm"]] for r in batch], dtype=torch.long, device=device,
        )
        h = torch.tensor(
            gen.encode_batch([r["context"] for r in batch]),
            dtype=torch.float32,
            device=device,
        )
        code = F.normalize(head.rhythm_embed(rhythm_ids), dim=-1)
        conditioned = F.normalize(h + cond_scale * code, dim=-1)
        logits = head.head(conditioned)
        target = pack_targets([r["target_dist"] for r in batch], head.index, device)
        word = -(target * torch.log_softmax(logits, dim=-1)).sum(dim=-1)
        total += float(word.sum())
        seen += len(batch)
    return round(total / max(seen, 1), 4)


if __name__ == "__main__":
    sys.exit(main())
