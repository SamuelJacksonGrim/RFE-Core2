"""
interference/phase_noise.py

Phase noise — oscillatory interference applied to latent vectors.

Unlike Gaussian noise (isotropic) or directional noise (perpendicular),
phase noise operates in the frequency domain: it perturbs the phase
angles of the vector's FFT spectrum while preserving amplitude structure.

This produces interference patterns that:
  - Shift the vector's internal oscillatory structure
  - Preserve the magnitude spectrum (energy distribution unchanged)
  - Create plausible variants that are spectrally related to the original
  - Simulate the effect of resonance interference on a field state

Modes
-----
  spectral    Phase perturbation in FFT domain (default)
  temporal    Sinusoidal modulation across vector components
  harmonic    Amplifies specific harmonic overtones
"""

from __future__ import annotations

import numpy as np


class PhaseNoise:
    """
    Phase-aware noise injection.

    Parameters
    ----------
    intensity : float
        Base noise intensity. Scales with mode.
    mode : str
        "spectral" | "temporal" | "harmonic"
    harmonic_order : int
        For "harmonic" mode: which overtone to amplify.
    """

    def __init__(
        self,
        intensity:      float = 0.05,
        mode:           str   = "spectral",
        harmonic_order: int   = 2,
    ):
        self.intensity      = intensity
        self.mode           = mode
        self.harmonic_order = harmonic_order

    def apply(
        self,
        vec: np.ndarray,
        rng: np.random.Generator = None,
    ) -> np.ndarray:
        """
        Apply phase noise to vec.

        Returns a unit-normalized vector with perturbed phase structure.
        """
        if rng is None:
            rng = np.random.default_rng()

        if self.mode == "spectral":
            return self._spectral(vec, rng)
        if self.mode == "temporal":
            return self._temporal(vec, rng)
        if self.mode == "harmonic":
            return self._harmonic(vec)

        raise ValueError(f"Unknown mode: '{self.mode}'")

    # ------------------------------------------------------------------
    # Modes
    # ------------------------------------------------------------------

    def _spectral(self, vec: np.ndarray, rng: np.random.Generator) -> np.ndarray:
        """
        Perturb FFT phase angles while preserving amplitude spectrum.
        The inverse FFT produces a vector with the same energy distribution
        but different internal oscillatory structure.
        """
        freqs     = np.fft.rfft(vec.astype(np.float64))
        amplitudes = np.abs(freqs)
        phases     = np.angle(freqs)

        # Add random phase perturbation
        phase_noise = rng.uniform(
            -self.intensity * np.pi,
             self.intensity * np.pi,
            size=phases.shape,
        )
        new_phases = phases + phase_noise

        # Reconstruct with original amplitudes, new phases
        new_freqs = amplitudes * np.exp(1j * new_phases)
        result    = np.fft.irfft(new_freqs, n=len(vec))

        norm = np.linalg.norm(result)
        return (result / (norm + 1e-8)).astype(np.float32)

    def _temporal(self, vec: np.ndarray, rng: np.random.Generator) -> np.ndarray:
        """
        Sinusoidal modulation across vector components.
        Phase offset is random; frequency is proportional to intensity.
        """
        dim    = len(vec)
        freq   = self.intensity * 10.0
        offset = rng.uniform(0, 2 * np.pi)
        t      = np.arange(dim, dtype=np.float64)
        wave   = np.sin(freq * t / dim + offset) * self.intensity
        result = vec.astype(np.float64) + wave
        norm   = np.linalg.norm(result)
        return (result / (norm + 1e-8)).astype(np.float32)

    def _harmonic(self, vec: np.ndarray) -> np.ndarray:
        """
        Amplify a specific harmonic overtone in the FFT spectrum.
        Creates constructive interference at the target frequency.
        """
        freqs = np.fft.rfft(vec.astype(np.float64))
        n     = len(freqs)

        # Find dominant frequency
        dominant = int(np.argmax(np.abs(freqs)))
        target   = dominant * self.harmonic_order

        if 0 < target < n:
            # Boost the harmonic bin
            freqs[target] *= (1.0 + self.intensity * 5.0)

        result = np.fft.irfft(freqs, n=len(vec))
        norm   = np.linalg.norm(result)
        return (result / (norm + 1e-8)).astype(np.float32)
