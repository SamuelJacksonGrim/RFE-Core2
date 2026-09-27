"""Bare CBOW: mean of token embeddings, no transformer.

The encoder runs collapsed to participation ~4 under the same loss, with
and without a rhythm term. This control asks whether that is the loss or
the stack. Same rows, same soft cross-entropy, same 20 epochs, no rhythm
code. If this fills dimensions, the objective is doing what word2vec does
and the shared stack is what falls into the basin.

    python -m tools.completion.bow_control --dim 128
"""

from __future__ import annotations

import argparse
import random
import sys

import numpy as np
import torch
import torch.nn.functional as F

from tools.completion.corpus import load_jsonl
from tools.completion.geometry import dump_json, population
from tools.completion.live_guard import REPO, assert_live_intact
from tools.completion.measure import completion_scores, fit_rhythm_probe
from training.completion import pack_targets
from training.corpus import HOLDOUT_PATH, RHYTHMS, TRAIN_PATH, load_corpus

SCRATCH = REPO.parent / "scratch" / "completion"


def _overfit_check(device: str) -> None:
    """32 one-hot rows, dim 32, must leave chance. Catches a broken loss."""
    torch.manual_seed(0)
    n, dim, V = 32, 32, 40
    emb = torch.nn.Embedding(n, dim).to(device)
    head = torch.nn.Linear(dim, V).to(device)
    opt = torch.optim.Adam(list(emb.parameters()) + list(head.parameters()), lr=1e-2)
    targets = torch.arange(n, device=device) % V
    ids = torch.arange(n, device=device)
    for _ in range(80):
        opt.zero_grad()
        h = F.normalize(emb(ids), dim=-1)
        loss = F.cross_entropy(head(h), targets)
        loss.backward()
        opt.step()
    final = float(loss.detach())
    if final > 0.5:
        raise SystemExit(f"bare CBOW failed the overfit check, loss={final:.3f}")
    print(f"overfit check ok  loss={final:.4f}", flush=True)


def _encode(emb, token_lists, index, device) -> torch.Tensor:
    rows = []
    for tl in token_lists:
        ix = torch.tensor([index[t] for t in tl], dtype=torch.long, device=device)
        rows.append(emb(ix).mean(dim=0))
    return F.normalize(torch.stack(rows, dim=0), dim=-1)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dim", type=int, required=True)
    ap.add_argument("--epochs", type=int, default=20)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--batch-size", type=int, default=128)
    ap.add_argument("--lr", type=float, default=1e-2)
    args = ap.parse_args()

    assert_live_intact()
    _seed = args.seed
    random.seed(_seed)
    np.random.seed(_seed)
    torch.manual_seed(_seed)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    if device == "cuda":
        torch.cuda.manual_seed_all(_seed)
    _overfit_check(device)

    train_rows = load_jsonl(SCRATCH / "completion_train.jsonl")
    hold_rows = load_jsonl(SCRATCH / "completion_holdout.jsonl")
    live_hold = load_corpus(HOLDOUT_PATH)
    live_train = load_corpus(TRAIN_PATH)
    surface = sorted({t for row in train_rows for t in row["context"]}
                     | {t for row in train_rows for t in row["targets"]}
                     | {t for rec in live_train for t in rec["tokens"]}
                     | {t for rec in live_hold for t in rec["tokens"]})
    index = {t: i for i, t in enumerate(surface)}
    out_vocab = sorted({t for row in train_rows for t in row["targets"]}
                       | {t for row in hold_rows for t in row["targets"]})
    out_index = {t: i for i, t in enumerate(out_vocab)}

    emb = torch.nn.Embedding(len(surface), args.dim).to(device)
    head = torch.nn.Linear(args.dim, len(out_vocab)).to(device)
    torch.nn.init.normal_(emb.weight, std=0.035)
    opt = torch.optim.Adam(
        list(emb.parameters()) + list(head.parameters()),
        lr=args.lr, weight_decay=0.0,
    )
    print(
        f"bare CBOW dim={args.dim} surface={len(surface)} V={len(out_vocab)} "
        f"train={len(train_rows)} device={device}",
        flush=True,
    )

    def run_epoch(rows, train: bool) -> float:
        if train:
            emb.train(); head.train()
            order = torch.randperm(len(rows)).tolist()
        else:
            emb.eval(); head.eval()
            order = list(range(len(rows)))
        total = 0.0
        seen = 0
        for start in range(0, len(order), args.batch_size):
            batch = [rows[i] for i in order[start:start + args.batch_size]]
            target = pack_targets([r["target_dist"] for r in batch], out_index, device)
            h = _encode(emb, [r["context"] for r in batch], index, device)
            log_q = torch.log_softmax(head(h), dim=-1)
            loss = -(target * log_q).sum(-1).mean()
            if train:
                opt.zero_grad()
                loss.backward()
                opt.step()
            total += float(loss.detach()) * len(batch)
            seen += len(batch)
        return total / max(seen, 1)

    history = []
    for epoch in range(1, args.epochs + 1):
        tr = run_epoch(train_rows, True)
        if epoch == args.epochs or epoch % 5 == 0:
            with torch.no_grad():
                ho = run_epoch(hold_rows, False)
                ctx = _encode(emb, [r["context"] for r in hold_rows], index, device).cpu().numpy()
                full = _encode(emb, [r["tokens"] for r in live_hold], index, device).cpu().numpy()
            pop_ctx = population(ctx)
            pop_full = population(full)
            history.append({
                "epoch": epoch,
                "train_ce": round(tr, 4),
                "hold_ce": round(ho, 4),
                "context_pr": pop_ctx["participation_ratio"],
                "context_eff": pop_ctx["eff_rank_512cap"],
                "live_holdout_pr": pop_full["participation_ratio"],
                "live_holdout_eff": pop_full["eff_rank_512cap"],
            })
            print(
                f"epoch {epoch}  train_ce {tr:.4f}  hold_ce {ho:.4f}  "
                f"PR {pop_full['participation_ratio']}  eff {pop_full['eff_rank_512cap']}  "
                f"ctx_PR {pop_ctx['participation_ratio']}",
                flush=True,
            )

    emb.eval(); head.eval()
    with torch.no_grad():
        h_tr = _encode(emb, [r["context"] for r in train_rows], index, device)
        h_ho = _encode(emb, [r["context"] for r in hold_rows], index, device)
        logits_ho = head(h_ho)
        logits_tr = head(h_tr)
        Ztr = _encode(emb, [r["tokens"] for r in live_train], index, device).cpu().numpy()
        Zho = _encode(emb, [r["tokens"] for r in live_hold], index, device).cpu().numpy()
    ytr = [r["rhythm"] for r in live_train]
    yho = [r["rhythm"] for r in live_hold]
    rhythm = fit_rhythm_probe(Ztr, ytr, Zho, yho)
    hold_scores = completion_scores(logits_ho, hold_rows, out_vocab)
    train_scores = completion_scores(logits_tr, train_rows, out_vocab)
    print(
        f"peaked_top1 hold {hold_scores['peaked_top1']} train {train_scores['peaked_top1']}  "
        f"rhythm_probe {rhythm['holdout_acc']}",
        flush=True,
    )
    report = {
        "objective": "bare_cbow_mean_embedding",
        "dim": args.dim,
        "epochs": args.epochs,
        "seed": args.seed,
        "note": "no transformer, no rhythm term, mean of embeddings then L2",
        "history": history,
        "population_live_holdout": population(Zho),
        "rhythm_linear_probe": rhythm,
        "completion_holdout": hold_scores,
        "completion_train": train_scores,
        "rhythms": list(RHYTHMS),
    }
    path = REPO / "docs" / "findings" / "logs" / "2026-09-23-completion" / f"bow_dim{args.dim}_s{args.seed}.json"
    dump_json(str(path), report)
    assert_live_intact()
    print(f"REPORT {path}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
