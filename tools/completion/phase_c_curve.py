"""Phase C frontier. Same S3 grid, causal RoPE readout instead of mean-pool.

Recur rows are presented as [kernel_0, kernel_1, vary]. The token set is the
set the mean-pool run trained on, so that table is still the control. Broad
rows keep their authored context. The gate is the S3 gate: novel-tuple top-1
at least 3x the recur-stem rhythm unigram, and live-holdout recall@8 at least
0.60, at the same time.

    python -m tools.completion.phase_c_curve --check
    python -m tools.completion.phase_c_curve --fractions 1.0 --epochs 1 --tag-prefix _phasec_smoke
    python -m tools.completion.phase_c_curve --sweep --epochs 80 --dim 128
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

from tools.completion.corpus import load_jsonl
from tools.completion.geometry import dump_json
from tools.completion.live_guard import REPO, assert_live_intact
from tools.completion.s3_curve import _score, _unigrams
from tools.order.sequence import role_order_row
from tools.voice.gen_recurring_stems import SCRATCH, mix_rows

LOG = REPO / "docs" / "findings" / "logs" / "2026-09-23-phase-c"
MEAN_POOL = REPO / "docs" / "findings" / "logs" / "2026-09-23-phase-b" / "s3_frontier.json"
# 0.70 is on the published frontier. The S3 helper's SWEEP tuple omitted it.
SWEEP = (0.0, 0.20, 0.40, 0.60, 0.70, 0.80, 1.00)


def _tag(fraction: float, seed: int, prefix: str) -> str:
    return f"{prefix}_r{int(round(fraction * 100)):03d}s{seed}"


def _write(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=True) + "\n")


def _plain(rows: list[dict]) -> list[dict]:
    out = []
    for row in rows:
        item = dict(row)
        item.pop("target_dist", None)
        item.pop("n_obs", None)
        item.pop("support", None)
        out.append(item)
    return out


def _prepare(fraction: float, seed: int, prefix: str) -> tuple[Path, Path, dict]:
    broad = _plain(load_jsonl(SCRATCH / "broad_train.jsonl"))
    recur = _plain(load_jsonl(SCRATCH / "recur_train.jsonl"))
    hold = [role_order_row(row) for row in _plain(load_jsonl(SCRATCH / "recur_holdout.jsonl"))]
    mixed, meta = mix_rows(broad, recur, fraction, seed)
    mixed = [role_order_row(row) for row in mixed]
    tag = _tag(fraction, seed, prefix)
    train_path = SCRATCH / f"phasec_mix_{tag}_train.jsonl"
    hold_path = SCRATCH / "phasec_recur_holdout.jsonl"
    _write(train_path, mixed)
    _write(hold_path, hold)
    meta["train_path"] = str(train_path)
    meta["hold_path"] = str(hold_path)
    meta["hold_rows"] = len(hold)
    meta["presentation"] = "role order on recur rows; authored order on broad rows"
    return train_path, hold_path, meta


def _checkpoint_paths(dim: int, tag: str) -> list[Path]:
    return [
        REPO / f"data/checkpoints/sequence_encoder_phasec_{dim}{tag}.pt",
        REPO / f"data/checkpoints/sequence_encoder_phasec_{dim}{tag}.json",
        REPO / f"data/checkpoints/completion_head_{dim}{tag}.pt",
    ]


def _clear_our_checkpoints(dim: int, tag: str) -> None:
    for path in _checkpoint_paths(dim, tag):
        if path.name.startswith("banked_mouth") or "phaseb" in path.name:
            raise SystemExit(f"refusing to delete a banked file: {path}")
        if path.is_file():
            path.unlink()


def _check_role_order() -> None:
    recur = [role_order_row(row) for row in _plain(load_jsonl(SCRATCH / "recur_train.jsonl"))]
    hold = [role_order_row(row) for row in _plain(load_jsonl(SCRATCH / "recur_holdout.jsonl"))]
    broad = [role_order_row(row) for row in _plain(load_jsonl(SCRATCH / "broad_train.jsonl"))]
    if not recur or not hold or not broad:
        raise SystemExit("S3 scratch files are empty")
    groups = defaultdict(set)
    for row in recur + hold:
        if row["presentation"] != "role":
            raise SystemExit("a recur row was not role-ordered")
        if row["context"][: len(row["kernel"])] != list(row["kernel"]):
            raise SystemExit("kernel is not the prefix")
        if row["context"][-1] != row["vary"]:
            raise SystemExit("vary is not the last position")
        key = (row["rhythm"], row["domain"], tuple(row["kernel"]))
        groups[key].add(tuple(row["context"][:2]))
    moved = [key for key, stems in groups.items() if len(stems) != 1]
    if moved:
        raise SystemExit(f"{len(moved)} kernels change position across surfaces")
    if any(row["presentation"] != "authored" or row["context"] == [] for row in broad):
        raise SystemExit("broad presentation changed")
    # Unseen kernels have no trained pair. They are still a 3-token role order.
    splits = sorted({row["split"] for row in hold})
    print(
        f"role order ok  train {len(recur)}  hold {len(hold)}  "
        f"broad {len(broad)}  kernels {len(groups)}  splits {splits}",
        flush=True,
    )


def _point_from_report(report: dict, meta: dict, unigrams: dict, live: dict, fraction, epochs, dim, seed, tag, report_path: Path) -> dict:
    scored = _score(report, unigrams)
    extras = report.get("extras") or {}
    order = extras.get("order") or {}
    content = (extras.get("legibility_content_only") or {}).get("holdout") or {}
    recur_uni = unigrams["novel_tuple"]["recur_unigram"]
    tuple_top = scored["novel_tuple_top1"]
    ratio = None if tuple_top is None or not recur_uni else round(tuple_top / recur_uni, 3)
    point = {
        "encoder": "rope",
        "presentation": meta["presentation"],
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
        "tuple_over_recur_unigram": ratio,
        "order": order,
        "content_recall@8": content.get("recall@k"),
        **scored,
        "both_clear": bool(scored["novel_clears"] and scored["mouth_clears"]),
    }
    print(
        f"POINT frac {fraction}  tuple {scored['novel_tuple_top1']} ({ratio}x)  "
        f"oov {scored['novel_oov_top1']}  recall {scored['recall@8']}  "
        f"content_recall {point['content_recall@8']}  "
        f"rev_cos {order.get('reverse_cosine')}  both {point['both_clear']}",
        flush=True,
    )
    return point


def _train(fraction: float, epochs: int, dim: int, seed: int, prefix: str, force: bool) -> dict:
    live = assert_live_intact()
    train_path, hold_path, meta = _prepare(fraction, seed, prefix)
    unigrams = _unigrams(train_path, hold_path)
    tag = _tag(fraction, seed, prefix)
    report_path = (
        REPO / "docs" / "findings" / "logs" / "2026-09-23-completion"
        / f"train_dim{dim}{tag}_s{seed}.json"
    )
    if force or not report_path.is_file():
        _clear_our_checkpoints(dim, tag)
        if report_path.is_file():
            report_path.unlink()
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
            "--encoder", "rope",
            "--legibility",
            "--tag", tag,
            "--train-rows", str(train_path),
            "--hold-rows", str(hold_path),
        ]
        print("RUN " + " ".join(cmd), flush=True)
        subprocess.run(cmd, check=True, cwd=str(REPO))
    else:
        print(f"SKIP train, report exists {report_path}", flush=True)
    report = json.loads(report_path.read_text(encoding="utf-8"))
    if int(report.get("epochs", -1)) != int(epochs):
        raise SystemExit(
            f"{report_path} has {report.get('epochs')} epochs, wanted {epochs}. "
            "Pass --force to retrain."
        )
    point = _point_from_report(
        report, meta, unigrams, live, fraction, epochs, dim, seed, tag, report_path,
    )
    assert_live_intact()
    return point


def _payload(dim: int, epochs: int, seed: int, points: list[dict]) -> dict:
    mean_pool = None
    if MEAN_POOL.is_file():
        mean_pool = json.loads(MEAN_POOL.read_text(encoding="utf-8"))
    bar = None
    for point in points:
        bar = point["unigram"]["novel_tuple"]["bar_3x"]
        break
    return {
        "encoder": "causal RoPE readout, orthogonal to a prefix-mean anchor (all but the last token), unit-norm",
        "presentation": "recur rows as [kernel_0, kernel_1, vary]; broad rows authored",
        "dim": dim,
        "epochs": epochs,
        "seed": seed,
        "gate": {
            "novel_tuple_top1": ">= 3x the recur-stem rhythm unigram, same bar as S3",
            "recall@8": ">= 0.60 on the live holdout mouth (full line, glue included)",
            "oov": "novel-token top-1 is reported against the mean-pool ceiling of ~0.30. It is not the joint gate.",
        },
        "bar_3x": bar,
        "points": points,
        "any_both_clear": any(p["both_clear"] for p in points),
        "max_oov_top1": max((p["novel_oov_top1"] or 0) for p in points) if points else None,
        "mean_pool_s3": mean_pool,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fractions", default="")
    parser.add_argument("--sweep", action="store_true")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--epochs", type=int, default=80)
    parser.add_argument("--dim", type=int, default=128)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--tag-prefix", default="_phasec")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    if args.check:
        _check_role_order()
        return 0
    if args.sweep:
        fractions = list(SWEEP)
    elif args.fractions:
        fractions = [float(x) for x in args.fractions.split(",") if x.strip()]
    else:
        raise SystemExit("pass --fractions, --sweep, or --check")
    out = LOG / f"frontier_dim{args.dim}_e{args.epochs}.json"
    points = []
    if out.is_file() and not args.force:
        points = json.loads(out.read_text(encoding="utf-8")).get("points") or []
    done = {(p["recur_fraction"], p["seed"]) for p in points}
    for fraction in fractions:
        if (fraction, args.seed) in done and not args.force:
            print(f"SKIP curve point {fraction}", flush=True)
            continue
        if args.force:
            points = [p for p in points if not (p["recur_fraction"] == fraction and p["seed"] == args.seed)]
        point = _train(fraction, args.epochs, args.dim, args.seed, args.tag_prefix, args.force)
        points.append(point)
        dump_json(str(out.relative_to(REPO)).replace("\\", "/"), _payload(args.dim, args.epochs, args.seed, points))
        print(f"CURVE {out}", flush=True)
    print("PHASEC_DONE", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
