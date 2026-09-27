"""Decode-organ legibility for one long-sequence cell.

Phase 0 protocol: frozen encoder, fresh TokenDecoder, BCE, hidden 256,
20 epochs, seed 42, holdout recall@8. Also records mean true-set size and
mean hits, because recall@8 divides by the bag size and longer bags are a
harder fraction.

Does not overwrite decoder_5rhythm.pt.

    python -m tools.longseq.legibility --arm long --dim 256
"""
from __future__ import annotations

import argparse
import hashlib
import statistics
import sys
from pathlib import Path

import numpy as np
import torch

from agents.decoder import TokenDecoder
from tools.dim256.geometry import dump_json, load_generator, refuse_protected
from tools.longseq.train import ALSO_PROTECTED, _paths
from training.corpus import load_corpus
from training.decoder_training import _vocab_from, evaluate, train_decoder

ROOT = Path(__file__).resolve().parents[2]
LOG_DIR = ROOT / "docs" / "findings" / "logs" / "2026-09-23-longseq"


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def _refuse(path: str) -> None:
    refuse_protected(path)
    if Path(path).name in ALSO_PROTECTED:
        raise SystemExit(f"refusing to overwrite a dim-256 paired artifact: {path}")


def _encode(gen, records, batch=256):
    gen.eval()
    xs = []
    for i in range(0, len(records), batch):
        xs.append(gen.encode_batch([r["tokens"] for r in records[i:i + batch]]))
    X = torch.tensor(np.concatenate(xs, axis=0), dtype=torch.float32, device=gen.device)
    return X, [r["tokens"] for r in records]


@torch.no_grad()
def _bag_stats(decoder, X, token_lists, top_k: int) -> dict:
    """Absolute hits, so a longer bag is not punished only by the recall fraction."""
    decoder.eval()
    k = min(top_k, decoder.vocab_size)
    topk_idx = decoder(X).topk(k, dim=-1).indices.tolist()
    hits, sizes = [], []
    for pred_idx, toks in zip(topk_idx, token_lists):
        true = {decoder.index[t] for t in toks if t in decoder.index}
        if not true:
            continue
        hits.append(len(true & set(pred_idx)))
        sizes.append(len(true))
    return {
        "mean_hits": round(statistics.fmean(hits), 3) if hits else None,
        "mean_true": round(statistics.fmean(sizes), 3) if sizes else None,
    }


@torch.no_grad()
def _median_true_rank(decoder, X, token_lists) -> float | None:
    decoder.eval()
    logits = decoder(X)
    order = logits.argsort(dim=-1, descending=True)
    ranks = torch.empty_like(order)
    idx = torch.arange(order.shape[1], device=order.device).unsqueeze(0).expand_as(order)
    ranks.scatter_(1, order, idx)
    meds = []
    for i, toks in enumerate(token_lists):
        js = [decoder.index[t] for t in toks if t in decoder.index]
        if not js:
            continue
        meds.append(float(torch.median(ranks[i, js].float())) + 1.0)
    if not meds:
        return None
    return round(statistics.median(meds), 2)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", choices=("short", "long", "length", "vocab"), required=True)
    ap.add_argument("--dim", type=int, required=True)
    ap.add_argument("--epochs", type=int, default=20)
    ap.add_argument("--hidden", type=int, default=256)
    ap.add_argument("--topk", type=int, default=8)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    torch.manual_seed(args.seed)
    np.random.seed(args.seed)
    train_path, hold_path = _paths(args.arm)
    weights = f"data/checkpoints/longseq_{args.arm}_d{args.dim}.pt"
    ecology = f"data/checkpoints/longseq_{args.arm}_d{args.dim}.ecology.json"
    saved = f"data/checkpoints/longseq_decoder_{args.arm}_d{args.dim}.pt"
    _refuse(saved)

    train = load_corpus(train_path)
    hold = load_corpus(hold_path)
    vocab = _vocab_from(train)
    print(
        f"arm={args.arm} train={len(train)} holdout={len(hold)} "
        f"vocab={len(vocab)} dim={args.dim} decoder_hidden={args.hidden}",
        flush=True,
    )
    gen = load_generator(args.dim, weights, ecology, seed=args.seed)
    print(f"encoder device={gen.device} embedding={tuple(gen.embedding.weight.shape)}", flush=True)
    Xtr, ttr = _encode(gen, train)
    Xho, tho = _encode(gen, hold)
    dec = TokenDecoder(vocab, dim=args.dim, hidden=args.hidden, device=gen.device)
    print("training decoder ...", flush=True)
    train_decoder(gen, dec, Xtr, ttr, epochs=args.epochs)
    tr = evaluate(dec, Xtr, ttr, top_k=args.topk)
    ho = evaluate(dec, Xho, tho, top_k=args.topk)
    tr.update(_bag_stats(dec, Xtr, ttr, args.topk))
    ho.update(_bag_stats(dec, Xho, tho, args.topk))
    tr["median_true_rank"] = _median_true_rank(dec, Xtr, ttr)
    ho["median_true_rank"] = _median_true_rank(dec, Xho, tho)
    print("TRAIN  ", tr, flush=True)
    print("HOLDOUT", ho, flush=True)

    torch.save(
        {"state_dict": dec.state_dict(), "vocab": vocab, "dim": args.dim, "hidden": args.hidden},
        saved,
    )
    print(f"SAVED {saved}", flush=True)
    report = {
        "arm": args.arm,
        "dim": args.dim,
        "weights": weights,
        "train_sha256": _sha256(train_path),
        "holdout_sha256": _sha256(hold_path),
        "epochs": args.epochs,
        "hidden": args.hidden,
        "topk": args.topk,
        "seed": args.seed,
        "train": tr,
        "holdout": ho,
        "saved_decoder": saved,
    }
    path = LOG_DIR / f"legibility_{args.arm}_d{args.dim}.json"
    dump_json(str(path), report)
    print(f"REPORT {path}", flush=True)
    print(
        f"holdout recall@8={ho['recall@k']} lift={ho['lift_over_random']} "
        f"hits={ho['mean_hits']}/{ho['mean_true']} median_rank={ho['median_true_rank']}",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
