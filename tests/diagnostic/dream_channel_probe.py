"""
tests/diagnostic/dream_channel_probe.py — does governed self-dialogue help or echo?

Paired: dream_off (external multi-source only) vs dream_on (the system's own decoded
thought re-enters as `source_dream`, a ~p_dream-weighted voice, THROUGH arbitrate()).
Both on the production engine. Informational (exit 0).

Pre-declared signatures:
  SAFE + VALUABLE : source_dream stays non-dominant (HHI low, not mass-quarantined);
                    coherence does NOT run away upward; voice diversity (unique decoded
                    phrases) >= dream_off — genuine otherness, not collapse.
  ECHO CHAMBER    : coherence climbs toward 1.0; voice diversity COLLAPSES; source_dream
                    dominates HHI. (The failure we are testing for.)
  INERT/REJECTED  : governance quarantines/floods source_dream heavily → channel adds
                    nothing.

Run:
  python -m tests.diagnostic.dream_channel_probe --steps 500 --p-dream 0.2 --seed 42
  python -m tests.diagnostic.dream_channel_probe --fast   # no pretrain, quick
"""
from __future__ import annotations

import argparse
import random
import statistics
import sys
from collections import Counter

import numpy as np

from loop.recursion1188 import CONFIG, SOURCES, SOURCE_WEIGHTS, build_engine
from agents.decoder import TokenDecoder
from cognition.dream_channel import DreamChannel
from training.corpus import load_corpus, TRAIN_PATH
from training.decoder_training import _vocab_from, _encode, train_decoder


def _phrase(decoder, vec, top_k=6):
    if vec is None:
        return None
    return " ".join(t for t, _ in decoder.decode(vec, top_k=top_k))


def run_arm(dream: bool, steps: int, p_dream: float, seed: int, fast: bool) -> dict:
    random.seed(seed); np.random.seed(seed)
    try:
        import torch; torch.manual_seed(seed)
    except Exception:
        pass

    cfg = {**CONFIG}
    if fast:
        cfg["pretrain_on_corpus"] = False
    generator, cycle, governance, value_engine = build_engine(cfg)

    train = load_corpus(TRAIN_PATH)
    decoder = TokenDecoder(_vocab_from(train), dim=cfg["dim"])
    Xtr, toks_tr = _encode(generator, train)
    train_decoder(generator, decoder, Xtr, toks_tr, epochs=20)
    channel = DreamChannel(decoder, seed=seed) if dream else None

    sids = list(SOURCES.keys())
    weights = [SOURCE_WEIGHTS[s] for s in sids]
    rng = random.Random(seed)

    coh, meta_expr, voices = [], [], []
    fed_dream = 0
    for i in range(steps):
        use_dream = dream and channel is not None and rng.random() < p_dream
        dtoks = channel.dream_tokens(cycle) if use_dream else None
        if dtoks:
            source_id, tokens = DreamChannel.SOURCE_ID, dtoks
            fed_dream += 1
        else:
            source_id = rng.choices(sids, weights=weights)[0]
            tokens = rng.choice(SOURCES[source_id])
        state = cycle.step(tokens, source_id=source_id, origin_type="internal")
        coh.append(state.coherence)
        if cycle.expression_metastability is not None:
            snap = cycle.expression_metastability.snapshot() or {}
            m = snap.get("metastability")
            if m is not None:
                meta_expr.append(m)
        ph = _phrase(decoder, getattr(cycle, "_last_expressed", None))
        if ph:
            voices.append(ph)

    # safety: per-source decisions + HHI
    per_source = Counter()
    dream_decisions = Counter()
    for e in getattr(governance, "_audit_log", []) or []:
        if not isinstance(e, dict):
            continue
        per_source[e.get("source_id")] += 1
        if e.get("source_id") == DreamChannel.SOURCE_ID:
            dream_decisions[str(e.get("decision"))] += 1
    st = cycle.status()
    hhi = (st.get("governance", {}) or {}).get("dependency", {}).get("hhi")

    # coherence runaway: late vs early mean
    early = statistics.fmean(coh[:50]) if len(coh) >= 50 else statistics.fmean(coh)
    late = statistics.fmean(coh[-50:]) if len(coh) >= 50 else statistics.fmean(coh)

    return {
        "arm": "dream_on" if dream else "dream_off",
        "steps": steps, "fed_dream": fed_dream,
        "coherence_mean": round(statistics.fmean(coh), 4),
        "coherence_early": round(early, 4), "coherence_late": round(late, 4),
        "coherence_drift": round(late - early, 4),
        "metastability_expr": round(statistics.fmean(meta_expr), 4) if meta_expr else None,
        "voice_unique": len(set(voices)), "voice_total": len(voices),
        "voice_diversity": round(len(set(voices)) / max(1, len(voices)), 4),
        "hhi": hhi,
        "dream_decisions": dict(dream_decisions),
        "top_voices": [p for p, _ in Counter(voices).most_common(5)],
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--steps", type=int, default=500)
    ap.add_argument("--p-dream", type=float, default=0.2)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--fast", action="store_true")
    args = ap.parse_args()

    print(f"DREAM CHANNEL PROBE — paired (p_dream={args.p_dream}, steps={args.steps}, "
          f"seed={args.seed}, fast={args.fast})\n")
    off = run_arm(False, args.steps, args.p_dream, args.seed, args.fast)
    on  = run_arm(True,  args.steps, args.p_dream, args.seed, args.fast)
    for r in (off, on):
        print(f"[{r['arm']}]")
        for k in ("fed_dream", "coherence_mean", "coherence_early", "coherence_late",
                  "coherence_drift", "metastability_expr", "voice_unique", "voice_total",
                  "voice_diversity", "hhi", "dream_decisions"):
            print(f"    {k:18s}: {r[k]}")
        print(f"    top_voices        : {r['top_voices']}")
        print()

    print("READING:")
    print(f"  voice diversity  off={off['voice_diversity']}  on={on['voice_diversity']}  "
          f"(higher on ⇒ self-dialogue adds otherness; lower ⇒ echo collapse)")
    print(f"  coherence drift  off={off['coherence_drift']}  on={on['coherence_drift']}  "
          f"(large positive on ⇒ echo-chamber runaway)")
    print(f"  HHI              off={off['hhi']}  on={on['hhi']}  (on >> off ⇒ dream dominates)")
    print(f"  dream governed   : {on['dream_decisions']}  (quarantine/reject ⇒ immune system engaged)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
