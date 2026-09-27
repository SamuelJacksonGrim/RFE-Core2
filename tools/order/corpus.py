"""Ordered completion rows. The blank stays where the word was.

The mean-pool corpus sorts the other content words and drops glue, because
a sum cannot tell those apart. An order-aware encoder can, so this builder
does not sort and does not close the hole.

A row's context is the live line with one content word replaced by
``<BLANK>``. Glue is never the target and it is not stripped: "a little
___" is the positioned stem. Lines with fewer than two content words are
skipped, same rule as the completion corpus — a glue-only frame was the
collapse, not a context.

Nothing here writes ``data/corpus/``.
"""

from __future__ import annotations

import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Tuple

from tools.completion.corpus import GLUE
from tools.order.encoder import BLANK
from training.corpus import RHYTHMS

Key = Tuple[str, Tuple[str, ...]]


def _content(tokens: Sequence[str]) -> List[str]:
    return [t for t in tokens if t not in GLUE]


def examples_of(record: dict) -> List[dict]:
    """One positioned hold-out per content word. Empty if the line is too short."""
    tokens = list(record["tokens"])
    if BLANK in tokens or "<PAD>" in tokens:
        raise ValueError(f"live line already contains a reserved token: {tokens}")
    rhythm = record["rhythm"]
    if rhythm not in RHYTHMS:
        raise ValueError(f"unknown rhythm {rhythm}")
    content = _content(tokens)
    if len(content) < 2:
        return []
    rows = []
    for i, tok in enumerate(tokens):
        if tok in GLUE:
            continue
        context = tokens[:i] + [BLANK] + tokens[i + 1:]
        rows.append({
            "context": context,
            "rhythm": rhythm,
            "target": tok,
            "blank_pos": i,
            "line_len": len(tokens),
            "content_bag": tuple(sorted(content)),
        })
    return rows


def _accumulate(records: Iterable[dict]) -> Dict[Key, Counter]:
    counts: Dict[Key, Counter] = defaultdict(Counter)
    for rec in records:
        for ex in examples_of(rec):
            counts[(ex["rhythm"], tuple(ex["context"]))][ex["target"]] += 1
    return counts


def _cross_contexts(counts: Dict[Key, Counter]) -> set:
    by_ctx: Dict[Tuple[str, ...], set] = defaultdict(set)
    for rhythm, ctx in counts:
        by_ctx[ctx].add(rhythm)
    return {ctx for ctx, rhythms in by_ctx.items() if len(rhythms) > 1}


def _rows_from_counts(counts: Dict[Key, Counter], cross: set) -> List[dict]:
    # blank position and line length are functions of the context string.
    rows = []
    for rhythm, ctx in counts:
        counter = counts[(rhythm, ctx)]
        blank_at = ctx.index(BLANK)
        n_content = sum(1 for t in ctx if t not in GLUE and t != BLANK)
        total = sum(counter.values())
        dist = {w: c / total for w, c in counter.items()}
        rows.append({
            "context": list(ctx),
            "rhythm": rhythm,
            "targets": {w: int(counter[w]) for w in sorted(counter)},
            "target_dist": dist,
            "n_obs": int(total),
            "support": len(dist),
            "kind": "stem" if n_content == 1 and len(counter) >= 3 else "cbow",
            "n_content": n_content,
            "blank_pos": blank_at,
            "line_len": len(ctx),
            "cross_rhythm": ctx in cross,
        })
    rows.sort(key=lambda r: (RHYTHMS.index(r["rhythm"]), r["context"], r["kind"]))
    return rows


def build_rows(records: Sequence[dict]) -> List[dict]:
    counts = _accumulate(records)
    return _rows_from_counts(counts, _cross_contexts(counts))


def filter_holdout(train_records: Sequence[dict], hold_records: Sequence[dict]) -> tuple[List[dict], dict]:
    """Drop a holdout context only when that exact positioned string was trained.

    A new order of a seen bag is kept. That is the row mean-pool cannot
    represent as a different input. Token overlap is kept.
    """
    train_counts = _accumulate(train_records)
    train_keys = set(train_counts)
    hold_counts: Dict[Key, Counter] = defaultdict(Counter)
    dropped = 0
    kept_examples = 0
    for rec in hold_records:
        for ex in examples_of(rec):
            key = (ex["rhythm"], tuple(ex["context"]))
            if key in train_keys:
                dropped += 1
                continue
            hold_counts[key][ex["target"]] += 1
            kept_examples += 1
    rows = _rows_from_counts(hold_counts, _cross_contexts(train_counts))
    return rows, {
        "holdout_exact_contexts_dropped": dropped,
        "holdout_examples_kept": kept_examples,
        "holdout_rows": len(rows),
    }


def _multiset_groups(rows: Sequence[dict]) -> Dict[tuple, List[dict]]:
    groups: Dict[tuple, List[dict]] = defaultdict(list)
    for row in rows:
        key = (row["rhythm"], tuple(sorted(row["context"])))
        groups[key].append(row)
    return groups


def order_structure(rows: Sequence[dict]) -> dict:
    """Where order could change the completion, and where it cannot.

    Same multiset of context tokens, more than one order. If those orders
    carry different target distributions, a mean-pool encoder is given one
    vector and two answers. That is the only slice on which order can raise
    completion accuracy. Agreed targets mean order is redundant for the loss.
    """
    groups = _multiset_groups(rows)
    multi = 0
    disagree = 0
    disagree_rows = 0
    agree_rows = 0
    for items in groups.values():
        seqs = {tuple(i["context"]) for i in items}
        if len(seqs) < 2:
            continue
        multi += 1
        dists = {tuple(sorted(i["targets"].items())) for i in items}
        if len(dists) > 1:
            disagree += 1
            disagree_rows += len(items)
        else:
            agree_rows += len(items)
    return {
        "rows": len(rows),
        "multisets_with_several_orders": multi,
        "orders_whose_targets_disagree": disagree,
        "rows_in_disagreeing_orders": disagree_rows,
        "rows_in_agreed_orders": agree_rows,
    }


def tag_holdout_conflicts(train_rows: Sequence[dict], hold_rows: List[dict]) -> dict:
    """Mark holdout rows whose context multiset collides, in train, across orders."""
    groups = _multiset_groups(train_rows)
    disagreeing = set()
    multi = set()
    for key, items in groups.items():
        seqs = {tuple(i["context"]) for i in items}
        if len(seqs) < 2:
            continue
        multi.add(key)
        dists = {tuple(sorted(i["targets"].items())) for i in items}
        if len(dists) > 1:
            disagreeing.add(key)
    n_multi = 0
    n_disagree = 0
    for row in hold_rows:
        key = (row["rhythm"], tuple(sorted(row["context"])))
        row["train_order_multiset"] = key in multi
        row["train_order_conflict"] = key in disagreeing
        n_multi += int(key in multi)
        n_disagree += int(key in disagreeing)
    return {
        "holdout_rows_whose_multiset_has_several_train_orders": n_multi,
        "holdout_rows_in_a_train_target_conflict": n_disagree,
    }


def line_order_pairs(records: Sequence[dict]) -> dict:
    """Live lines that are the same tokens in more than one order."""
    groups: Dict[tuple, set] = defaultdict(set)
    lengths: Counter = Counter()
    skipped = 0
    for rec in records:
        tokens = tuple(rec["tokens"])
        lengths[len(tokens)] += 1
        if len(_content(tokens)) < 2:
            skipped += 1
            continue
        groups[(rec["rhythm"], tuple(sorted(tokens)))].add(tokens)
    multi = sum(1 for seqs in groups.values() if len(seqs) > 1)
    return {
        "lines": len(records),
        "by_len": {str(k): lengths[k] for k in sorted(lengths)},
        "lines_skipped_lt2_content": skipped,
        "bags_with_several_orders": multi,
    }


def _entropy(rows: Sequence[dict]) -> float:
    if not rows:
        return 0.0
    total = 0.0
    for row in rows:
        total += -sum(p * math.log(p) for p in row["target_dist"].values() if p > 0)
    return total / len(rows)


def summarize(rows: Sequence[dict]) -> dict:
    supports = [r["support"] for r in rows]
    by_kind = Counter(r["kind"] for r in rows)
    by_rhythm = Counter(r["rhythm"] for r in rows)
    return {
        "rows": len(rows),
        "by_kind": dict(by_kind),
        "by_rhythm": {r: by_rhythm.get(r, 0) for r in RHYTHMS},
        "by_line_len": {
            str(k): v for k, v in sorted(Counter(r["line_len"] for r in rows).items())
        },
        "by_blank_pos": {
            str(k): v for k, v in sorted(Counter(r["blank_pos"] for r in rows).items())
        },
        "peaked_rows": sum(1 for s in supports if s == 1),
        "stem_rows": by_kind.get("stem", 0),
        "cross_rhythm_rows": sum(1 for r in rows if r["cross_rhythm"]),
        "mean_entropy_nats": round(_entropy(rows), 4),
        "order": order_structure(rows),
    }


def dump_jsonl(path: Path, rows: Sequence[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def load_jsonl(path: Path) -> List[dict]:
    rows = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def selftest() -> None:
    """Blank stays put. Orders do not collapse. Glue is not a target."""
    records = [
        {"tokens": ["mary", "had", "a", "little", "lamb"], "rhythm": "dream"},
        {"tokens": ["lamb", "little", "a", "had", "mary"], "rhythm": "dream"},
        {"tokens": ["the", "seal", "holds"], "rhythm": "stabilize"},
        {"tokens": ["holds", "the", "seal"], "rhythm": "stabilize"},
        {"tokens": ["only"], "rhythm": "reflect"},
    ]
    # The live corpus is length 2-4. This selftest uses a longer proverb so
    # the blank's index is obvious. max_len on the encoder is a separate guard.
    built = build_rows(records[:1])
    contexts = {tuple(r["context"]): r for r in built}
    hole = ("mary", "had", "a", "little", BLANK)
    assert hole in contexts, contexts.keys()
    assert contexts[hole]["targets"] == {"lamb": 1}
    assert contexts[hole]["blank_pos"] == 4
    assert all("a" not in r["targets"] and "the" not in r["targets"] for r in built)
    # Two orders of the same line are not one row.
    both = build_rows(records[:2])
    assert len(both) > len(built)
    structure = order_structure(both)
    assert structure["multisets_with_several_orders"] > 0

    # Same remaining tokens, different hole, different target: a real conflict
    # for a bag encoder once the two contexts are permutations.
    conflict_src = [
        {"tokens": ["alpha", "beta"], "rhythm": "dream"},
        {"tokens": ["beta", "gamma"], "rhythm": "dream"},
    ]
    # hold beta from line 1 -> [alpha, BLANK] target beta
    # hold beta from... line 2 hold gamma -> [beta, BLANK] target gamma
    # those are different multisets. Build the permutation conflict directly:
    direct = [
        {"tokens": ["red", "blue", "green"], "rhythm": "explore"},
        {"tokens": ["green", "blue", "red"], "rhythm": "explore"},
    ]
    rows = build_rows(direct)
    # Holding out "blue" yields two orders of {red, BLANK, green}, same target.
    blue = [r for r in rows if r["targets"] == {"blue": 1}]
    assert len(blue) == 2, blue
    assert order_structure(rows)["rows_in_agreed_orders"] >= 2

    clash = [
        {"tokens": ["red", "BLUE", "green"], "rhythm": "explore"},
        {"tokens": ["green", "RED", "blue"], "rhythm": "explore"},
    ]
    # Not a clean clash. Construct rows by hand through two lines that punch
    # different words and leave a permutation of the same context.
    clash = [
        {"tokens": ["x", "y", "z"], "rhythm": "explore"},
        {"tokens": ["z", "q", "x"], "rhythm": "explore"},
    ]
    clash_rows = build_rows(clash)
    # [x, BLANK, z] target y   and   [z, BLANK, x] target q
    pair = [r for r in clash_rows if set(r["context"]) == {"x", BLANK, "z"}]
    assert len(pair) == 2, clash_rows
    assert order_structure(clash_rows)["orders_whose_targets_disagree"] >= 1

    hold_rows, stats = filter_holdout(direct, direct)
    assert hold_rows == []
    assert stats["holdout_exact_contexts_dropped"] > 0
    fresh, _stats = filter_holdout(direct, clash)
    assert fresh, "a new order must be kept"
    tagged = tag_holdout_conflicts(clash_rows, fresh)
    assert tagged["holdout_rows_in_a_train_target_conflict"] > 0

    short = build_rows([{"tokens": ["only", "the"], "rhythm": "reflect"}])
    assert short == []
    print("corpus selftest ok", flush=True)
