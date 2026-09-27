"""Population and separability, the same instrument as the dim-256 readout.

participation_ratio and eff_rank_512cap match tools/dim256/geometry.py so a
number in this experiment is comparable to the contrastive finding.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from agents.generator import Generator
from tools.completion.live_guard import refuse_protected
from training.corpus import RHYTHMS


def load_generator(dim: int, weights: str, ecology: str, seed: int = 0) -> Generator:
    import torch

    torch.manual_seed(seed)
    gen = Generator(
        vocab_size=8192, dim=dim, depth=4, heads=4, ff_mult=4, dropout=0.1,
        auto_decay_interval=None,
    )
    gen.load_checkpoint(weights, ecology)
    gen.eval()
    return gen


def encode_texts(gen: Generator, token_lists, batch: int = 256) -> np.ndarray:
    gen.eval()
    out = []
    for i in range(0, len(token_lists), batch):
        out.append(gen.encode_batch(token_lists[i:i + batch]))
    return np.concatenate(out, axis=0).astype(np.float64)


def embedding_means(gen: Generator, token_lists, batch: int = 256) -> np.ndarray:
    """Unit-norm masked means of token embeddings, before position and the stack.

    Same reduction as Generator.token_embedding_mean. This is the point upstream
    of the transformer, which encode_texts (the field vector) is not.
    """
    import torch
    import torch.nn.functional as F

    gen.eval()
    out = []
    with torch.no_grad():
        for i in range(0, len(token_lists), batch):
            chunk = token_lists[i:i + batch]
            encoded = [gen._tokens_to_ids(tl or ["<BOS>"], None) for tl in chunk]
            gen._ensure_embedding_capacity()
            max_len = max(len(s) for s in encoded)
            pad_id = gen.address_space.pad_id
            padded = [s + [pad_id] * (max_len - len(s)) for s in encoded]
            ids = torch.tensor(padded, dtype=torch.long, device=gen.device)
            mean = F.normalize(gen.token_embedding_mean(ids), dim=-1)
            out.append(mean.detach().cpu().numpy())
    return np.concatenate(out, axis=0).astype(np.float64)


def mean_cosine(a: np.ndarray, b: np.ndarray) -> float:
    """Mean row-wise cosine. Both clouds are re-normalized."""
    a = _unit_rows(np.asarray(a, dtype=np.float64))
    b = _unit_rows(np.asarray(b, dtype=np.float64))
    return float((a * b).sum(axis=1).mean())


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
    cov = (X.T @ X) / max(len(Z), 1)
    lam = np.clip(np.linalg.eigvalsh(cov), 0.0, None)
    pr = float((lam.sum() ** 2) / (np.sum(lam ** 2) + 1e-12))
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
    """Centroid cosine matrix. Worst pair = highest off-diagonal."""
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
    off = [p["centroid_cos"] for p in pairs]
    return {
        "within_centroid_cos": within,
        "worst_pair": pairs[0] if pairs else None,
        "best_separated_pair": pairs[-1] if pairs else None,
        "offdiag_mean": round(float(np.mean(off)), 4) if off else None,
        "offdiag_max": round(float(np.max(off)), 4) if off else None,
        "offdiag_min": round(float(np.min(off)), 4) if off else None,
    }


def nearest_centroid_accuracy(Z: np.ndarray, labels, rhythms=RHYTHMS) -> float:
    Z = _unit_rows(np.asarray(Z, dtype=np.float64))
    labels = np.asarray(labels)
    centroids = []
    names = []
    for r in rhythms:
        block = Z[labels == r]
        if len(block) == 0:
            continue
        c = block.mean(axis=0)
        centroids.append(c / (np.linalg.norm(c) + 1e-12))
        names.append(r)
    C = np.stack(centroids, axis=0)
    pred = np.array(names)[(Z @ C.T).argmax(axis=1)]
    return float((pred == labels).mean())


def dump_json(path: str, obj) -> None:
    refuse_protected(path)
    dest = Path(path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(obj, indent=2), encoding="utf-8")
