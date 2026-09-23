"""Decode-organ legibility at a chosen dim.

Phase 0 protocol (training/decoder_training.py): frozen encoder, fresh
TokenDecoder, BCE, hidden 256, 20 epochs, seed 42, holdout recall@8.
The decoder hidden width stays 256 — that is the head, not the field.

Does not overwrite decoder_5rhythm.pt. A 256D head, if saved, is a new file.

    python -m tools.dim256.legibility --dim 128 \
        --weights data/checkpoints/generator_weights_5rhythm.pt \
        --ecology data/checkpoints/generator_ecology_5rhythm.json --no-save
"""
from __future__ import annotations

import argparse
import statistics
import sys

import numpy as np
import torch

from agents.decoder import TokenDecoder
from tools.dim256.geometry import dump_json, load_generator, refuse_protected
from training.corpus import HOLDOUT_PATH, TRAIN_PATH, corpus_version, load_corpus
from training.decoder_training import _vocab_from, evaluate, train_decoder


def _encode(gen, records, batch=256):
    gen.eval()
    xs = []
    for i in range(0, len(records), batch):
        xs.append(gen.encode_batch([r["tokens"] for r in records[i:i + batch]]))
    X = torch.tensor(np.concatenate(xs, axis=0), dtype=torch.float32, device=gen.device)
    toks = [r["tokens"] for r in records]
    return X, toks


@torch.no_grad()
def median_true_rank(decoder, X, token_lists) -> float | None:
    """1-based median, over sequences, of the median rank of that sequence's true tokens."""
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
    ap.add_argument("--dim", type=int, required=True)
    ap.add_argument("--weights", required=True)
    ap.add_argument("--ecology", required=True)
    ap.add_argument("--epochs", type=int, default=20)
    ap.add_argument("--hidden", type=int, default=256)
    ap.add_argument("--topk", type=int, default=8)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--save", default="")
    ap.add_argument("--no-save", action="store_true")
    ap.add_argument("--report", default="")
    args = ap.parse_args()

    torch.manual_seed(args.seed)
    np.random.seed(args.seed)
    train = load_corpus(TRAIN_PATH)
    hold = load_corpus(HOLDOUT_PATH)
    vocab = _vocab_from(train)
    print(
        f"corpus v{corpus_version()} train={len(train)} holdout={len(hold)} "
        f"vocab={len(vocab)} dim={args.dim} decoder_hidden={args.hidden}",
        flush=True,
    )
    gen = load_generator(args.dim, args.weights, args.ecology, seed=args.seed)
    print(f"encoder device={gen.device} embedding={tuple(gen.embedding.weight.shape)}", flush=True)
    Xtr, ttr = _encode(gen, train)
    Xho, tho = _encode(gen, hold)
    dec = TokenDecoder(vocab, dim=args.dim, hidden=args.hidden, device=gen.device)
    print("training decoder ...", flush=True)
    train_decoder(gen, dec, Xtr, ttr, epochs=args.epochs)
    tr = evaluate(dec, Xtr, ttr, top_k=args.topk)
    ho = evaluate(dec, Xho, tho, top_k=args.topk)
    tr["median_true_rank"] = median_true_rank(dec, Xtr, ttr)
    ho["median_true_rank"] = median_true_rank(dec, Xho, tho)
    print("TRAIN  ", tr, flush=True)
    print("HOLDOUT", ho, flush=True)

    saved = None
    if not args.no_save:
        saved = args.save or f"data/checkpoints/decoder_5rhythm_{args.dim}.pt"
        refuse_protected(saved)
        torch.save(
            {"state_dict": dec.state_dict(), "vocab": vocab, "dim": args.dim,
             "hidden": args.hidden},
            saved,
        )
        print(f"SAVED {saved}", flush=True)

    report = {
        "corpus_version": corpus_version(),
        "dim": args.dim,
        "weights": args.weights,
        "epochs": args.epochs,
        "hidden": args.hidden,
        "topk": args.topk,
        "seed": args.seed,
        "train": tr,
        "holdout": ho,
        "saved_decoder": saved,
    }
    path = args.report or f"docs/findings/logs/2026-09-23-dim256/legibility_dim{args.dim}.json"
    dump_json(path, report)
    print(f"REPORT {path}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
