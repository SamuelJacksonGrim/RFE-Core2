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
cognition/reflective_loop.py

Reflective loop — recursive self-refinement until convergence.

Where RecursiveAttention refines a vector by attending to history,
the ReflectiveLoop refines it by running multiple passes through
the full cognition stack (attractor pull → watcher check → field
resonance blend) until the vector stabilizes or a depth limit is hit.

This is where the system begins to genuinely reflect:
  - A thought is held
  - Run through its own coherence filter
  - Adjusted toward the field
  - Re-evaluated
  - Repeated until stable

Convergence is measured by cosine similarity between successive passes.
High similarity = the thought has found its stable form.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np


@dataclass
class ReflectionResult:
    vector:          np.ndarray   # final stabilized vector
    passes:          int          # how many passes were needed
    converged:       bool         # True if convergence criterion met
    final_coherence: float        # coherence on the final pass
    delta_trace:     list         # cosine delta between successive passes


class ReflectiveLoop:
    """
    Recursive self-refinement over the cognition stack.

    Parameters
    ----------
    max_depth : int
        Maximum number of refinement passes.
    convergence_threshold : float
        Cosine similarity between successive passes that signals convergence.
    field_blend : float
        How strongly the field state pulls each pass.
    attractor_blend : float
        How strongly the nearest attractor pulls each pass.
    coherence_gate : float
        Minimum coherence to continue refining. Below this, reflection halts.
    """

    def __init__(
        self,
        max_depth:            int   = 5,
        convergence_threshold: float = 0.995,
        field_blend:          float = 0.1,
        attractor_blend:      float = 0.08,
        coherence_gate:       float = 0.2,
    ):
        self.max_depth             = max_depth
        self.convergence_threshold = convergence_threshold
        self.field_blend           = field_blend
        self.attractor_blend       = attractor_blend
        self.coherence_gate        = coherence_gate

    def reflect(
        self,
        vec:       np.ndarray,
        watcher=None,        # Watcher instance
        anchor:    Optional[np.ndarray] = None,
        field=None,          # ResonanceField instance
        attractor=None,      # Attractor instance
        generator=None,      # Generator (for signal relay)
    ) -> ReflectionResult:
        """
        Run recursive self-refinement on vec.

        Parameters
        ----------
        vec : np.ndarray, shape (dim,)
        watcher : Watcher or None
            Used for coherence evaluation on each pass.
        anchor : np.ndarray or None
            Witness anchor for geometric coherence.
        field : ResonanceField or None
            Field state blended in on each pass.
        attractor : Attractor or None
            Attractor pull applied on each pass.
        generator : Generator or None
            For signal relay on convergence.

        Returns
        -------
        ReflectionResult
        """
        current     = vec.copy().astype(np.float32)
        delta_trace = []
        converged   = False
        coherence   = 0.5
        passes      = 0

        field_state = field.resonate() if field is not None else None

        for i in range(self.max_depth):
            passes = i + 1
            prev   = current.copy()

            # --- Attractor pull ---
            if attractor is not None and len(attractor.centers) > 0:
                current = attractor.pull(current, generator=generator)

            # --- Field blend ---
            if field_state is not None:
                field_norm = np.linalg.norm(field_state)
                if field_norm > 1e-6:
                    blended = (1.0 - self.field_blend) * current + self.field_blend * field_state
                    norm    = np.linalg.norm(blended)
                    current = (blended / (norm + 1e-8)).astype(np.float32)

            # --- Coherence check ---
            if watcher is not None and anchor is not None:
                report    = watcher.evaluate(current, anchor, field_state)
                coherence = report.composite
                if coherence < self.coherence_gate and i > 0:
                    # Vector is incoherent — halt refinement
                    break
            
            # --- Convergence check ---
            delta = float(np.dot(current, prev) / (
                np.linalg.norm(current) * np.linalg.norm(prev) + 1e-8
            ))
            delta_trace.append(round(delta, 6))

            if delta >= self.convergence_threshold:
                converged = True
                break

        return ReflectionResult(
            vector          = current,
            passes          = passes,
            converged       = converged,
            final_coherence = round(coherence, 6),
            delta_trace     = delta_trace,
        )
