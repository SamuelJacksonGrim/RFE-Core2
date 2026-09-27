"""Where participation lives, and what production recursive attention does to it.

Three vectors, on the live holdout lines:

  embedding_mean   masked mean of sqrt(dim)-scaled token embeddings,
                   before position and the transformer
  stack            Generator.forward with the residual flag forced off
                   (the post-transformer field vector the previous run measured)
  residual         same weights, orthogonal embedding-mean residual turned on
                   at inference. No extra training. A plumbing test.

RecursiveAttention is not part of Generator and was not in the completion
training graph. Production runs it untrained, under refine(), with
diversity_blend 0.60, after the generator vector (attractor pull is 0.15
and is not applied here). This probe runs that module at init, in eval, so
dropout is off and the number is the pooler rather than dropout noise.

    python -m tools.completion.probe_points
    python -m tools.completion.probe_points --self-check
"""

from __future__ import annotations

import argparse
import sys

import numpy as np
import torch

from agents.generator import Generator
from cognition.recursive_attention import RecursiveAttention
from tools.completion.geometry import (
    dump_json,
    embedding_means,
    encode_texts,
    load_generator,
    mean_cosine,
    population,
)
from tools.completion.live_guard import (
    FROZEN_ECOLOGY,
    FROZEN_WEIGHTS,
    REPO,
    assert_live_intact,
)
from training.corpus import HOLDOUT_PATH, TRAIN_PATH, load_corpus

LOG = REPO / "docs" / "findings" / "logs" / "2026-09-23-completion"


def _self_check() -> None:
    torch.manual_seed(0)
    gen = Generator(
        vocab_size=64, dim=32, depth=2, heads=4, ff_mult=4, dropout=0.0,
        auto_decay_interval=None,
    )
    gen.eval()
    lists = [["alpha", "beta"], ["alpha", "gamma"], ["beta", "delta"], ["alpha"]]
    gen.embedding_residual = False
    off = encode_texts(gen, lists)
    gen.embedding_residual = True
    on = encode_texts(gen, lists)
    gen.embedding_residual = False
    again = encode_texts(gen, lists)
    if not np.allclose(off, again):
        raise SystemExit("residual flag off did not restore the forward")
    if np.allclose(off, on):
        raise SystemExit("residual flag did not change the forward")
    emb = embedding_means(gen, lists)
    cos = mean_cosine(on, emb)
    # h = normalize(u + s_orth), u · s_orth = 0, ||s_orth|| <= 1,
    # so u · h >= 1/sqrt(2).
    if cos < 0.70:
        raise SystemExit(f"residual does not lock the embedding direction: cos {cos}")
    gen.embedding_residual = False
    print(f"self-check ok  cos(residual, embedding_mean) {cos:.4f}", flush=True)


def _refine_cloud(vecs: np.ndarray, dim: int, blend: float, isolated: bool, seed: int = 0) -> np.ndarray:
    torch.manual_seed(seed)
    ra = RecursiveAttention(
        dim=dim, heads=4, history_len=16, recursion_depth=3, dropout=0.1,
        diversity_blend=blend,
    )
    ra.eval()
    out = []
    ra.clear_history()
    for row in vecs:
        if isolated:
            ra.clear_history()
        out.append(ra.refine(np.asarray(row, dtype=np.float32)))
    return np.stack(out).astype(np.float64)


def _fresh(dim: int, surface_tokens, seed: int = 0) -> Generator:
    torch.manual_seed(seed)
    np.random.seed(seed)
    gen = Generator(
        vocab_size=8192, dim=dim, depth=4, heads=4, ff_mult=4, dropout=0.1,
        auto_decay_interval=None,
    )
    gen.eval()
    gen.encode_batch([[t] for t in surface_tokens])
    gen.eval()
    return gen


def _ra_block(vecs: np.ndarray, dim: int) -> dict:
    """Production blend, plus the two ends of the knob, on one cloud."""
    block = {}
    for blend, isolated, name in (
        (0.0, False, "stream_blend0"),
        (0.6, False, "stream_blend0.6"),
        (0.6, True, "isolated_blend0.6"),
        (1.0, False, "stream_blend1"),
    ):
        refined = _refine_cloud(vecs, dim, blend, isolated)
        pop = population(refined)
        block[name] = {
            "participation_ratio": pop["participation_ratio"],
            "eff_rank_512cap": pop["eff_rank_512cap"],
            "cos_to_input": round(mean_cosine(refined, vecs), 4),
        }
        print(
            f"  ra {name}  PR {pop['participation_ratio']}  "
            f"eff {pop['eff_rank_512cap']}  cos_in {block[name]['cos_to_input']}",
            flush=True,
        )
    return block


def _one(name: str, gen: Generator, lines) -> dict:
    dim = gen.dim
    print(f"=== {name} dim {dim} ===", flush=True)
    gen.embedding_residual = False
    field = encode_texts(gen, lines)
    emb = embedding_means(gen, lines)
    gen.embedding_residual = True
    residual = encode_texts(gen, lines)
    gen.embedding_residual = False

    def pack(cloud):
        pop = population(cloud)
        return {
            "participation_ratio": pop["participation_ratio"],
            "eff_rank_512cap": pop["eff_rank_512cap"],
            "quiet_dims": pop["quiet_dims_lt_1pct_median"],
            "dead_dims": pop["dead_dims_std_lt_1e-3"],
        }

    points = {
        "embedding_mean": pack(emb),
        "stack": pack(field),
        "residual_at_inference": pack(residual),
        "cos_stack_emb": round(mean_cosine(field, emb), 4),
        "cos_residual_emb": round(mean_cosine(residual, emb), 4),
    }
    print(
        f"  emb_PR {points['embedding_mean']['participation_ratio']}  "
        f"stack_PR {points['stack']['participation_ratio']}  "
        f"resid_PR {points['residual_at_inference']['participation_ratio']}  "
        f"cos_stack_emb {points['cos_stack_emb']}  "
        f"cos_resid_emb {points['cos_residual_emb']}",
        flush=True,
    )
    print("  recursive attention on the stack output", flush=True)
    points["ra_on_stack"] = _ra_block(field, dim)
    print("  recursive attention on the residual output", flush=True)
    points["ra_on_residual"] = _ra_block(residual, dim)
    return {"name": name, "dim": dim, "points": points}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--self-check", action="store_true")
    ap.add_argument(
        "--which",
        default="",
        help="comma-separated run names to keep; empty runs the full set",
    )
    args = ap.parse_args()
    _self_check()
    if args.self_check:
        return 0
    chosen = {n for n in args.which.split(",") if n}

    live = assert_live_intact()
    train = load_corpus(TRAIN_PATH)
    hold = load_corpus(HOLDOUT_PATH)
    surface = sorted({t for rec in train for t in rec["tokens"]})
    lines = [r["tokens"] for r in hold]
    print(f"live holdout lines {len(lines)}  surface {len(surface)}", flush=True)

    runs = []
    if not chosen or any(n.startswith("init") for n in chosen):
        for dim in (128, 256):
            if chosen and f"init{dim}" not in chosen:
                continue
            runs.append(_one(f"init{dim}", _fresh(dim, surface), lines))

    specs = [
        ("frozen128", 128, FROZEN_WEIGHTS, FROZEN_ECOLOGY),
        (
            "stack128_cbowlr",
            128,
            "data/checkpoints/generator_weights_completion_128_cbowlr.pt",
            "data/checkpoints/generator_ecology_completion_128_cbowlr.json",
        ),
        (
            "emb128",
            128,
            "data/checkpoints/generator_weights_completion_128_emb.pt",
            "data/checkpoints/generator_ecology_completion_128_emb.json",
        ),
        (
            "emb256",
            256,
            "data/checkpoints/generator_weights_completion_256_emb.pt",
            "data/checkpoints/generator_ecology_completion_256_emb.json",
        ),
        (
            "stack256",
            256,
            "data/checkpoints/generator_weights_completion_256_stack.pt",
            "data/checkpoints/generator_ecology_completion_256_stack.json",
        ),
        (
            "resid128",
            128,
            "data/checkpoints/generator_weights_completion_128_resid.pt",
            "data/checkpoints/generator_ecology_completion_128_resid.json",
        ),
        (
            "resid256",
            256,
            "data/checkpoints/generator_weights_completion_256_resid.pt",
            "data/checkpoints/generator_ecology_completion_256_resid.json",
        ),
        (
            "recur128",
            128,
            "data/checkpoints/generator_weights_completion_128_recur.pt",
            "data/checkpoints/generator_ecology_completion_128_recur.json",
        ),
        (
            "recur256",
            256,
            "data/checkpoints/generator_weights_completion_256_recur.pt",
            "data/checkpoints/generator_ecology_completion_256_recur.json",
        ),
    ]
    for name, dim, weights, ecology in specs:
        w = REPO / weights
        e = REPO / ecology
        if chosen and name not in chosen:
            continue
        if not (w.exists() and e.exists()):
            print(f"skip {name}: missing checkpoint", flush=True)
            continue
        gen = load_generator(dim, str(w), str(e))
        runs.append(_one(name, gen, lines))

    payload = {
        "live_holdout_lines": len(lines),
        "measurement": {
            "embedding_mean": "masked mean of sqrt(dim)-scaled token embeddings, pre-position",
            "stack": "Generator.forward, residual off. This is the previous run's participation.",
            "residual_at_inference": "orthogonal mix of embedding mean and stack, flag on, no retrain",
            "recursive_attention": (
                "untrained RecursiveAttention.refine, eval, history 16, depth 3, "
                "diversity_blend as named. Streaming uses live-holdout order. "
                "Attractor pull is not applied."
            ),
        },
        "live_sha256": live,
        "runs": runs,
    }
    path = LOG / ("probe_points.json" if not chosen else "probe_" + "_".join(sorted(chosen)) + ".json")
    dump_json(str(path), payload)
    assert_live_intact()
    print(f"REPORT {path}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
