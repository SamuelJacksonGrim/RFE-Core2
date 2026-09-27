"""Write the completion corpus under rfe/scratch. Does not touch data/corpus/.

    python -m tools.completion.build_corpus
"""

from __future__ import annotations

import sys
from pathlib import Path

from tools.completion.corpus import (
    build_rows,
    content_of,
    distribution_rank,
    filter_holdout,
    selftest,
    summarize,
    dump_jsonl,
)
from tools.completion.geometry import dump_json
from tools.completion.live_guard import REPO, assert_live_intact, sha256
from training.corpus import HOLDOUT_PATH, TRAIN_PATH, corpus_version, load_corpus

SCRATCH = REPO.parent / "scratch" / "completion"


def _bag_stats(records) -> dict:
    bags = []
    short = 0
    for rec in records:
        words = content_of(rec["tokens"])
        if len(words) < 2:
            short += 1
            continue
        bags.append((rec["rhythm"], frozenset(words)))
    return {
        "records": len(records),
        "fewer_than_2_content": short,
        "content_bags": len(bags),
        "unique_content_bags": len(set(bags)),
        "order_invariant_dupes_dropped": len(bags) - len(set(bags)),
    }


def main() -> int:
    selftest()
    print("selftest ok", flush=True)
    live = assert_live_intact()
    train = load_corpus(TRAIN_PATH)
    hold = load_corpus(HOLDOUT_PATH)

    train_rows = build_rows(train)
    hold_rows, hold_stats = filter_holdout(train, hold)
    # Every holdout target has to be a train content word. The live split
    # already promises this; say so in the report if it ever breaks.
    train_words = {t for rec in train for t in content_of(rec["tokens"])}
    stray = sorted({w for r in hold_rows for w in r["targets"] if w not in train_words})
    if stray:
        raise SystemExit(f"holdout targets absent from train content vocab: {stray[:8]}")

    scratch_train = SCRATCH / "completion_train.jsonl"
    scratch_hold = SCRATCH / "completion_holdout.jsonl"
    dump_jsonl(scratch_train, train_rows)
    dump_jsonl(scratch_hold, hold_rows)

    report = {
        "corpus_version": corpus_version(),
        "context": "content words only, sorted, no glue pad",
        "live_sha256": live,
        "source_train": _bag_stats(train),
        "source_holdout": _bag_stats(hold),
        "train": summarize(train_rows),
        "holdout": summarize(hold_rows),
        "holdout_filter": hold_stats,
        "train_distribution_rank": distribution_rank(train_rows),
        "files": {
            "train": str(scratch_train),
            "holdout": str(scratch_hold),
            "train_sha256": sha256(scratch_train),
            "holdout_sha256": sha256(scratch_hold),
        },
    }
    report_path = SCRATCH / "build_report.json"
    dump_json(str(report_path), report)
    committed = REPO / "docs" / "findings" / "logs" / "2026-09-23-completion" / "build_report.json"
    dump_json(str(committed), report)
    # Confirm the build did not move the live files.
    assert_live_intact()
    tr = report["train"]
    print(
        f"train rows {tr['rows']}  peaked {tr['peaked_rows']}  "
        f"distinct peaked targets {tr['distinct_peaked_targets']}  "
        f"stem {tr['stem_rows']}  cross-rhythm {tr['cross_rhythm_rows']}  "
        f"dist rank {report['train_distribution_rank']}",
        flush=True,
    )
    print(f"holdout rows {report['holdout']['rows']}  dropped bags {hold_stats}", flush=True)
    print(f"WROTE {scratch_train}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
