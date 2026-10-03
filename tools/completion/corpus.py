"""Build context -> completion rows from the live rhythm corpus.

A row is one context and the empirical distribution of held-out content
words. The context is the other content words of a real sequence, sorted.
Mean-pool cannot see order, so permutations are one row. Glue is not a
target and it is not padded into the context.

Padding was tried. A fixed 4-glue frame plus the content word made the
scaffold 4/5 of the pool. On that file the word loss barely moved
(holdout CE 6.54 -> 5.05, entropy floor 0.28) while participation of the
live holdout fell from 21 at init to 4.5, the same collapse as the
contrastive runs. The frame is archived as the gluepad arm. Glue stays in
the live lines the mouth and the field read; it is scaffolding there, not
a fake context.

The distribution is the CBOW target. A one-word context with three or more
observed fillers is a stem: "Mary had a little ___". When that pivot is
attested in more than one rhythm, the same context tokens carry a different
filler distribution per rhythm. That is the rhythm condition. It is not
invented past what the live sequences co-occur.

Nothing here writes data/corpus/.
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Tuple

from training.corpus import RHYTHMS

# Closed class only. Every token here occurs in the live train vocab
# (checked at build time). Not a frequency cutoff — a hub noun is not glue.
GLUE = frozenset({
    "a", "an", "the", "of", "to", "in", "on", "is", "it", "its", "with", "and",
    "or", "as", "at", "by", "for", "be", "from", "into", "onto", "over", "under",
    "toward", "towards", "against", "within", "without", "between", "among",
    "through", "across", "along", "beneath", "beyond",
})

Key = Tuple[str, Tuple[str, ...]]


def content_of(tokens: Sequence[str], glue: frozenset = GLUE) -> List[str]:
    seen = []
    for t in tokens:
        if t in glue or t in seen:
            continue
        seen.append(t)
    return seen


def context_glue_of(tokens: Sequence[str], context_glue: frozenset) -> List[str]:
    """The reasoning glue a real sequence carries (not / because / if ...), deduped. Corpus v2 only (2026-10-03):
    it joins the context so 'soup hot' and 'soup not hot' are different rows; it is never a target. Empty set =
    legacy behaviour (no glue in context)."""
    if not context_glue:
        return []
    seen = []
    for t in tokens:
        if t in context_glue and t not in seen:
            seen.append(t)
    return seen


def canonical_context(content_others: Sequence[str], glue: frozenset = GLUE,
                      extra_glue: Sequence[str] = ()) -> List[str]:
    """Sorted context. Content words always; reasoning glue only when the caller passes it explicitly (corpus v2).
    Never a padded glue frame (see the module note)."""
    if any(t in glue for t in content_others):
        raise ValueError(f"glue in content context: {sorted(content_others)}")
    others = sorted(list(content_others) + list(extra_glue))
    if not content_others:
        raise ValueError("empty completion context")
    return others


def _bags(records: Iterable[dict], glue: frozenset = GLUE,
          context_glue: frozenset = frozenset()) -> Dict[Key, Counter]:
    """Leave-one-out counts, order-invariant within a rhythm.

    A content bag (rhythm, frozenset of content words [+ the record's context glue]) is counted once, so
    an order-swapped duplicate does not become two observations. With context_glue, 'soup hot' and
    'soup not hot' are different bags and different contexts.
    """
    seen_bags = set()
    counts: Dict[Key, Counter] = defaultdict(Counter)
    for rec in records:
        rhythm = rec["rhythm"]
        if rhythm not in RHYTHMS:
            raise ValueError(f"unknown rhythm {rhythm}")
        words = content_of(rec["tokens"], glue)
        if len(words) < 2:
            continue
        extra = context_glue_of(rec["tokens"], context_glue)
        bag = frozenset(words) | frozenset(extra)
        bag_key = (rhythm, bag)
        if bag_key in seen_bags:
            continue
        seen_bags.add(bag_key)
        for i, target in enumerate(words):
            others = words[:i] + words[i + 1:]
            ctx = tuple(canonical_context(others, glue, extra))
            counts[(rhythm, ctx)][target] += 1
    return counts


def _rows_from_counts(counts: Dict[Key, Counter], cross_contexts: set, glue: frozenset = GLUE) -> List[dict]:
    rows = []
    for rhythm, ctx in counts:
        counter = counts[(rhythm, ctx)]
        n_content = sum(1 for t in ctx if t not in glue)
        kind = "stem" if n_content == 1 and len(counter) >= 3 else "cbow"
        rows.append({
            "context": list(ctx),
            "rhythm": rhythm,
            "targets": {w: int(counter[w]) for w in sorted(counter)},
            "kind": kind,
            "n_content": n_content,
            "cross_rhythm": ctx in cross_contexts,
        })
    rows.sort(key=lambda r: (RHYTHMS.index(r["rhythm"]), r["context"], r["kind"]))
    return rows


def _cross_contexts(counts: Dict[Key, Counter]) -> set:
    by_ctx = defaultdict(set)
    for rhythm, ctx in counts:
        by_ctx[ctx].add(rhythm)
    return {ctx for ctx, rhythms in by_ctx.items() if len(rhythms) > 1}


def build_rows(records: Sequence[dict], glue: frozenset = GLUE,
               context_glue: frozenset = frozenset()) -> List[dict]:
    counts = _bags(records, glue, context_glue)
    return _rows_from_counts(counts, _cross_contexts(counts), glue)


def filter_holdout(train_records: Sequence[dict], hold_records: Sequence[dict], glue: frozenset = GLUE,
                   context_glue: frozenset = frozenset()) -> tuple[List[dict], dict]:
    """Drop holdout bags that already occur in train, order-invariant.

    Token overlap is allowed. A seen pivot with a new filler is kept.
    """
    def bag_of(rec):
        words = content_of(rec["tokens"], glue)
        return words, frozenset(words) | frozenset(context_glue_of(rec["tokens"], context_glue))

    train_bags = set()
    for rec in train_records:
        words, bag = bag_of(rec)
        if len(words) >= 2:
            train_bags.add((rec["rhythm"], bag))

    seen_bags = set()
    dropped = 0
    counts: Dict[Key, Counter] = defaultdict(Counter)
    for rec in hold_records:
        words, bag = bag_of(rec)
        if len(words) < 2:
            continue
        bag_key = (rec["rhythm"], bag)
        if bag_key in seen_bags:
            continue
        seen_bags.add(bag_key)
        if bag_key in train_bags:
            dropped += 1
            continue
        extra = context_glue_of(rec["tokens"], context_glue)
        for i, target in enumerate(words):
            others = words[:i] + words[i + 1:]
            ctx = tuple(canonical_context(others, glue, extra))
            counts[(rec["rhythm"], ctx)][target] += 1

    rows = _rows_from_counts(counts, _cross_contexts(counts), glue)
    return rows, {
        "holdout_content_bags_dropped": dropped,
        "holdout_rows": len(rows),
    }


def attach_dists(rows: List[dict]) -> List[dict]:
    out = []
    for row in rows:
        total = sum(row["targets"].values())
        dist = {w: c / total for w, c in row["targets"].items()}
        item = dict(row)
        item["target_dist"] = dist
        item["n_obs"] = int(total)
        item["support"] = len(dist)
        out.append(item)
    return out


def summarize(rows: List[dict]) -> dict:
    n = len(rows)
    supports = [len(r["targets"]) for r in rows]
    peaked_targets = {
        next(iter(r["targets"])) for r in rows if len(r["targets"]) == 1
    }
    words = {w for r in rows for w in r["targets"]}
    by_kind = Counter(r["kind"] for r in rows)
    by_rhythm = Counter(r["rhythm"] for r in rows)
    cross = sum(1 for r in rows if r["cross_rhythm"])
    # Distinct one-hot targets are linearly independent rows of P. This is a
    # lower bound on rank(P), which is the dimension demand of the softmax.
    return {
        "rows": n,
        "by_kind": dict(by_kind),
        "by_rhythm": {r: by_rhythm.get(r, 0) for r in RHYTHMS},
        "by_n_content": dict(Counter(r["n_content"] for r in rows)),
        "support_mean": round(sum(supports) / n, 3) if n else None,
        "support_max": max(supports) if supports else 0,
        "peaked_rows": sum(1 for s in supports if s == 1),
        "stem_rows": by_kind.get("stem", 0),
        "distinct_peaked_targets": len(peaked_targets),
        "words_in_any_support": len(words),
        "cross_rhythm_rows": cross,
        "by_context_len": {
            str(k): v
            for k, v in sorted(Counter(len(r["context"]) for r in rows).items())
        },
        "mean_entropy_nats": _mean_entropy(rows),
    }


def distribution_rank(rows: List[dict]) -> dict | None:
    """Participation of the context -> completion matrix.

    One-hot rows on different targets are independent, so this is the
    dimension demand of the softmax. None when numpy is not installed;
    the training interpreter has it.
    """
    try:
        import numpy as np
    except ImportError:
        return None
    if not rows:
        return None
    words = sorted({w for r in rows for w in r["targets"]})
    index = {w: i for i, w in enumerate(words)}
    P = np.zeros((len(rows), len(words)), dtype=np.float64)
    for i, row in enumerate(rows):
        total = float(sum(row["targets"].values()))
        for w, c in row["targets"].items():
            P[i, index[w]] = c / total
    centered = P - P.mean(axis=0, keepdims=True)
    lam = np.linalg.svd(centered, compute_uv=False) ** 2
    pr = float((lam.sum() ** 2) / (np.sum(lam ** 2) + 1e-12))
    rel = lam[0] * 1e-6 if len(lam) else 0.0
    return {
        "rows": len(rows),
        "support_vocab": len(words),
        "participation_ratio": round(pr, 2),
        "numerical_rank": int((lam > rel).sum()) if len(lam) else 0,
    }


def _mean_entropy(rows: List[dict]) -> float | None:
    if not rows:
        return None
    import math
    total = 0.0
    for row in rows:
        counts = list(row["targets"].values())
        z = sum(counts)
        h = 0.0
        for c in counts:
            p = c / z
            h -= p * math.log(p)
        total += h
    return round(total / len(rows), 4)


def dump_jsonl(path: Path, rows: List[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        for row in rows:
            # Counts only on disk. The dist is derived so the file stays exact.
            payload = {
                "context": row["context"],
                "rhythm": row["rhythm"],
                "targets": row["targets"],
                "kind": row["kind"],
                "n_content": row["n_content"],
                "cross_rhythm": row["cross_rhythm"],
            }
            f.write(json.dumps(payload, ensure_ascii=True) + "\n")


def load_jsonl(path: Path) -> List[dict]:
    rows = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return attach_dists(rows)


def selftest() -> None:
    """Order swaps collapse; glue is never the target; stems share a pivot."""
    records = [
        {"tokens": ["hold", "anchor"], "rhythm": "stabilize"},
        {"tokens": ["anchor", "hold"], "rhythm": "stabilize"},
        {"tokens": ["the", "hold", "anchor"], "rhythm": "stabilize"},
        {"tokens": ["hold", "ground"], "rhythm": "stabilize"},
        {"tokens": ["hold", "steady"], "rhythm": "stabilize"},
        {"tokens": ["hold", "fracture"], "rhythm": "rupture"},
        {"tokens": ["hold", "crack"], "rhythm": "rupture"},
        {"tokens": ["hold", "split"], "rhythm": "rupture"},
        {"tokens": ["in", "bedrock"], "rhythm": "stabilize"},  # one content word: skip
    ]
    rows = build_rows(records)
    # {hold, anchor} counted once despite three surface forms.
    hold_ctx = canonical_context(["hold"])
    anchor_rows = [
        r for r in rows
        if r["context"] == hold_ctx and r["rhythm"] == "stabilize"
    ]
    if len(anchor_rows) != 1:
        raise AssertionError(f"expected one stabilize stem for pivot hold, got {anchor_rows}")
    targets = anchor_rows[0]["targets"]
    if targets.get("anchor") != 1 or targets.get("ground") != 1 or targets.get("steady") != 1:
        raise AssertionError(f"stem counts not merged: {targets}")
    if "the" in targets or "in" in targets:
        raise AssertionError("glue leaked into the target")
    if any(any(t in GLUE for t in r["context"]) for r in rows):
        raise AssertionError("glue was written into a context")
    if anchor_rows[0]["context"] != ["hold"]:
        raise AssertionError(f"pivot context drifted: {anchor_rows[0]['context']}")
    rupture = [
        r for r in rows if r["context"] == hold_ctx and r["rhythm"] == "rupture"
    ]
    if not rupture or not rupture[0]["cross_rhythm"] or not anchor_rows[0]["cross_rhythm"]:
        raise AssertionError("shared pivot was not marked cross-rhythm")
    # Holdout copy of the train bag is dropped; a new filler of a seen pivot stays.
    hold_rows, stats = filter_holdout(
        records,
        [
            {"tokens": ["anchor", "hold"], "rhythm": "stabilize"},
            {"tokens": ["hold", "rest"], "rhythm": "stabilize"},
        ],
    )
    if stats["holdout_content_bags_dropped"] < 1:
        raise AssertionError(f"leaked bag was kept: {stats}")
    flat = {w for r in hold_rows for w in r["targets"]}
    if "anchor" in flat:
        raise AssertionError("leaked target survived")
    if "rest" not in flat:
        raise AssertionError("new filler was dropped")
