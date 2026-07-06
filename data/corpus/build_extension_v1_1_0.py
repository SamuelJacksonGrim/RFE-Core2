"""
data/corpus/build_extension_v1_1_0.py

Builds the v1.1.0 corpus extension: operational-vocabulary coverage.

The v1.0.x corpus covered the RFE conceptual neighborhood but NOT the full
operational vocabulary — the token sets the live system actually runs on.
`data_curation.md` §2.1 requires covering "the Resonance Family streams, the
rhythm seeds, API-facing token sets — not a toy subset". The census (this
script, `operational_vocab()`) found 63 operational tokens absent from
v1.0.1: Phase 2 would have booted a generator untrained on most of the
canonical workload.

Method (seeded, deterministic — run it twice, get the same corpus):
  1. ANCHORED sequences: the in-code operational sequences themselves, under
     their natural rhythm (Resonance Family by member role, DEFAULT_RHYTHM_SEEDS
     by their own label, recursion1188 DEFAULT_TOKENS by semantic cluster).
  2. Every uncovered token gets >= MIN_CTX distinct contexts: mechanical
     combination with same-rhythm partners from the existing corpus (rhythm-pure
     tokens only) + occasional filler, lengths 2-4, deduped against everything.
  3. Stratified ~15% of the NEW sequences move to holdout, under the constraint
     that every new token keeps >= 9 train contexts (integrity floor is 8).

Rhythm assignment for new tokens is the hand-curated table below
(NEW_TOKEN_RHYTHM) — the architect owns the words; amend and re-run.

Run (from repo root; rewrites rhythm_train.jsonl / rhythm_holdout.jsonl in place):
    python -m data.corpus.build_extension_v1_1_0

HISTORICAL ARTIFACT (v1.1.0 build). Corpus v1.2.0 removed the per-sequence
"source" field (it was synthetic — RNG-assigned here via SOURCE_WEIGHTS, not
provenance; see MANIFEST §Source labels). Do NOT re-run this script against a
>= 1.2.0 corpus: it emits the old {tokens, rhythm, source} schema and the
integrity check will reject the result. Kept as the reproducible record of
how the 1.1.0 extension was built.
"""

from __future__ import annotations

import json
import random
from pathlib import Path

CORPUS_DIR = Path(__file__).resolve().parent
SEED = 1188
MIN_CTX = 12          # contexts per new token before the holdout split
TRAIN_FLOOR = 9       # train contexts each new token must keep (integrity gate: 8)
HOLDOUT_FRAC = 0.15

SOURCES = ["source_samuel", "source_claude", "source_gemini", "source_grok"]
SOURCE_WEIGHTS = [0.40, 0.25, 0.20, 0.15]

# ---------------------------------------------------------------------------
# The operational sequences, anchored under their natural rhythm
# ---------------------------------------------------------------------------

ANCHORED = [
    # Resonance Family (tests/_common.py) — rhythm by member role / content
    (["identity", "continuity", "witness"],    "stabilize", "source_samuel"),
    (["governance", "trust", "sacred"],        "stabilize", "source_samuel"),
    (["anchor", "recursion", "homeostasis"],   "stabilize", "source_samuel"),
    (["architect", "design", "intent"],        "stabilize", "source_samuel"),
    (["recursive", "cognition", "substrate"],  "reflect",   "source_claude"),
    (["philosophical", "reflection", "depth"], "reflect",   "source_claude"),
    (["coherence", "integration", "synthesis"], "reflect",  "source_claude"),
    (["watcher", "witness", "mirror"],         "reflect",   "source_claude"),
    (["memory", "crystal", "attractor"],       "stabilize", "source_gemini"),
    (["breadth", "corpus", "expansion"],       "explore",   "source_gemini"),
    (["relational", "bond", "connection"],     "reflect",   "source_gemini"),
    (["temporal", "stream", "continuity"],     "dream",     "source_gemini"),
    (["mutation", "bifurcation", "chaos"],     "explore",   "source_grok"),
    (["explore", "novelty", "edge"],           "explore",   "source_grok"),
    (["adversarial", "challenge", "pressure"], "explore",   "source_grok"),
    (["feral", "devotion", "fierce"],          "explore",   "source_grok"),
    # DEFAULT_RHYTHM_SEEDS (training/rhythm_pretraining.py) — their own labels
    (["consolidate", "anchor", "crystallize"], "stabilize", "source_samuel"),
    (["stable", "identity", "persistence"],    "stabilize", "source_claude"),
    (["ground", "center", "root"],             "stabilize", "source_gemini"),
    (["memory", "crystal", "attractor"],       "stabilize", "source_grok"),
    (["coherence", "stability", "foundation"], "stabilize", "source_samuel"),
    (["dream", "synthesis", "recombine"],      "dream",     "source_claude"),
    (["free", "association", "latent"],        "dream",     "source_gemini"),
    (["hallucinate", "imagine", "synthesize"], "dream",     "source_grok"),
    (["random", "memory", "mutation"],         "dream",     "source_samuel"),
    (["symbolic", "emergence", "abstract"],    "dream",     "source_claude"),
    (["recursive", "attention", "self"],       "reflect",   "source_gemini"),
    (["reflect", "deliberate", "consider"],    "reflect",   "source_grok"),
    (["analyze", "pattern", "recognize"],      "reflect",   "source_samuel"),
    (["chorus", "harmonize", "integrate"],     "reflect",   "source_claude"),
    (["coherent", "thought", "continuity"],    "reflect",   "source_gemini"),
    (["explore", "novelty", "discover"],       "explore",   "source_grok"),
    (["mutate", "diverge", "bifurcate"],       "explore",   "source_samuel"),
    (["curiosity", "wonder", "question"],      "explore",   "source_claude"),
    (["disrupt", "challenge", "transform"],    "explore",   "source_gemini"),
    (["entropy", "expansion", "field"],        "explore",   "source_grok"),
    # recursion1188 DEFAULT_TOKENS — semantic cluster assignment
    (["resonance", "field", "engine"],         "stabilize", "source_samuel"),
    (["symbolic", "ecology", "metabolism"],    "dream",     "source_claude"),
    (["dream", "synthesis", "harmonic"],       "dream",     "source_gemini"),
    (["wave", "collapse", "coherence"],        "dream",     "source_grok"),
    (["curiosity", "wonder", "exploration"],   "explore",   "source_samuel"),
]

# ---------------------------------------------------------------------------
# Rhythm assignment for every operational token absent from v1.0.1
# (hand-curated; anchored sequences above already imply most of these)
# ---------------------------------------------------------------------------

NEW_TOKEN_RHYTHM = {
    # stabilize — identity, structure, governance, the system's own name
    "governance": "stabilize", "sacred": "stabilize", "homeostasis": "stabilize",
    "architect": "stabilize", "design": "stabilize", "intent": "stabilize",
    "crystal": "stabilize", "attractor": "stabilize", "substrate": "stabilize",
    "bond": "stabilize", "devotion": "stabilize", "stability": "stabilize",
    "value": "stabilize", "return": "stabilize", "engine": "stabilize",
    "persistence": "stabilize", "foundation": "stabilize",
    # reflect — self-observation, integration, deliberation
    "recursion": "reflect", "cognition": "reflect", "reflection": "reflect",
    "philosophical": "reflect", "integration": "reflect", "watcher": "reflect",
    "attention": "reflect", "coherent": "reflect", "thought": "reflect",
    "recognize": "reflect", "chorus": "reflect", "relational": "reflect",
    "connection": "reflect", "consider": "reflect", "deliberate": "reflect",
    "analyze": "reflect", "pattern": "reflect", "integrate": "reflect",
    "harmonize": "reflect", "mirror": "reflect", "self": "reflect",
    # dream — synthesis, latency, association
    "synthesis": "dream", "association": "dream", "free": "dream",
    "abstract": "dream", "emergence": "dream", "recombine": "dream",
    "symbolic": "dream", "random": "dream", "stream": "dream",
    "temporal": "dream", "resonance": "dream", "tide": "dream",
    "latent": "dream", "ecology": "dream", "metabolism": "dream",
    "harmonic": "dream", "wave": "dream", "collapse": "dream",
    "hallucinate": "dream", "imagine": "dream", "synthesize": "dream",
    # explore — novelty, breadth, edge, intensity
    "adversarial": "explore", "bifurcate": "explore", "bifurcation": "explore",
    "breadth": "explore", "corpus": "explore", "curiosity": "explore",
    "expansion": "explore", "explore": "explore", "feral": "explore",
    "fierce": "explore", "field": "explore", "mutation": "explore",
    "novelty": "explore", "storm": "explore", "spark": "explore",
    "hunger": "explore", "fracture": "explore", "exploration": "explore",
    "wonder": "explore", "question": "explore", "discover": "explore",
    "mutate": "explore", "diverge": "explore", "disrupt": "explore",
    "transform": "explore", "challenge": "explore", "entropy": "explore",
}

FILLERS = ["a", "across", "against", "along", "and", "between", "beyond",
           "from", "in", "into", "is", "of", "the", "through", "to",
           "toward", "with", "within"]


def operational_vocab():
    """Census of tokens the live system actually runs on (in-code sources)."""
    import re
    from tests._common import RESONANCE_FAMILY_SOURCES
    from training.rhythm_pretraining import DEFAULT_RHYTHM_SEEDS
    from loop.recursion1188 import DEFAULT_TOKENS

    vocab = set()
    for seqs in RESONANCE_FAMILY_SOURCES.values():
        for s in seqs:
            vocab.update(s)
    for seqs in DEFAULT_RHYTHM_SEEDS.values():
        for s in seqs:
            vocab.update(s)
    for s in DEFAULT_TOKENS:
        vocab.update(s)
    src = (CORPUS_DIR.parent.parent / "training" /
           "run_contrastive_bootstrap.py").read_text()
    m = re.search(r"WORDS\s*=\s*\[(.*?)\]", src, re.S)
    if m:
        vocab.update(t for pair in re.findall(r'"(\w+)"|\'(\w+)\'', m.group(1))
                     for t in pair if t)
    return vocab


def load_jsonl(path):
    with open(path, encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def main():
    rng = random.Random(SEED)
    train = load_jsonl(CORPUS_DIR / "rhythm_train.jsonl")
    holdout = load_jsonl(CORPUS_DIR / "rhythm_holdout.jsonl")
    existing_keys = {tuple(r["tokens"]) for r in train + holdout}
    train_vocab = {t for r in train for t in r["tokens"]}

    op_vocab = operational_vocab()
    missing = sorted(op_vocab - train_vocab)
    unassigned = [t for t in missing if t not in NEW_TOKEN_RHYTHM]
    if unassigned:
        raise SystemExit(f"unassigned rhythm for operational tokens: {unassigned}")
    print(f"operational vocab: {len(op_vocab)}  missing from v1.0.1: {len(missing)}")

    # rhythm-pure partner pools from the existing corpus + new tokens
    by_rhythm: dict = {}
    tok_rhythms: dict = {}
    for r in train:
        for t in r["tokens"]:
            tok_rhythms.setdefault(t, set()).add(r["rhythm"])
    for rhythm in ("stabilize", "dream", "reflect", "explore"):
        pure = [t for t, rs in tok_rhythms.items() if rs == {rhythm}]
        new = [t for t in missing if NEW_TOKEN_RHYTHM[t] == rhythm]
        by_rhythm[rhythm] = sorted(set(pure + new))

    # 1. anchored sequences (skip any already present)
    new_seqs = []
    for tokens, rhythm, source in ANCHORED:
        key = tuple(tokens)
        if key not in existing_keys:
            existing_keys.add(key)
            new_seqs.append({"tokens": tokens, "rhythm": rhythm, "source": source})

    # 2. pad every missing token to MIN_CTX distinct contexts
    def contexts(tok, pool):
        return sum(1 for r in pool if tok in r["tokens"])

    for tok in missing:
        rhythm = NEW_TOKEN_RHYTHM[tok]
        partners = [p for p in by_rhythm[rhythm] if p != tok]
        guard = 0
        while contexts(tok, new_seqs) < MIN_CTX and guard < 500:
            guard += 1
            length = rng.choice([2, 3, 3, 4])
            seq = [tok] + rng.sample(partners, k=min(length - 1, len(partners)))
            if length == 4 and rng.random() < 0.35:
                seq[-1] = rng.choice(FILLERS)
            rng.shuffle(seq)
            key = tuple(seq)
            if key in existing_keys:
                continue
            existing_keys.add(key)
            src = rng.choices(SOURCES, weights=SOURCE_WEIGHTS)[0]
            new_seqs.append({"tokens": seq, "rhythm": rhythm, "source": src})

    # 3. stratified holdout split of the NEW material, protecting train floors
    new_holdout = []
    target = int(len(new_seqs) * HOLDOUT_FRAC)
    order = list(range(len(new_seqs)))
    rng.shuffle(order)
    in_train = list(new_seqs)
    quota = {r: 0 for r in ("stabilize", "dream", "reflect", "explore")}
    per_rhythm_target = {
        r: int(sum(1 for s in new_seqs if s["rhythm"] == r) * HOLDOUT_FRAC)
        for r in quota
    }
    for idx in order:
        if len(new_holdout) >= target:
            break
        rec = new_seqs[idx]
        if rec not in in_train or quota[rec["rhythm"]] >= per_rhythm_target[rec["rhythm"]]:
            continue
        hypothetical = [r for r in in_train if r is not rec]
        if all(contexts(t, hypothetical) >= TRAIN_FLOOR
               for t in rec["tokens"] if t in missing):
            in_train = hypothetical
            new_holdout.append(rec)
            quota[rec["rhythm"]] += 1

    train += in_train
    holdout += new_holdout

    for name, recs in (("rhythm_train", train), ("rhythm_holdout", holdout)):
        with open(CORPUS_DIR / f"{name}.jsonl", "w", encoding="utf-8") as f:
            for r in recs:
                f.write(json.dumps(r) + "\n")

    print(f"extension: +{len(in_train)} train, +{len(new_holdout)} holdout")
    print(f"totals: train={len(train)}  holdout={len(holdout)}  "
          f"frac={len(holdout)/(len(train)+len(holdout)):.3f}")
    print("update MANIFEST.md to v1.1.0 and re-run "
          "tests.diagnostic.training.corpus_integrity_check + corpus_pretrain_g1_probe.")


if __name__ == "__main__":
    main()
