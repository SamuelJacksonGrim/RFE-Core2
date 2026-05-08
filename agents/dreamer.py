"""
agents/dreamer.py

Dream synthesis — offline latent recombination and symbolic mutation.

The Dreamer runs during low-energy field states (rhythm == "dream" or
"stabilize") and performs:
  1. Memory sampling from VectorSpace and TemporalStream
  2. Harmonic recombination of sampled vectors
  3. Bifurcation into divergent variants
  4. Emotional modulation of mutation intensity
  5. Field injection of dream products
  6. Storage of viable dreams back into VectorSpace

This is where the system generates genuine novelty:
  - Abstract synthesis from disparate memories
  - Symbolic emergence from harmonic mutation
  - Unexpected associations from bifurcated recombination
  - Latent exploration without external input

Dream products that survive Watcher evaluation are stored and can
later crystallize into memory crystals or attractor centers.
"""

from __future__ import annotations

import random
import uuid
from dataclasses import dataclass
from typing import List, Optional

import numpy as np

from interference.wave_collapse import collapse_wave
from interference.differential import inject_ambiguity
from interference.harmonic_mutation import HarmonicMutator
from interference.bifurcation import BifurcationEngine


@dataclass
class DreamProduct:
    """A single dream synthesis output."""
    key:         str
    vector:      np.ndarray
    origin_keys: List[str]    # memory keys that seeded this dream
    coherence:   float        # Watcher evaluation (if available)
    injected:    bool         # whether it was injected into the field
    stored:      bool         # whether it was stored in VectorSpace


class Dreamer:
    """
    Offline latent recombination and symbolic mutation engine.

    Parameters
    ----------
    field : ResonanceField
        Target field for dream injection.
    vector_space : VectorSpace
        Memory source and storage target.
    stream : TemporalStream or None
        Secondary memory source (recent trajectory).
    mutator : HarmonicMutator or None
        Harmonic mutation engine. Created with defaults if None.
    bifurcator : BifurcationEngine or None
        Bifurcation engine for variant generation.
    base_injection_strength : float
        Field injection strength for dream products.
    n_samples : int
        Number of memory vectors sampled per dream cycle.
    n_variants : int
        Number of bifurcated variants to generate from each dream.
    store_dreams : bool
        Whether to store dream products back into VectorSpace.
    coherence_gate : float
        Minimum coherence for a dream to be injected / stored.
    """

    def __init__(
        self,
        field,
        vector_space,
        stream=None,
        mutator:                  Optional[HarmonicMutator]   = None,
        bifurcator:               Optional[BifurcationEngine] = None,
        base_injection_strength:  float = 0.4,
        n_samples:                int   = 3,
        n_variants:               int   = 2,
        store_dreams:             bool  = True,
        coherence_gate:           float = 0.25,
    ):
        self.field                    = field
        self.vector_space             = vector_space
        self.stream                   = stream
        self.mutator                  = mutator or HarmonicMutator(mutation_rate=0.2, amplitude_scale=0.4)
        self.bifurcator               = bifurcator or BifurcationEngine(n_branches=2, divergence=0.15, mode="radial")
        self.base_injection_strength  = base_injection_strength
        self.n_samples                = n_samples
        self.n_variants               = n_variants
        self.store_dreams             = store_dreams
        self.coherence_gate           = coherence_gate

        self._dream_count = 0
        self._rng = np.random.default_rng()

    # ------------------------------------------------------------------
    # Dream cycle
    # ------------------------------------------------------------------

    def dream(
        self,
        emotion=None,      # EmotionalGradient instance
        watcher=None,      # Watcher instance
        anchor=None,       # Witness anchor np.ndarray
        crystal_store=None,
        generator=None,
    ) -> List[DreamProduct]:
        """
        Execute one dream cycle.

        Parameters
        ----------
        emotion : EmotionalGradient or None
            Modulates mutation intensity and injection strength.
        watcher : Watcher or None
            Evaluates dream coherence before injection.
        anchor : np.ndarray or None
            Witness anchor for coherence evaluation.
        crystal_store : CrystalStore or None
            If provided, high-coherence dreams are offered for crystallization.
        generator : Generator or None
            For ecology signal relay.

        Returns
        -------
        List[DreamProduct]
        """
        if len(self.vector_space) < 2:
            return []

        # Modulate parameters from emotional state
        if emotion is not None:
            mutation_scale    = emotion.mutation_scale()
            injection_strength = self.base_injection_strength * emotion.field_gain() * 0.5
        else:
            mutation_scale    = 0.1
            injection_strength = self.base_injection_strength

        field_state = self.field.resonate()
        products    = []

        # --- Sample memories ---
        sampled_vecs, sampled_keys = self._sample_memories()
        if len(sampled_vecs) < 2:
            return []

        # --- Harmonic recombination ---
        hybrid = self._recombine(sampled_vecs, mutation_scale)

        # --- Generate variants ---
        variants = self.bifurcator.bifurcate(hybrid, rng=self._rng)

        for variant in variants[:self.n_variants]:
            # Ambiguity injection (EPHEMERAL token class in ecology)
            variant = inject_ambiguity(variant, scale=mutation_scale * 0.5, mode="rotational", rng=self._rng)

            key     = f"dream_{uuid.uuid4().hex[:8]}"
            coherence = 0.5
            injected  = False
            stored    = False

            # Coherence gate
            if watcher is not None and anchor is not None:
                report    = watcher.evaluate(variant, anchor, field_state)
                coherence = report.composite

            if coherence >= self.coherence_gate:
                # Inject into field
                self.field.inject(variant, strength=injection_strength)
                injected = True

                # Store back into VectorSpace
                if self.store_dreams:
                    self.vector_space.put(key, variant, tags=["dream"])
                    stored = True

                # Offer to crystal store
                if crystal_store is not None and watcher is not None and anchor is not None:
                    from substrate.memory_crystals import CrystalStore
                    report = watcher.evaluate(variant, anchor, field_state)
                    crystal_store.maybe_crystallize(
                        vec                      = variant,
                        composite_coherence      = report.composite,
                        crystallization_pressure = report.crystallization_pressure,
                        long_relation            = 0.5,  # dreams don't have long-relation yet
                        origin_tokens            = [key],
                        field                    = self.field,
                        generator                = generator,
                    )

            products.append(DreamProduct(
                key         = key,
                vector      = variant,
                origin_keys = sampled_keys,
                coherence   = round(coherence, 4),
                injected    = injected,
                stored      = stored,
            ))

        self._dream_count += 1
        return products

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _sample_memories(self):
        """Sample vectors from VectorSpace and optionally TemporalStream."""
        keys    = self.vector_space.keys()
        n       = min(self.n_samples, len(keys))
        sampled_keys = random.sample(keys, n)
        sampled_vecs = [self.vector_space.get(k) for k in sampled_keys]
        sampled_vecs = [v for v in sampled_vecs if v is not None]

        # Supplement with recent stream vectors if available
        if self.stream is not None and len(self.stream) > 0:
            stream_vecs = self.stream.recent_vectors(n=2)
            sampled_vecs.extend(stream_vecs)
            sampled_keys.extend([f"stream_{i}" for i in range(len(stream_vecs))])

        return sampled_vecs, sampled_keys

    def _recombine(self, vectors: List[np.ndarray], mutation_scale: float) -> np.ndarray:
        """Harmonically recombine a list of vectors into a single hybrid."""
        if len(vectors) == 1:
            return self.mutator.mutate(vectors[0], rng=self._rng)

        if len(vectors) == 2:
            hybrid = self.mutator.recombine(vectors[0], vectors[1], rng=self._rng)
        else:
            # Multi-vector: progressive recombination
            hybrid = self.mutator.recombine(vectors[0], vectors[1], rng=self._rng)
            for v in vectors[2:]:
                hybrid = self.mutator.recombine(hybrid, v, rng=self._rng, blend=0.3)

        # Apply mutation scaled by emotional state
        original_rate = self.mutator.mutation_rate
        self.mutator.mutation_rate = float(np.clip(mutation_scale * 2.0, 0.05, 0.5))
        hybrid = self.mutator.mutate(hybrid, rng=self._rng)
        self.mutator.mutation_rate = original_rate

        return hybrid

    # ------------------------------------------------------------------
    # Diagnostics
    # ------------------------------------------------------------------

    @property
    def dream_count(self) -> int:
        return self._dream_count
