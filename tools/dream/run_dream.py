"""
tools/dream/run_dream.py — run a downtime dream session (offline, observe-only).

The waking analogue is `tools/decoder/listen.py` (the system's waking read-out).
This is its sleep: when no one is interacting, the system dreams — recombining its
own memories (crystals) + the field into fluid, symbolic word-clouds — and then
CONSOLIDATES, distilling the recurrent symbols + strong values + durable crystals
into reloadable, skill-compatible artifacts on disk (a dream journal + a
consolidated-memory file). See `cognition/dream_session.py` and `docs/north_star.md`.

Flow:
  1. build the composed engine (frozen generator as encoder)
  2. train a TokenDecoder read-out head against THIS engine's generator
  3. run a stretch of WAKING steps to populate crystals / values / field
  4. go to sleep: DreamSession.run() → symbolic dreams → consolidation files

Strictly offline/terminal: dreaming reads state and writes files. It does NOT feed
the live field or governance (no source re-entry through arbitrate()).

Run:
  python -m tools.dream.run_dream                      # production engine (pretrained)
  python -m tools.dream.run_dream --fast --wake 60     # quick: no corpus pretrain
  python -m tools.dream.run_dream --images 16 --out dreams
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
from cognition.dream_session import DreamSession


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--wake", type=int, default=80, help="waking steps to live before sleeping")
    ap.add_argument("--images", type=int, default=12, help="dream images to generate")
    ap.add_argument("--mutation", type=float, default=0.45, help="dream perturbation scale")
    ap.add_argument("--topk", type=int, default=6, help="words per dream image")
    ap.add_argument("--epochs", type=int, default=20, help="decoder training epochs")
    ap.add_argument("--out", type=str, default="dreams", help="output directory for artifacts")
    ap.add_argument("--fast", action="store_true", help="skip corpus pretrain (faster, lower-fidelity)")
    ap.add_argument("--seed", type=int, default=1188)
    args = ap.parse_args()

    random.seed(args.seed); np.random.seed(args.seed)
    try:
        import torch; torch.manual_seed(args.seed)
    except Exception:
        pass

    cfg = {**CONFIG}
    if args.fast:
        cfg["pretrain_on_corpus"] = False
    print(f"[dream] building engine (pretrain={cfg.get('pretrain_on_corpus')}) ...", flush=True)
    generator, cycle, governance, value_engine = build_engine(cfg)

    print("[dream] training decoder read-out head on corpus ...", flush=True)
    train = load_corpus(TRAIN_PATH)
    decoder = TokenDecoder(_vocab_from(train), dim=cfg["dim"])
    Xtr, toks_tr = _encode(generator, train)
    train_decoder(generator, decoder, Xtr, toks_tr, epochs=args.epochs)

    # --- waking life: live a stretch so there is something to dream about ---
    sids = list(SOURCES.keys())
    weights = [SOURCE_WEIGHTS[s] for s in sids]
    rng = random.Random(args.seed)
    print(f"\n[dream] living {args.wake} waking steps ...", flush=True)
    for _ in range(args.wake):
        source_id = rng.choices(sids, weights=weights)[0]
        tokens = rng.choice(SOURCES[source_id])
        cycle.step(tokens, source_id=source_id, origin_type="internal")
    print(f"[dream] waking life done — crystals={len(cycle.crystal_store.crystals)} "
          f"values={len(value_engine.values)}", flush=True)

    # --- sleep: dream + consolidate ---
    print(f"\n[dream] going to sleep — dreaming {args.images} images ...\n", flush=True)
    session = DreamSession(decoder, out_dir=args.out, mutation=args.mutation, seed=args.seed)
    images = session.dream(cycle, n_images=args.images)
    for i, im in enumerate(images):
        print(f"  {i+1:>2}. from {im['from']:<22} → {', '.join(im['image'][:args.topk])}")

    manifest = session.consolidate(cycle, images)
    print("\n[dream] consolidation:")
    print(f"  recurrent symbols : {', '.join(manifest['recurrent_symbols']) or '—'}")
    print(f"  strong/core values: {', '.join(manifest['strong_values']) or '—'}")
    print(f"  durable crystals  : {'; '.join(manifest['crystals']) or '—'}")
    print(f"\n[dream] wrote:\n  {manifest['journal']}\n  {manifest['memory']}")
    print("\n[dream] done (offline — nothing was fed back into the live loop).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
