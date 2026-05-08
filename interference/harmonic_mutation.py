"""
interference/harmonic_mutation.py

Harmonic mutation — evolution of vectors through spectral recombination.

Harmonic mutation operates in the frequency domain. Rather than adding
noise to a vector directly, it modifies the harmonic structure of the
vector's FFT spectrum — amplifying, suppressing, or recombining overtones.

This produces mutations that:
  - Preserve the vector's fundamental character (dominant frequency)
  - Evolve its higher-order structure (harmonics, overtones)
  - Generate spectrally plausible variants (not random noise)
  - Enable cross-vector harmonic recombination (hybrid synthesis)

Used by
-------
  Dreamer:  mutate dream hybrids through harmonic evolution
  Chorus:   differentiate agent outputs through spectral mutation
  Training: augment training examples with harmonically plausible variants
"""

from __future__ import annotations

from typing import List, Optional

import numpy as np


class HarmonicMutator:
    """
    Spectral harmonic mutation engine.

    Parameters
    ----------
    mutation_rate : float
        Fraction of harmonic bins modified per mutation. ∈ [0, 1]
    amplitude_scale : float
        Scale of amplitude perturbation per bin.
    preserve_fundamental : bool
        If True, the dominant frequency bin is never modified.
    cross_fade : float
        For recombination: blend weight between parent spectra. ∈ [0, 1]
    """

    def __init__(
        self,
        mutation_rate:         float = 0.15,
        amplitude_scale:       float = 0.3,
        preserve_fundamental:  bool  = True,
        cross_fade:            float = 0.5,
    ):
        self.mutation_rate        = mutation_rate
        self.amplitude_scale      = amplitude_scale
        self.preserve_fundamental = preserve_fundamental
        self.cross_fade           = cross_fade

    # ------------------------------------------------------------------
    # Single-vector mutation
    # ------------------------------------------------------------------

    def mutate(
        self,
        vec: np.ndarray,
        rng: np.random.Generator = None,
    ) -> np.ndarray:
        """
        Harmonically mutate a single vector.

        Randomly selects a fraction of harmonic bins and perturbs their
        amplitudes while preserving phase relationships.

        Returns L2-normalized mutated vector.
        """
        if rng is None:
            rng = np.random.default_rng()

        freqs      = np.fft.rfft(vec.astype(np.float64))
        n_bins     = len(freqs)
        amplitudes = np.abs(freqs)
        phases     = np.angle(freqs)

        dominant = int(np.argmax(amplitudes))

        # Select bins to mutate
        n_mutate = max(1, int(n_bins * self.mutation_rate))
        candidates = [i for i in range(n_bins) if not (self.preserve_fundamental and i == dominant)]
        if not candidates:
            candidates = list(range(n_bins))

        mutate_idx = rng.choice(candidates, size=min(n_mutate, len(candidates)), replace=False)

        new_amplitudes = amplitudes.copy()
        for idx in mutate_idx:
            scale = rng.uniform(
                1.0 - self.amplitude_scale,
                1.0 + self.amplitude_scale,
            )
            new_amplitudes[idx] = max(0.0, new_amplitudes[idx] * scale)

        # Reconstruct
        new_freqs = new_amplitudes * np.exp(1j * phases)
        result    = np.fft.irfft(new_freqs, n=len(vec))
        norm      = np.linalg.norm(result)
        return (result / (norm + 1e-8)).astype(np.float32)

    # ------------------------------------------------------------------
    # Harmonic recombination (two-parent)
    # ------------------------------------------------------------------

    def recombine(
        self,
        vec_a:     np.ndarray,
        vec_b:     np.ndarray,
        rng:       np.random.Generator = None,
        blend:     Optional[float] = None,
    ) -> np.ndarray:
        """
        Harmonically recombine two vectors.

        Each frequency bin independently draws from parent A or parent B
        based on the cross_fade probability. Phase is inherited from the
        dominant parent at each bin.

        Parameters
        ----------
        vec_a, vec_b : np.ndarray
            Parent vectors.
        blend : float or None
            Override instance cross_fade for this call.

        Returns L2-normalized hybrid vector.
        """
        if rng is None:
            rng = np.random.default_rng()

        fade = blend if blend is not None else self.cross_fade

        freqs_a = np.fft.rfft(vec_a.astype(np.float64))
        freqs_b = np.fft.rfft(vec_b.astype(np.float64))

        n_bins    = min(len(freqs_a), len(freqs_b))
        freqs_a   = freqs_a[:n_bins]
        freqs_b   = freqs_b[:n_bins]

        amp_a, phase_a = np.abs(freqs_a), np.angle(freqs_a)
        amp_b, phase_b = np.abs(freqs_b), np.angle(freqs_b)

        # Per-bin crossover mask
        mask = rng.random(n_bins) < fade

        new_amp   = np.where(mask, amp_b,   amp_a)
        new_phase = np.where(mask, phase_b, phase_a)

        new_freqs = new_amp * np.exp(1j * new_phase)
        dim       = max(len(vec_a), len(vec_b))
        result    = np.fft.irfft(new_freqs, n=dim)[:len(vec_a)]
        norm      = np.linalg.norm(result)
        return (result / (norm + 1e-8)).astype(np.float32)

    # ------------------------------------------------------------------
    # Batch mutation
    # ------------------------------------------------------------------

    def mutate_batch(
        self,
        vectors: List[np.ndarray],
        rng:     np.random.Generator = None,
    ) -> List[np.ndarray]:
        """Apply mutation to each vector in a list."""
        if rng is None:
            rng = np.random.default_rng()
        return [self.mutate(v, rng) for v in vectors]

    def harmonic_series(
        self,
        vec:    np.ndarray,
        n:      int = 4,
        rng:    np.random.Generator = None,
    ) -> List[np.ndarray]:
        """
        Generate a harmonic series: n progressively mutated variants,
        each derived from the previous. Forms an evolutionary trajectory.
        """
        if rng is None:
            rng = np.random.default_rng()
        series  = [vec.copy()]
        current = vec
        for _ in range(n - 1):
            current = self.mutate(current, rng)
            series.append(current)
        return series
