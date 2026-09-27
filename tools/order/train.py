"""Train one order-aware readout under the completion loss.

Same recipe as the embedding run that filled dimensions: Adam, lr 1e-2,
no weight decay, 40 epochs, seed 0, batch 128, rhythm weight 0, no rhythm
code. The code is the escape hatch the completion finding measured out.

The checkpoint is a new file. It is not a Generator checkpoint and it is
not written into the main checkout.

    python -m tools.order.train --dim 128 --readout gated
"""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

from tools.completion.corpus import GLUE
from tools.completion.geometry import population
from tools.order.corpus import load_jsonl
from tools.order.encoder import OrderEncoder
from tools.order.guard import REPO, SCRATCH, assert_live_intact, assert_safe_output
from training.completion import pack_targets

LOG = REPO / "docs" / "findings" / "logs" / "2026-09-23-order-aware"


def _seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def _content_vocab(records) -> list[str]:
    words = {t for rec in records for t in rec["tokens"] if t not in GLUE}
    return sorted(words)


def _surface_vocab(records) -> list[str]:
    return sorted({t for rec in records for t in rec["tokens"]})


@torch.no_grad()
def _word_ce(enc: OrderEncoder, head: nn.Linear, rows, index, device: str) -> float:
    if not rows:
        return float("nan")
    total = 0.0
    seen = 0
    for start in range(0, len(rows), 256):
        batch = rows[start:start + 256]
        vecs = enc.encode_token_lists([r["context"] for r in batch])
        h = torch.tensor(vecs, dtype=torch.float32, device=device)
        logits = head(h)
        target = pack_targets([r["target_dist"] for r in batch], index, device)
        word = -(target * torch.log_softmax(logits, dim=-1)).sum(dim=-1)
        total += float(word.sum())
        seen += len(batch)
    return round(total / max(seen, 1), 4)


def train_one(
    dim: int,
    readout: str,
    epochs: int = 40,
    seed: int = 0,
    batch_size: int = 128,
    lr: float = 1e-2,
    weight_decay: float = 0.0,
) -> dict:
    live = assert_live_intact()
    if not torch.cuda.is_available():
        raise SystemExit("CUDA is not available; refusing a silent CPU train")
    device = "cuda"
    _seed(seed)

    train_rows = load_jsonl(SCRATCH / "order_train.jsonl")
    hold_rows = load_jsonl(SCRATCH / "order_holdout.jsonl")
    from training.corpus import load_corpus

    from tools.order.guard import MAIN

    live_train = load_corpus(MAIN / "data" / "corpus" / "rhythm_train.jsonl")
    live_hold = load_corpus(MAIN / "data" / "corpus" / "rhythm_holdout.jsonl")
    surface = _surface_vocab(live_train + live_hold)
    content = _content_vocab(live_train)
    index = {t: i for i, t in enumerate(content)}
    missing = sorted({w for r in train_rows for w in r["targets"] if w not in index})
    if missing:
        raise SystemExit(f"train target outside content vocab: {missing[:6]}")
    hold_rows = [r for r in hold_rows if all(w in index for w in r["targets"])]

    print(
        f"order train readout={readout} dim={dim} epochs={epochs} "
        f"rows={len(train_rows)} hold={len(hold_rows)} "
        f"surface={len(surface)} content={len(content)} device={device}",
        flush=True,
    )

    enc = OrderEncoder(surface, dim, readout, max_len=8, device=device)
    head = nn.Linear(dim, len(content)).to(device)
    nn.init.xavier_uniform_(head.weight)
    nn.init.zeros_(head.bias)
    opt = torch.optim.Adam(
        list(enc.parameters()) + list(head.parameters()),
        lr=lr,
        weight_decay=weight_decay,
    )

    hold_lines = [r["tokens"] for r in live_hold]
    history = []

    def snapshot(epoch_done: int) -> None:
        enc.eval()
        head.eval()
        Z = enc.encode_token_lists(hold_lines)
        pop = population(Z)
        ce = _word_ce(enc, head, hold_rows, index, device)
        snap = {
            "epoch": epoch_done,
            "live_holdout_participation": pop["participation_ratio"],
            "live_holdout_eff_rank": pop["eff_rank_512cap"],
            "completion_holdout_word_ce": ce,
            "row_norm_mean": pop["row_norm_mean"],
        }
        history.append(snap)
        print(
            f"snap epoch {epoch_done}  PR {pop['participation_ratio']}  "
            f"eff {pop['eff_rank_512cap']}  hold_word_ce {ce}  "
            f"norm {pop['row_norm_mean']:.4f}",
            flush=True,
        )

    snapshot(0)
    loss_history = []
    for epoch in range(epochs):
        enc.train()
        head.train()
        order = torch.randperm(len(train_rows)).tolist()
        total = 0.0
        seen = 0
        for start in range(0, len(train_rows), batch_size):
            batch = [train_rows[i] for i in order[start:start + batch_size]]
            ids = enc.pad([enc.ids_of(r["context"]) for r in batch])
            target = pack_targets([r["target_dist"] for r in batch], index, device)
            opt.zero_grad()
            logits = head(enc(ids))
            loss = -(target * F.log_softmax(logits, dim=-1)).sum(dim=-1).mean()
            if not torch.isfinite(loss):
                raise RuntimeError(f"non-finite loss at epoch {epoch} readout={readout}")
            loss.backward()
            torch.nn.utils.clip_grad_norm_(
                list(enc.parameters()) + list(head.parameters()), 1.0,
            )
            opt.step()
            n = len(batch)
            total += float(loss.detach()) * n
            seen += n
        mean_loss = total / max(seen, 1)
        loss_history.append(round(mean_loss, 6))
        print(f"epoch {epoch + 1}/{epochs}  train_ce={mean_loss:.4f}", flush=True)
        if (epoch + 1) % 5 == 0 or epoch + 1 == epochs:
            snapshot(epoch + 1)

    enc.eval()
    head.eval()
    pad_max = float(enc.embedding.weight[enc.pad_id].detach().abs().max())
    if pad_max > 1e-6:
        raise RuntimeError(f"pad row moved: max abs {pad_max}")

    ckpt = REPO / "data" / "checkpoints" / f"order_encoder_{readout}_{dim}.pt"
    assert_safe_output(ckpt)
    ckpt.parent.mkdir(parents=True, exist_ok=True)
    blob = {
        "state_dict": enc.state_dict(),
        "surface_vocab": surface,
        "head_state_dict": head.state_dict(),
        "head_vocab": content,
        "dim": dim,
        "readout": readout,
        "max_len": enc.max_len,
        "epochs": epochs,
        "seed": seed,
        "lr": lr,
        "weight_decay": weight_decay,
        "batch_size": batch_size,
    }
    torch.save(blob, ckpt)
    from tools.completion.live_guard import sha256
    digest = sha256(ckpt)
    print(f"SAVED {ckpt} sha256={digest}", flush=True)

    report = {
        "objective": "order_aware_completion",
        "readout": readout,
        "dim": dim,
        "epochs": epochs,
        "seed": seed,
        "batch_size": batch_size,
        "learning_rate": lr,
        "weight_decay": weight_decay,
        "rhythm_weight": 0.0,
        "content_vocab": len(content),
        "surface_vocab": len(surface),
        "train_rows": len(train_rows),
        "hold_rows": len(hold_rows),
        "device": device,
        "torch": torch.__version__,
        "final_train_ce": loss_history[-1] if loss_history else None,
        "loss_history": loss_history,
        "snapshots": history,
        "checkpoint": str(ckpt),
        "checkpoint_sha256": digest,
        "live_sha256": live,
        "pad_row_max_abs": pad_max,
    }
    out = LOG / f"train_{readout}_dim{dim}_s{seed}.json"
    assert_safe_output(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    assert_live_intact()
    print(f"REPORT {out}", flush=True)
    del enc, head, opt
    torch.cuda.empty_cache()
    return report


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dim", type=int, required=True)
    ap.add_argument("--readout", required=True)
    ap.add_argument("--epochs", type=int, default=40)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--batch-size", type=int, default=128)
    ap.add_argument("--lr", type=float, default=1e-2)
    args = ap.parse_args()
    train_one(
        dim=args.dim,
        readout=args.readout,
        epochs=args.epochs,
        seed=args.seed,
        batch_size=args.batch_size,
        lr=args.lr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
