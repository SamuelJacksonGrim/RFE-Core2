"""Shared readouts for the dim-256 experiment.

Separability, dead-dimension population, and checkpoint loading. Nothing here
writes a checkpoint or steps the field.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from agents.generator import Generator
from training.corpus import RHYTHMS, load_corpus

# Live 128D artifacts. Never write these.
PROTECTED = {
    "generator_weights_5rhythm.pt",
    "generator_ecology_5rhythm.json",
    "generator_weights_5rhythm_kimi.pt",
    "generator_ecology_5rhythm_kimi.json",
    "generator_weights_5rhythm_legible.pt",
    "generator_ecology_5rhythm_legible.json",
    "decoder_5rhythm.pt",
    "decoder_5rhythm_ecology.pt",
}


def refuse_protected(path: str) -> None:
    name = Path(path).name
    if name in PROTECTED:
        raise SystemExit(f"refusing to write protected 128D artifact: {path}")


def load_generator(dim: int, weights: str, ecology: str, seed: int = 0) -> Generator:
    import torch

    torch.manual_seed(seed)
    gen = Generator(vocab_size=8192, dim=dim, depth=4, heads=4, ff_mult=4, dropout=0.1)
    gen.load_checkpoint(weights, ecology)
    gen.eval()
    return gen


def encode_records(gen: Generator, records, batch: int = 256) -> np.ndarray:
    out = []
    for i in range(0, len(records), batch):
        chunk = [r["tokens"] for r in records[i:i + batch]]
        out.append(gen.encode_batch(chunk))
    return np.concatenate(out, axis=0).astype(np.float64)


def _unit_rows(Z: np.ndarray) -> np.ndarray:
    n = np.linalg.norm(Z, axis=1, keepdims=True)
    return Z / np.maximum(n, 1e-12)


def population(Z: np.ndarray) -> dict:
    """How the encoded cloud fills the ambient dimension."""
    Z = _unit_rows(np.asarray(Z, dtype=np.float64))
    std = Z.std(axis=0)
    med = float(np.median(std))
    quiet_cut = max(med * 0.01, 1e-4)
    X = Z - Z.mean(axis=0, keepdims=True)
    # Covariance is (dim, dim). Holdout n >> dim for both 128 and 256.
    cov = (X.T @ X) / max(len(Z), 1)
    lam = np.clip(np.linalg.eigvalsh(cov), 0.0, None)
    pr = float((lam.sum() ** 2) / (np.sum(lam ** 2) + 1e-12))
    # SVD effective rank on a cap so the number is comparable across dims.
    cap = min(len(Z), 512)
    lam_s = np.linalg.svd(Z[:cap], compute_uv=False) ** 2
    eff = float((lam_s.sum() ** 2) / (np.sum(lam_s ** 2) + 1e-12))
    return {
        "n": int(len(Z)),
        "dim": int(Z.shape[1]),
        "row_norm_mean": float(np.linalg.norm(Z, axis=1).mean()),
        "per_dim_std_min": float(std.min()),
        "per_dim_std_p05": float(np.quantile(std, 0.05)),
        "per_dim_std_median": med,
        "quiet_dims_lt_1pct_median": int((std < quiet_cut).sum()),
        "dead_dims_std_lt_1e-3": int((std < 1e-3).sum()),
        "participation_ratio": round(pr, 3),
        "eff_rank_512cap": round(eff, 3),
    }


def separability(Z: np.ndarray, labels, rhythms=RHYTHMS) -> dict:
    """Centroid cosine matrix. Worst pair = highest off-diagonal (most tangled)."""
    Z = _unit_rows(np.asarray(Z, dtype=np.float64))
    labels = np.asarray(labels)
    centroids = []
    within = {}
    for r in rhythms:
        block = Z[labels == r]
        if len(block) == 0:
            centroids.append(np.zeros(Z.shape[1]))
            within[r] = None
            continue
        c = block.mean(axis=0)
        c = c / (np.linalg.norm(c) + 1e-12)
        centroids.append(c)
        within[r] = round(float((block @ c).mean()), 4)
    C = np.stack(centroids, axis=0)
    S = C @ C.T
    pairs = []
    for i in range(len(rhythms)):
        for j in range(i + 1, len(rhythms)):
            pairs.append({
                "a": rhythms[i],
                "b": rhythms[j],
                "centroid_cos": round(float(S[i, j]), 4),
            })
    pairs.sort(key=lambda p: p["centroid_cos"], reverse=True)
    worst = pairs[0] if pairs else None
    best = pairs[-1] if pairs else None
    off = [p["centroid_cos"] for p in pairs]
    return {
        "rhythms": list(rhythms),
        "n": int(len(Z)),
        "within_centroid_cos": within,
        "pairs_tangled_first": pairs,
        "worst_pair": worst,
        "best_separated_pair": best,
        "offdiag_mean": round(float(np.mean(off)), 4) if off else None,
        "offdiag_max": round(float(np.max(off)), 4) if off else None,
        "offdiag_min": round(float(np.min(off)), 4) if off else None,
        "matrix": [[round(float(x), 4) for x in row] for row in S],
    }


def report_checkpoint(dim: int, weights: str, ecology: str, split_path, seed: int = 0) -> dict:
    records = load_corpus(split_path)
    gen = load_generator(dim, weights, ecology, seed=seed)
    Z = encode_records(gen, records)
    labels = [r["rhythm"] for r in records]
    # Spot-check: encode_batch matches generate on one sequence.
    one = records[0]["tokens"]
    a = gen.encode_batch([one])[0]
    b = gen.generate(one)
    agree = float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-12))
    return {
        "dim": dim,
        "weights": weights,
        "ecology": ecology,
        "split": str(split_path),
        "n": len(records),
        "encode_matches_generate_cos": round(agree, 6),
        "population": population(Z),
        "separability": separability(Z, labels),
    }


def dump_json(path: str, obj) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(obj, indent=2), encoding="utf-8")
