"""Train the S3 mix curve. One corpus, two gates, several coverage ratios.

recur_fraction is recurring-stem rows / all training rows. Broad rows are the
live leave-one-out completion file, kept in full until the fraction is 1.
The bar is 3x the recurring-stem rhythm unigram, and it does not fall when
broad rows dilute that marginal. Decode recall is the phase-0 mouth on the
live holdout.

    python -m tools.completion.s3_curve --fractions 1.0 --epochs 20 --dim 128
    python -m tools.completion.s3_curve --sweep --epochs 20 --dim 128
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from tools.completion.corpus import content_of, load_jsonl
from tools.completion.geometry import dump_json
from tools.completion.live_guard import REPO, assert_live_intact
from tools.completion.measure import unigram_baseline
from tools.voice.gen_recurring_stems import SCRATCH, mix_rows
from training.corpus import TRAIN_PATH, load_corpus

LOG = REPO / "docs" / "findings" / "logs" / "2026-09-23-phase-b"
SWEEP = (0.0, 0.2, 0.4, 0.6, 0.8, 1.0)


def _tag(fraction: float, seed: int) -> str:
    return f"_s3r{int(round(fraction * 100)):03d}s{seed}"


def _write(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=True) + "\n")


def _prepare(fraction: float, seed: int) -> tuple[Path, Path, dict]:
    broad = load_jsonl(SCRATCH / "broad_train.jsonl")
    recur = load_jsonl(SCRATCH / "recur_train.jsonl")
    hold = load_jsonl(SCRATCH / "recur_holdout.jsonl")
    # load_jsonl attaches a distribution. The trainer attaches it again.
    # Write counts only, plus the fields the trainer and the report need.
    def _plain(rows):
        out = []
        for row in rows:
            item = dict(row)
            item.pop("target_dist", None)
            item.pop("n_obs", None)
            item.pop("support", None)
            out.append(item)
        return out

    mixed, meta = mix_rows(_plain(broad), _plain(recur), fraction, seed)
    train_path = SCRATCH / f"mix_{_tag(fraction, seed)}_train.jsonl"
    hold_path = SCRATCH / "recur_holdout.jsonl"
    _write(train_path, mixed)
    meta["train_path"] = str(train_path)
    meta["hold_path"] = str(hold_path)
    meta["hold_rows"] = len(hold)
    return train_path, hold_path, meta


def _unigrams(train_path: Path, hold_path: Path) -> dict:
    live = load_corpus(TRAIN_PATH)
    vocab = sorted({t for rec in live for t in content_of(rec["tokens"])})
    train = load_jsonl(train_path)
    hold = load_jsonl(hold_path)
    # Recur-only marginal: broad rows must not be allowed to zero the bar.
    recur_only = [r for r in train if r.get("source") == "recur"]
    if not recur_only:
        recur_only = load_jsonl(SCRATCH / "recur_train.jsonl")
    out = {}
    for split in ("novel", "novel_tuple", "unseen_kernel", "seen"):
        sub = [r for r in hold if r.get("split") == split]
        mixed = unigram_baseline(train, sub, vocab)
        recur = unigram_baseline(recur_only, sub, vocab)
        bar = max(mixed["mode_top1"], recur["mode_top1"])
        out[split] = {
            "mixed_unigram": mixed["mode_top1"],
            "recur_unigram": recur["mode_top1"],
            "bar_3x": round(3 * bar, 4),
            "n": mixed["n"],
        }
    return out


def _score(report: dict, unigrams: dict) -> dict:
    snaps = report.get("snapshots") or []
    last = snaps[-1] if snaps else {}
    by = last.get("completion_holdout_by_split") or {}
    mouth = ((report.get("extras") or {}).get("legibility") or {}).get("holdout") or {}
    novel = (by.get("novel") or {}).get("mode_top1")
    tuple_top = (by.get("novel_tuple") or {}).get("mode_top1")
    # The gate is a partner-tuple that was never a training bag. The OOV
    # slice (a partner token absent from train) is reported beside it.
    bar = unigrams["novel_tuple"]["bar_3x"]
    oov_bar = unigrams["novel"]["bar_3x"]
    recall = mouth.get("recall@k")
    return {
        "novel_top1": tuple_top,
        "novel_oov_top1": novel,
        "novel_tuple_top1": tuple_top,
        "unseen_kernel_top1": (by.get("unseen_kernel") or {}).get("mode_top1"),
        "seen_top1": (by.get("seen") or {}).get("mode_top1"),
        "train_top1": last.get("completion_train_mode_top1"),
        "recall@8": recall,
        "median_true_rank": mouth.get("median_true_rank"),
        "output_pr": last.get("live_holdout_participation"),
        "bar_3x_novel": bar,
        "bar_3x_oov": oov_bar,
        "novel_clears": None if tuple_top is None else bool(tuple_top + 1e-9 >= bar),
        "oov_clears": None if novel is None else bool(novel + 1e-9 >= oov_bar),
        "mouth_clears": None if recall is None else bool(recall + 1e-9 >= 0.60),
        "curve": [
            {
                "epoch": s.get("epoch"),
                "novel_oov_top1": (s.get("completion_holdout_by_split") or {}).get("novel", {}).get("mode_top1"),
                "novel_tuple_top1": (s.get("completion_holdout_by_split") or {}).get("novel_tuple", {}).get("mode_top1"),
                "unseen_kernel_top1": (s.get("completion_holdout_by_split") or {}).get("unseen_kernel", {}).get("mode_top1"),
                "output_pr": s.get("live_holdout_participation"),
            }
            for s in snaps
        ],
    }


def _train(fraction: float, epochs: int, dim: int, seed: int, legibility: bool) -> dict:
    live = assert_live_intact()
    train_path, hold_path, meta = _prepare(fraction, seed)
    unigrams = _unigrams(train_path, hold_path)
    tag = _tag(fraction, seed)
    cmd = [
        sys.executable, "-m", "tools.completion.train",
        "--dim", str(dim),
        "--epochs", str(epochs),
        "--seed", str(seed),
        "--batch-size", "128",
        "--lr", "0.01",
        "--weight-decay", "0",
        "--rhythm-weight", "0",
        "--cond-scale", "0",
        "--residual",
        "--tag", tag,
        "--train-rows", str(train_path),
        "--hold-rows", str(hold_path),
    ]
    if legibility:
        cmd.append("--legibility")
    print("RUN " + " ".join(cmd), flush=True)
    subprocess.run(cmd, check=True, cwd=str(REPO))
    report_path = (
        REPO / "docs" / "findings" / "logs" / "2026-09-23-completion"
        / f"train_dim{dim}{tag}_s{seed}.json"
    )
    report = json.loads(report_path.read_text(encoding="utf-8"))
    scored = _score(report, unigrams)
    point = {
        "recur_fraction": fraction,
        "broad_to_recur": meta["broad_to_recur"],
        "broad_rows": meta["broad_rows"],
        "recur_rows": meta["recur_rows"],
        "mixed_rows": meta["mixed_rows"],
        "dim": dim,
        "epochs": epochs,
        "seed": seed,
        "tag": tag,
        "report": str(report_path.relative_to(REPO)).replace("\\", "/"),
        "live_sha256": live,
        "unigram": unigrams,
        **scored,
        "both_clear": bool(scored["novel_clears"] and scored["mouth_clears"]),
    }
    print(
        f"POINT frac {fraction}  novel {scored['novel_top1']}  "
        f"tuple {scored['novel_tuple_top1']}  unseen {scored['unseen_kernel_top1']}  "
        f"bar {scored['bar_3x_novel']}  recall {scored['recall@8']}  "
        f"both {point['both_clear']}",
        flush=True,
    )
    assert_live_intact()
    return point


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fractions", default="", help="comma list, e.g. 0,0.4,1")
    ap.add_argument("--sweep", action="store_true")
    ap.add_argument("--epochs", type=int, default=20)
    ap.add_argument("--dim", type=int, default=128)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--no-legibility", action="store_true")
    ap.add_argument("--append", action="store_true")
    args = ap.parse_args()
    if args.sweep:
        fractions = list(SWEEP)
    elif args.fractions:
        fractions = [float(x) for x in args.fractions.split(",") if x.strip()]
    else:
        raise SystemExit("pass --fractions or --sweep")
    out = LOG / f"s3_curve_dim{args.dim}_e{args.epochs}.json"
    points = []
    if args.append and out.is_file():
        points = json.loads(out.read_text(encoding="utf-8")).get("points") or []
    for fraction in fractions:
        point = _train(
            fraction, args.epochs, args.dim, args.seed, not args.no_legibility,
        )
        points.append(point)
        payload = {
            "dim": args.dim,
            "epochs": args.epochs,
            "seed": args.seed,
            "gate": {
                "novel_top1": "novel_tuple >= 3x the recur-stem rhythm unigram (higher of mixed and recur-only). OOV partner tokens are reported separately and are not the bar.",
                "recall@8": ">= 0.60 on the live holdout mouth",
            },
            "points": points,
            "any_both_clear": any(p["both_clear"] for p in points),
        }
        dump_json(str(out), payload)
        print(f"CURVE {out}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
