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
#
"""
interference/bifurcation.py

Bifurcation engine — controlled trajectory splitting at cognitive decision points.

Bifurcation generates multiple divergent variants of a vector,
each exploring a different region of the embedding space.
This is how the system generates genuine alternatives rather than
just noisy copies.

Applications
------------
  Chorus agent diversity:  seed each agent from a different bifurcation
  Dream synthesis:         bifurcate a memory before recombination
  Attractor exploration:   probe multiple basins from one seed
  Curiosity-driven search: generate hypotheses from a single observation

Modes
-----
  radial      Variants distributed radially around the seed
  axial       Variants along principal axes of the seed's subspace
  orthogonal  Each variant is maximally orthogonal to the others
  gradient    Variants following estimated gradient directions
"""

from __future__ import annotations

from typing import List

import numpy as np


class BifurcationEngine:
    """
    Controlled trajectory splitting.

    Parameters
    ----------
    n_branches : int
        Default number of branches to generate.
    divergence : float
        How far apart branches are pushed. Higher = more diverse.
    mode : str
        "radial" | "axial" | "orthogonal" | "gradient"
    normalize : bool
        If True, all branches are L2-normalized.
    """

    def __init__(
        self,
        n_branches: int   = 4,
        divergence: float = 0.2,
        mode:       str   = "radial",
        normalize:  bool  = True,
    ):
        self.n_branches = n_branches
        self.divergence = divergence
        self.mode       = mode
        self.normalize  = normalize

    def bifurcate(
        self,
        vec:        np.ndarray,
        n_branches: int = None,
        rng:        np.random.Generator = None,
    ) -> List[np.ndarray]:
        """
        Generate n_branches divergent variants of vec.

        Parameters
        ----------
        vec : np.ndarray, shape (dim,)
        n_branches : int or None
            Override instance default.
        rng : np.random.Generator or None

        Returns
        -------
        List of np.ndarray, each shape (dim,), normalized
        """
        if rng is None:
            rng = np.random.default_rng()

        n = n_branches or self.n_branches

        if self.mode == "radial":
            return self._radial(vec, n, rng)
        if self.mode == "axial":
            return self._axial(vec, n, rng)
        if self.mode == "orthogonal":
            return self._orthogonal(vec, n, rng)
        if self.mode == "gradient":
            return self._gradient(vec, n, rng)

        raise ValueError(f"Unknown bifurcation mode: '{self.mode}'")

    # ------------------------------------------------------------------
    # Modes
    # ------------------------------------------------------------------

    def _radial(
        self,
        vec: np.ndarray,
        n:   int,
        rng: np.random.Generator,
    ) -> List[np.ndarray]:
        """
        Radially distributed branches around the seed vector.
        Each branch = seed + divergence * random unit perturbation.
        Angles between branches are approximately equal.
        """
        dim     = vec.shape[0]
        results = []

        for i in range(n):
            # Evenly spaced angles in a random subspace
            noise  = rng.normal(0, 1, size=dim)
            noise -= noise.dot(vec) * vec / (np.dot(vec, vec) + 1e-8)  # orthogonalize
            noise /= np.linalg.norm(noise) + 1e-8

            angle  = (2 * np.pi * i / n)
            branch = vec + self.divergence * (np.cos(angle) * noise)
            results.append(self._norm(branch))

        return results

    def _axial(
        self,
        vec: np.ndarray,
        n:   int,
        rng: np.random.Generator,
    ) -> List[np.ndarray]:
        """
        Variants along the principal axes derived from the seed.
        Uses a random orthonormal basis in the seed's null space.
        """
        dim  = vec.shape[0]
        unit = vec / (np.linalg.norm(vec) + 1e-8)

        # Build a random orthonormal basis orthogonal to unit
        basis = []
        for _ in range(n):
            v = rng.normal(0, 1, size=dim)
            v -= v.dot(unit) * unit
            for b in basis:
                v -= v.dot(b) * b
            norm = np.linalg.norm(v)
            if norm > 1e-8:
                basis.append(v / norm)

        results = []
        for ax in basis:
            branch = vec + self.divergence * ax
            results.append(self._norm(branch))

        # Pad with radial if not enough basis vectors
        while len(results) < n:
            results.append(self._norm(vec + rng.normal(0, self.divergence * 0.5, size=dim)))

        return results[:n]

    def _orthogonal(
        self,
        vec: np.ndarray,
        n:   int,
        rng: np.random.Generator,
    ) -> List[np.ndarray]:
        """
        Each branch is maximally orthogonal to all others (Gram-Schmidt).
        Produces the most diverse possible set of directions.
        """
        dim     = vec.shape[0]
        vectors = [vec.copy()]

        for _ in range(n - 1):
            candidate = rng.normal(0, 1, size=dim)
            for v in vectors:
                candidate -= candidate.dot(v) * v / (np.dot(v, v) + 1e-8)
            norm = np.linalg.norm(candidate)
            if norm > 1e-8:
                vectors.append(candidate / norm)
            else:
                vectors.append(rng.normal(0, 1, size=dim))

        # Blend each orthogonal direction with the seed at divergence rate
        results = []
        for v in vectors:
            branch = (1.0 - self.divergence) * vec + self.divergence * v
            results.append(self._norm(branch))

        return results[:n]

    def _gradient(
        self,
        vec: np.ndarray,
        n:   int,
        rng: np.random.Generator,
    ) -> List[np.ndarray]:
        """
        Variants following approximate gradient directions in FFT space.
        Explores spectrally distinct regions of the embedding.
        """
        freqs = np.fft.rfft(vec.astype(np.float64))
        n_bins = len(freqs)
        results = []

        bin_indices = rng.choice(n_bins, size=n, replace=(n > n_bins))

        for bin_idx in bin_indices:
            perturbed = freqs.copy()
            perturbed[bin_idx] *= (1.0 + self.divergence * rng.uniform(0.5, 2.0))
            branch = np.fft.irfft(perturbed, n=len(vec))
            results.append(self._norm(branch.astype(np.float32)))

        return results

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _norm(self, vec: np.ndarray) -> np.ndarray:
        if not self.normalize:
            return vec.astype(np.float32)
        norm = np.linalg.norm(vec)
        return (vec / (norm + 1e-8)).astype(np.float32)
