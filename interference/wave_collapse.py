# Copyright 2026 Samuel Jackson Grim
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
interference/wave_collapse.py

Wave collapse — superposition resolution for multi-vector ensembles.

Three collapse modes
--------------------
  mean      Simple weighted mean, L2-normalized. Default.
  resonant  Weights vectors by their own L2 norm (louder signals pull harder).
  entropic  Weights inversely by entropy — low-entropy (focused) vectors
            contribute more than high-entropy (diffuse) ones.

All modes return a unit-normalized vector.
"""

from typing import List, Optional
import numpy as np


def collapse_wave(
    vectors: List[np.ndarray],
    weights: Optional[List[float]] = None,
    mode: str = "mean",
) -> np.ndarray:
    """
    Collapse a list of vectors into a single normalized resultant.

    Parameters
    ----------
    vectors : list of np.ndarray, each shape (dim,)
    weights : list of float or None
        Manual weights. If None, weights are derived from `mode`.
        When provided, `mode` is ignored and simple weighted mean is used.
    mode : str
        "mean"     — uniform weights (or use provided weights)
        "resonant" — weight by vector magnitude
        "entropic" — weight by inverse entropy (focused > diffuse)

    Returns
    -------
    np.ndarray, shape (dim,), L2-normalized

    Raises
    ------
    ValueError  if vectors is empty or contains shape mismatches
    """
    if not vectors:
        raise ValueError("collapse_wave received an empty vector list")

    shapes = {v.shape for v in vectors}
    if len(shapes) > 1:
        raise ValueError(f"collapse_wave received vectors with mixed shapes: {shapes}")

    if weights is not None:
        if len(weights) != len(vectors):
            raise ValueError(
                f"weights length ({len(weights)}) != vectors length ({len(vectors)})"
            )
        w = np.array(weights, dtype=np.float64)
    else:
        w = _derive_weights(vectors, mode)

    # Normalize weights to sum to 1
    w_sum = w.sum()
    if w_sum < 1e-8:
        w = np.ones(len(vectors)) / len(vectors)
    else:
        w = w / w_sum

    merged = np.zeros_like(vectors[0], dtype=np.float64)
    for vec, wi in zip(vectors, w):
        merged += vec.astype(np.float64) * wi

    norm = np.linalg.norm(merged)
    if norm < 1e-8:
        # Degenerate collapse — vectors cancelled; return first vector
        return vectors[0] / (np.linalg.norm(vectors[0]) + 1e-8)

    return (merged / norm).astype(np.float32)


def _derive_weights(vectors: List[np.ndarray], mode: str) -> np.ndarray:
    """Compute per-vector weights for the given collapse mode."""
    n = len(vectors)

    if mode == "mean":
        return np.ones(n)

    if mode == "resonant":
        # Louder (higher-norm) vectors pull the collapse harder
        norms = np.array([np.linalg.norm(v) for v in vectors])
        return np.clip(norms, 1e-8, None)

    if mode == "entropic":
        # Low-entropy (focused) vectors contribute more
        entropies = np.array([_vector_entropy(v) for v in vectors])
        max_H = np.log(vectors[0].shape[0])
        # Invert and normalize: low entropy → high weight
        inv = max_H - entropies
        return np.clip(inv, 1e-8, None)

    raise ValueError(f"Unknown collapse mode: '{mode}'. Use 'mean', 'resonant', or 'entropic'.")


def _vector_entropy(vec: np.ndarray) -> float:
    """Distributional entropy of |vec| interpreted as a probability mass."""
    p = np.abs(vec)
    total = p.sum()
    if total < 1e-8:
        return 0.0
    p = np.clip(p / total, 1e-10, 1.0)
    return float(-np.sum(p * np.log(p)))
