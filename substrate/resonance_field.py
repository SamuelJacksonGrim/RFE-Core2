"""
substrate/resonance_field.py

Resonance field — the system's continuous dynamic substrate.

The field is not a flat memory store. It is a living superposition of
all injected vectors, subject to:
  - Nonlinear saturation (tanh)
  - Exponential decay
  - FFT spectral decomposition and harmonic analysis
  - Phase synchrony tracking
  - Rhythm-state detection across four modes

Rhythm states
-------------
  stabilize  field energy very low  — consolidation, crystallization
  dream      field energy low       — free association, latent recombination
  reflect    field energy medium    — deliberate recursion
  explore    field energy high      — mutation, novelty seeking

Spectral features
-----------------
  dominant_frequency  — index of the FFT bin with highest power
  spectral_entropy    — distributional entropy across frequency bins
  harmonic_ratio      — power in harmonic bins relative to total power
  phase_coherence     — mean pairwise phase alignment across recent history

These feed into Watcher's field resonance layer and will eventually
support full harmonic matching and phase synchrony gating.
"""

import collections
from dataclasses import dataclass
from typing import List, Optional

import numpy as np


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class SpectralSnapshot:
    """FFT-derived field characteristics at a single point in time."""
    dominant_frequency: int    # FFT bin index with highest power
    spectral_entropy:   float  # entropy across frequency power distribution
    harmonic_ratio:     float  # fraction of power in harmonic bins
    phase_coherence:    float  # mean pairwise phase alignment ∈ [0, 1]
    energy:             float  # L2 norm of the field at snapshot time


@dataclass
class FieldState:
    """
    Complete observable state of the field at a single step.
    Returned by observe() for use by loop, watcher, and visualization.
    """
    raw:              np.ndarray   # field vector before tanh
    resonated:        np.ndarray   # tanh(field)
    energy:           float        # L2 norm of raw field
    rhythm:           str          # stabilize | dream | reflect | explore
    spectral:         SpectralSnapshot
    internal_coherence: float      # mean cosine of field vs history mean ∈ [0,1]
    step:             int


# ---------------------------------------------------------------------------
# ResonanceField
# ---------------------------------------------------------------------------

class ResonanceField:
    """
    Continuous dynamic field substrate.

    Parameters
    ----------
    dim : int
        Field dimensionality (must match Generator output dim).
    decay : float
        Per-step exponential decay applied to the field.
    history_len : int
        Maximum number of injected vectors retained in history.
        Bounded to prevent unbounded memory growth.
    rhythm_thresholds : dict or None
        Energy thresholds for the four rhythm states.
        Defaults: stabilize < 0.5, dream < 2.0, reflect < 5.0, explore ≥ 5.0
    harmonic_bins : int
        Number of harmonic overtone bins to check in FFT analysis.
    phase_history_len : int
        Window size for phase coherence computation.
    """

    # Default rhythm energy thresholds
    DEFAULT_THRESHOLDS = {
        "stabilize": 0.5,
        "dream":     2.0,
        "reflect":   5.0,
        # explore = everything above reflect
    }

    def __init__(
        self,
        dim: int = 128,
        decay: float = 0.995,
        history_len: int = 256,
        rhythm_thresholds: Optional[dict] = None,
        harmonic_bins: int = 4,
        phase_history_len: int = 16,
    ):
        self.dim            = dim
        self.decay_rate     = decay
        self.harmonic_bins  = harmonic_bins
        self.thresholds     = rhythm_thresholds or dict(self.DEFAULT_THRESHOLDS)

        # Field vector
        self.field: np.ndarray = np.zeros(dim)

        # Bounded injection history — prevents unbounded memory growth
        self.history: collections.deque = collections.deque(maxlen=history_len)

        # Phase angle history for phase coherence computation
        self._phase_history: collections.deque = collections.deque(
            maxlen=phase_history_len
        )

        # Step counter
        self._step = 0

    # ------------------------------------------------------------------
    # Core operations
    # ------------------------------------------------------------------

    def inject(self, vec: np.ndarray, strength: float = 1.0):
        """
        Inject a vector into the field.

        The field accumulates as a superposition. Each injection is
        stored in history for spectral and coherence analysis.

        Parameters
        ----------
        vec : np.ndarray, shape (dim,)
        strength : float
            Injection amplitude. Values < 1.0 for soft/dream injections.
        """
        scaled = vec * strength
        self.field = self.field + scaled
        self.history.append(vec.copy())  # store normalized original, not scaled

        # Track phase angles from FFT for phase coherence
        freqs = np.fft.rfft(vec)
        phases = np.angle(freqs)
        self._phase_history.append(phases)

    def resonate(self) -> np.ndarray:
        """
        Apply nonlinear saturation to the field.
        Returns tanh(field) — bounded to [-1, 1] per dimension.
        This is the observable field state used by Watcher and the loop.
        """
        return np.tanh(self.field)

    def decay(self):
        """Apply exponential decay to the field."""
        self.field = self.field * self.decay_rate
        self._step += 1

    def reset(self):
        """Zero the field (does not clear history)."""
        self.field = np.zeros(self.dim)

    # ------------------------------------------------------------------
    # Observation
    # ------------------------------------------------------------------

    def observe(self) -> FieldState:
        """
        Return the complete observable state of the field.
        Non-destructive — does not modify field or history.
        """
        resonated = self.resonate()
        energy    = float(np.linalg.norm(self.field))
        rhythm    = self.current_rhythm()
        spectral  = self.spectral_snapshot()
        coherence = self.internal_coherence()

        return FieldState(
            raw               = self.field.copy(),
            resonated         = resonated,
            energy            = round(energy, 6),
            rhythm            = rhythm,
            spectral          = spectral,
            internal_coherence = round(coherence, 6),
            step              = self._step,
        )

    # ------------------------------------------------------------------
    # Rhythm detection
    # ------------------------------------------------------------------

    def current_rhythm(self) -> str:
        """
        Map current field energy to a cognitive rhythm state.

        States
        ------
        stabilize  energy < 0.5   consolidation, crystallization
        dream      energy < 2.0   free association, latent recombination
        reflect    energy < 5.0   deliberate recursion
        explore    energy >= 5.0  mutation, novelty seeking
        """
        energy = float(np.linalg.norm(self.field))
        t = self.thresholds

        if energy < t["stabilize"]:
            return "stabilize"
        if energy < t["dream"]:
            return "dream"
        if energy < t["reflect"]:
            return "reflect"
        return "explore"

    # ------------------------------------------------------------------
    # Spectral analysis
    # ------------------------------------------------------------------

    def spectral_snapshot(self) -> SpectralSnapshot:
        """
        FFT-based spectral decomposition of the current field.

        Computes:
          - dominant_frequency: bin with highest power
          - spectral_entropy: distributional entropy across power spectrum
          - harmonic_ratio: fraction of power concentrated in harmonic bins
          - phase_coherence: mean pairwise phase alignment across recent history
        """
        freqs      = np.fft.rfft(self.field)
        power      = np.abs(freqs) ** 2
        total_power = power.sum()

        # Dominant frequency bin
        dominant = int(np.argmax(power))

        # Spectral entropy
        if total_power > 1e-8:
            p = power / total_power
            p = np.clip(p, 1e-10, 1.0)
            spectral_entropy = float(-np.sum(p * np.log(p)))
        else:
            spectral_entropy = 0.0

        # Harmonic ratio: power fraction in first N harmonic bins
        harmonic_ratio = self._harmonic_ratio(power, dominant)

        # Phase coherence across recent injection history
        phase_coherence = self._phase_coherence()

        energy = float(np.linalg.norm(self.field))

        return SpectralSnapshot(
            dominant_frequency = dominant,
            spectral_entropy   = round(spectral_entropy, 6),
            harmonic_ratio     = round(harmonic_ratio, 6),
            phase_coherence    = round(phase_coherence, 6),
            energy             = round(energy, 6),
        )

    def _harmonic_ratio(self, power: np.ndarray, dominant: int) -> float:
        """
        Fraction of total power in harmonic overtone bins of `dominant`.

        Harmonics are at 2×, 3×, ..., N× the dominant frequency bin,
        clipped to the valid FFT range.
        """
        total = power.sum()
        if total < 1e-8 or dominant == 0:
            return 0.0

        harmonic_power = 0.0
        for n in range(2, self.harmonic_bins + 2):
            bin_idx = dominant * n
            if bin_idx < len(power):
                harmonic_power += power[bin_idx]

        return float(np.clip(harmonic_power / total, 0.0, 1.0))

    def _phase_coherence(self) -> float:
        """
        Mean pairwise cosine similarity of phase angle vectors across
        the recent injection history.

        High phase coherence → injected vectors are oscillating in phase.
        Low phase coherence  → chaotic / incoherent injection stream.

        Returns 0.5 (neutral) when history is too short to measure.
        """
        if len(self._phase_history) < 2:
            return 0.5

        phases = list(self._phase_history)
        n      = len(phases)
        sims   = []

        # Sample up to 16 pairs to keep cost bounded
        max_pairs = min(16, n * (n - 1) // 2)
        rng       = np.random.default_rng(seed=self._step)  # deterministic sampling
        pairs     = rng.choice(n, size=(max_pairs, 2), replace=True)

        for i, j in pairs:
            if i == j:
                continue
            a, b = phases[i], phases[j]
            # Phase vectors are angles — use cosine of the difference
            sim = float(np.mean(np.cos(a - b)))
            sims.append(sim)

        if not sims:
            return 0.5

        # Map from [-1, 1] to [0, 1]
        raw = float(np.mean(sims))
        return float(np.clip((raw + 1.0) / 2.0, 0.0, 1.0))

    # ------------------------------------------------------------------
    # Internal coherence
    # ------------------------------------------------------------------

    def internal_coherence(self) -> float:
        """
        Mean cosine similarity between the current field state and
        the mean of recent injection history.

        High → field state is consistent with its recent inputs.
        Low  → field has drifted from its injection trajectory.

        Returns 0.5 (neutral) when history is empty.
        """
        if len(self.history) == 0:
            return 0.5

        history_mean = np.mean(list(self.history)[-32:], axis=0)
        norm_field   = np.linalg.norm(self.field)
        norm_mean    = np.linalg.norm(history_mean)

        if norm_field < 1e-8 or norm_mean < 1e-8:
            return 0.5

        cos = float(
            np.dot(self.field, history_mean) / (norm_field * norm_mean + 1e-8)
        )
        return float(np.clip((cos + 1.0) / 2.0, 0.0, 1.0))

    # ------------------------------------------------------------------
    # Spectral diffusion (future: graph diffusion over semantic lattice)
    # ------------------------------------------------------------------

    def diffuse(self, alpha: float = 0.1):
        """
        Apply spectral smoothing to the field via inverse FFT.

        Attenuates high-frequency components, preserving low-frequency
        structure — effectively a frequency-domain low-pass filter that
        lets dominant patterns emerge from noise.

        alpha : float
            Attenuation strength. 0 = no effect, 1 = full suppression of HF.
        """
        freqs = np.fft.rfft(self.field)

        # Linear attenuation mask: HF bins attenuated by alpha
        n_bins = len(freqs)
        mask = 1.0 - alpha * np.linspace(0.0, 1.0, n_bins)
        freqs = freqs * mask

        self.field = np.fft.irfft(freqs, n=self.dim)

    # ------------------------------------------------------------------
    # Diagnostics
    # ------------------------------------------------------------------

    def summary(self) -> dict:
        """Lightweight diagnostic dict for loop logging."""
        state = self.observe()
        return {
            "energy":            state.energy,
            "rhythm":            state.rhythm,
            "internal_coherence": state.internal_coherence,
            "spectral_entropy":  state.spectral.spectral_entropy,
            "phase_coherence":   state.spectral.phase_coherence,
            "harmonic_ratio":    state.spectral.harmonic_ratio,
            "dominant_freq":     state.spectral.dominant_frequency,
            "history_len":       len(self.history),
            "step":              self._step,
        }
