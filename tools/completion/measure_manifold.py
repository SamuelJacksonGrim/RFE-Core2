"""Live-holdout manifold at the frozen and completion checkpoints.

participation_ratio matches geometry.population: unit rows, center,
eigvalsh((X.T @ X) / N). effective_rank is exp(spectral entropy),
Roy & Vetterli, not eff_rank_512cap.

    python -m tools.completion.measure_manifold
"""

from __future__ import annotations

import sys

import numpy as np

from tools.completion.geometry import dump_json, encode_texts, load_generator, population
from tools.completion.live_guard import REPO, assert_live_intact
from tools.completion.manifold import LatentManifoldTracker, cross_check
from training.corpus import HOLDOUT_PATH, corpus_version, load_corpus

LOG = REPO / "docs" / "findings" / "logs" / "2026-09-23-phase-b" / "s1_manifold.json"

CROSS_CHECK_METHOD = (
    "Participation ratio on one unit-normalized centered batch, three "
    "implementations: numpy covariance eigvalsh (the tracker), torch.linalg "
    "eigvalsh of that same covariance, and numpy SVD of the centered data "
    "matrix via squared singular values (scale-invariant, so sigma^2 and "
    "sigma^2/N agree). geometry.population is a fourth read of the numpy formula."
)

PUBLISHED = {
    "PR_frozen": 3.4,
    "PR_c128": 47.8,
    "PR_c256": 81.9,
}

CHECKPOINTS = (
    {
        "key": "PR_frozen",
        "weights": "data/checkpoints/generator_weights_5rhythm.pt",
        "ecology": "data/checkpoints/generator_ecology_5rhythm.json",
        "dim": 128,
        "embedding_residual": False,
    },
    {
        "key": "PR_c128",
        "weights": "data/checkpoints/generator_weights_completion_128_emb.pt",
        "ecology": "data/checkpoints/generator_ecology_completion_128_emb.json",
        "dim": 128,
        "embedding_residual": True,
    },
    {
        "key": "PR_c256",
        "weights": "data/checkpoints/generator_weights_completion_256_emb.pt",
        "ecology": "data/checkpoints/generator_ecology_completion_256_emb.json",
        "dim": 256,
        "embedding_residual": True,
    },
)


def _finite(metrics: dict) -> None:
    for key, value in metrics.items():
        if isinstance(value, float) and not np.isfinite(value):
            raise SystemExit(f"non-finite metric {key}={value}")


def _self_check() -> dict:
    rng = np.random.default_rng(0)
    dim = 32
    isotropic = rng.normal(size=(64, dim))
    direction = rng.normal(size=(dim,))
    sign = np.ones((64, 1))
    sign[32:] = -1.0
    rank1 = sign * direction

    tracker = LatentManifoldTracker()
    out = {}
    for name, cloud, kind in (
        ("isotropic", isotropic, "iso"),
        ("rank1", rank1, "rank1"),
    ):
        metrics = tracker.metrics(cloud)
        _finite(metrics)
        checked = cross_check(cloud)
        if checked["abs_delta_eig"] > 1e-6 or checked["abs_delta_svd"] > 1e-6:
            raise SystemExit(
                f"self-check cross-check failed on {name}: "
                f"delta_eig {checked['abs_delta_eig']}  "
                f"delta_svd {checked['abs_delta_svd']}"
            )
        pop = population(cloud)
        delta_pop = abs(metrics["participation_ratio"] - pop["participation_ratio"])
        if delta_pop > 1e-3:
            raise SystemExit(
                f"self-check population disagree on {name}: "
                f"tracker {metrics['participation_ratio']}  "
                f"population {pop['participation_ratio']}"
            )
        pr = metrics["participation_ratio"]
        if kind == "rank1" and not (0.99 <= pr <= 1.01):
            raise SystemExit(f"rank-1 participation ratio {pr} is not ~1")
        if kind == "iso" and pr < dim * 0.25:
            raise SystemExit(
                f"isotropic participation ratio {pr} is not on the order of dim {dim}"
            )
        out[name] = {
            "participation_ratio": pr,
            "effective_rank": metrics["effective_rank"],
            "abs_delta_eig": checked["abs_delta_eig"],
            "abs_delta_svd": checked["abs_delta_svd"],
            "abs_delta_population": delta_pop,
            "population_participation_ratio": pop["participation_ratio"],
        }
        print(
            f"self-check {name}  PR {pr:.6f}  "
            f"eff {metrics['effective_rank']:.6f}  "
            f"delta_eig {checked['abs_delta_eig']:.3e}  "
            f"delta_svd {checked['abs_delta_svd']:.3e}",
            flush=True,
        )
    return out


def _json_block(metrics: dict, checked: dict, pop: dict, spec: dict) -> dict:
    pr = metrics["participation_ratio"]
    published = PUBLISHED[spec["key"]]
    return {
        "weights": spec["weights"],
        "ecology": spec["ecology"],
        "dim": spec["dim"],
        "embedding_residual": spec["embedding_residual"],
        "n": metrics["n"],
        "dim_metric": metrics["dim"],
        "participation_ratio": round(pr, 3),
        "participation_ratio_unrounded": pr,
        "pr_torch_eig": checked["pr_torch_eig"],
        "pr_numpy_svd": checked["pr_numpy_svd"],
        "pr_population": pop["participation_ratio"],
        "population_eff_rank_512cap": pop["eff_rank_512cap"],
        "abs_delta_tracker_eig": checked["abs_delta_eig"],
        "abs_delta_tracker_svd": checked["abs_delta_svd"],
        "abs_delta_tracker_population": abs(pr - pop["participation_ratio"]),
        "effective_rank": metrics["effective_rank"],
        "spectral_entropy": metrics["spectral_entropy"],
        "spectral_anisotropy": metrics["spectral_anisotropy"],
        "condition_number": metrics["condition_number"],
        "n_eigs_kept": metrics["n_eigs_kept"],
        "lam_max": metrics["lam_max"],
        "lam_floor": metrics["lam_floor"],
        "published_prior": published,
        "abs_delta_published": abs(pr - published),
        "cross_check_passed": True,
        "population_agreed": True,
    }


def _finding(blocks: dict) -> str | None:
    off = []
    for key, prior in PUBLISHED.items():
        got = blocks[key]["participation_ratio_unrounded"]
        pop = blocks[key]["pr_population"]
        if abs(got - prior) > 0.05:
            off.append(f"{key} tracker {got:.6f} (population {pop}, published {prior})")
    if not off:
        return None
    return (
        "The tracker matches geometry.population and both numpy routes, so the "
        "covariance definition is the one that is right: unit-norm rows, center, "
        "eigvalsh((X.T @ X) / N), participation (sum lam)^2 / (sum(lam**2) + 1e-12). "
        "The published figures are a prior measurement, not this cloud, and the "
        "cloud was not re-sliced or re-encoded to chase them. "
        + "Disagreements: "
        + "; ".join(off)
        + "."
    )


def main() -> int:
    live = assert_live_intact()
    self_check = _self_check()
    print("self-check passed", flush=True)

    hold = load_corpus(HOLDOUT_PATH)
    texts = [r["tokens"] for r in hold]
    if len(texts) != 1505:
        raise SystemExit(f"expected 1505 holdout lines, got {len(texts)}")

    tracker = LatentManifoldTracker()
    blocks = {}
    for spec in CHECKPOINTS:
        weights = REPO / spec["weights"]
        ecology = REPO / spec["ecology"]
        if not weights.is_file() or not ecology.is_file():
            raise SystemExit(f"missing checkpoint: {spec['weights']}")
        gen = load_generator(spec["dim"], str(weights), str(ecology))
        gen.embedding_residual = bool(spec["embedding_residual"])
        gen.eval()
        print(
            f"encode {spec['key']}  dim {spec['dim']}  "
            f"residual {bool(spec['embedding_residual'])}  device {gen.device}",
            flush=True,
        )
        cloud = encode_texts(gen, texts)
        if cloud.shape != (1505, spec["dim"]):
            raise SystemExit(f"{spec['key']} cloud shape {cloud.shape}")
        metrics = tracker.metrics(cloud)
        _finite(metrics)
        checked = cross_check(cloud)
        pop = population(cloud)
        delta_eig = checked["abs_delta_eig"]
        delta_svd = checked["abs_delta_svd"]
        delta_pop = abs(metrics["participation_ratio"] - pop["participation_ratio"])
        if delta_eig > 1e-4 or delta_svd > 1e-4:
            raise SystemExit(
                f"cross-check failed {spec['key']}: "
                f"tracker {checked['pr_tracker']}  "
                f"eig {checked['pr_torch_eig']}  svd {checked['pr_numpy_svd']}  "
                f"delta_eig {delta_eig}  delta_svd {delta_svd}"
            )
        if delta_pop > 1e-3:
            raise SystemExit(
                f"population disagree {spec['key']}: "
                f"tracker {metrics['participation_ratio']}  "
                f"population {pop['participation_ratio']}"
            )
        block = _json_block(metrics, checked, pop, spec)
        blocks[spec["key"]] = block
        print(
            f"{spec['key']}  tracker {metrics['participation_ratio']:.6f}  "
            f"torch_eig {checked['pr_torch_eig']:.6f}  "
            f"numpy_svd {checked['pr_numpy_svd']:.6f}  "
            f"population {pop['participation_ratio']}  "
            f"delta_eig {delta_eig:.3e}  delta_svd {delta_svd:.3e}  "
            f"delta_pop {delta_pop:.3e}  "
            f"eff {metrics['effective_rank']:.6f}  "
            f"H {metrics['spectral_entropy']:.6f}  "
            f"aniso {metrics['spectral_anisotropy']:.6f}  "
            f"cond {metrics['condition_number']:.6f}  "
            f"kept {metrics['n_eigs_kept']}",
            flush=True,
        )
        del gen, cloud

    finding = _finding(blocks)
    payload = {
        "cross_check_method": CROSS_CHECK_METHOD,
        "corpus_version": corpus_version(),
        "n_holdout": 1505,
        "self_check": self_check,
        "checkpoints": blocks,
        "finding": finding,
        "live_sha256": live,
    }
    dump_json(str(LOG), payload)
    assert_live_intact()
    print(f"cross-check passed  REPORT {LOG}", flush=True)
    if finding:
        print(f"finding: {finding}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
