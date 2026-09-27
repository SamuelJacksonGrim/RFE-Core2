"""Read separability + dimension population off an existing checkpoint.

Does not train, does not step the field, does not write weights.

    python -m tools.dim256.readout --dim 128 \
        --weights data/checkpoints/generator_weights_5rhythm.pt \
        --ecology data/checkpoints/generator_ecology_5rhythm.json
"""
from __future__ import annotations

import argparse
import sys

from tools.dim256.geometry import dump_json, report_checkpoint
from training.corpus import HOLDOUT_PATH, TRAIN_PATH


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dim", type=int, required=True)
    ap.add_argument("--weights", required=True)
    ap.add_argument("--ecology", required=True)
    ap.add_argument("--split", choices=("holdout", "train"), default="holdout")
    ap.add_argument("--report", default="")
    args = ap.parse_args()
    path = HOLDOUT_PATH if args.split == "holdout" else TRAIN_PATH
    rep = report_checkpoint(args.dim, args.weights, args.ecology, path)
    out = args.report or (
        f"docs/findings/logs/2026-09-23-dim256/readout_dim{args.dim}_{args.split}.json"
    )
    dump_json(out, rep)
    sep = rep["separability"]
    pop = rep["population"]
    print(f"REPORT {out}", flush=True)
    print(
        f"dim={args.dim} split={args.split} n={rep['n']} "
        f"encode~generate cos={rep['encode_matches_generate_cos']}",
        flush=True,
    )
    print(f"worst_pair {sep['worst_pair']}", flush=True)
    print(f"best_separated {sep['best_separated_pair']}", flush=True)
    print(
        f"offdiag mean/max/min {sep['offdiag_mean']} / {sep['offdiag_max']} / {sep['offdiag_min']}",
        flush=True,
    )
    print(f"within {sep['within_centroid_cos']}", flush=True)
    print(
        f"population PR={pop['participation_ratio']} eff_rank={pop['eff_rank_512cap']} "
        f"quiet={pop['quiet_dims_lt_1pct_median']}/{pop['dim']} "
        f"dead={pop['dead_dims_std_lt_1e-3']} std_min={pop['per_dim_std_min']:.5f}",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
