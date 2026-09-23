"""Build the ordered rows, train every readout at 128 and 256, then measure.

One process, one GPU, sequential. Does not take the card exclusively.
"""

from __future__ import annotations

import json
import sys
import traceback

from tools.order.corpus import (
    build_rows,
    dump_jsonl,
    filter_holdout,
    line_order_pairs,
    summarize,
    tag_holdout_conflicts,
)
from tools.order.encoder import READOUTS
from tools.order.guard import MAIN, REPO, SCRATCH, assert_live_intact, assert_safe_output
from tools.order.measure import main as measure_main
from tools.order.test_encoder import main as test_main
from tools.order.train import train_one
from training.corpus import load_corpus

LOG = REPO / "docs" / "findings" / "logs" / "2026-09-23-order-aware"


def build() -> dict:
    live = assert_live_intact()
    train = load_corpus(MAIN / "data" / "corpus" / "rhythm_train.jsonl")
    hold = load_corpus(MAIN / "data" / "corpus" / "rhythm_holdout.jsonl")
    longest = max(len(r["tokens"]) for r in train + hold)
    if longest > 8:
        raise SystemExit(f"live line length {longest} exceeds encoder max_len 8")
    train_rows = build_rows(train)
    hold_rows, dropped = filter_holdout(train, hold)
    conflict = tag_holdout_conflicts(train_rows, hold_rows)
    report = {
        "live_sha256": live,
        "train_lines": line_order_pairs(train),
        "hold_lines": line_order_pairs(hold),
        "train": summarize(train_rows),
        "holdout": summarize(hold_rows),
        "holdout_filter": dropped,
        "holdout_conflict_tags": conflict,
    }
    SCRATCH.mkdir(parents=True, exist_ok=True)
    dump_jsonl(assert_safe_output(SCRATCH / "order_train.jsonl"), train_rows)
    dump_jsonl(assert_safe_output(SCRATCH / "order_holdout.jsonl"), hold_rows)
    out = LOG / "build_report.json"
    assert_safe_output(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2), flush=True)
    print(f"WROTE {SCRATCH / 'order_train.jsonl'} and build report", flush=True)
    return report


def main() -> int:
    if test_main() != 0:
        return 1
    build()
    assert_live_intact()
    failures = []
    for dim in (128, 256):
        for readout in READOUTS:
            try:
                train_one(dim=dim, readout=readout, epochs=40, seed=0)
            except Exception:
                failures.append(f"{readout} dim {dim}")
                traceback.print_exc()
            assert_live_intact()
    code = measure_main()
    if failures:
        print(f"TRAIN FAILURES: {failures}", flush=True)
        return 1
    return code


if __name__ == "__main__":
    sys.exit(main())
