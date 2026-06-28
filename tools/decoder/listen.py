"""
tools/decoder/listen.py — let the system read its own thoughts (observe-only).

Builds the composed engine, trains a TokenDecoder against THIS engine's (frozen)
generator on the corpus, then runs the autonomous cycle and decodes each step's
expressed vector (`cycle._last_expressed`) into words — "what the system said".

Strictly a terminal sink: the decoder reads the expressed vector and prints/logs;
nothing is fed back into the field or governance. (The governed dream channel —
feeding decoded words back in as a source through arbitrate() — is a separate,
explicit Phase-2 wiring, NOT this tool.)

Run:
  python -m tools.decoder.listen                 # production engine (pretrained)
  python -m tools.decoder.listen --fast --steps 40   # quick: no pretrain
  python -m tools.decoder.listen --steps 60 --topk 6
"""
from __future__ import annotations

import argparse
import random
import sys

import numpy as np

from loop.recursion1188 import CONFIG, SOURCES, SOURCE_WEIGHTS, build_engine
from agents.decoder import TokenDecoder
from training.corpus import load_corpus, TRAIN_PATH
from training.decoder_training import _vocab_from, _encode, train_decoder


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--steps", type=int, default=40)
    ap.add_argument("--topk", type=int, default=6)
    ap.add_argument("--epochs", type=int, default=20)
    ap.add_argument("--fast", action="store_true", help="skip corpus pretrain (faster, lower-fidelity read)")
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    random.seed(args.seed); np.random.seed(args.seed)
    try:
        import torch; torch.manual_seed(args.seed)
    except Exception:
        pass

    cfg = {**CONFIG}
    if args.fast:
        cfg["pretrain_on_corpus"] = False
    print(f"[listen] building engine (pretrain={cfg.get('pretrain_on_corpus')}) ...", flush=True)
    generator, cycle, governance, value_engine = build_engine(cfg)

    # Train the read-out head against THIS engine's frozen generator.
    print("[listen] training decoder on corpus ...", flush=True)
    train = load_corpus(TRAIN_PATH)
    decoder = TokenDecoder(_vocab_from(train), dim=cfg["dim"])
    Xtr, toks_tr = _encode(generator, train)
    train_decoder(generator, decoder, Xtr, toks_tr, epochs=args.epochs)

    sids = list(SOURCES.keys())
    weights = [SOURCE_WEIGHTS[s] for s in sids]
    rng = random.Random(args.seed)

    print(f"\n[listen] running {args.steps} steps — what the system said each step:\n", flush=True)
    print(f"{'step':>4} {'rhythm':<10} {'input':<34} → spoken")
    print("-" * 92)
    for i in range(args.steps):
        source_id = rng.choices(sids, weights=weights)[0]
        tokens = rng.choice(SOURCES[source_id])
        state = cycle.step(tokens, source_id=source_id, origin_type="internal")
        vec = cycle._last_expressed
        spoken = "—"
        if vec is not None:
            spoken = " ".join(t for t, _ in decoder.decode(vec, top_k=args.topk))
        print(f"{i:>4} {state.rhythm:<10} {(' '.join(tokens))[:34]:<34} → {spoken}", flush=True)

    print("\n[listen] done (observe-only — nothing was fed back into the loop).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
