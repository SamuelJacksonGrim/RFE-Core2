"""
training/decoder_training.py — train the TokenDecoder to reverse the (frozen) encoder.

Autoencoder objective, self-supervised on the existing corpus:
    tokens --(frozen Generator, eval/no_grad)--> vector --(Decoder)--> bag-of-tokens
    loss = BCEWithLogits(decoder(vector), multi_hot(tokens))   # multi-label
Only the Decoder trains; the Generator is the fixed encoder ("the encoder you have,
the decoder you add").

Reconstruction is measured on the held-out split as recall@k / precision@k / exact-bag@k
against a random baseline — how well a thought can be read back into words, and thus how
lossy the encoder is.

Run:
  python -m training.decoder_training                 # fast: untrained eval encoder
  python -m training.decoder_training --pretrain      # production encoder (corpus-pretrained)
  python -m training.decoder_training --epochs 25 --hidden 256 --topk 8
"""
from __future__ import annotations

import argparse
import statistics
import sys
from typing import List, Sequence

import numpy as np
import torch
import torch.nn as nn

from agents.generator import Generator
from agents.decoder import TokenDecoder
from training.corpus import load_corpus, TRAIN_PATH, HOLDOUT_PATH, corpus_version


def _vocab_from(records: List[dict]) -> List[str]:
    toks = set()
    for r in records:
        toks.update(r.get("tokens", []))
    return sorted(toks)


def _encode(generator: Generator, records: List[dict]) -> "tuple[torch.Tensor, list]":
    """Frozen-encoder pass: token lists → (N, dim) vectors + the token lists."""
    token_lists = [r.get("tokens", []) for r in records]
    vecs = [generator.generate(tl) for tl in token_lists]  # generate() is @no_grad
    X = torch.tensor(np.array(vecs), dtype=torch.float32, device=generator.device)
    return X, token_lists


def train_decoder(generator, decoder, X, token_lists, epochs=20, batch_size=64, lr=1e-3):
    Y = decoder.multi_hot(token_lists)
    opt = torch.optim.Adam(decoder.parameters(), lr=lr)
    loss_fn = nn.BCEWithLogitsLoss()
    n = X.shape[0]
    decoder.train()
    for ep in range(epochs):
        perm = torch.randperm(n, device=X.device)
        total = 0.0
        for s in range(0, n, batch_size):
            idx = perm[s:s + batch_size]
            opt.zero_grad()
            loss = loss_fn(decoder(X[idx]), Y[idx])
            loss.backward()
            opt.step()
            total += float(loss.detach()) * len(idx)
        if ep == 0 or (ep + 1) % 5 == 0 or ep == epochs - 1:
            print(f"  epoch {ep+1:2d}/{epochs}  loss={total/n:.4f}")
    return decoder


@torch.no_grad()
def evaluate(decoder, X, token_lists, top_k=8) -> dict:
    """recall@k / precision@k / exact-bag@k on (X, token_lists), vs a random baseline."""
    decoder.eval()
    logits = decoder(X)
    k = min(top_k, decoder.vocab_size)
    topk_idx = logits.topk(k, dim=-1).indices.tolist()
    recalls, precisions, exact = [], [], []
    for pred_idx, toks in zip(topk_idx, token_lists):
        true = {decoder.index[t] for t in toks if t in decoder.index}
        if not true:
            continue
        pred = set(pred_idx)
        hit = len(true & pred)
        recalls.append(hit / len(true))
        precisions.append(hit / k)
        exact.append(1.0 if true <= pred else 0.0)
    rand_recall = k / decoder.vocab_size  # expected recall of k random guesses
    return {
        "n": len(recalls),
        "top_k": k,
        "recall@k":    round(statistics.fmean(recalls), 4) if recalls else None,
        "precision@k": round(statistics.fmean(precisions), 4) if precisions else None,
        "exact_bag@k": round(statistics.fmean(exact), 4) if exact else None,
        "random_recall@k": round(rand_recall, 4),
        "lift_over_random": round(statistics.fmean(recalls) / rand_recall, 2) if recalls else None,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--epochs", type=int, default=20)
    ap.add_argument("--hidden", type=int, default=256)
    ap.add_argument("--topk", type=int, default=8)
    ap.add_argument("--pretrain", action="store_true",
                    help="corpus-pretrain the encoder first (the production regime)")
    ap.add_argument("--dim", type=int, default=128)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    import random as _random
    _random.seed(args.seed); np.random.seed(args.seed); torch.manual_seed(args.seed)

    train = load_corpus(TRAIN_PATH)
    holdout = load_corpus(HOLDOUT_PATH)
    vocab = _vocab_from(train)
    print(f"corpus v{corpus_version()}  train={len(train)} holdout={len(holdout)} vocab={len(vocab)}")

    generator = Generator(vocab_size=8192, dim=args.dim, depth=4, heads=4)
    if args.pretrain:
        from training.corpus import to_rhythm_seeds
        from training.rhythm_pretraining import RhythmPretrainer, PretrainingConfig
        print("pretraining encoder on corpus ...")
        RhythmPretrainer(generator, rhythm_seeds=to_rhythm_seeds(train),
                         config=PretrainingConfig(n_epochs=8)).pretrain()
    generator.eval()  # frozen encoder, operating regime
    print(f"encoder: {'pretrained+' if args.pretrain else ''}eval")

    decoder = TokenDecoder(vocab, dim=args.dim, hidden=args.hidden)
    print(f"decoder: {decoder.state()}")

    Xtr, toks_tr = _encode(generator, train)
    Xho, toks_ho = _encode(generator, holdout)

    print("training decoder ...")
    train_decoder(generator, decoder, Xtr, toks_tr, epochs=args.epochs)

    train_metrics = evaluate(decoder, Xtr, toks_tr, top_k=args.topk)
    hold_metrics  = evaluate(decoder, Xho, toks_ho, top_k=args.topk)
    print("\nRECONSTRUCTION (bag-of-tokens):")
    print(f"  train  : {train_metrics}")
    print(f"  holdout: {hold_metrics}")

    # A few example renders: thought (true tokens) -> decoder's top guesses
    print("\nEXAMPLE RENDERS (holdout — true tokens → decoded top-6):")
    for r in range(min(6, len(toks_ho))):
        guesses = decoder.decode(Xho[r].cpu().numpy(), top_k=6)
        gtxt = ", ".join(f"{t}" for t, _ in guesses)
        print(f"  {toks_ho[r]}  →  [{gtxt}]")

    return 0


if __name__ == "__main__":
    sys.exit(main())
