"""
interference — Noise, mutation, and wave collapse for RFE-Core2.
"""

from interference.wave_collapse import collapse_wave
from interference.differential import inject_ambiguity
from interference.phase_noise import PhaseNoise
from interference.bifurcation import BifurcationEngine
from interference.harmonic_mutation import HarmonicMutator

__all__ = [
    "collapse_wave",
    "inject_ambiguity",
    "PhaseNoise",
    "BifurcationEngine",
    "HarmonicMutator",
]
