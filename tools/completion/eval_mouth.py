"""Phase-0 mouth plus both participation points, on one checkpoint.

The residual flag is inference-only here. It does not train.

    python -m tools.completion.eval_mouth --dim 128 --tag emb_resid_infer --residual \
        --weights data/checkpoints/generator_weights_completion_128_emb.pt \
        --ecology data/checkpoints/generator_ecology_completion_128_emb.json
"""

from __future__ import annotations

import argparse
import sys

from tools.completion.geometry import dump_json, load_generator
from tools.completion.live_guard import REPO, assert_live_intact
from tools.completion.measure import legibility
from tools.completion.train import _measure_points
from training.corpus import HOLDOUT_PATH, TRAIN_PATH, corpus_version, load_corpus

LOG = REPO / "docs" / "findings" / "logs" / "2026-09-23-completion"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dim", type=int, required=True)
    ap.add_argument("--weights", required=True)
    ap.add_argument("--ecology", required=True)
    ap.add_argument("--tag", required=True)
    ap.add_argument("--residual", action="store_true")
    args = ap.parse_args()

    live = assert_live_intact()
    train = load_corpus(TRAIN_PATH)
    hold = load_corpus(HOLDOUT_PATH)
    gen = load_generator(args.dim, str(REPO / args.weights), str(REPO / args.ecology))
    gen.embedding_residual = bool(args.residual)
    print(
        f"mouth {args.tag}  dim {args.dim}  residual {bool(args.residual)}  "
        f"device {gen.device}",
        flush=True,
    )
    points = _measure_points(gen, [r["tokens"] for r in hold])
    print(
        f"out_PR {points['output']['participation_ratio']}  "
        f"emb_PR {points['embedding_mean']['participation_ratio']}  "
        f"stack_PR {points['stack']['participation_ratio']}  "
        f"eff_out {points['output']['eff_rank_512cap']}",
        flush=True,
    )
    mouth = legibility(gen, train, hold, args.dim)
    print(f"legibility holdout {mouth['holdout']}", flush=True)
    payload = {
        "tag": args.tag,
        "dim": args.dim,
        "weights": args.weights,
        "embedding_residual": bool(args.residual),
        "corpus_version": corpus_version(),
        "points_live_holdout": points,
        "legibility": mouth,
        "live_sha256": live,
    }
    path = LOG / f"mouth_{args.tag}.json"
    dump_json(str(path), payload)
    assert_live_intact()
    print(f"REPORT {path}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
