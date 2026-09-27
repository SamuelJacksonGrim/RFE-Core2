"""Spectrum of a unit-normalized latent cloud.

Rows are L2-normalized, then centered. Eigenvalues are
eigvalsh((X.T @ X) / N), clipped at 0. N is the row count, not N-1.

participation_ratio = (sum lam)^2 / (sum(lam**2) + 1e-12). This is the
same value as tools.completion.geometry.population.

Positive eigenvalues are renormalized to p. spectral_entropy is
-sum(p ln p) in nats (zeros dropped; 0 log 0 = 0). effective_rank =
exp(spectral_entropy), Roy & Vetterli. It is not population's
eff_rank_512cap.

spectral_anisotropy = D * lam.max / sum(lam). Flat across the ambient
dimension is 1; rank-1 is D.

condition_number = lam.max / lam_floor, where lam_floor is the smallest
eigenvalue >= 1e-8 * lam.max. n_eigs_kept counts those eigenvalues.
"""

from __future__ import annotations

import numpy as np


def _numpy_cloud(z) -> np.ndarray:
    if isinstance(z, np.ndarray):
        return np.array(z, dtype=np.float64, copy=True)
    try:
        import torch
    except ImportError:
        torch = None
    if torch is not None and isinstance(z, torch.Tensor):
        with torch.no_grad():
            return z.detach().to(dtype=torch.float64).cpu().numpy()
    return np.array(z, dtype=np.float64, copy=True)


def _unit_center(raw: np.ndarray) -> np.ndarray:
    nrm = np.linalg.norm(raw, axis=1, keepdims=True)
    centered = raw / np.maximum(nrm, 1e-12)
    return centered - centered.mean(axis=0, keepdims=True)


class LatentManifoldTracker:
    def metrics(self, z) -> dict:
        raw = _numpy_cloud(z)
        if raw.ndim != 2:
            raise ValueError(f"expected z shape (N, D), got {raw.shape}")
        n, dim = int(raw.shape[0]), int(raw.shape[1])
        X = _unit_center(raw)
        lam = np.clip(np.linalg.eigvalsh((X.T @ X) / max(n, 1)), 0.0, None)
        pr = float((lam.sum() ** 2) / (np.sum(lam ** 2) + 1e-12))
        pos = lam[lam > 0.0]
        if pos.size == 0:
            entropy = 0.0
            effective = 0.0
        else:
            p = pos / pos.sum()
            entropy = float(-(p * np.log(p)).sum())
            effective = float(np.exp(entropy))
        lam_max = float(lam.max()) if lam.size else 0.0
        total = float(lam.sum())
        if total > 0.0:
            anisotropy = float(dim * lam_max / total)
        else:
            anisotropy = 0.0
        if lam_max > 0.0:
            kept = lam[lam >= 1e-8 * lam_max]
        else:
            kept = lam[:0]
        n_kept = int(kept.size)
        if n_kept == 0:
            lam_floor = 0.0
            condition = 1.0
        else:
            lam_floor = float(kept.min())
            condition = float(lam_max / lam_floor)
        return {
            "participation_ratio": pr,
            "effective_rank": effective,
            "spectral_entropy": entropy,
            "spectral_anisotropy": anisotropy,
            "condition_number": condition,
            "n": n,
            "dim": dim,
            "n_eigs_kept": n_kept,
            "lam_max": lam_max,
            "lam_floor": lam_floor,
        }


def _torch_covariance_pr(raw: np.ndarray) -> float:
    """Independent of numpy.linalg. Same cloud, torch.linalg.eigvalsh."""
    import torch

    with torch.no_grad():
        z = torch.as_tensor(raw, dtype=torch.float64)
        z = z / z.norm(dim=1, keepdim=True).clamp_min(1e-12)
        x = z - z.mean(dim=0, keepdim=True)
        n = max(int(z.shape[0]), 1)
        lam = torch.linalg.eigvalsh((x.T @ x) / n).clamp_min(0)
        return float((lam.sum() ** 2) / (lam.square().sum() + 1e-12))


def cross_check(z) -> dict:
    """Three participation ratios on one unit-normalized centered batch.

    (a) LatentManifoldTracker.metrics (numpy covariance eigenvalues)
    (b) torch.linalg.eigvalsh of the same covariance, a separate implementation
    (c) numpy SVD of the centered data matrix; PR from squared singular
        values. Scale-invariant, so sigma^2 and sigma^2/N agree.
    """
    pr_a = float(LatentManifoldTracker().metrics(z)["participation_ratio"])
    raw = _numpy_cloud(z)
    pr_b = _torch_covariance_pr(raw)

    nrm_c = np.linalg.norm(raw, axis=1, keepdims=True)
    Zc = raw / np.maximum(nrm_c, 1e-12)
    Xc = Zc - Zc.mean(axis=0, keepdims=True)
    sig2 = np.square(np.linalg.svd(Xc, compute_uv=False))
    pr_c = float((sig2.sum() ** 2) / (np.sum(sig2 ** 2) + 1e-12))

    return {
        "pr_tracker": pr_a,
        "pr_torch_eig": pr_b,
        "pr_numpy_svd": pr_c,
        "abs_delta_eig": abs(pr_a - pr_b),
        "abs_delta_svd": abs(pr_a - pr_c),
    }
