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
from tools.completion.geometry import (
    dump_json,
    embedding_means,
    encode_texts,
    mean_cosine,
    population,
)
from tools.completion.live_guard import REPO, assert_live_intact, refuse_protected
from tools.completion.measure import completion_scores
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
    ap.add_argument(
        "--residual",
        action="store_true",
        help="field vector keeps an orthogonal residual of the embedding mean; "
             "the transformer reads detached embeddings and cannot cancel that direction",
    )
    ap.add_argument(
        "--legibility",
        action="store_true",
        help="at the end, train the phase-0 mouth on the live lines",
    )
    ap.add_argument(
        "--final-probe",
        action="store_true",
        help="at the end, fit a fresh linear completion probe on frozen context vectors",
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
    if args.embeddings_only and args.residual:
        raise SystemExit("pick one of --embeddings-only or --residual")
    gen.embedding_residual = bool(args.residual)
    if args.embeddings_only:
        for name, param in gen.named_parameters():
            if not name.startswith("embedding."):
                param.requires_grad = False
        frozen = sum(not p.requires_grad for p in gen.parameters())
        print(f"embeddings-only: froze {frozen} tensors", flush=True)
    if args.residual:
        print(
            "residual: orthogonal embedding-mean mix, transformer input detached",
            flush=True,
        )
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
        points = _measure_points(gen, [r["tokens"] for r in live_hold])
        pop = points["output"]
        Zctx = encode_texts(gen, [r["context"] for r in hold_rows])
        pop_ctx = population(Zctx)
        hold_read = _completion_readout(
            gen, head, hold_rows, rhythm_index, trainer.config.cond_scale,
        )
        train_read = _completion_readout(
            gen, head, rows, rhythm_index, trainer.config.cond_scale,
        )
        word_ce = None if hold_read is None else hold_read["ce"]
        snap = {
            "epoch": epoch_done,
            "live_holdout_participation": pop["participation_ratio"],
            "live_holdout_eff_rank": pop["eff_rank_512cap"],
            "live_holdout_embedding_participation": points["embedding_mean"]["participation_ratio"],
            "live_holdout_embedding_eff_rank": points["embedding_mean"]["eff_rank_512cap"],
            "live_holdout_stack_participation": points["stack"]["participation_ratio"],
            "live_holdout_stack_eff_rank": points["stack"]["eff_rank_512cap"],
            "live_holdout_cos_stack_emb": points["cos_stack_emb"],
            "live_holdout_cos_output_emb": points["cos_output_emb"],
            "context_holdout_participation": pop_ctx["participation_ratio"],
            "context_holdout_eff_rank": pop_ctx["eff_rank_512cap"],
            "completion_holdout_word_ce": word_ce,
            "completion_holdout_mode_top1": None if hold_read is None else hold_read["mode_top1"],
            "completion_holdout_support_recall@8": (
                None if hold_read is None else hold_read["support_recall@8"]
            ),
            "completion_holdout_by_split": None if hold_read is None else hold_read.get("by_split"),
            "completion_train_mode_top1": None if train_read is None else train_read["mode_top1"],
            "completion_train_word_ce": None if train_read is None else train_read["ce"],
        }
        history.append(snap)
        similar = (snap["completion_holdout_by_split"] or {}).get("similar") or {}
        print(
            f"snap epoch {epoch_done}  "
            f"out_PR {pop['participation_ratio']}  "
            f"emb_PR {points['embedding_mean']['participation_ratio']}  "
            f"stack_PR {points['stack']['participation_ratio']}  "
            f"cos_out_emb {points['cos_output_emb']}  "
            f"ctx_PR {pop_ctx['participation_ratio']}  "
            f"hold_ce {word_ce}  hold_top1 {snap['completion_holdout_mode_top1']}  "
            f"similar_top1 {similar.get('mode_top1')}  "
            f"train_top1 {snap['completion_train_mode_top1']}",
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
            "embedding_residual": bool(args.residual),
            "cond_scale": trainer.config.cond_scale,
            "rhythm_weight": trainer.config.rhythm_weight,
        },
        head_path,
    )
    print(f"SAVED {weights}", flush=True)
    print(f"SAVED {ecology}", flush=True)
    print(f"SAVED {head_path}", flush=True)

    extras = _final_extras(args, gen, rows, hold_rows, vocab, live_train, live_hold)

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
        "embedding_residual": bool(args.residual),
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
        "extras": extras,
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


def _measure_points(gen, token_lists) -> dict:
    """Participation at the embedding mean, the stack output, and the field vector.

    The field vector is encode_batch, which includes the residual when that
    flag is on. The stack output is the same forward with the flag forced off,
    so a rich residual cannot hide a collapsed transformer.
    """
    flag = bool(gen.embedding_residual)
    z_out = encode_texts(gen, token_lists)
    z_emb = embedding_means(gen, token_lists)
    if flag:
        gen.embedding_residual = False
        try:
            z_stack = encode_texts(gen, token_lists)
        finally:
            gen.embedding_residual = True
    else:
        z_stack = z_out
    return {
        "output": population(z_out),
        "embedding_mean": population(z_emb),
        "stack": population(z_stack),
        "cos_stack_emb": round(mean_cosine(z_stack, z_emb), 4),
        "cos_output_emb": round(mean_cosine(z_out, z_emb), 4),
    }


def _final_extras(args, gen, rows, hold_rows, vocab, live_train, live_hold) -> dict:
    extras = {}
    if args.final_probe:
        from tools.completion.measure import fit_rhythm_probe, fit_soft_probe

        print("final frozen completion probe ...", flush=True)
        xtr = encode_texts(gen, [r["context"] for r in rows])
        xho = encode_texts(gen, [r["context"] for r in hold_rows])
        slices = None
        if any("split" in r for r in hold_rows):
            slices = {}
            for split in sorted({r.get("split") for r in hold_rows}):
                sub = [r for r in hold_rows if r.get("split") == split]
                slices[split] = (encode_texts(gen, [r["context"] for r in sub]), sub)
        probe = fit_soft_probe(xtr, rows, xho, hold_rows, vocab, slices=slices)
        extras["frozen_completion_probe"] = probe
        print(
            f"frozen probe holdout mode_top1 {probe['holdout'].get('mode_top1')}  "
            f"peaked_top1 {probe['holdout'].get('peaked_top1')}  "
            f"ce {probe['holdout'].get('ce')}",
            flush=True,
        )
        if probe.get("slices"):
            for name, sc in probe["slices"].items():
                print(
                    f"frozen probe split {name}  n {sc.get('n')}  "
                    f"mode_top1 {sc.get('mode_top1')}  "
                    f"recall@8 {sc.get('support_recall@8')}  ce {sc.get('ce')}",
                    flush=True,
                )
        ztr = encode_texts(gen, [r["tokens"] for r in live_train])
        zho = encode_texts(gen, [r["tokens"] for r in live_hold])
        extras["rhythm_linear_probe"] = fit_rhythm_probe(
            ztr, [r["rhythm"] for r in live_train], zho, [r["rhythm"] for r in live_hold],
        )
        print(f"rhythm probe {extras['rhythm_linear_probe']}", flush=True)
    if args.legibility:
        from tools.completion.measure import legibility

        print("training phase-0 mouth ...", flush=True)
        mouth = legibility(gen, live_train, live_hold, args.dim)
        extras["legibility"] = mouth
        print(f"legibility holdout {mouth['holdout']}", flush=True)
    return extras


@torch.no_grad()
def _completion_readout(gen, head, rows, rhythm_index, cond_scale: float) -> dict | None:
    """Co-trained head on these rows. Splits are scored separately when present."""
    if not rows:
        return None
    device = gen.device
    logits = []
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
        logits.append(head.head(conditioned))
    stacked = torch.cat(logits, dim=0)
    scores = completion_scores(stacked, rows, head.vocab)
    scores["ce"] = round(_word_ce(stacked, rows, head.index, device), 4)
    if any("split" in r for r in rows):
        by = {}
        for split in sorted({r.get("split") for r in rows}):
            idx = [i for i, r in enumerate(rows) if r.get("split") == split]
            sub_rows = [rows[i] for i in idx]
            sub_logits = stacked[idx]
            sub = completion_scores(sub_logits, sub_rows, head.vocab)
            sub["ce"] = round(_word_ce(sub_logits, sub_rows, head.index, device), 4)
            by[split] = sub
        scores["by_split"] = by
    return scores


def _word_ce(logits, rows, index, device: str) -> float:
    target = pack_targets([r["target_dist"] for r in rows], index, device)
    return float((-(target * torch.log_softmax(logits, dim=-1)).sum(-1)).mean())


if __name__ == "__main__":
    sys.exit(main())
