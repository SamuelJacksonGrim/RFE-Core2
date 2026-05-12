"""
loop/dream_cycle.py

Dream cycle — deep offline synthesis during idle / low-energy periods.

The dream cycle runs when the field is in "stabilize" or "dream" rhythm
for an extended period. It performs intensive memory recombination,
harmonic mutation, and symbolic emergence without external input.

Unlike the autonomous cycle's dream_behavior (one dream call per step),
the dream cycle is a dedicated offline loop that runs N dream iterations
with progressive mutation depth, attractor merge passes, and crystal
consolidation.

This is closest to biological REM sleep: consolidation, abstraction,
symbolic synthesis, and identity stabilization — all without new input.
"""

from __future__ import annotations

import time
import logging
from dataclasses import dataclass
from typing import List, Optional

import numpy as np

from agents.dreamer import Dreamer, DreamProduct
from substrate.memory_crystals import CrystalStore
from substrate.resonance_field import ResonanceField
from agents.attractor import Attractor

logger = logging.getLogger(__name__)


@dataclass
class DreamCycleReport:
    iterations:     int
    products:       List[DreamProduct]
    injected:       int
    stored:         int
    crystallized:   int
    elapsed_s:      float
    field_energy_before: float
    field_energy_after:  float


class DreamCycle:
    """
    Deep offline synthesis loop.

    Parameters
    ----------
    dreamer : Dreamer
    crystal_store : CrystalStore
    field : ResonanceField
    attractor : Attractor or None
    n_iterations : int
        Number of dream iterations per cycle run.
    mutation_ramp : bool
        If True, mutation scale increases with each iteration
        (deeper exploration as the cycle progresses).
    merge_attractors : bool
        If True, runs attractor.merge_pass() at end of cycle.
    diffuse_field : bool
        If True, applies field.diffuse() after each iteration.
    """

    def __init__(
        self,
        dreamer:          Dreamer,
        crystal_store:    CrystalStore,
        field:            ResonanceField,
        attractor:        Optional[Attractor] = None,
        n_iterations:     int   = 8,
        mutation_ramp:    bool  = True,
        merge_attractors: bool  = True,
        diffuse_field:    bool  = True,
    ):
        self.dreamer          = dreamer
        self.crystal_store    = crystal_store
        self.field            = field
        self.attractor        = attractor
        self.n_iterations     = n_iterations
        self.mutation_ramp    = mutation_ramp
        self.merge_attractors = merge_attractors
        self.diffuse_field    = diffuse_field

    def run(
        self,
        emotion=None,    # EmotionalGradient
        watcher=None,    # Watcher
        anchor: Optional[np.ndarray] = None,
        generator=None,  # Generator
    ) -> DreamCycleReport:
        """
        Execute one full dream cycle.

        Parameters
        ----------
        emotion : EmotionalGradient or None
        watcher : Watcher or None
        anchor : np.ndarray or None
            Witness anchor for coherence evaluation.
        generator : Generator or None

        Returns
        -------
        DreamCycleReport
        """
        t0 = time.perf_counter()
        field_energy_before = float(np.linalg.norm(self.field.field))

        all_products:  List[DreamProduct] = []
        total_injected    = 0
        total_stored      = 0
        total_crystallized = 0

        # Store original mutation scale and ramp if needed
        base_mutation = self.dreamer.mutator.mutation_rate

        for i in range(self.n_iterations):

            if self.mutation_ramp:
                ramp = 1.0 + (i / max(self.n_iterations - 1, 1)) * 0.5
                self.dreamer.mutator.mutation_rate = min(base_mutation * ramp, 0.5)

            products = self.dreamer.dream(
                emotion       = emotion,
                watcher       = watcher,
                anchor        = anchor,
                crystal_store = self.crystal_store,
                generator     = generator,
            )

            for p in products:
                if p.injected:
                    total_injected += 1
                if p.stored:
                    total_stored += 1

            all_products.extend(products)

            # Check crystallization of injected products
            if watcher is not None and anchor is not None:
                field_state = self.field.resonate()
                for p in products:
                    if p.injected:
                        report = watcher.evaluate(p.vector, anchor, field_state)
                        crystal = self.crystal_store.maybe_crystallize(
                            vec                      = p.vector,
                            composite_coherence      = report.composite,
                            crystallization_pressure = report.crystallization_pressure,
                            long_relation            = 0.6,
                            origin_tokens            = [p.key],
                            field                    = self.field,
                            generator                = generator,
                        )
                        if crystal is not None:
                            total_crystallized += 1

            if self.diffuse_field:
                self.field.diffuse(alpha=0.03)

            logger.debug(
                "Dream iteration %d/%d: %d products, %d injected",
                i + 1, self.n_iterations, len(products), total_injected,
            )

        # Restore mutation rate
        self.dreamer.mutator.mutation_rate = base_mutation

        # Post-cycle consolidation
        if self.merge_attractors and self.attractor is not None:
            self.attractor.merge_pass()

        self.crystal_store.decay_step()

        field_energy_after = float(np.linalg.norm(self.field.field))
        elapsed = time.perf_counter() - t0

        report = DreamCycleReport(
            iterations          = self.n_iterations,
            products            = all_products,
            injected            = total_injected,
            stored              = total_stored,
            crystallized        = total_crystallized,
            elapsed_s           = round(elapsed, 3),
            field_energy_before = round(field_energy_before, 4),
            field_energy_after  = round(field_energy_after, 4),
        )

        logger.info(
            "Dream cycle complete: %d iterations, %d products, "
            "%d injected, %d crystallized, %.2fs",
            report.iterations, len(report.products),
            report.injected, report.crystallized, report.elapsed_s,
        )

        return report
