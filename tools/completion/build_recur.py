"""Bigger completion corpus: the same stem, many times, with many fillers.

The live leave-one-out file is mostly one context, one filler, seen once.
A holdout context then has nothing to generalize from. This builder does
not touch that file or the live corpus. It writes a second pair under
rfe/scratch/completion/.

A stem is one rhythm-pure content pivot. The pivot recurs as the bare
context and inside many similar contexts (the pivot plus partner content
words the stem has not used yet). Every context of a stem shares one
filler distribution: a mode plus five other rhythm-appropriate fillers.
Glue is stored as a surface scaffold and is not pooled into the context.
A fixed glue frame was measured (the gluepad arm) and it erased the geometry.

Holdout splits, tagged on each row:
  similar   same pivot, partner tuple never in train. The generalization test.
  novel     pivot never in train. Negative control. Should sit near the unigram.
  seen      a copy of a train context. Ceiling, not a generalization claim.

    python -m tools.completion.build_recur
"""

from __future__ import annotations

import json
import random
import sys
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path

from tools.completion.corpus import GLUE, content_of
from tools.completion.geometry import dump_json
from tools.completion.live_guard import REPO, assert_live_intact, sha256
from tools.completion.measure import unigram_baseline
from training.corpus import RHYTHMS, TRAIN_PATH, corpus_version, load_corpus

SCRATCH = REPO.parent / "scratch" / "completion"
SEED = 0
# mode 11, five others at 2. Mode probability 11/21 ≈ 0.524.
MODE_COUNT = 11
OTHER_COUNT = 2
OTHERS = 5


def _majority(records) -> dict:
    """Content word -> rhythm, if one rhythm has at least 3/4 of its occurrences."""
    counts = defaultdict(Counter)
    for rec in records:
        rhythm = rec["rhythm"]
        if rhythm not in RHYTHMS:
            raise ValueError(f"unknown rhythm {rhythm}")
        for token in content_of(rec["tokens"]):
            counts[token][rhythm] += 1
    assigned = {r: [] for r in RHYTHMS}
    skipped = 0
    for token, ctr in counts.items():
        total = sum(ctr.values())
        best = max(ctr.values())
        if best / total < 0.75:
            skipped += 1
            continue
        for rhythm in RHYTHMS:
            if ctr[rhythm] == best:
                assigned[rhythm].append(token)
                break
    for rhythm in RHYTHMS:
        assigned[rhythm] = sorted(assigned[rhythm])
    return assigned, skipped


def _allocate(words, rng):
    words = list(words)
    rng.shuffle(words)
    n = len(words)
    # Wide filler inventory so a rhythm unigram's top-8 is not the whole
    # support. Eight fillers made recall@8 trivial for the marginal.
    n_fill = 16 if n >= 64 else 8
    n_novel = 4 if n >= 36 else 2
    n_pivot = min(32, max(8, (n - n_fill - n_novel) // 3))
    n_partner = n - n_fill - n_novel - n_pivot
    if n_partner < 12:
        n_pivot = max(6, n_pivot - (12 - n_partner))
        n_partner = n - n_fill - n_novel - n_pivot
    if min(n_fill, n_pivot, n_partner) < 6 or n_novel < 2:
        raise SystemExit(
            f"not enough rhythm-pure words ({n}): "
            f"fill {n_fill} novel {n_novel} pivot {n_pivot} partner {n_partner}"
        )
    i0 = 0
    fillers = words[i0:i0 + n_fill]
    i0 += n_fill
    novel = words[i0:i0 + n_novel]
    i0 += n_novel
    pivots = words[i0:i0 + n_pivot]
    i0 += n_pivot
    partners = words[i0:]
    return fillers, novel, pivots, partners


def _targets(fillers, index: int) -> dict:
    mode = fillers[index % len(fillers)]
    others = []
    step = 0
    while len(others) < OTHERS:
        word = fillers[(index + 1 + step) % len(fillers)]
        if word != mode and word not in others:
            others.append(word)
        step += 1
        if step > len(fillers) + 2:
            break
    targets = {mode: MODE_COUNT}
    for word in others:
        targets[word] = OTHER_COUNT
    return targets


def _row(context, rhythm, targets, stem, split, kind) -> dict:
    if any(t in GLUE for t in context):
        raise AssertionError(f"glue in context: {context}")
    return {
        "context": list(context),
        "rhythm": rhythm,
        "targets": targets,
        "kind": kind,
        "n_content": len(context),
        "cross_rhythm": False,
        "split": split,
        "stem": stem,
        "scaffold": ["the", *context, "of", "a"],
    }


def _contexts_for_pivot(pivot, partners, rng):
    """Train and holdout partner frames. Exact tuples do not cross the split."""
    pairs = list(combinations(partners, 2))
    rng.shuffle(pairs)
    n_3_train = min(220, max(0, len(pairs) - 40))
    n_3_hold = min(36, max(0, len(pairs) - n_3_train))
    two = list(partners)
    rng.shuffle(two)
    n_2_train = min(20, max(0, len(two) - 8))
    n_2_hold = min(8, max(0, len(two) - n_2_train))
    train = [[pivot]]
    train += [[pivot, p] for p in two[:n_2_train]]
    train += [[pivot, a, b] for a, b in pairs[:n_3_train]]
    hold = [[pivot, p] for p in two[n_2_train:n_2_train + n_2_hold]]
    hold += [[pivot, a, b] for a, b in pairs[n_3_train:n_3_train + n_3_hold]]
    return train, hold


def _write(path: Path, rows) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=True) + "\n")


def _key(row) -> tuple:
    return (row["rhythm"], tuple(row["context"]))


def build(records) -> tuple[list, list, dict]:
    rng = random.Random(SEED)
    assigned, skipped = _majority(records)
    train_rows = []
    hold_rows = []
    per_rhythm = {}
    for rhythm in RHYTHMS:
        print(f"pure {rhythm} {len(assigned[rhythm])}", flush=True)
        fillers, novel, pivots, partners = _allocate(assigned[rhythm], rng)
        per_rhythm[rhythm] = {
            "pure_words": len(assigned[rhythm]),
            "pivots": len(pivots),
            "novel_pivots": len(novel),
            "fillers": len(fillers),
            "partners": len(partners),
        }
        for i, pivot in enumerate(pivots):
            targets = _targets(fillers, i)
            train_ctx, hold_ctx = _contexts_for_pivot(pivot, partners, rng)
            for ctx in train_ctx:
                train_rows.append(_row(sorted(ctx), rhythm, targets, pivot, "train", "recur"))
            for ctx in hold_ctx:
                hold_rows.append(_row(sorted(ctx), rhythm, targets, pivot, "similar", "recur"))
        for i, pivot in enumerate(novel):
            targets = _targets(fillers, i + len(pivots))
            _train_unused, hold_ctx = _contexts_for_pivot(pivot, partners, rng)
            # A handful of unseen frames, not the whole partner grid.
            for ctx in hold_ctx[:12]:
                hold_rows.append(_row(sorted(ctx), rhythm, targets, pivot, "novel", "recur"))

    train_keys = {_key(r) for r in train_rows}
    similar = [r for r in hold_rows if r["split"] == "similar"]
    novel_rows = [r for r in hold_rows if r["split"] == "novel"]
    if any(_key(r) in train_keys for r in similar):
        raise AssertionError("similar holdout context leaked into train")
    if any(_key(r) in train_keys for r in novel_rows):
        raise AssertionError("novel holdout context leaked into train")
    train_stems = {r["stem"] for r in train_rows}
    if any(r["stem"] in train_stems for r in novel_rows):
        raise AssertionError("novel pivot was used as a train stem")

    seen_ix = list(range(len(train_rows)))
    rng.shuffle(seen_ix)
    n_seen = min(2000, max(1, len(train_rows) // 12))
    for i in seen_ix[:n_seen]:
        row = dict(train_rows[i])
        row["split"] = "seen"
        hold_rows.append(row)

    def _sort(rows):
        rows.sort(key=lambda r: (RHYTHMS.index(r["rhythm"]), r["stem"], r["context"], r["split"]))

    _sort(train_rows)
    _sort(hold_rows)
    per_stem = Counter(r["stem"] for r in train_rows)
    summary = {
        "seed": SEED,
        "skipped_ambiguous_content_words": skipped,
        "per_rhythm": per_rhythm,
        "train_rows": len(train_rows),
        "holdout_rows": len(hold_rows),
        "holdout_by_split": dict(Counter(r["split"] for r in hold_rows)),
        "stems": len(per_stem),
        "contexts_per_stem_min": min(per_stem.values()),
        "contexts_per_stem_mean": round(sum(per_stem.values()) / len(per_stem), 2),
        "contexts_per_stem_max": max(per_stem.values()),
        "fillers_per_stem": 1 + OTHERS,
        "mode_count": MODE_COUNT,
        "other_count": OTHER_COUNT,
        "glue": "scaffold field only (the ... of a); not in the context and not a target",
        "by_context_len_train": dict(Counter(len(r["context"]) for r in train_rows)),
    }
    return train_rows, hold_rows, summary


def main() -> int:
    live = assert_live_intact()
    records = load_corpus(TRAIN_PATH)
    train_rows, hold_rows, summary = build(records)
    # Targets have to be content words of the live train file. The allocator
    # only draws from those, so this is a guard against a later edit.
    vocab = {t for rec in records for t in content_of(rec["tokens"])}
    stray = sorted({w for r in train_rows + hold_rows for w in r["targets"] if w not in vocab})
    if stray:
        raise SystemExit(f"target outside live content vocab: {stray[:6]}")
    if any(t in GLUE for r in train_rows + hold_rows for t in r["context"]):
        raise SystemExit("glue landed in a context")

    train_path = SCRATCH / "completion_recur_train.jsonl"
    hold_path = SCRATCH / "completion_recur_holdout.jsonl"
    _write(train_path, train_rows)
    _write(hold_path, hold_rows)

    from tools.completion.corpus import load_jsonl

    loaded_train = load_jsonl(train_path)
    loaded_hold = load_jsonl(hold_path)
    similar = [r for r in loaded_hold if r.get("split") == "similar"]
    novel = [r for r in loaded_hold if r.get("split") == "novel"]
    seen = [r for r in loaded_hold if r.get("split") == "seen"]
    vocab_list = sorted(vocab)
    summary["unigram_similar"] = unigram_baseline(loaded_train, similar, vocab_list)
    summary["unigram_novel"] = unigram_baseline(loaded_train, novel, vocab_list)
    summary["unigram_seen"] = unigram_baseline(loaded_train, seen, vocab_list)
    summary["corpus_version"] = corpus_version()
    summary["live_sha256"] = live
    summary["files"] = {
        "train": str(train_path),
        "holdout": str(hold_path),
        "train_sha256": sha256(train_path),
        "holdout_sha256": sha256(hold_path),
    }
    report_path = SCRATCH / "build_recur_report.json"
    dump_json(str(report_path), summary)
    dump_json(
        str(REPO / "docs" / "findings" / "logs" / "2026-09-23-completion" / "build_recur_report.json"),
        summary,
    )
    assert_live_intact()
    print(
        f"train {summary['train_rows']}  stems {summary['stems']}  "
        f"contexts/stem {summary['contexts_per_stem_min']}-"
        f"{summary['contexts_per_stem_mean']}-{summary['contexts_per_stem_max']}  "
        f"hold {summary['holdout_by_split']}",
        flush=True,
    )
    print(
        f"unigram similar mode_top1 {summary['unigram_similar'].get('mode_top1')}  "
        f"peaked {summary['unigram_similar'].get('peaked_top1')}  "
        f"ce {summary['unigram_similar'].get('ce')}",
        flush=True,
    )
    print(f"WROTE {train_path}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
